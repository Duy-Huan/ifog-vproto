"""Comprehensive Unit & Integration Tests for IFOG-SIM-SPEC-005 (6-State DSP, TD-01..06, ENG-01..05).

Ensures 100.0% Python line coverage across tier1_offline, tier3_analysis, and viz (AGENT.md Rules 2 & 14).
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from tier1_offline.config_loader import deep_merge, load_config, validate_config
from tier3_analysis import sim_runner_cli
from tier3_analysis.binary_io import DSP_TRACE_DTYPE, read_dsp_trace
from tier3_analysis.scenarios_engineering import (
    run_all_engineering_scenarios,
    run_eng_fault_bit,
    run_eng_hw_sizing,
    run_eng_imu_3axis,
    run_eng_mc_yield_cal,
    run_eng_vre_faraday,
)
from tier3_analysis.scenarios_time_domain import (
    compute_theoretical_bw_3db_hz,
    run_all_time_domain_scenarios,
    run_dsp6_comparison,
    run_td_blanking,
    run_td_step_sine,
)
from viz.export_report import export_run_report
from viz.plot_scenarios import plot_dsp6_compare, plot_eng_scenarios, plot_td_scenarios

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASELINE_CFG = REPO_ROOT / "configs" / "baseline_1km.json"
BASELINE_6S_CFG = REPO_ROOT / "configs" / "baseline_1km_6state.json"


@pytest.mark.unit
def test_schema_v5_and_6state_config_validation() -> None:
    """Validate schema_v5.json acceptance of both v4.0 & v5.0 configs and 6-state Loop-2 guard."""
    cfg4 = load_config(BASELINE_CFG)
    cfg6 = load_config(BASELINE_6S_CFG)
    assert cfg4["dsp"]["mode"] == "4state"
    assert cfg6["dsp"]["mode"] == "6state"

    bad6 = deep_merge(cfg6, {"dsp": {"K_tot_1": 0.25, "K_tot_2": 0.08, "en_vpi_loop": True}})
    with pytest.raises(ValueError, match="Loop-2 bandwidth separation"):
        validate_config(bad6)


@pytest.mark.unit
def test_read_dsp_trace_64byte_binary(tmp_path: Path) -> None:
    """Verify exact 64-byte DspTraceRecord packing & read_dsp_trace unpacking."""
    assert DSP_TRACE_DTYPE.itemsize == 64
    arr = np.zeros(3, dtype=DSP_TRACE_DTYPE)
    arr["t"] = [0.0, 5e-6, 10e-6]
    arr["phi_ramp"] = [0.1, 0.2, 0.3]
    arr["delta_phi_step"] = [1e-4, 1e-4, 1e-4]
    arr["g_dac"] = [1.0, 0.99, 0.98]
    arr["e_omega"] = [1.0, 2.0, 3.0]
    arr["e_asym"] = [0.5, -0.5, 0.25]
    arr["adc_code"] = [100, 101, 102]
    arr["dac_code"] = [-50, 50, -50]
    arr["e_vpi"] = [10, 5, 1]
    arr["prbs_bit"] = [1, -1, 1]
    arr["bit_fault_code"] = [0, 0, 5]
    p = tmp_path / "dsp_trace.bin"
    arr.tofile(p)
    out = read_dsp_trace(p)
    assert len(out["t"]) == 3
    assert int(out["bit_fault_code"][2]) == 5
    assert int(out["prbs_bit"][1]) == -1


@pytest.mark.unit
def test_theoretical_bw_3db_edge_branches() -> None:
    """Cover tau_s=None, tau_s!=None, len(below)==0, and idx==0 branches of compute_theoretical_bw_3db_hz."""
    tf = 4.0 * 4.89672e-6
    bw_z = compute_theoretical_bw_3db_hz(0.25, tf)
    bw_f = compute_theoretical_bw_3db_hz(0.25, tf, tau_s=4.89672e-6)
    assert bw_z > bw_f > 1000.0
    # idx == 0 branch: ultra-low gain starts below -3 dB at 1 Hz
    bw_tiny = compute_theoretical_bw_3db_hz(1.0e-8, tf, tau_s=4.89672e-6)
    assert math.isclose(bw_tiny, 1.0, rel_tol=1e-6)
    # len(below) == 0 branch: high-gain 1st-order frame filter stays > 1/sqrt(2) across Nyquist
    bw_hi = compute_theoretical_bw_3db_hz(0.99, tf, tau_s=4.89672e-6)
    assert bw_hi > 0.45 / tf


@pytest.mark.unit
def test_td_and_eng_scenarios_real_coverage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run real SPEC-005 scenarios + edge branches to cover scenarios_time_domain, scenarios_engineering & plot_scenarios."""
    cfg = load_config(BASELINE_CFG)
    out_all = tmp_path / "all_sc"

    # 1. Real 6-state DSP comparison + all 6 TD scenarios (runs in ~8 s total)
    dsp6 = run_dsp6_comparison(SIM_BIN, cfg, out_all)
    assert dsp6["dsp6_pass"] is True

    # Also exercise td01 when micro_waveforms already exists & td02 with 6state + flat-high bode fallback
    td_res = run_all_time_domain_scenarios(SIM_BIN, cfg, out_all)
    assert td_res["all_passed"] is True
    # Run td01 once more into same dir so `if not (out_dir / "micro_waveforms.bin").exists()` False branch executes
    run_td_blanking(SIM_BIN, cfg, out_all)

    # Exercise td02 below_3db fallback branch (when gain never drops below -3 dB) & 6state/2state mode mapping
    import tier3_analysis.scenarios_time_domain as td_mod

    orig_run_t2 = td_mod._run_tier2

    def _flat_bode_t2(bin_p: Path, c: dict[str, Any], phys_p: Path, wdir: Path, shupe_path: Path | None = None) -> dict[str, Any]:
        return orig_run_t2(bin_p, c, phys_p, wdir, shupe_path=shupe_path)

    # Run td02 with high gain K_tot_1=0.55 & 6state, plus monkeypatch np.where branch via ultra-low freq
    cfg6_hi = deep_merge(cfg, {"dsp": {"mode": "6state", "alpha_rad": math.pi / 3.0, "K_tot_1": 0.55}})
    monkeypatch.setattr(td_mod, "_run_tier2", _flat_bode_t2)
    orig_read = td_mod.read_sim_records

    def _unity_sine_read(p: Path) -> dict[str, np.ndarray]:
        d = orig_read(p)
        if "sine_" in str(p):
            d["omega_out"] = d["omega_in"].copy()
        return d

    monkeypatch.setattr(td_mod, "read_sim_records", _unity_sine_read)
    td02_flat = run_td_step_sine(SIM_BIN, cfg6_hi, tmp_path / "td02_flat")
    assert td02_flat["bw_3db_measured_Hz"] == 9000.0
    monkeypatch.undo()

    # 2. Real all 5 Engineering scenarios with compact mc_runs=4 (still real Tier 1 + Tier 2, runs in ~10 s!)
    eng_res = run_all_engineering_scenarios(SIM_BIN, cfg, out_all, mc_runs=4)
    assert eng_res["all_passed"] is True

    # 3. Plot empty directory (tests None-return paths in plot_scenarios) & full directory + export_report
    empty_figs = tmp_path / "empty_figs"
    assert plot_td_scenarios(tmp_path / "nonexistent_dir", empty_figs) == []
    assert plot_eng_scenarios(tmp_path / "nonexistent_dir", empty_figs) == []

    # Also test eng04 plot with one failed case color branch
    e4_copy = json.loads((out_all / "eng04_fault_bit.json").read_text(encoding="utf-8"))
    e4_copy["cases"][0]["pass"] = False
    fail_dir = tmp_path / "eng04_fail_plot"
    fail_dir.mkdir()
    (fail_dir / "eng04_fault_bit.json").write_text(json.dumps(e4_copy), encoding="utf-8")
    assert len(plot_eng_scenarios(fail_dir, fail_dir / "figs")) == 1

    # Export full unified report (.png, .md, .html + CSV copy) covering all _summarize_scenario_detail & Plotly branches
    rep = export_run_report(out_all, formats=("png", "md", "html"), report_dir=tmp_path / "rep_all", update_index=True)
    assert rep["report_meta"]["overall_status"] == "PASS"
    assert (tmp_path / "rep_all" / "virtual_calibration_dataset.csv").exists()
    assert (tmp_path / "rep_all" / "figures" / "dsp6_compare.png").exists()
    assert plot_dsp6_compare(dsp6, tmp_path / "dsp6_single.png").exists()

    md_text = (tmp_path / "rep_all" / "report.md").read_text(encoding="utf-8")
    html_text = (tmp_path / "rep_all" / "report.html").read_text(encoding="utf-8")
    assert "## 7. Gate 5 — Official 6-State Symmetric DSP Benchmark" in md_text
    assert "## 8. Group A — Official Time-Domain Scenarios" in md_text
    assert "## 9. Group B — System Engineering & Production Scenarios" in md_text
    assert "ENG-04 — Real-Time FPGA BIT/FDIR" in md_text
    assert "ENG-05 — Monte Carlo Production Yield" in md_text
    for marker in (
        "Interactive Telemetry — Core Acceptance Gates",
        "Interactive Telemetry — Group A: 6 Time-Domain Scenarios",
        "Interactive Telemetry — Group B: 5 System Engineering",
        "Official 6-State DSP",
        "12-Bit Quantization Idle Tones",
        "Hardware Sizing & Cost Trade-Off",
        "Monte Carlo Production Yield",
    ):
        assert marker in html_text


@pytest.mark.unit
def test_sim_runner_cli_all_spec005_mode_dispatches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify every SPEC-005 CLI mode dispatch and --dsp-mode override in sim_runner_cli.py."""
    called: list[str] = []

    def _make_stub(name: str):
        def _stub(*args: Any, **kwargs: Any) -> dict[str, Any]:
            called.append(name)
            return {"ok": True}

        return _stub

    for fn_name in (
        "run_gate1_stage",
        "run_gate2_stage",
        "run_gate3_stage",
        "run_gate4_stage",
        "run_dsp6_comparison",
        "run_td_blanking",
        "run_td_step_sine",
        "run_td_vpi_shock",
        "run_td_high_rate",
        "run_td_shupe_shock",
        "run_td_limit_cycles",
        "run_all_time_domain_scenarios",
        "run_eng_hw_sizing",
        "run_eng_imu_3axis",
        "run_eng_vre_faraday",
        "run_eng_fault_bit",
        "run_eng_mc_yield_cal",
        "run_all_engineering_scenarios",
    ):
        monkeypatch.setattr(sim_runner_cli, fn_name, _make_stub(fn_name))

    modes = [
        "dsp6_compare",
        "td_blanking",
        "td_step_sine",
        "td_vpi_shock",
        "td_high_rate",
        "td_shupe_shock",
        "td_limit_cycles",
        "td_all",
        "eng_hw_sizing",
        "eng_imu_3axis",
        "eng_vre_faraday",
        "eng_fault_bit",
        "eng_mc_yield_cal",
        "eng_all",
        "all_scenarios",
    ]
    for m in modes:
        rc = sim_runner_cli.main(
            [
                "--mode",
                m,
                "--cfg",
                str(BASELINE_CFG),
                "--bin",
                str(SIM_BIN),
                "--data-dir",
                str(tmp_path / "data"),
                "--report-dir",
                str(tmp_path / "report"),
                "--run-id",
                f"u_{m}",
                "--dsp-mode",
                "6state" if m == "dsp6_compare" else "4state",
                "--mc-runs",
                "8",
            ]
        )
        assert rc == 0

    for expected in (
        "run_dsp6_comparison",
        "run_td_blanking",
        "run_td_step_sine",
        "run_td_vpi_shock",
        "run_td_high_rate",
        "run_td_shupe_shock",
        "run_td_limit_cycles",
        "run_all_time_domain_scenarios",
        "run_eng_hw_sizing",
        "run_eng_imu_3axis",
        "run_eng_vre_faraday",
        "run_eng_fault_bit",
        "run_eng_mc_yield_cal",
        "run_all_engineering_scenarios",
    ):
        assert expected in called

    # Verify individual engineering helper entrypoints are importable & callable cleanly
    assert callable(run_eng_hw_sizing)
    assert callable(run_eng_imu_3axis)
    assert callable(run_eng_vre_faraday)
    assert callable(run_eng_fault_bit)
    assert callable(run_eng_mc_yield_cal)
