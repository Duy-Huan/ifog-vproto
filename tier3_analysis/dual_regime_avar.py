"""Tier 3 Dual-Regime Long-Term Synthesis & IEEE Std 952-2020 Overlapping AVAR (EQ-24..EQ-30).

Implements:
  - EQ-24: 5-component IEEE Std 952-2020 Allan Variance model (Q, N, B, K, R)
  - EQ-25: Rate Random Walk (RRW) in Wiener & 1st-order Gauss-Markov AR(1) modes
  - EQ-26: Inter-tier Tier 1 -> Tier 3 phase-to-rate conversion (rad/s <-> deg/h)
  - EQ-28: Slow-scale 10-hour / 100 Hz (3.6e6 samples) rate time-series synthesis
  - EQ-29: O(N) vectorized IEEE Std 952 Overlapping Allan Variance sigma^2(T_m)
  - EQ-30: Dual-regime Fast (< 1 s) + Slow (>= 1 s) merge & < 5% overlap check on [0.1, 5] s
  - Relative-weighted NNLS (WLS) 5-parameter recovery (Q_hat, N_hat, B_hat, K_hat, R_hat)

CLI Contract (IFOG-SIM-SPEC-004 Section 5.2):
    python3 tier3_analysis/dual_regime_avar.py --run data/run01/
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import nnls
from scipy.signal import lfilter

from tier1_offline.config_loader import (
    DEG_H_TO_RAD_S,
    RAD_S_TO_DEG_H,
    load_config,
)
from tier1_offline.shupe_thermal import read_shupe_lut
from tier3_analysis.binary_io import read_sim_records

# Unit conversion factors between SI (rad, s) and IEEE Std 952 inertial units (deg, h)
RAD_TO_ARCSEC: float = (180.0 / math.pi) * 3600.0
RAD_S_RT_S_TO_DEG_RT_H: float = (180.0 / math.pi) * 60.0
RAD_S32_TO_DEG_H32: float = (180.0 / math.pi) * (3600.0 ** 1.5)
RAD_S2_TO_DEG_H2: float = (180.0 / math.pi) * (3600.0 ** 2)


def ieee952_avar_model(
    T_s: np.ndarray,
    Q_rad: float,
    N_rad_per_rt_s: float,
    B_rad_per_s: float,
    K_rad_per_s32: float,
    R_rad_per_s2: float,
) -> np.ndarray:
    """Evaluate IEEE Std 952-2020 5-component Allan variance sigma^2(T) in SI units (EQ-24)."""
    T = np.asarray(T_s, dtype=np.float64)
    return (
        3.0 * (Q_rad ** 2) / (T ** 2)
        + (N_rad_per_rt_s ** 2) / T
        + (2.0 * math.log(2.0) / math.pi) * (B_rad_per_s ** 2)
        + ((K_rad_per_s32 ** 2) * T) / 3.0
        + ((R_rad_per_s2 ** 2) * (T ** 2)) / 2.0
    )


def overlapping_avar(
    omega_rad_s: np.ndarray,
    dt_s: float,
    m_values: np.ndarray | list[int] | None = None,
    n_points: int = 48,
    angle_lsb_rad: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute IEEE Std 952 Overlapping Allan Variance (EQ-29) in vectorized O(N).

        sigma^2(T_m) = 1 / (2 (N - 2m) T_m^2) * sum_{j=1}^{N-2m} (theta_{j+2m} - 2 theta_{j+m} + theta_j)^2

    If ``angle_lsb_rad > 0``, quantizes integrated angle readout theta_j to ``angle_lsb_rad``
    (IEEE Std 952 Annex C quantized angle readout yielding Q = angle_lsb_rad / sqrt(12)).
    """
    omega = np.asarray(omega_rad_s, dtype=np.float64)
    n_samples = len(omega)
    max_m = (n_samples - 1) // 2
    if max_m < 1:
        raise ValueError("Need at least 3 samples to compute Overlapping AVAR")

    if m_values is None:
        raw_m = np.unique(
            np.round(np.geomspace(1, max_m, num=n_points)).astype(np.int64)
        )
        m_arr = raw_m[(raw_m >= 1) & (raw_m <= max_m)]
    else:
        m_arr = np.asarray(m_values, dtype=np.int64)
        m_arr = m_arr[(m_arr >= 1) & (m_arr <= max_m)]

    # Integrated angle theta_j with theta_0 = 0
    theta = np.empty(n_samples + 1, dtype=np.float64)
    theta[0] = 0.0
    np.cumsum(omega * dt_s, out=theta[1:])
    if angle_lsb_rad > 0.0:
        theta = np.round(theta / angle_lsb_rad) * angle_lsb_rad

    taus = m_arr.astype(np.float64) * dt_s
    avar = np.empty(len(m_arr), dtype=np.float64)
    for idx, m in enumerate(m_arr):
        m_int = int(m)
        diff = theta[2 * m_int :] - 2.0 * theta[m_int:-m_int] + theta[:-2 * m_int]
        tm = taus[idx]
        avar[idx] = float(np.mean(diff * diff)) / (2.0 * tm * tm)

    return taus, np.sqrt(np.maximum(avar, 0.0))


def phase_to_rate_rad_s(phase_rad: np.ndarray | float, k_opt: float) -> np.ndarray | float:
    """Convert non-reciprocal optical phase [rad] to equivalent rate [rad/s] (EQ-26)."""
    return phase_rad / k_opt


def rate_rad_s_to_deg_h(rate_rad_s: np.ndarray | float) -> np.ndarray | float:
    """Convert angular rate from rad/s to deg/h (EQ-26: x 206264.806247)."""
    return rate_rad_s * RAD_S_TO_DEG_H


def generate_rrw_series(
    n_samples: int,
    dt_s: float,
    K_rad_per_s32: float,
    rng: np.random.Generator,
    mode: str = "wiener",
    T_c_s: float = 10000.0,
) -> np.ndarray:
    """Generate Rate Random Walk series in Wiener or 1st-order Gauss-Markov AR(1) mode (EQ-25)."""
    if K_rad_per_s32 <= 0.0:
        return np.zeros(n_samples, dtype=np.float64)
    w = rng.standard_normal(n_samples)
    if mode == "wiener":
        return np.cumsum(K_rad_per_s32 * math.sqrt(dt_s) * w)
    if mode == "gauss_markov":
        phi = math.exp(-dt_s / T_c_s)
        sigma_gm = K_rad_per_s32 * math.sqrt(T_c_s / 2.0)
        scale = sigma_gm * math.sqrt(max(0.0, 1.0 - phi * phi))
        zi_scale = sigma_gm * phi
        x0 = rng.standard_normal() * zi_scale
        out, _ = lfilter([scale], [1.0, -phi], w, zi=[x0])
        return np.asarray(out, dtype=np.float64)
    raise ValueError(f"Unsupported rrw_mode: {mode}")


def generate_calibrated_pink_series(
    n_samples: int,
    dt_s: float,
    B_rad_per_s: float,
    rng: np.random.Generator,
    n_poles: int = 12,
    f_min_Hz: float = 1.0e-5,
    f_max_Hz: float = 40.0,
) -> np.ndarray:
    """Generate calibrated 1/f flicker rate noise whose IEEE 952 ADEV plateau equals sqrt(2 ln 2 / pi) * B."""
    if B_rad_per_s <= 0.0:
        return np.zeros(n_samples, dtype=np.float64)
    ratio = (f_max_Hz / f_min_Hz) ** (1.0 / float(n_poles - 1))
    total = np.zeros(n_samples, dtype=np.float64)
    for p in range(n_poles):
        fp = f_min_Hz * (ratio ** p)
        ap = math.exp(-2.0 * math.pi * fp * dt_s)
        bp = math.sqrt(max(0.0, 1.0 - ap * ap))
        w = rng.standard_normal(n_samples)
        z0 = rng.standard_normal() * ap
        branch, _ = lfilter([bp], [1.0, -ap], w, zi=[z0])
        total += branch
    gain = B_rad_per_s * math.sqrt(math.log(ratio) / math.pi)
    return total * gain


def extract_fast_qn_arw(
    taus_fast: np.ndarray,
    adev_fast: np.ndarray,
    t_fit_min: float = 1.5e-3,
    t_arw_min: float = 0.08,
    t_arw_max: float = 3.0,
) -> tuple[float, float]:
    """Fit short-tau Quantization (Q_fast, slope -1) and ARW (N_fast, slope -1/2) above loop rolloff."""
    mask = (taus_fast >= t_fit_min) & (taus_fast <= t_arw_max) & (adev_fast > 0.0)
    t_sub = taus_fast[mask]
    s2 = adev_fast[mask] ** 2
    inv_s2 = 1.0 / np.maximum(s2, 1e-30)
    A = np.column_stack([3.0 / (t_sub ** 2), 1.0 / t_sub]) * inv_s2[:, None]
    coeffs, _ = nnls(A, np.ones_like(s2))
    q_hat = math.sqrt(max(0.0, float(coeffs[0])))
    n_hat = math.sqrt(max(0.0, float(coeffs[1])))

    arw_mask = (taus_fast >= t_arw_min) & (taus_fast <= t_arw_max) & (adev_fast > 0.0)
    if np.count_nonzero(arw_mask) >= 2:
        t_arw = taus_fast[arw_mask]
        s2_arw = np.maximum(adev_fast[arw_mask] ** 2 - 3.0 * (q_hat ** 2) / (t_arw ** 2), 0.0)
        n_hat = float(math.sqrt(float(np.median(s2_arw * t_arw))))
    return q_hat, n_hat


def fit_5region_wls(
    taus_s: np.ndarray,
    adev_rad_s: np.ndarray,
    t_min_fit: float = 0.0,
) -> dict[str, float]:
    """Recover IEEE Std 952-2020 (Q, N, B, K, R) via relative-weighted NNLS on sigma^2(T) (EQ-24)."""
    T = np.asarray(taus_s, dtype=np.float64)
    s2 = np.asarray(adev_rad_s, dtype=np.float64) ** 2
    mask = (T >= t_min_fit) & (T > 0.0) & (s2 > 0.0)
    T = T[mask]
    s2 = s2[mask]

    basis = np.column_stack(
        [
            3.0 / (T ** 2),
            1.0 / T,
            np.full_like(T, (2.0 * math.log(2.0)) / math.pi),
            T / 3.0,
            (T ** 2) / 2.0,
        ]
    )
    inv_s2 = 1.0 / s2
    coeffs, _ = nnls(basis * inv_s2[:, None], np.ones_like(s2))

    q_rad = math.sqrt(max(0.0, float(coeffs[0])))
    n_si = math.sqrt(max(0.0, float(coeffs[1])))
    b_si = math.sqrt(max(0.0, float(coeffs[2])))
    k_si = math.sqrt(max(0.0, float(coeffs[3])))
    r_si = math.sqrt(max(0.0, float(coeffs[4])))

    return {
        "Q_rad": q_rad,
        "N_rad_per_rt_s": n_si,
        "B_rad_per_s": b_si,
        "K_rad_per_s32": k_si,
        "R_rad_per_s2": r_si,
        "Q_arcsec": q_rad * RAD_TO_ARCSEC,
        "N_deg_per_rt_h": n_si * RAD_S_RT_S_TO_DEG_RT_H,
        "B_deg_per_h": b_si * RAD_S_TO_DEG_H,
        "K_deg_per_rt_h3": k_si * RAD_S32_TO_DEG_H32,
        "R_deg_per_h2": r_si * RAD_S2_TO_DEG_H2,
    }


def compute_residual_tier3_bi(b_total_rad_s: float, b_t2_meas_rad_s: float) -> float:
    """Compute residual Tier-3 mechanical Bias Instability preventing double-counting (EQ-52).

        B_T3,mech = sqrt(max(0, B_total^2 - B_T2,meas^2))
    """
    return math.sqrt(max(0.0, (b_total_rad_s ** 2) - (b_t2_meas_rad_s ** 2)))


class DualRegimeStitcher:
    """SPEC-007 Dual-Regime AVAR Stitcher with anti-double-counting back-reflection BI subtraction."""

    def __init__(self, splice_t_s: float = 1.0) -> None:
        self.splice_t_s = float(splice_t_s)

    @staticmethod
    def residual_mechanical_bi(b_total_rad_s: float, b_t2_meas_rad_s: float) -> float:
        """Return residual Tier-3 BI after subtracting Tier-2 back-reflection BI in quadrature (EQ-52)."""
        return compute_residual_tier3_bi(b_total_rad_s, b_t2_meas_rad_s)

    def stitch(
        self,
        taus_fast: np.ndarray,
        adev_fast: np.ndarray,
        taus_slow: np.ndarray,
        adev_slow: np.ndarray,
    ) -> dict[str, Any]:
        """Verify [0.1, 5.0] s overlap continuity and merge Fast (< splice_t_s) + Slow (>= splice_t_s)."""
        overlap = check_overlap_continuity(taus_fast, adev_fast, taus_slow, adev_slow)
        taus_merged, adev_merged = merge_dual_regime_avar(
            taus_fast, adev_fast, taus_slow, adev_slow, splice_t_s=self.splice_t_s
        )
        return {
            "taus_merged": taus_merged,
            "adev_merged": adev_merged,
            "overlap_check": overlap,
        }


def synthesize_slow_scale_series(
    cfg: dict[str, Any],
    phys_params: dict[str, Any],
    n_fast_rad_per_rt_s: float,
    k_matrix: dict[str, Any] | None = None,
    shupe_lut: tuple[np.ndarray, np.ndarray] | None = None,
    b_t2_meas_rad_s: float = 0.0,
) -> tuple[np.ndarray, float, dict[str, float]]:
    """Synthesize slow-scale rate series Omega_slow[i] over configured hours at f_dec (EQ-28, EQ-52)."""
    ss = cfg["slow_scale"]
    f_dec = float(ss["f_dec_Hz"])
    dt_slow = 1.0 / f_dec
    duration_s = float(ss["duration_hours"]) * 3600.0
    n_slow = int(round(duration_s * f_dec))
    seed = int(cfg["meta"]["seed"]) + 95200
    rng = np.random.default_rng(seed)

    k_opt = float(phys_params["K_opt_rad_per_rad_s"])
    t_slow = np.arange(n_slow, dtype=np.float64) * dt_slow

    # 1. White ARW term calibrated directly from Fast-Scale N_hat (EQ-28 term 1)
    omega_arw = (n_fast_rad_per_rt_s / math.sqrt(dt_slow)) * rng.standard_normal(n_slow)

    # 2. Electronic 1/f leakage + residual mechanical BI (EQ-28 term 2, EQ-52 anti-double-counting)
    b_cfg_rad_s = float(ss["B_flicker_deg_per_h"]) * DEG_H_TO_RAD_S
    if k_matrix is not None:
        k_vec = np.asarray(k_matrix["K_node_unit_vector"], dtype=np.float64)
        sig_nodes = np.array(
            [
                float(cfg["noise"]["sigma_pink_tia_V"]),
                float(cfg["noise"]["sigma_pink_dac_rel"]),
                float(cfg["noise"]["sigma_pink_xtalk_rel"]),
            ],
            dtype=np.float64,
        )
        # Combined RMS electronic leakage BI scale (rad/s)
        b_total_rad_s = float(np.hypot(b_cfg_rad_s, np.linalg.norm(k_vec * sig_nodes)))
    else:
        b_total_rad_s = b_cfg_rad_s

    b_elec_rad_s = compute_residual_tier3_bi(b_total_rad_s, b_t2_meas_rad_s)

    omega_pink = generate_calibrated_pink_series(
        n_samples=n_slow, dt_s=dt_slow, B_rad_per_s=b_elec_rad_s, rng=rng
    )

    # 3. Tier-1 Polarization drift Omega_pol[i] = phi_pol(t_i) / K_opt (EQ-26)
    phi_pol_0 = float(phys_params["phi_pol_rad"]) if cfg["ablation_flags"]["en_pol_error"] else 0.0
    phi_pol_drift = float(cfg["optics"].get("phi_pol_drift_rad_per_s", 0.0))
    omega_pol = phase_to_rate_rad_s(phi_pol_0 + phi_pol_drift * t_slow, k_opt)

    # 4. Rate Random Walk Omega_RRW[i] (EQ-25)
    k_rrw_si = float(ss["K_rrw_deg_per_rt_h3"]) / RAD_S32_TO_DEG_H32
    omega_rrw = generate_rrw_series(
        n_samples=n_slow,
        dt_s=dt_slow,
        K_rad_per_s32=k_rrw_si,
        rng=rng,
        mode=str(ss["rrw_mode"]),
        T_c_s=float(ss["T_c_s"]),
    )

    # 5. Thermal Shupe + deterministic Rate Ramp Omega_Shupe[i] (EQ-26)
    r_cfg_si = float(ss["R_ramp_deg_per_h2"]) / RAD_S2_TO_DEG_H2
    omega_shupe = r_cfg_si * t_slow
    if shupe_lut is not None and cfg["ablation_flags"]["en_shupe"]:
        lut_t, lut_phi = shupe_lut
        phi_shupe_t = np.interp(t_slow, lut_t, lut_phi)
        omega_shupe = omega_shupe + phase_to_rate_rad_s(phi_shupe_t, k_opt)

    # 6. Faraday drift Omega_Faraday[i] (EQ-26)
    if cfg["ablation_flags"]["en_faraday"]:
        mag = cfg["magneto_optic"]
        phi_far = float(mag["verdet_rad_per_Tm"]) * float(mag["B_ext_T"]) * float(mag["effective_loop_m"])
        omega_far = float(phase_to_rate_rad_s(phi_far, k_opt))
    else:
        omega_far = 0.0

    omega_slow = omega_arw + omega_pink + omega_pol + omega_rrw + omega_shupe + omega_far
    truth_params = {
        "N_rad_per_rt_s": n_fast_rad_per_rt_s,
        "B_rad_per_s": b_elec_rad_s,
        "K_rad_per_s32": k_rrw_si,
        "R_rad_per_s2": r_cfg_si,
    }
    return omega_slow, dt_slow, truth_params


def check_overlap_continuity(
    taus_fast: np.ndarray,
    adev_fast: np.ndarray,
    taus_slow: np.ndarray,
    adev_slow: np.ndarray,
    t_min: float = 0.1,
    t_max: float = 5.0,
) -> dict[str, float | bool]:
    """Verify Dual-Regime overlap continuity max |sigma_fast - sigma_slow| / sigma_fast < 5% (EQ-30)."""
    lo = max(t_min, float(taus_fast[0]), float(taus_slow[0]))
    hi = min(t_max, float(taus_fast[-1]), float(taus_slow[-1]))
    if hi <= lo:
        raise ValueError(f"Empty overlap window between Fast [{taus_fast[0]}, {taus_fast[-1]}] and Slow")

    grid = np.geomspace(lo, hi, num=20)
    log_fast = np.interp(
        np.log10(grid), np.log10(taus_fast), np.log10(np.maximum(adev_fast, 1e-30))
    )
    log_slow = np.interp(
        np.log10(grid), np.log10(taus_slow), np.log10(np.maximum(adev_slow, 1e-30))
    )
    sig_fast = 10.0 ** log_fast
    sig_slow = 10.0 ** log_slow
    rel_err = np.abs(sig_fast - sig_slow) / sig_fast
    max_rel_err = float(np.max(rel_err))
    return {
        "overlap_t_min_s": float(lo),
        "overlap_t_max_s": float(hi),
        "max_relative_mismatch": max_rel_err,
        "max_relative_mismatch_pct": 100.0 * max_rel_err,
        "continuity_pass_lt_5pct": bool(max_rel_err < 0.05),
    }


def merge_dual_regime_avar(
    taus_fast: np.ndarray,
    adev_fast: np.ndarray,
    taus_slow: np.ndarray,
    adev_slow: np.ndarray,
    splice_t_s: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Splice Fast-Scale (T_m < 1 s) and Slow-Scale (T_m >= 1 s) ADEV curves (EQ-30)."""
    mask_f = taus_fast < splice_t_s
    mask_s = taus_slow >= splice_t_s
    taus_merged = np.concatenate([taus_fast[mask_f], taus_slow[mask_s]])
    adev_merged = np.concatenate([adev_fast[mask_f], adev_slow[mask_s]])
    return taus_merged, adev_merged


def run_dual_regime_avar(
    run_dir: Path | str,
    cfg_path: Path | str | None = None,
    slow_ensemble: int = 1,
) -> dict[str, Any]:
    """Execute full Tier 3 Dual-Regime AVAR pipeline on a run directory.

    Supports both single-run ``sim_out.bin`` and Monte Carlo multi-seed Fast-Scale
    ensembles (``sim_out_*.bin``) plus ``slow_ensemble`` independent 10h Slow-Scale
    realizations averaged in Allan-variance space per IEEE Std 952-2020 Annex C.
    """
    rdir = Path(run_dir)
    if cfg_path is not None:
        cfg = load_config(cfg_path)
    elif (rdir / "cfg.json").exists():
        cfg = load_config(rdir / "cfg.json")
    else:
        default_cfg = Path(__file__).resolve().parent.parent / "configs" / "baseline_1km.json"
        cfg = load_config(default_cfg)

    with (rdir / "phys_params.json").open("r", encoding="utf-8") as fh:
        phys_params = json.load(fh)

    k_matrix = None
    if (rdir / "k_matrix.json").exists():
        with (rdir / "k_matrix.json").open("r", encoding="utf-8") as fh:
            k_matrix = json.load(fh)

    shupe_lut = None
    if (rdir / "shupe_lut.bin").exists():
        lt, lphi, _ = read_shupe_lut(rdir / "shupe_lut.bin")
        shupe_lut = (lt, lphi)

    # 1. Fast-Scale Overlapping AVAR from real Tier-2 sim_out.bin (or sim_out_*.bin ensemble)
    fast_bins = sorted(rdir.glob("sim_out_*.bin"))
    if not fast_bins:
        fast_bins = [rdir / "sim_out.bin"]

    k_opt = float(phys_params["K_opt_rad_per_rad_s"])
    angle_lsb_rad = (
        (2.0 * math.pi / (2 ** (int(cfg["adc_dac"]["N_dac_bits"]) + 11) * k_opt))
        if cfg["ablation_flags"]["en_quantization"]
        else 0.0
    )
    q_theory_rad = angle_lsb_rad / math.sqrt(12.0)

    taus_fast: np.ndarray | None = None
    avar_fast_acc: np.ndarray | None = None
    dt_fast = 0.0
    fast_duration_s = 0.0
    for bin_file in fast_bins:
        rec = read_sim_records(bin_file)
        t_fast = rec["t"]
        omega_fast = rec["omega_out"]
        dt_fast = float(np.median(np.diff(t_fast)))
        fast_duration_s = float(t_fast[-1] - t_fast[0])
        trim = min(len(omega_fast) // 10, max(100, int(round(0.02 / dt_fast))))
        tf, af = overlapping_avar(
            omega_fast[trim:], dt_fast, n_points=44, angle_lsb_rad=angle_lsb_rad
        )
        taus_fast = tf
        avar_fast_acc = (af ** 2) if avar_fast_acc is None else (avar_fast_acc + (af ** 2))

    assert taus_fast is not None and avar_fast_acc is not None
    adev_fast = np.sqrt(avar_fast_acc / float(len(fast_bins)))
    q_fast, n_fast = extract_fast_qn_arw(taus_fast, adev_fast, t_fit_min=1.5e-3)

    # 2. Slow-Scale 10-hour / 100 Hz synthesis + Overlapping AVAR (single or ensemble)
    base_seed = int(cfg["meta"]["seed"])
    taus_slow: np.ndarray | None = None
    avar_slow_acc: np.ndarray | None = None
    dt_slow = 0.0
    slow_n_samples = 0
    truth_slow: dict[str, float] = {}

    for ens_idx in range(max(1, slow_ensemble)):
        ens_cfg = cfg if ens_idx == 0 else {**cfg, "meta": {**cfg["meta"], "seed": base_seed + ens_idx * 1009}}
        omega_slow, dt_slow, truth_slow = synthesize_slow_scale_series(
            cfg=ens_cfg,
            phys_params=phys_params,
            n_fast_rad_per_rt_s=n_fast,
            k_matrix=k_matrix,
            shupe_lut=shupe_lut,
        )
        slow_n_samples = int(len(omega_slow))
        ts, as_cur = overlapping_avar(
            omega_slow, dt_slow, n_points=52, angle_lsb_rad=angle_lsb_rad
        )
        taus_slow = ts
        avar_slow_acc = (as_cur ** 2) if avar_slow_acc is None else (avar_slow_acc + (as_cur ** 2))

    assert taus_slow is not None and avar_slow_acc is not None
    adev_slow = np.sqrt(avar_slow_acc / float(max(1, slow_ensemble)))

    # 3. Overlap continuity check on [0.1, 5.0] s (EQ-30)
    overlap = check_overlap_continuity(taus_fast, adev_fast, taus_slow, adev_slow)

    # 4. Merge curves & WLS 5-region IEEE 952 fit above closed-loop rolloff (EQ-24)
    taus_merged, adev_merged = merge_dual_regime_avar(
        taus_fast, adev_fast, taus_slow, adev_slow, splice_t_s=1.0
    )
    t_max_fit = float(cfg["slow_scale"]["duration_hours"]) * 3600.0 * 0.42
    fit_mask = taus_merged <= t_max_fit
    fitted = fit_5region_wls(taus_merged[fit_mask], adev_merged[fit_mask], t_min_fit=1.5e-3)

    # Persist outputs for viz/plot_avar_5regions.py and viz/export_report.py
    np.savez(
        rdir / "avar_curve.npz",
        taus_fast=taus_fast,
        adev_fast_rad_s=adev_fast,
        taus_slow=taus_slow,
        adev_slow_rad_s=adev_slow,
        taus_merged=taus_merged,
        adev_merged_rad_s=adev_merged,
        adev_fast_deg_h=rate_rad_s_to_deg_h(adev_fast),
        adev_slow_deg_h=rate_rad_s_to_deg_h(adev_slow),
        adev_merged_deg_h=rate_rad_s_to_deg_h(adev_merged),
    )

    metrics: dict[str, Any] = {
        "spec_id": "IFOG-SIM-SPEC-004",
        "fast_dt_s": dt_fast,
        "fast_duration_s": fast_duration_s,
        "fast_ensemble_count": len(fast_bins),
        "slow_dt_s": dt_slow,
        "slow_n_samples": slow_n_samples,
        "slow_ensemble_count": max(1, slow_ensemble),
        "Q_fast_rad": q_fast,
        "Q_theory_rad": q_theory_rad,
        "N_fast_rad_per_rt_s": n_fast,
        "N_fast_deg_per_rt_h": n_fast * RAD_S_RT_S_TO_DEG_RT_H,
        "overlap_check": overlap,
        "fitted_ieee952": fitted,
        "slow_synthesis_truth": {
            "Q_arcsec": q_theory_rad * RAD_TO_ARCSEC,
            "N_deg_per_rt_h": truth_slow["N_rad_per_rt_s"] * RAD_S_RT_S_TO_DEG_RT_H,
            "B_deg_per_h": truth_slow["B_rad_per_s"] * RAD_S_TO_DEG_H,
            "K_deg_per_rt_h3": truth_slow["K_rad_per_s32"] * RAD_S32_TO_DEG_H32,
            "R_deg_per_h2": truth_slow["R_rad_per_s2"] * RAD_S2_TO_DEG_H2,
        },
    }
    with (rdir / "avar_metrics.json").open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    return metrics


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Tier 3 Dual-Regime AVAR synthesis and 5-region fitting."""
    parser = argparse.ArgumentParser(
        description="Tier 3 Dual-Regime Overlapping AVAR Synthesis & IEEE 952 WLS Fit"
    )
    parser.add_argument("--run", required=True, help="Run directory containing sim_out.bin & phys_params.json")
    parser.add_argument("--cfg", default=None, help="Optional explicit config JSON path")
    parser.add_argument("--slow-ensemble", type=int, default=1, help="Number of Slow-Scale realizations to average")
    args = parser.parse_args(argv)

    run_dual_regime_avar(args.run, cfg_path=args.cfg, slow_ensemble=args.slow_ensemble)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
