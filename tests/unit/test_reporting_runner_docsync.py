"""Unit tests achieving 100% line coverage across viz/export_report.py,
tier3_analysis/sim_runner_cli.py, and tier3_analysis/doc_sync.py (AGENT.md Rules 2, 14, 16).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tier1_offline.config_loader import deep_merge, load_config
from tier3_analysis import doc_sync, sim_runner_cli
from viz import export_report

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASE_CFG = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.unit
def test_export_report_md_html_and_index_100pct(tmp_path: Path) -> None:
    """Exercise every Markdown, HTML, status, and centralized report/index branch."""
    assert export_report.get_project_version(REPO_ROOT) == "1.1.0"
    assert export_report.get_project_version(tmp_path) == "0.0.0"
    assert export_report._fmt_num(None) == "N/A"
    assert export_report._fmt_num(1.2345, ".2f") == "1.23"

    # Build a rich run directory with ALL sections (Tier 1, Tier 2, Gate 1..4, PSD, Sweep, AVAR)
    run_dir = tmp_path / "data_run"
    report_root = tmp_path / "report"
    rep_dir = report_root / "full_rich"
    cfg = deep_merge(
        load_config(BASE_CFG),
        {
            "ablation_flags": {"en_shupe": True},
            "simulation": {"duration_s": 0.35, "decimation_tau": 4, "dump_micro_ms": 0.05},
            "slow_scale": {"f_dec_Hz": 20.0, "duration_hours": 0.05},
        },
    )
    sim_runner_cli.run_single_simulation(SIM_BIN, cfg, run_dir, duration_s=0.35, dump_micro_ms=0.05)

    # Add Gate 1, Gate 2, Gate 3, and Gate 4 synthetic-container metrics from real Tier 2 sim_out.bin
    sim_bytes = (run_dir / "sim_out.bin").read_bytes()
    (run_dir / "psd_linear.bin").write_bytes(sim_bytes)
    (run_dir / "psd_nonlinear.bin").write_bytes(sim_bytes)
    (run_dir / "gate1_metrics.json").write_text(
        json.dumps(
            {
                "small_signal_err_rad": 1e-13,
                "flyback_count": 1500,
                "final_eps_vpi_eff": 1e-10,
                "gate1_pass": True,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "sweep_results.json").write_text(
        json.dumps(
            {
                "rates_in_deg_per_s": [-0.2, 0.0, 0.2],
                "uncompensated_out_deg_per_s": [-0.15, 0.01, 0.15],
                "compensated_out_deg_per_s": [-0.2, 0.0, 0.2],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "nonlinearity_summary.json").write_text(
        json.dumps(
            {
                "uncompensated": {
                    "deadband_peak_err_deg_per_s": 0.08,
                    "deadband_width_deg_per_s": 0.04,
                    "bunny_ears_peak_sf_ppm": 250000.0,
                },
                "compensated": {
                    "deadband_peak_err_deg_per_s": 1e-5,
                    "deadband_width_deg_per_s": 0.0,
                    "bunny_ears_peak_sf_ppm": 100.0,
                },
                "deadband_reduction_pct": 99.9,
                "bunny_ears_sf_reduction_pct": 99.9,
                "gate2_pass": True,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "k_matrix.json").write_text(
        json.dumps(
            {
                "K_physical_vector": [1e-3, 2e-3, 3e-3],
                "K_node_unit_vector": [1e-4, 1e-4, 1e-4],
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "gate3_metrics.json").write_text(
        json.dumps(
            {
                "slope_linear": 0.02,
                "slope_nonlinear": -0.98,
                "k_repeatability_max_rel_pct": 0.05,
                "gate3_pass": True,
            }
        ),
        encoding="utf-8",
    )
    from tier3_analysis.dual_regime_avar import run_dual_regime_avar

    run_dual_regime_avar(run_dir, cfg_path=run_dir / "cfg.json", slow_ensemble=1)

    rc = export_report.main(
        [
            "--run",
            str(run_dir),
            "--report-dir",
            str(rep_dir),
            "--format",
            "png,md,html",
            "--mode",
            "full",
            "--update-index",
        ]
    )
    assert rc == 0
    assert (rep_dir / "report.md").exists()
    assert (rep_dir / "report.html").exists()
    assert (rep_dir / "metrics_summary.json").exists()
    assert (run_dir / "metrics_summary.json").exists()
    assert (report_root / "index.md").exists()
    assert (report_root / "index.html").exists()

    md_text = (rep_dir / "report.md").read_text(encoding="utf-8")
    assert "Executive Gate & Run Status" in md_text
    assert "Peak Thermal Shupe Phase" in md_text
    assert "Gate 2 — Deadband & Bunny Ears" in md_text
    assert "Gate 3 — 1/f Flicker" in md_text
    assert "Gate 4 — Dual-Regime Overlapping AVAR" in md_text

    # Cover index edge cases: non-dir file, dir without metrics_summary.json, FAIL status, INFO status, missing md/html
    (report_root / "README.md").write_text("index test\n", encoding="utf-8")
    (report_root / "empty_subdir").mkdir()
    fail_dir = report_root / "fail_case"
    fail_dir.mkdir()
    (fail_dir / "metrics_summary.json").write_text(
        json.dumps(
            {
                "report_meta": {
                    "run_id": "fail_case",
                    "mode": "gate1",
                    "version": "1.1.0",
                    "generated_utc": "2026-11-25T00:00:00Z",
                    "overall_status": "FAIL",
                }
            }
        ),
        encoding="utf-8",
    )
    info_dir = report_root / "info_case"
    export_report.export_run_report(tmp_path / "empty_in", formats=("html",), report_dir=info_dir, update_index=True)

    # Also cover sim_summary-only fallback row + FAIL HTML pill
    only_sim = tmp_path / "only_sim"
    only_sim.mkdir()
    (only_sim / "sim_summary.json").write_text(
        json.dumps(
            {
                "total_tau_steps": 400,
                "total_records_written": 100,
                "flyback_count": 0,
                "adc_clip_count": 0,
                "final_delta_phi_step_rad": 0.0,
                "final_eps_vpi_eff": 0.0,
                "mean_omega_out_second_half_rad_per_s": 0.0,
            }
        ),
        encoding="utf-8",
    )
    s_only = export_report.export_run_report(only_sim, formats=("md", "html"))
    assert s_only["report_meta"]["overall_status"] == "PASS"

    fail_run = tmp_path / "fail_run"
    fail_run.mkdir()
    (fail_run / "gate1_metrics.json").write_text(
        json.dumps({"small_signal_err_rad": 1.0, "flyback_count": 0, "final_eps_vpi_eff": 0.1, "gate1_pass": False}),
        encoding="utf-8",
    )
    s_fail = export_report.export_run_report(fail_run, formats=("md", "html"))
    assert s_fail["report_meta"]["overall_status"] == "FAIL"


@pytest.mark.unit
def test_sim_runner_cli_all_modes_and_error_branches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise all simulation runner modes, auto-build, and CLI arguments for 100% coverage."""
    # ensure_sim_binary error & auto_build branches
    missing_bin = tmp_path / "missing_build" / "ifog_sim"
    with pytest.raises(FileNotFoundError, match="Tier 2 binary not found"):
        sim_runner_cli.ensure_sim_binary(missing_bin, auto_build=False)

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(cmd)
        missing_bin.parent.mkdir(parents=True, exist_ok=True)
        missing_bin.write_text("#!/bin/sh\n", encoding="utf-8")
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(sim_runner_cli.subprocess, "run", fake_run)
    built = sim_runner_cli.ensure_sim_binary(missing_bin, auto_build=True)
    assert built == missing_bin and len(calls) == 2
    monkeypatch.undo()

    # Unsupported mode error branch
    with pytest.raises(ValueError, match="Unsupported simulation mode"):
        sim_runner_cli.run_simulation_workflow("invalid_mode", bin_path=SIM_BIN)

    # Compact 3-point sweep spec for fast unit execution of gate2 / sweep / full
    mini_ramp = {
        "sweep_name": "unit_mini_ramp",
        "base_config": str(BASE_CFG),
        "rates_deg_per_s": [-0.05, 0.0, 0.05],
        "duration_per_point_s": 0.004,
        "decimation_tau": 4,
        "uncompensated_overrides": {
            "dsp": {"en_vpi_loop": False, "en_adc_blanking": False, "en_prbs_dither": False},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
        },
        "compensated_overrides": {
            "dsp": {"en_vpi_loop": True, "en_adc_blanking": True, "en_prbs_dither": True},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
        },
    }
    ramp_p = tmp_path / "mini_ramp.json"
    ramp_p.write_text(json.dumps(mini_ramp), encoding="utf-8")

    mini_mc = {
        "sweep_name": "unit_mini_mc",
        "base_config": str(BASE_CFG),
        "seeds": [7],
        "duration_per_point_s": 0.003,
        "decimation_tau": 4,
        "scenarios": [{"label": "clean", "overrides": {"noise": {"en_white_noise": False}}}],
    }
    mc_p = tmp_path / "mini_mc.json"
    mc_p.write_text(json.dumps(mini_mc), encoding="utf-8")

    data_root = tmp_path / "data"
    rep_root = tmp_path / "report"

    # 1. single via main() CLI (also exercises auto run_id=None)
    rc = sim_runner_cli.main(
        [
            "--mode",
            "single",
            "--cfg",
            str(BASE_CFG),
            "--bin",
            str(SIM_BIN),
            "--data-dir",
            str(data_root),
            "--report-dir",
            str(rep_root),
            "--duration-s",
            "0.005",
        ]
    )
    assert rc == 0
    assert (rep_root / "index.md").exists() and (rep_root / "index.html").exists()

    # 2. gate1
    s1 = sim_runner_cli.run_simulation_workflow(
        "gate1", cfg_path=BASE_CFG, bin_path=SIM_BIN, data_root=data_root, report_root=rep_root, run_id="u_g1"
    )
    assert s1["gate1_metrics"]["gate1_pass"] is True

    # 3. gate2
    s2 = sim_runner_cli.run_simulation_workflow(
        "gate2",
        cfg_path=BASE_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_g2",
        sweep_path=ramp_p,
        workers=2,
    )
    assert s2["nonlinearity_summary"] is not None

    # 4. gate3 (short unit duration)
    s3 = sim_runner_cli.run_simulation_workflow(
        "gate3",
        cfg_path=BASE_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_g3",
        gate3_duration_s=0.25,
        k_duration_s=0.05,
    )
    assert s3["gate3_metrics"] is not None

    # 5. gate4 (short unit duration with valid >=0.1s overlap window)
    s4 = sim_runner_cli.run_simulation_workflow(
        "gate4",
        cfg_path=BASE_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_g4",
        fast_duration_s=0.35,
        fast_ensemble=2,
        slow_ensemble=1,
        slow_duration_hours=0.05,
        k_duration_s=0.05,
        workers=2,
    )
    assert s4["avar_metrics"] is not None

    # 6. sweep (both ramp -> sweep_results.json exists AND mc -> no sweep_results.json)
    sim_runner_cli.run_simulation_workflow(
        "sweep",
        cfg_path=BASE_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_sw_ramp",
        sweep_path=ramp_p,
        workers=2,
    )
    sim_runner_cli.run_simulation_workflow(
        "sweep",
        cfg_path=BASE_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_sw_mc",
        sweep_path=mc_p,
        workers=1,
    )

    # 7. full (unified 4-gate orchestration)
    s_full = sim_runner_cli.run_simulation_workflow(
        "full",
        cfg_path=BASE_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_full",
        sweep_path=ramp_p,
        fast_duration_s=0.35,
        fast_ensemble=2,
        slow_ensemble=1,
        slow_duration_hours=0.05,
        gate3_duration_s=0.25,
        k_duration_s=0.05,
        workers=2,
    )
    assert (rep_root / "u_full" / "report.md").exists()
    assert (rep_root / "u_full" / "report.html").exists()
    assert s_full["gate1_metrics"] is not None and s_full["avar_metrics"] is not None


@pytest.mark.unit
def test_doc_sync_rule16_pass_and_all_failure_branches(tmp_path: Path) -> None:
    """Exercise 100% of tier3_analysis/doc_sync.py (Rule 16 version-doc sync checks)."""
    # 1. Live repository must pass Rule 16 cleanly (with and without expected tag + json_out)
    json_out = tmp_path / "sync_report.json"
    rc = doc_sync.main(
        ["--repo-root", str(REPO_ROOT), "--expected-tag", "v1.1.0", "--json-out", str(json_out)]
    )
    assert rc == 0
    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["ok"] is True and report["version"] == "1.1.0"

    # 2. Error branches for read_pyproject_version & compute_tex_sha256_manifest
    with pytest.raises(FileNotFoundError, match="Missing pyproject.toml"):
        doc_sync.read_pyproject_version(tmp_path / "no_repo")

    bad_repo = tmp_path / "bad_ver"
    bad_repo.mkdir()
    (bad_repo / "pyproject.toml").write_text('[project]\nname="x"\nversion="1.0-rc1"\n', encoding="utf-8")
    with pytest.raises(ValueError, match="not valid SemVer"):
        doc_sync.read_pyproject_version(bad_repo)

    with pytest.raises(FileNotFoundError, match="Missing LaTeX document"):
        doc_sync.compute_tex_sha256_manifest(bad_repo)

    # 3. Synthetic isolated copy testing --write-checksums, blank lines, missing files, tag mismatch, stale PDFs
    sandbox = tmp_path / "sandbox"
    (sandbox / "docs").mkdir(parents=True)
    for rel in (
        "pyproject.toml",
        "README.md",
        "AGENT.md",
        "docs/IFOG_VPROTO_ARCHITECTURE.md",
        "docs/IFOG_VPROTO_ARCHITECTURE.tex",
        "docs/IFOG_VPROTO_ARCHITECTURE.pdf",
        "docs/RELEASE_NOTES.md",
        "docs/RELEASE_NOTES.tex",
        "docs/RELEASE_NOTES.pdf",
        "docs/CHANGELOG.md",
    ):
        shutil.copy2(REPO_ROOT / rel, sandbox / rel)

    # Missing DOCS_BUILD.sha256 branch + mismatched expected_tag branch -> exit 1
    assert doc_sync.main(["--repo-root", str(sandbox), "--expected-tag", "v9.9.9"]) == 1

    # Write checksums via CLI + append blank line to exercise blank-line parser skip
    assert doc_sync.main(["--repo-root", str(sandbox), "--write-checksums"]) == 0
    sha_p = sandbox / "docs" / "DOCS_BUILD.sha256"
    sha_p.write_text(sha_p.read_text(encoding="utf-8") + "\n\n", encoding="utf-8")
    assert doc_sync.main(["--repo-root", str(sandbox), "--expected-tag", "v1.1.0"]) == 0

    # Tamper .tex (stale PDF checksum), remove CHANGELOG (missing file), truncate PDF (empty PDF), mismatch README
    (sandbox / "docs" / "RELEASE_NOTES.tex").write_text("% drifted\n", encoding="utf-8")
    (sandbox / "docs" / "CHANGELOG.md").unlink()
    (sandbox / "docs" / "RELEASE_NOTES.pdf").write_bytes(b"tiny")
    (sandbox / "README.md").write_text("# stale readme\n", encoding="utf-8")
    res_bad = doc_sync.verify_doc_version_sync(sandbox)
    assert res_bad["ok"] is False
    assert any("Stale PDF checksum" in e for e in res_bad["errors"])
    assert any("Missing required synchronized document" in e for e in res_bad["errors"])
    assert any("Compiled PDF missing or empty" in e for e in res_bad["errors"])
    assert any("README.md" in e for e in res_bad["errors"])
