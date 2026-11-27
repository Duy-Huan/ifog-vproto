"""Publication-grade 300-DPI visualizers for v4.1.0 Group E Industrial Scenarios (IND-01..IND-06)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def apply_industrial_style() -> None:
    """Apply clean publication-grade matplotlib styling for Group E figures."""
    plt.rcParams.update(
        {
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "font.size": 9.5,
        }
    )


def plot_ind01_lab_validation(run_dir: Path | str, out_path: Path | str) -> Path:
    """Plot IND-01: 3-Rig Physical Lab CAS-4 Validation (10h AVAR, Rate-Table Deadband, Thermal Chamber)."""
    apply_industrial_style()
    rdir = Path(run_dir)
    data = json.loads((rdir / "ind01_lab_validation.json").read_text(encoding="utf-8"))
    curves = np.load(rdir / "ind01_lab_curves.npz")

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 4.8))
    fig.suptitle(
        f"IND-01 Physical Lab CAS-{data['nasa_cas_level']} Validation "
        f"(Max Error: {data['max_error_before_pct']:.1f}% -> {data['max_error_after_pct']:.2f}%, "
        f"ASME V&V 20 max |E|/u_val = {data['max_ratio_E_over_u_val_after']:.2f})",
        fontsize=12,
        fontweight="bold",
    )

    # Panel 1: 10h Static AVAR
    ax = axes[0]
    ax.errorbar(
        curves["taus_s"],
        curves["avar_meas"],
        yerr=curves["u_avar_abs"],
        fmt="o",
        color="#111827",
        ms=4,
        capsize=2,
        label="Lab 10h AVAR (u_D)",
    )
    ax.loglog(curves["taus_s"], curves["avar_pre"], "--", color="#DC2626", lw=1.6, label="Uncalibrated")
    ax.loglog(curves["taus_s"], curves["avar_post"], "-", color="#2563EB", lw=2.2, label="CAS-4 Calibrated")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Averaging Time tau [s]")
    ax.set_ylabel("ADEV [deg/h]")
    ax.set_title("(a) 10h Granite-Table Static AVAR")
    ax.legend(fontsize=8)

    # Panel 2: Slow Rate-Table Deadband/Bunny Ears zoom [-3, +3] deg/h
    ax = axes[1]
    w_in = curves["omega_in_deg_h"]
    mask = np.abs(w_in) <= 3.2
    ax.plot(w_in[mask], curves["err_meas_deg_h"][mask], "ko", ms=4, label="Rate-Table Lab")
    ax.plot(w_in[mask], curves["err_pre_deg_h"][mask], "--", color="#DC2626", lw=1.6, label="Uncalibrated")
    ax.plot(w_in[mask], curves["err_post_deg_h"][mask], "-", color="#059669", lw=2.2, label="Calibrated")
    ax.set_xlabel("Input Rate Omega_in [deg/h]")
    ax.set_ylabel("Rate Error [deg/h]")
    ax.set_title("(b) Rate-Table Deadband & Bunny Ears")
    ax.legend(fontsize=8)

    # Panel 3: Thermal Chamber -40..+85 degC Bias Drift
    ax = axes[2]
    ax.plot(curves["T_chamber_C"], curves["bias_meas_deg_h"], "ko", ms=4, label="Thermal Chamber")
    ax.plot(curves["T_chamber_C"], curves["bias_pre_deg_h"], "--", color="#DC2626", lw=1.6, label="Uncalibrated")
    ax.plot(curves["T_chamber_C"], curves["bias_post_deg_h"], "-", color="#7C3AED", lw=2.2, label="Calibrated")
    ax.set_xlabel("Chamber Temperature [degC]")
    ax.set_ylabel("Thermal Bias Drift [deg/h]")
    ax.set_title("(c) -40..+85 degC Chamber Bias")
    ax.legend(fontsize=8)

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    fig.savefig(out_p, dpi=300)
    plt.close(fig)
    return out_p


def plot_ind02_fixed_point_rtl(run_dir: Path | str, out_path: Path | str) -> Path:
    """Plot IND-02: Bit-True FPGA Fixed-Point (Q16.32 vs Q8.24 vs Float64) across 2/4/6-State DSP."""
    apply_industrial_style()
    rdir = Path(run_dir)
    data = json.loads((rdir / "ind02_fixed_point_rtl.json").read_text(encoding="utf-8"))
    curves = np.load(rdir / "ind02_fxp_curves.npz")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
    fig.suptitle(
        "IND-02 Bit-True FPGA Fixed-Point DSP & SystemVerilog RTL (2-State / 4-State / 6-State, 0-LSB Match)",
        fontsize=12,
        fontweight="bold",
    )

    # Panel 1: Log-scale Quantization RMS Error (Q16.32 48-bit vs Q8.24 32-bit trunc) across 2/4/6-State
    ax = axes[0]
    mode_keys = ["2state", "4state", "6state"]
    labels = ["2-State\n(alpha=pi/4)", "4-State\n(alpha=pi/4)", "6-State\n(alpha=pi/3)"]
    q48 = [data["modes"][k]["variants"]["q16_32"]["quant_err_rms_deg_h"] for k in mode_keys]
    q32 = [data["modes"][k]["variants"]["q8_24_trunc"]["quant_err_rms_deg_h"] for k in mode_keys]
    x = np.arange(len(mode_keys))
    w = 0.34
    b1 = ax.bar(x - w / 2, q48, w, color="#2563EB", label="FPGA Q16.32 (48-bit, 0-LSB RTL)")
    b2 = ax.bar(x + w / 2, q32, w, color="#DC2626", label="FPGA Q8.24 (32-bit Trunc)")
    ax.set_yscale("log")
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("RMS Quantization Error vs Float64 [deg/h]")
    ax.set_title("(a) Register Bit-Width Sensitivity (2 / 4 / 6 States)")
    ax.legend(fontsize=8.5)
    for bar in list(b1) + list(b2):
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h * 1.15, f"{h:.2f}", ha="center", va="bottom", fontsize=8)

    # Panel 2: Closed-loop step response Float64 vs Q16.32 across all 3 DSP modes
    ax = axes[1]
    colors = {"2state": "#059669", "4state": "#D97706", "6state": "#2563EB"}
    for k, lbl in zip(mode_keys, ("2-State", "4-State", "6-State")):
        ax.plot(curves[f"t_ms_{k}_float64"], curves[f"w_{k}_float64"], "-", color=colors[k], lw=2.0, label=f"{lbl} Float64")
        ax.plot(curves[f"t_ms_{k}_q16_32"], curves[f"w_{k}_q16_32"], ":", color="#111827", lw=1.4, label=f"{lbl} Q16.32")
    ax.set_xlabel("Time [ms]")
    ax.set_ylabel("Output Rate [deg/s]")
    ax.set_title("(b) Step Response Overlay (Float64 vs Q16.32, 0 Overflows)")
    ax.legend(fontsize=7.5, ncol=2)

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    fig.savefig(out_p, dpi=300)
    plt.close(fig)
    return out_p


def plot_ind03_fem_3d(run_dir: Path | str, out_path: Path | str) -> Path:
    """Plot IND-03: 3D ANSYS/COMSOL FEM T(r,theta,z,t) & sigma -> shupe_lut.bin v2 -> Tier 2."""
    apply_industrial_style()
    rdir = Path(run_dir)
    data = json.loads((rdir / "ind03_fem_3d.json").read_text(encoding="utf-8"))
    curves = np.load(rdir / "ind03_fem3d_curves.npz")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
    fig.suptitle(
        f"IND-03 3D Cylindrical FEM (dT={data['max_spatial_dT_K']:.1f} K, "
        f"sigma={data['max_stress_MPa']:.2f} MPa, Octupole Suppression = {data['octupole_suppression_ratio']:.2f}x)",
        fontsize=12,
        fontweight="bold",
    )

    t_min = curves["t_s"] / 60.0
    ax = axes[0]
    ax.plot(t_min, curves["omega_1d_quad_deg_h"], "--", color="#6B7280", lw=1.8, label="1D Radial Quadrupole")
    ax.plot(t_min, curves["omega_3d_quad_deg_h"], "-", color="#DC2626", lw=2.2, label="3D FEM Quadrupole (Eccentric)")
    ax.plot(t_min, curves["omega_3d_oct_deg_h"], "-", color="#059669", lw=2.2, label="3D FEM Octupole (ABBA-BAAB)")
    ax.set_xlabel("Time [min]")
    ax.set_ylabel("Thermal + Stress Drift [deg/h]")
    ax.set_title("(a) 1D vs 3D Asymmetric FEM Drift")
    ax.legend(fontsize=8.5)

    ax = axes[1]
    ax.plot(t_min, curves["phi_shupe_3d_q"] * 1.0e6, "-", color="#2563EB", lw=2.0, label="3D Shupe dT/dt [urad]")
    ax.plot(t_min, curves["phi_stress_3d_q"] * 1.0e6, "-", color="#D97706", lw=2.0, label="3D Elasto-Optic Stress [urad]")
    ax.set_xlabel("Time [min]")
    ax.set_ylabel("Non-Reciprocal Phase [urad]")
    ax.set_title("(b) 3D Shupe vs Potting Stress Decomposition")
    ax.legend(fontsize=8.5, loc="upper left")
    ax2 = ax.twinx()
    ax2.plot(t_min, curves["k_opt_rel_ppm"], ":", color="#7C3AED", lw=1.8, label="dK_opt/K_opt [ppm]")
    ax2.set_ylabel("Scale-Factor Shift [ppm]", color="#7C3AED")

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    fig.savefig(out_p, dpi=300)
    plt.close(fig)
    return out_p


def plot_ind04_random_vib_psd(run_dir: Path | str, out_path: Path | str) -> Path:
    """Plot IND-04: MIL-STD-810H / DO-160G Random Vibration PSD & 2-DOF Isolator/Bobbin Mitigation."""
    apply_industrial_style()
    rdir = Path(run_dir)
    data = json.loads((rdir / "ind04_random_vib_psd.json").read_text(encoding="utf-8"))
    curves = np.load(rdir / "ind04_vib_psd_curves.npz")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
    fig.suptitle(
        f"IND-04 MIL-STD-810H / DO-160G Random Vibration PSD "
        f"(Coil g_rms: {data['coil_hard_mounted_g_rms']:.2f} -> {data['coil_isolated_g_rms']:.2f} g, "
        f"VRE Bias Reduced {data['vre_reduction_ratio']:.2f}x)",
        fontsize=11.5,
        fontweight="bold",
    )

    f = curves["freqs_hz"]
    ax = axes[0]
    ax.loglog(f, curves["psd_in"], "--", color="#111827", lw=1.8, label=f"MIL-STD-810H Input ({data['input_g_rms']:.2f} g_rms)")
    ax.loglog(f, curves["psd_hard"], "-", color="#DC2626", lw=2.0, label=f"Hard-Mounted Bobbin ({data['coil_hard_mounted_g_rms']:.2f} g_rms)")
    ax.loglog(f, curves["psd_iso"], "-", color="#059669", lw=2.2, label=f"Elastomer Isolated ({data['coil_isolated_g_rms']:.2f} g_rms)")
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Acceleration PSD [g^2/Hz]")
    ax.set_title("(a) Broadband Random Vibration PSD (20-2000 Hz)")
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.loglog(f, curves["trans_hard"], "-", color="#DC2626", lw=2.0, label=f"Bobbin Only (fn={data['bobbin_fn_Hz']:.0f} Hz, Q={data['bobbin_Q']:.0f})")
    ax.loglog(f, curves["trans_iso"], "-", color="#2563EB", lw=2.2, label=f"Isolator + Bobbin (f_iso={data['isolator_fn_Hz']:.0f} Hz)")
    ax.axhline(1.0, color="#6B7280", ls=":", lw=1.2)
    ax.set_xlabel("Frequency [Hz]")
    ax.set_ylabel("Transmissibility |H_mech(f)|")
    ax.set_title(
        f"(b) 2-DOF Transmissibility | Tier 2 VRE: {data['vre_bias_hard_deg_h']:.2f} -> {data['vre_bias_isolated_deg_h']:.2f} deg/h"
    )
    ax.legend(fontsize=8)

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    fig.savefig(out_p, dpi=300)
    plt.close(fig)
    return out_p


def plot_ind05_fmu_multi_instance(run_dir: Path | str, out_path: Path | str) -> Path:
    """Plot IND-05: 3 Concurrent Independent FMI 3.0.2 FMU Axes (6-State / 4-State / 2-State) in 1 Process."""
    apply_industrial_style()
    rdir = Path(run_dir)
    data = json.loads((rdir / "ind05_fmu_multi_instance.json").read_text(encoding="utf-8"))
    curves = np.load(rdir / "ind05_fmu_multi_curves.npz")

    fig, axes = plt.subplots(1, 2, figsize=(13.5, 4.8))
    fig.suptitle(
        "IND-05 Multi-Instance Pure-C++17 Source-Code FMI 3.0.2 FMU "
        "(3 Concurrent Axes in 1 Process: 6-State / 4-State / 2-State, 0 XSD Errors)",
        fontsize=11.5,
        fontweight="bold",
    )

    t_ms = curves["t_ms"]
    ax = axes[0]
    specs = [
        ("axis_x_6state", "Axis X (6-State, target +5 deg/s)", "#2563EB"),
        ("axis_y_4state", "Axis Y (4-State, target -12 deg/s)", "#D97706"),
        ("axis_z_2state", "Axis Z (2-State, target +25 deg/s)", "#059669"),
    ]
    for key, lbl, col in specs:
        ax.plot(t_ms, curves[f"{key}_deg_s"], "-", color=col, lw=2.2, label=lbl)
        tgt = data["concurrent_axes"][key]["target_deg_s"]
        ax.axhline(tgt, color=col, ls="--", lw=1.0, alpha=0.6)
    ax.set_xlabel("Co-Simulation Time [ms]")
    ax.set_ylabel("FMU Axis Rate Output [deg/s]")
    ax.set_title("(a) Interleaved In-Process Lockstep Execution")
    ax.legend(fontsize=8)

    ax = axes[1]
    names = ["Axis X\n(6-State)", "Axis Y\n(4-State)", "Axis Z\n(2-State)"]
    errs = [data["concurrent_axes"][k]["err_pct"] for k, _, _ in specs]
    bars = ax.bar(names, errs, color=["#2563EB", "#D97706", "#059669"], width=0.5)
    ax.axhline(0.5, color="#DC2626", ls="--", lw=1.4, label="Pass Limit (0.5%)")
    ax.set_ylabel("Steady-State Tracking Error [%]")
    ax.set_title("(b) Zero Cross-Axis Interference Verification")
    ax.legend(fontsize=8.5)
    for bar, e in zip(bars, errs):
        ax.text(bar.get_x() + bar.get_width() / 2, e + 0.015, f"{e:.3f}%", ha="center", va="bottom", fontsize=8.5)

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    fig.savefig(out_p, dpi=300)
    plt.close(fig)
    return out_p


def plot_ind06_pvt_aging_corners(run_dir: Path | str, out_path: Path | str) -> Path:
    """Plot IND-06: 12-Corner PVT Matrix + 10-Year SLD/MIOC Aging & 50 krad(Si) Space TID."""
    apply_industrial_style()
    rdir = Path(run_dir)
    data = json.loads((rdir / "ind06_pvt_aging_corners.json").read_text(encoding="utf-8"))

    fig, axes = plt.subplots(1, 2, figsize=(13.8, 4.8))
    fig.suptitle(
        f"IND-06 Worst-Case 12-Corner PVT & 10-Yr / 50 krad(Si) Space Aging "
        f"(WC PVT ARW={data['worst_case_pvt_arw_deg_per_rt_h']:.5f}, EOL ARW={data['eol_50krad_arw_deg_per_rt_h']:.5f} deg/rt-h)",
        fontsize=11.5,
        fontweight="bold",
    )

    # Panel 1: 12-Corner PVT ARW bars colored by Process Corner
    ax = axes[0]
    corners = data["pvt_corners"]
    x = np.arange(len(corners))
    arws = [c["arw_deg_per_rt_h"] * 1.0e3 for c in corners]  # mdeg/rt-h
    cols = ["#2563EB" if c["process"] == "Nominal" else "#DC2626" for c in corners]
    ax.bar(x, arws, color=cols, width=0.68)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{int(c['T_C']):+d}C\n{int(round(c['rail_scale']*100))}%" for c in corners],
        fontsize=7.5,
    )
    ax.set_ylabel("ARW [mdeg / rt-h]")
    ax.set_title("(a) 12-Corner PVT Sweep (Blue=Nominal, Red=WC 3-sigma)")

    # Panel 2: 10-Year Aging + Space TID (0..50 krad) Optical Power & ARW Degradation
    ax = axes[1]
    ms = data["aging_tid_milestones"]
    m_lbls = [m["label"].replace("_", "\n") for m in ms]
    xm = np.arange(len(ms))
    pwr_pct = [m["total_power_factor"] * 100.0 for m in ms]
    arw_mdeg = [m["arw_deg_per_rt_h"] * 1.0e3 for m in ms]
    ax.bar(xm - 0.18, pwr_pct, width=0.36, color="#059669", label="Optical Power Remaining [%]")
    ax.set_xticks(xm)
    ax.set_xticklabels(m_lbls, fontsize=8)
    ax.set_ylabel("Remaining Optical Power [%]", color="#059669")
    ax.set_ylim(0, 115)
    ax2 = ax.twinx()
    ax2.plot(xm + 0.18, arw_mdeg, "o-", color="#7C3AED", lw=2.2, ms=6, label="Mission ARW [mdeg/rt-h]")
    ax2.set_ylabel("ARW [mdeg / rt-h]", color="#7C3AED")
    ax.set_title("(b) 10-Yr SLD/MIOC Aging & 50 krad(Si) RIA")

    out_p = Path(out_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.92))
    fig.savefig(out_p, dpi=300)
    plt.close(fig)
    return out_p


def plot_all_industrial_figures(run_dir: Path | str, fig_dir: Path | str) -> list[Path]:
    """Generate all available Group E (IND-01..IND-06) 300-DPI PNG figures for a run directory."""
    rdir = Path(run_dir)
    fdir = Path(fig_dir)
    fdir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    mapping = [
        ("ind01_lab_validation.json", "fig_ind01_lab_validation.png", plot_ind01_lab_validation),
        ("ind02_fixed_point_rtl.json", "fig_ind02_fixed_point_rtl.png", plot_ind02_fixed_point_rtl),
        ("ind03_fem_3d.json", "fig_ind03_fem_3d.png", plot_ind03_fem_3d),
        ("ind04_random_vib_psd.json", "fig_ind04_random_vib_psd.png", plot_ind04_random_vib_psd),
        ("ind05_fmu_multi_instance.json", "fig_ind05_fmu_multi_instance.png", plot_ind05_fmu_multi_instance),
        ("ind06_pvt_aging_corners.json", "fig_ind06_pvt_aging_corners.png", plot_ind06_pvt_aging_corners),
    ]
    for json_name, png_name, fn in mapping:
        if (rdir / json_name).exists():
            created.append(fn(rdir, fdir / png_name))
    return created
