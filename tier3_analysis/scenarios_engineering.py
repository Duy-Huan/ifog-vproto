"""IFOG-SIM-SPEC-005 5 System Engineering & Production Scenarios (ENG-01 .. ENG-05).

Implements:
  - ENG-01 (EQ-35): Hardware Sizing (ADC/DAC ENOB 10..16 bit, Aperture Jitter, TIA/SLD Pareto)
  - ENG-02 (EQ-36): Real 3-Axis Shared-SLD & Shared-Rail IMU SystemC-AMS Co-Simulation
  - ENG-03 (EQ-37, EQ-38): Vibration Rectification Error (VRE) & Dynamic Faraday / Mu-metal Sizing
  - ENG-04 (EQ-39): 5-Fault Injection & Real-Time FPGA BIT/FDIR Verification (Time-to-Alert & Recovery)
  - ENG-05 (EQ-40, EQ-41): Parallel Monte Carlo Production Yield (C_pk) & -40..+85 C Virtual Thermal Calibration (Poly + EKF)
"""

from __future__ import annotations

import concurrent.futures
import csv
import json
import math
import os
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from tier1_offline.config_loader import (
    DEG_S_TO_RAD_S,
    RAD_S_TO_DEG_H,
    RAD_S_TO_DEG_S,
    compute_tia_dynamics,
    deep_merge,
)
from tier1_offline.jones_spectral import solve_tier1_optics
from tier1_offline.shupe_thermal import solve_tier1_shupe
from tier3_analysis.binary_io import read_dsp_trace, read_sim_records


def compute_wilson_ci_95(n_pass: int, n_total: int) -> tuple[float, float]:
    """Compute exact Wilson 95% binomial confidence interval for Production Yield (EQ-40)."""
    if n_total <= 0:
        raise ValueError("n_total must be positive")
    z = 1.959963984540054
    p = n_pass / n_total
    denom = 1.0 + (z * z) / n_total
    center = (p + (z * z) / (2.0 * n_total)) / denom
    half = (z * math.sqrt((p * (1.0 - p)) / n_total + (z * z) / (4.0 * n_total * n_total))) / denom
    return max(0.0, center - half), min(1.0, center + half)


def compute_cpk(samples: np.ndarray, lsl: float, usl: float) -> float:
    """Compute process capability index C_pk = min((USL - mu)/(3*sigma), (mu - LSL)/(3*sigma)) (EQ-40)."""
    mu = float(np.mean(samples))
    sigma = float(np.std(samples, ddof=1)) if len(samples) > 1 else 0.0
    if sigma <= 1.0e-18:
        return 10.0 if (lsl <= mu <= usl) else 0.0
    return min((usl - mu) / (3.0 * sigma), (mu - lsl) / (3.0 * sigma))


def compute_mumetal_shield_dB(
    sensitivity_deg_h_per_G: float,
    max_field_G: float,
    bias_budget_deg_h: float,
) -> float:
    """Compute required Mu-metal magnetic shielding attenuation in dB (EQ-38)."""
    unshielded = abs(sensitivity_deg_h_per_G) * abs(max_field_G)
    if unshielded <= bias_budget_deg_h or bias_budget_deg_h <= 0.0:
        return 0.0
    return float(20.0 * math.log10(unshielded / bias_budget_deg_h))


def fit_thermal_polynomial_and_ekf(
    T_C: np.ndarray,
    dT_dt: np.ndarray,
    bias_deg_h: np.ndarray,
    T_ref_C: float = 25.0,
) -> dict[str, Any]:
    """Fit 2D thermal compensation polynomial & run 1D Extended Kalman Filter (EKF) bias estimator (EQ-41)."""
    dT = T_C - T_ref_C
    X = np.column_stack([np.ones_like(dT), dT, dT**2, dT_dt, dT * dT_dt])
    coeffs, _, _, _ = np.linalg.lstsq(X, bias_deg_h, rcond=None)
    pred_poly = X @ coeffs
    resid_poly = bias_deg_h - pred_poly

    # Sequential EKF estimating thermal bias state x_k = [bias_offset, c_T, c_T2, c_dT] online
    x_hat = np.zeros(4, dtype=np.float64)
    P_cov = np.diag([100.0, 10.0, 1.0, 100.0])
    Q_proc = np.diag([1.0e-5, 1.0e-7, 1.0e-9, 1.0e-6])
    R_meas = 1.0e-3
    ekf_pred = np.zeros_like(bias_deg_h)
    for idx in range(len(bias_deg_h)):
        H = np.array([1.0, float(dT[idx]), float(dT[idx] ** 2), float(dT_dt[idx])], dtype=np.float64)
        P_pred = P_cov + Q_proc
        y_pred = float(H @ x_hat)
        ekf_pred[idx] = y_pred
        S = float(H @ P_pred @ H) + R_meas
        K_gain = (P_pred @ H) / S
        x_hat = x_hat + K_gain * (float(bias_deg_h[idx]) - y_pred)
        P_cov = (np.eye(4) - np.outer(K_gain, H)) @ P_pred

    resid_ekf = bias_deg_h - ekf_pred
    raw_rms = float(np.sqrt(np.mean(bias_deg_h**2)))
    poly_rms = float(np.sqrt(np.mean(resid_poly**2)))
    # Evaluate EKF tracking error after initial 5-sample adaptation warmup
    warm = min(5, max(1, len(resid_ekf) // 3))
    ekf_rms = float(np.sqrt(np.mean(resid_ekf[warm:] ** 2)))
    return {
        "poly_coeffs": [float(c) for c in coeffs],
        "raw_rms_deg_per_h": raw_rms,
        "poly_residual_rms_deg_per_h": poly_rms,
        "ekf_residual_rms_deg_per_h": ekf_rms,
        "poly_reduction_pct": (1.0 - poly_rms / max(raw_rms, 1.0e-12)) * 100.0,
        "ekf_reduction_pct": (1.0 - ekf_rms / max(raw_rms, 1.0e-12)) * 100.0,
        "poly_pred_deg_per_h": [float(v) for v in pred_poly],
        "ekf_pred_deg_per_h": [float(v) for v in ekf_pred],
    }


def _run_t2(
    bin_path: Path,
    cfg: dict[str, Any],
    phys_p: Path,
    work_dir: Path,
    extra_args: list[str] | None = None,
) -> dict[str, Any]:
    work_dir.mkdir(parents=True, exist_ok=True)
    cf = work_dir / "cfg.json"
    cf.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    cmd = [str(bin_path), "--phys", str(phys_p), "--cfg", str(cf), "--out", str(work_dir)]
    if extra_args:
        cmd.extend(extra_args)
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    if extra_args and "--imu3axis" in extra_args:
        return json.loads((work_dir / "imu_3axis_summary.json").read_text(encoding="utf-8"))
    return json.loads((work_dir / "sim_summary.json").read_text(encoding="utf-8"))


def _estimate_arw_deg_rt_h(bin_path_sim: Path) -> float:
    """Estimate short-term ARW [deg/sqrt(h)] from stationary Tier 2 sim_out.bin stream."""
    rec = read_sim_records(bin_path_sim)
    skip = len(rec["omega_out"]) // 4
    w = rec["omega_out"][skip:]
    dt = float(np.median(np.diff(rec["t"])))
    sigma_w = float(np.std(w))
    # N [rad/sqrt(s)] = sigma_w * sqrt(dt); convert rad/sqrt(s) -> deg/sqrt(h) = (180/pi)*60
    n_rad_rt_s = sigma_w * math.sqrt(dt)
    return float(n_rad_rt_s * (180.0 / math.pi) * 60.0)


def run_eng_hw_sizing(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    workers: int | None = None,
) -> dict[str, Any]:
    """ENG-01: Hardware Sizing Trade-Off — ENOB (10..16 bit), Aperture Jitter (EQ-35) & TIA/SLD Pareto."""
    work = out_dir / "eng01_work"
    work.mkdir(parents=True, exist_ok=True)
    phys = solve_tier1_optics(base_cfg)
    phys_p = work / "phys_params.json"
    phys_p.write_text(json.dumps(phys, indent=2), encoding="utf-8")
    max_w = workers if workers is not None else min(4, max(1, os.cpu_count() or 1))

    # 1A. ENOB Sweep (10..16 bits) at tiny slow rate 0.02 deg/s (quantization & deadband sensitivity)
    enob_bits = [10, 11, 12, 13, 14, 15, 16]
    test_rate_deg_s = 0.02

    def _run_enob(bits: int) -> dict[str, Any]:
        cfg = deep_merge(
            base_cfg,
            {
                "adc_dac": {"N_adc_bits": bits, "N_dac_bits": bits},
                "dsp": {"en_prbs_dither": False, "en_vpi_loop": True},
                "noise": {"en_white_noise": True, "en_pink_noise": False},
                "ablation_flags": {"en_quantization": True, "en_xtalk": True, "en_ltf_transient": True},
                "simulation": {
                    "duration_s": 0.06,
                    "decimation_tau": 4,
                    "dump_micro_ms": 0.0,
                    "stimulus": {"type": "constant", "omega_rad_per_s": test_rate_deg_s * DEG_S_TO_RAD_S},
                },
            },
        )
        sub = work / f"enob_{bits}"
        s = _run_t2(bin_path, cfg, phys_p, sub)
        mean_deg_s = float(s["mean_omega_out_second_half_rad_per_s"]) * RAD_S_TO_DEG_S
        deadband_err = abs(mean_deg_s - test_rate_deg_s)
        arw = _estimate_arw_deg_rt_h(sub / "sim_out.bin")
        meets_spec = bool(deadband_err < 0.01 and arw < 0.005)
        return {
            "bits": bits,
            "deadband_err_deg_per_s": deadband_err,
            "arw_deg_per_rt_h": arw,
            "meets_spec": meets_spec,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        enob_rows = list(pool.map(_run_enob, enob_bits))
    passing_bits = [r["bits"] for r in enob_rows if r["meets_spec"]]
    min_passing_bits = int(min(passing_bits)) if passing_bits else 16

    # 1B. Aperture Jitter Sweep (0, 20 ps, 100 ps, 500 ps, 2 ns, 10 ns) per EQ-35
    jitter_ps_list = [0.0, 20.0, 100.0, 500.0, 2000.0, 10000.0]

    def _run_jitter(jit_ps: float) -> dict[str, Any]:
        cfg = deep_merge(
            base_cfg,
            {
                "adc_dac": {"aperture_jitter_s": jit_ps * 1.0e-12},
                "dsp": {"en_prbs_dither": False, "en_vpi_loop": True},
                "noise": {"en_white_noise": True, "en_pink_noise": False},
                "ablation_flags": {"en_ltf_transient": True, "en_xtalk": True, "en_quantization": True},
                "simulation": {
                    "duration_s": 0.06,
                    "decimation_tau": 4,
                    "dump_micro_ms": 0.0,
                    "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
                },
            },
        )
        sub = work / f"jitter_{int(jit_ps)}ps"
        _run_t2(bin_path, cfg, phys_p, sub)
        arw = _estimate_arw_deg_rt_h(sub / "sim_out.bin")
        return {"jitter_ps": jit_ps, "arw_deg_per_rt_h": arw}

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        jitter_rows = list(pool.map(_run_jitter, jitter_ps_list))
    arw_0 = jitter_rows[0]["arw_deg_per_rt_h"]
    for r in jitter_rows:
        r["arw_degradation_pct"] = (r["arw_deg_per_rt_h"] / max(arw_0, 1.0e-12) - 1.0) * 100.0

    # 1C. TIA (R_f, C_f_opt) & SLD Power P_peak Pareto Grid
    pareto_specs = [
        (10_000.0, 50.0e-6),
        (25_000.0, 50.0e-6),
        (50_000.0, 50.0e-6),
        (10_000.0, 100.0e-6),
        (50_000.0, 100.0e-6),
        (100_000.0, 100.0e-6),
        (50_000.0, 200.0e-6),
        (25_000.0, 200.0e-6),
    ]

    def _run_pareto(pair: tuple[float, float]) -> dict[str, Any]:
        rf, p_pk = pair
        dyn = compute_tia_dynamics(
            rf,
            float(base_cfg["analog_frontend"]["C_tot_F"]),
            0.0,
            float(base_cfg["analog_frontend"]["f_gbw_Hz"]),
        )
        cf_opt = dyn["C_f_opt_F"]
        dyn_opt = compute_tia_dynamics(
            rf,
            float(base_cfg["analog_frontend"]["C_tot_F"]),
            cf_opt,
            float(base_cfg["analog_frontend"]["f_gbw_Hz"]),
        )
        cfg = deep_merge(
            base_cfg,
            {
                "optics": {"P_peak_W": p_pk},
                "analog_frontend": {"R_f_ohm": rf, "C_f_F": cf_opt},
                "dsp": {"en_prbs_dither": False},
                "noise": {"en_white_noise": True, "en_pink_noise": False},
                "simulation": {
                    "duration_s": 0.04,
                    "decimation_tau": 4,
                    "dump_micro_ms": 0.0,
                    "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
                },
            },
        )
        sub = work / f"pareto_rf{int(rf)}_p{int(p_pk * 1e6)}"
        s = _run_t2(bin_path, cfg, phys_p, sub)
        arw = _estimate_arw_deg_rt_h(sub / "sim_out.bin")
        return {
            "R_f_kohm": rf / 1.0e3,
            "C_f_opt_pF": cf_opt * 1.0e12,
            "P_peak_uW": p_pk * 1.0e6,
            "t_s_0p1pct_ns": dyn_opt["t_s_0p1pct_s"] * 1.0e9,
            "adc_clip_count": int(s["adc_clip_count"]),
            "arw_deg_per_rt_h": arw,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        pareto_rows = list(pool.map(_run_pareto, pareto_specs))
    valid_pareto = [r for r in pareto_rows if r["adc_clip_count"] == 0]
    best_pareto = min(valid_pareto, key=lambda r: r["arw_deg_per_rt_h"])

    result = {
        "scenario_id": "ENG-01",
        "formula_id": "EQ-35",
        "title": "Hardware Sizing Trade-Off (ENOB 10-16 bit, Aperture Jitter & TIA/SLD Pareto)",
        "enob_sweep": enob_rows,
        "recommended_min_bits": min_passing_bits,
        "jitter_sweep": jitter_rows,
        "tia_sld_pareto": pareto_rows,
        "pareto_optimal": best_pareto,
        "pass": bool(
            enob_rows[-1]["deadband_err_deg_per_s"] <= enob_rows[0]["deadband_err_deg_per_s"]
            and jitter_rows[-1]["arw_deg_per_rt_h"] > jitter_rows[0]["arw_deg_per_rt_h"]
            and best_pareto["arw_deg_per_rt_h"] > 0.0
        ),
    }
    (out_dir / "eng01_hw_sizing.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_eng_imu_3axis(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    """ENG-02: Real Concurrent 3-Axis IMU SystemC-AMS Co-Simulation (Shared SLD + Power Rail, EQ-36)."""
    work = out_dir / "eng02_work"
    work.mkdir(parents=True, exist_ok=True)
    phys = solve_tier1_optics(base_cfg)
    phys["visibility_V"] = 1.0
    phys["phi_pol_rad"] = 0.0
    phys["delta_phi_kerr_rad"] = 0.0
    phys_p = work / "phys_ideal.json"
    phys_p.write_text(json.dumps(phys, indent=2), encoding="utf-8")

    omega_x_deg_s = 500.0
    base_imu = deep_merge(
        base_cfg,
        {
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_vpi_loop": True, "en_prbs_dither": False, "max_delta_phi_step_rad": 25.0},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": True,
                "en_ram": True,
                "en_xtalk": True,
                "en_ltf_transient": True,
                "en_tia_poly_nl": True,
                "en_quantization": False,
            },
            "simulation": {"duration_s": 0.04, "decimation_tau": 6, "dump_micro_ms": 0.0},
        },
    )

    def _run_case(label: str, dsp_mode: str, alpha: float, rho: float, z_rail: float) -> dict[str, Any]:
        cfg = deep_merge(
            base_imu,
            {
                "dsp": {"mode": dsp_mode, "alpha_rad": alpha},
                "imu_3axis": {
                    "omega_x_rad_per_s": omega_x_deg_s * DEG_S_TO_RAD_S,
                    "omega_y_rad_per_s": 0.0,
                    "omega_z_rad_per_s": 0.0,
                    "rho_opt_coupling": rho,
                    "z_rail_ohm": z_rail,
                    "r_load_ohm": 50.0,
                    "c_load_F": 200.0e-12,
                },
            },
        )
        return _run_t2(bin_path, cfg, phys_p, work / label, extra_args=["--imu3axis"])

    iso_4s = _run_case("isolated_4s", "4state", math.pi / 4.0, 0.0, 0.0)
    cpl_4s = _run_case("coupled_4s", "4state", math.pi / 4.0, 2.0e-3, 0.25)
    cpl_6s = _run_case("coupled_6s", "6state", math.pi / 3.0, 2.0e-3, 0.25)

    y_crosstalk_4s = abs(float(cpl_4s["y_bias_err_deg_per_h"]) - float(iso_4s["y_bias_err_deg_per_h"]))
    y_crosstalk_6s = abs(float(cpl_6s["y_bias_err_deg_per_h"]))
    result = {
        "scenario_id": "ENG-02",
        "formula_id": "EQ-36",
        "title": "3-Axis IMU Shared-SLD & Shared-Rail Inter-Axis Crosstalk (Axis X = 500 deg/s)",
        "axis_x_target_deg_per_s": omega_x_deg_s,
        "isolated_4state": iso_4s,
        "coupled_4state": cpl_4s,
        "coupled_6state": cpl_6s,
        "inter_axis_y_crosstalk_4state_deg_per_h": y_crosstalk_4s,
        "inter_axis_y_crosstalk_6state_deg_per_h": y_crosstalk_6s,
        "peak_rail_droop_V": float(cpl_4s["peak_rail_droop_V"]),
        "pass": bool(
            abs(float(cpl_4s["axis_x_mean_rate_deg_per_s"]) - omega_x_deg_s) < 5.0
            and int(cpl_4s["axis_x_flyback_count"]) > 1000
            and float(cpl_4s["peak_rail_droop_V"]) > 0.0
            and y_crosstalk_4s > 0.0
        ),
    }
    (out_dir / "eng02_imu_3axis.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_eng_vre_faraday(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    workers: int | None = None,
) -> dict[str, Any]:
    """ENG-03: Vibration Rectification Error (VRE, EQ-37) & Magnetic Faraday / Mu-Metal Sizing (EQ-38)."""
    work = out_dir / "eng03_work"
    work.mkdir(parents=True, exist_ok=True)
    phys = solve_tier1_optics(base_cfg)
    phys["visibility_V"] = 1.0
    phys["phi_pol_rad"] = 0.0
    phys["delta_phi_kerr_rad"] = 0.0
    phys_p = work / "phys_ideal.json"
    phys_p.write_text(json.dumps(phys, indent=2), encoding="utf-8")
    max_w = workers if workers is not None else min(4, max(1, os.cpu_count() or 1))

    # 3A. VRE Sweep: g_rms in [0, 2, 5, 10] g with quadratic TIA nonlinearity G2 ON vs OFF
    # Note: Quadratic G2*(V_0 + dV_vib)^2 produces rectified bias when combined with modulation asymmetry!
    vre_base = deep_merge(
        base_cfg,
        {
            "dsp": {"mode": "4state", "alpha_rad": math.pi / 4.0, "en_vpi_loop": False, "en_prbs_dither": False},
            "mioc": {"eps_vpi": 0.0, "gamma_nl_rad_per_V2": 0.0, "alpha_ram_per_V": 2.0e-4},
            "analog_frontend": {"C_xtalk_F": 0.0, "k_xtalk_A_per_V": 0.0, "G2_per_V": 0.08, "G3_per_V2": 0.0},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": False,
                "en_ram": True,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": True,
                "en_quantization": False,
            },
            "simulation": {
                "duration_s": 0.04,
                "decimation_tau": 1,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
            },
        },
    )
    g_levels = [0.0, 2.0, 5.0, 10.0]

    def _run_vre(args_tuple: tuple[float, bool]) -> dict[str, Any]:
        g_val, en_g2 = args_tuple
        cfg = deep_merge(
            vre_base,
            {
                "ablation_flags": {"en_tia_poly_nl": en_g2},
                "vibration": {
                    "en_vibration": g_val > 0.0,
                    "freq_Hz": 1500.0,
                    "g_rms": g_val,
                    "loss_mod_per_g": 0.02,
                    "phase_mod_rad_per_g": 0.0,
                },
            },
        )
        tag = f"vre_g{int(g_val)}_{'nl' if en_g2 else 'lin'}"
        sub = work / tag
        _run_t2(bin_path, cfg, phys_p, sub)
        rec = read_sim_records(sub / "sim_out.bin")
        mask = rec["t"] >= 0.015
        y = rec["omega_out"][mask] * RAD_S_TO_DEG_H
        w = np.hanning(len(y))
        dc_bias = float(np.sum(w * y) / np.sum(w))
        return {
            "g_rms": g_val,
            "en_tia_poly_nl": en_g2,
            "bias_deg_per_h": dc_bias,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        vre_nl = list(pool.map(_run_vre, [(g, True) for g in g_levels]))
        vre_lin = list(pool.map(_run_vre, [(g, False) for g in g_levels]))

    b0_nl = vre_nl[0]["bias_deg_per_h"]
    b0_lin = vre_lin[0]["bias_deg_per_h"]
    g_sq = np.array([r["g_rms"] ** 2 for r in vre_nl[1:]], dtype=np.float64)
    db_nl = np.array([r["bias_deg_per_h"] - b0_nl for r in vre_nl[1:]], dtype=np.float64)
    db_lin = np.array([r["bias_deg_per_h"] - b0_lin for r in vre_lin[1:]], dtype=np.float64)
    db_g2_only = db_nl - db_lin
    vre_coeff_nl = float(np.dot(g_sq, db_nl) / np.dot(g_sq, g_sq))
    vre_coeff_lin = float(np.dot(g_sq, db_lin) / np.dot(g_sq, g_sq))
    vre_coeff_g2_only = float(np.dot(g_sq, db_g2_only) / np.dot(g_sq, g_sq))
    vre_pred = vre_coeff_g2_only * g_sq
    ss_res = float(np.sum((db_g2_only - vre_pred) ** 2))
    ss_tot = float(np.sum((db_g2_only - np.mean(db_g2_only)) ** 2))
    vre_r2 = 1.0 - ss_res / max(ss_tot, 1.0e-30)

    # 3B. Magnetic Faraday Sensitivity Sweep B in [-5, -2, 0, +2, +5] Gauss (1 G = 1e-4 T)
    b_gauss_list = [-5.0, -2.0, 0.0, 2.0, 5.0]
    verdet = float(base_cfg["magneto_optic"]["verdet_rad_per_Tm"])
    eff_loop_m = 0.02  # 2 cm residual uncompensated radial magnetic loop asymmetry
    faraday_base = deep_merge(
        vre_base,
        {
            "dsp": {"mode": "6state", "alpha_rad": math.pi / 3.0},
            "ablation_flags": {"en_ram": False, "en_tia_poly_nl": False, "en_faraday": True},
            "magneto_optic": {"verdet_rad_per_Tm": verdet, "effective_loop_m": eff_loop_m},
            "simulation": {"duration_s": 0.015, "decimation_tau": 6},
        },
    )

    def _run_faraday(b_g: float) -> dict[str, float]:
        cfg = deep_merge(faraday_base, {"magneto_optic": {"B_ext_T": b_g * 1.0e-4}})
        s = _run_t2(bin_path, cfg, phys_p, work / f"faraday_{b_g:+.1f}G")
        return {
            "B_gauss": b_g,
            "bias_deg_per_h": float(s["mean_omega_out_second_half_rad_per_s"]) * RAD_S_TO_DEG_H,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        faraday_rows = list(pool.map(_run_faraday, b_gauss_list))

    b_arr = np.array([r["B_gauss"] for r in faraday_rows])
    w_arr = np.array([r["bias_deg_per_h"] for r in faraday_rows])
    s_b_meas = float(np.polyfit(b_arr, w_arr, 1)[0])
    s_b_theory = float((verdet * eff_loop_m * 1.0e-4 / float(phys["K_opt_rad_per_rad_s"])) * RAD_S_TO_DEG_H)
    s_b_err_pct = abs(s_b_meas - s_b_theory) / max(abs(s_b_theory), 1.0e-12) * 100.0
    mumetal_dB = compute_mumetal_shield_dB(s_b_meas, max_field_G=1.0, bias_budget_deg_h=0.01)

    result = {
        "scenario_id": "ENG-03",
        "formula_ids": ["EQ-37", "EQ-38"],
        "title": "Vibration Rectification Error (VRE) & Magnetic Faraday Sensitivity / Mu-Metal Sizing",
        "vre": {
            "g_rms_levels": g_levels,
            "nonlinear_delta_bias_deg_per_h": [float(r["bias_deg_per_h"] - b0_nl) for r in vre_nl],
            "linear_delta_bias_deg_per_h": [float(r["bias_deg_per_h"] - b0_lin) for r in vre_lin],
            "g2_rectification_delta_deg_per_h": [0.0] + [float(v) for v in db_g2_only],
            "vre_coeff_nonlinear_deg_h_per_g2": vre_coeff_nl,
            "vre_coeff_linear_deg_h_per_g2": vre_coeff_lin,
            "vre_coeff_g2_only_deg_h_per_g2": vre_coeff_g2_only,
            "quadratic_fit_r2": vre_r2,
        },
        "faraday": {
            "effective_loop_m": eff_loop_m,
            "sweep": faraday_rows,
            "sensitivity_measured_deg_h_per_G": s_b_meas,
            "sensitivity_theory_deg_h_per_G": s_b_theory,
            "theory_err_pct": s_b_err_pct,
            "required_mumetal_shield_dB_for_1G_0p01degh": mumetal_dB,
            "mumetal_required": bool(mumetal_dB > 0.0),
        },
        "pass": bool(
            abs(vre_coeff_g2_only) > 1.0e-3
            and vre_r2 > 0.99
            and s_b_err_pct < 1.0
        ),
    }
    (out_dir / "eng03_vre_faraday.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_eng_fault_bit(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    """ENG-04: 5-Fault Injection & Real-Time FPGA BIT/FDIR Detection & Recovery (EQ-39)."""
    work = out_dir / "eng04_work"
    work.mkdir(parents=True, exist_ok=True)
    phys = solve_tier1_optics(base_cfg)
    phys_p = work / "phys_params.json"
    phys_p.write_text(json.dumps(phys, indent=2), encoding="utf-8")

    inject_t = 0.004
    base_fi = deep_merge(
        base_cfg,
        {
            "dsp": {"mode": "6state", "alpha_rad": math.pi / 3.0, "en_prbs_dither": False, "en_vpi_loop": True},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "bit_fdir": {
                "en_bit": True,
                "en_fdir_recovery": True,
                "sld_drop_ratio": 0.65,
                "fiber_break_ratio": 0.15,
                "vpi_err_threshold": 20000.0,
                "seu_err_threshold": 2000.0,
            },
            "simulation": {
                "duration_s": 0.012,
                "decimation_tau": 1,
                "dump_micro_ms": 0.0,
                "dump_dsp_trace": True,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
            },
        },
    )

    fault_specs = [
        ("sld_drop_50pct", 1, {"inject_time_s": inject_t, "duration_s": 0.0}),
        ("fiber_break", 2, {"inject_time_s": inject_t, "duration_s": 0.0}),
        ("mioc_electrode_open", 3, {"inject_time_s": inject_t, "duration_s": 0.0}),
        ("adc_saturation", 4, {"inject_time_s": inject_t, "duration_s": 0.002}),
        ("dsp_seu_bitflip", 5, {"inject_time_s": inject_t, "duration_s": 0.0, "seu_delta_phi_rad": 0.4}),
    ]

    cases: list[dict[str, Any]] = []
    for ftype, expected_code, fparams in fault_specs:
        cfg = deep_merge(base_fi, {"fault_injection": {"type": ftype, **fparams}})
        sub = work / ftype
        s = _run_t2(bin_path, cfg, phys_p, sub)
        tr = read_dsp_trace(sub / "dsp_trace.bin")
        detected_code = int(s["bit_first_fault_code"])
        tta_us = float(s["bit_time_to_alert_s"]) * 1.0e6
        recovered = bool(s["fdir_recovered"])
        case_ok = (detected_code == expected_code) and (0.0 <= tta_us < 200.0)
        if ftype == "dsp_seu_bitflip":
            case_ok = case_ok and recovered
        cases.append(
            {
                "fault_type": ftype,
                "expected_bit_code": expected_code,
                "detected_bit_code": detected_code,
                "alert_time_ms": float(s["bit_alert_time_s"]) * 1.0e3,
                "time_to_alert_us": tta_us,
                "fdir_recovered": recovered,
                "trace_samples": int(len(tr["t"])),
                "pass": bool(case_ok),
            }
        )

    result = {
        "scenario_id": "ENG-04",
        "formula_id": "EQ-39",
        "title": "Fault Injection & Real-Time FPGA BIT/FDIR Verification (5 Fault Modes)",
        "inject_time_ms": inject_t * 1.0e3,
        "cases": cases,
        "all_detected_and_recovered": all(c["pass"] for c in cases),
        "pass": all(c["pass"] for c in cases),
    }
    (out_dir / "eng04_fault_bit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_eng_mc_yield_cal(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    mc_runs: int = 64,
    workers: int | None = None,
) -> dict[str, Any]:
    """ENG-05: Parallel Monte Carlo Production Yield (EQ-40) & -40..+85 C Virtual Calibration (EQ-41)."""
    work = out_dir / "eng05_work"
    work.mkdir(parents=True, exist_ok=True)
    max_w = workers if workers is not None else min(8, max(1, os.cpu_count() or 1))
    rng = np.random.default_rng(int(base_cfg["meta"]["seed"]) + 505)

    # 5A. Monte Carlo Production Yield across mc_runs random component draws
    # Tolerances: +/-5% V_pi, +/-10% TIA f_gbw, log-normal h-parameter, +/-20% PCB crosstalk, eps_vpi spread
    mc_draws: list[dict[str, float]] = []
    for i in range(mc_runs):
        mc_draws.append(
            {
                "idx": i,
                "seed": int(base_cfg["meta"]["seed"]) + 10_000 + i * 17,
                "v_pi_scale": float(np.clip(rng.normal(1.0, 0.025), 0.90, 1.10)),
                "gbw_scale": float(np.clip(rng.normal(1.0, 0.05), 0.80, 1.20)),
                "h_scale": float(np.exp(rng.normal(0.0, 0.25))),
                "xtalk_scale": float(np.clip(rng.normal(1.0, 0.15), 0.50, 1.60)),
                "eps_vpi": float(np.clip(rng.normal(0.0, 0.02), -0.06, 0.06)),
            }
        )

    def _run_mc_unit(draw: dict[str, float]) -> dict[str, Any]:
        idx = int(draw["idx"])
        rf = float(base_cfg["analog_frontend"]["R_f_ohm"])
        ctot = float(base_cfg["analog_frontend"]["C_tot_F"])
        gbw = float(base_cfg["analog_frontend"]["f_gbw_Hz"]) * draw["gbw_scale"]
        cf_opt = compute_tia_dynamics(rf, ctot, 0.0, gbw)["C_f_opt_F"]
        cfg = deep_merge(
            base_cfg,
            {
                "meta": {"seed": int(draw["seed"])},
                "optics": {"h_param_inv_m": float(base_cfg["optics"]["h_param_inv_m"]) * draw["h_scale"]},
                "mioc": {
                    "V_pi_0_V": float(base_cfg["mioc"]["V_pi_0_V"]) * draw["v_pi_scale"],
                    "eps_vpi": draw["eps_vpi"],
                },
                "analog_frontend": {
                    "f_gbw_Hz": gbw,
                    "C_f_F": cf_opt,
                    "k_xtalk_A_per_V": float(base_cfg["analog_frontend"]["k_xtalk_A_per_V"]) * draw["xtalk_scale"],
                },
                "dsp": {"mode": "6state", "alpha_rad": math.pi / 3.0, "en_prbs_dither": False},
                "noise": {"en_white_noise": True, "en_pink_noise": False},
                "simulation": {
                    "duration_s": 0.02,
                    "decimation_tau": 6,
                    "dump_micro_ms": 0.0,
                    "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
                },
            },
        )
        sub = work / f"mc_{idx:04d}"
        sub.mkdir(parents=True, exist_ok=True)
        phys_u = solve_tier1_optics(cfg)
        phys_u_p = sub / "phys.json"
        phys_u_p.write_text(json.dumps(phys_u), encoding="utf-8")
        s = _run_t2(bin_path, cfg, phys_u_p, sub)
        bias_deg_h = float(s["mean_omega_out_second_half_rad_per_s"]) * RAD_S_TO_DEG_H
        eps_res = abs(float(s["final_eps_vpi_eff"]))
        ts_ns = float(s["tia_ts_0p1pct_s"]) * 1.0e9
        unit_pass = bool(abs(bias_deg_h) <= 1.0 and eps_res <= 5.0e-3 and ts_ns <= 250.0)
        return {
            "unit_id": idx,
            "bias_deg_per_h": bias_deg_h,
            "eps_vpi_eff": eps_res,
            "tia_ts_ns": ts_ns,
            "pass": unit_pass,
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        mc_results = list(pool.map(_run_mc_unit, mc_draws))

    n_pass = sum(1 for r in mc_results if r["pass"])
    yield_frac = n_pass / len(mc_results)
    ci_lo, ci_hi = compute_wilson_ci_95(n_pass, len(mc_results))
    bias_arr = np.array([r["bias_deg_per_h"] for r in mc_results], dtype=np.float64)
    cpk_bias = compute_cpk(bias_arr, lsl=-1.0, usl=1.0)

    # 5B. Virtual Thermal Calibration Dataset (-40 C to +85 C across heating/static/cooling ramps)
    temps_C = [-40.0, -20.0, 0.0, 25.0, 50.0, 70.0, 85.0]
    ramps_K_s = [-0.5, 0.0, 0.5]
    alpha_lambda_per_K = 2.5e-5  # SLD center wavelength thermal coefficient (~38 pm/K @ 1550 nm)
    alpha_vpi_per_K = 4.0e-4     # LiNbO3 MIOC V_pi thermal coefficient
    cal_points = [(t_c, r_k) for t_c in temps_C for r_k in ramps_K_s]

    def _run_cal_point(pt: tuple[float, float]) -> dict[str, float]:
        t_c, dT_dt = pt
        dT = t_c - 25.0
        lam_T = float(base_cfg["optics"]["lambda_bar_m"]) * (1.0 + alpha_lambda_per_K * dT)
        vpi_T = float(base_cfg["mioc"]["V_pi_0_V"]) * (1.0 + alpha_vpi_per_K * dT)
        # Thermal polarization drift + Shupe transient at operating temperature
        phi_pol_T = 2.0e-8 * dT + 2.5e-10 * (dT**2)
        cfg_t = deep_merge(
            base_cfg,
            {
                "optics": {"lambda_bar_m": lam_T},
                "thermal": {
                    "boundary_ramp_K_per_s": dT_dt,
                    "boundary_asymmetry_K_per_s": 0.25 * dT_dt,
                    "duration_s": 20.0,
                    "dt_s": 1.0,
                },
                "mioc": {"V_pi_0_V": vpi_T, "eps_vpi": alpha_vpi_per_K * dT},
                "dsp": {"mode": "6state", "alpha_rad": math.pi / 3.0, "en_prbs_dither": False},
                "noise": {"en_white_noise": False, "en_pink_noise": False},
                "ablation_flags": {
                    "en_pol_error": True,
                    "en_kerr": False,
                    "en_shupe": False,
                    "en_faraday": False,
                    "en_mioc_vpi_err": True,
                    "en_ram": False,
                    "en_xtalk": False,
                    "en_ltf_transient": False,
                    "en_tia_poly_nl": False,
                    "en_quantization": False,
                },
                "simulation": {
                    "duration_s": 0.012,
                    "decimation_tau": 6,
                    "dump_micro_ms": 0.0,
                    "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
                },
            },
        )
        sub = work / f"cal_T{int(t_c)}_R{int(round(dT_dt * 10))}"
        sub.mkdir(parents=True, exist_ok=True)
        phys_t = solve_tier1_optics(cfg_t)
        _, phi_sh_arr, _ = solve_tier1_shupe(cfg_t)
        # Peak Shupe phase from Tier 1 solver coupled cleanly into static thermal operating point
        shupe_phi = float(phi_sh_arr[len(phi_sh_arr) // 2])
        phys_t["phi_pol_rad"] = phi_pol_T + shupe_phi
        phys_t["delta_phi_kerr_rad"] = 0.0
        phys_t_p = sub / "phys.json"
        phys_t_p.write_text(json.dumps(phys_t), encoding="utf-8")
        s = _run_t2(bin_path, cfg_t, phys_t_p, sub)
        bias_deg_h = float(s["mean_omega_out_second_half_rad_per_s"]) * RAD_S_TO_DEG_H
        sf_err_ppm = (float(base_cfg["optics"]["lambda_bar_m"]) / lam_T - 1.0) * 1.0e6
        return {
            "T_C": t_c,
            "dT_dt_K_per_s": dT_dt,
            "omega_out_deg_per_h": bias_deg_h,
            "sf_err_ppm": sf_err_ppm,
            "final_g_dac": float(s["final_g_dac"]),
            "final_eps_vpi_eff": float(s["final_eps_vpi_eff"]),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        cal_rows = list(pool.map(_run_cal_point, cal_points))

    # Write CSV Virtual Calibration Dataset for downstream algorithm / EKF engineers
    csv_path = out_dir / "virtual_calibration_dataset.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(cal_rows[0].keys()))
        writer.writeheader()
        writer.writerows(cal_rows)

    T_arr = np.array([r["T_C"] for r in cal_rows], dtype=np.float64)
    dT_arr = np.array([r["dT_dt_K_per_s"] for r in cal_rows], dtype=np.float64)
    b_arr = np.array([r["omega_out_deg_per_h"] for r in cal_rows], dtype=np.float64)
    cal_eval = fit_thermal_polynomial_and_ekf(T_arr, dT_arr, b_arr)

    result = {
        "scenario_id": "ENG-05",
        "formula_ids": ["EQ-40", "EQ-41"],
        "title": "Monte Carlo Production Yield (C_pk) & -40..+85 C Virtual Thermal Calibration",
        "monte_carlo": {
            "n_runs": len(mc_results),
            "n_pass": n_pass,
            "yield_pct": yield_frac * 100.0,
            "wilson_ci95_pct": [ci_lo * 100.0, ci_hi * 100.0],
            "bias_mean_deg_per_h": float(np.mean(bias_arr)),
            "bias_std_deg_per_h": float(np.std(bias_arr, ddof=1)) if len(bias_arr) > 1 else 0.0,
            "cpk_bias_1degh": cpk_bias,
            "bias_samples_deg_per_h": [float(v) for v in bias_arr],
        },
        "virtual_calibration": {
            "dataset_csv": str(csv_path.name),
            "n_points": len(cal_rows),
            "temp_range_C": [min(temps_C), max(temps_C)],
            "rows": cal_rows,
            **cal_eval,
        },
        "pass": bool(
            yield_frac > 0.5
            and cal_eval["poly_reduction_pct"] >= 90.0
            and cal_eval["ekf_reduction_pct"] >= 50.0
        ),
    }
    (out_dir / "eng05_mc_yield_cal.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_all_engineering_scenarios(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    mc_runs: int = 64,
    workers: int | None = None,
) -> dict[str, Any]:
    """Execute all 5 System Engineering & Production scenarios (ENG-01 .. ENG-05) into out_dir."""
    out_dir.mkdir(parents=True, exist_ok=True)
    eng01 = run_eng_hw_sizing(bin_path, base_cfg, out_dir, workers=workers)
    eng02 = run_eng_imu_3axis(bin_path, base_cfg, out_dir)
    eng03 = run_eng_vre_faraday(bin_path, base_cfg, out_dir, workers=workers)
    eng04 = run_eng_fault_bit(bin_path, base_cfg, out_dir)
    eng05 = run_eng_mc_yield_cal(bin_path, base_cfg, out_dir, mc_runs=mc_runs, workers=workers)
    summary = {
        "spec_id": "IFOG-SIM-SPEC-005",
        "scenarios": {
            "ENG-01": eng01,
            "ENG-02": eng02,
            "ENG-03": eng03,
            "ENG-04": eng04,
            "ENG-05": eng05,
        },
        "all_passed": all(s["pass"] for s in (eng01, eng02, eng03, eng04, eng05)),
    }
    (out_dir / "eng_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
