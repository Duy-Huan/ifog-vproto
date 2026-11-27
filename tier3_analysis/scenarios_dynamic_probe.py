"""IFOG-SIM-SPEC-005 Group C: Dynamic Response, Output PSD & Internal Electro-Optic Probe Scenarios.

Implements 4 dedicated closed-loop characterization scenarios running genuine compiled
Tier 2 C++ SystemC-AMS simulations (zero mocks, zero smoke-test shortcuts):
  - DYN-01 (dyn_step_response): Closed-loop step response (0->10 deg/s, 0->100 deg/s,
      4-State vs Official 6-State, and K_tot_1 gain sweep) with Sagnac vs feedback phase traces.
  - DYN-02 (dyn_freq_response): Full closed-loop Bode Magnitude [dB], unwrapped Phase [deg],
      and Group Delay [us] (20 Hz..10 kHz, 15 log-spaced points) comparing 4-State vs 6-State
      against analytical Z-domain transfer function.
  - DYN-03 (dyn_output_psd): Stationary broadband output angular-rate PSD [(deg/h)^2/Hz],
      ASD [deg/h/rt-Hz], analytical EQ-15/EQ-19 ARW floor, 1/f suppression (6-State vs 4-State),
      and cumulative integrated RMS rate noise.
  - DYN-04 (dyn_sine_electro_optic): Sinusoidal angular-rate excitation (50 deg/s @ 250 Hz)
      exposing the complete internal electro-optic signal chain: Omega_in(t), Sagnac phase
      Delta_phi_S(t), closed-loop feedback phase Delta_phi_fb(t), residual phase error,
      MIOC serrodyne feedback voltage V_fb_MIOC(t) & total V_MIOC(t), Photodiode optical power
      P_PD(t) & photocurrent I_PD(t), TIA output V_TIA(t), ADC blanking zoom, and Omega_out(t)
      harmonic purity (THD / SFDR).
"""

from __future__ import annotations

import concurrent.futures
import json
import math
import os
from pathlib import Path
from typing import Any

import numpy as np

from tier1_offline.config_loader import (
    DEG_S_TO_RAD_S,
    K_BOLTZMANN,
    Q_ELECTRON,
    RAD_S_TO_DEG_H,
    RAD_S_TO_DEG_S,
    deep_merge,
)
from tier3_analysis.binary_io import (
    compute_welch_psd,
    read_dsp_trace,
    read_micro_records,
    read_sim_records,
)
from tier3_analysis.scenarios_time_domain import (
    _ensure_phys,
    _run_tier2,
    compute_theoretical_bw_3db_hz,
)


def compute_closed_loop_frf_theory(
    freqs_hz: np.ndarray,
    K_tot_1: float,
    frame_period_s: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Analytical Z-domain closed-loop FRF H(f) = [K / (1 - (1-K)*z_f^-1)] * exp(-j*pi*f*T_f).

    Returns (mag_dB, phase_deg, group_delay_us) matching DigitalDSP_SC frame integration
    with exact half-frame averaging delay (DC group delay = ((1 - K)/K + 0.5) * T_f).
    """
    f = np.asarray(freqs_hz, dtype=np.float64)
    z_inv = np.exp(-1j * 2.0 * np.pi * f * frame_period_s)
    h = (K_tot_1 / (1.0 - (1.0 - K_tot_1) * z_inv)) * np.exp(-1j * np.pi * f * frame_period_s)
    mag_db = 20.0 * np.log10(np.maximum(np.abs(h), 1.0e-12))
    phase_rad = np.unwrap(np.angle(h))
    phase_deg = np.degrees(phase_rad)
    group_delay_us = -(np.gradient(phase_deg, f) / 360.0) * 1.0e6
    return mag_db, phase_deg, group_delay_us


def compute_analytical_arw_psd_deg2_h2_per_hz(
    cfg: dict[str, Any],
    phys: dict[str, Any],
) -> dict[str, float]:
    """Compute analytical EQ-15 + EQ-19 white-noise ARW [deg/rt-h] and one-sided rate PSD [(deg/h)^2/Hz]."""
    alpha = float(cfg["dsp"]["alpha_rad"])
    p_peak = float(cfg["optics"]["P_peak_W"])
    vis = float(phys["visibility_V"])
    k_opt = float(phys["K_opt_rad_per_rad_s"])
    delta_nu = float(phys["delta_nu_eff_Hz"])
    resp = float(cfg["analog_frontend"]["responsivity_A_per_W"])
    i_dark = float(cfg["analog_frontend"]["I_dark_A"])
    r_f = float(cfg["analog_frontend"]["R_f_ohm"])
    t_k = float(cfg["analog_frontend"]["T_tia_K"])
    e_n = float(cfg["analog_frontend"]["e_n_op_V_per_rtHz"])
    i_n = float(cfg["analog_frontend"]["i_n_op_A_per_rtHz"])
    k_over = int(cfg["adc_dac"]["K_oversample"])
    k_start = int(cfg["adc_dac"]["k_start"])
    k_end = int(cfg["adc_dac"]["k_end"])
    eta_b = float(k_end - k_start + 1) / float(k_over)

    # Operating-point average optical power and slope at bias angle alpha (EQ-13, EQ-15)
    p_op = 0.5 * p_peak * (1.0 - vis * math.cos(alpha))
    i_pd = resp * p_op
    s_i_shot = 2.0 * Q_ELECTRON * (i_pd + i_dark)
    s_i_rin = (i_pd * i_pd) / delta_nu
    s_i_therm = 4.0 * K_BOLTZMANN * t_k / r_f
    s_i_op = i_n * i_n + (e_n / r_f) ** 2
    s_i_tot = s_i_shot + s_i_rin + s_i_therm + s_i_op

    # Phase sensitivity dI/d(Delta_phi) = 0.5 * R * P_peak * V * sin(alpha); blanking raises PSD by 1/eta_b
    di_dphi = 0.5 * resp * p_peak * vis * math.sin(alpha)
    s_phi_rad2_hz = (s_i_tot / (di_dphi * di_dphi)) / eta_b
    s_omega_rad2_s2_hz = s_phi_rad2_hz / (k_opt * k_opt)
    s_omega_deg2_h2_hz = s_omega_rad2_s2_hz * (RAD_S_TO_DEG_H**2)
    asd_deg_h_per_rt_hz = math.sqrt(s_omega_deg2_h2_hz)
    arw_deg_per_rt_h = math.sqrt(s_omega_deg2_h2_hz / 2.0) / 60.0
    return {
        "eta_blanking": eta_b,
        "S_i_tot_A2_per_Hz": s_i_tot,
        "psd_white_deg2_h2_per_Hz": s_omega_deg2_h2_hz,
        "asd_white_deg_h_per_rtHz": asd_deg_h_per_rt_hz,
        "arw_analytical_deg_per_rt_h": arw_deg_per_rt_h,
    }


def _log_bin_spectrum(
    freqs: np.ndarray,
    psd: np.ndarray,
    f_min: float,
    f_max: float,
    n_bins: int = 120,
) -> tuple[list[float], list[float]]:
    """Compress a dense Welch PSD onto clean log-spaced frequency bins preserving energy."""
    mask = (freqs >= f_min) & (freqs <= f_max) & (psd > 0.0)
    f_v = freqs[mask]
    p_v = psd[mask]
    edges = np.geomspace(float(f_v[0]), float(f_v[-1]), n_bins + 1)
    f_out: list[float] = []
    p_out: list[float] = []
    for i in range(n_bins):
        sel = (f_v >= edges[i]) & (f_v <= edges[i + 1])
        if np.any(sel):
            f_out.append(float(np.exp(np.mean(np.log(f_v[sel])))))
            p_out.append(float(np.mean(p_v[sel])))
    return f_out, p_out


def _extract_step_case(
    bin_path: Path,
    base_clean: dict[str, Any],
    phys_p: Path,
    k_opt: float,
    work_dir: Path,
    label: str,
    dsp_mode: str,
    k_tot_1: float,
    target_deg_s: float,
) -> dict[str, Any]:
    """Execute one genuine Tier 2 step simulation and extract full time-domain metrics & phase traces."""
    alpha_val = math.pi / 3.0 if dsp_mode == "6state" else math.pi / 4.0
    step_t = 0.001
    dur_s = 0.008
    k_tot_2 = min(float(base_clean["dsp"]["K_tot_2"]), 0.08 * k_tot_1)
    cfg = deep_merge(
        base_clean,
        {
            "dsp": {"mode": dsp_mode, "alpha_rad": alpha_val, "K_tot_1": k_tot_1, "K_tot_2": k_tot_2},
            "simulation": {
                "duration_s": dur_s,
                "decimation_tau": 1,
                "dump_micro_ms": 0.0,
                "dump_dsp_trace": True,
                "stimulus": {
                    "type": "step",
                    "omega_start_rad_per_s": 0.0,
                    "omega_end_rad_per_s": target_deg_s * DEG_S_TO_RAD_S,
                    "step_time_s": step_t,
                },
            },
        },
    )
    _run_tier2(bin_path, cfg, phys_p, work_dir / label)
    rec = read_sim_records(work_dir / label / "sim_out.bin")
    tr = read_dsp_trace(work_dir / label / "dsp_trace.bin")
    n = min(len(rec["t"]), len(tr["t"]))
    t_s = rec["t"][:n]
    w_in_deg = rec["omega_in"][:n] * RAD_S_TO_DEG_S
    w_out_deg = rec["omega_out"][:n] * RAD_S_TO_DEG_S
    phi_sagnac = k_opt * rec["omega_in"][:n]
    phi_fb = tr["delta_phi_step"][:n]
    phi_err_mrad = (phi_sagnac - phi_fb) * 1.0e3
    e_omega = tr["e_omega"][:n]

    post = t_s >= step_t
    t_rel_ms = (t_s[post] - step_t) * 1.0e3
    y_post = w_out_deg[post]
    idx_10 = int(np.argmax(y_post >= 0.10 * target_deg_s))
    idx_50 = int(np.argmax(y_post >= 0.50 * target_deg_s))
    idx_90 = int(np.argmax(y_post >= 0.90 * target_deg_s))
    delay_ms = float(t_rel_ms[idx_50])
    rise_ms = float(t_rel_ms[idx_90] - t_rel_ms[idx_10])
    overshoot_pct = float(max(0.0, (float(np.max(y_post)) - target_deg_s) / target_deg_s * 100.0))
    out_2 = np.where(np.abs(y_post - target_deg_s) > 0.02 * target_deg_s)[0]
    out_01 = np.where(np.abs(y_post - target_deg_s) > 0.001 * target_deg_s)[0]
    settle_2_ms = float(t_rel_ms[out_2[-1]])
    settle_01_ms = float(t_rel_ms[out_01[-1]])
    steady_err_pct = float(abs(float(np.mean(y_post[-200:])) - target_deg_s) / target_deg_s * 100.0)

    # Save crisp window [-0.5 ms .. +4.5 ms] around step edge for plotting
    win = (t_s >= (step_t - 0.0005)) & (t_s <= (step_t + 0.0045))
    idx_w = np.where(win)[0]
    stride = max(1, len(idx_w) // 320)
    sel = idx_w[::stride]
    return {
        "label": label,
        "dsp_mode": dsp_mode,
        "K_tot_1": k_tot_1,
        "target_deg_per_s": target_deg_s,
        "target_phi_sagnac_rad": target_deg_s * DEG_S_TO_RAD_S * k_opt,
        "delay_time_50_ms": delay_ms,
        "rise_time_10_90_ms": rise_ms,
        "settling_time_2pct_ms": settle_2_ms,
        "settling_time_0p1pct_ms": settle_01_ms,
        "overshoot_pct": overshoot_pct,
        "steady_state_err_pct": steady_err_pct,
        "trace": {
            "t_ms": [float((t_s[i] - step_t) * 1.0e3) for i in sel],
            "omega_in_deg_per_s": [float(w_in_deg[i]) for i in sel],
            "omega_out_deg_per_s": [float(w_out_deg[i]) for i in sel],
            "tracking_err_deg_per_s": [float(w_out_deg[i] - w_in_deg[i]) for i in sel],
            "phi_sagnac_rad": [float(phi_sagnac[i]) for i in sel],
            "delta_phi_step_rad": [float(phi_fb[i]) for i in sel],
            "phi_err_mrad": [float(phi_err_mrad[i]) for i in sel],
            "e_omega_counts": [float(e_omega[i]) for i in sel],
        },
    }


def run_dyn_step_response(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    workers: int | None = None,
) -> dict[str, Any]:
    """DYN-01: Dedicated Closed-Loop Step Response (10 & 100 deg/s, 4-State vs 6-State, K_tot_1 Sweep)."""
    work = out_dir / "dyn01_work"
    phys, phys_p = _ensure_phys(base_cfg, work, ideal=True)
    k_opt = float(phys["K_opt_rad_per_rad_s"])

    base_clean = deep_merge(
        base_cfg,
        {
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_vpi_loop": True, "en_prbs_dither": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
        },
    )

    specs = [
        ("step10_2state", "2state", 0.25, 10.0),
        ("step10_4state", "4state", 0.25, 10.0),
        ("step10_6state", "6state", 0.25, 10.0),
        ("step100_2state", "2state", 0.25, 100.0),
        ("step100_4state", "4state", 0.25, 100.0),
        ("step100_6state", "6state", 0.25, 100.0),
        ("step10_6state_k015", "6state", 0.15, 10.0),
        ("step10_6state_k045", "6state", 0.45, 10.0),
    ]

    def _run_one(item: tuple[str, str, float, float]) -> dict[str, Any]:
        lbl, mode, kt, tgt = item
        return _extract_step_case(bin_path, base_clean, phys_p, k_opt, work, lbl, mode, kt, tgt)

    max_w = workers if workers is not None else min(len(specs), max(1, os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        cases_list = list(pool.map(_run_one, specs))
    cases = {c["label"]: c for c in cases_list}

    tr_k015 = cases["step10_6state_k015"]["rise_time_10_90_ms"]
    tr_k025 = cases["step10_6state"]["rise_time_10_90_ms"]
    tr_k045 = cases["step10_6state_k045"]["rise_time_10_90_ms"]
    max_ss_err = max(c["steady_state_err_pct"] for c in cases_list)
    passed = bool(max_ss_err < 0.05 and tr_k045 < tr_k025 < tr_k015)

    result = {
        "scenario_id": "DYN-01",
        "title": "Closed-Loop Step Response (10 & 100 deg/s, 2/4/6-State DSP & K_tot_1 Sweep)",
        "K_opt_rad_per_rad_s": k_opt,
        "cases": cases,
        "max_steady_state_err_pct": max_ss_err,
        "monotonic_gain_speedup": bool(tr_k045 < tr_k025 < tr_k015),
        "pass": passed,
    }
    (out_dir / "dyn01_step_response.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_dyn_freq_response(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    workers: int | None = None,
) -> dict[str, Any]:
    """DYN-02: Full Closed-Loop Frequency Response — Bode Magnitude, Unwrapped Phase & Group Delay."""
    work = out_dir / "dyn02_work"
    phys, phys_p = _ensure_phys(base_cfg, work, ideal=True)
    tau_s = float(phys["tau_s"])
    k_tot_1 = float(base_cfg["dsp"]["K_tot_1"])

    base_clean = deep_merge(
        base_cfg,
        {
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_vpi_loop": True, "en_prbs_dither": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
        },
    )

    freqs_hz = [
        20.0, 50.0, 100.0, 200.0, 400.0, 700.0, 1000.0,
        1500.0, 2000.0, 2500.0, 3200.0, 4200.0, 5500.0, 7500.0, 10000.0,
        14000.0, 20000.0,
    ]
    amp_deg_s = 2.0
    amp_rad_s = amp_deg_s * DEG_S_TO_RAD_S

    jobs: list[tuple[str, float]] = [
        (mode, f_hz) for mode in ("2state", "4state", "6state") for f_hz in freqs_hz
    ]

    def _run_pt(item: tuple[str, float]) -> dict[str, Any]:
        mode, f_hz = item
        alpha_val = math.pi / 3.0 if mode == "6state" else math.pi / 4.0
        dur = max(0.015, 7.0 / f_hz)
        cfg_f = deep_merge(
            base_clean,
            {
                "dsp": {"mode": mode, "alpha_rad": alpha_val},
                "simulation": {
                    "duration_s": dur,
                    "decimation_tau": 1,
                    "dump_micro_ms": 0.0,
                    "stimulus": {
                        "type": "sine",
                        "omega_rad_per_s": 0.0,
                        "freq_Hz": f_hz,
                        "amp_rad_per_s": amp_rad_s,
                    },
                },
            },
        )
        sub = work / f"{mode}_{int(f_hz)}Hz"
        _run_tier2(bin_path, cfg_f, phys_p, sub)
        rec = read_sim_records(sub / "sim_out.bin")
        skip_t = max(0.004, 1.0 / f_hz)
        mask = rec["t"] >= skip_t
        tt = rec["t"][mask]
        yy = rec["omega_out"][mask]
        win = np.hanning(len(tt))
        w_sum = float(np.sum(win))
        ph = 2.0 * np.pi * f_hz * tt
        re_c = float(2.0 / w_sum * np.sum(win * yy * np.sin(ph)))
        im_c = float(2.0 / w_sum * np.sum(win * yy * np.cos(ph)))
        gain = math.hypot(re_c, im_c) / amp_rad_s
        return {
            "mode": mode,
            "freq_Hz": f_hz,
            "mag_linear": gain,
            "mag_dB": 20.0 * math.log10(max(gain, 1.0e-12)),
            "phase_rad_raw": math.atan2(im_c, re_c),
        }

    max_w = workers if workers is not None else min(len(jobs), max(1, os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        raw_pts = list(pool.map(_run_pt, jobs))

    f_arr = np.array(freqs_hz, dtype=np.float64)
    modes_out: dict[str, Any] = {}
    for mode, n_states in (("2state", 2), ("4state", 4), ("6state", 6)):
        pts = [p for p in raw_pts if p["mode"] == mode]
        mags_db = np.array([p["mag_dB"] for p in pts], dtype=np.float64)
        ph_unwrap_deg = np.degrees(np.unwrap([p["phase_rad_raw"] for p in pts]))
        gd_us = -(np.gradient(ph_unwrap_deg, f_arr) / 360.0) * 1.0e6

        # 2-State sliding-window demodulation updates every 1*tau; 4-State/6-State update once per N*tau frame
        frame_s = tau_s if mode == "2state" else n_states * tau_s
        th_mag_db, th_phase_deg, th_gd_us = compute_closed_loop_frf_theory(f_arr, k_tot_1, frame_s)
        bw_theory_hz = compute_theoretical_bw_3db_hz(k_tot_1, frame_s, tau_s=tau_s)

        below = np.where(mags_db <= -3.0)[0]
        i1 = int(below[0])
        i0 = i1 - 1
        frac = (mags_db[i0] - (-3.0)) / max(mags_db[i0] - mags_db[i1], 1.0e-12)
        bw_meas_hz = float(f_arr[i0] + frac * (f_arr[i1] - f_arr[i0]))
        phase_at_bw = float(ph_unwrap_deg[i0] + frac * (ph_unwrap_deg[i1] - ph_unwrap_deg[i0]))
        bw_err_pct = abs(bw_meas_hz - bw_theory_hz) / max(bw_theory_hz, 1.0) * 100.0

        idx_100 = freqs_hz.index(100.0)
        idx_1k = freqs_hz.index(1000.0)
        modes_out[mode] = {
            "n_states": n_states,
            "frame_rate_Hz": 1.0 / frame_s,
            "bw_3db_measured_Hz": bw_meas_hz,
            "bw_3db_theory_Hz": bw_theory_hz,
            "bw_mismatch_pct": bw_err_pct,
            "dc_gain_20Hz_dB": float(mags_db[0]),
            "phase_at_100Hz_deg": float(ph_unwrap_deg[idx_100]),
            "phase_at_1kHz_deg": float(ph_unwrap_deg[idx_1k]),
            "phase_at_bw_deg": phase_at_bw,
            "low_freq_group_delay_us": float(np.mean(gd_us[:5])),
            "freqs_Hz": freqs_hz,
            "mag_dB": [float(x) for x in mags_db],
            "phase_deg": [float(x) for x in ph_unwrap_deg],
            "group_delay_us": [float(x) for x in gd_us],
            "theory_mag_dB": [float(x) for x in th_mag_db],
            "theory_phase_deg": [float(x) for x in th_phase_deg],
            "theory_group_delay_us": [float(x) for x in th_gd_us],
        }

    m2, m4, m6 = modes_out["2state"], modes_out["4state"], modes_out["6state"]
    bw_ratio = m4["bw_3db_measured_Hz"] / max(m6["bw_3db_measured_Hz"], 1.0)
    passed = bool(
        abs(m2["dc_gain_20Hz_dB"]) < 0.1
        and abs(m4["dc_gain_20Hz_dB"]) < 0.1
        and abs(m6["dc_gain_20Hz_dB"]) < 0.1
        and m4["bw_mismatch_pct"] < 25.0
        and m6["bw_mismatch_pct"] < 25.0
        and m2["bw_3db_measured_Hz"] > 2.0 * m4["bw_3db_measured_Hz"]
        and m4["bw_3db_measured_Hz"] > m6["bw_3db_measured_Hz"]
        and m6["phase_deg"][-1] < m6["phase_at_1kHz_deg"] < m6["phase_at_100Hz_deg"] < 0.0
    )
    result = {
        "scenario_id": "DYN-02",
        "title": "Closed-Loop Frequency Response — Full Bode Magnitude, Phase & Group Delay (2/4/6-State)",
        "sine_amp_deg_per_s": amp_deg_s,
        "K_tot_1": k_tot_1,
        "two_state": m2,
        "four_state": m4,
        "six_state": m6,
        "bw_ratio_4state_to_6state": bw_ratio,
        "bw_ratio_2state_to_6state": m2["bw_3db_measured_Hz"] / max(m6["bw_3db_measured_Hz"], 1.0),
        "pass": passed,
    }
    (out_dir / "dyn02_freq_response.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_dyn_output_psd(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    duration_s: float = 1.0,
    workers: int | None = None,
) -> dict[str, Any]:
    """DYN-03: Stationary Broadband Output Angular-Rate PSD [(deg/h)^2/Hz], ASD & Cumulative RMS Noise."""
    work = out_dir / "dyn03_work"
    phys, phys_p = _ensure_phys(base_cfg, work, ideal=False)
    arw_ref = compute_analytical_arw_psd_deg2_h2_per_hz(base_cfg, phys)

    cfg_white = deep_merge(
        base_cfg,
        {
            "dsp": {"mode": "4state", "alpha_rad": math.pi / 4.0, "en_vpi_loop": True, "en_prbs_dither": False},
            "noise": {"en_white_noise": True, "en_pink_noise": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
            "simulation": {
                "duration_s": float(duration_s),
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
            },
        },
    )
    cfg_full_4s = deep_merge(
        base_cfg,
        {
            "dsp": {"mode": "4state", "alpha_rad": math.pi / 4.0, "en_vpi_loop": True, "en_prbs_dither": True},
            "mioc": {"alpha_ram_per_V": 2.0e-4},
            "analog_frontend": {"C_xtalk_F": 0.0, "k_xtalk_A_per_V": 2.0e-6},
            "noise": {
                "en_white_noise": True,
                "en_pink_noise": True,
                "pink_f_min_Hz": 1.0,
                "pink_f_max_Hz": 5000.0,
                "sigma_pink_tia_V": 5.0e-4,
                "sigma_pink_dac_rel": 1.0e-5,
                "sigma_pink_xtalk_rel": 0.25,
            },
            "ablation_flags": {
                "en_pol_error": True,
                "en_kerr": True,
                "en_mioc_vpi_err": True,
                "en_ram": True,
                "en_xtalk": True,
                "en_ltf_transient": True,
                "en_tia_poly_nl": True,
                "en_quantization": True,
            },
            "simulation": {
                "duration_s": float(duration_s),
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
            },
        },
    )
    cfg_full_2s = deep_merge(
        cfg_full_4s,
        {"dsp": {"mode": "2state", "alpha_rad": math.pi / 4.0, "en_vpi_loop": False}},
    )
    cfg_full_6s = deep_merge(
        cfg_full_4s,
        {"dsp": {"mode": "6state", "alpha_rad": math.pi / 3.0}},
    )

    jobs = [
        ("white_linear", cfg_white),
        ("full_2state", cfg_full_2s),
        ("full_4state", cfg_full_4s),
        ("full_6state", cfg_full_6s),
    ]

    def _run_psd(item: tuple[str, dict[str, Any]]) -> tuple[str, dict[str, Any]]:
        name, c = item
        sub = work / name
        _run_tier2(bin_path, c, phys_p, sub)
        rec = read_sim_records(sub / "sim_out.bin")
        dt = float(np.median(np.diff(rec["t"])))
        fs = 1.0 / dt
        skip = min(1000, len(rec["omega_out"]) // 10)
        w_deg_h = rec["omega_out"][skip:] * RAD_S_TO_DEG_H
        nperseg = min(16384, max(512, len(w_deg_h) // 3))
        freqs, psd_deg2_h2 = compute_welch_psd(w_deg_h, fs_Hz=fs, nperseg=nperseg)

        # Ignore DC bin f=0; compute cumulative integrated RMS rate noise [deg/h]
        f_pos = freqs[1:]
        p_pos = np.maximum(psd_deg2_h2[1:], 1.0e-30)
        df = np.diff(f_pos, prepend=f_pos[0])
        cum_rms = np.sqrt(np.cumsum(p_pos * df))

        # Band metrics
        lf_mask = (f_pos >= 5.0) & (f_pos <= 40.0)
        mid_mask = (f_pos >= 200.0) & (f_pos <= 900.0)
        hf_mask = (f_pos >= 8000.0) & (f_pos <= 20000.0)
        lf_psd = float(np.mean(p_pos[lf_mask]))
        mid_psd = float(np.mean(p_pos[mid_mask]))
        hf_psd = float(np.mean(p_pos[hf_mask]))
        arw_meas = math.sqrt(mid_psd / 2.0) / 60.0
        rolloff_db = 10.0 * math.log10(max(hf_psd / max(mid_psd, 1.0e-30), 1.0e-12))

        f_bin, p_bin = _log_bin_spectrum(f_pos, p_pos, float(f_pos[0]), float(f_pos[-1]), n_bins=120)
        # Interpolate cumulative RMS onto binned frequencies
        cum_bin = [float(v) for v in np.interp(f_bin, f_pos, cum_rms)]
        asd_bin = [float(math.sqrt(v)) for v in p_bin]
        return name, {
            "fs_Hz": fs,
            "n_samples": int(len(w_deg_h)),
            "lf_5_40Hz_psd_deg2_h2_per_Hz": lf_psd,
            "mid_200_900Hz_psd_deg2_h2_per_Hz": mid_psd,
            "hf_8_20kHz_psd_deg2_h2_per_Hz": hf_psd,
            "measured_arw_deg_per_rt_h": arw_meas,
            "hf_rolloff_dB": rolloff_db,
            "total_rms_rate_noise_deg_per_h": float(cum_rms[-1]),
            "freqs_Hz": f_bin,
            "psd_deg2_h2_per_Hz": p_bin,
            "asd_deg_h_per_rtHz": asd_bin,
            "cum_rms_deg_per_h": cum_bin,
        }

    max_w = workers if workers is not None else min(4, max(1, os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        regimes = dict(pool.map(_run_psd, jobs))

    wl = regimes["white_linear"]
    f4 = regimes["full_4state"]
    f6 = regimes["full_6state"]
    lf_supp_db = 10.0 * math.log10(
        max(f4["lf_5_40Hz_psd_deg2_h2_per_Hz"] / max(f6["lf_5_40Hz_psd_deg2_h2_per_Hz"], 1.0e-30), 1.0)
    )
    arw_ratio = wl["measured_arw_deg_per_rt_h"] / max(arw_ref["arw_analytical_deg_per_rt_h"], 1.0e-12)
    passed = bool(
        0.5 <= arw_ratio <= 2.0
        and wl["hf_rolloff_dB"] < -3.0
        and lf_supp_db > 10.0
    )

    result = {
        "scenario_id": "DYN-03",
        "title": "Output Angular-Rate Power Spectral Density (PSD), ASD & Cumulative RMS Noise (2/4/6-State)",
        "duration_s": float(duration_s),
        "analytical_white_ref": arw_ref,
        "regimes": regimes,
        "arw_white_meas_to_theory_ratio": arw_ratio,
        "low_freq_6state_suppression_dB": lf_supp_db,
        "pass": passed,
    }
    (out_dir / "dyn03_output_psd.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_dyn_sine_electro_optic(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    """DYN-04: Sinusoidal Rate Input & Full Internal Electro-Optic Signal Chain (PD, V_fb MIOC, Sagnac Phase, TIA)."""
    work = out_dir / "dyn04_work"
    phys, phys_p = _ensure_phys(base_cfg, work, ideal=False)
    k_opt = float(phys["K_opt_rad_per_rad_s"])
    v_pi_0 = float(base_cfg["mioc"]["V_pi_0_V"])
    resp_a_w = float(base_cfg["analog_frontend"]["responsivity_A_per_W"])
    p_peak_w = float(base_cfg["optics"]["P_peak_W"])
    K = int(base_cfg["adc_dac"]["K_oversample"])
    k_start = int(base_cfg["adc_dac"]["k_start"])
    k_end = int(base_cfg["adc_dac"]["k_end"])
    k_clean = (k_start + k_end) // 2

    amp_deg_s = 50.0
    freq_hz = 250.0
    period_s = 1.0 / freq_hz
    dur_s = 4.0 * period_s  # 16.0 ms = 4 exact sine cycles
    dump_micro_ms = 2.05 * period_s * 1.0e3  # 8.2 ms > 2 full sine cycles of sub-tau electro-optic trace

    cfg_sine = deep_merge(
        base_cfg,
        {
            "dsp": {
                "mode": "6state",
                "alpha_rad": math.pi / 3.0,
                "en_vpi_loop": True,
                "en_adc_blanking": True,
                "en_prbs_dither": True,
            },
            "noise": {"en_white_noise": True, "en_pink_noise": False},
            "ablation_flags": {
                "en_pol_error": True,
                "en_kerr": True,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": True,
                "en_ram": True,
                "en_xtalk": True,
                "en_ltf_transient": True,
                "en_tia_poly_nl": True,
                "en_quantization": True,
            },
            "simulation": {
                "duration_s": dur_s,
                "decimation_tau": 1,
                "dump_micro_ms": dump_micro_ms,
                "dump_dsp_trace": True,
                "stimulus": {
                    "type": "sine",
                    "omega_rad_per_s": 0.0,
                    "freq_Hz": freq_hz,
                    "amp_rad_per_s": amp_deg_s * DEG_S_TO_RAD_S,
                },
            },
        },
    )

    summary = _run_tier2(bin_path, cfg_sine, phys_p, work / "sine_run")
    rec = read_sim_records(work / "sine_run" / "sim_out.bin")
    tr = read_dsp_trace(work / "sine_run" / "dsp_trace.bin")
    micro = read_micro_records(work / "sine_run" / "micro_waveforms.bin")

    # 1. Closed-loop sinusoidal tracking, THD & SFDR on steady-state cycles [4 ms .. 16 ms]
    ss_mask = rec["t"] >= period_s
    t_ss = rec["t"][ss_mask]
    w_out_ss_deg = rec["omega_out"][ss_mask] * RAD_S_TO_DEG_S
    win = np.hanning(len(t_ss))
    w_sum = float(np.sum(win))
    ph = 2.0 * np.pi * freq_hz * t_ss
    re_c = float(2.0 / w_sum * np.sum(win * w_out_ss_deg * np.sin(ph)))
    im_c = float(2.0 / w_sum * np.sum(win * w_out_ss_deg * np.cos(ph)))
    meas_amp_deg_s = math.hypot(re_c, im_c)
    sine_gain = meas_amp_deg_s / amp_deg_s
    sine_phase_lag_deg = math.degrees(math.atan2(im_c, re_c))

    # Windowed FFT over steady-state cycles for THD & SFDR
    dt_ss = float(np.median(np.diff(t_ss)))
    fft_mag = np.abs(np.fft.rfft((w_out_ss_deg - np.mean(w_out_ss_deg)) * win))
    fft_freqs = np.fft.rfftfreq(len(t_ss), d=dt_ss)
    fund_idx = int(np.argmin(np.abs(fft_freqs - freq_hz)))
    fund_mag = float(fft_mag[fund_idx])
    harm_p2 = 0.0
    for h_ord in (2, 3, 4, 5):
        h_idx = int(np.argmin(np.abs(fft_freqs - h_ord * freq_hz)))
        harm_p2 += float(fft_mag[h_idx]) ** 2
    thd_db = 10.0 * math.log10(max(harm_p2 / max(fund_mag * fund_mag, 1.0e-30), 1.0e-18))
    spur_mask = np.abs(fft_freqs - freq_hz) > (0.6 * freq_hz)
    spur_mask[0] = False
    max_spur = float(np.max(fft_mag[spur_mask]))
    sfdr_db = 20.0 * math.log10(max(fund_mag / max(max_spur, 1.0e-18), 1.0))

    # 2. Macro-scale 2-cycle electro-optic trace (0..8 ms) combining sim_out, dsp_trace & micro_waveforms
    n_clusters = len(micro["t"]) // K
    n_macro = min(n_clusters, len(rec["t"]), len(tr["t"]))
    t_mac_s = rec["t"][:n_macro]
    w_in_mac = rec["omega_in"][:n_macro] * RAD_S_TO_DEG_S
    w_out_mac = rec["omega_out"][:n_macro] * RAD_S_TO_DEG_S
    phi_sagnac_mac = k_opt * rec["omega_in"][:n_macro]
    phi_fb_mac = tr["delta_phi_step"][:n_macro]
    phi_err_mrad = (phi_sagnac_mac - phi_fb_mac) * 1.0e3
    phi_ramp_mac = tr["phi_ramp"][:n_macro]
    # Pure serrodyne MIOC feedback voltage V_fb_MIOC = -(phi_ramp / pi) * V_pi_0 (Rule 13 negative-feedback polarity)
    v_fb_mioc_mac = -(phi_ramp_mac / math.pi) * v_pi_0

    # Extract settled blanking-window micro sample (k_clean) per tau slot
    idx_clean = np.arange(n_macro) * K + k_clean
    v_mioc_total_mac = micro["v_drv"][idx_clean]
    p_pd_uW_mac = micro["p_det"][idx_clean] * 1.0e6
    i_pd_uA_mac = micro["p_det"][idx_clean] * resp_a_w * 1.0e6
    v_tia_mac = micro["v_tia"][idx_clean]

    # Compute 6-state frame-demodulated PD differential Delta_P_PD(t) vs residual Sagnac phase error
    n_frames = n_macro // 6
    p_mat = p_pd_uW_mac[: n_frames * 6].reshape(n_frames, 6)
    p_demod_uW = (np.sum(p_mat[:, 3:6], axis=1) - np.sum(p_mat[:, 0:3], axis=1)) / 6.0
    t_fr_ms = t_mac_s[2 : n_frames * 6 : 6] * 1.0e3
    phi_err_fr_mrad = phi_err_mrad[2 : n_frames * 6 : 6]
    # Correlate frame-demodulated PD signal with residual Sagnac phase after initial 0.5 ms startup
    valid_fr = t_fr_ms >= 0.5
    pd_phi_corr = float(abs(np.corrcoef(p_demod_uW[valid_fr], phi_err_fr_mrad[valid_fr])[0, 1]))
    # Exclude the single t=0 uninitialized ring-buffer startup frame from displayed PD envelope
    fr_disp = t_fr_ms >= 0.08
    mac_start = int(np.searchsorted(t_mac_s, 0.00005))
    mac_stride = max(1, (n_macro - mac_start) // 850)
    # Also extract crisp 60 us sub-tau zoom around peak angular rate (t = 5.0 ms -> sin(2*pi*250*0.005) = +1)
    zoom_t0 = 0.00497
    zoom_t1 = 0.00503
    z_mask = (micro["t"] >= zoom_t0) & (micro["t"] <= zoom_t1)
    t_z_us = (micro["t"][z_mask] - zoom_t0) * 1.0e6
    v_mioc_z = micro["v_drv"][z_mask]
    v_fb_z = -(micro["phi_ramp"][z_mask] / math.pi) * v_pi_0
    p_pd_z_uW = micro["p_det"][z_mask] * 1.0e6
    i_pd_z_uA = micro["p_det"][z_mask] * resp_a_w * 1.0e6
    v_tia_z = micro["v_tia"][z_mask]
    blank_z = micro["in_blanking"][z_mask]

    peak_phi_sagnac_theory = k_opt * amp_deg_s * DEG_S_TO_RAD_S
    peak_phi_sagnac_meas = float(np.max(np.abs(phi_sagnac_mac)))
    peak_phi_err_mrad = float(np.max(np.abs(phi_err_mrad[t_mac_s >= 0.001])))
    flybacks = int(summary["flyback_count"])
    p_pd_max_uW = float(np.max(p_pd_uW_mac[mac_start:]))
    p_pd_min_uW = float(np.min(p_pd_uW_mac[mac_start:]))

    passed = bool(
        0.95 <= sine_gain <= 1.05
        and sfdr_db > 35.0
        and abs(peak_phi_sagnac_meas - peak_phi_sagnac_theory) / peak_phi_sagnac_theory < 0.005
        and flybacks > 10
        and 0.0 <= p_pd_min_uW <= p_pd_max_uW <= (1.15 * p_peak_w * 1.0e6)
        and pd_phi_corr > 0.90
    )

    result = {
        "scenario_id": "DYN-04",
        "title": "Sinusoidal Rate Input & Full Electro-Optic Signal Chain (PD, V_fb MIOC, Sagnac Phase, TIA)",
        "dsp_mode": "6state",
        "sine_amp_deg_per_s": amp_deg_s,
        "sine_freq_Hz": freq_hz,
        "duration_ms": dur_s * 1.0e3,
        "K_opt_rad_per_rad_s": k_opt,
        "V_pi_0_V": v_pi_0,
        "responsivity_A_per_W": resp_a_w,
        "peak_phi_sagnac_rad": peak_phi_sagnac_meas,
        "peak_phi_sagnac_theory_rad": peak_phi_sagnac_theory,
        "peak_phi_err_mrad": peak_phi_err_mrad,
        "sine_tracking_gain": sine_gain,
        "sine_phase_lag_deg": sine_phase_lag_deg,
        "output_thd_dB": thd_db,
        "output_sfdr_dB": sfdr_db,
        "flyback_count": flybacks,
        "p_pd_min_uW": p_pd_min_uW,
        "p_pd_max_uW": p_pd_max_uW,
        "i_pd_max_uA": float(np.max(i_pd_uA_mac[mac_start:])),
        "v_tia_max_V": float(np.max(v_tia_mac[mac_start:])),
        "v_fb_mioc_peak_V": float(np.max(np.abs(v_fb_mioc_mac))),
        "v_mioc_total_peak_V": float(np.max(np.abs(v_mioc_total_mac))),
        "pd_demod_to_phi_err_corr": pd_phi_corr,
        "macro_trace": {
            "t_ms": [float(x * 1.0e3) for x in t_mac_s[mac_start::mac_stride]],
            "omega_in_deg_per_s": [float(x) for x in w_in_mac[mac_start::mac_stride]],
            "omega_out_deg_per_s": [float(x) for x in w_out_mac[mac_start::mac_stride]],
            "phi_sagnac_rad": [float(x) for x in phi_sagnac_mac[mac_start::mac_stride]],
            "phi_feedback_rad": [float(x) for x in phi_fb_mac[mac_start::mac_stride]],
            "phi_err_mrad": [float(x) for x in phi_err_mrad[mac_start::mac_stride]],
            "phi_ramp_rad": [float(x) for x in phi_ramp_mac[mac_start::mac_stride]],
            "v_fb_mioc_V": [float(x) for x in v_fb_mioc_mac[mac_start::mac_stride]],
            "v_mioc_total_V": [float(x) for x in v_mioc_total_mac[mac_start::mac_stride]],
            "p_pd_uW": [float(x) for x in p_pd_uW_mac[mac_start::mac_stride]],
            "i_pd_uA": [float(x) for x in i_pd_uA_mac[mac_start::mac_stride]],
            "v_tia_V": [float(x) for x in v_tia_mac[mac_start::mac_stride]],
            "frame_t_ms": [float(x) for x in t_fr_ms[fr_disp]],
            "p_pd_demod_uW": [float(x) for x in p_demod_uW[fr_disp]],
        },
        "micro_zoom": {
            "t_origin_ms": zoom_t0 * 1.0e3,
            "t_us": [float(x) for x in t_z_us],
            "v_mioc_total_V": [float(x) for x in v_mioc_z],
            "v_fb_mioc_V": [float(x) for x in v_fb_z],
            "p_pd_uW": [float(x) for x in p_pd_z_uW],
            "i_pd_uA": [float(x) for x in i_pd_z_uA],
            "v_tia_V": [float(x) for x in v_tia_z],
            "in_blanking": [int(x) for x in blank_z],
        },
        "pass": passed,
    }
    (out_dir / "dyn04_sine_electro_optic.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def run_all_dynamic_probe_scenarios(
    bin_path: Path,
    base_cfg: dict[str, Any],
    out_dir: Path,
    psd_duration_s: float = 1.0,
    workers: int | None = None,
) -> dict[str, Any]:
    """Execute all 4 Group C Dynamic Characterization, Output PSD & Electro-Optic Probe scenarios."""
    out_dir.mkdir(parents=True, exist_ok=True)
    d1 = run_dyn_step_response(bin_path, base_cfg, out_dir, workers=workers)
    d2 = run_dyn_freq_response(bin_path, base_cfg, out_dir, workers=workers)
    d3 = run_dyn_output_psd(bin_path, base_cfg, out_dir, duration_s=psd_duration_s, workers=workers)
    d4 = run_dyn_sine_electro_optic(bin_path, base_cfg, out_dir)
    summary = {
        "DYN-01": d1,
        "DYN-02": d2,
        "DYN-03": d3,
        "DYN-04": d4,
        "all_passed": bool(d1["pass"] and d2["pass"] and d3["pass"] and d4["pass"]),
    }
    (out_dir / "dyn_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
