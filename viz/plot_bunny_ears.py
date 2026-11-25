"""Diagnostic Plot 2: Closed-Loop Deadband & Bunny Ears Scale-Factor Nonlinearity (Table 3).

CLI Contract:
    python3 viz/plot_bunny_ears.py --sweep-results data/sweep01/sweep_results.json \
        --out data/sweep01/figures/bunny_ears.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tier3_analysis.analyze_nonlinearity import analyze_sweep_nonlinearity


def plot_bunny_ears(
    sweep_results_path: Path | str,
    out_png: Path | str,
) -> Path:
    """Plot uncompensated vs compensated Deadband rate error and Bunny Ears SF error."""
    with Path(sweep_results_path).open("r", encoding="utf-8") as fh:
        sweep_data = json.load(fh)

    analysis = analyze_sweep_nonlinearity(sweep_data)
    rates_in = np.asarray(sweep_data["rates_in_deg_per_s"], dtype=np.float64)
    err_uncomp = np.asarray(analysis["uncompensated"]["rate_error_deg_per_s"], dtype=np.float64)
    err_comp = np.asarray(analysis["compensated"]["rate_error_deg_per_s"], dtype=np.float64)
    sf_uncomp = np.asarray(analysis["uncompensated"]["sf_error_ppm"], dtype=np.float64)
    sf_comp = np.asarray(analysis["compensated"]["sf_error_ppm"], dtype=np.float64)

    nz = np.abs(rates_in) > 1.0e-12

    fig, axes = plt.subplots(2, 1, figsize=(10.0, 6.8), sharex=True, dpi=300)

    ax = axes[0]
    ax.plot(
        rates_in,
        err_uncomp,
        "o-",
        color="#9B2C2C",
        linewidth=1.5,
        markersize=4,
        label="Uncompensated (V_pi Lock/Blanking/Dither OFF)",
    )
    ax.plot(
        rates_in,
        err_comp,
        "s-",
        color="#0E6251",
        linewidth=1.5,
        markersize=4,
        label="Compensated (4-State V_pi + Blanking + PRBS Dither)",
    )
    ax.axhline(0.0, color="#718096", linestyle="--", linewidth=0.8)
    ax.set_ylabel("Rate Error (Omega_out - Omega_in) [deg/s]")
    ax.set_title(
        f"Closed-Loop Deadband & Bunny Ears Mitigation "
        f"(Deadband Red: {analysis['deadband_reduction_pct']:.1f}%, "
        f"Bunny Ears SF Red: {analysis['bunny_ears_sf_reduction_pct']:.1f}%)"
    )
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8)

    ax = axes[1]
    ax.plot(
        rates_in[nz],
        sf_uncomp[nz],
        "o-",
        color="#9B2C2C",
        linewidth=1.4,
        markersize=4,
        label="Uncompensated SF Error [ppm]",
    )
    ax.plot(
        rates_in[nz],
        sf_comp[nz],
        "s-",
        color="#0E6251",
        linewidth=1.4,
        markersize=4,
        label="Compensated SF Error [ppm]",
    )
    ax.axhline(0.0, color="#718096", linestyle="--", linewidth=0.8)
    ax.set_ylabel("Scale Factor Error [ppm]")
    ax.set_xlabel("Input Angular Rate Omega_in [deg/s]")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8)

    fig.tight_layout()
    out_path = Path(out_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Bunny Ears / Deadband plotting."""
    parser = argparse.ArgumentParser(description="Plot Closed-Loop Deadband & Bunny Ears")
    parser.add_argument("--sweep-results", required=True, help="Path to sweep_results.json")
    parser.add_argument("--out", required=True, help="Output PNG path")
    args = parser.parse_args(argv)

    plot_bunny_ears(args.sweep_results, args.out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
