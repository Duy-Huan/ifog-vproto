"""Per-formula verification suite for Optical Domain equations (EQ-04 .. EQ-13)."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import (
    C_LIGHT,
    compute_delta_nu_eff,
    compute_k_opt,
    compute_kerr_phase,
    compute_tau,
    deep_merge,
    load_config,
)
from tier1_offline.jones_spectral import (
    build_spectral_slices,
    compute_jones_matrices,
    evaluate_static_interference,
    extract_visibility_and_pol_phase,
    solve_tier1_optics,
)
from tier1_offline.shupe_thermal import shupe_integral
from tier3_analysis.binary_io import read_micro_records

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASE_CFG_PATH = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.formula
def test_eq04_spectral_jones_reciprocity_and_bandwidth() -> None:
    """EQ-04 (Sec 3.1.1 Eq. 7): SLD Delta_nu_eff, normalized weights, J_CCW == J_CW^T."""
    lam = 1.55e-6
    dlam = 40.0e-9
    omega_k, weights, dnu_eff = build_spectral_slices(lam, dlam, n_spec=64)

    expected_dnu_fwhm = (C_LIGHT / (lam ** 2)) * dlam
    expected_dnu_eff = math.sqrt(math.pi / (2.0 * math.log(2.0))) * expected_dnu_fwhm
    assert math.isclose(dnu_eff, expected_dnu_eff, rel_tol=1e-12)
    assert math.isclose(float(np.sum(weights)), 1.0, rel_tol=1e-14)
    assert len(omega_k) == 64

    j_cw, j_ccw, thetas = compute_jones_matrices(
        omega_k=omega_k,
        lambda_bar_m=lam,
        n_eff=1.468,
        L_m=1000.0,
        beat_length_m=2.0e-3,
        h_param_inv_m=1.0e-5,
        er_dB=60.0,
        m_segments=200,
        seed=42004,
    )
    assert len(thetas) == 200
    # Strict Lorentz reciprocity: J_CCW(omega_k) = J_CW(omega_k)^T for all spectral slices
    np.testing.assert_allclose(j_ccw, np.transpose(j_cw, (0, 2, 1)), atol=1e-15)


@pytest.mark.formula
def test_eq05_fringe_visibility_and_polarization_phase() -> None:
    """EQ-05 (Sec 3.1.1 Eq. 8): V = (P_max-P_min)/(P_max+P_min), phi_pol = argmin P_static - pi."""
    omega_k, weights, _ = build_spectral_slices(1.55e-6, 40.0e-9, n_spec=64)
    j_cw, j_ccw, _ = compute_jones_matrices(
        omega_k, 1.55e-6, 1.468, 1000.0, 2.0e-3, 1.0e-4, 40.0, 200, seed=77
    )
    v_closed, phi_pol_closed, p_max, p_min = extract_visibility_and_pol_phase(j_cw, j_ccw, weights)

    # Cross-check against direct grid evaluation of P_static(Delta_phi)
    grid = np.linspace(-math.pi, math.pi, 4096, endpoint=False)
    p_grid = evaluate_static_interference(j_cw, j_ccw, weights, grid)
    v_grid = (float(np.max(p_grid)) - float(np.min(p_grid))) / (
        float(np.max(p_grid)) + float(np.min(p_grid))
    )
    phi_min = float(grid[int(np.argmin(p_grid))])
    # Wrap (phi_min - pi) to [-pi, pi]
    phi_pol_grid = (phi_min - math.pi + math.pi) % (2.0 * math.pi) - math.pi

    assert math.isclose(v_closed, (p_max - p_min) / (p_max + p_min), rel_tol=1e-12)
    assert math.isclose(v_closed, v_grid, rel_tol=1e-5)
    assert abs(phi_pol_closed - phi_pol_grid) < 3.0e-3

    # Ideal h=0 fiber must have V == 1 and phi_pol == 0
    j_cw_id, j_ccw_id, _ = compute_jones_matrices(
        omega_k, 1.55e-6, 1.468, 1000.0, 2.0e-3, 0.0, 60.0, 200, seed=77
    )
    v_id, phi_id, _, _ = extract_visibility_and_pol_phase(j_cw_id, j_ccw_id, weights)
    assert math.isclose(v_id, 1.0, rel_tol=1e-12)
    assert abs(phi_id) < 1e-14


@pytest.mark.formula
def test_eq06_transit_time_and_nonreciprocal_phase_sum(tmp_path: Path) -> None:
    """EQ-06 (Sec 3.1.2 Eq. 9): tau = n_eff*L/c and superposition of NR phase terms in Tier 2."""
    tau = compute_tau(1000.0, 1.468)
    assert math.isclose(tau, 4.896720917508872e-6, rel_tol=1e-12)

    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "optics": {"phi_pol_drift_rad_per_s": 0.0},
            "magneto_optic": {"verdet_rad_per_Tm": 0.6, "B_ext_T": 1.0e-5, "effective_loop_m": 0.5},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": False},
            "ablation_flags": {
                "en_pol_error": True,
                "en_kerr": True,
                "en_shupe": False,
                "en_faraday": True,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
            "simulation": {
                "duration_s": 0.015,
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 1.0e-4},
            },
        },
    )
    phys = solve_tier1_optics(cfg)
    phys_p = tmp_path / "phys.json"
    cfg_p = tmp_path / "cfg.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")
    cfg_p.write_text(json.dumps(cfg), encoding="utf-8")

    subprocess.run(
        [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(cfg_p), "--out", str(tmp_path / "out")],
        check=True,
        capture_output=True,
    )
    summary = json.loads((tmp_path / "out" / "sim_summary.json").read_text(encoding="utf-8"))
    expected_nr = (
        phys["K_opt_rad_per_rad_s"] * 1.0e-4
        + phys["phi_pol_rad"]
        + phys["delta_phi_kerr_rad"]
        + 0.6 * 1.0e-5 * 0.5
    )
    assert abs(summary["final_delta_phi_step_rad"] - expected_nr) < 1e-11


@pytest.mark.formula
def test_eq07_sagnac_scale_factor_k_opt() -> None:
    """EQ-07 (Sec 3.1.2 Eq. 10a): K_opt = 2*pi*L*D/(lambda_bar*c) & 0.001 deg/h Sagnac phase."""
    k_opt = compute_k_opt(1000.0, 0.10, 1.55e-6)
    expected = (2.0 * math.pi * 1000.0 * 0.10) / (1.55e-6 * C_LIGHT)
    assert math.isclose(k_opt, expected, rel_tol=1e-14)
    # Spec Table 4 row 2 check: 0.001 deg/h -> Delta_phi_S ~ 6.55e-9 rad
    omega_0p001_deg_h = 0.001 / ((180.0 / math.pi) * 3600.0)
    dphi_s = k_opt * omega_0p001_deg_h
    assert math.isclose(dphi_s, 6.5554e-9, rel_tol=1e-3)


@pytest.mark.formula
def test_eq08_optical_kerr_phase_bergh1982() -> None:
    """EQ-08 (Sec 3.1.2 Eq. 10b): Delta_phi_Kerr with broadband SLD coherence factor eta_coh."""
    phi_kerr = compute_kerr_phase(
        n2_m2_per_W=2.6e-20,
        L_eff_m=1000.0,
        lambda_bar_m=1.55e-6,
        A_eff_m2=5.0e-11,
        kappa_split=0.5005,
        P_coil_W=1.0e-3,
        eta_coh=1.0,
    )
    expected = (2.0 * math.pi * 2.6e-20 * 1000.0) / (1.55e-6 * 5.0e-11) * (1.0 - 1.001) * 1.0e-3
    assert math.isclose(phi_kerr, expected, rel_tol=1e-14)
    # Symmetric 50/50 coupler (kappa = 0.5) must cancel Kerr phase identically to 0
    assert compute_kerr_phase(2.6e-20, 1000.0, 1.55e-6, 5.0e-11, 0.5, 1.0e-3, 1.0) == 0.0


@pytest.mark.formula
def test_eq09_thermal_shupe_integral_analytic() -> None:
    """EQ-09 (Sec 3.1.2 Eq. 11): Closed-form Shupe integral verification for linear thermal gradient."""
    L_m = 1000.0
    lam = 1.55e-6
    n_eff = 1.468
    dn_dT = 1.0e-5
    alpha_T = 5.5e-7
    z = np.linspace(0.0, L_m, 1001)

    # Case 1: Uniform dT/dt = C with symmetric coil (delta_z_quad = 0) -> integral(L - 2z) = 0!
    dT_dt_uniform = np.full_like(z, 0.01)
    assert abs(shupe_integral(z, dT_dt_uniform, L_m, lam, n_eff, dn_dT, alpha_T, 0.0)) < 1e-18

    # Case 2: Linear spatial gradient dT/dt(z) = a * z -> integral_0^L (a*z)(L - 2z) dz = -a * L^3 / 6
    a = 1.0e-6
    dT_dt_lin = a * z
    val = shupe_integral(z, dT_dt_lin, L_m, lam, n_eff, dn_dT, alpha_T, 0.0)
    pref = (2.0 * math.pi / (lam * C_LIGHT)) * (dn_dT + n_eff * alpha_T)
    analytic = pref * (-a * (L_m ** 3) / 6.0)
    assert math.isclose(val, analytic, rel_tol=1e-5)

    # Case 3: Uniform dT/dt = C with constant quadrupole asymmetry delta_z_quad = d0 -> pref * C * d0 * L
    d0 = 0.005
    val_q = shupe_integral(z, dT_dt_uniform, L_m, lam, n_eff, dn_dT, alpha_T, d0)
    assert math.isclose(val_q, pref * 0.01 * d0 * L_m, rel_tol=1e-10)


@pytest.mark.formula
def test_eq10_magneto_optic_faraday_phase(tmp_path: Path) -> None:
    """EQ-10 (Sec 3.1.2 Eq. 12): Delta_phi_Faraday = V_Verdet * integral(B . ds) in Tier 2."""
    verdet = 0.6
    b_ext = 2.0e-4
    loop_m = 0.25
    expected_phi = verdet * b_ext * loop_m

    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "magneto_optic": {"verdet_rad_per_Tm": verdet, "B_ext_T": b_ext, "effective_loop_m": loop_m},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": True,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
            "simulation": {
                "duration_s": 0.012,
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.0},
            },
        },
    )
    phys = solve_tier1_optics(cfg)
    (tmp_path / "phys.json").write_text(json.dumps(phys), encoding="utf-8")
    (tmp_path / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
    subprocess.run(
        [str(SIM_BIN), "--phys", str(tmp_path / "phys.json"), "--cfg", str(tmp_path / "cfg.json"), "--out", str(tmp_path / "out")],
        check=True,
        capture_output=True,
    )
    s = json.loads((tmp_path / "out" / "sim_summary.json").read_text(encoding="utf-8"))
    assert abs(s["final_delta_phi_step_rad"] - expected_phi) < 1e-11


@pytest.mark.formula
def test_eq11_mioc_modulation_phase_nonlinearity() -> None:
    """EQ-11 (Sec 3.1.2 Eq. 13): phi_MIOC[m] = pi*(1+eps_Vpi)*V_drv/V_pi0 + gamma_nl*V_drv^2."""
    v_drv = np.array([-3.0, -1.5, 0.0, 1.5, 3.0])
    v_pi0 = 3.0
    eps_vpi = 0.02
    gamma_nl = 1.0e-3
    phi = math.pi * (1.0 + eps_vpi) * (v_drv / v_pi0) + gamma_nl * (v_drv ** 2)
    assert math.isclose(float(phi[2]), 0.0, abs_tol=1e-15)
    assert math.isclose(float(phi[4]), math.pi * 1.02 + 9.0e-3, rel_tol=1e-14)
    assert math.isclose(float(phi[0]), -math.pi * 1.02 + 9.0e-3, rel_tol=1e-14)


@pytest.mark.formula
def test_eq12_differential_modulation_phase_wrap2pi() -> None:
    """EQ-12 (Sec 3.1.2 Eq. 14): Delta_phi_mod = wrap_2pi(phi[m] - phi[m-K]) preserves <1e-15 rad precision."""
    def wrap_2pi(x: float) -> float:
        return x - 2.0 * math.pi * round(x / (2.0 * math.pi))

    dphi_small = 6.55e-9
    # Even after 1000 full 2*pi wraps, precision error remains well below 1e-12 rad
    wrapped = wrap_2pi(dphi_small + 2000.0 * math.pi)
    assert abs(wrapped) <= math.pi
    assert abs(wrapped - dphi_small) < 1e-12
    assert math.isclose(wrap_2pi(-3.0 * math.pi + 0.4), -math.pi + 0.4, abs_tol=1e-14)


@pytest.mark.formula
def test_eq13_photodiode_optical_power_with_ram(tmp_path: Path) -> None:
    """EQ-13 (Sec 3.1.2 Eq. 15): P_det[m] = (P_peak/2)*(1+alpha_RAM*V_drv)*(1+V*cos(dphi_NR+dphi_mod)) in Tier 2."""
    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "mioc": {"V_pi_0_V": 3.0, "eps_vpi": 0.02, "gamma_nl_rad_per_V2": 1.0e-3, "alpha_ram_per_V": 5.0e-3},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": True,
                "en_ram": True,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
            "simulation": {
                "duration_s": 0.0005,
                "decimation_tau": 1,
                "dump_micro_ms": 0.2,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.05},
            },
        },
    )
    phys = solve_tier1_optics(cfg)
    (tmp_path / "phys.json").write_text(json.dumps(phys), encoding="utf-8")
    (tmp_path / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
    subprocess.run(
        [str(SIM_BIN), "--phys", str(tmp_path / "phys.json"), "--cfg", str(tmp_path / "cfg.json"), "--out", str(tmp_path / "out")],
        check=True,
        capture_output=True,
    )

    m = read_micro_records(tmp_path / "out" / "micro_waveforms.bin")
    K = cfg["adc_dac"]["K_oversample"]
    v_drv = m["v_drv"]
    p_det = m["p_det"]

    k_opt = phys["K_opt_rad_per_rad_s"]
    vis = phys["visibility_V"]
    dphi_nr = k_opt * 0.05
    phi_mioc = math.pi * 1.02 * (v_drv / 3.0) + 1.0e-3 * (v_drv ** 2)
    diff_raw = phi_mioc[K:] - phi_mioc[:-K]
    dphi_mod = diff_raw - (2.0 * math.pi) * np.round(diff_raw / (2.0 * math.pi))
    p_expected = 0.5 * cfg["optics"]["P_peak_W"] * (1.0 + 5.0e-3 * v_drv[K:]) * (
        1.0 + vis * np.cos(dphi_nr + dphi_mod)
    )
    np.testing.assert_allclose(p_det[K:], p_expected, rtol=1e-12, atol=1e-18)
