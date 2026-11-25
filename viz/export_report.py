"""Diagnostic Report Exporter: metrics_summary.json, 300-DPI PNGs, & Interactive Plotly HTML (Table 3).

CLI Contract (IFOG-SIM-SPEC-004 Section 5.2):
    python3 viz/export_report.py --run data/run01/ --format png,html
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from viz.plot_avar_5regions import plot_avar_5regions
from viz.plot_bunny_ears import plot_bunny_ears
from viz.plot_psd_flicker import plot_psd_flicker
from viz.plot_waveforms import plot_waveforms


def _load_optional_json(path: Path) -> dict[str, Any] | None:
    if path.exists():
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    return None


def _build_interactive_html(
    rdir: Path, summary: dict[str, Any], out_html: Path
) -> Path:
    """Build self-contained interactive Plotly HTML report for run_id."""
    fig = make_subplots(
        rows=2,
        cols=1,
        subplot_titles=(
            "Overlapping Allan Deviation (Dual-Regime Fast + Slow)",
            "Closed-Loop Deadband & Bunny Ears Scale-Factor Error",
        ),
        vertical_spacing=0.15,
    )

    avar_npz = rdir / "avar_curve.npz"
    if avar_npz.exists():
        npz = np.load(avar_npz)
        fig.add_trace(
            go.Scatter(
                x=npz["taus_fast"],
                y=npz["adev_fast_deg_h"],
                mode="markers+lines",
                name="Fast-Scale ADEV [deg/h]",
                line={"color": "#1B365D"},
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=npz["taus_slow"],
                y=npz["adev_slow_deg_h"],
                mode="markers+lines",
                name="Slow-Scale ADEV [deg/h]",
                line={"color": "#0E6251"},
            ),
            row=1,
            col=1,
        )
        fig.update_xaxes(type="log", title_text="Cluster Time T [s]", row=1, col=1)
        fig.update_yaxes(type="log", title_text="ADEV [deg/h]", row=1, col=1)

    sweep_json = rdir / "sweep_results.json"
    if sweep_json.exists():
        sw = _load_optional_json(sweep_json)
        assert sw is not None
        r_in = np.asarray(sw["rates_in_deg_per_s"], dtype=np.float64)
        u_err = np.asarray(sw["uncompensated_out_deg_per_s"], dtype=np.float64) - r_in
        c_err = np.asarray(sw["compensated_out_deg_per_s"], dtype=np.float64) - r_in
        fig.add_trace(
            go.Scatter(
                x=r_in,
                y=u_err,
                mode="lines+markers",
                name="Uncompensated Error [deg/s]",
                line={"color": "#9B2C2C"},
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=r_in,
                y=c_err,
                mode="lines+markers",
                name="Compensated Error [deg/s]",
                line={"color": "#0E6251"},
            ),
            row=2,
            col=1,
        )
        fig.update_xaxes(title_text="Input Rate [deg/s]", row=2, col=1)
        fig.update_yaxes(title_text="Rate Error [deg/s]", row=2, col=1)

    fig.update_layout(
        title="IFOG-SIM-SPEC-004 Virtual Prototype Interactive Diagnostic Report",
        height=850,
        template="plotly_white",
    )

    plot_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    summary_pre = json.dumps(summary, indent=2)
    html_doc = (
        "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        "<title>IFOG-SIM-SPEC-004 Report</title>"
        "<style>body{font-family:sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;}"
        "pre{background:#F7FAFC;border:1px solid #CBD5E0;padding:1rem;overflow-x:auto;}</style>"
        "</head><body>"
        "<h1>IFOG-SIM-SPEC-004 Virtual Prototype Diagnostic Report</h1>"
        f"{plot_html}"
        "<h2>Metrics Summary (metrics_summary.json)</h2>"
        f"<pre>{summary_pre}</pre>"
        "</body></html>"
    )
    out_html.write_text(html_doc, encoding="utf-8")
    return out_html


def export_run_report(
    run_dir: Path | str, formats: tuple[str, ...] = ("png", "html")
) -> dict[str, Any]:
    """Export metrics_summary.json, 300-DPI PNG figures, and interactive HTML report."""
    rdir = Path(run_dir)
    fig_dir = rdir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "spec_id": "IFOG-SIM-SPEC-004",
        "run_dir": str(rdir),
        "phys_params": _load_optional_json(rdir / "phys_params.json"),
        "shupe_summary": _load_optional_json(rdir / "shupe_summary.json"),
        "sim_summary": _load_optional_json(rdir / "sim_summary.json"),
        "k_matrix": _load_optional_json(rdir / "k_matrix.json"),
        "nonlinearity_summary": _load_optional_json(rdir / "nonlinearity_summary.json"),
        "avar_metrics": _load_optional_json(rdir / "avar_metrics.json"),
        "generated_artifacts": [],
    }

    if "png" in formats:
        if (rdir / "micro_waveforms.bin").exists():
            p = plot_waveforms(
                rdir / "micro_waveforms.bin",
                fig_dir / "waveforms.png",
                summary_json_path=rdir / "sim_summary.json",
            )
            summary["generated_artifacts"].append(str(p))

        if (rdir / "sweep_results.json").exists():
            p = plot_bunny_ears(rdir / "sweep_results.json", fig_dir / "bunny_ears.png")
            summary["generated_artifacts"].append(str(p))

        if (rdir / "psd_linear.bin").exists() and (rdir / "psd_nonlinear.bin").exists():
            psd_stats = plot_psd_flicker(
                rdir / "psd_linear.bin",
                rdir / "psd_nonlinear.bin",
                fig_dir / "psd_flicker.png",
            )
            summary["psd_flicker"] = psd_stats
            summary["generated_artifacts"].append(str(fig_dir / "psd_flicker.png"))

        if (rdir / "avar_curve.npz").exists() and (rdir / "avar_metrics.json").exists():
            p = plot_avar_5regions(
                rdir / "avar_curve.npz",
                rdir / "avar_metrics.json",
                fig_dir / "avar_5regions.png",
            )
            summary["generated_artifacts"].append(str(p))

    if "html" in formats:
        html_path = _build_interactive_html(rdir, summary, rdir / "report.html")
        summary["generated_artifacts"].append(str(html_path))

    with (rdir / "metrics_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return summary


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for unified diagnostic report export."""
    parser = argparse.ArgumentParser(
        description="Export IFOG-SIM-SPEC-004 Metrics Summary, PNG Figures & HTML Report"
    )
    parser.add_argument("--run", required=True, help="Run directory")
    parser.add_argument(
        "--format",
        default="png,html",
        help="Comma-separated output formats (png,html)",
    )
    args = parser.parse_args(argv)

    fmts = tuple(f.strip().lower() for f in args.format.split(",") if f.strip())
    export_run_report(args.run, formats=fmts)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
