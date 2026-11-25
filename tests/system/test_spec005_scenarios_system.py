"""Full Real End-to-End System Tests for IFOG-SIM-SPEC-005 (6-State DSP, TD-01..TD-06, ENG-01..ENG-05).

Executes genuine compiled Tier 2 C++ SystemC-AMS binaries (zero mocks, zero smoke tests, Rule 5).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tier1_offline.config_loader import load_config
from tier3_analysis.scenarios_engineering import run_all_engineering_scenarios
from tier3_analysis.scenarios_time_domain import run_all_time_domain_scenarios, run_dsp6_comparison
from viz.export_report import export_run_report

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASELINE_CFG = REPO_ROOT / "configs" / "baseline_1km.json"
BASELINE_6STATE_CFG = REPO_ROOT / "configs" / "baseline_1km_6state.json"


@pytest.mark.system
@pytest.mark.gate
def test_gate5_official_6state_dsp_system(tmp_path: Path) -> None:
    """Gate 5: Real 6-state symmetric DSP (alpha=pi/3) static precision, V_pi lock & >40 dB RAM/xtalk rejection."""
    assert SIM_BIN.exists(), "Compiled Tier 2 binary build/ifog_sim must exist"
    cfg6 = load_config(BASELINE_6STATE_CFG)
    assert cfg6["dsp"]["mode"] == "6state"
    res = run_dsp6_comparison(SIM_BIN, cfg6, tmp_path)
    assert res["dsp6_pass"] is True
    assert res["six_state"]["static_err_rad"] < 1.0e-9
    assert res["six_state"]["final_eps_vpi_eff"] < 1.0e-5
    assert res["ram_xtalk_rejection_dB"] > 40.0
    assert res["six_state"]["e_asym_rms_counts"] > 10.0


@pytest.mark.system
def test_all_6_time_domain_scenarios_system(tmp_path: Path) -> None:
    """Real full execution of all 6 SPEC-005 Time-Domain scenarios (TD-01 .. TD-06) + auto-report."""
    cfg = load_config(BASELINE_CFG)
    res = run_all_time_domain_scenarios(SIM_BIN, cfg, tmp_path)
    assert res["all_passed"] is True
    for sid in ("TD-01", "TD-02", "TD-03", "TD-04", "TD-05", "TD-06"):
        assert res["scenarios"][sid]["pass"] is True, f"{sid} failed: {res['scenarios'][sid]}"
    rep = export_run_report(tmp_path, formats=("png", "md", "html"), report_dir=tmp_path / "rep")
    assert rep["report_meta"]["overall_status"] == "PASS"
    assert (tmp_path / "rep" / "report.md").exists()
    assert (tmp_path / "rep" / "report.html").exists()


@pytest.mark.system
def test_all_5_engineering_scenarios_system(tmp_path: Path) -> None:
    """Real full execution of all 5 SPEC-005 System Engineering scenarios (ENG-01 .. ENG-05) + CSV dataset."""
    cfg = load_config(BASELINE_CFG)
    res = run_all_engineering_scenarios(SIM_BIN, cfg, tmp_path, mc_runs=32)
    assert res["all_passed"] is True
    for sid in ("ENG-01", "ENG-02", "ENG-03", "ENG-04", "ENG-05"):
        assert res["scenarios"][sid]["pass"] is True, f"{sid} failed: {res['scenarios'][sid]}"
    # Verify ENG-02 6-state beats 4-state on inter-axis crosstalk & ENG-04 detects all 5 faults
    eng02 = res["scenarios"]["ENG-02"]
    assert eng02["inter_axis_y_crosstalk_6state_deg_per_h"] < eng02["inter_axis_y_crosstalk_4state_deg_per_h"]
    eng04 = res["scenarios"]["ENG-04"]
    assert len(eng04["cases"]) == 5 and all(c["pass"] for c in eng04["cases"])
    assert (tmp_path / "virtual_calibration_dataset.csv").exists()
    rep = export_run_report(tmp_path, formats=("png", "md", "html"), report_dir=tmp_path / "rep")
    assert rep["report_meta"]["overall_status"] == "PASS"
    assert (tmp_path / "rep" / "virtual_calibration_dataset.csv").exists()
    assert json.loads((tmp_path / "rep" / "metrics_summary.json").read_text())["spec_id"] == "IFOG-SIM-SPEC-005"
