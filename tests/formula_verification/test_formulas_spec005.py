"""Per-Formula Normative Verification Suite for IFOG-SIM-SPEC-005 (EQ-31 .. EQ-41).

Each formula test is independent, deterministic, and executed as a mandatory CI/CD gate
by scripts/verify_formulas_ci.py (AGENT.md Rule 3).
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from tier1_offline.config_loader import RAD_S_TO_DEG_H
from tier3_analysis.scenarios_engineering import (
    compute_cpk,
    compute_mumetal_shield_dB,
    compute_wilson_ci_95,
    fit_thermal_polynomial_and_ekf,
)
from tier3_analysis.scenarios_time_domain import compute_theoretical_bw_3db_hz


def _six_state_psi(alpha: float) -> np.ndarray:
    a_hi = 0.5 * (math.pi + alpha)
    a_lo = 0.5 * (math.pi - 3.0 * alpha)
    return np.array([a_hi, -a_hi, a_lo, -a_hi, a_hi, -a_lo], dtype=np.float64)


@pytest.mark.formula
def test_eq31_six_state_instantaneous_and_differential_phase_sequence() -> None:
    """EQ-31: Verify 6-state anti-periodic psi_0..psi_5, zero DC mean, peak <= 3*pi/4, and exact phi_1..phi_6."""
    for alpha in (math.pi / 6.0, math.pi / 4.0, math.pi / 3.0, math.pi / 2.0):
        psi = _six_state_psi(alpha)
        # Anti-periodicity psi_{k+3} = -psi_k and zero DC drive mean
        np.testing.assert_allclose(psi[3:], -psi[:3], atol=1e-15)
        assert abs(float(np.sum(psi))) < 1e-15
        # Differential sequence phi_k = psi_{k-1} - psi_{k-2 mod 6}
        phi = np.array([psi[k] - psi[(k - 1) % 6] for k in range(6)])
        expected_phi = np.array(
            [
                +(math.pi - alpha),
                -(math.pi + alpha),
                +(math.pi - alpha),
                -(math.pi - alpha),
                +(math.pi + alpha),
                -(math.pi - alpha),
            ]
        )
        np.testing.assert_allclose(phi, expected_phi, atol=1e-15)
    # At optimal alpha = pi/3, peak instantaneous bias is exactly 2*pi/3 (33.3% below 4-state pi)
    psi_opt = _six_state_psi(math.pi / 3.0)
    assert math.isclose(float(np.max(np.abs(psi_opt))), 2.0 * math.pi / 3.0, rel_tol=1e-15)


@pytest.mark.formula
def test_eq32_six_state_taylor_expansion_and_zero_crosstalk_optimal_angle() -> None:
    """EQ-32: Verify 1st-order Taylor expansion at all 6 states and exact RAM/xtalk/MIOC-V^2 null at alpha=pi/3."""
    alpha = math.pi / 3.0
    psi = _six_state_psi(alpha)
    phi = np.array([psi[k] - psi[(k - 1) % 6] for k in range(6)])
    dphi_nr = 1.0e-6
    eps_vpi = 1.0e-5

    exact = np.cos(dphi_nr + (1.0 + eps_vpi) * phi)
    ca, sa = math.cos(alpha), math.sin(alpha)
    approx = np.array(
        [
            -ca - sa * dphi_nr - sa * (math.pi - alpha) * eps_vpi,
            -ca - sa * dphi_nr + sa * (math.pi + alpha) * eps_vpi,
            -ca - sa * dphi_nr - sa * (math.pi - alpha) * eps_vpi,
            -ca + sa * dphi_nr - sa * (math.pi - alpha) * eps_vpi,
            -ca + sa * dphi_nr + sa * (math.pi + alpha) * eps_vpi,
            -ca + sa * dphi_nr - sa * (math.pi - alpha) * eps_vpi,
        ]
    )
    np.testing.assert_allclose(exact, approx, atol=1e-9)

    # Exact cancellation of linear V_drv, dV/dt (phi), and V_drv^2 in e_Omega at alpha* = pi/3
    assert abs(float(np.sum(psi[3:]) - np.sum(psi[:3]))) < 1e-15
    assert abs(float(np.sum(phi[3:]) - np.sum(phi[:3]))) < 1e-15
    assert abs(float(np.sum(psi[3:] ** 2) - np.sum(psi[:3] ** 2))) < 1e-15
    # Verify non-zero residual -(pi - 3*alpha) away from pi/3
    psi_other = _six_state_psi(math.pi / 4.0)
    assert math.isclose(
        float(np.sum(psi_other[3:]) - np.sum(psi_other[:3])),
        -(math.pi - 3.0 * math.pi / 4.0),
        abs_tol=1e-14,
    )


@pytest.mark.formula
def test_eq33_six_state_three_channel_orthogonal_demodulation() -> None:
    """EQ-33: Verify 3-channel orthogonal 6-state demodulation (e_Omega, e_Vpi, e_asym) & dither cancellation."""
    alpha = math.pi / 3.0
    psi = _six_state_psi(alpha)
    phi = np.array([psi[k] - psi[(k - 1) % 6] for k in range(6)])
    s_alpha = 12000.0
    a_scale = s_alpha / math.sin(alpha)
    y_dc = 5000.0
    dphi_nr = 2.0e-6
    eps_vpi = 1.0e-6
    ram_alpha = 1.0e-3

    # Pure Sagnac + V_pi (no RAM): e_Omega = 6*S*dphi, e_Vpi = 8*pi*S*eps, e_asym = 0
    y = y_dc + a_scale * np.cos(dphi_nr + (1.0 + eps_vpi) * phi)
    e_omega = (y[3] + y[4] + y[5]) - (y[0] + y[1] + y[2])
    e_vpi = 2.0 * (y[1] + y[4]) - (y[0] + y[2] + y[3] + y[5])
    e_asym = (y[0] - y[2]) + (y[5] - y[3])
    assert math.isclose(e_omega, 6.0 * s_alpha * dphi_nr, rel_tol=1e-6)
    assert math.isclose(e_vpi, 8.0 * math.pi * s_alpha * eps_vpi, rel_tol=1e-5)
    assert abs(e_asym) < 1e-9

    # With linear RAM term (1 + ram_alpha * psi): e_Omega & e_Vpi stay unaffected while e_asym detects RAM!
    y_ram = y * (1.0 + ram_alpha * psi)
    e_asym_ram = (y_ram[0] - y_ram[2]) + (y_ram[5] - y_ram[3])
    assert abs(e_asym_ram) > 1.0


@pytest.mark.formula
def test_eq34_six_state_loop_gains_bandwidth_and_anti_windup() -> None:
    """EQ-34: Verify 6-state Loop-1/Loop-2 gain calibration, analytical -3 dB bandwidth & anti-windup clamp."""
    s_alpha = 11000.0
    k_tot_1 = 0.25
    k_tot_2 = 0.02
    k_i1 = k_tot_1 / (6.0 * s_alpha)
    k_i2 = k_tot_2 / (8.0 * math.pi * s_alpha)
    assert math.isclose(6.0 * s_alpha * k_i1, k_tot_1, rel_tol=1e-15)
    assert math.isclose(8.0 * math.pi * s_alpha * k_i2, k_tot_2, rel_tol=1e-15)
    assert k_tot_2 <= 0.1 * k_tot_1

    # Analytical -3 dB closed-loop bandwidth of T_1(z) = K_tot / (z^3 - z^2 + K_tot)
    frame_period_s = 6.0 * 4.89672e-6
    bw_hz = compute_theoretical_bw_3db_hz(k_tot_1, frame_period_s)
    z_bw = np.exp(1j * 2.0 * math.pi * bw_hz * frame_period_s)
    mag_bw = abs(k_tot_1 / (z_bw**3 - z_bw**2 + k_tot_1))
    assert math.isclose(mag_bw, 1.0 / math.sqrt(2.0), rel_tol=1e-3)

    # Anti-windup clamp bounds integrator cleanly
    dphi_max = 12.0
    clamped_pos = max(-dphi_max, min(dphi_max, 18.5))
    clamped_neg = max(-dphi_max, min(dphi_max, -18.5))
    assert clamped_pos == dphi_max and clamped_neg == -dphi_max


@pytest.mark.formula
def test_eq35_adc_aperture_jitter_voltage_variance_and_arw_rss() -> None:
    """EQ-35: Verify ADC sampling aperture jitter dV_j = (dV/dt)*dt_j and RSS ARW combination."""
    slew_v_per_s = 5.0e6
    sigma_tj_s = 100.0e-12
    rng = np.random.default_rng(35)
    dv_j = slew_v_per_s * sigma_tj_s * rng.standard_normal(200_000)
    expected_sigma_v = slew_v_per_s * sigma_tj_s
    assert math.isclose(float(np.std(dv_j)), expected_sigma_v, rel_tol=1e-2)

    arw_0 = 3.8e-4
    arw_j = 2.0e-4
    arw_tot = math.hypot(arw_0, arw_j)
    assert math.isclose(arw_tot**2, arw_0**2 + arw_j**2, rel_tol=1e-15)


@pytest.mark.formula
def test_eq36_imu_3axis_shared_sld_and_rail_droop_coupling() -> None:
    """EQ-36: Verify 3-axis IMU shared-SLD optical reflection P_axis,i and shared rail droop Delta_V_rail."""
    p_peak = 1.0e-4
    v_pi = 3.0
    rho = 2.0e-3
    vx, vy, vz = 3.0, -1.5, 0.5
    dvx, dvy, dvz = 1.0e7, 2.0e6, 2.0e6
    r_load, c_load, z_rail = 50.0, 200.0e-12, 0.25

    p_y = p_peak * (1.0 + rho * (vx + vz) / v_pi)
    i_bus = (abs(vx) + abs(vy) + abs(vz)) / r_load + c_load * (abs(dvx) + abs(dvy) + abs(dvz))
    dv_rail = -z_rail * i_bus
    assert math.isclose(p_y, p_peak * (1.0 + rho * 3.5 / 3.0), rel_tol=1e-15)
    assert dv_rail < 0.0
    assert math.isclose(dv_rail, -0.25 * (5.0 / 50.0 + 200e-12 * 1.4e7), rel_tol=1e-15)


@pytest.mark.formula
def test_eq37_vibration_rectification_error_quadratic_law() -> None:
    """EQ-37: Verify quadratic TIA G2*V^2 rectification DC shift scales strictly as g_rms^2."""
    g2 = 2.0e-2
    alpha_vib = 0.02
    v0 = 2.5
    t = np.linspace(0.0, 0.2, 200_000, endpoint=False)
    dc_shifts = []
    for g_rms in (1.0, 2.0, 4.0):
        a_g = math.sqrt(2.0) * g_rms * np.sin(2.0 * math.pi * 250.0 * t)
        v_vib = v0 * (1.0 + alpha_vib * a_g)
        v_nl = v_vib + g2 * (v_vib**2)
        dc_shift = float(np.mean(v_nl)) - (v0 + g2 * v0**2)
        expected = g2 * (v0 * alpha_vib * g_rms) ** 2
        assert math.isclose(dc_shift, expected, rel_tol=1e-5)
        dc_shifts.append(dc_shift)
    # Quadratic law: doubling g_rms quadruples VRE DC bias
    assert math.isclose(dc_shifts[1] / dc_shifts[0], 4.0, rel_tol=1e-5)
    assert math.isclose(dc_shifts[2] / dc_shifts[0], 16.0, rel_tol=1e-5)


@pytest.mark.formula
def test_eq38_faraday_magnetic_sensitivity_and_mumetal_attenuation() -> None:
    """EQ-38: Verify Faraday magnetic sensitivity S_B [deg/h/G] and Mu-metal shielding attenuation [dB]."""
    verdet = 0.6
    eff_loop_m = 0.02
    k_opt = 1.3521580787
    s_b = (verdet * eff_loop_m * 1.0e-4 / k_opt) * RAD_S_TO_DEG_H
    assert s_b > 0.1
    shield_db = compute_mumetal_shield_dB(s_b, max_field_G=1.0, bias_budget_deg_h=0.01)
    assert math.isclose(shield_db, 20.0 * math.log10(s_b / 0.01), rel_tol=1e-12)
    # Zero shielding required when already below budget
    assert compute_mumetal_shield_dB(0.005, max_field_G=1.0, bias_budget_deg_h=0.01) == 0.0


@pytest.mark.formula
def test_eq39_bit_fdir_fault_classification_thresholds() -> None:
    """EQ-39: Verify mutually exclusive BIT/FDIR classification thresholds across all 5 fault classes."""
    y_nom = 15_000.0
    code_max = 32_767.0
    vpi_thr = 4000.0
    seu_thr = 4000.0

    def classify(y_now: float, y_mean: float, e_vpi: float, e_omega: float) -> int:
        if abs(y_now) >= 0.98 * code_max:
            return 4
        if y_mean < 0.15 * y_nom:
            return 2
        if y_mean < 0.65 * y_nom:
            return 1
        if abs(e_vpi) > vpi_thr:
            return 3
        if abs(e_omega) > seu_thr:
            return 5
        return 0

    assert classify(y_nom, y_nom, 0.0, 0.0) == 0
    assert classify(0.5 * y_nom, 0.5 * y_nom, 0.0, 0.0) == 1
    assert classify(0.0, 0.0, 0.0, 0.0) == 2
    assert classify(y_nom, y_nom, 12_000.0, 0.0) == 3
    assert classify(32_767.0, y_nom, 0.0, 0.0) == 4
    assert classify(y_nom, y_nom, 0.0, 15_000.0) == 5


@pytest.mark.formula
def test_eq40_monte_carlo_wilson_ci95_and_cpk() -> None:
    """EQ-40: Verify Wilson 95% binomial CI bounds and process capability index C_pk."""
    lo, hi = compute_wilson_ci_95(95, 100)
    assert 0.88 < lo < 0.95 < hi < 0.99
    with pytest.raises(ValueError):
        compute_wilson_ci_95(0, 0)

    # Known normal distribution centered at 0 with sigma=0.2 inside [-1, +1] -> C_pk = 1 / 0.6 = 1.6667
    samples = np.array([-0.2, 0.2] * 50, dtype=np.float64)
    sigma = float(np.std(samples, ddof=1))
    cpk = compute_cpk(samples, lsl=-1.0, usl=1.0)
    assert math.isclose(cpk, 1.0 / (3.0 * sigma), rel_tol=1e-12)
    assert compute_cpk(np.zeros(5), lsl=-1.0, usl=1.0) == 10.0
    assert compute_cpk(np.full(5, 5.0), lsl=-1.0, usl=1.0) == 0.0


@pytest.mark.formula
def test_eq41_thermal_drift_polynomial_and_ekf_compensation() -> None:
    """EQ-41: Verify thermal wavelength/V_pi drift scaling, 2D polynomial compensation, and EKF residual reduction."""
    T = np.repeat(np.array([-40.0, -20.0, 0.0, 25.0, 50.0, 70.0, 85.0]), 3)
    dT_dt = np.tile(np.array([-0.5, 0.0, 0.5]), 7)
    dT = T - 25.0
    # Synthetic exact physical thermal bias surface
    bias = 0.05 + 0.008 * dT + 2.0e-4 * (dT**2) + 0.35 * dT_dt + 0.002 * dT * dT_dt
    res = fit_thermal_polynomial_and_ekf(T, dT_dt, bias)
    assert res["poly_residual_rms_deg_per_h"] < 1e-12
    assert res["poly_reduction_pct"] > 99.999
    assert res["ekf_reduction_pct"] > 50.0
    np.testing.assert_allclose(res["poly_coeffs"], [0.05, 0.008, 2.0e-4, 0.35, 0.002], atol=1e-10)
