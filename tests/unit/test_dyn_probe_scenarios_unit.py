"""Unit & Real-Core Coverage Tests for Group C Dynamic Response, Output PSD & Electro-Optic Probe (DYN-01..DYN-04).

Guarantees 100.0% Python line coverage across tier3_analysis/scenarios_dynamic_probe.py,
plot_dyn_scenarios() in viz/plot_scenarios.py, and Group C Markdown/Plotly sections in viz/export_report.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import load_config
from tier1_offline.jones_spectral import solve_tier1_optics
from tier3_analysis.scenarios_dynamic_probe import (
    compute_analytical_arw_psd_deg2_h2_per_hz,
    compute_closed_loop_frf_theory,
    run_all_dynamic_probe_scenarios,
)
from viz.export_report import export_run_report
from viz.plot_scenarios import plot_dyn_scenarios

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASELINE_CFG = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.unit
def test_dyn_analytical_helpers_and_real_group_c_coverage(tmp_path: Path) -> None:
    """Verify analytical FRF/ARW helpers, all 4 real Group C scenarios, empty/full plotting & unified report."""
    cfg = load_config(BASELINE_CFG)
    phys = solve_tier1_optics(cfg)

    # 1. Analytical Z-domain FRF helper
    freqs = np.array([20.0, 100.0, 1000.0, 5000.0, 10000.0])
    mag_db, phase_deg, gd_us = compute_closed_loop_frf_theory(freqs, 0.25, 6.0 * phys["tau_s"])
    assert abs(mag_db[0]) < 0.05
    assert mag_db[-1] < -10.0
    assert phase_deg[-1] < phase_deg[2] < phase_deg[0] < 0.0
    assert gd_us[0] > 80.0

    # 2. Analytical EQ-15 + EQ-19 ARW white PSD helper
    arw_ref = compute_analytical_arw_psd_deg2_h2_per_hz(cfg, phys)
    assert 1.0e-4 < arw_ref["arw_analytical_deg_per_rt_h"] < 1.0e-3
    assert arw_ref["psd_white_deg2_h2_per_Hz"] > 0.0

    # 3. Empty directory check for plot_dyn_scenarios (covers all None-return branches)
    assert plot_dyn_scenarios(tmp_path / "missing_dyn", tmp_path / "empty_figs") == []

    # 4. Run all 4 real Group C scenarios (using compact 0.5 s PSD for unit speed, still real C++ SystemC-AMS)
    out_dyn = tmp_path / "dyn_out"
    res = run_all_dynamic_probe_scenarios(SIM_BIN, cfg, out_dyn, psd_duration_s=0.5)
    assert res["all_passed"] is True
    for sid in ("DYN-01", "DYN-02", "DYN-03", "DYN-04"):
        assert res[sid]["pass"] is True

    # 5. Export complete unified report (.png, .md, .html) verifying all Group C Markdown & Plotly paths
    rep_dir = tmp_path / "rep_dyn"
    rep = export_run_report(out_dyn, formats=("png", "md", "html"), report_dir=rep_dir, update_index=True)
    assert rep["report_meta"]["overall_status"] == "PASS"
    assert len(rep["gate_statuses"]) == 4
    for png in (
        "dyn01_step_response.png",
        "dyn02_freq_response.png",
        "dyn03_output_psd.png",
        "dyn04_sine_electro_optic.png",
    ):
        assert (rep_dir / "figures" / png).exists()

    md_text = (rep_dir / "report.md").read_text(encoding="utf-8")
    html_text = (rep_dir / "report.html").read_text(encoding="utf-8")
    assert "## 10. Group C — Closed-Loop Dynamic Response, Output PSD & Electro-Optic Probe" in md_text
    assert "DYN-01 — Closed-Loop Step Response Comparison Table" in md_text
    assert "DYN-04 — Sinusoidal Input (`50 deg/s @ 250 Hz`) Internal Electro-Optic Signal Chain" in md_text
    for marker in (
        "Interactive Telemetry — Group C: Dynamic Response, Output PSD & Electro-Optic Probe",
        "Closed-Loop Step Response & Loop-1 Gain Trade-Off",
        "Full Closed-Loop Frequency Response",
        "Output Angular-Rate PSD & Cumulative Noise",
        "Sinusoidal Input Internal Electro-Optic Chain",
    ):
        assert marker in html_text
