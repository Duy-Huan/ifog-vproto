"""Official IFOG-SIM-SPEC-007 High-Fidelity Predictive Physics & Inverse Calibration Scenarios.

Implements two real end-to-end verification scenarios combining Tier 1 v2 LUT solvers,
compiled Tier 2 SystemC-AMS C++ binary (``ifog_sim``), and Tier 3 ``InverseCalibrator``:

  1. ``PHY-01`` (``spec007_physics``):
     - Discrete quadrupole vs octupole coil winding map & elasto-optic stress drift (EQ-45, EQ-46)
     - Dynamic Sagnac scale factor K_opt(t), V_eff(t), phi_pol(t), V_pi(t) in LUT v2 (EQ-47..EQ-49)
     - Real Tier 2 ``ifog_sim`` micro-waveform comparison: MIOC electro-acoustic step dynamics
       (EQ-50) & capacitive C_xtalk * dV/dt spike vs C_xtalk = 0 legacy reduction (EQ-51)
     - Coherent Rayleigh + facet back-reflection BI & Tier 3 anti-double-counting stitch (EQ-52)

  2. ``CAL-01`` (``spec007_calibration``):
     - Synthetic hardware-prototype benchmark with injected hidden parasitic parameters
     - Proves uncalibrated datasheet baseline exceeds > 40% error across AVAR, Deadband, and Thermal Bias
     - Runs 3-stage bounded ``InverseCalibrator`` (EQ-53) reducing prediction error to < 5% across
       all three domains + real Tier 2 closed-loop verification pre- vs post-calibration.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from tier1_offline.config_loader import (
    RAD_S_TO_DEG_H,
    compute_backscatter_sigma_rad,
    deep_merge,
    load_config,
)
from tier1_offline.jones_spectral import solve_tier1_optics
from tier1_offline.shupe_thermal import (
    build_winding_map,
    read_shupe_lut_v2,
    solve_tier1_shupe_v2,
    write_shupe_lut_v2,
)
from tier3_analysis.binary_io import read_micro_records, read_sim_records
from tier3_analysis.dual_regime_avar import (
    DEG_H_TO_RAD_S,
    DualRegimeStitcher,
    overlapping_avar,
)
from tier3_analysis.inverse_calibration import (
    InverseCalibrator,
    forward_avar_psd,
    forward_slow_rate_ramp,
    forward_thermal_ramp,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC007_CFG = REPO_ROOT / "configs" / "baseline_1km_spec007.json"


def _run_tier2_sim(
    bin_path: Path,
    cfg: dict[str, Any],
    work_dir: Path,
    lut_channels: dict[str, np.ndarray] | None = None,
) -> tuple[dict[str, Any], Path]:
    """Run real Tier 1 + compiled Tier 2 C++ SystemC-AMS binary in work_dir."""
    work_dir.mkdir(parents=True, exist_ok=True)
    phys = solve_tier1_optics(cfg)
    phys_path = work_dir / "phys_params.json"
    phys_path.write_text(json.dumps(phys, indent=2), encoding="utf-8")

    cfg_path = work_dir / "cfg.json"
    cfg_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

    cmd = [
        str(bin_path),
        "--phys",
        str(phys_path),
        "--cfg",
        str(cfg_path),
        "--out",
        str(work_dir),
    ]
    if lut_channels is not None:
        shupe_path = work_dir / "shupe_lut.bin"
        write_shupe_lut_v2(
            shupe_path,
            lut_channels["t_s"],
            lut_channels["delta_phi_shupe_rad"],
            lut_channels["delta_phi_stress_rad"],
            lut_channels["visibility_V_t"],
            lut_channels["phi_pol_rad_t"],
            lut_channels["v_pi_V_t"],
            lut_channels["k_opt_scale_rel_t"],
        )
        cmd.extend(["--shupe", str(shupe_path)])

    subprocess.run(cmd, check=True)
    summary = json.loads((work_dir / "sim_summary.json").read_text(encoding="utf-8"))
    return summary, work_dir


def run_spec007_physics(
    bin_path: Path | str,
    cfg: dict[str, Any] | None = None,
    out_dir: Path | str = "data/spec007_physics",
) -> dict[str, Any]:
    """Execute PHY-01: real Tier 1 v2 LUT + Tier 2 MIOC/crosstalk/back-reflection verification."""
    bpath = Path(bin_path)
    odir = Path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)
    base_cfg = load_config(DEFAULT_SPEC007_CFG) if cfg is None else cfg
    if "spec007_physics" not in base_cfg:
        base_cfg = deep_merge(load_config(DEFAULT_SPEC007_CFG), {"meta": base_cfg["meta"]})

    # 1. Compare Quadrupole vs Octupole discrete winding + elasto-optic stress + 6-channel v2 LUT
    th_ov = {"thermal": {"duration_s": 1200.0, "dt_s": 10.0, "boundary_ramp_K_per_s": 5.0e-3, "boundary_asymmetry_K_per_s": 1.0e-3}}
    cfg_quad = deep_merge(base_cfg, {**th_ov, "spec007_physics": {"winding_pattern": "quadrupole"}})
    cfg_oct = deep_merge(base_cfg, {**th_ov, "spec007_physics": {"winding_pattern": "octupole"}})
    phys_quad = solve_tier1_optics(cfg_quad)
    ch_quad, sum_quad = solve_tier1_shupe_v2(cfg_quad, phys_params=phys_quad)
    ch_oct, sum_oct = solve_tier1_shupe_v2(cfg_oct, phys_params=phys_quad)

    w_quad = build_winding_map(
        L_m=float(cfg_quad["optics"]["L_m"]),
        D_m=float(cfg_quad["optics"]["D_m"]),
        coil_thickness_m=float(cfg_quad["thermal"]["coil_thickness_m"]),
        n_turns=256,
        n_layers=16,
        winding_pattern="quadrupole",
        flange_offset_m=float(cfg_quad["spec007_physics"]["flange_offset_m"]),
        delta_z_quad_m=float(cfg_quad["thermal"]["delta_z_quad_m"]),
    )
    w_oct = build_winding_map(
        L_m=float(cfg_oct["optics"]["L_m"]),
        D_m=float(cfg_oct["optics"]["D_m"]),
        coil_thickness_m=float(cfg_oct["thermal"]["coil_thickness_m"]),
        n_turns=256,
        n_layers=16,
        winding_pattern="octupole",
        flange_offset_m=float(cfg_oct["spec007_physics"]["flange_offset_m"]),
        delta_z_quad_m=float(cfg_oct["thermal"]["delta_z_quad_m"]),
    )

    # Verify v2 binary roundtrip accuracy
    lut_path = odir / "shupe_lut_v2_quad.bin"
    write_shupe_lut_v2(
        lut_path,
        ch_quad["t_s"],
        ch_quad["delta_phi_shupe_rad"],
        ch_quad["delta_phi_stress_rad"],
        ch_quad["visibility_V_t"],
        ch_quad["phi_pol_rad_t"],
        ch_quad["v_pi_V_t"],
        ch_quad["k_opt_scale_rel_t"],
    )
    lut_rt = read_shupe_lut_v2(lut_path)
    lut_roundtrip_err = float(
        np.max(np.abs(lut_rt["delta_phi_stress_rad"] - ch_quad["delta_phi_stress_rad"]))
    )

    # 2. Real Tier 2 micro-waveform comparison: SPEC-007 (MIOC acoustic + C_xtalk=5pF) vs C_xtalk=0 ideal MIOC
    sim_common = {
        "noise": {"en_white_noise": False, "en_pink_noise": False},
        "simulation": {
            "duration_s": 0.012,
            "decimation_tau": 1,
            "dump_micro_ms": 0.12,
            "stimulus": {"type": "constant", "omega_rad_per_s": 0.05},
        },
    }
    cfg_sp7_on = deep_merge(
        cfg_quad,
        {
            **sim_common,
            "spec007_physics": {
                "en_spec007_physics": True,
                "C_xtalk_F": 5.0e-12,
                "G_xtalk_S": 1.5e-8,
                "mioc_f_elec_Hz": 12.0e6,
                "mioc_f_acoustic_Hz": 3.5e6,
                "mioc_zeta_acoustic": 0.08,
                "mioc_g_acoustic": 0.06,
                "R_facet_dB": -55.0,
                "sigma_theta_env_rad": 0.25,
            },
        },
    )
    cfg_sp7_nocap = deep_merge(
        cfg_sp7_on,
        {
            "analog_frontend": {"C_xtalk_F": 0.0, "k_xtalk_A_per_V": 1.5e-8},
            "spec007_physics": {
                "C_xtalk_F": 0.0,
                "mioc_f_elec_Hz": 0.0,
                "mioc_f_acoustic_Hz": 0.0,
                "mioc_g_acoustic": 0.0,
            },
        },
    )

    _, dir_on = _run_tier2_sim(bpath, cfg_sp7_on, odir / "sim_spec007_on", lut_channels=ch_quad)
    _, dir_off = _run_tier2_sim(bpath, cfg_sp7_nocap, odir / "sim_spec007_nocap", lut_channels=ch_quad)

    micro_on = read_micro_records(dir_on / "micro_waveforms.bin")
    micro_off = read_micro_records(dir_off / "micro_waveforms.bin")
    n_cmp = min(len(micro_on["t"]), len(micro_off["t"]))
    v_tia_diff_rms = float(
        np.sqrt(np.mean((micro_on["v_tia"][:n_cmp] - micro_off["v_tia"][:n_cmp]) ** 2))
    )
    p_det_diff_rms = float(
        np.sqrt(np.mean((micro_on["p_det"][:n_cmp] - micro_off["p_det"][:n_cmp]) ** 2))
    )

    # 3. Verify Rayleigh/facet back-reflection BI & Tier 3 anti-double-counting stitch (EQ-52)
    sim_on = read_sim_records(dir_on / "sim_out.bin")
    dt_sim = float(np.median(np.diff(sim_on["t"])))
    taus_f, adev_f = overlapping_avar(sim_on["omega_out"][50:], dt_sim, n_points=16)
    sigma_back = compute_backscatter_sigma_rad(
        R_facet_dB=-55.0,
        alpha_R_per_m=float(cfg_sp7_on["spec007_physics"]["alpha_R_per_m"]),
        S_capture=float(cfg_sp7_on["spec007_physics"]["S_capture"]),
        delta_nu_eff_Hz=float(phys_quad["delta_nu_eff_Hz"]),
    )
    b_total_si = 0.005 * DEG_H_TO_RAD_S
    b_t2_si = 0.003 * DEG_H_TO_RAD_S
    b_t3_mech_si = DualRegimeStitcher.residual_mechanical_bi(b_total_si, b_t2_si)
    bi_quadrature_err = abs(math.hypot(b_t2_si, b_t3_mech_si) - b_total_si)

    # Save curves for viz/plot_spec007_calibration.py
    np.savez(
        odir / "spec007_physics_curves.npz",
        z_turns=w_quad["z_m"],
        dz_quad=w_quad["delta_z_quad_m"],
        dz_oct=w_oct["delta_z_quad_m"],
        t_lut_s=ch_quad["t_s"],
        phi_shupe_quad=ch_quad["delta_phi_shupe_rad"],
        phi_stress_quad=ch_quad["delta_phi_stress_rad"],
        phi_tot_oct=ch_oct["delta_phi_shupe_rad"] + ch_oct["delta_phi_stress_rad"],
        k_opt_rel_ppm=(ch_quad["k_opt_scale_rel_t"] - 1.0) * 1.0e6,
        v_pi_t_V=ch_quad["v_pi_V_t"],
        t_micro_us=micro_on["t"][:n_cmp] * 1.0e6,
        v_tia_on=micro_on["v_tia"][:n_cmp],
        v_tia_nocap=micro_off["v_tia"][:n_cmp],
        p_det_on_uW=micro_on["p_det"][:n_cmp] * 1.0e6,
        p_det_nocap_uW=micro_off["p_det"][:n_cmp] * 1.0e6,
        taus_fast=taus_f,
        adev_fast_deg_h=adev_f * RAD_S_TO_DEG_H,
    )

    quad_peak_deg_h = float(sum_quad["max_abs_omega_shupe_deg_per_h"])
    oct_peak_deg_h = float(sum_oct["max_abs_omega_shupe_deg_per_h"])
    oct_reduction_pct = (
        100.0 * (1.0 - oct_peak_deg_h / max(quad_peak_deg_h, 1.0e-12))
    )

    passed = bool(
        lut_roundtrip_err < 1.0e-15
        and oct_peak_deg_h < quad_peak_deg_h
        and v_tia_diff_rms > 1.0e-5
        and p_det_diff_rms > 1.0e-9
        and sigma_back > 1.0e-4
        and bi_quadrature_err < 1.0e-15
    )

    summary = {
        "scenario_id": "PHY-01",
        "spec_id": "IFOG-SIM-SPEC-007",
        "lut_version": 2,
        "lut_roundtrip_err_rad": lut_roundtrip_err,
        "quadrupole_peak_therm_deg_per_h": quad_peak_deg_h,
        "octupole_peak_therm_deg_per_h": oct_peak_deg_h,
        "octupole_drift_reduction_pct": float(oct_reduction_pct),
        "k_opt_thermal_drift_ppm": float(sum_quad["k_opt_rel_drift_ppm"]),
        "v_pi_final_V": float(sum_quad["v_pi_final_V"]),
        "v_tia_cap_spike_diff_rms_V": v_tia_diff_rms,
        "p_det_mioc_acoustic_diff_rms_W": p_det_diff_rms,
        "sigma_phi_back_rad": float(sigma_back),
        "b_t3_mech_deg_per_h": float(b_t3_mech_si * RAD_S_TO_DEG_H),
        "bi_quadrature_conservation_err_rad_s": float(bi_quadrature_err),
        "passed": passed,
    }
    (odir / "spec007_physics_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def run_spec007_calibration(
    bin_path: Path | str,
    cfg: dict[str, Any] | None = None,
    out_dir: Path | str = "data/spec007_calibration",
) -> dict[str, Any]:
    """Execute CAL-01: synthetic closed-loop inverse calibration benchmark (>40% -> <5% error)."""
    bpath = Path(bin_path)
    odir = Path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)
    base_cfg = load_config(DEFAULT_SPEC007_CFG) if cfg is None else cfg
    if "spec007_physics" not in base_cfg:
        base_cfg = deep_merge(load_config(DEFAULT_SPEC007_CFG), {"meta": base_cfg["meta"]})

    # Ground-truth hidden physical prototype parameters (deviating significantly from datasheet)
    true_params = {
        "c_pink_coeff": 4.20,
        "R_facet_dB": -52.0,
        "eta_pd_scale": 0.55,
        "C_xtalk_F": 7.8e-12,
        "G_xtalk_S": 6.2e-8,
        "dac_asym_lsb": 1.35,
        "diffusivity_m2_per_s": 5.2e-7,
        "delta_z_quad_m": 0.0046,
        "alpha_vpi_ppm_K": 620.0,
        "alpha_bobbin_ppm_K": 18.5,
    }
    # Uncalibrated textbook/datasheet initial parameters (>40% error across all 3 domains)
    uncal_params = {
        "c_pink_coeff": 1.00,
        "R_facet_dB": -72.0,
        "eta_pd_scale": 1.00,
        "C_xtalk_F": 2.0e-12,
        "G_xtalk_S": 1.5e-8,
        "dac_asym_lsb": 0.0,
        "diffusivity_m2_per_s": 9.5e-7,
        "delta_z_quad_m": 0.0018,
        "alpha_vpi_ppm_K": 250.0,
        "alpha_bobbin_ppm_K": 8.0,
    }

    rng = np.random.default_rng(7007)
    taus = np.geomspace(1.0e-2, 1.0e4, 28)
    freqs = np.geomspace(1.0e-3, 1.0e2, 28)
    omega_in = np.linspace(-2.5, 2.5, 61)
    t_th = np.linspace(0.0, 900.0, 31)

    cal = InverseCalibrator()

    # Synthesize realistic noisy hardware measurements (~0.8% measurement noise)
    av_true, psd_true = forward_avar_psd(
        taus, freqs, true_params["c_pink_coeff"], true_params["R_facet_dB"],
        true_params["eta_pd_scale"], cal.avar_ctx,
    )
    av_meas = av_true * (1.0 + 0.008 * rng.standard_normal(len(taus)))
    psd_meas = psd_true * (1.0 + 0.010 * rng.standard_normal(len(freqs)))

    db_true = forward_slow_rate_ramp(
        omega_in, true_params["C_xtalk_F"], true_params["G_xtalk_S"],
        true_params["dac_asym_lsb"], cal.db_ctx,
    )
    db_meas = db_true["omega_out_deg_h"] + 0.004 * rng.standard_normal(len(omega_in))

    th_true = forward_thermal_ramp(
        t_th, true_params["diffusivity_m2_per_s"], true_params["delta_z_quad_m"],
        true_params["alpha_vpi_ppm_K"], true_params["alpha_bobbin_ppm_K"], cal.th_ctx,
    )
    bias_meas = th_true["omega_bias_deg_h"] + 0.0004 * rng.standard_normal(len(t_th))
    sf_meas = th_true["sf_err_ppm"] + 0.25 * rng.standard_normal(len(t_th))

    dataset = {
        "taus_s": taus,
        "avar_meas_deg_h": av_meas,
        "freqs_Hz": freqs,
        "psd_meas_deg_h2_Hz": psd_meas,
        "omega_in_deg_h": omega_in,
        "omega_out_meas_deg_h": db_meas,
        "t_thermal_s": t_th,
        "omega_bias_meas_deg_h": bias_meas,
        "sf_err_meas_ppm": sf_meas,
    }

    cal_res = cal.calibrate_all(dataset, uncal_params, out_path=odir / "calibrated_params.json")
    cal_p = cal_res["calibrated_params"]

    # Compute before/after curves for diagnostic plotting
    av_pre, _ = forward_avar_psd(
        taus, freqs, uncal_params["c_pink_coeff"], uncal_params["R_facet_dB"],
        uncal_params["eta_pd_scale"], cal.avar_ctx,
    )
    av_post, _ = forward_avar_psd(
        taus, freqs, cal_p["c_pink_coeff"], cal_p["R_facet_dB"],
        cal_p["eta_pd_scale"], cal.avar_ctx,
    )
    db_pre = forward_slow_rate_ramp(
        omega_in, uncal_params["C_xtalk_F"], uncal_params["G_xtalk_S"],
        uncal_params["dac_asym_lsb"], cal.db_ctx,
    )["omega_out_deg_h"]
    db_post = forward_slow_rate_ramp(
        omega_in, cal_p["C_xtalk_F"], cal_p["G_xtalk_S"],
        cal_p["dac_asym_lsb"], cal.db_ctx,
    )["omega_out_deg_h"]
    th_pre = forward_thermal_ramp(
        t_th, uncal_params["diffusivity_m2_per_s"], uncal_params["delta_z_quad_m"],
        uncal_params["alpha_vpi_ppm_K"], uncal_params["alpha_bobbin_ppm_K"], cal.th_ctx,
    )
    th_post = forward_thermal_ramp(
        t_th, cal_p["diffusivity_m2_per_s"], cal_p["delta_z_quad_m"],
        cal_p["alpha_vpi_ppm_K"], cal_p["alpha_bobbin_ppm_K"], cal.th_ctx,
    )

    # Real compiled Tier 2 closed-loop verification with calibrated parameters vs truth
    def _build_t2_cfg(p: dict[str, float]) -> dict[str, Any]:
        return deep_merge(
            base_cfg,
            {
                "noise": {"en_white_noise": False, "en_pink_noise": False},
                "dsp": {"mode": "4state", "alpha_rad": math.pi / 4.0, "en_prbs_dither": False},
                "analog_frontend": {"C_xtalk_F": p["C_xtalk_F"], "k_xtalk_A_per_V": p["G_xtalk_S"]},
                "spec007_physics": {
                    "en_spec007_physics": True,
                    "C_xtalk_F": p["C_xtalk_F"],
                    "G_xtalk_S": p["G_xtalk_S"],
                    "R_facet_dB": p["R_facet_dB"],
                    "alpha_vpi_ppm_K": p["alpha_vpi_ppm_K"],
                    "alpha_bobbin_ppm_K": p["alpha_bobbin_ppm_K"],
                },
                "simulation": {
                    "duration_s": 0.01,
                    "decimation_tau": 4,
                    "dump_micro_ms": 0.0,
                    "stimulus": {"type": "constant", "omega_rad_per_s": 0.02},
                },
            },
        )

    s_true, _ = _run_tier2_sim(bpath, _build_t2_cfg(true_params), odir / "t2_truth")
    s_cal, _ = _run_tier2_sim(bpath, _build_t2_cfg(cal_p), odir / "t2_calibrated")
    t2_rate_err_pct = (
        100.0
        * abs(
            s_cal["mean_omega_out_second_half_rad_per_s"]
            - s_true["mean_omega_out_second_half_rad_per_s"]
        )
        / max(abs(s_true["mean_omega_out_second_half_rad_per_s"]), 1.0e-12)
    )

    # Compute parameter recovery accuracy vs ground truth
    param_err_pct: dict[str, float] = {}
    for k, tv in true_params.items():
        denom = abs(tv) if abs(tv) > 1.0e-15 else 1.0
        param_err_pct[k] = float(100.0 * abs(cal_p[k] - tv) / denom)

    np.savez(
        odir / "spec007_calibration_curves.npz",
        taus_s=taus,
        avar_meas_deg_h=av_meas,
        avar_pre_deg_h=av_pre,
        avar_post_deg_h=av_post,
        omega_in_deg_h=omega_in,
        db_meas_deg_h=db_meas,
        db_pre_deg_h=db_pre,
        db_post_deg_h=db_post,
        t_thermal_s=t_th,
        bias_meas_deg_h=bias_meas,
        bias_pre_deg_h=th_pre["omega_bias_deg_h"],
        bias_post_deg_h=th_post["omega_bias_deg_h"],
        sf_meas_ppm=sf_meas,
        sf_pre_ppm=th_pre["sf_err_ppm"],
        sf_post_ppm=th_post["sf_err_ppm"],
    )

    eb = cal_res["error_before_pct"]
    ea = cal_res["error_after_pct"]
    max_param_err_pct = float(max(param_err_pct.values()))
    passed = bool(
        eb["avar_nrmse_pct"] > 40.0
        and eb["deadband_nrmse_pct"] > 40.0
        and eb["thermal_bias_nrmse_pct"] > 40.0
        and ea["avar_nrmse_pct"] < 5.0
        and ea["deadband_nrmse_pct"] < 5.0
        and ea["thermal_bias_nrmse_pct"] < 5.0
        and ea["thermal_sf_nrmse_pct"] < 5.0
        and max_param_err_pct < 5.0
        and t2_rate_err_pct < 5.0
    )

    summary = {
        "scenario_id": "CAL-01",
        "spec_id": "IFOG-SIM-SPEC-007",
        "true_params": true_params,
        "uncalibrated_params": uncal_params,
        "calibrated_params": cal_p,
        "ci95": cal_res["ci95"],
        "param_recovery_err_pct": param_err_pct,
        "max_param_recovery_err_pct": max_param_err_pct,
        "error_before_pct": eb,
        "error_after_pct": ea,
        "cost_before": cal_res["cost_before"],
        "cost_after": cal_res["cost_after"],
        "tier2_closed_loop_rate_err_pct": float(t2_rate_err_pct),
        "passed": passed,
    }
    (odir / "spec007_calibration_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def run_all_spec007_scenarios(
    bin_path: Path | str,
    cfg: dict[str, Any] | None = None,
    out_dir: Path | str = "data/spec007_all",
) -> dict[str, Any]:
    """Run both official SPEC-007 scenarios (PHY-01 + CAL-01) and persist unified summary."""
    odir = Path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)
    phy = run_spec007_physics(bin_path, cfg, odir / "phy01_spec007_physics")
    cal = run_spec007_calibration(bin_path, cfg, odir / "cal01_spec007_calibration")
    summary = {
        "spec_id": "IFOG-SIM-SPEC-007",
        "phy01_physics": phy,
        "cal01_calibration": cal,
        "all_passed": bool(phy["passed"] and cal["passed"]),
    }
    (odir / "spec007_all_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary
