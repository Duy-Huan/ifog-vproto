"""Full Real End-to-End System Verification for IFOG-SIM-SPEC-006 FMI 3.0 Co-Simulation FMU (Gate 6).

Executes genuine compiled build/ifog_core.fmu via FMPy (zero mocks, zero smoke tests, Rule 5):
  - Gate 6A: Official FMI 3.0 XML Schema & ZIP compliance via fmpy.validation.validate_fmu
  - Gate 6B: Bit-exact (< 1e-12 rad/s) equivalence vs standalone build/ifog_sim (4-state & 6-state)
  - Gate 6C: Slow Rate Ramp staircase deadband sweep across 0 deg/h (enable_dither=False vs True)
  - Gate 6D: Full 60 s x 4-seed FMU fast-scale + 10 h x 12-seed Slow-Scale 5-region IEEE 952 AVAR
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tier3_analysis.fmi_master_runner import run_fmi_gate_suite
from viz.export_report import export_run_report

REPO_ROOT = Path(__file__).resolve().parents[2]
FMU_PATH = REPO_ROOT / "build" / "ifog_core.fmu"
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"


@pytest.mark.system
@pytest.mark.gate
@pytest.mark.regression
def test_gate6_fmi3_fmu_full_end_to_end(tmp_path: Path) -> None:
    """Real full-scale Gate 6 FMI 3.0 Co-Simulation FMU verification + auto-report export."""
    assert FMU_PATH.exists(), "build/ifog_core.fmu missing; build with cmake --build build --target package_fmu"
    assert SIM_BIN.exists(), "build/ifog_sim missing; build Tier 2 first"

    summary = run_fmi_gate_suite(
        fmu_path=FMU_PATH,
        bin_path=SIM_BIN,
        out_dir=tmp_path / "gate6",
        fast_avar_duration_s=60.0,
        fast_ensemble=4,
        step_size_s=1.0e-3,
        slow_ensemble=12,
    )

    assert summary["validation"]["validation_pass"] is True
    assert summary["validation"]["validation_problems"] == []
    assert summary["validation"]["fmi_version"] == "3.0"
    assert summary["validation"]["can_be_instantiated_only_once_per_process"] is True

    assert summary["equivalence"]["equivalence_pass"] is True
    assert summary["equivalence"]["max_final_omega_err_rad_per_s"] < 1.0e-12

    assert summary["deadband"]["deadband_pass"] is True
    assert summary["deadband"]["deadband_reduction_pct"] >= 90.0

    assert summary["avar"]["avar_pass"] is True
    assert summary["avar"]["overlap_check"]["continuity_pass_lt_5pct"] is True
    assert summary["avar"]["max_5region_param_err_pct"] <= 10.0

    assert summary["fmi_gate_pass"] is True

    rep_dir = tmp_path / "rep_gate6"
    rep = export_run_report(tmp_path / "gate6", formats=("png", "md", "html"), report_dir=rep_dir)
    assert rep["report_meta"]["overall_status"] == "PASS"
    assert (rep_dir / "figures" / "fmi_fmu_gate.png").exists()
    assert (rep_dir / "report.md").exists()
    assert (rep_dir / "report.html").exists()
