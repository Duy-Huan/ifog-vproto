"""Publication-quality 300-DPI diagnostic plots for IFOG-SIM-SPEC-007 (PHY-01 & CAL-01)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def plot_spec007_calibration_validation(
    cal_dir: Path | str,
    out_png: Path | str,
) -> Path:
    """Render 3-panel Before vs After vs Hardware Truth validation plot for CAL-01 (EQ-53)."""
    cdir = Path(cal_dir)
    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)

    curves = np.load(cdir / "spec007_calibration_curves.npz")
    summary = json.loads((cdir / "spec007_calibration_summary.json").read_text(encoding="utf-8"))
    eb = summary["error_before_pct"]
    ea = summary["error_after_pct"]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6), dpi=300)

    # Panel 1: Static AVAR Before vs After vs Measured Truth
    ax0 = axes[0]
    ax0.loglog(curves["taus_s"], curves["avar_meas_deg_h"], "ko", ms=3.5, label="Hardware Truth")
    ax0.loglog(
        curves["taus_s"],
        curves["avar_pre_deg_h"],
        "--",
        color="#d62728",
        lw=1.8,
        label=f"Uncalibrated ({eb['avar_nrmse_pct']:.1f}%)",
    )
    ax0.loglog(
        curves["taus_s"],
        curves["avar_post_deg_h"],
        "-",
        color="#1f77b4",
        lw=2.0,
        label=f"SPEC-007 Calibrated ({ea['avar_nrmse_pct']:.2f}%)",
    )
    ax0.set_title("Stage A: Static AVAR (c_1/f, R_facet, eta_PD)", fontsize=10, fontweight="bold")
    ax0.set_xlabel("Cluster Time tau [s]")
    ax0.set_ylabel("ADEV sigma(tau) [deg/h]")
    ax0.grid(True, which="both", alpha=0.3)
    ax0.legend(fontsize=8, loc="best")

    # Panel 2: Slow-Rate Ramp Deadband & Bunny Ears Residual
    ax1 = axes[1]
    w_in = curves["omega_in_deg_h"]
    ax1.plot(w_in, curves["db_meas_deg_h"] - w_in, "ko", ms=3.0, label="Hardware Truth")
    ax1.plot(
        w_in,
        curves["db_pre_deg_h"] - w_in,
        "--",
        color="#d62728",
        lw=1.8,
        label=f"Uncalibrated ({eb['deadband_nrmse_pct']:.1f}%)",
    )
    ax1.plot(
        w_in,
        curves["db_post_deg_h"] - w_in,
        "-",
        color="#2ca02c",
        lw=2.0,
        label=f"SPEC-007 Calibrated ({ea['deadband_nrmse_pct']:.2f}%)",
    )
    ax1.set_title("Stage B: Deadband & Bunny Ears (C_xtalk, G_xtalk)", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Input Rate Omega_in [deg/h]")
    ax1.set_ylabel("Rate Error Omega_out - Omega_in [deg/h]")
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=8, loc="best")

    # Panel 3: Thermal Chamber Ramp Bias Drift
    ax2 = axes[2]
    t_min = curves["t_thermal_s"] / 60.0
    ax2.plot(t_min, curves["bias_meas_deg_h"], "ko", ms=3.5, label="Hardware Truth")
    ax2.plot(
        t_min,
        curves["bias_pre_deg_h"],
        "--",
        color="#d62728",
        lw=1.8,
        label=f"Uncalibrated ({eb['thermal_bias_nrmse_pct']:.1f}%)",
    )
    ax2.plot(
        t_min,
        curves["bias_post_deg_h"],
        "-",
        color="#9467bd",
        lw=2.0,
        label=f"SPEC-007 Calibrated ({ea['thermal_bias_nrmse_pct']:.2f}%)",
    )
    ax2.set_title("Stage C: Thermal Chamber Ramp (D_th, dz_quad, a_Vpi)", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Chamber Ramp Time [min]")
    ax2.set_ylabel("Thermal Bias Drift [deg/h]")
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=8, loc="best")

    fig.suptitle(
        "IFOG-SIM-SPEC-007 Inverse Calibration Validation (CAL-01 / EQ-53): >40% Baseline -> <5% Calibrated",
        fontsize=11.5,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out


def plot_spec007_physics_winding_mioc(
    phy_dir: Path | str,
    out_png: Path | str,
) -> Path:
    """Render 3-panel SPEC-007 high-fidelity physics figure for PHY-01 (EQ-45..EQ-52)."""
    pdir = Path(phy_dir)
    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)

    curves = np.load(pdir / "spec007_physics_curves.npz")
    summary = json.loads((pdir / "spec007_physics_summary.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.6), dpi=300)

    # Panel 1: Quadrupole vs Octupole Thermo-Optical Drift (Shupe + Elasto-Optic Stress)
    ax0 = axes[0]
    t_min = curves["t_lut_s"] / 60.0
    ax0.plot(
        t_min,
        (curves["phi_shupe_quad"] + curves["phi_stress_quad"]) * 1.0e6,
        color="#d62728",
        lw=1.9,
        label="Quadrupole (Shupe + Stress)",
    )
    ax0.plot(
        t_min,
        curves["phi_shupe_quad"] * 1.0e6,
        "--",
        color="#ff7f0e",
        lw=1.4,
        label="Quadrupole (Shupe Only)",
    )
    ax0.plot(
        t_min,
        curves["phi_tot_oct"] * 1.0e6,
        color="#1f77b4",
        lw=2.0,
        label=f"Octupole (-{summary['octupole_drift_reduction_pct']:.1f}%)",
    )
    ax0.set_title("EQ-45/46: Quadrupole vs Octupole + Stress Drift", fontsize=10, fontweight="bold")
    ax0.set_xlabel("Thermal Ramp Time [min]")
    ax0.set_ylabel("Non-Reciprocal Phase [urad]")
    ax0.grid(True, alpha=0.3)
    ax0.legend(fontsize=8, loc="best")

    # Panel 2: Dynamic Scale Factor K_opt(t) & Half-Wave Voltage V_pi(t) from LUT v2
    ax1 = axes[1]
    l1 = ax1.plot(t_min, curves["k_opt_rel_ppm"], color="#2ca02c", lw=2.0, label="dK_opt / K_opt,0 [ppm]")
    ax1.set_title("EQ-47/48/49: Dynamic LUT v2 Optical Drift", fontsize=10, fontweight="bold")
    ax1.set_xlabel("Thermal Ramp Time [min]")
    ax1.set_ylabel("Scale Factor Drift [ppm]", color="#2ca02c")
    ax1.grid(True, alpha=0.3)
    ax1b = ax1.twinx()
    l2 = ax1b.plot(t_min, curves["v_pi_t_V"], "--", color="#9467bd", lw=1.8, label="V_pi(t) [V]")
    ax1b.set_ylabel("MIOC V_pi(t) [V]", color="#9467bd")
    lines = l1 + l2
    ax1.legend(lines, [ln.get_label() for ln in lines], fontsize=8, loc="best")

    # Panel 3: Capacitive Crosstalk Spike & MIOC Electro-Acoustic Ringing on V_TIA(t)
    ax2 = axes[2]
    n_show = min(96, len(curves["t_micro_us"]))
    t_us = curves["t_micro_us"][:n_show]
    ax2.plot(t_us, curves["v_tia_on"][:n_show], color="#d62728", lw=1.6, label="SPEC-007 (C_xtalk + MIOC Ac.)")
    ax2.plot(t_us, curves["v_tia_nocap"][:n_show], "--", color="#1f77b4", lw=1.5, label="Legacy (C_xtalk = 0, Ideal MIOC)")
    ax2.set_title("EQ-50/51: MIOC Acoustic & C_xtalk dV/dt Transient", fontsize=10, fontweight="bold")
    ax2.set_xlabel("Sub-tau Micro-Time [us]")
    ax2.set_ylabel("TIA Output V_TIA(t) [V]")
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=8, loc="best")

    fig.suptitle(
        "IFOG-SIM-SPEC-007 Predictive Physics Verification (PHY-01 / EQ-45..EQ-52)",
        fontsize=11.5,
        fontweight="bold",
        y=0.99,
    )
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out
