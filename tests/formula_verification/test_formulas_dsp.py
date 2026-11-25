"""Per-formula verification suite for Digital DSP & Control Loop equations (EQ-01..EQ-03, EQ-20..EQ-23)."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import deep_merge, load_config
from tier1_offline.jones_spectral import solve_tier1_optics
from tier3_analysis.binary_io import read_sim_records

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASE_CFG_PATH = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.formula
def test_eq01_four_state_bias_phase_sequence() -> None:
    """EQ-01 (Sec 1 Eq. 1): 4-state bias sequence [+(pi-a), -(pi-a), -(pi+a), +(pi+a)], a in (0, pi/2]."""
    for alpha in [math.pi / 8.0, math.pi / 4.0, math.pi / 2.0]:
        phi_seq = [+(math.pi - alpha), -(math.pi - alpha), -(math.pi + alpha), +(math.pi + alpha)]
        assert 0.0 < alpha <= math.pi / 2.0
        assert math.isclose(phi_seq[0], -phi_seq[1], rel_tol=1e-15)
        assert math.isclose(phi_seq[2], -phi_seq[3], rel_tol=1e-15)
        assert math.isclose(sum(phi_seq), 0.0, abs_tol=1e-15)


@pytest.mark.formula
def test_eq02_four_state_first_order_taylor_expansion() -> None:
    """EQ-02 (Sec 1 Eqs. 2-5): First-order Taylor linearization of cos(dphi_NR + (1+eps_Vpi)*phi_k)."""
    alpha = math.pi / 4.0
    phi_seq = [+(math.pi - alpha), -(math.pi - alpha), -(math.pi + alpha), +(math.pi + alpha)]
    dphi_nr = 1.0e-5
    eps_vpi = 1.0e-4
    exact = [math.cos(dphi_nr + (1.0 + eps_vpi) * pk) for pk in phi_seq]
    taylor = [
        -math.cos(alpha) - math.sin(alpha) * dphi_nr - eps_vpi * (math.pi - alpha) * math.sin(alpha),
        -math.cos(alpha) + math.sin(alpha) * dphi_nr - eps_vpi * (math.pi - alpha) * math.sin(alpha),
        -math.cos(alpha) - math.sin(alpha) * dphi_nr + eps_vpi * (math.pi + alpha) * math.sin(alpha),
        -math.cos(alpha) + math.sin(alpha) * dphi_nr + eps_vpi * (math.pi + alpha) * math.sin(alpha),
    ]
    np.testing.assert_allclose(exact, taylor, atol=1e-7)


@pytest.mark.formula
def test_eq03_orthogonal_four_state_demodulation_sign_correction() -> None:
    """EQ-03 (Sec 1 Eq. 6): Corrected e_Omega = (y2-y1)+(y4-y3) and e_Vpi = (y3+y4)-(y1+y2) orthogonality."""
    alpha = math.pi / 4.0
    phi_seq = [+(math.pi - alpha), -(math.pi - alpha), -(math.pi + alpha), +(math.pi + alpha)]
    dphi_nr = 1.0e-5
    eps_vpi = 1.0e-4
    exact = [math.cos(dphi_nr + (1.0 + eps_vpi) * pk) for pk in phi_seq]

    s_alpha_norm = math.sin(alpha)
    e_omega = (exact[1] - exact[0]) + (exact[3] - exact[2])
    e_vpi = (exact[2] + exact[3]) - (exact[0] + exact[1])
    assert math.isclose(e_omega, 4.0 * s_alpha_norm * dphi_nr, rel_tol=1e-4)
    assert math.isclose(e_vpi, 4.0 * math.pi * s_alpha_norm * eps_vpi, rel_tol=1e-4)

    # Confirm the legacy wrong sign (Audit Table 1) cancels Sagnac to ~0
    wrong_old = (exact[1] - exact[0]) + (exact[2] - exact[3])
    assert abs(wrong_old) < 1e-8


@pytest.mark.formula
def test_eq20_two_state_and_four_state_integrator_laws(tmp_path: Path) -> None:
    """EQ-20 (Sec 3.3.1 Eqs. 24-27): Both 2-state and 4-state closed-loop convergence in Tier 2."""
    base = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "mioc": {"gamma_nl_rad_per_V2": 0.0},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False},
            "ablation_flags": {
                "en_pol_error": False,
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
                "duration_s": 0.02,
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.02},
            },
        },
    )
    phys = solve_tier1_optics(base)
    phys_p = tmp_path / "phys.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")

    # 4-state mode: tracks BOTH Omega_in AND locks eps_vpi=2% -> <1e-5
    cfg4 = deep_merge(base, {"dsp": {"mode": "4state", "en_vpi_loop": True, "K_P_1": 1e-6}})
    (tmp_path / "cfg4.json").write_text(json.dumps(cfg4), encoding="utf-8")
    subprocess.run(
        [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(tmp_path / "cfg4.json"), "--out", str(tmp_path / "out4")],
        check=True,
        capture_output=True,
    )
    s4 = json.loads((tmp_path / "out4" / "sim_summary.json").read_text(encoding="utf-8"))
    assert abs(s4["final_omega_out_rad_per_s"] - 0.02) < 1e-9
    assert abs(s4["final_eps_vpi_eff"]) < 1e-5

    # 2-state mode (ideal V_pi): tracks Omega_in with alternating sign demodulation
    cfg2 = deep_merge(
        base,
        {
            "dsp": {"mode": "2state", "en_vpi_loop": False},
            "ablation_flags": {"en_mioc_vpi_err": False},
        },
    )
    (tmp_path / "cfg2.json").write_text(json.dumps(cfg2), encoding="utf-8")
    subprocess.run(
        [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(tmp_path / "cfg2.json"), "--out", str(tmp_path / "out2")],
        check=True,
        capture_output=True,
    )
    s2 = json.loads((tmp_path / "out2" / "sim_summary.json").read_text(encoding="utf-8"))
    assert abs(s2["final_omega_out_rad_per_s"] - 0.02) < 1e-9


@pytest.mark.formula
def test_eq21_digital_ramp_flyback_and_prbs_dither_zero_bias(tmp_path: Path) -> None:
    """EQ-21 (Sec 3.3.1 Eqs. 28-29): Continuous 2*pi flyback resets & unbiased PRBS dither cancellation."""
    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {
                "mode": "4state",
                "en_vpi_loop": True,
                "en_prbs_dither": True,
                "prbs_amplitude_rad": 0.015,
            },
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
                "duration_s": 0.03,
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.5},
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
    assert s["flyback_count"] > 500
    assert abs(s["mean_omega_out_second_half_rad_per_s"] - 0.5) < 1e-4


@pytest.mark.formula
def test_eq22_z_domain_jury_stability_and_loop2_separation(tmp_path: Path) -> None:
    """EQ-22 (Sec 3.3.2 Eqs. 30-31): Jury stability of z^3 - z^2 + K_tot = 0 & Loop-2 separation."""
    # Exact Schur-Cohn / Jury stability bound for z^3 - z^2 + K_tot = 0 is 0 < K_tot < (sqrt(5)-1)/2 ~ 0.618
    # (which strictly contains the spec recommended range [0.15, 0.35] and lies within necessary bound (0, 1)).
    golden_bound = (math.sqrt(5.0) - 1.0) / 2.0
    for k_stable in [0.05, 0.15, 0.25, 0.35, 0.55]:
        assert 0.0 < k_stable < golden_bound < 1.0
        roots = np.roots([1.0, -1.0, 0.0, k_stable])
        assert np.all(np.abs(roots) < 1.0), f"Expected stable roots for K_tot={k_stable}"

    for k_unstable in [0.65, 1.0, 1.05, 1.5]:
        roots = np.roots([1.0, -1.0, 0.0, k_unstable])
        assert np.any(np.abs(roots) >= 1.0 - 1e-12), f"Expected unstable root for K_tot={k_unstable}"

    # Verify fail-closed enforcement in ifog_sim when K_tot_1 >= 1 or K_tot_2 > 0.1 * K_tot_1
    base = load_config(BASE_CFG_PATH)
    phys = solve_tier1_optics(base)
    phys_p = tmp_path / "phys.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")

    bad1 = deep_merge(base, {"dsp": {"K_tot_1": 1.05}})
    p1 = tmp_path / "bad_jury.json"
    p1.write_text(json.dumps(bad1), encoding="utf-8")
    r1 = subprocess.run(
        [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(p1), "--out", str(tmp_path / "o1")],
        capture_output=True,
        text=True,
    )
    assert r1.returncode != 0

    bad2 = deep_merge(base, {"dsp": {"K_tot_1": 0.25, "K_tot_2": 0.05, "en_vpi_loop": True}})
    p2 = tmp_path / "bad_sep.json"
    p2.write_text(json.dumps(bad2), encoding="utf-8")
    r2 = subprocess.run(
        [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(p2), "--out", str(tmp_path / "o2")],
        capture_output=True,
        text=True,
    )
    assert r2.returncode != 0


@pytest.mark.formula
def test_eq23_closed_loop_scale_factor_sf_cl(tmp_path: Path) -> None:
    """EQ-23 (Sec 3.3.2 Eq. 32): Omega_out = Delta_phi_step / SF_CL where SF_CL = K_opt."""
    cfg = deep_merge(
        load_config(BASE_CFG_PATH),
        {
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": True},
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
                "duration_s": 0.02,
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": 0.123456},
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
    rec = read_sim_records(tmp_path / "out" / "sim_out.bin")
    assert math.isclose(
        s["final_omega_out_rad_per_s"],
        s["final_delta_phi_step_rad"] / phys["K_opt_rad_per_rad_s"],
        rel_tol=1e-12,
    )
    assert abs(float(rec["omega_out"][-1]) - 0.123456) < 1e-10
