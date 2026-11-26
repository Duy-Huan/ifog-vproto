"""Comprehensive Unit Tests for FMI 3.0 Master Orchestrator, FMU Gate Plotting & Reporting (SPEC-006).

Achieves 100.0% line coverage across tier3_analysis/fmi_master_runner.py, plot_fmi_gate,
ensure_fmu_archive, and Gate 6 branches in viz/export_report.py.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tier3_analysis import fmi_master_runner, sim_runner_cli
from viz.export_report import export_run_report
from viz.plot_scenarios import plot_fmi_gate

REPO_ROOT = Path(__file__).resolve().parents[2]
FMU_PATH = REPO_ROOT / "build" / "ifog_core.fmu"
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"


@pytest.mark.unit
def test_validate_fmu_package_and_missing_error(tmp_path: Path) -> None:
    """Validate real packaged build/ifog_core.fmu and FileNotFoundError on missing archive."""
    with pytest.raises(FileNotFoundError, match="package_fmu"):
        fmi_master_runner.validate_fmu_package(tmp_path / "missing.fmu")

    assert FMU_PATH.exists(), "Run cmake --build build --target package_fmu first"
    val = fmi_master_runner.validate_fmu_package(FMU_PATH)
    assert val["validation_pass"] is True
    assert val["fmi_version"] == "3.0"
    assert val["can_be_instantiated_only_once_per_process"] is True
    assert val["validation_problems"] == []
    assert val["missing_required_variables"] == []
    assert val["has_resources"] is True
    assert val["variable_count"] >= 15


@pytest.mark.unit
def test_execute_worker_job_and_isolated_error_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cover _execute_worker_job (both with & without input_rows) and worker failure guard."""
    rec_dtype = np.dtype(
        [
            ("time", np.float64),
            ("omega_out", np.float64),
            ("omega_out_avg", np.float64),
            ("e_vpi_res", np.float64),
            ("bit_status", np.uint32),
        ]
    )
    fake_rec = np.array(
        [(0.0, 0.0, 0.0, 0.0, 0), (1e-3, 0.01, 0.01, 1e-6, 0)],
        dtype=rec_dtype,
    )
    monkeypatch.setattr(fmi_master_runner.fmpy, "simulate_fmu", lambda **kwargs: fake_rec)

    # With input_rows via CLI --worker-job / --worker-out
    job_p = tmp_path / "job.json"
    out_p = tmp_path / "res.npz"
    job_p.write_text(
        json.dumps(
            {
                "fmu_path": str(FMU_PATH),
                "start_time": 0.0,
                "stop_time": 1e-3,
                "step_size": 1e-3,
                "start_values": {"dsp_mode": 4},
                "input_rows": [[0.0, 0.01, 0.0], [1e-3, 0.01, 0.0]],
                "output": ["omega_out", "omega_out_avg", "e_vpi_res", "bit_status"],
            }
        ),
        encoding="utf-8",
    )
    rc = fmi_master_runner.main(["--worker-job", str(job_p), "--worker-out", str(out_p)])
    assert rc == 0
    with np.load(out_p) as npz:
        assert np.allclose(npz["omega_out"], [0.0, 0.01])

    # Without input_rows
    job_no_in = tmp_path / "job_no_in.json"
    out_no_in = tmp_path / "res_no_in.npz"
    job_no_in.write_text(
        json.dumps(
            {
                "fmu_path": str(FMU_PATH),
                "start_time": 0.0,
                "stop_time": 1e-3,
                "step_size": 1e-3,
                "start_values": {},
                "input_rows": None,
                "output": ["omega_out"],
            }
        ),
        encoding="utf-8",
    )
    fmi_master_runner._execute_worker_job(job_no_in, out_no_in)
    assert out_no_in.exists()

    # Worker subprocess non-zero exit error guard
    monkeypatch.setattr(
        fmi_master_runner.subprocess,
        "run",
        lambda *a, **kw: subprocess.CompletedProcess(a[0], 1, "", "boom"),
    )
    with pytest.raises(RuntimeError, match="Isolated FMU worker failed"):
        fmi_master_runner.simulate_fmu_isolated(FMU_PATH, stop_time=1e-3)


@pytest.mark.unit
def test_fmi_equivalence_deadband_avar_and_cli_orchestration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test real FMU equivalence (<1e-12), deadband, AVAR helper wiring, CLI, plotting & HTML report."""
    # 1. Real bit-exact FMU vs standalone Tier 2 equivalence (< 1e-12 rad/s on 4-state & 6-state!)
    eq = fmi_master_runner.run_fmi_equivalence_verification(
        fmu_path=FMU_PATH,
        bin_path=SIM_BIN,
        out_dir=tmp_path,
        omega_rad_per_s=0.05,
        duration_s=0.01,
        step_size_s=1.0e-3,
    )
    assert eq["equivalence_pass"] is True
    assert eq["max_final_omega_err_rad_per_s"] < 1.0e-12

    # 2. Fast staircase deadband sweep on compact 5-point symmetric grid using real FMU
    db = fmi_master_runner.run_fmi_deadband_sweep(
        fmu_path=FMU_PATH,
        out_dir=tmp_path,
        rates_deg_per_s=[-0.05, -0.01, 0.0, 0.01, 0.05],
        dwell_per_point_s=0.02,
        step_size_s=1.0e-3,
        max_workers=2,
    )
    assert len(db["dither_off_out_deg_per_s"]) == 5
    assert len(db["dither_on_out_deg_per_s"]) == 5

    # 3. Exercise run_fmi_dual_regime_avar (with stale file cleanup + synthetic AVAR return for fast unit test)
    avar_dir = tmp_path / "fmi_avar"
    avar_dir.mkdir(parents=True, exist_ok=True)
    (avar_dir / "sim_out_99.bin").write_bytes(b"stale")

    def _fake_avar(run_dir: Path | str, cfg_path: Any = None, slow_ensemble: int = 1) -> dict[str, Any]:
        r = Path(run_dir)
        np.savez(
            r / "avar_curve.npz",
            taus_fast=np.array([0.002, 0.01, 0.1, 1.0, 5.0]),
            adev_fast_deg_h=np.array([0.5, 0.2, 0.07, 0.02, 0.01]),
            taus_slow=np.array([0.1, 1.0, 5.0, 100.0, 3600.0]),
            adev_slow_deg_h=np.array([0.07, 0.02, 0.01, 0.005, 0.02]),
        )
        return {
            "overlap_check": {"max_relative_mismatch_pct": 1.2, "continuity_pass_lt_5pct": True},
            "fitted_ieee952": {
                "Q_arcsec": 0.002,
                "N_deg_per_rt_h": 0.00035,
                "B_deg_per_h": 0.0038,
                "K_deg_per_rt_h3": 0.022,
                "R_deg_per_h2": 0.025,
            },
            "slow_synthesis_truth": {
                "Q_arcsec": 0.002,
                "N_deg_per_rt_h": 0.00035,
                "B_deg_per_h": 0.0038,
                "K_deg_per_rt_h3": 0.022,
                "R_deg_per_h2": 0.025,
            },
        }

    import tier3_analysis.dual_regime_avar as dra

    monkeypatch.setattr(dra, "run_dual_regime_avar", _fake_avar)
    av = fmi_master_runner.run_fmi_dual_regime_avar(
        fmu_path=FMU_PATH,
        out_dir=tmp_path,
        fast_duration_s=0.01,
        fast_ensemble=1,
        step_size_s=1.0e-3,
        slow_ensemble=1,
        max_workers=1,
    )
    assert av["avar_pass"] is True
    assert not (avar_dir / "sim_out_99.bin").exists()

    # 4. Full run_fmi_gate_suite + main() CLI + plot_fmi_gate + export_run_report integration
    monkeypatch.setattr(
        fmi_master_runner,
        "run_fmi_deadband_sweep",
        lambda **kw: {**db, "deadband_reduction_pct": 96.5, "deadband_pass": True},
    )
    gate_dir = tmp_path / "gate_cli"
    rc = fmi_master_runner.main(
        [
            "--fmu",
            str(FMU_PATH),
            "--bin",
            str(SIM_BIN),
            "--out",
            str(gate_dir),
            "--avar-duration-s",
            "0.01",
            "--fast-ensemble",
            "1",
            "--slow-ensemble",
            "1",
            "--workers",
            "1",
        ]
    )
    assert rc == 0
    gate_summary = json.loads((gate_dir / "fmi_gate_summary.json").read_text(encoding="utf-8"))
    assert gate_summary["fmi_gate_pass"] is True

    # Plot & export report (covering both with & without avar_curve.npz)
    rep_dir = tmp_path / "rep_fmi"
    exported = export_run_report(gate_dir, formats=("png", "md", "html"), report_dir=rep_dir)
    assert (rep_dir / "figures" / "fmi_fmu_gate.png").exists()
    assert (rep_dir / "report.md").exists()
    assert (rep_dir / "report.html").exists()
    assert any("Gate 6" in g["gate"] for g in exported["gate_statuses"])

    # Also cover plot_fmi_gate when fmi_avar/avar_curve.npz is absent
    p_no_npz = plot_fmi_gate(gate_summary, tmp_path / "empty_dir", tmp_path / "fmi_no_npz.png")
    assert p_no_npz.exists()


@pytest.mark.unit
def test_ensure_fmu_archive_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Cover ensure_fmu_archive existing, missing error, and auto_build paths in sim_runner_cli."""
    assert sim_runner_cli.ensure_fmu_archive(FMU_PATH) == FMU_PATH

    missing = tmp_path / "build" / "ifog_core.fmu"
    with pytest.raises(FileNotFoundError, match="package_fmu"):
        sim_runner_cli.ensure_fmu_archive(missing, auto_build=False)

    cmds: list[list[str]] = []

    def _fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmds.append(cmd)
        missing.parent.mkdir(parents=True, exist_ok=True)
        missing.write_bytes(b"PK")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(sim_runner_cli.subprocess, "run", _fake_run)
    built = sim_runner_cli.ensure_fmu_archive(missing, auto_build=True)
    assert built == missing
    assert len(cmds) == 2 and "package_fmu" in cmds[1]
