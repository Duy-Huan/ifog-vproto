"""Diagnostic Plot 4: Overlapping AVAR with 5 IEEE Std 952-2020 Asymptotes & Overlap Band (Table 3).

CLI Contract:
    python3 viz/plot_avar_5regions.py --run data/run01/ --out data/run01/figures/avar_5regions.png
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tier1_offline.config_loader import RAD_S_TO_DEG_H
from tier3_analysis.dual_regime_avar import ieee952_avar_model


def plot_avar_5regions(
    avar_npz_path: Path | str,
    metrics_json_path: Path | str,
    out_png: Path | str,
) -> Path:
    """Plot log-log Overlapping ADEV [deg/h] vs T [s] with all 5 WLS asymptotes (EQ-24, EQ-30)."""
    npz = np.load(avar_npz_path)
    with Path(metrics_json_path).open("r", encoding="utf-8") as fh:
        metrics = json.load(fh)

    taus_fast = npz["taus_fast"]
    adev_fast = npz["adev_fast_deg_h"]
    taus_slow = npz["taus_slow"]
    adev_slow = npz["adev_slow_deg_h"]
    taus_merged = npz["taus_merged"]
    adev_merged = npz["adev_merged_deg_h"]

    fit = metrics["fitted_ieee952"]
    q_si = float(fit["Q_rad"])
    n_si = float(fit["N_rad_per_rt_s"])
    b_si = float(fit["B_rad_per_s"])
    k_si = float(fit["K_rad_per_s32"])
    r_si = float(fit["R_rad_per_s2"])

    t_line = np.geomspace(float(taus_merged[0]), float(taus_merged[-1]), 300)
    total_fit = np.sqrt(ieee952_avar_model(t_line, q_si, n_si, b_si, k_si, r_si)) * RAD_S_TO_DEG_H

    fig, ax = plt.subplots(figsize=(10.5, 6.5), dpi=300)

    # Shaded overlap verification band [0.1, 5.0] s (EQ-30)
    ov = metrics["overlap_check"]
    ax.axvspan(
        ov["overlap_t_min_s"],
        ov["overlap_t_max_s"],
        color="#FEFCBF",
        alpha=0.45,
        label=f"Overlap Zone [0.1, 5] s (max mismatch: {ov['max_relative_mismatch_pct']:.2f}%)",
    )

    ax.loglog(taus_fast, adev_fast, "o", color="#1B365D", markersize=3.5, alpha=0.8, label="Fast-Scale (Tier 2 SystemC-AMS)")
    ax.loglog(taus_slow, adev_slow, "s", color="#0E6251", markersize=3.5, alpha=0.8, label="Slow-Scale (Tier 3, 10h @ 100 Hz)")
    ax.loglog(t_line, total_fit, "-", color="#1A202C", linewidth=1.8, label="Total IEEE 952 WLS 5-Region Fit")

    # Individual 5 asymptotes (only plot positive fitted components)
    y_min = max(1.0e-12, float(np.min(adev_merged)) * 0.25)
    y_max = max(y_min * 10.0, float(np.max(adev_merged)) * 4.0)

    if q_si > 0.0:
        sig_q = (math.sqrt(3.0) * q_si / t_line) * RAD_S_TO_DEG_H
        ax.loglog(t_line, sig_q, "--", color="#805AD5", linewidth=1.0, label=f"QN (-1): Q={fit['Q_arcsec']:.3g} arcsec")
    if n_si > 0.0:
        sig_n = (n_si / np.sqrt(t_line)) * RAD_S_TO_DEG_H
        ax.loglog(t_line, sig_n, "--", color="#2B6CB0", linewidth=1.0, label=f"ARW (-1/2): N={fit['N_deg_per_rt_h']:.4g} deg/rt(h)")
    if b_si > 0.0:
        sig_b = np.full_like(t_line, math.sqrt(2.0 * math.log(2.0) / math.pi) * b_si * RAD_S_TO_DEG_H)
        ax.loglog(t_line, sig_b, "--", color="#38A169", linewidth=1.0, label=f"BI (0): B={fit['B_deg_per_h']:.4g} deg/h")
    if k_si > 0.0:
        sig_k = (k_si * np.sqrt(t_line / 3.0)) * RAD_S_TO_DEG_H
        ax.loglog(t_line, sig_k, "--", color="#D69E2E", linewidth=1.0, label=f"RRW (+1/2): K={fit['K_deg_per_rt_h3']:.4g} deg/h^(3/2)")
    if r_si > 0.0:
        sig_r = (r_si * t_line / math.sqrt(2.0)) * RAD_S_TO_DEG_H
        ax.loglog(t_line, sig_r, "--", color="#9B2C2C", linewidth=1.0, label=f"RR (+1): R={fit['R_deg_per_h2']:.4g} deg/h^2")

    ax.set_ylim(y_min, y_max)
    ax.set_xlabel("Cluster Time T [s]")
    ax.set_ylabel("Overlapping Allan Deviation sigma(T) [deg/h]")
    ax.set_title("IEEE Std 952-2020 Dual-Regime Overlapping AVAR (5 Noise Regions)")
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    ax.legend(loc="best", fontsize=7.5, ncol=2)

    fig.tight_layout()
    out_path = Path(out_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for 5-region Overlapping AVAR plotting."""
    parser = argparse.ArgumentParser(description="Plot IEEE 952 5-Region Overlapping AVAR")
    parser.add_argument("--run", required=True, help="Run directory containing avar_curve.npz & avar_metrics.json")
    parser.add_argument("--out", default=None, help="Output PNG path")
    args = parser.parse_args(argv)

    rdir = Path(args.run)
    out_png = Path(args.out) if args.out else (rdir / "figures" / "avar_5regions.png")
    plot_avar_5regions(rdir / "avar_curve.npz", rdir / "avar_metrics.json", out_png)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
