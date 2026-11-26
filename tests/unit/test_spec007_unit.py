"""Unit tests achieving 100.0% statement coverage for IFOG-SIM-SPEC-007 Python modules."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tier1_offline import config_loader, jones_spectral, shupe_thermal
from tier3_analysis.dual_regime_avar import DualRegimeStitcher
from tier3_analysis.inverse_calibration import InverseCalibrator
from tier3_analysis.scenarios_spec007 import (
    DEFAULT_SPEC007_CFG,
    run_all_spec007_scenarios,
    run_spec007_calibration,
    run_spec007_physics,
)
from tier3_analysis.sim_runner_cli import run_simulation_workflow
from viz.export_report import export_run_report
from viz.plot_spec007_calibration import (
    plot_spec007_calibration_validation,
    plot_spec007_physics_winding_mioc,
)
from viz.report_narratives import (
    render_narrative_html,
    render_narrative_markdown,
    render_tier_formulas_html,
    render_tier_formulas_markdown,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"


@pytest.mark.unit
def test_spec007_tier1_config_winding_lut_v2_and_cli(tmp_path: Path) -> None:
    """Cover schema_v6, SPEC-007 validation errors, winding errors, FEM v2, and CLI v2."""
    cfg_v6 = config_loader.load_config(DEFAULT_SPEC007_CFG)
    sp7 = config_loader.get_spec007_physics(cfg_v6)
    assert sp7["en_spec007_physics"] is True
    assert sp7["lut_version"] == 2

    # Fail-closed Rule 11: n_turns < n_layers
    bad_cfg = config_loader.deep_merge(cfg_v6, {"spec007_physics": {"n_turns": 8, "n_layers": 16}})
    with pytest.raises(ValueError, match="n_turns"):
        config_loader.validate_config(bad_cfg)

    # Winding validation guards
    with pytest.raises(ValueError, match="Unsupported winding_pattern"):
        shupe_thermal.build_winding_map(1000.0, 0.1, 0.015, 64, 8, winding_pattern="dipole")
    with pytest.raises(ValueError, match="Invalid coil winding dimensions"):
        shupe_thermal.build_winding_map(1000.0, 0.1, 0.015, 4, 8, winding_pattern="quadrupole")

    # Truncated LUT header guard
    trunc = tmp_path / "trunc.bin"
    trunc.write_bytes(b"SHUP")
    with pytest.raises(ValueError, match="Truncated shupe_lut.bin header"):
        shupe_thermal.read_shupe_lut_v2(trunc)

    # Tier 1 optics with SPEC-007 backscatter
    phys = jones_spectral.solve_tier1_optics(cfg_v6)
    assert phys["L_coherence_m"] > 0.0
    assert phys["sigma_phi_back_rad"] > 0.0

    # Tier 1 shupe_thermal CLI writing v2 LUT (with phys_params.json present) and FEM CSV v2 path
    out_v2 = tmp_path / "run_v2"
    out_v2.mkdir()
    (out_v2 / "phys_params.json").write_text(json.dumps(phys), encoding="utf-8")
    short_cfg = config_loader.deep_merge(
        cfg_v6, {"thermal": {"duration_s": 40.0, "dt_s": 10.0}, "spec007_physics": {"n_turns": 64, "n_layers": 8}}
    )
    cfg_file = tmp_path / "short_v6.json"
    cfg_file.write_text(json.dumps(short_cfg), encoding="utf-8")
    assert shupe_thermal.main(["--cfg", str(cfg_file), "--out", str(out_v2)]) == 0
    lut_rd = shupe_thermal.read_shupe_lut_v2(out_v2 / "shupe_lut.bin")
    assert lut_rd["version"] == 2
    assert len(lut_rd["t_s"]) == 5

    # FEM CSV branch inside solve_tier1_shupe_v2
    fem_csv = tmp_path / "fem.csv"
    fem_lines = ["t_s,z_m,dT_dt_K_per_s"]
    for tv in (0.0, 10.0, 20.0):
        for zv in (0.0, 500.0, 1000.0):
            fem_lines.append(f"{tv},{zv},{1e-3 * (zv / 1000.0)}")
    fem_csv.write_text("\n".join(fem_lines) + "\n", encoding="utf-8")
    fem_cfg = config_loader.deep_merge(short_cfg, {"thermal": {"fem_csv_path": str(fem_csv)}})
    ch_fem, sum_fem = shupe_thermal.solve_tier1_shupe_v2(fem_cfg, phys_params=phys)
    assert sum_fem["source_mode"] == "fem_csv"
    assert len(ch_fem["t_s"]) == 3


@pytest.mark.unit
def test_spec007_stitcher_scenarios_plots_cli_and_report(tmp_path: Path) -> None:
    """Cover DualRegimeStitcher, PHY-01, CAL-01, CLI modes, plots, narratives & tier formula docs."""
    # DualRegimeStitcher stitch() method
    stitcher = DualRegimeStitcher(splice_t_s=1.0)
    taus_f = np.geomspace(1e-3, 5.0, 20)
    taus_s = np.geomspace(1e-1, 1e3, 20)
    adev_f = 1e-4 / np.sqrt(taus_f)
    adev_s = 1e-4 / np.sqrt(taus_s)
    st = stitcher.stitch(taus_f, adev_f, taus_s, adev_s)
    assert st["overlap_check"]["continuity_pass_lt_5pct"] is True
    assert len(st["taus_merged"]) > 10

    # Tier-by-Tier formula compendium renderers (Markdown & HTML)
    md_lines = render_tier_formulas_markdown()
    assert any("EQ-01" in ln and "EQ-53" in ln for ln in md_lines)
    html_block = render_tier_formulas_html()
    assert "sec-formulas" in html_block and "EQ-53" in html_block

    # Exercise PHY-01, CAL-01, and CLI modes spec007_physics / spec007_calibration / spec007_all
    assert SIM_BIN.exists(), f"Missing {SIM_BIN}"
    base_v4 = config_loader.load_config(REPO_ROOT / "configs" / "baseline_1km.json")
    phy = run_spec007_physics(SIM_BIN, cfg=base_v4, out_dir=tmp_path / "phy_v4")
    assert phy["passed"] is True
    cal = run_spec007_calibration(SIM_BIN, cfg=base_v4, out_dir=tmp_path / "cal_v4")
    assert cal["passed"] is True

    # Test spec007_physics, spec007_calibration, and spec007_all via unified runner + report export
    rep_root = tmp_path / "reports"
    data_root = tmp_path / "data"
    s_phy = run_simulation_workflow(
        mode="spec007_physics",
        cfg_path=DEFAULT_SPEC007_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_sp7_phy",
    )
    assert s_phy["report_meta"]["overall_status"] == "PASS"

    s_cal = run_simulation_workflow(
        mode="spec007_calibration",
        cfg_path=DEFAULT_SPEC007_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_sp7_cal",
    )
    assert s_cal["report_meta"]["overall_status"] == "PASS"

    s_all = run_simulation_workflow(
        mode="spec007_all",
        cfg_path=DEFAULT_SPEC007_CFG,
        bin_path=SIM_BIN,
        data_root=data_root,
        report_root=rep_root,
        run_id="u_sp7_all",
    )
    assert s_all["report_meta"]["overall_status"] == "PASS"
    assert (rep_root / "u_sp7_all" / "figures" / "fig_spec007_physics_winding_mioc.png").exists()
    assert (rep_root / "u_sp7_all" / "figures" / "fig_spec007_calibration_validation.png").exists()

    md_text = (rep_root / "u_sp7_all" / "report.md").read_text(encoding="utf-8")
    html_text = (rep_root / "u_sp7_all" / "report.html").read_text(encoding="utf-8")
    assert "PHY-01" in md_text and "CAL-01" in md_text and "## 12." in md_text
    assert "sec-formulas" in html_text and "fig_spec007_calibration_validation.png" in html_text

    # Direct narrative render checks
    n_md = render_narrative_markdown("fig_spec007_calibration_validation", s_all)
    n_html = render_narrative_html("fig_spec007_physics_winding_mioc", s_all)
    assert any("CAL-01" in ln for ln in n_md)
    assert "PHY-01" in n_html

    # Direct plotter and run_all_spec007_scenarios standalone call
    all_out = run_all_spec007_scenarios(SIM_BIN, out_dir=tmp_path / "direct_all")
    assert all_out["all_passed"] is True
    p1 = plot_spec007_physics_winding_mioc(
        tmp_path / "direct_all" / "phy01_spec007_physics", tmp_path / "p1.png"
    )
    p2 = plot_spec007_calibration_validation(
        tmp_path / "direct_all" / "cal01_spec007_calibration", tmp_path / "p2.png"
    )
    assert p1.stat().st_size > 10_000 and p2.stat().st_size > 10_000
    export_run_report(tmp_path / "direct_all", formats=("md", "html"), report_dir=tmp_path / "direct_rep")
    assert (tmp_path / "direct_rep" / "report.md").exists()
    assert InverseCalibrator().w_avar == 1.0
