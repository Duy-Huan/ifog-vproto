"""Comprehensive Unit Tests for IFOG-VPROTO v4.1.0 Industrial TRL 7-8 / DO-254 Upgrade (100% Coverage)."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tier1_offline.config_loader import load_config
from tier1_offline.jones_spectral import solve_tier1_optics
from tier1_offline.shupe_thermal import (
    generate_asymmetric_3d_fem_csv,
    load_fem_3d_csv,
    main as shupe_main,
    solve_tier1_shupe_3d_fem,
)
from tier3_analysis.lab_validation import (
    compute_asme_vv20_metric,
    generate_reference_lab_dataset,
    load_lab_avar_csv,
    load_lab_rate_ramp_csv,
    load_lab_thermal_csv,
    validate_against_lab_dataset,
)
from tier3_analysis.scenarios_industrial import (
    compute_aging_and_tid_factors,
    mechanical_transmissibility_2dof,
    mil_std_810h_cat24_psd,
    rtl_fixed_quantize_int,
    run_all_industrial_scenarios,
    run_ind01_lab_validation,
    run_ind02_fixed_point_rtl,
    run_ind03_fem_3d,
    run_ind04_random_vib_psd,
    run_ind05_fmu_multi_instance,
    run_ind06_pvt_aging_corners,
    verify_rtl_bit_true_equivalence,
)
from tier3_analysis import sim_runner_cli
from viz.export_report import export_run_report
from viz.plot_industrial import plot_all_industrial_figures
from viz.plot_scenarios import plot_dsp6_compare, plot_dyn_scenarios
from viz.report_narratives import get_figure_narrative

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_PATH = REPO_ROOT / "build" / "ifog_sim"
MULTI_FMU = REPO_ROOT / "build" / "ifog_core_multi.fmu"
BASE_CFG_PATH = REPO_ROOT / "configs" / "baseline_1km_spec007.json"


def test_fem_3d_csv_loader_errors_and_cli(tmp_path: Path) -> None:
    """Exercise 3D FEM CSV validation errors, solver, and --fem-3d-csv CLI path."""
    bad_cols = tmp_path / "bad_cols.csv"
    bad_cols.write_text("t_s,r_m\n0.0,0.05\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        load_fem_3d_csv(bad_cols)

    one_t = tmp_path / "one_t.csv"
    one_t.write_text(
        "t_s,r_m,theta_rad,z_ax_m,T_K,sigma_eff_Pa\n"
        "0.0,0.05,0.0,0.0,298.15,0.0\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="at least 2 timestamps"):
        load_fem_3d_csv(one_t)

    fem_csv = generate_asymmetric_3d_fem_csv(tmp_path / "coil_3d.csv", n_times=4, n_r=3, n_theta=4, n_z_ax=2)
    fem = load_fem_3d_csv(fem_csv)
    assert len(fem["t_s"]) == 4

    cfg = load_config(BASE_CFG_PATH)
    phys = solve_tier1_optics(cfg)
    ch, summary = solve_tier1_shupe_3d_fem(cfg, fem_csv, phys_params=phys, n_theta_per_turn=4)
    assert summary["source_mode"] == "fem_3d_csv"
    assert len(ch["delta_phi_stress_rad"]) == 4

    out_cli = tmp_path / "cli_out"
    out_cli.mkdir()
    (out_cli / "phys_params.json").write_text(json.dumps(phys), encoding="utf-8")
    rc = shupe_main(["--cfg", str(BASE_CFG_PATH), "--out", str(out_cli), "--fem-3d-csv", str(fem_csv)])
    assert rc == 0
    assert (out_cli / "shupe_lut.bin").exists()


def test_lab_validation_csv_errors_and_pipeline(tmp_path: Path) -> None:
    """Exercise physical lab CSV error paths, ASME V&V 20 math, and full CAS-4 validation."""
    bad_hdr = tmp_path / "bad_hdr.csv"
    bad_hdr.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing required columns"):
        load_lab_avar_csv(bad_hdr)

    short_csv = tmp_path / "short.csv"
    short_csv.write_text("omega_in_deg_s,omega_out_deg_s,u_meas_deg_h\n0.0,0.0,0.01\n", encoding="utf-8")
    with pytest.raises(ValueError, match="at least 4 data rows"):
        load_lab_rate_ramp_csv(short_csv)

    lab_dir = generate_reference_lab_dataset(tmp_path / "lab_ref", seed=2026)
    assert len(load_lab_avar_csv(lab_dir / "static_avar_10h.csv")["taus_s"]) == 28
    assert len(load_lab_rate_ramp_csv(lab_dir / "rate_table_deadband.csv")["omega_in_deg_h"]) == 53
    assert len(load_lab_thermal_csv(lab_dir / "thermal_chamber_ramp.csv")["t_thermal_s"]) == 41

    vv = compute_asme_vv20_metric(np.array([1.0, 2.0]), np.array([1.01, 1.99]), np.array([0.02, 0.02]))
    assert vv["ratio_E_over_u_val"] < 1.0

    rep = validate_against_lab_dataset(lab_dir, out_dir=tmp_path / "lab_out")
    assert rep["pass"] is True
    assert rep["nasa_cas_level"] == 4
    assert (tmp_path / "lab_out" / "lab_validation_report.json").exists()


def test_industrial_math_helpers() -> None:
    """Cover fixed-point RTL saturation/truncation, MIL-STD-810H PSD, 2-DOF transmissibility, and TID aging."""
    q_ok, ovf = rtl_fixed_quantize_int(1.25, 48, 32, truncate=False)
    assert not ovf and q_ok == int(round(1.25 * (1 << 32)))
    q_tr, ovf = rtl_fixed_quantize_int(1.9, 16, 8, truncate=True)
    assert not ovf and q_tr == int(math.floor(1.9 * 256))
    q_hi, ovf_hi = rtl_fixed_quantize_int(500.0, 16, 8, truncate=False)
    assert ovf_hi and q_hi == (1 << 15) - 1
    q_lo, ovf_lo = rtl_fixed_quantize_int(-500.0, 16, 8, truncate=False)
    assert ovf_lo and q_lo == -(1 << 15)

    chk = verify_rtl_bit_true_equivalence(np.array([0.0, 0.5, -0.25]), 48, 32, False)
    assert chk["exact_0lsb_match"] is True

    freqs = np.array([20.0, 100.0, 480.0, 2000.0])
    psd = mil_std_810h_cat24_psd(freqs)
    assert psd[1] == pytest.approx(0.04, rel=1e-6)
    h_hard = mechanical_transmissibility_2dof(freqs, f_iso_hz=None)
    h_iso = mechanical_transmissibility_2dof(freqs, f_iso_hz=65.0)
    assert h_hard[2] > h_iso[2]

    af = compute_aging_and_tid_factors(10.0, 50.0, L_km=1.0)
    assert 0.0 < af["total_power_factor"] < 1.0
    assert af["ria_dB"] > 1.0


def test_group_e_full_execution_plotting_and_report_export(tmp_path: Path) -> None:
    """Execute all 6 Group E scenarios (IND-01..IND-06), plots, narratives, and report export."""
    assert BIN_PATH.exists() and MULTI_FMU.exists()
    cfg = load_config(BASE_CFG_PATH)
    run_dir = tmp_path / "ind_run"
    # Use a fresh lab dir so the auto-generate fallback branch in IND-01 is also covered
    fresh_lab = tmp_path / "fresh_lab_csvs"
    res = run_all_industrial_scenarios(
        BIN_PATH, cfg, run_dir, lab_dir=fresh_lab, multi_fmu_path=MULTI_FMU
    )
    assert res["all_pass"] is True

    figs = plot_all_industrial_figures(run_dir, tmp_path / "figs_check")
    assert len(figs) == 6

    report_dir = tmp_path / "ind_report"
    summary = export_run_report(
        run_dir, formats=("png", "md", "html"), report_dir=report_dir, run_meta={"run_id": "ind_unit", "mode": "ind_all"}
    )
    assert summary["report_meta"]["overall_status"] == "PASS"
    assert len(summary["gate_statuses"]) == 6
    assert (report_dir / "report.md").exists() and (report_dir / "report.html").exists()

    for stem in (
        "fig_ind01_lab_validation",
        "fig_ind02_fixed_point_rtl",
        "fig_ind03_fem_3d",
        "fig_ind04_random_vib_psd",
        "fig_ind05_fmu_multi_instance",
        "fig_ind06_pvt_aging_corners",
    ):
        nar = get_figure_narrative(stem, summary)
        assert "ĐẠT" in nar["what_it_proves"]


def test_dsp_2_4_6_state_plotting_branches(tmp_path: Path) -> None:
    """Cover 2-State plot overlays in plot_dsp6_compare, DYN-01, DYN-02, and DYN-03."""
    dsp_data = {
        "two_state": {"ram_xtalk_bias_deg_per_h": 1000.0, "peak_bias_vpi_frac": 0.5},
        "four_state": {"ram_xtalk_bias_deg_per_h": 350.0, "peak_bias_vpi_frac": 1.0},
        "six_state": {"ram_xtalk_bias_deg_per_h": 1e-4, "peak_bias_vpi_frac": 2.0 / 3.0},
        "ram_xtalk_rejection_dB": 130.0,
        "peak_voltage_reduction_pct": 33.3,
    }
    p_dsp = plot_dsp6_compare(dsp_data, tmp_path / "dsp246.png")
    assert p_dsp.exists()

    tr = {
        "t_ms": [-0.1, 0.0, 0.5, 1.0],
        "omega_in_deg_per_s": [0.0, 10.0, 10.0, 10.0],
        "omega_out_deg_per_s": [0.0, 1.0, 9.5, 10.0],
        "tracking_err_deg_per_s": [0.0, -9.0, -0.5, 0.0],
        "phi_sagnac_rad": [0.0, 0.2, 0.2, 0.2],
        "delta_phi_step_rad": [0.0, 0.02, 0.19, 0.2],
    }
    case_tmpl = {"rise_time_10_90_ms": 0.1, "trace": tr}
    d1 = {
        "cases": {
            "step10_2state": case_tmpl,
            "step10_4state": case_tmpl,
            "step10_6state": case_tmpl,
            "step100_4state": case_tmpl,
            "step100_6state": case_tmpl,
            "step10_6state_k015": case_tmpl,
            "step10_6state_k045": case_tmpl,
        }
    }
    (tmp_path / "dyn01_step_response.json").write_text(json.dumps(d1), encoding="utf-8")

    bode_m = {
        "freqs_Hz": [20.0, 100.0, 1000.0, 5000.0],
        "mag_dB": [0.0, -0.1, -1.5, -6.0],
        "theory_mag_dB": [0.0, -0.1, -1.5, -6.0],
        "phase_deg": [-1.0, -5.0, -40.0, -80.0],
        "theory_phase_deg": [-1.0, -5.0, -40.0, -80.0],
        "group_delay_us": [50.0, 50.0, 45.0, 30.0],
        "theory_group_delay_us": [50.0, 50.0, 45.0, 30.0],
        "bw_3db_measured_Hz": 2000.0,
        "low_freq_group_delay_us": 50.0,
    }
    d2 = {"two_state": bode_m, "four_state": bode_m, "six_state": bode_m, "bw_ratio_4state_to_6state": 1.5}
    (tmp_path / "dyn02_freq_response.json").write_text(json.dumps(d2), encoding="utf-8")

    reg_m = {
        "freqs_Hz": [10.0, 100.0, 1000.0],
        "psd_deg2_h2_per_Hz": [10.0, 1.0, 0.5],
        "asd_deg_h_per_rtHz": [3.16, 1.0, 0.7],
        "cum_rms_deg_per_h": [10.0, 20.0, 30.0],
    }
    d3 = {
        "regimes": {"white_linear": reg_m, "full_2state": reg_m, "full_4state": reg_m, "full_6state": reg_m},
        "analytical_white_ref": {"psd_white_deg2_h2_per_Hz": 1.0, "arw_analytical_deg_per_rt_h": 0.005},
        "low_freq_6state_suppression_dB": 25.0,
    }
    (tmp_path / "dyn03_output_psd.json").write_text(json.dumps(d3), encoding="utf-8")
    figs = plot_dyn_scenarios(tmp_path, tmp_path / "dyn_figs")
    assert len(figs) == 3


def test_sim_runner_cli_industrial_mode_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify all 7 new ind_* CLI modes dispatch cleanly in sim_runner_cli."""
    called: list[str] = []
    monkeypatch.setattr(sim_runner_cli, "ensure_sim_binary", lambda p, auto_build=False: Path(p))
    monkeypatch.setattr(sim_runner_cli, "run_ind01_lab_validation", lambda *a, **kw: called.append("ind01"))
    monkeypatch.setattr(sim_runner_cli, "run_ind02_fixed_point_rtl", lambda *a, **kw: called.append("ind02"))
    monkeypatch.setattr(sim_runner_cli, "run_ind03_fem_3d", lambda *a, **kw: called.append("ind03"))
    monkeypatch.setattr(sim_runner_cli, "run_ind04_random_vib_psd", lambda *a, **kw: called.append("ind04"))
    monkeypatch.setattr(sim_runner_cli, "run_ind05_fmu_multi_instance", lambda *a, **kw: called.append("ind05"))
    monkeypatch.setattr(sim_runner_cli, "run_ind06_pvt_aging_corners", lambda *a, **kw: called.append("ind06"))
    monkeypatch.setattr(sim_runner_cli, "run_all_industrial_scenarios", lambda *a, **kw: called.append("ind_all"))
    monkeypatch.setattr(
        sim_runner_cli,
        "export_run_report",
        lambda run_dir, **kw: {"report_dir": str(tmp_path / "rep"), "report_meta": {"overall_status": "PASS"}, "generated_artifacts": []},
    )

    for mode in (
        "ind_lab_validation",
        "ind_fixed_point_rtl",
        "ind_fem_3d",
        "ind_random_vib_psd",
        "ind_fmu_multi_instance",
        "ind_pvt_aging_corners",
        "ind_all",
    ):
        sim_runner_cli.run_simulation_workflow(
            mode=mode,
            cfg_path=BASE_CFG_PATH,
            bin_path=BIN_PATH,
            data_root=tmp_path / "data",
            report_root=tmp_path / "report",
            run_id=f"r_{mode}",
        )
    assert called == ["ind01", "ind02", "ind03", "ind04", "ind05", "ind06", "ind_all"]
