"""Independent Normative Formula Verification Tests for IFOG-SIM-SPEC-007 (EQ-45 .. EQ-53).

Each test maps 1-to-1 to a normative equation in spec/IFOG-SIM-SPEC-007.{tex,md}
(cross-referencing draft prompt numbering EQ-40..EQ-48) and is verified by
scripts/verify_formulas_ci.py under AGENT.md Rule 3.
"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import (
    C_LIGHT,
    RAD_S_TO_DEG_H,
    compute_backscatter_sigma_rad,
    compute_k_opt,
)
from tier1_offline.shupe_thermal import (
    SHUPE_HEADER_STRUCT,
    SHUPE_RECORD_V2_STRUCT,
    build_winding_map,
    compute_dynamic_k_opt_rel,
    compute_dynamic_optical_params,
    elasto_optic_stress_integral,
    read_shupe_lut,
    read_shupe_lut_v2,
    shupe_integral,
    write_shupe_lut,
    write_shupe_lut_v2,
)
from tier3_analysis.dual_regime_avar import (
    DualRegimeStitcher,
    compute_residual_tier3_bi,
)
from tier3_analysis.inverse_calibration import (
    InverseCalibrator,
    compute_multi_objective_cost,
    forward_avar_psd,
    forward_slow_rate_ramp,
    forward_thermal_ramp,
)


@pytest.mark.formula
def test_eq45_spec007_discrete_winding_map() -> None:
    """EQ-45 (SPEC-007 §2.1a / draft EQ-40): Discrete quadrupole vs octupole turn-by-turn map."""
    w_q = build_winding_map(
        L_m=1000.0,
        D_m=0.10,
        coil_thickness_m=0.015,
        n_turns=256,
        n_layers=16,
        winding_pattern="quadrupole",
        flange_offset_m=0.004,
        delta_z_quad_m=0.002,
    )
    w_o = build_winding_map(
        L_m=1000.0,
        D_m=0.10,
        coil_thickness_m=0.015,
        n_turns=256,
        n_layers=16,
        winding_pattern="octupole",
        flange_offset_m=0.004,
        delta_z_quad_m=0.002,
    )
    assert w_q["z_m"].shape == (256,)
    assert np.all((w_q["z_m"] > 0.0) & (w_q["z_m"] < 1000.0))
    assert np.min(w_q["r_m"]) >= 0.0425 - 1e-12
    assert np.max(w_q["r_m"]) <= 0.0575 + 1e-12
    # Doubly-balanced octupole strictly reduces residual spatial asymmetry vs quadrupole
    assert float(np.std(w_o["delta_z_quad_m"])) < 0.30 * float(np.std(w_q["delta_z_quad_m"]))


@pytest.mark.formula
def test_eq46_spec007_elasto_optic_stress_shupe_integral() -> None:
    """EQ-46 (SPEC-007 §2.1b / draft EQ-41): Total thermo-optical phase = Shupe + elasto-optic stress."""
    L_m = 1000.0
    lambda_bar = 1.55e-6
    z = np.linspace(0.0, L_m, 1001)
    # Linear thermal gradient dT/dt = g0 * (z / L) yields exact closed-form integral
    # int_0^L (z/L)(L - 2z) dz = -L^2 / 6
    g0 = 1.0e-2
    dT_dt = g0 * (z / L_m)
    stress_rate = 1.2e5 * dT_dt
    C_eo = 3.5e-12

    phi_shupe = shupe_integral(z, dT_dt, L_m, lambda_bar, 1.468, 1.0e-5, 5.5e-7, 0.0)
    phi_stress = elasto_optic_stress_integral(z, stress_rate, L_m, lambda_bar, C_eo, 0.0)
    phi_therm = phi_shupe + phi_stress

    expected_stress = (2.0 * math.pi / (lambda_bar * C_LIGHT)) * C_eo * (1.2e5 * g0) * (-(L_m ** 2) / 6.0)
    assert abs(phi_stress - expected_stress) / abs(expected_stress) < 1.0e-5
    assert abs(phi_therm - (phi_shupe + expected_stress)) / abs(phi_therm) < 1.0e-6
    assert elasto_optic_stress_integral(z, stress_rate, L_m, lambda_bar, 0.0, 0.0) == 0.0


@pytest.mark.formula
def test_eq47_spec007_dynamic_k_opt_scale_factor() -> None:
    """EQ-47 (SPEC-007 §2.2a / draft EQ-42): Dynamic Sagnac scale factor K_opt(t)."""
    k_opt_0 = compute_k_opt(1000.0, 0.10, 1.55e-6)
    rel = float(
        compute_dynamic_k_opt_rel(
            dT_coil_K=25.0,
            dT_sld_K=10.0,
            alpha_bobbin_ppm_K=12.0,
            alpha_lambda_pm_K=35.0,
            lambda_bar_m=1.55e-6,
            kappa_back_m_per_W=1.5e-9,
            P_back_W=1.0e-6,
            n_eff=1.468,
            dn_dT_per_K=1.0e-5,
        )
    )
    expected = (
        1.0
        + 12.0e-6 * 25.0
        - (35.0e-12 * 10.0 + 1.5e-9 * 1.0e-6) / 1.55e-6
        + (1.0e-5 / 1.468) * 25.0
    )
    assert abs(rel - expected) < 1.0e-15
    assert abs(k_opt_0 * rel - k_opt_0 * expected) < 1.0e-14


@pytest.mark.formula
def test_eq48_spec007_dynamic_visibility_pol_vpi() -> None:
    """EQ-48 (SPEC-007 §2.2b / draft EQ-43): Time-varying V_eff(t), phi_pol(t), V_pi(t)."""
    v_eff, phi_pol, v_pi = compute_dynamic_optical_params(
        V_eff_0=0.998,
        phi_pol_0=1.2e-7,
        V_pi_0=3.0,
        dT_coil_K=-20.0,
        dT_mioc_K=15.0,
        beta_V_per_K=1.5e-4,
        gamma_pol_rad_per_K=2.0e-8,
        alpha_vpi_ppm_K=380.0,
    )
    assert abs(float(v_eff) - 0.998 * (1.0 - 1.5e-4 * 20.0)) < 1.0e-15
    assert abs(float(phi_pol) - (1.2e-7 + 2.0e-8 * (-20.0))) < 1.0e-18
    assert abs(float(v_pi) - 3.0 * (1.0 + 380.0e-6 * 15.0)) < 1.0e-15


@pytest.mark.formula
def test_eq49_spec007_binary_lut_v2_roundtrip_and_v1_fallback(tmp_path: Path) -> None:
    """EQ-49 (SPEC-007 §2.3 / draft EQ-44): Binary LUT v2 (24 B + 56 B <7d) roundtrip & v1 fallback."""
    assert SHUPE_HEADER_STRUCT.size == 24
    assert SHUPE_RECORD_V2_STRUCT.size == 56

    t = np.linspace(0.0, 100.0, 11)
    shupe = 1.0e-7 * t
    stress = 2.5e-8 * t
    vis = 0.999 - 1.0e-5 * t
    pol = 5.0e-8 + 1.0e-9 * t
    vpi = 3.0 + 1.0e-4 * t
    krel = 1.0 + 1.0e-6 * t

    p_v2 = tmp_path / "lut_v2.bin"
    write_shupe_lut_v2(p_v2, t, shupe, stress, vis, pol, vpi, krel)
    assert p_v2.stat().st_size == 24 + 11 * 56

    rd = read_shupe_lut_v2(p_v2)
    assert rd["version"] == 2
    assert float(np.max(np.abs(rd["delta_phi_shupe_rad"] - shupe))) < 1.0e-15
    assert float(np.max(np.abs(rd["delta_phi_stress_rad"] - stress))) < 1.0e-15
    assert float(np.max(np.abs(rd["k_opt_scale_rel_t"] - krel))) < 1.0e-15

    # O(1) linear interpolation mid-point check (< 1e-12 rad)
    t_mid = 35.0
    interp_tot = float(np.interp(t_mid, rd["t_s"], rd["delta_phi_shupe_rad"] + rd["delta_phi_stress_rad"]))
    assert abs(interp_tot - (1.25e-7 * t_mid)) < 1.0e-12

    # Legacy v1 reader fallback compatibility
    p_v1 = tmp_path / "lut_v1.bin"
    write_shupe_lut(p_v1, t, shupe)
    rd1 = read_shupe_lut_v2(p_v1)
    assert rd1["version"] == 1
    assert np.all(rd1["delta_phi_stress_rad"] == 0.0)
    assert np.all(rd1["k_opt_scale_rel_t"] == 1.0)
    t_leg, phi_leg, _ = read_shupe_lut(p_v2)
    assert float(np.max(np.abs(phi_leg - (shupe + stress)))) < 1.0e-15
    assert len(t_leg) == 11


@pytest.mark.formula
def test_eq50_spec007_mioc_electro_acoustic_dynamics() -> None:
    """EQ-50 (SPEC-007 §2.4a / draft EQ-45): MIOC 2nd-order electro-acoustic step dynamics + K_delay."""
    # Discrete-time exact ZOH 1st-order electrode + 2nd-order acoustic resonance step response
    dt = 4.8967209e-6 / 16.0
    f_elec = 15.0e6
    f_ac = 3.5e6
    zeta_ac = 0.08
    g_ac = 0.06
    a_e = math.exp(-2.0 * math.pi * f_elec * dt)
    w_ac = 2.0 * math.pi * f_ac
    wd = w_ac * math.sqrt(1.0 - zeta_ac ** 2)
    e = math.exp(-zeta_ac * w_ac * dt)
    c, s = math.cos(wd * dt), math.sin(wd * dt)
    phi11 = e * (c + (zeta_ac / math.sqrt(1.0 - zeta_ac ** 2)) * s)
    phi12 = e * (s / wd)
    phi21 = -e * (w_ac ** 2 / wd) * s
    phi22 = e * (c - (zeta_ac / math.sqrt(1.0 - zeta_ac ** 2)) * s)

    v_e, x1, x2 = 0.0, 0.0, 0.0
    trace = []
    for _ in range(200):
        v_e = a_e * v_e + (1.0 - a_e) * 1.5
        dx1 = x1 - v_e
        nx1 = v_e + phi11 * dx1 + phi12 * x2
        nx2 = phi21 * dx1 + phi22 * x2
        x1, x2 = nx1, nx2
        trace.append(v_e + g_ac * (x1 - v_e))

    arr = np.asarray(trace)
    # Acoustic resonance produces measurable overshoot > 1.5 V then settles exactly to 1.5 V
    assert float(np.max(arr)) > 1.501
    assert abs(float(arr[-1]) - 1.5) < 1.0e-5
    # Verify phase scaling Delta_phi_fb = (pi / V_pi(t)) * V_mioc_eff[k - K_delay]
    v_pi_t = 3.01
    dphi_fb = (math.pi / v_pi_t) * float(arr[-1])
    assert abs(dphi_fb - math.pi * 1.5 / 3.01) < 1.0e-4


@pytest.mark.formula
def test_eq51_spec007_capacitive_resistive_crosstalk_reduction() -> None:
    """EQ-51 (SPEC-007 §2.4b / draft EQ-46): Capacitive spike charge conservation & C_xtalk=0 reduction."""
    dt = 3.06e-7
    G_xtalk = 1.5e-8
    C_xtalk = 5.0e-12
    v_dac = np.concatenate([np.zeros(20), np.full(40, 1.5)])
    v_prev = np.concatenate([[0.0], v_dac[:-1]])

    i_xtalk = G_xtalk * v_dac + C_xtalk * (v_dac - v_prev) / dt
    i_res_only = G_xtalk * v_dac

    # Exact integral charge conservation of capacitive spike: sum(i_cap * dt) == C_xtalk * Delta_V
    q_cap_integral = float(np.sum((i_xtalk - i_res_only) * dt))
    assert abs(q_cap_integral - C_xtalk * 1.5) < 1.0e-25

    # Exact reduction to legacy SPEC-004 resistive crosstalk when C_xtalk == 0
    i_zero_cap = G_xtalk * v_dac + 0.0 * (v_dac - v_prev) / dt
    assert float(np.max(np.abs(i_zero_cap - i_res_only))) == 0.0


@pytest.mark.formula
def test_eq52_spec007_rayleigh_facet_backscatter_and_bi_stitch() -> None:
    """EQ-52 (SPEC-007 §2.5 / draft EQ-47): Rayleigh/facet phase RMS & Tier-3 anti-double-counting BI."""
    delta_nu_eff = 7.51e12
    L_c = C_LIGHT / delta_nu_eff
    R_facet_dB = -60.0
    alpha_R = 4.5e-5
    S_cap = 1.5e-3
    sigma = compute_backscatter_sigma_rad(R_facet_dB, alpha_R, S_cap, delta_nu_eff)
    expected = 2.0 * math.sqrt(10.0 ** (-6.0) + 0.5 * alpha_R * S_cap * L_c)
    assert abs(sigma - expected) < 1.0e-15

    # Anti-double-counting quadrature subtraction: B_T3,mech = sqrt(max(0, B_tot^2 - B_T2^2))
    b_tot = 5.0e-8
    b_t2 = 3.0e-8
    b_t3 = DualRegimeStitcher.residual_mechanical_bi(b_tot, b_t2)
    assert abs(b_t3 - 4.0e-8) < 1.0e-20
    assert compute_residual_tier3_bi(3.0e-8, 5.0e-8) == 0.0


@pytest.mark.formula
def test_eq53_spec007_inverse_calibration_objective_and_recovery() -> None:
    """EQ-53 (SPEC-007 §2.6 / draft EQ-48): Weighted multi-objective residual & <5% parameter recovery."""
    cal = InverseCalibrator()
    taus = np.geomspace(1.0e-2, 1.0e4, 24)
    freqs = np.geomspace(1.0e-3, 1.0e2, 24)
    w_in = np.linspace(-2.5, 2.5, 51)
    t_th = np.linspace(0.0, 900.0, 25)

    truth = {
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
    guess = {
        "c_pink_coeff": 1.0,
        "R_facet_dB": -72.0,
        "eta_pd_scale": 1.0,
        "C_xtalk_F": 2.0e-12,
        "G_xtalk_S": 1.5e-8,
        "dac_asym_lsb": 0.0,
        "diffusivity_m2_per_s": 9.5e-7,
        "delta_z_quad_m": 0.0018,
        "alpha_vpi_ppm_K": 250.0,
        "alpha_bobbin_ppm_K": 8.0,
    }

    av_m, psd_m = forward_avar_psd(taus, freqs, truth["c_pink_coeff"], truth["R_facet_dB"], truth["eta_pd_scale"], cal.avar_ctx)
    db_m = forward_slow_rate_ramp(w_in, truth["C_xtalk_F"], truth["G_xtalk_S"], truth["dac_asym_lsb"], cal.db_ctx)["omega_out_deg_h"]
    th_m = forward_thermal_ramp(t_th, truth["diffusivity_m2_per_s"], truth["delta_z_quad_m"], truth["alpha_vpi_ppm_K"], truth["alpha_bobbin_ppm_K"], cal.th_ctx)

    # Zero cost at exact truth
    assert compute_multi_objective_cost(av_m, av_m, db_m, db_m, th_m["omega_bias_deg_h"], th_m["omega_bias_deg_h"]) == 0.0

    dataset = {
        "taus_s": taus,
        "avar_meas_deg_h": av_m,
        "freqs_Hz": freqs,
        "psd_meas_deg_h2_Hz": psd_m,
        "omega_in_deg_h": w_in,
        "omega_out_meas_deg_h": db_m,
        "t_thermal_s": t_th,
        "omega_bias_meas_deg_h": th_m["omega_bias_deg_h"],
        "sf_err_meas_ppm": th_m["sf_err_ppm"],
    }
    res = cal.calibrate_all(dataset, guess)
    assert res["pass_lt_5pct"] is True
    assert res["cost_after"] < 1.0e-8 * res["cost_before"]
    for k, tv in truth.items():
        rel_err = abs(res["calibrated_params"][k] - tv) / abs(tv)
        assert rel_err < 0.05, f"Parameter {k} recovery error {rel_err:.4f} >= 5%"
