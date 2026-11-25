"""Per-formula verification suite for Analog Front-End & ADC equations (EQ-14 .. EQ-19)."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import (
    K_BOLTZMANN,
    Q_ELECTRON,
    compute_tia_dynamics,
    compute_tia_noise_variance,
    deep_merge,
    load_config,
)
from tier1_offline.jones_spectral import solve_tier1_optics
from tier3_analysis.binary_io import read_micro_records, read_sim_records

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASE_CFG_PATH = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.formula
def test_eq14_tia_input_current_and_crosstalk(tmp_path: Path) -> None:
    """EQ-14 (Sec 3.2.1 Eq. 16): I_in[m] = R*P_det + C_xtalk*dV/dt + k_xtalk*V_drv in Tier 2."""
    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "analog_frontend": {"C_xtalk_F": 2.0e-12, "k_xtalk_A_per_V": 2.0e-7, "V_off_0_V": 0.0},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": True,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
            "simulation": {"duration_s": 0.0004, "decimation_tau": 1, "dump_micro_ms": 0.2},
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
    dt_fast = phys["tau_s"] / cfg["adc_dac"]["K_oversample"]
    dv_dt = np.diff(m["v_drv"]) / dt_fast
    i_expected = (
        cfg["analog_frontend"]["responsivity_A_per_W"] * m["p_det"][1:]
        + 2.0e-12 * dv_dt
        + 2.0e-7 * m["v_drv"][1:]
    )
    v_tia_expected = cfg["analog_frontend"]["R_f_ohm"] * i_expected
    np.testing.assert_allclose(m["v_tia"][1:], v_tia_expected, rtol=1e-10, atol=1e-12)


@pytest.mark.formula
def test_eq15_six_component_tia_noise_psd_and_variance() -> None:
    """EQ-15 (Sec 3.2.1 Eq. 17): Exact integral of 6-component S_i,tot(f) over [0, B_fast]."""
    p_det = 2.0e-5
    resp = 0.95
    i_dark = 5.0e-9
    t_tia = 300.0
    rf = 50000.0
    dnu_eff = 7.51e12
    i_n = 2.0e-12
    e_n = 4.0e-9
    c_tot = 3.0e-12
    c_f = 2.523e-13
    b_fast = 1.6337e6

    res = compute_tia_noise_variance(
        p_det, resp, i_dark, t_tia, rf, dnu_eff, i_n, e_n, c_tot, c_f, b_fast
    )
    # Direct numerical quadrature of S_i,tot(f) from 0 to B_fast
    f_grid = np.linspace(0.0, b_fast, 20001)
    s_f = (
        2.0 * Q_ELECTRON * (resp * p_det + i_dark)
        + 4.0 * K_BOLTZMANN * t_tia / rf
        + ((resp * p_det) ** 2) / dnu_eff
        + i_n ** 2
        + (e_n / rf) ** 2
        + (e_n ** 2) * ((2.0 * math.pi * f_grid) ** 2) * ((c_tot + c_f) ** 2)
    )
    var_quad = float(np.trapezoid(s_f, f_grid))
    assert math.isclose(res["var_total_A2"], var_quad, rel_tol=1e-6)


@pytest.mark.formula
def test_eq16_tia_second_order_transfer_function() -> None:
    """EQ-16 (Sec 3.2.2 Eqs. 18-19): H_TIA(s) = R_f*w0^2/(s^2 + 2*zeta*w0*s + w0^2), w0, zeta."""
    rf = 50000.0
    c_tot = 3.0e-12
    f_gbw = 150.0e6
    cf = math.sqrt(c_tot / (2.0 * math.pi * rf * f_gbw))
    dyn = compute_tia_dynamics(rf, c_tot, cf, f_gbw)

    w0_exp = math.sqrt((2.0 * math.pi * f_gbw) / (rf * (c_tot + cf)))
    zeta_exp = 0.5 * w0_exp * (rf * cf + 1.0 / (2.0 * math.pi * f_gbw))
    assert math.isclose(dyn["omega_0_rad_per_s"], w0_exp, rel_tol=1e-14)
    assert math.isclose(dyn["zeta"], zeta_exp, rel_tol=1e-14)
    assert math.isclose(dyn["omega_0_rad_per_s"], 7.613e7, rel_tol=1e-2)

    h_dc = (rf * w0_exp ** 2) / (w0_exp ** 2)
    h_w0 = abs((rf * w0_exp ** 2) / ((1j * w0_exp) ** 2 + 2.0 * zeta_exp * w0_exp * (1j * w0_exp) + w0_exp ** 2))
    assert math.isclose(h_dc, rf, rel_tol=1e-14)
    assert math.isclose(h_w0, rf / (2.0 * zeta_exp), rel_tol=1e-12)


@pytest.mark.formula
def test_eq17_butterworth_cf_opt_and_settling_time() -> None:
    """EQ-17 (Sec 3.2.2 Eq. 20): C_f,opt = sqrt(C_tot/(2*pi*R_f*f_GBW)) and t_s(0.1%) = 6.9/(zeta*w0)."""
    rf = 50000.0
    c_tot = 3.0e-12
    f_gbw = 150.0e6
    cf_opt = math.sqrt(c_tot / (2.0 * math.pi * rf * f_gbw))
    dyn = compute_tia_dynamics(rf, c_tot, cf_opt, f_gbw)

    assert math.isclose(dyn["C_f_opt_F"], 0.252313e-12, rel_tol=1e-3)
    assert math.isclose(dyn["t_s_0p1pct_s"], 6.9 / (dyn["zeta"] * dyn["omega_0_rad_per_s"]), rel_tol=1e-14)
    # Spec Table 4 row 1 feasibility bound: t_s(0.1%) < dt_fast = 306 ns
    assert dyn["t_s_0p1pct_s"] < 3.06e-7


@pytest.mark.formula
def test_eq18_tia_cubic_polynomial_nonlinearity_and_clipping(tmp_path: Path) -> None:
    """EQ-18 (Sec 3.2.3 Eqs. 21-22): V_adc = clip(G1*V_lin + G2*V_lin^2 + G3*V_lin^3, V_min, V_max)."""
    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "analog_frontend": {
                "V_off_0_V": 0.25,
                "G1": 1.0,
                "G2_per_V": 0.05,
                "G3_per_V2": 0.01,
                "V_min_V": -1.5,
                "V_max_V": 1.5,
            },
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": True,
                "en_quantization": False,
            },
            "simulation": {"duration_s": 0.0003, "decimation_tau": 1, "dump_micro_ms": 0.2},
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
    v_lin = m["v_tia"] + 0.25
    v_poly = v_lin + 0.05 * (v_lin ** 2) + 0.01 * (v_lin ** 3)
    v_exp = np.clip(v_poly, -1.5, 1.5)
    np.testing.assert_allclose(m["v_adc"], v_exp, rtol=1e-12, atol=1e-12)


@pytest.mark.formula
def test_eq19_adc_blanking_quantizer_and_arw_penalty(tmp_path: Path) -> None:
    """EQ-19 (Sec 3.2.3 Eq. 23): Blanking averaging, N_ADC quantization, and 1/sqrt(eta_b) ARW penalty."""
    # Compare ARW standard deviation at eta_b = 1.0 (16/16) vs eta_b = 0.25 (4/16) -> ratio must be 2.0 (= 1/sqrt(0.25))!
    base = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "noise": {"en_white_noise": True, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": False},
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
                "en_quantization": True,
            },
            "simulation": {"duration_s": 0.4, "decimation_tau": 4, "dump_micro_ms": 0.05},
        },
    )
    phys = solve_tier1_optics(base)
    phys_p = tmp_path / "phys.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")

    stds = {}
    for label, k_start, k_end in [("full", 0, 15), ("quarter", 12, 15)]:
        c = deep_merge(base, {"adc_dac": {"k_start": k_start, "k_end": k_end}})
        cf = tmp_path / f"cfg_{label}.json"
        cf.write_text(json.dumps(c), encoding="utf-8")
        od = tmp_path / f"out_{label}"
        subprocess.run(
            [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(cf), "--out", str(od)],
            check=True,
            capture_output=True,
        )
        rec = read_sim_records(od / "sim_out.bin")
        # Verify exact integer ADC code on micro trace matches EQ-19 formula
        micro = read_micro_records(od / "micro_waveforms.bin")
        K = 16
        delta_adc = 2.0 * c["adc_dac"]["V_fs_adc_V"] / (2 ** c["adc_dac"]["N_adc_bits"])
        win_v = micro["v_adc"][k_start : k_end + 1]
        expected_code = int(round(float(np.mean(win_v)) / delta_adc))
        assert int(micro["adc_code"][0]) == expected_code

        stds[label] = float(np.std(rec["omega_out"][500:]))

    ratio = stds["quarter"] / stds["full"]
    expected_penalty = 1.0 / math.sqrt(4.0 / 16.0)  # 2.0
    assert abs(ratio - expected_penalty) / expected_penalty < 0.08
