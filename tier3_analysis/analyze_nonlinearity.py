"""Tier 3 Nonlinearity Analyzer: Deadband Width & Bunny Ears Scale-Factor Error (Gate 2).

Computes quantitative Deadband lock-in width and Bunny Ears peak scale-factor error
from Slow Rate Ramp sweep curves, and evaluates mitigation reduction when 4-state
V_pi locking, ADC Blanking, and PRBS Dither are enabled.

CLI Contract:
    python3 tier3_analysis/analyze_nonlinearity.py \
        --sweep-results data/sweep01/sweep_results.json --out data/sweep01/
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np


def compute_curve_nonlinearity_metrics(
    rates_in_deg_s: np.ndarray, rates_out_deg_s: np.ndarray
) -> dict[str, Any]:
    """Compute Deadband & Bunny Ears quantitative metrics for a rate sweep curve."""
    rates_in = np.asarray(rates_in_deg_s, dtype=np.float64)
    rates_out = np.asarray(rates_out_deg_s, dtype=np.float64)
    rate_err = rates_out - rates_in

    # Relative scale-factor error [ppm] for non-zero rates
    nz_mask = np.abs(rates_in) > 1.0e-12
    sf_err_ppm = np.zeros_like(rates_in)
    sf_err_ppm[nz_mask] = ((rates_out[nz_mask] - rates_in[nz_mask]) / rates_in[nz_mask]) * 1.0e6

    # Deadband region: low-rate points around 0 where |err| / |omega_in| > 5% OR |omega_in| <= 0.05
    # Measure peak absolute rate error inside low-rate deadband zone |omega_in| <= 0.05 deg/s
    # AND effective deadband width where |sf_err| > 50,000 ppm (5% lock-in distortion)
    low_zone = np.abs(rates_in) <= 0.05 + 1e-12
    deadband_peak_err_deg_s = float(np.max(np.abs(rate_err[low_zone])))

    locked_mask = nz_mask & (np.abs(sf_err_ppm) > 5.0e4)
    if np.any(locked_mask):
        deadband_width_deg_s = float(2.0 * np.max(np.abs(rates_in[locked_mask])))
    else:
        deadband_width_deg_s = float(2.0 * deadband_peak_err_deg_s)

    # Bunny Ears peak: max absolute rate error & max relative SF error [ppm] across sweep
    bunny_ears_peak_err_deg_s = float(np.max(np.abs(rate_err)))
    bunny_ears_peak_sf_ppm = float(np.max(np.abs(sf_err_ppm[nz_mask]))) if np.any(nz_mask) else 0.0

    # Separate positive & negative side peaks to verify bilateral Bunny Ears signature
    pos_mask = rates_in > 0.0
    neg_mask = rates_in < 0.0
    pos_peak_ppm = float(np.max(np.abs(sf_err_ppm[pos_mask]))) if np.any(pos_mask) else 0.0
    neg_peak_ppm = float(np.max(np.abs(sf_err_ppm[neg_mask]))) if np.any(neg_mask) else 0.0

    return {
        "deadband_width_deg_per_s": deadband_width_deg_s,
        "deadband_peak_err_deg_per_s": deadband_peak_err_deg_s,
        "bunny_ears_peak_err_deg_per_s": bunny_ears_peak_err_deg_s,
        "bunny_ears_peak_sf_ppm": bunny_ears_peak_sf_ppm,
        "bunny_ears_pos_peak_ppm": pos_peak_ppm,
        "bunny_ears_neg_peak_ppm": neg_peak_ppm,
        "rate_error_deg_per_s": rate_err.tolist(),
        "sf_error_ppm": sf_err_ppm.tolist(),
    }


def analyze_sweep_nonlinearity(sweep_data: dict[str, Any]) -> dict[str, Any]:
    """Compare uncompensated vs compensated sweep curves and compute Gate 2 reduction %."""
    rates_in = np.asarray(sweep_data["rates_in_deg_per_s"], dtype=np.float64)
    uncomp_out = np.asarray(sweep_data["uncompensated_out_deg_per_s"], dtype=np.float64)
    comp_out = np.asarray(sweep_data["compensated_out_deg_per_s"], dtype=np.float64)

    m_uncomp = compute_curve_nonlinearity_metrics(rates_in, uncomp_out)
    m_comp = compute_curve_nonlinearity_metrics(rates_in, comp_out)

    def _reduction_pct(before: float, after: float) -> float:
        if before <= 0.0:
            return 0.0
        return float(100.0 * (1.0 - after / before))

    deadband_red = _reduction_pct(
        m_uncomp["deadband_peak_err_deg_per_s"], m_comp["deadband_peak_err_deg_per_s"]
    )
    bunny_sf_red = _reduction_pct(
        m_uncomp["bunny_ears_peak_sf_ppm"], m_comp["bunny_ears_peak_sf_ppm"]
    )
    bunny_err_red = _reduction_pct(
        m_uncomp["bunny_ears_peak_err_deg_per_s"], m_comp["bunny_ears_peak_err_deg_per_s"]
    )

    return {
        "spec_id": "IFOG-SIM-SPEC-004",
        "gate_id": "Gate-2",
        "uncompensated": m_uncomp,
        "compensated": m_comp,
        "deadband_reduction_pct": deadband_red,
        "bunny_ears_sf_reduction_pct": bunny_sf_red,
        "bunny_ears_err_reduction_pct": bunny_err_red,
        "gate2_pass": bool(deadband_red >= 90.0 and bunny_sf_red >= 90.0),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Deadband & Bunny Ears nonlinearity analysis."""
    parser = argparse.ArgumentParser(
        description="Analyze Deadband & Bunny Ears Nonlinearity from Slow Rate Ramp Sweep (Gate 2)"
    )
    parser.add_argument("--sweep-results", required=True, help="Path to sweep_results.json")
    parser.add_argument("--out", required=True, help="Output directory for nonlinearity_summary.json")
    args = parser.parse_args(argv)

    with Path(args.sweep_results).open("r", encoding="utf-8") as fh:
        sweep_data = json.load(fh)

    summary = analyze_sweep_nonlinearity(sweep_data)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "nonlinearity_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
