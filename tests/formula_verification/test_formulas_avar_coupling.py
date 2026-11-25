"""Per-formula verification suite for IEEE 952 AVAR & Inter-Tier Coupling (EQ-24 .. EQ-30)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import RAD_S_TO_DEG_H, deep_merge, load_config
from tier1_offline.jones_spectral import solve_tier1_optics
from tier3_analysis.dual_regime_avar import (
    RAD_S2_TO_DEG_H2,
    RAD_S32_TO_DEG_H32,
    RAD_S_RT_S_TO_DEG_RT_H,
    check_overlap_continuity,
    fit_5region_wls,
    generate_rrw_series,
    ieee952_avar_model,
    merge_dual_regime_avar,
    overlapping_avar,
    phase_to_rate_rad_s,
    rate_rad_s_to_deg_h,
    synthesize_slow_scale_series,
)
from tier3_analysis.extract_k_matrix import extract_k_matrix

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASE_CFG_PATH = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.formula
def test_eq24_ieee952_five_component_avar_and_wls_recovery() -> None:
    """EQ-24 (Sec 3.4 Eq. 33): Exact 5-component AVAR curve & exact WLS NNLS recovery of (Q,N,B,K,R)."""
    taus = np.geomspace(1e-4, 2e4, 80)
    q_true = 2.0e-7
    n_true = 1.5e-7
    b_true = 2.0e-8
    k_true = 5.0e-10
    r_true = 1.0e-11

    avar = ieee952_avar_model(taus, q_true, n_true, b_true, k_true, r_true)
    # Check exact analytical formula point-by-point
    expected = (
        3.0 * q_true ** 2 / (taus ** 2)
        + n_true ** 2 / taus
        + (2.0 * math.log(2.0) / math.pi) * (b_true ** 2)
        + (k_true ** 2) * taus / 3.0
        + (r_true ** 2) * (taus ** 2) / 2.0
    )
    np.testing.assert_allclose(avar, expected, rtol=1e-14)

    # Verify WLS NNLS recovers all 5 parameters cleanly to < 1e-6 relative error on noiseless curve
    fit = fit_5region_wls(taus, np.sqrt(avar))
    assert math.isclose(fit["Q_rad"], q_true, rel_tol=1e-5)
    assert math.isclose(fit["N_rad_per_rt_s"], n_true, rel_tol=1e-5)
    assert math.isclose(fit["B_rad_per_s"], b_true, rel_tol=1e-5)
    assert math.isclose(fit["K_rad_per_s32"], k_true, rel_tol=1e-5)
    assert math.isclose(fit["R_rad_per_s2"], r_true, rel_tol=1e-5)


@pytest.mark.formula
def test_eq25_rrw_wiener_and_gauss_markov_models() -> None:
    """EQ-25 (Sec 3.4 Eq. 34): Wiener RRW (+1/2 slope) & 1st-order Gauss-Markov convergence for T << T_c."""
    dt = 0.1
    n_samples = 200_000  # 20,000 s
    k_true = 1.0e-4

    # Wiener mode: sigma(T) = K * sqrt(T / 3)
    rng_w = np.random.default_rng(1001)
    omega_w = generate_rrw_series(n_samples, dt, k_true, rng_w, mode="wiener")
    taus_w, adev_w = overlapping_avar(omega_w, dt, m_values=[10, 50, 200, 1000])
    theory_w = k_true * np.sqrt(taus_w / 3.0)
    rel_err_w = np.abs(adev_w - theory_w) / theory_w
    assert float(np.median(rel_err_w)) < 0.10

    # Gauss-Markov mode: stationary variance == sigma_GM^2 = K^2 * T_c / 2 & matches Wiener for T << T_c
    t_c = 500.0
    rng_gm = np.random.default_rng(2002)
    omega_gm = generate_rrw_series(n_samples, dt, k_true, rng_gm, mode="gauss_markov", T_c_s=t_c)
    sigma_gm_theory = k_true * math.sqrt(t_c / 2.0)
    assert abs(float(np.std(omega_gm)) - sigma_gm_theory) / sigma_gm_theory < 0.15

    taus_gm, adev_gm = overlapping_avar(omega_gm, dt, m_values=[10, 50])
    theory_short = k_true * np.sqrt(taus_gm / 3.0)
    assert float(np.max(np.abs(adev_gm - theory_short) / theory_short)) < 0.15


@pytest.mark.formula
def test_eq26_inter_tier_phase_to_rate_and_unit_conversions() -> None:
    """EQ-26 (Sec 4.1 Eq. 35): Omega = Delta_phi / K_opt and exact rad/s -> deg/h factor 206264.806."""
    assert math.isclose(RAD_S_TO_DEG_H, 206264.80624709636, rel_tol=1e-12)
    k_opt = 1.3521580786785043
    phi = 6.5554e-9
    omega_rad_s = phase_to_rate_rad_s(phi, k_opt)
    omega_deg_h = rate_rad_s_to_deg_h(omega_rad_s)
    assert math.isclose(float(omega_deg_h), 0.001, rel_tol=1e-3)


@pytest.mark.formula
def test_eq27_leakage_gain_matrix_k_100hz_fft(tmp_path: Path) -> None:
    """EQ-27 (Sec 4.2 Eq. 36): 100 Hz sinusoidal FFT extraction of K = [K_TIA, K_DAC, K_xtalk] < 2% repeatability."""
    cfg = load_config(BASE_CFG_PATH)
    phys = solve_tier1_optics(cfg)
    phys_p = tmp_path / "phys.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")

    k1 = extract_k_matrix(SIM_BIN, cfg, phys_p, tmp_path / "k1", freq_Hz=100.0, duration_s=0.1)
    k2 = extract_k_matrix(SIM_BIN, cfg, phys_p, tmp_path / "k2", freq_Hz=100.0, duration_s=0.1)

    v1 = np.asarray(k1["K_physical_vector"], dtype=np.float64)
    v2 = np.asarray(k2["K_physical_vector"], dtype=np.float64)
    assert np.all(np.isfinite(v1))
    assert v1[2] > 0.0  # Resistive crosstalk leakage path is strictly non-zero
    rel_diff = np.abs(v1 - v2) / np.maximum(np.abs(v1), 1e-15)
    assert float(np.max(rel_diff)) < 0.02


@pytest.mark.formula
def test_eq28_slow_scale_synthesis_composition() -> None:
    """EQ-28 (Sec 4.3 Eq. 37): Slow-scale superposition of ARW, pink, pol, RRW, Shupe, Faraday."""
    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "ablation_flags": {"en_pol_error": True, "en_shupe": True, "en_faraday": True},
            "magneto_optic": {"verdet_rad_per_Tm": 0.6, "B_ext_T": 1e-5, "effective_loop_m": 0.5},
            "slow_scale": {
                "f_dec_Hz": 100.0,
                "duration_hours": 0.25,
                "rrw_mode": "wiener",
                "K_rrw_deg_per_rt_h3": 0.01,
                "B_flicker_deg_per_h": 0.005,
                "R_ramp_deg_per_h2": 0.02,
            },
        },
    )
    phys = solve_tier1_optics(cfg)
    lut_t = np.array([0.0, 900.0])
    lut_phi = np.array([0.0, 1.0e-7])
    k_mat = {"K_node_unit_vector": [1e-4, 1e-4, 1e-4]}
    n_fast = 1.0e-7

    omega_slow, dt_slow, truth = synthesize_slow_scale_series(
        cfg=cfg, phys_params=phys, n_fast_rad_per_rt_s=n_fast, k_matrix=k_mat, shupe_lut=(lut_t, lut_phi)
    )
    assert len(omega_slow) == 90_000
    assert math.isclose(dt_slow, 0.01, rel_tol=1e-12)
    assert truth["N_rad_per_rt_s"] == n_fast
    assert truth["R_rad_per_s2"] > 0.0
    assert np.all(np.isfinite(omega_slow))


@pytest.mark.formula
def test_eq29_overlapping_avar_exact_against_naive_formula() -> None:
    """EQ-29 (Sec 4.3 Eq. 38): Vectorized overlapping_avar matches literal IEEE 952 summation & white/ramp analytic limits."""
    # Exact match with literal summation formula
    rng = np.random.default_rng(7)
    omega = rng.standard_normal(500) * 0.01
    dt = 0.02
    taus, adev = overlapping_avar(omega, dt, m_values=[1, 5, 20])
    theta = np.concatenate([[0.0], np.cumsum(omega) * dt])
    for idx, m in enumerate([1, 5, 20]):
        tm = m * dt
        s = 0.0
        count = len(theta) - 2 * m
        for j in range(count):
            d = theta[j + 2 * m] - 2.0 * theta[j + m] + theta[j]
            s += d * d
        expected_adev = math.sqrt(s / (2.0 * count * tm * tm))
        assert math.isclose(float(adev[idx]), expected_adev, rel_tol=1e-12)

    # Exact Rate Ramp analytic check: Omega(t) = R * t -> sigma(T) == R * T / sqrt(2)
    r_slope = 0.05
    t_ramp = np.arange(2000) * 0.01
    taus_r, adev_r = overlapping_avar(r_slope * t_ramp, 0.01, m_values=[10, 50, 200])
    np.testing.assert_allclose(adev_r, r_slope * taus_r / math.sqrt(2.0), rtol=1e-10)


@pytest.mark.formula
def test_eq30_dual_regime_overlap_continuity_check() -> None:
    """EQ-30 (Sec 4.3 Eq. 39): Dual-regime splicing & < 5% continuity criterion on T_m in [0.1, 5] s."""
    taus_fast = np.geomspace(1e-3, 10.0, 40)
    taus_slow = np.geomspace(0.05, 1e4, 50)
    n_val = 1.2e-7
    adev_fast = n_val / np.sqrt(taus_fast)
    adev_slow_good = (n_val * 1.02) / np.sqrt(taus_slow)  # 2% mismatch -> PASS
    adev_slow_bad = (n_val * 1.12) / np.sqrt(taus_slow)   # 12% mismatch -> FAIL

    ok = check_overlap_continuity(taus_fast, adev_fast, taus_slow, adev_slow_good)
    assert ok["continuity_pass_lt_5pct"] is True
    assert abs(float(ok["max_relative_mismatch_pct"]) - 2.0) < 0.2

    bad = check_overlap_continuity(taus_fast, adev_fast, taus_slow, adev_slow_bad)
    assert bad["continuity_pass_lt_5pct"] is False
    assert float(bad["max_relative_mismatch_pct"]) > 10.0

    tm, am = merge_dual_regime_avar(taus_fast, adev_fast, taus_slow, adev_slow_good, splice_t_s=1.0)
    assert np.all(np.diff(tm) > 0.0)
    assert len(tm) == len(am)
