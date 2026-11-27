"""End-to-End System Verification for v4.1.0 Group E Industrial Qualification Suite (IND-01..IND-06)."""

from __future__ import annotations

from pathlib import Path

from tier3_analysis.sim_runner_cli import run_simulation_workflow

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_PATH = REPO_ROOT / "build" / "ifog_sim"
MULTI_FMU = REPO_ROOT / "build" / "ifog_core_multi.fmu"
CFG_SPEC007 = REPO_ROOT / "configs" / "baseline_1km_spec007.json"


def test_system_ind_all_end_to_end(tmp_path: Path) -> None:
    """Run full CLI --mode ind_all with real Tier 2 C++ binary & multi-instance Source-Code FMU."""
    summary = run_simulation_workflow(
        mode="ind_all",
        cfg_path=CFG_SPEC007,
        bin_path=BIN_PATH,
        multi_fmu_path=MULTI_FMU,
        data_root=tmp_path / "data",
        report_root=tmp_path / "report",
        run_id="sys_ind_all_v41",
    )
    assert summary["report_meta"]["overall_status"] == "PASS"
    assert len(summary["gate_statuses"]) == 6
    assert all(g["status"] == "PASS" for g in summary["gate_statuses"])
    rep_dir = Path(summary["report_dir"])
    assert (rep_dir / "report.md").exists()
    assert (rep_dir / "report.html").exists()
    pngs = sorted((rep_dir / "figures").glob("fig_ind0*.png"))
    assert len(pngs) == 6
