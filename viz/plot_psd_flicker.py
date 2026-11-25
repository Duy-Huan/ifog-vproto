"""Diagnostic Plot 3: Welch PSD Verification of 1/f Flicker Filtering vs Leakage (Table 3).

CLI Contract:
    python3 viz/plot_psd_flicker.py --linear data/lin/sim_out.bin \
        --nonlinear data/nl/sim_out.bin --out data/run01/figures/psd_flicker.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tier3_analysis.binary_io import compute_welch_psd, fit_loglog_slope, read_sim_records


def plot_psd_flicker(
    linear_bin: Path | str,
    nonlinear_bin: Path | str,
    out_png: Path | str,
    f_fit_min: float = 15.0,
    f_fit_max: float = 1500.0,
) -> dict[str, float]:
    """Plot linear (slope ~0) vs nonlinear (slope ~-1) Welch PSD in dB/Hz (Gate 3)."""
    rec_lin = read_sim_records(linear_bin)
    rec_nl = read_sim_records(nonlinear_bin)

    dt_lin = float(np.median(np.diff(rec_lin["t"])))
    dt_nl = float(np.median(np.diff(rec_nl["t"])))
    trim_lin = min(len(rec_lin["omega_out"]) // 10, 500)
    trim_nl = min(len(rec_nl["omega_out"]) // 10, 500)

    f_lin, p_lin = compute_welch_psd(rec_lin["omega_out"][trim_lin:], fs_Hz=1.0 / dt_lin, nperseg=8192)
    f_nl, p_nl = compute_welch_psd(rec_nl["omega_out"][trim_nl:], fs_Hz=1.0 / dt_nl, nperseg=8192)

    slope_lin = fit_loglog_slope(f_lin, p_lin, f_fit_min, f_fit_max)
    slope_nl = fit_loglog_slope(f_nl, p_nl, f_fit_min, f_fit_max)

    fig, ax = plt.subplots(figsize=(9.5, 5.5), dpi=300)
    mask_l = (f_lin >= 1.0) & (f_lin <= 5.0e4) & (p_lin > 0.0)
    mask_n = (f_nl >= 1.0) & (f_nl <= 5.0e4) & (p_nl > 0.0)

    ax.semilogx(
        f_lin[mask_l],
        10.0 * np.log10(p_lin[mask_l]),
        color="#1B365D",
        linewidth=1.2,
        label=f"Linear (TIA 1/f Filtered, slope={slope_lin:+.2f})",
    )
    ax.semilogx(
        f_nl[mask_n],
        10.0 * np.log10(p_nl[mask_n]),
        color="#9B2C2C",
        linewidth=1.2,
        label=f"Nonlinear (Crosstalk + G2/G3 Leakage, slope={slope_nl:+.2f})",
    )

    # Reference -10 dB/dec (1/f) slope line anchored at midpoint of nonlinear band
    f_ref = np.geomspace(f_fit_min, f_fit_max, 50)
    idx_anchor = int(np.argmin(np.abs(f_nl - 100.0)))
    p_anchor = max(float(p_nl[idx_anchor]), 1e-30)
    ref_line = p_anchor * (100.0 / f_ref)
    ax.semilogx(
        f_ref,
        10.0 * np.log10(ref_line),
        "--",
        color="#975A16",
        linewidth=1.3,
        label="Reference 1/f (-10 dB/dec, slope = -1)",
    )

    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Welch PSD [dB re (rad/s)^2/Hz]")
    ax.set_title("1/f Flicker Noise Modulation Rejection vs Nonlinear Leakage (Gate 3)")
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=8.5)

    fig.tight_layout()
    out_path = Path(out_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)

    return {"slope_linear": slope_lin, "slope_nonlinear": slope_nl}


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Welch PSD 1/f flicker diagnostics."""
    parser = argparse.ArgumentParser(description="Plot Welch PSD for 1/f Flicker Verification")
    parser.add_argument("--linear", required=True, help="Path to linear sim_out.bin")
    parser.add_argument("--nonlinear", required=True, help="Path to nonlinear sim_out.bin")
    parser.add_argument("--out", required=True, help="Output PNG path")
    args = parser.parse_args(argv)

    plot_psd_flicker(args.linear, args.nonlinear, args.out)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
