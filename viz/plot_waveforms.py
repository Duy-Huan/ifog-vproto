"""Diagnostic Plot 1: TIA Transients, ADC Blanking Window, and 2*pi Phase Ramp (Table 3).

CLI Contract:
    python3 viz/plot_waveforms.py --run data/run01/ --out data/run01/figures/waveforms.png
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from tier3_analysis.binary_io import read_micro_records


def plot_waveforms(
    micro_bin_path: Path | str,
    out_png: Path | str,
    summary_json_path: Path | str | None = None,
    max_samples: int = 256,
) -> Path:
    """Plot micro-sample V_TIA(t), ADC blanking window, V_drv(t), and 2*pi ramp."""
    data = read_micro_records(micro_bin_path)
    n = min(len(data["t"]), max_samples)
    if n == 0:
        raise ValueError("micro_waveforms.bin contains zero samples")

    t_us = data["t"][:n] * 1.0e6
    v_tia = data["v_tia"][:n]
    v_adc = data["v_adc"][:n]
    v_drv = data["v_drv"][:n]
    phi_ramp = data["phi_ramp"][:n]
    in_blank = data["in_blanking"][:n] > 0

    meta_note = ""
    if summary_json_path is not None and Path(summary_json_path).exists():
        with Path(summary_json_path).open("r", encoding="utf-8") as fh:
            s = json.load(fh)
        ts_us = s.get("tia_ts_0p1pct_s", 0.0) * 1.0e6
        eta_b = s.get("eta_blanking", 1.0)
        meta_note = f" | t_s(0.1%) = {ts_us:.3f} us, eta_b = {eta_b:.2f}"

    fig, axes = plt.subplots(3, 1, figsize=(10.5, 7.5), sharex=True, dpi=300)

    # Panel 1: TIA transient & ADC Blanking window
    ax = axes[0]
    ax.plot(t_us, v_tia, label="V_TIA(t) [V]", color="#1B365D", linewidth=1.2)
    ax.plot(t_us, v_adc, "--", label="V_adc(t) [V]", color="#0E6251", linewidth=1.0, alpha=0.85)
    ax.scatter(
        t_us[in_blank],
        v_adc[in_blank],
        s=10,
        color="#975A16",
        label="ADC Blanking Clean Window",
        zorder=4,
    )
    ax.set_ylabel("Voltage [V]")
    ax.set_title(f"TIA Transient Response & ADC Blanking Alignment{meta_note}")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8)

    # Panel 2: MIOC Drive Voltage V_drv(t)
    ax = axes[1]
    ax.step(t_us, v_drv, where="post", color="#9B2C2C", linewidth=1.1, label="V_drv(t) [V]")
    ax.set_ylabel("MIOC V_drv [V]")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8)

    # Panel 3: Digital Phase Ramp modulo 2*pi
    ax = axes[2]
    ax.plot(t_us, phi_ramp, color="#2B6CB0", linewidth=1.2, label="phi_ramp [rad] (mod 2*pi)")
    ax.axhline(np.pi, color="#718096", linestyle="--", linewidth=0.8)
    ax.axhline(-np.pi, color="#718096", linestyle="--", linewidth=0.8)
    ax.set_ylabel("Phase [rad]")
    ax.set_xlabel("Simulation Time [us]")
    ax.grid(True, linestyle=":", alpha=0.5)
    ax.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    out_path = Path(out_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300)
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for waveform plotting."""
    parser = argparse.ArgumentParser(description="Plot TIA Transients & Blanking Waveforms")
    parser.add_argument("--run", required=True, help="Run directory containing micro_waveforms.bin")
    parser.add_argument("--out", default=None, help="Output PNG path")
    parser.add_argument("--max-samples", type=int, default=256, help="Max micro-samples to render")
    args = parser.parse_args(argv)

    rdir = Path(args.run)
    out_png = Path(args.out) if args.out else (rdir / "figures" / "waveforms.png")
    plot_waveforms(
        rdir / "micro_waveforms.bin",
        out_png,
        summary_json_path=rdir / "sim_summary.json",
        max_samples=args.max_samples,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
