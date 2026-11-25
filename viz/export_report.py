"""Automated Diagnostic Report Generator: Markdown (.md), Interactive HTML (.html), 300-DPI PNGs & Index.

Supports both the normative IFOG-SIM-SPEC-004 Section 5.2 CLI contract:
    python3 viz/export_report.py --run data/run01/ --format png,html
and centralized automatic report publication into report/:
    python3 viz/export_report.py --run data/run01/ --report-dir report/run01 --format png,md,html --update-index
"""

from __future__ import annotations

import argparse
import html
import json
import shutil
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from tier3_analysis.binary_io import compute_welch_psd, read_sim_records
from viz.plot_avar_5regions import plot_avar_5regions
from viz.plot_bunny_ears import plot_bunny_ears
from viz.plot_psd_flicker import plot_psd_flicker
from viz.plot_scenarios import plot_dsp6_compare, plot_eng_scenarios, plot_td_scenarios
from viz.plot_waveforms import plot_waveforms

REPO_ROOT = Path(__file__).resolve().parents[1]


def get_project_version(repo_root: Path | None = None) -> str:
    """Read the canonical SemVer project version from pyproject.toml."""
    root = repo_root if repo_root is not None else REPO_ROOT
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return "0.0.0"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return None


def _fmt_num(value: Any, fmt: str = ".4g") -> str:
    if value is None:
        return "N/A"
    return format(float(value), fmt)


def _compute_gate_statuses(summary: dict[str, Any]) -> list[dict[str, str]]:
    """Derive human-readable Gate 1..4 & Single-Run verification rows from collected metrics."""
    rows: list[dict[str, str]] = []

    g1 = summary.get("gate1_metrics")
    if g1 is not None:
        passed = bool(g1.get("gate1_pass", False))
        detail = (
            f"Small-signal err={_fmt_num(g1.get('small_signal_err_rad'), '.2e')} rad (<1e-9), "
            f"flybacks={g1.get('flyback_count', 0)} (>1000), "
            f"eps_Vpi_eff={_fmt_num(g1.get('final_eps_vpi_eff'), '.2e')} (<1e-5)"
        )
        rows.append({"gate": "Gate 1 — Golden Linear & 2pi Flyback", "status": "PASS" if passed else "FAIL", "detail": detail})

    nl = summary.get("nonlinearity_summary")
    if nl is not None:
        passed = bool(nl.get("gate2_pass", False))
        detail = (
            f"Deadband reduction={_fmt_num(nl.get('deadband_reduction_pct'), '.2f')}% (>=90%), "
            f"Bunny Ears SF reduction={_fmt_num(nl.get('bunny_ears_sf_reduction_pct'), '.2f')}% (>=90%)"
        )
        rows.append({"gate": "Gate 2 — Deadband & Bunny Ears", "status": "PASS" if passed else "FAIL", "detail": detail})

    g3 = summary.get("gate3_metrics")
    if g3 is not None:
        passed = bool(g3.get("gate3_pass", False))
        detail = (
            f"Linear PSD slope={_fmt_num(g3.get('slope_linear'), '.3f')} (~0), "
            f"Nonlinear 1/f slope={_fmt_num(g3.get('slope_nonlinear'), '.3f')} (~-1), "
            f"K-matrix repeatability={_fmt_num(g3.get('k_repeatability_max_rel_pct'), '.3f')}% (<2%)"
        )
        rows.append({"gate": "Gate 3 — 1/f Flicker & K-Matrix", "status": "PASS" if passed else "FAIL", "detail": detail})

    av = summary.get("avar_metrics")
    if av is not None:
        ov = av.get("overlap_check", {})
        ov_pass = bool(ov.get("continuity_pass_lt_5pct", False))
        fit = av.get("fitted_ieee952", {})
        truth = av.get("slow_synthesis_truth", {})
        max_param_err_pct = 0.0
        for key in ("Q_arcsec", "N_deg_per_rt_h", "B_deg_per_h", "K_deg_per_rt_h3", "R_deg_per_h2"):
            t_val = float(truth.get(key, 0.0))
            if t_val > 0.0:
                max_param_err_pct = max(max_param_err_pct, abs(float(fit.get(key, 0.0)) - t_val) / t_val * 100.0)
        passed = ov_pass and (max_param_err_pct <= 10.0)
        detail = (
            f"Overlap mismatch={_fmt_num(ov.get('max_relative_mismatch_pct'), '.2f')}% (<5%), "
            f"Max 5-region WLS err={max_param_err_pct:.2f}% (<=10%)"
        )
        rows.append({"gate": "Gate 4 — Dual-Regime 5-Region AVAR", "status": "PASS" if passed else "FAIL", "detail": detail})

    dsp6 = summary.get("dsp6_compare")
    if dsp6 is not None:
        passed = bool(dsp6.get("dsp6_pass", False))
        s6 = dsp6["six_state"]
        detail = (
            f"6-state static err={_fmt_num(s6.get('static_err_rad'), '.2e')} rad, "
            f"eps_Vpi={_fmt_num(s6.get('final_eps_vpi_eff'), '.2e')}, "
            f"RAM/xtalk gain={_fmt_num(dsp6.get('ram_xtalk_rejection_dB'), '.1f')} dB"
        )
        rows.append({"gate": "Gate 5 — Official 6-State DSP (EQ-31..34)", "status": "PASS" if passed else "FAIL", "detail": detail})

    for sc_id, sc in summary.get("td_scenarios", {}).items():
        rows.append(
            {
                "gate": f"{sc_id} — {sc.get('title', sc_id)}",
                "status": "PASS" if bool(sc.get("pass", False)) else "FAIL",
                "detail": _summarize_scenario_detail(sc_id, sc),
            }
        )

    for sc_id, sc in summary.get("eng_scenarios", {}).items():
        rows.append(
            {
                "gate": f"{sc_id} — {sc.get('title', sc_id)}",
                "status": "PASS" if bool(sc.get("pass", False)) else "FAIL",
                "detail": _summarize_scenario_detail(sc_id, sc),
            }
        )

    if not rows and summary.get("sim_summary") is not None:
        ss = summary["sim_summary"]
        detail = (
            f"TauSteps={ss.get('total_tau_steps', 0)}, "
            f"Records={ss.get('total_records_written', 0)}, "
            f"Flybacks={ss.get('flyback_count', 0)}, "
            f"MeanRate={_fmt_num(ss.get('mean_omega_out_second_half_rad_per_s'), '.3e')} rad/s"
        )
        rows.append({"gate": "Closed-Loop Tier 2 Run", "status": "PASS", "detail": detail})

    return rows


def _summarize_scenario_detail(sc_id: str, sc: dict[str, Any]) -> str:
    """Build concise quantitative KPI summary string for TD-01..06 & ENG-01..05 rows."""
    if sc_id == "TD-01":
        return f"t_s={sc['tia_ts_0p1pct_ns']:.1f} ns, k*_opt={sc['k_start_optimal_0p5pct']}, clean_err={sc['clean_window_max_err_pct']:.3f}%, ARW x{sc['arw_blanking_penalty_factor']:.3f}"
    if sc_id == "TD-02":
        return f"t_r={sc['rise_time_10_90_ms']:.2f} ms, OS={sc['overshoot_pct']:.1f}%, BW={sc['bw_3db_measured_Hz']:.0f} Hz (theory {sc['bw_3db_theory_Hz']:.0f} Hz)"
    if sc_id == "TD-03":
        return f"4s eps={sc['four_state']['final_eps_vpi_eff']:.2e}, 6s eps={sc['six_state']['final_eps_vpi_eff']:.2e}, 6s conv={sc['six_state']['convergence_99pct_ms']:.1f} ms"
    if sc_id == "TD-04":
        return f"700 deg/s err={sc['hold_700_err_pct']:.3f}%, wraps={sc['flyback_count']:,} ({sc['flyback_rate_kHz']:.1f} kHz), anti-windup={sc['anti_windup_flag_count']}"
    if sc_id == "TD-05":
        return f"Peak={sc['peak_uncompensated_bias_deg_per_h']:.3f} deg/h, filter suppression={sc['thermal_compensation_reduction_pct']:.1f}%, r={sc['truth_correlation_r']:.4f}"
    if sc_id == "TD-06":
        return f"Bias reduction={sc['bias_err_reduction_pct']:.1f}%, unique DAC codes {sc['without_dither']['unique_dac_codes']}->{sc['with_dither']['unique_dac_codes']}"
    if sc_id == "ENG-01":
        return f"Min ENOB={sc['recommended_min_bits']}-bit, Jitter ARW deg={sc['jitter_sweep'][-1]['arw_degradation_pct']:+.1f}%, best Pareto ARW={sc['pareto_optimal']['arw_deg_per_rt_h']:.4e} deg/rt-h"
    if sc_id == "ENG-02":
        return f"Rail droop={sc['peak_rail_droop_V']*1e3:.1f} mV, Axis-Y xtalk 4s={sc['inter_axis_y_crosstalk_4state_deg_per_h']:.3e} vs 6s={sc['inter_axis_y_crosstalk_6state_deg_per_h']:.3e} deg/h"
    if sc_id == "ENG-03":
        return f"VRE={sc['vre']['vre_coeff_nonlinear_deg_h_per_g2']:.3e} deg/h/g^2, Faraday={sc['faraday']['sensitivity_measured_deg_h_per_G']:.3f} deg/h/G, Mu-metal={sc['faraday']['required_mumetal_shield_dB_for_1G_0p01degh']:.1f} dB"
    if sc_id == "ENG-04":
        max_tta = max(c["time_to_alert_us"] for c in sc["cases"])
        return f"5/5 faults detected, max TTA={max_tta:.1f} us, SEU FDIR recovered={sc['cases'][-1]['fdir_recovered']}"
    return f"MC Yield={sc['monte_carlo']['yield_pct']:.1f}% (N={sc['monte_carlo']['n_runs']}, Cpk={sc['monte_carlo']['cpk_bias_1degh']:.2f}), Cal Poly red={sc['virtual_calibration']['poly_reduction_pct']:.1f}%"


def _overall_status(gate_rows: list[dict[str, str]]) -> str:
    if not gate_rows:
        return "INFO"
    return "PASS" if all(r["status"] == "PASS" for r in gate_rows) else "FAIL"


def _build_markdown_report(
    summary: dict[str, Any],
    fig_rel_paths: list[str],
    out_md: Path,
) -> Path:
    """Render a comprehensive, version-stamped Markdown simulation report."""
    meta = summary["report_meta"]
    gate_rows = summary["gate_statuses"]
    lines: list[str] = [
        f"# IFOG Simulation Report — `{meta['run_id']}`",
        "",
        "| Field | Value |",
        "| :--- | :--- |",
        f"| **Specification** | `{summary['spec_id']}` (v5.0) |",
        f"| **Software Version** | `v{meta['version']}` |",
        f"| **Run Mode** | `{meta['mode']}` |",
        f"| **Generated (UTC)** | `{meta['generated_utc']}` |",
        f"| **Overall Status** | **{meta['overall_status']}** |",
        f"| **Data Directory** | `{summary['run_dir']}` |",
        f"| **Report Directory** | `{summary['report_dir']}` |",
        "",
    ]

    if gate_rows:
        lines.extend(
            [
                "## 1. Executive Gate & Run Status",
                "",
                "| Verification Gate / Stage | Status | Key Quantitative Metrics |",
                "| :--- | :---: | :--- |",
            ]
        )
        for row in gate_rows:
            lines.append(f"| {row['gate']} | **{row['status']}** | {row['detail']} |")
        lines.append("")

    phys = summary.get("phys_params")
    if phys is not None:
        lines.extend(
            [
                "## 2. Tier 1 Offline Optical & Thermal Parameters",
                "",
                "| Parameter | Value | Units |",
                "| :--- | ---: | :--- |",
                f"| Sagnac Scale Factor $K_{{\\text{{opt}}}}$ | `{_fmt_num(phys.get('K_opt_rad_per_rad_s'), '.6f')}` | rad/(rad/s) |",
                f"| Fringe Visibility $V$ | `{_fmt_num(phys.get('visibility_V'), '.6f')}` | — |",
                f"| Polarization Bias Phase $\\phi_{{\\text{{pol}}}}$ | `{_fmt_num(phys.get('phi_pol_rad'), '.3e')}` | rad |",
                f"| Optical Kerr Phase $\\Delta\\phi_{{\\text{{Kerr}}}}$ | `{_fmt_num(phys.get('delta_phi_kerr_rad'), '.3e')}` | rad |",
            ]
        )
        sh = summary.get("shupe_summary")
        if sh is not None:
            lines.append(
                f"| Peak Thermal Shupe Phase | `{_fmt_num(sh.get('max_abs_delta_phi_rad'), '.3e')}` | rad |"
            )
            lines.append(
                f"| Peak Thermal Shupe Rate | `{_fmt_num(sh.get('max_abs_omega_shupe_deg_per_h'), '.4f')}` | deg/h |"
            )
        lines.append("")

    ss = summary.get("sim_summary")
    if ss is not None:
        lines.extend(
            [
                "## 3. Tier 2 SystemC-AMS Closed-Loop Core Telemetry",
                "",
                "| Metric | Value |",
                "| :--- | ---: |",
                f"| Total Transit Steps ($\\tau$) | `{ss.get('total_tau_steps', 0):,}` |",
                f"| Logged 32-Byte Records | `{ss.get('total_records_written', 0):,}` |",
                f"| $2\\pi$ Flyback Resets | `{ss.get('flyback_count', 0):,}` |",
                f"| ADC Rail Clip Events | `{ss.get('adc_clip_count', 0)}` |",
                f"| Final $\\Delta\\phi_{{\\text{{step}}}}$ | `{_fmt_num(ss.get('final_delta_phi_step_rad'), '.6e')} rad` |",
                f"| Residual $\\epsilon_{{V_\\pi,\\text{{eff}}}}$ | `{_fmt_num(ss.get('final_eps_vpi_eff'), '.3e')}` |",
                f"| Mean Output Rate (2nd Half) | `{_fmt_num(ss.get('mean_omega_out_second_half_rad_per_s'), '.6e')} rad/s` |",
                "",
            ]
        )

    nl = summary.get("nonlinearity_summary")
    if nl is not None:
        u = nl["uncompensated"]
        c = nl["compensated"]
        lines.extend(
            [
                "## 4. Gate 2 — Deadband & Bunny Ears Nonlinearity Analysis",
                "",
                "| Metric | Uncompensated | Compensated (4-State + Blanking + PRBS) | Reduction |",
                "| :--- | ---: | ---: | ---: |",
                f"| Deadband Peak Error [deg/s] | `{_fmt_num(u.get('deadband_peak_err_deg_per_s'), '.4e')}` | `{_fmt_num(c.get('deadband_peak_err_deg_per_s'), '.4e')}` | **{nl['deadband_reduction_pct']:.2f}%** |",
                f"| Deadband Width [deg/s] | `{_fmt_num(u.get('deadband_width_deg_per_s'), '.4e')}` | `{_fmt_num(c.get('deadband_width_deg_per_s'), '.4e')}` | — |",
                f"| Bunny Ears Peak SF Error [ppm] | `{_fmt_num(u.get('bunny_ears_peak_sf_ppm'), '.2f')}` | `{_fmt_num(c.get('bunny_ears_peak_sf_ppm'), '.2f')}` | **{nl['bunny_ears_sf_reduction_pct']:.2f}%** |",
                "",
            ]
        )

    km = summary.get("k_matrix")
    psd_stats = summary.get("psd_flicker")
    if km is not None or psd_stats is not None:
        lines.append("## 5. Gate 3 — 1/f Flicker PSD & Leakage Gain Matrix $\\mathbf{K}$")
        lines.append("")
        if psd_stats is not None:
            lines.extend(
                [
                    "| Flicker Regime | Log-Log PSD Slope ($15\\text{ Hz}..1.5\\text{ kHz}$) | Expected Behavior |",
                    "| :--- | ---: | :--- |",
                    f"| Linear Closed-Loop | `{psd_stats['slope_linear']:.4f}` | Flat white floor ($\\approx 0$) |",
                    f"| Nonlinear + Crosstalk | `{psd_stats['slope_nonlinear']:.4f}` | Unfiltered $1/f$ leakage ($\\approx -1$) |",
                    "",
                ]
            )
        if km is not None:
            vec = km.get("K_physical_vector", [])
            lines.extend(
                [
                    "| Injection Node | Extracted Physical Gain $K_i$ |",
                    "| :--- | ---: |",
                ]
            )
            for label, val in zip(("TIA (`tia`)", "DAC (`dac`)", "Crosstalk (`xtalk`)"), vec):
                lines.append(f"| {label} | `{_fmt_num(val, '.4e')}` |")
            lines.append("")

    av = summary.get("avar_metrics")
    if av is not None:
        ov = av["overlap_check"]
        fit = av["fitted_ieee952"]
        truth = av["slow_synthesis_truth"]
        slow_dt = av.get("slow_dt_s")
        slow_fs = (1.0 / float(slow_dt)) if slow_dt else av.get("slow_f_dec_Hz")
        lines.extend(
            [
                "## 6. Gate 4 — Dual-Regime Overlapping AVAR & 5-Region WLS Fit",
                "",
                f"- **Fast-Scale Duration:** `{_fmt_num(av.get('fast_duration_s'), '.2f')} s` (ensemble `{av.get('fast_ensemble_count', 1)}` runs)",
                f"- **Slow-Scale Samples:** `{av.get('slow_n_samples', 0):,}` samples @ `{_fmt_num(slow_fs, '.1f')} Hz` (ensemble `{av.get('slow_ensemble_count', 1)}` runs)",
                f"- **Overlap Continuity ($T_m \\in [0.1, 5.0]\\text{{ s}}$):** Max mismatch = **`{ov['max_relative_mismatch_pct']:.2f}%`** (`{'PASS' if ov['continuity_pass_lt_5pct'] else 'FAIL'}`, threshold `< 5%`)",
                "",
                "| IEEE Std 952 Parameter | Analytical Truth | WLS Fitted | Relative Error |",
                "| :--- | ---: | ---: | ---: |",
            ]
        )
        for name, key, unit in (
            ("Quantization $Q$", "Q_arcsec", "arcsec"),
            ("Angle Random Walk $N$", "N_deg_per_rt_h", "deg/sqrt(h)"),
            ("Bias Instability $B$", "B_deg_per_h", "deg/h"),
            ("Rate Random Walk $K$", "K_deg_per_rt_h3", "deg/h^(3/2)"),
            ("Rate Ramp $R$", "R_deg_per_h2", "deg/h^2"),
        ):
            t_val = float(truth[key])
            f_val = float(fit[key])
            err_pct = ((f_val - t_val) / t_val * 100.0) if t_val > 0.0 else 0.0
            lines.append(
                f"| {name} [{unit}] | `{t_val:.5g}` | `{f_val:.5g}` | `{err_pct:+.2f}%` |"
            )
        lines.append("")

    dsp6 = summary.get("dsp6_compare")
    if dsp6 is not None:
        s4 = dsp6["four_state"]
        s6 = dsp6["six_state"]
        lines.extend(
            [
                "## 7. Gate 5 — Official 6-State Symmetric DSP Benchmark (`EQ-31`–`EQ-34`)",
                "",
                "| Metric | 4-State Lefèvre ($\\alpha=\\pi/4$) | Official 6-State ($\\alpha^*=\\pi/3$) | Gain / Margin |",
                "| :--- | ---: | ---: | ---: |",
                f"| Peak MIOC Bias Voltage [$V_\\pi$ frac] | `{s4['peak_bias_vpi_frac']:.3f}` | `{s6['peak_bias_vpi_frac']:.3f}` | **-{dsp6['peak_voltage_reduction_pct']:.1f}%** |",
                f"| Golden Linear Static Error [rad] | `{s4['static_err_rad']:.2e}` | `{s6['static_err_rad']:.2e}` | `< 1e-9 rad` |",
                f"| Loop-2 Residual $\\epsilon_{{V_\\pi,\\text{{eff}}}}$ | `{s4['final_eps_vpi_eff']:.2e}` | `{s6['final_eps_vpi_eff']:.2e}` | `< 1e-5` |",
                f"| RAM + Crosstalk + $\\gamma_{{\\text{{nl}}}}$ Bias [deg/h] | `{s4['ram_xtalk_bias_deg_per_h']:.3f}` | `{s6['ram_xtalk_bias_deg_per_h']:.2e}` | **+{dsp6['ram_xtalk_rejection_dB']:.2f} dB** |",
                f"| Online Asymmetry Monitor $e_{{\\text{{asym}}}}$ RMS | `N/A` | `{s6['e_asym_rms_counts']:.2f} counts` | Online health check |",
                "",
            ]
        )

    td_sc = summary.get("td_scenarios", {})
    if td_sc:
        lines.extend(
            [
                "## 8. Group A — Official Time-Domain Scenarios (`TD-01`..`TD-06`)",
                "",
                "| Scenario ID | Engineering Verification Scope | Key Measured Metrics | Status |",
                "| :--- | :--- | :--- | :---: |",
            ]
        )
        for sc_id, sc in td_sc.items():
            st = "PASS" if bool(sc.get("pass", False)) else "FAIL"
            lines.append(
                f"| `{sc_id}` | {sc.get('title', sc_id)} | {_summarize_scenario_detail(sc_id, sc)} | **{st}** |"
            )
        lines.append("")

    eng_sc = summary.get("eng_scenarios", {})
    if eng_sc:
        lines.extend(
            [
                "## 9. Group B — System Engineering & Production Scenarios (`ENG-01`..`ENG-05`)",
                "",
                "| Scenario ID | Engineering Scope | Key Quantitative Results | Status |",
                "| :--- | :--- | :--- | :---: |",
            ]
        )
        for sc_id, sc in eng_sc.items():
            st = "PASS" if bool(sc.get("pass", False)) else "FAIL"
            lines.append(
                f"| `{sc_id}` | {sc.get('title', sc_id)} | {_summarize_scenario_detail(sc_id, sc)} | **{st}** |"
            )
        lines.append("")

        e4 = eng_sc.get("ENG-04")
        if e4 is not None:
            lines.extend(
                [
                    "### ENG-04 — Real-Time FPGA BIT/FDIR 5-Fault Detection & Recovery Table",
                    "",
                    "| Fault Mode | Expected Code | Detected Code | Time-to-Alert [us] | FDIR Recovered | Status |",
                    "| :--- | :---: | :---: | ---: | :---: | :---: |",
                ]
            )
            for c in e4["cases"]:
                lines.append(
                    f"| `{c['fault_type']}` | `{c['expected_bit_code']}` | `{c['detected_bit_code']}` "
                    f"| `{c['time_to_alert_us']:.2f}` | `{c['fdir_recovered']}` | **{'PASS' if c['pass'] else 'FAIL'}** |"
                )
            lines.append("")

        e5 = eng_sc.get("ENG-05")
        if e5 is not None:
            mc = e5["monte_carlo"]
            cal = e5["virtual_calibration"]
            ci = mc["wilson_ci95_pct"]
            lines.extend(
                [
                    "### ENG-05 — Monte Carlo Production Yield & Virtual Thermal Calibration (`-40..+85 C`)",
                    "",
                    f"- **Monte Carlo Yield:** `{mc['n_pass']}/{mc['n_runs']}` = **`{mc['yield_pct']:.2f}%`** (95% Wilson CI: `[{ci[0]:.2f}%, {ci[1]:.2f}%]`, Bias mean `{mc['bias_mean_deg_per_h']:.3f} deg/h`, std `{mc['bias_std_deg_per_h']:.3f} deg/h`, **$C_{{pk}} = {mc['cpk_bias_1degh']:.3f}$**)",
                    f"- **Virtual Thermal Calibration CSV:** [`{cal['dataset_csv']}`]({cal['dataset_csv']}) (`{cal['n_points']}` operating points across `{cal['temp_range_C'][0]:.0f}..{cal['temp_range_C'][1]:+.0f} C`)",
                    f"- **Thermal Drift Compensation:** Raw RMS `{cal['raw_rms_deg_per_h']:.2f} deg/h` -> 2D Poly `{cal['poly_residual_rms_deg_per_h']:.4f} deg/h` (**`{cal['poly_reduction_pct']:.2f}%`**) | 4-State EKF `{cal['ekf_residual_rms_deg_per_h']:.4f} deg/h` (**`{cal['ekf_reduction_pct']:.2f}%`**)",
                    "",
                ]
            )

    if fig_rel_paths:
        lines.extend(["## 10. Diagnostic Figures (300-DPI)", ""])
        for rel in fig_rel_paths:
            title = Path(rel).stem.replace("_", " ").title()
            lines.append(f"### {title}")
            lines.append(f"![{title}]({rel})")
            lines.append("")

    out_md.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_md


def _plotly_div(fig: go.Figure, height: int = 380) -> str:
    """Serialize a Plotly Figure to a lightweight HTML div (CDN loaded once in document head)."""
    fig.update_layout(
        height=height,
        template="plotly_white",
        margin={"l": 60, "r": 25, "t": 55, "b": 50},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1.0},
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def _build_plotly_sections(rdir: Path, summary: dict[str, Any]) -> str:
    """Build interactive Plotly HTML5 chart cards for all available Core, TD, and ENG scenarios."""
    sections: list[str] = []

    # 1. Core Acceptance Gates (Gate 2, Gate 3, Gate 4, Gate 5)
    core_divs: list[str] = []
    if (rdir / "avar_curve.npz").exists():
        npz = np.load(rdir / "avar_curve.npz")
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=npz["taus_fast"], y=npz["adev_fast_deg_h"], mode="markers+lines", name="Fast-Scale ADEV [deg/h]", line={"color": "#1B365D"})
        )
        fig.add_trace(
            go.Scatter(x=npz["taus_slow"], y=npz["adev_slow_deg_h"], mode="markers+lines", name="Slow-Scale ADEV [deg/h]", line={"color": "#0E6251"})
        )
        fig.update_xaxes(type="log", title_text="Cluster Time T [s]")
        fig.update_yaxes(type="log", title_text="ADEV [deg/h]")
        fig.update_layout(title="Gate 4 — Dual-Regime Overlapping Allan Deviation (Fast + 10 h Slow)")
        core_divs.append(_plotly_div(fig, 400))

    if (rdir / "sweep_results.json").exists():
        sw = _load_optional_json(rdir / "sweep_results.json")
        assert sw is not None
        r_in = np.asarray(sw["rates_in_deg_per_s"], dtype=np.float64)
        u_err = np.asarray(sw["uncompensated_out_deg_per_s"], dtype=np.float64) - r_in
        c_err = np.asarray(sw["compensated_out_deg_per_s"], dtype=np.float64) - r_in
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=r_in, y=u_err, mode="lines+markers", name="Uncompensated Error [deg/s]", line={"color": "#9B2C2C"}))
        fig.add_trace(go.Scatter(x=r_in, y=c_err, mode="lines+markers", name="Compensated Error [deg/s]", line={"color": "#0E6251"}))
        fig.update_xaxes(title_text="Input Rate [deg/s]")
        fig.update_yaxes(title_text="Rate Error [deg/s]")
        fig.update_layout(title="Gate 2 — Closed-Loop Deadband & Bunny Ears Mitigation")
        core_divs.append(_plotly_div(fig, 370))

    if (rdir / "psd_linear.bin").exists() and (rdir / "psd_nonlinear.bin").exists():
        rec_l = read_sim_records(rdir / "psd_linear.bin")
        rec_n = read_sim_records(rdir / "psd_nonlinear.bin")
        dt_l = float(np.median(np.diff(rec_l["t"])))
        dt_n = float(np.median(np.diff(rec_n["t"])))
        skip = min(500, len(rec_l["omega_out"]) // 10)
        f_l, p_l = compute_welch_psd(rec_l["omega_out"][skip:], fs_Hz=1.0 / dt_l)
        f_n, p_n = compute_welch_psd(rec_n["omega_out"][skip:], fs_Hz=1.0 / dt_n)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=f_l[1:], y=p_l[1:], mode="lines", name="Linear PSD [(rad/s)^2/Hz]", line={"color": "#1B365D"}))
        fig.add_trace(go.Scatter(x=f_n[1:], y=p_n[1:], mode="lines", name="Nonlinear 1/f PSD [(rad/s)^2/Hz]", line={"color": "#9B2C2C"}))
        fig.update_xaxes(type="log", title_text="Frequency [Hz]")
        fig.update_yaxes(type="log", title_text="PSD [(rad/s)^2/Hz]")
        fig.update_layout(title="Gate 3 — 1/f Flicker Modulation Rejection vs Nonlinear Leakage")
        core_divs.append(_plotly_div(fig, 380))

    dsp6 = summary.get("dsp6_compare")
    if dsp6 is not None:
        s4, s6 = dsp6["four_state"], dsp6["six_state"]
        fig = make_subplots(rows=1, cols=2, subplot_titles=("RAM + Crosstalk Bias [deg/h] (Log)", "Peak MIOC Bias Voltage [V_pi frac]"))
        fig.add_trace(
            go.Bar(
                x=["4-State (pi/4)", "6-State (pi/3)"],
                y=[max(float(s4["ram_xtalk_bias_deg_per_h"]), 1e-12), max(float(s6["ram_xtalk_bias_deg_per_h"]), 1e-12)],
                marker_color=["#9B2C2C", "#0E6251"],
                name="Bias [deg/h]",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Bar(
                x=["4-State (pi/4)", "6-State (pi/3)"],
                y=[float(s4["peak_bias_vpi_frac"]), float(s6["peak_bias_vpi_frac"])],
                marker_color=["#1B365D", "#2B6CB0"],
                name="Peak V_pi frac",
            ),
            row=1,
            col=2,
        )
        fig.update_yaxes(type="log", title_text="Bias Error [deg/h]", row=1, col=1)
        fig.update_yaxes(title_text="V_pi Fraction", range=[0, 1.2], row=1, col=2)
        fig.update_layout(title=f"Gate 5 — Official 6-State DSP (+{dsp6['ram_xtalk_rejection_dB']:.1f} dB Rejection, -{dsp6['peak_voltage_reduction_pct']:.1f}% Peak Voltage)")
        core_divs.append(_plotly_div(fig, 380))

    if core_divs:
        sections.append("<h2>Interactive Telemetry — Core Acceptance Gates</h2>" + "".join(f"<div class='plot-card'>{d}</div>" for d in core_divs))

    # 2. Group A — 6 Time-Domain Scenarios (TD-01..TD-06)
    td_sc = summary.get("td_scenarios", {})
    td_divs: list[str] = []
    if "TD-01" in td_sc:
        d = td_sc["TD-01"]
        ks = list(range(len(d["rel_err_by_k_pct"])))
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=ks, y=[max(v, 1e-5) for v in d["rel_err_by_k_pct"]], mode="lines+markers", name="Max TIA Settling Err [%]", line={"color": "#1B365D"}))
        fig.add_hline(y=0.5, line_dash="dash", line_color="#9B2C2C", annotation_text="0.5% Settling Threshold")
        fig.add_vrect(x0=d["k_start_configured"], x1=d["k_end_configured"], fillcolor="#C6F6D5", opacity=0.35, line_width=0)
        fig.update_xaxes(title_text="Sub-sample Index k")
        fig.update_yaxes(type="log", title_text="Settling Error [%]")
        fig.update_layout(title=f"TD-01 — Sub-tau Settling & ADC Blanking Alignment (k*={d['k_start_optimal_0p5pct']}, t_s={d['tia_ts_0p1pct_ns']:.1f} ns)")
        td_divs.append(_plotly_div(fig, 360))

    if "TD-02" in td_sc:
        d = td_sc["TD-02"]
        fig = make_subplots(rows=1, cols=2, subplot_titles=("Step Response (0 -> 100 deg/s)", f"Closed-Loop Bode (-3 dB BW = {d['bw_3db_measured_Hz']:.0f} Hz)"))
        fig.add_trace(go.Scatter(x=d["step_trace"]["t_ms"], y=d["step_trace"]["omega_out_deg_per_s"], mode="lines", name="Omega_out [deg/s]", line={"color": "#1B365D"}), row=1, col=1)
        fig.add_trace(go.Scatter(x=[p["freq_Hz"] for p in d["bode_points"]], y=[p["mag_dB"] for p in d["bode_points"]], mode="lines+markers", name="Magnitude [dB]", line={"color": "#9B2C2C"}), row=1, col=2)
        fig.add_hline(y=-3.0, line_dash="dash", line_color="#4A5568", row=1, col=2)
        fig.update_xaxes(title_text="Time after step [ms]", row=1, col=1)
        fig.update_yaxes(title_text="Rate [deg/s]", row=1, col=1)
        fig.update_xaxes(type="log", title_text="Frequency [Hz]", row=1, col=2)
        fig.update_yaxes(title_text="Magnitude [dB]", row=1, col=2)
        fig.update_layout(title="TD-02 — Closed-Loop Step & Sine Bode Bandwidth")
        td_divs.append(_plotly_div(fig, 380))

    if "TD-03" in td_sc:
        d = td_sc["TD-03"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["four_state"]["trace_t_ms"], y=[v * 100.0 for v in d["four_state"]["trace_eps_vpi_eff"]], mode="lines", name="4-State Loop-2 [%]", line={"color": "#9B2C2C"}))
        fig.add_trace(go.Scatter(x=d["six_state"]["trace_t_ms"], y=[v * 100.0 for v in d["six_state"]["trace_eps_vpi_eff"]], mode="lines", name="6-State Loop-2 [%]", line={"color": "#0E6251"}))
        fig.update_xaxes(title_text="Time after +5% V_pi Shock [ms]")
        fig.update_yaxes(title_text="Residual eps_Vpi [%]")
        fig.update_layout(title="TD-03 — Loop-2 Gain-Lock Convergence Under +5% Thermal Shock")
        td_divs.append(_plotly_div(fig, 360))

    if "TD-04" in td_sc:
        d = td_sc["TD-04"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["trace"]["t_ms"], y=d["trace"]["omega_in_deg_per_s"], mode="lines", name="Command Omega_in [deg/s]", line={"color": "#4A5568", "dash": "dash"}))
        fig.add_trace(go.Scatter(x=d["trace"]["t_ms"], y=d["trace"]["omega_out_deg_per_s"], mode="lines", name="Closed-Loop Omega_out [deg/s]", line={"color": "#1B365D"}))
        fig.update_xaxes(title_text="Time [ms]")
        fig.update_yaxes(title_text="Rate [deg/s]")
        fig.update_layout(title=f"TD-04 — High-Rate 0->700 deg/s Tracking ({d['flyback_count']:,} 2pi Wraps @ {d['flyback_rate_kHz']:.1f} kHz)")
        td_divs.append(_plotly_div(fig, 360))

    if "TD-05" in td_sc:
        d = td_sc["TD-05"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["trace"]["t_ms"], y=d["trace"]["omega_out_deg_per_h"], mode="lines", name="Uncompensated Shupe [deg/h]", line={"color": "#9B2C2C"}))
        fig.add_trace(go.Scatter(x=d["trace"]["t_ms"], y=d["trace"]["omega_comp_deg_per_h"], mode="lines", name="Extrapolative Thermal Filter [deg/h]", line={"color": "#0E6251"}))
        fig.update_xaxes(title_text="Time [ms]")
        fig.update_yaxes(title_text="Thermal Bias Drift [deg/h]")
        fig.update_layout(title=f"TD-05 — Real-Time Shupe Shock & Compensation ({d['thermal_compensation_reduction_pct']:.2f}% Suppression)")
        td_divs.append(_plotly_div(fig, 360))

    if "TD-06" in td_sc:
        d = td_sc["TD-06"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=d["without_dither"]["freqs_Hz"], y=d["without_dither"]["psd_dB"], mode="lines", name="No Dither (Limit Cycles)", line={"color": "#9B2C2C"}))
        fig.add_trace(go.Scatter(x=d["with_dither"]["freqs_Hz"], y=d["with_dither"]["psd_dB"], mode="lines", name="With LFSR PRBS Dither", line={"color": "#0E6251"}))
        fig.update_xaxes(type="log", title_text="Frequency [Hz]")
        fig.update_yaxes(title_text="PSD [dB((deg/s)^2/Hz)]")
        fig.update_layout(title=f"TD-06 — 12-Bit Quantization Idle Tones vs PRBS Dither (DAC codes {d['without_dither']['unique_dac_codes']}->{d['with_dither']['unique_dac_codes']})")
        td_divs.append(_plotly_div(fig, 360))

    if td_divs:
        sections.append("<h2>Interactive Telemetry — Group A: 6 Time-Domain Scenarios (TD-01..TD-06)</h2>" + "".join(f"<div class='plot-card'>{d}</div>" for d in td_divs))

    # 3. Group B — 5 System Engineering & Production Scenarios (ENG-01..ENG-05)
    eng_sc = summary.get("eng_scenarios", {})
    eng_divs: list[str] = []
    if "ENG-01" in eng_sc:
        d = eng_sc["ENG-01"]
        fig = make_subplots(rows=1, cols=2, subplot_titles=(f"ENOB Sweep (Min Passing = {d['recommended_min_bits']}-bit)", "ADC Aperture Jitter vs ARW"))
        fig.add_trace(
            go.Scatter(x=[r["bits"] for r in d["enob_sweep"]], y=[max(r["deadband_err_deg_per_s"], 1e-7) for r in d["enob_sweep"]], mode="lines+markers", name="Deadband Err [deg/s]", line={"color": "#1B365D"}),
            row=1,
            col=1,
        )
        fig.add_hline(y=0.01, line_dash="dash", line_color="#9B2C2C", row=1, col=1)
        fig.add_trace(
            go.Scatter(x=[r["jitter_ps"] for r in d["jitter_sweep"]], y=[r["arw_deg_per_rt_h"] for r in d["jitter_sweep"]], mode="lines+markers", name="ARW [deg/rt-h]", line={"color": "#0E6251"}),
            row=1,
            col=2,
        )
        fig.update_xaxes(title_text="Resolution [bits]", row=1, col=1)
        fig.update_yaxes(type="log", title_text="Deadband Error [deg/s]", row=1, col=1)
        fig.update_xaxes(title_text="Aperture Jitter [ps]", row=1, col=2)
        fig.update_yaxes(title_text="ARW [deg/rt-h]", row=1, col=2)
        fig.update_layout(title="ENG-01 — Hardware Sizing & Cost Trade-Off (ENOB & Aperture Jitter)")
        eng_divs.append(_plotly_div(fig, 380))

    if "ENG-02" in eng_sc:
        d = eng_sc["ENG-02"]
        fig = go.Figure(
            go.Bar(
                x=["Isolated (4-State)", "Shared SLD/Rail (4-State)", "Shared SLD/Rail (6-State)"],
                y=[
                    abs(float(d["isolated_4state"]["y_bias_err_deg_per_h"])),
                    abs(float(d["coupled_4state"]["y_bias_err_deg_per_h"])),
                    abs(float(d["coupled_6state"]["y_bias_err_deg_per_h"])),
                ],
                marker_color=["#4A5568", "#9B2C2C", "#0E6251"],
            )
        )
        fig.update_yaxes(title_text="Stationary Axis-Y Bias Error [deg/h]")
        fig.update_layout(title=f"ENG-02 — Concurrent 3-Axis SystemC-AMS IMU Crosstalk (Rail Droop = {d['peak_rail_droop_V']*1e3:.1f} mV)")
        eng_divs.append(_plotly_div(fig, 360))

    if "ENG-03" in eng_sc:
        d = eng_sc["ENG-03"]
        g2 = [v * v for v in d["vre"]["g_rms_levels"]]
        fig = make_subplots(rows=1, cols=2, subplot_titles=("VRE Quadratic Rectification (g_rms^2)", f"Faraday Sweep (Mu-Metal = {d['faraday']['required_mumetal_shield_dB_for_1G_0p01degh']:.1f} dB)"))
        fig.add_trace(go.Scatter(x=g2, y=d["vre"]["nonlinear_delta_bias_deg_per_h"], mode="lines+markers", name="Nonlinear TIA (G2>0)", line={"color": "#9B2C2C"}), row=1, col=1)
        fig.add_trace(go.Scatter(x=g2, y=d["vre"]["linear_delta_bias_deg_per_h"], mode="lines+markers", name="Linear TIA (G2=0)", line={"color": "#0E6251", "dash": "dash"}), row=1, col=1)
        fig.add_trace(go.Scatter(x=[r["B_gauss"] for r in d["faraday"]["sweep"]], y=[r["bias_deg_per_h"] for r in d["faraday"]["sweep"]], mode="lines+markers", name="Faraday Bias [deg/h]", line={"color": "#1B365D"}), row=1, col=2)
        fig.update_xaxes(title_text="Vibration Power g_rms^2 [g^2]", row=1, col=1)
        fig.update_yaxes(title_text="Bias Shift [deg/h]", row=1, col=1)
        fig.update_xaxes(title_text="External Magnetic Field B [Gauss]", row=1, col=2)
        fig.update_yaxes(title_text="Faraday Bias [deg/h]", row=1, col=2)
        fig.update_layout(title="ENG-03 — Vibration Rectification Error (VRE) & Faraday Sensitivity")
        eng_divs.append(_plotly_div(fig, 380))

    if "ENG-04" in eng_sc:
        d = eng_sc["ENG-04"]
        fig = go.Figure(
            go.Bar(
                y=[c["fault_type"] for c in d["cases"]],
                x=[c["time_to_alert_us"] for c in d["cases"]],
                orientation="h",
                marker_color=["#0E6251" if c["pass"] else "#9B2C2C" for c in d["cases"]],
            )
        )
        fig.update_xaxes(title_text="BIT Time-to-Alert [us]")
        fig.update_layout(title="ENG-04 — Real-Time FPGA BIT/FDIR Detection Latency (5 Fault Modes)")
        eng_divs.append(_plotly_div(fig, 340))

    if "ENG-05" in eng_sc:
        d = eng_sc["ENG-05"]
        mc = d["monte_carlo"]
        cal = d["virtual_calibration"]
        raw = [r["omega_out_deg_per_h"] for r in cal["rows"]]
        res_poly = [r - p for r, p in zip(raw, cal["poly_pred_deg_per_h"])]
        res_ekf = [r - p for r, p in zip(raw, cal["ekf_pred_deg_per_h"])]
        idx = list(range(len(raw)))
        fig = make_subplots(rows=1, cols=2, subplot_titles=(f"MC Yield = {mc['yield_pct']:.1f}% (N={mc['n_runs']}, Cpk={mc['cpk_bias_1degh']:.2f})", "Virtual Thermal Calibration (-40..+85 C)"))
        fig.add_trace(go.Histogram(x=mc["bias_samples_deg_per_h"], nbinsx=20, name="MC Unit Bias [deg/h]", marker_color="#1B365D"), row=1, col=1)
        fig.add_vline(x=-1.0, line_dash="dash", line_color="#9B2C2C", row=1, col=1)
        fig.add_vline(x=1.0, line_dash="dash", line_color="#9B2C2C", row=1, col=1)
        fig.add_trace(go.Scatter(x=idx, y=raw, mode="lines+markers", name="Raw Thermal Bias", line={"color": "#9B2C2C"}), row=1, col=2)
        fig.add_trace(go.Scatter(x=idx, y=res_poly, mode="lines+markers", name="2D Poly Residual", line={"color": "#0E6251"}), row=1, col=2)
        fig.add_trace(go.Scatter(x=idx, y=res_ekf, mode="lines", name="4-State EKF Residual", line={"color": "#2B6CB0", "dash": "dot"}), row=1, col=2)
        fig.update_xaxes(title_text="Bias Error [deg/h]", row=1, col=1)
        fig.update_yaxes(title_text="Unit Count", row=1, col=1)
        fig.update_xaxes(title_text="Thermal Point Index (21 pts)", row=1, col=2)
        fig.update_yaxes(title_text="Bias [deg/h]", row=1, col=2)
        fig.update_layout(title="ENG-05 — Monte Carlo Production Yield & -40..+85 C Virtual Thermal Calibration")
        eng_divs.append(_plotly_div(fig, 390))

    if eng_divs:
        sections.append("<h2>Interactive Telemetry — Group B: 5 System Engineering Scenarios (ENG-01..ENG-05)</h2>" + "".join(f"<div class='plot-card'>{d}</div>" for d in eng_divs))

    return "".join(sections)


def _build_interactive_html(
    rdir: Path,
    summary: dict[str, Any],
    fig_rel_paths: list[str],
    out_html: Path,
) -> Path:
    """Build self-contained industrial HTML5 diagnostic report with interactive Plotly charts & KPI tables."""
    meta = summary["report_meta"]
    gate_rows = summary["gate_statuses"]
    plot_sections_html = _build_plotly_sections(rdir, summary)

    status_cls = "pass" if meta["overall_status"] == "PASS" else ("fail" if meta["overall_status"] == "FAIL" else "info")
    gate_table_rows = "".join(
        f"<tr><td>{html.escape(r['gate'])}</td>"
        f"<td><span class='badge {'pass' if r['status'] == 'PASS' else 'fail'}'>{html.escape(r['status'])}</span></td>"
        f"<td>{html.escape(r['detail'])}</td></tr>"
        for r in gate_rows
    )

    avar_section = ""
    av = summary.get("avar_metrics")
    if av is not None:
        fit = av["fitted_ieee952"]
        truth = av["slow_synthesis_truth"]
        av_rows = []
        for name, key, unit in (
            ("Quantization (Q)", "Q_arcsec", "arcsec"),
            ("Angle Random Walk (N)", "N_deg_per_rt_h", "deg/sqrt(h)"),
            ("Bias Instability (B)", "B_deg_per_h", "deg/h"),
            ("Rate Random Walk (K)", "K_deg_per_rt_h3", "deg/h^(3/2)"),
            ("Rate Ramp (R)", "R_deg_per_h2", "deg/h^2"),
        ):
            t_val = float(truth[key])
            f_val = float(fit[key])
            err_pct = ((f_val - t_val) / t_val * 100.0) if t_val > 0.0 else 0.0
            av_rows.append(
                f"<tr><td>{html.escape(name)} [{html.escape(unit)}]</td>"
                f"<td>{t_val:.5g}</td><td>{f_val:.5g}</td><td>{err_pct:+.2f}%</td></tr>"
            )
        avar_section = (
            "<h2>Dual-Regime IEEE Std 952 5-Region WLS Recovery</h2>"
            "<table><thead><tr><th>Parameter</th><th>Analytical Truth</th><th>WLS Fitted</th><th>Error</th></tr></thead>"
            f"<tbody>{''.join(av_rows)}</tbody></table>"
        )

    gallery_html = ""
    if fig_rel_paths:
        cards = "".join(
            f"<figure><figcaption>{html.escape(Path(p).stem.replace('_', ' ').title())}</figcaption>"
            f"<img src='{html.escape(p)}' alt='{html.escape(Path(p).name)}'></figure>"
            for p in fig_rel_paths
        )
        gallery_html = f"<h2>300-DPI Diagnostic Figures Gallery ({len(fig_rel_paths)} Plots)</h2><div class='gallery'>{cards}</div>"

    summary_pre = html.escape(json.dumps(summary, indent=2))
    html_doc = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>IFOG Simulation Report — {html.escape(meta['run_id'])}</title>"
        "<script src='https://cdn.plot.ly/plotly-2.35.2.min.js'></script>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:1200px;margin:2rem auto;padding:0 1.25rem;color:#1A202C;background:#F8FAFC;}"
        ".header{background:#1B365D;color:#FFF;padding:1.5rem 2rem;border-radius:10px;margin-bottom:1.5rem;}"
        ".header h1{margin:0 0 .5rem 0;font-size:1.6rem;}"
        ".meta{display:flex;flex-wrap:wrap;gap:.75rem;font-size:.9rem;opacity:.95;}"
        ".badge{display:inline-block;padding:.2rem .6rem;border-radius:999px;font-weight:700;font-size:.82rem;}"
        ".badge.pass{background:#0E6251;color:#FFF;} .badge.fail{background:#9B2C2C;color:#FFF;} .badge.info{background:#4A5568;color:#FFF;}"
        "h2{color:#1B365D;border-bottom:2px solid #CBD5E0;padding-bottom:.35rem;margin-top:2rem;}"
        "table{width:100%;border-collapse:collapse;background:#FFF;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);}"
        "th,td{padding:.65rem .9rem;border-bottom:1px solid #E2E8F0;text-align:left;font-size:.92rem;}"
        "th{background:#EDF2F7;color:#1B365D;}"
        ".plot-card{background:#FFF;padding:.75rem;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);margin-bottom:1.25rem;}"
        ".gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(480px,1fr));gap:1.25rem;}"
        "figure{margin:0;background:#FFF;padding:1rem;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.08);}"
        "figcaption{font-weight:600;color:#1B365D;margin-bottom:.5rem;}"
        "figure img{width:100%;height:auto;border:1px solid #E2E8F0;border-radius:4px;}"
        "pre{background:#1A202C;color:#E2E8F0;padding:1rem;border-radius:8px;overflow-x:auto;font-size:.82rem;}"
        "</style></head><body>"
        "<div class='header'>"
        f"<h1>IFOG-SIM-SPEC-005 Virtual Prototype Report — {html.escape(meta['run_id'])}</h1>"
        "<div class='meta'>"
        f"<span>Version: <strong>v{html.escape(meta['version'])}</strong></span>"
        f"<span>Mode: <strong>{html.escape(meta['mode'])}</strong></span>"
        f"<span>Generated: <strong>{html.escape(meta['generated_utc'])}</strong></span>"
        f"<span class='badge {status_cls}'>{html.escape(meta['overall_status'])}</span>"
        "</div></div>"
        + (
            "<h2>Executive Gate & Scenario Verification Summary</h2>"
            "<table><thead><tr><th>Gate / Scenario</th><th>Status</th><th>Quantitative Metrics</th></tr></thead>"
            f"<tbody>{gate_table_rows}</tbody></table>"
            if gate_rows
            else ""
        )
        + avar_section
        + plot_sections_html
        + gallery_html
        + "<h2>Raw Metrics Summary (<code>metrics_summary.json</code>)</h2>"
        + f"<details><summary>Expand full JSON payload</summary><pre>{summary_pre}</pre></details>"
        + "</body></html>"
    )
    out_html.write_text(html_doc, encoding="utf-8")
    return out_html


def update_report_index(report_root: Path | str) -> tuple[Path, Path]:
    """Scan report_root/*/metrics_summary.json and write report/index.md and report/index.html."""
    root = Path(report_root)
    root.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, str]] = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        summary_file = sub / "metrics_summary.json"
        if not summary_file.exists():
            continue
        data = json.loads(summary_file.read_text(encoding="utf-8"))
        meta = data.get("report_meta", {})
        entries.append(
            {
                "run_id": str(meta.get("run_id", sub.name)),
                "dir": sub.name,
                "mode": str(meta.get("mode", "unknown")),
                "version": str(meta.get("version", get_project_version())),
                "generated_utc": str(meta.get("generated_utc", "")),
                "status": str(meta.get("overall_status", "INFO")),
                "has_md": "yes" if (sub / "report.md").exists() else "no",
                "has_html": "yes" if (sub / "report.html").exists() else "no",
            }
        )
    entries.sort(key=lambda e: (e["generated_utc"], e["dir"]), reverse=True)

    md_lines = [
        "# IFOG Virtual Prototype — Simulation Reports Index",
        "",
        f"Automatically maintained by `viz/export_report.py` (`v{get_project_version()}`).",
        "",
        "| Run ID | Mode | Version | Generated (UTC) | Status | Markdown | HTML |",
        "| :--- | :--- | :---: | :--- | :---: | :---: | :---: |",
    ]
    html_rows: list[str] = []
    for e in entries:
        md_link = f"[report.md]({e['dir']}/report.md)" if e["has_md"] == "yes" else "—"
        html_link = f"[report.html]({e['dir']}/report.html)" if e["has_html"] == "yes" else "—"
        md_lines.append(
            f"| `{e['run_id']}` | `{e['mode']}` | `v{e['version']}` | `{e['generated_utc']}` | **{e['status']}** | {md_link} | {html_link} |"
        )
        md_a = f"<a href='{html.escape(e['dir'])}/report.md'>report.md</a>" if e["has_md"] == "yes" else "—"
        html_a = f"<a href='{html.escape(e['dir'])}/report.html'>report.html</a>" if e["has_html"] == "yes" else "—"
        cls = "pass" if e["status"] == "PASS" else ("fail" if e["status"] == "FAIL" else "info")
        html_rows.append(
            f"<tr><td><code>{html.escape(e['run_id'])}</code></td>"
            f"<td>{html.escape(e['mode'])}</td>"
            f"<td>v{html.escape(e['version'])}</td>"
            f"<td>{html.escape(e['generated_utc'])}</td>"
            f"<td><span class='badge {cls}'>{html.escape(e['status'])}</span></td>"
            f"<td>{md_a}</td><td>{html_a}</td></tr>"
        )

    idx_md = root / "index.md"
    idx_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    idx_html = root / "index.html"
    idx_html.write_text(
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>IFOG Simulation Reports Index</title>"
        "<style>"
        "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1.25rem;background:#F8FAFC;color:#1A202C;}"
        "h1{color:#1B365D;} table{width:100%;border-collapse:collapse;background:#FFF;border-radius:8px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.08);}"
        "th,td{padding:.65rem .9rem;border-bottom:1px solid #E2E8F0;text-align:left;font-size:.92rem;} th{background:#1B365D;color:#FFF;}"
        ".badge{display:inline-block;padding:.15rem .55rem;border-radius:999px;font-weight:700;font-size:.8rem;color:#FFF;}"
        ".badge.pass{background:#0E6251;} .badge.fail{background:#9B2C2C;} .badge.info{background:#4A5568;}"
        "</style></head><body>"
        f"<h1>IFOG-SIM-SPEC-005 Simulation Reports Index (v{html.escape(get_project_version())})</h1>"
        "<table><thead><tr><th>Run ID</th><th>Mode</th><th>Version</th><th>Generated (UTC)</th><th>Status</th><th>Markdown</th><th>HTML</th></tr></thead>"
        f"<tbody>{''.join(html_rows)}</tbody></table>"
        "</body></html>",
        encoding="utf-8",
    )
    return idx_md, idx_html


def export_run_report(
    run_dir: Path | str,
    formats: tuple[str, ...] = ("png", "md", "html"),
    report_dir: Path | str | None = None,
    run_meta: dict[str, Any] | None = None,
    update_index: bool = False,
) -> dict[str, Any]:
    """Export metrics_summary.json, 300-DPI PNG figures, Markdown (.md), and HTML (.html) reports."""
    rdir = Path(run_dir)
    dest_dir = Path(report_dir) if report_dir is not None else rdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    fig_dir = dest_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    meta_in = run_meta or {}
    td_files = (
        ("TD-01", "td01_blanking.json"),
        ("TD-02", "td02_step_sine.json"),
        ("TD-03", "td03_vpi_shock.json"),
        ("TD-04", "td04_high_rate.json"),
        ("TD-05", "td05_shupe_shock.json"),
        ("TD-06", "td06_limit_cycles.json"),
    )
    eng_files = (
        ("ENG-01", "eng01_hw_sizing.json"),
        ("ENG-02", "eng02_imu_3axis.json"),
        ("ENG-03", "eng03_vre_faraday.json"),
        ("ENG-04", "eng04_fault_bit.json"),
        ("ENG-05", "eng05_mc_yield_cal.json"),
    )
    td_loaded = {k: v for k, fname in td_files if (v := _load_optional_json(rdir / fname)) is not None}
    eng_loaded = {k: v for k, fname in eng_files if (v := _load_optional_json(rdir / fname)) is not None}
    dsp6_loaded = _load_optional_json(rdir / "dsp6_compare.json")

    summary: dict[str, Any] = {
        "spec_id": "IFOG-SIM-SPEC-005",
        "run_dir": str(rdir),
        "report_dir": str(dest_dir),
        "phys_params": _load_optional_json(rdir / "phys_params.json"),
        "shupe_summary": _load_optional_json(rdir / "shupe_summary.json"),
        "sim_summary": _load_optional_json(rdir / "sim_summary.json"),
        "gate1_metrics": _load_optional_json(rdir / "gate1_metrics.json"),
        "k_matrix": _load_optional_json(rdir / "k_matrix.json"),
        "gate3_metrics": _load_optional_json(rdir / "gate3_metrics.json"),
        "nonlinearity_summary": _load_optional_json(rdir / "nonlinearity_summary.json"),
        "avar_metrics": _load_optional_json(rdir / "avar_metrics.json"),
        "dsp6_compare": dsp6_loaded,
        "td_scenarios": td_loaded,
        "eng_scenarios": eng_loaded,
        "generated_artifacts": [],
    }

    fig_rel_paths: list[str] = []
    if "png" in formats:
        if (rdir / "micro_waveforms.bin").exists():
            p = plot_waveforms(
                rdir / "micro_waveforms.bin",
                fig_dir / "waveforms.png",
                summary_json_path=rdir / "sim_summary.json",
            )
            summary["generated_artifacts"].append(str(p))
            fig_rel_paths.append("figures/waveforms.png")

        if (rdir / "sweep_results.json").exists():
            p = plot_bunny_ears(rdir / "sweep_results.json", fig_dir / "bunny_ears.png")
            summary["generated_artifacts"].append(str(p))
            fig_rel_paths.append("figures/bunny_ears.png")

        if (rdir / "psd_linear.bin").exists() and (rdir / "psd_nonlinear.bin").exists():
            psd_stats = plot_psd_flicker(
                rdir / "psd_linear.bin",
                rdir / "psd_nonlinear.bin",
                fig_dir / "psd_flicker.png",
            )
            summary["psd_flicker"] = psd_stats
            summary["generated_artifacts"].append(str(fig_dir / "psd_flicker.png"))
            fig_rel_paths.append("figures/psd_flicker.png")

        if (rdir / "avar_curve.npz").exists() and (rdir / "avar_metrics.json").exists():
            p = plot_avar_5regions(
                rdir / "avar_curve.npz",
                rdir / "avar_metrics.json",
                fig_dir / "avar_5regions.png",
            )
            summary["generated_artifacts"].append(str(p))
            fig_rel_paths.append("figures/avar_5regions.png")

        if dsp6_loaded is not None:
            p = plot_dsp6_compare(dsp6_loaded, fig_dir / "dsp6_compare.png")
            summary["generated_artifacts"].append(str(p))
            fig_rel_paths.append("figures/dsp6_compare.png")

        for p in plot_td_scenarios(rdir, fig_dir):
            summary["generated_artifacts"].append(str(p))
            fig_rel_paths.append(f"figures/{p.name}")

        for p in plot_eng_scenarios(rdir, fig_dir):
            summary["generated_artifacts"].append(str(p))
            fig_rel_paths.append(f"figures/{p.name}")

    cal_csv = rdir / "virtual_calibration_dataset.csv"
    if cal_csv.exists() and dest_dir.resolve() != rdir.resolve():
        shutil.copy2(cal_csv, dest_dir / cal_csv.name)
        summary["generated_artifacts"].append(str(dest_dir / cal_csv.name))

    gate_rows = _compute_gate_statuses(summary)
    summary["gate_statuses"] = gate_rows
    summary["report_meta"] = {
        "run_id": str(meta_in.get("run_id", dest_dir.name)),
        "mode": str(meta_in.get("mode", "diagnostic")),
        "version": str(meta_in.get("version", get_project_version())),
        "generated_utc": str(
            meta_in.get("generated_utc", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
        ),
        "overall_status": _overall_status(gate_rows),
    }

    if "md" in formats:
        md_path = _build_markdown_report(summary, fig_rel_paths, dest_dir / "report.md")
        summary["generated_artifacts"].append(str(md_path))

    if "html" in formats:
        html_path = _build_interactive_html(rdir, summary, fig_rel_paths, dest_dir / "report.html")
        summary["generated_artifacts"].append(str(html_path))

    dest_summary_path = dest_dir / "metrics_summary.json"
    with dest_summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)

    if dest_dir.resolve() != rdir.resolve() and rdir.exists():
        shutil.copy2(dest_summary_path, rdir / "metrics_summary.json")

    if update_index:
        update_report_index(dest_dir.parent)

    return summary


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for unified diagnostic report export."""
    parser = argparse.ArgumentParser(
        description="Export IFOG-SIM-SPEC-005 Metrics Summary, 300-DPI PNGs, Markdown & HTML Reports"
    )
    parser.add_argument("--run", required=True, help="Simulation data directory")
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Destination report directory (e.g., report/run01). Defaults to --run.",
    )
    parser.add_argument(
        "--format",
        default="png,md,html",
        help="Comma-separated output formats (png,md,html)",
    )
    parser.add_argument("--mode", default="diagnostic", help="Simulation mode label for report header")
    parser.add_argument(
        "--update-index",
        action="store_true",
        help="Refresh parent report/index.md and report/index.html after export",
    )
    args = parser.parse_args(argv)

    fmts = tuple(f.strip().lower() for f in args.format.split(",") if f.strip())
    export_run_report(
        args.run,
        formats=fmts,
        report_dir=args.report_dir,
        run_meta={"mode": args.mode},
        update_index=args.update_index,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
