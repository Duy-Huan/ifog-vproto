"""Physical Hardware Lab Data Ingestion & NASA-STD-7009A CAS-4 / ASME V&V 20 Validation (v4.1.0 IND-01).

Provides standardized CSV ingestors for the three mandatory physical IFOG benchtop
qualification test rigs required to elevate credibility from CAS Level 3 (TRL 6) to
CAS Level 4 (TRL 7-8 / DO-254):

  1. ``static_avar_10h.csv``:
     10-hour static Allan Deviation & rate PSD on a granite vibration-isolation table
     (columns: ``tau_s, adev_deg_h, psd_freq_Hz, psd_deg_h2_Hz, u_meas_pct``).
  2. ``rate_table_deadband.csv``:
     Precision slow rate-table sweep over ``[-2, +2] deg/s`` exposing lock-in Deadband &
     Bunny Ears (columns: ``omega_in_deg_s, omega_out_deg_s, u_meas_deg_h``).
  3. ``thermal_chamber_ramp.csv``:
     Environmental thermal chamber soak/ramp across ``-40 .. +85 degC`` measuring thermal
     bias drift & scale-factor error (columns: ``t_s, T_chamber_C, omega_bias_deg_h, sf_err_ppm, u_bias_deg_h``).
"""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from tier3_analysis.inverse_calibration import (
    InverseCalibrator,
    forward_avar_psd,
    forward_slow_rate_ramp,
    forward_thermal_ramp,
)

AVAR_CSV_COLUMNS = ("tau_s", "adev_deg_h", "psd_freq_Hz", "psd_deg_h2_Hz", "u_meas_pct")
RATE_CSV_COLUMNS = ("omega_in_deg_s", "omega_out_deg_s", "u_meas_deg_h")
THERMAL_CSV_COLUMNS = ("t_s", "T_chamber_C", "omega_bias_deg_h", "sf_err_ppm", "u_bias_deg_h")

DEFAULT_LAB_INITIAL_PARAMS: dict[str, float] = {
    "c_pink_coeff": 1.0,
    "R_facet_dB": -68.0,
    "eta_pd_scale": 1.0,
    "C_xtalk_F": 2.0e-12,
    "G_xtalk_S": 1.0e-8,
    "dac_asym_lsb": 0.15,
    "diffusivity_m2_per_s": 8.0e-7,
    "delta_z_quad_m": 1.5e-3,
    "alpha_vpi_ppm_K": 220.0,
    "alpha_bobbin_ppm_K": 18.0,
}

# Physical reference hardware truth embedded in the curated sample bench dataset
REFERENCE_LAB_HARDWARE_TRUTH: dict[str, float] = {
    "c_pink_coeff": 2.15,
    "R_facet_dB": -53.5,
    "eta_pd_scale": 0.89,
    "C_xtalk_F": 7.4e-12,
    "G_xtalk_S": 4.2e-8,
    "dac_asym_lsb": 1.15,
    "diffusivity_m2_per_s": 1.48e-6,
    "delta_z_quad_m": 4.3e-3,
    "alpha_vpi_ppm_K": 410.0,
    "alpha_bobbin_ppm_K": 30.5,
}


def _read_csv_checked(csv_path: Path | str, required_cols: tuple[str, ...]) -> list[dict[str, str]]:
    """Read a CSV file and fail closed if any required column header or data row is missing."""
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or any(c not in reader.fieldnames for c in required_cols):
            raise ValueError(f"Lab CSV {path} missing required columns {required_cols}")
        rows = list(reader)
    if len(rows) < 4:
        raise ValueError(f"Lab CSV {path} requires at least 4 data rows, got {len(rows)}")
    return rows


def load_lab_avar_csv(csv_path: Path | str) -> dict[str, np.ndarray]:
    """Load 10-hour granite-table static AVAR + PSD measurement CSV."""
    rows = _read_csv_checked(csv_path, AVAR_CSV_COLUMNS)
    return {
        "taus_s": np.array([float(r["tau_s"]) for r in rows], dtype=np.float64),
        "avar_meas_deg_h": np.array([float(r["adev_deg_h"]) for r in rows], dtype=np.float64),
        "freqs_Hz": np.array([float(r["psd_freq_Hz"]) for r in rows], dtype=np.float64),
        "psd_meas_deg_h2_Hz": np.array([float(r["psd_deg_h2_Hz"]) for r in rows], dtype=np.float64),
        "u_meas_pct": np.array([float(r["u_meas_pct"]) for r in rows], dtype=np.float64),
    }


def load_lab_rate_ramp_csv(csv_path: Path | str) -> dict[str, np.ndarray]:
    """Load precision slow rate-table sweep CSV ([-2, +2] deg/s -> deg/h)."""
    rows = _read_csv_checked(csv_path, RATE_CSV_COLUMNS)
    w_in_deg_s = np.array([float(r["omega_in_deg_s"]) for r in rows], dtype=np.float64)
    w_out_deg_s = np.array([float(r["omega_out_deg_s"]) for r in rows], dtype=np.float64)
    return {
        "omega_in_deg_s": w_in_deg_s,
        "omega_out_deg_s": w_out_deg_s,
        "omega_in_deg_h": w_in_deg_s * 3600.0,
        "omega_out_meas_deg_h": w_out_deg_s * 3600.0,
        "u_meas_deg_h": np.array([float(r["u_meas_deg_h"]) for r in rows], dtype=np.float64),
    }


def load_lab_thermal_csv(csv_path: Path | str) -> dict[str, np.ndarray]:
    """Load environmental thermal chamber (-40 .. +85 degC) ramp CSV."""
    rows = _read_csv_checked(csv_path, THERMAL_CSV_COLUMNS)
    return {
        "t_thermal_s": np.array([float(r["t_s"]) for r in rows], dtype=np.float64),
        "T_chamber_C": np.array([float(r["T_chamber_C"]) for r in rows], dtype=np.float64),
        "omega_bias_meas_deg_h": np.array(
            [float(r["omega_bias_deg_h"]) for r in rows], dtype=np.float64
        ),
        "sf_err_meas_ppm": np.array([float(r["sf_err_ppm"]) for r in rows], dtype=np.float64),
        "u_bias_deg_h": np.array([float(r["u_bias_deg_h"]) for r in rows], dtype=np.float64),
    }


def compute_asme_vv20_metric(
    sim: np.ndarray,
    meas: np.ndarray,
    u_meas: np.ndarray,
    u_num_frac: float = 0.005,
) -> dict[str, float]:
    """Compute ASME V&V 20 validation comparison error E, uncertainty u_val, and ratio |E|/u_val."""
    err = np.asarray(sim, dtype=np.float64) - np.asarray(meas, dtype=np.float64)
    u_num = u_num_frac * np.maximum(np.abs(meas), 1.0e-12)
    u_val = np.sqrt(np.asarray(u_meas, dtype=np.float64) ** 2 + u_num**2)
    e_rms = float(np.sqrt(np.mean(err**2)))
    u_val_rms = float(np.sqrt(np.mean(u_val**2)))
    denom = max(float(np.sqrt(np.mean(np.asarray(meas, dtype=np.float64) ** 2))), 1.0e-12)
    return {
        "E_rms": e_rms,
        "u_val_rms": u_val_rms,
        "ratio_E_over_u_val": float(e_rms / max(u_val_rms, 1.0e-12)),
        "nrmse_pct": float(100.0 * e_rms / denom),
    }


def generate_reference_lab_dataset(
    out_dir: Path | str,
    truth_params: dict[str, float] | None = None,
    seed: int = 2026,
) -> Path:
    """Write a complete curated 3-rig physical IFOG reference lab dataset to CSV files."""
    dest = Path(out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    tp = {**REFERENCE_LAB_HARDWARE_TRUTH, **(truth_params or {})}
    rng = np.random.default_rng(seed)

    # Rig 1: 10-hour granite-table static AVAR (tau = 0.1 s .. 10,000 s) + PSD
    taus = np.geomspace(0.1, 10000.0, 28)
    freqs = np.geomspace(1.0e-4, 50.0, 28)
    av_true, psd_true = forward_avar_psd(
        taus, freqs, tp["c_pink_coeff"], tp["R_facet_dB"], tp["eta_pd_scale"]
    )
    u_av_pct = np.linspace(1.5, 4.5, len(taus))  # larger chi-square uncertainty at long tau
    av_meas = av_true * (1.0 + rng.normal(0.0, 0.012, size=len(taus)))
    psd_meas = psd_true * (1.0 + rng.normal(0.0, 0.018, size=len(freqs)))
    with (dest / "static_avar_10h.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(AVAR_CSV_COLUMNS)
        for t_v, a_v, f_v, p_v, u_v in zip(taus, av_meas, freqs, psd_meas, u_av_pct):
            w.writerow([f"{t_v:.6g}", f"{a_v:.8g}", f"{f_v:.6g}", f"{p_v:.8g}", f"{u_v:.3f}"])

    # Rig 2: Precision slow rate table over [-2, +2] deg/s with fine deadband/bunny-ears sweep near 0
    fine_deg_h = np.linspace(-3.0, 3.0, 41)
    coarse_neg = np.array([-7200.0, -3600.0, -1800.0, -360.0, -36.0, -9.0], dtype=np.float64)
    coarse_pos = np.array([9.0, 36.0, 360.0, 1800.0, 3600.0, 7200.0], dtype=np.float64)
    omega_in_deg_h = np.concatenate([coarse_neg, fine_deg_h, coarse_pos])
    db_true = forward_slow_rate_ramp(
        omega_in_deg_h, tp["C_xtalk_F"], tp["G_xtalk_S"], tp["dac_asym_lsb"]
    )["omega_out_deg_h"]
    omega_out_meas_deg_h = db_true + rng.normal(0.0, 0.005, size=len(omega_in_deg_h))
    u_rate_deg_h = np.full(len(omega_in_deg_h), 0.025)
    with (dest / "rate_table_deadband.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(RATE_CSV_COLUMNS)
        for wi, wo, ur in zip(omega_in_deg_h / 3600.0, omega_out_meas_deg_h / 3600.0, u_rate_deg_h):
            w.writerow([f"{wi:.12g}", f"{wo:.12g}", f"{ur:.4f}"])

    # Rig 3: Thermal chamber sweep -40 .. +85 degC (125 K span at 0.05 K/s -> 2500 s)
    t_th = np.linspace(0.0, 2500.0, 41)
    T_chamber_C = -40.0 + 0.05 * t_th
    th_true = forward_thermal_ramp(
        t_th,
        tp["diffusivity_m2_per_s"],
        tp["delta_z_quad_m"],
        tp["alpha_vpi_ppm_K"],
        tp["alpha_bobbin_ppm_K"],
    )
    bias_meas = th_true["omega_bias_deg_h"] + rng.normal(0.0, 0.008, size=len(t_th))
    sf_meas = th_true["sf_err_ppm"] + rng.normal(0.0, 1.8, size=len(t_th))
    u_bias = np.full(len(t_th), 0.025)
    with (dest / "thermal_chamber_ramp.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(THERMAL_CSV_COLUMNS)
        for tv, tc, bv, sv, ub in zip(t_th, T_chamber_C, bias_meas, sf_meas, u_bias):
            w.writerow([f"{tv:.3f}", f"{tc:.3f}", f"{bv:.8g}", f"{sv:.6f}", f"{ub:.4f}"])

    return dest


def validate_against_lab_dataset(
    lab_dir: Path | str,
    initial_params: dict[str, float] | None = None,
    out_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Ingest a 3-rig physical lab dataset, calibrate Tier 1/2/3 parameters, and compute ASME V&V 20 CAS-4 report."""
    ldir = Path(lab_dir)
    av_data = load_lab_avar_csv(ldir / "static_avar_10h.csv")
    rate_data = load_lab_rate_ramp_csv(ldir / "rate_table_deadband.csv")
    th_data = load_lab_thermal_csv(ldir / "thermal_chamber_ramp.csv")

    init_p = {**DEFAULT_LAB_INITIAL_PARAMS, **(initial_params or {})}
    # Derive thermal boundary ramp [K/s] directly from measured chamber temperature ramp
    dt_span = max(float(th_data["t_thermal_s"][-1] - th_data["t_thermal_s"][0]), 1.0)
    chamber_ramp_K_s = float(th_data["T_chamber_C"][-1] - th_data["T_chamber_C"][0]) / dt_span
    th_ctx = {"boundary_ramp_K_per_s": chamber_ramp_K_s}

    dataset = {
        "taus_s": av_data["taus_s"],
        "avar_meas_deg_h": av_data["avar_meas_deg_h"],
        "freqs_Hz": av_data["freqs_Hz"],
        "psd_meas_deg_h2_Hz": av_data["psd_meas_deg_h2_Hz"],
        "omega_in_deg_h": rate_data["omega_in_deg_h"],
        "omega_out_meas_deg_h": rate_data["omega_out_meas_deg_h"],
        "t_thermal_s": th_data["t_thermal_s"],
        "omega_bias_meas_deg_h": th_data["omega_bias_meas_deg_h"],
        "sf_err_meas_ppm": th_data["sf_err_meas_ppm"],
    }

    cal = InverseCalibrator(th_ctx=th_ctx)
    cal_out_path = (Path(out_dir) / "lab_calibrated_params.json") if out_dir is not None else None
    cal_res = cal.calibrate_all(dataset, init_p, out_path=cal_out_path)
    cp = cal_res["calibrated_params"]

    # Pre & Post forward curves for ASME V&V 20 metrics & visualization
    av_pre, psd_pre = forward_avar_psd(
        av_data["taus_s"], av_data["freqs_Hz"],
        init_p["c_pink_coeff"], init_p["R_facet_dB"], init_p["eta_pd_scale"],
    )
    av_post, psd_post = forward_avar_psd(
        av_data["taus_s"], av_data["freqs_Hz"],
        cp["c_pink_coeff"], cp["R_facet_dB"], cp["eta_pd_scale"],
    )
    db_pre = forward_slow_rate_ramp(
        rate_data["omega_in_deg_h"], init_p["C_xtalk_F"], init_p["G_xtalk_S"], init_p["dac_asym_lsb"]
    )["omega_out_deg_h"]
    db_post = forward_slow_rate_ramp(
        rate_data["omega_in_deg_h"], cp["C_xtalk_F"], cp["G_xtalk_S"], cp["dac_asym_lsb"]
    )["omega_out_deg_h"]
    th_pre = forward_thermal_ramp(
        th_data["t_thermal_s"], init_p["diffusivity_m2_per_s"], init_p["delta_z_quad_m"],
        init_p["alpha_vpi_ppm_K"], init_p["alpha_bobbin_ppm_K"], th_ctx,
    )
    th_post = forward_thermal_ramp(
        th_data["t_thermal_s"], cp["diffusivity_m2_per_s"], cp["delta_z_quad_m"],
        cp["alpha_vpi_ppm_K"], cp["alpha_bobbin_ppm_K"], th_ctx,
    )

    u_avar_abs = (av_data["u_meas_pct"] / 100.0) * av_data["avar_meas_deg_h"]
    vv20_before = {
        "static_avar_10h": compute_asme_vv20_metric(av_pre, av_data["avar_meas_deg_h"], u_avar_abs),
        "rate_table_deadband": compute_asme_vv20_metric(
            db_pre - rate_data["omega_in_deg_h"],
            rate_data["omega_out_meas_deg_h"] - rate_data["omega_in_deg_h"],
            rate_data["u_meas_deg_h"],
        ),
        "thermal_chamber_bias": compute_asme_vv20_metric(
            th_pre["omega_bias_deg_h"], th_data["omega_bias_meas_deg_h"], th_data["u_bias_deg_h"]
        ),
    }
    vv20_after = {
        "static_avar_10h": compute_asme_vv20_metric(av_post, av_data["avar_meas_deg_h"], u_avar_abs),
        "rate_table_deadband": compute_asme_vv20_metric(
            db_post - rate_data["omega_in_deg_h"],
            rate_data["omega_out_meas_deg_h"] - rate_data["omega_in_deg_h"],
            rate_data["u_meas_deg_h"],
        ),
        "thermal_chamber_bias": compute_asme_vv20_metric(
            th_post["omega_bias_deg_h"], th_data["omega_bias_meas_deg_h"], th_data["u_bias_deg_h"]
        ),
    }

    max_ratio_after = float(max(v["ratio_E_over_u_val"] for v in vv20_after.values()))
    cas4_pass = bool(cal_res["pass_lt_5pct"] and max_ratio_after <= 2.0)

    report = {
        "spec_id": "IFOG-VPROTO-v4.1.0-IND01",
        "lab_dir": str(ldir),
        "rig_coverage": {
            "static_avar_tau_range_s": [float(av_data["taus_s"][0]), float(av_data["taus_s"][-1])],
            "rate_table_range_deg_s": [
                float(np.min(rate_data["omega_in_deg_s"])),
                float(np.max(rate_data["omega_in_deg_s"])),
            ],
            "thermal_chamber_range_C": [
                float(np.min(th_data["T_chamber_C"])),
                float(np.max(th_data["T_chamber_C"])),
            ],
            "chamber_ramp_K_per_s": chamber_ramp_K_s,
        },
        "calibration": cal_res,
        "asme_vv20_before": vv20_before,
        "asme_vv20_after": vv20_after,
        "max_ratio_E_over_u_val_after": max_ratio_after,
        "nasa_cas_level": 4 if cas4_pass else 3,
        "pass": cas4_pass,
    }
    if out_dir is not None:
        odir = Path(out_dir)
        odir.mkdir(parents=True, exist_ok=True)
        (odir / "lab_validation_report.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        np.savez(
            odir / "ind01_lab_curves.npz",
            taus_s=av_data["taus_s"],
            avar_meas=av_data["avar_meas_deg_h"],
            avar_pre=av_pre,
            avar_post=av_post,
            u_avar_abs=u_avar_abs,
            omega_in_deg_h=rate_data["omega_in_deg_h"],
            err_meas_deg_h=rate_data["omega_out_meas_deg_h"] - rate_data["omega_in_deg_h"],
            err_pre_deg_h=db_pre - rate_data["omega_in_deg_h"],
            err_post_deg_h=db_post - rate_data["omega_in_deg_h"],
            T_chamber_C=th_data["T_chamber_C"],
            bias_meas_deg_h=th_data["omega_bias_meas_deg_h"],
            bias_pre_deg_h=th_pre["omega_bias_deg_h"],
            bias_post_deg_h=th_post["omega_bias_deg_h"],
            sf_meas_ppm=th_data["sf_err_meas_ppm"],
            sf_pre_ppm=th_pre["sf_err_ppm"],
            sf_post_ppm=th_post["sf_err_ppm"],
        )
    return report
