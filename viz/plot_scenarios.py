"""300-DPI Diagnostic Plotters for IFOG-SIM-SPEC-005 Scenarios (6-State DSP, TD-01..06, ENG-01..05)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def _load_json(path: Path) -> dict[str, Any] | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def plot_dsp6_compare(data: dict[str, Any], out_path: Path | str) -> Path:
    """Plot 2-State vs 4-State vs Official 6-State Symmetric DSP comparison (EQ-31..EQ-34)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.2), dpi=300)

    labels: list[str] = []
    biases: list[float] = []
    vfracs: list[float] = []
    cols1: list[str] = []
    cols2: list[str] = []
    if "two_state" in data:
        labels.append("2-State\n($\\alpha=\\pi/4$)")
        biases.append(max(float(data["two_state"]["ram_xtalk_bias_deg_per_h"]), 1.0e-12))
        vfracs.append(float(data["two_state"]["peak_bias_vpi_frac"]))
        cols1.append("#D97706")
        cols2.append("#4A5568")
    labels.extend(["4-State\n($\\alpha=\\pi/4$)", "6-State\n($\\alpha=\\pi/3$)"])
    biases.extend([
        max(float(data["four_state"]["ram_xtalk_bias_deg_per_h"]), 1.0e-12),
        max(float(data["six_state"]["ram_xtalk_bias_deg_per_h"]), 1.0e-12),
    ])
    vfracs.extend([
        float(data["four_state"]["peak_bias_vpi_frac"]),
        float(data["six_state"]["peak_bias_vpi_frac"]),
    ])
    cols1.extend(["#C53030", "#0E6251"])
    cols2.extend(["#1B365D", "#2B6CB0"])

    bars1 = ax1.bar(labels, biases, color=cols1, width=0.5)
    ax1.set_yscale("log")
    ax1.set_ylabel("RAM + Crosstalk Bias Error [deg/h]")
    ax1.set_title(f"RAM & Crosstalk Rejection ({data['ram_xtalk_rejection_dB']:.1f} dB gain)")
    ax1.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars1, biases):
        ax1.text(bar.get_x() + bar.get_width() / 2.0, val * 1.3, f"{val:.2e}", ha="center", fontsize=8.5)

    bars2 = ax2.bar(labels, vfracs, color=cols2, width=0.5)
    ax2.set_ylim(0, 1.25)
    ax2.set_ylabel("Peak Bias Voltage [$V_\\pi$ fraction]")
    ax2.set_title(f"MIOC Peak Bias Swing (6s vs 4s: -{data['peak_voltage_reduction_pct']:.1f}%)")
    ax2.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars2, vfracs):
        ax2.text(bar.get_x() + bar.get_width() / 2.0, val + 0.04, f"{val:.3f} $V_\\pi$", ha="center", fontsize=9)

    fig.suptitle("IFOG-VPROTO v4.1.0 — Complete 2-State / 4-State / 6-State DSP Benchmark", fontweight="bold")
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out


def plot_td_scenarios(run_dir: Path | str, fig_dir: Path | str) -> list[Path]:
    """Generate 300-DPI figures for whichever TD-01..TD-06 JSON artifacts exist in run_dir."""
    rdir = Path(run_dir)
    fdir = Path(fig_dir)
    fdir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    td01 = _load_json(rdir / "td01_blanking.json")
    if td01 is not None:
        out = fdir / "td01_blanking.png"
        fig, ax = plt.subplots(figsize=(7.5, 4.0), dpi=300)
        ks = np.arange(len(td01["rel_err_by_k_pct"]))
        ax.semilogy(ks, np.maximum(td01["rel_err_by_k_pct"], 1.0e-5), "o-", color="#1B365D", lw=1.6)
        ax.axvspan(td01["k_start_configured"], td01["k_end_configured"], color="#C6F6D5", alpha=0.45, label="ADC Blanking Window")
        ax.axhline(0.5, color="#C53030", ls="--", lw=1.1, label="0.5% Settling Threshold")
        ax.set_xlabel("Sub-sample Index $k \\in [0, K-1]$")
        ax.set_ylabel("Max TIA Settling Error [%]")
        ax.set_title(
            f"TD-01: Sub-$\\tau$ TIA Settling ($t_s={td01['tia_ts_0p1pct_ns']:.1f}$ ns, "
            f"$k^*={td01['k_start_optimal_0p5pct']}$, ARW $\\times{td01['arw_blanking_penalty_factor']:.3f}$)"
        )
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8.5)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    td02 = _load_json(rdir / "td02_step_sine.json")
    if td02 is not None:
        out = fdir / "td02_step_bode.png"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.2), dpi=300)
        ax1.plot(td02["step_trace"]["t_ms"], td02["step_trace"]["omega_out_deg_per_s"], color="#1B365D", lw=1.6)
        ax1.axhline(td02["step_target_deg_per_s"], color="#0E6251", ls="--", lw=1.1, label="Target 100 deg/s")
        ax1.set_xlabel("Time after step [ms]")
        ax1.set_ylabel("$\\Omega_{\\mathrm{out}}$ [deg/s]")
        ax1.set_title(
            f"Step Response ($t_r={td02['rise_time_10_90_ms']:.2f}$ ms, OS={td02['overshoot_pct']:.1f}%)"
        )
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8.5)

        f_hz = [p["freq_Hz"] for p in td02["bode_points"]]
        m_db = [p["mag_dB"] for p in td02["bode_points"]]
        ax2.semilogx(f_hz, m_db, "o-", color="#9B2C2C", lw=1.6, label="Measured Closed-Loop")
        ax2.axhline(-3.0, color="#4A5568", ls="--", lw=1.0, label="-3 dB Cutoff")
        ax2.axvline(td02["bw_3db_measured_Hz"], color="#0E6251", ls=":", lw=1.2, label=f"Meas {td02['bw_3db_measured_Hz']:.0f} Hz")
        ax2.set_xlabel("Input Rate Frequency [Hz]")
        ax2.set_ylabel("Closed-Loop Magnitude [dB]")
        ax2.set_title(f"TD-02 Bode ($f_{{-3\\mathrm{{dB}}}}={td02['bw_3db_measured_Hz']:.0f}$ Hz vs Theory {td02['bw_3db_theory_Hz']:.0f} Hz)")
        ax2.grid(True, which="both", alpha=0.3)
        ax2.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    td03 = _load_json(rdir / "td03_vpi_shock.json")
    if td03 is not None:
        out = fdir / "td03_vpi_shock.png"
        fig, ax = plt.subplots(figsize=(7.5, 4.0), dpi=300)
        ax.plot(td03["four_state"]["trace_t_ms"], np.array(td03["four_state"]["trace_eps_vpi_eff"]) * 100.0, label="4-State Loop-2", color="#C53030", lw=1.6)
        ax.plot(td03["six_state"]["trace_t_ms"], np.array(td03["six_state"]["trace_eps_vpi_eff"]) * 100.0, label="6-State Loop-2", color="#0E6251", lw=1.6)
        ax.axhline(0.0, color="#4A5568", ls="--", lw=0.9)
        ax.set_xlabel("Time after +5% $V_\\pi$ Thermal Shock [ms]")
        ax.set_ylabel("Residual $\\epsilon_{V_\\pi,\\mathrm{eff}}$ [%]")
        ax.set_title("TD-03: Loop-2 $V_\\pi$ Thermal Shock Convergence (4-State vs 6-State)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8.5)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    td04 = _load_json(rdir / "td04_high_rate.json")
    if td04 is not None:
        out = fdir / "td04_high_rate.png"
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.2, 5.2), dpi=300, sharex=True)
        ax1.plot(td04["trace"]["t_ms"], td04["trace"]["omega_in_deg_per_s"], "--", color="#4A5568", lw=1.3, label="$\\Omega_{\\mathrm{in}}$")
        ax1.plot(td04["trace"]["t_ms"], td04["trace"]["omega_out_deg_per_s"], color="#1B365D", lw=1.6, label="$\\Omega_{\\mathrm{out}}$")
        ax1.set_ylabel("Rate [deg/s]")
        ax1.set_title(
            f"TD-04: High-Rate 0->700 deg/s ({td04['flyback_count']:,} wraps @ {td04['flyback_rate_kHz']:.1f} kHz, err={td04['hold_700_err_pct']:.3f}%)"
        )
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8.5)

        ax2.plot(td04["trace"]["t_ms"], td04["trace"]["phi_ramp_rad"], color="#0E6251", lw=0.9)
        ax2.set_xlabel("Time [ms]")
        ax2.set_ylabel("$\\phi_{\\mathrm{ramp}}$ [rad]")
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    td05 = _load_json(rdir / "td05_shupe_shock.json")
    if td05 is not None:
        out = fdir / "td05_shupe_shock.png"
        fig, ax = plt.subplots(figsize=(7.8, 4.0), dpi=300)
        ax.plot(td05["trace"]["t_ms"], td05["trace"]["omega_out_deg_per_h"], color="#C53030", lw=1.6, label="Uncompensated Shupe Bias")
        ax.plot(td05["trace"]["t_ms"], td05["trace"]["omega_comp_deg_per_h"], color="#0E6251", lw=1.5, label="Extrapolative Thermal Filter")
        ax.set_xlabel("Time [ms]")
        ax.set_ylabel("Bias Drift [deg/h]")
        ax.set_title(f"TD-05: Real-Time Shupe Thermal Shock (Suppression = {td05['thermal_compensation_reduction_pct']:.1f}%)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8.5)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    td06 = _load_json(rdir / "td06_limit_cycles.json")
    if td06 is not None:
        out = fdir / "td06_limit_cycles.png"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0), dpi=300)
        ax1.semilogx(td06["without_dither"]["freqs_Hz"], td06["without_dither"]["psd_dB"], color="#C53030", lw=1.2, label="No Dither (Limit Cycles)")
        ax1.semilogx(td06["with_dither"]["freqs_Hz"], td06["with_dither"]["psd_dB"], color="#0E6251", lw=1.2, label="With LFSR PRBS Dither")
        ax1.set_xlabel("Frequency [Hz]")
        ax1.set_ylabel("PSD [dB((deg/s)$^2$/Hz)]")
        ax1.set_title("TD-06: Quantization Idle Tones vs PRBS Whitening")
        ax1.grid(True, which="both", alpha=0.3)
        ax1.legend(fontsize=8)

        ax2.step(np.arange(len(td06["with_dither"]["sample_dac_codes"])), td06["with_dither"]["sample_dac_codes"], where="post", color="#1B365D", lw=1.1)
        ax2.set_xlabel("Sample Index $n$")
        ax2.set_ylabel("Integer `dac_code[n]`")
        ax2.set_title(f"12-Bit Dithered DAC Register (Bias Red. {td06['bias_err_reduction_pct']:.1f}%)")
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    return generated


def plot_eng_scenarios(run_dir: Path | str, fig_dir: Path | str) -> list[Path]:
    """Generate 300-DPI figures for whichever ENG-01..ENG-05 JSON artifacts exist in run_dir."""
    rdir = Path(run_dir)
    fdir = Path(fig_dir)
    fdir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    eng01 = _load_json(rdir / "eng01_hw_sizing.json")
    if eng01 is not None:
        out = fdir / "eng01_hw_sizing.png"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.2), dpi=300)
        bits = [r["bits"] for r in eng01["enob_sweep"]]
        errs = [max(r["deadband_err_deg_per_s"], 1.0e-7) for r in eng01["enob_sweep"]]
        ax1.semilogy(bits, errs, "o-", color="#1B365D", lw=1.6)
        ax1.axhline(0.01, color="#C53030", ls="--", lw=1.1, label="Spec Limit (0.01 deg/s)")
        ax1.set_xlabel("ADC/DAC Resolution [bits]")
        ax1.set_ylabel("Deadband Rate Error [deg/s]")
        ax1.set_title(f"ENG-01A: ENOB Sweep (Min Passing = {eng01['recommended_min_bits']}-bit)")
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8)

        jits = [r["jitter_ps"] for r in eng01["jitter_sweep"]]
        arws = [r["arw_deg_per_rt_h"] for r in eng01["jitter_sweep"]]
        ax2.plot(jits, arws, "s-", color="#0E6251", lw=1.6)
        ax2.set_xlabel("ADC Aperture Jitter $\\sigma_{t_j}$ [ps]")
        ax2.set_ylabel("ARW [deg/$\\sqrt{\\mathrm{h}}$]")
        ax2.set_title("ENG-01B: Sampling Clock Aperture Jitter vs ARW")
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    eng02 = _load_json(rdir / "eng02_imu_3axis.json")
    if eng02 is not None:
        out = fdir / "eng02_imu_3axis.png"
        fig, ax = plt.subplots(figsize=(8.2, 4.3), dpi=300)
        cats = ["Isolated\n(4-State)", "Shared SLD/Rail\n(4-State)", "Shared SLD/Rail\n(6-State)"]
        vals = [
            abs(float(eng02["isolated_4state"]["y_bias_err_deg_per_h"])),
            abs(float(eng02["coupled_4state"]["y_bias_err_deg_per_h"])),
            abs(float(eng02["coupled_6state"]["y_bias_err_deg_per_h"])),
        ]
        bars = ax.bar(cats, vals, color=["#4A5568", "#C53030", "#0E6251"], width=0.48)
        ymax = max(vals) * 1.18 + 1e-6
        ax.set_ylim(0.0, ymax)
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                val + ymax * 0.02,
                f"{val:.3g} deg/h",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )
        ax.set_ylabel("Stationary Axis-Y Bias Error [deg/h]")
        ax.set_title(
            f"ENG-02: 3-Axis IMU Inter-Axis Crosstalk (Axis X=500 deg/s, Rail Droop={eng02['peak_rail_droop_V']*1e3:.1f} mV)",
            fontsize=10,
        )
        ax.grid(True, axis="y", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    eng03 = _load_json(rdir / "eng03_vre_faraday.json")
    if eng03 is not None:
        out = fdir / "eng03_vre_faraday.png"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.0), dpi=300)
        g_arr = np.array(eng03["vre"]["g_rms_levels"])
        ax1.plot(g_arr**2, eng03["vre"]["nonlinear_delta_bias_deg_per_h"], "o-", color="#C53030", lw=1.6, label="Nonlinear TIA ($G_2>0$)")
        ax1.plot(g_arr**2, eng03["vre"]["linear_delta_bias_deg_per_h"], "s--", color="#0E6251", lw=1.4, label="Linear TIA ($G_2=0$)")
        ax1.set_xlabel("Vibration Power $g_{\\mathrm{rms}}^2$ [$g^2$]")
        ax1.set_ylabel("Rectified Bias Shift $\\Delta\\Omega_{\\mathrm{VRE}}$ [deg/h]")
        ax1.set_title(f"ENG-03A: VRE ({eng03['vre']['vre_coeff_nonlinear_deg_h_per_g2']:.3f} deg/h/$g^2$)")
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8)

        bf = [r["B_gauss"] for r in eng03["faraday"]["sweep"]]
        wf = [r["bias_deg_per_h"] for r in eng03["faraday"]["sweep"]]
        ax2.plot(bf, wf, "o-", color="#1B365D", lw=1.6)
        ax2.set_xlabel("External Magnetic Field $B_{\\mathrm{ext}}$ [Gauss]")
        ax2.set_ylabel("Faraday Bias Drift [deg/h]")
        ax2.set_title(
            f"ENG-03B: Faraday ({eng03['faraday']['sensitivity_measured_deg_h_per_G']:.3f} deg/h/G, "
            f"Mu-metal {eng03['faraday']['required_mumetal_shield_dB_for_1G_0p01degh']:.1f} dB)"
        )
        ax2.grid(True, alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    eng04 = _load_json(rdir / "eng04_fault_bit.json")
    if eng04 is not None:
        out = fdir / "eng04_fault_bit.png"
        fig, ax = plt.subplots(figsize=(8.0, 4.0), dpi=300)
        names = [c["fault_type"] for c in eng04["cases"]]
        ttas = [c["time_to_alert_us"] for c in eng04["cases"]]
        colors = ["#0E6251" if c["pass"] else "#C53030" for c in eng04["cases"]]
        ax.barh(names, ttas, color=colors)
        ax.set_xlabel("BIT Time-to-Alert [$\\mu$s]")
        ax.set_title("ENG-04: Real-Time FPGA BIT/FDIR Detection Latency Across 5 Fault Modes")
        ax.grid(True, axis="x", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    eng05 = _load_json(rdir / "eng05_mc_yield_cal.json")
    if eng05 is not None:
        out = fdir / "eng05_mc_yield_cal.png"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.8, 4.2), dpi=300)
        mc = eng05["monte_carlo"]
        ax1.hist(mc["bias_samples_deg_per_h"], bins=15, color="#1B365D", alpha=0.8, edgecolor="white")
        ax1.axvline(-1.0, color="#C53030", ls="--", lw=1.2)
        ax1.axvline(1.0, color="#C53030", ls="--", lw=1.2, label="Spec Limits $\\pm 1$ deg/h")
        ax1.set_xlabel("Unit Bias Error [deg/h]")
        ax1.set_ylabel("Unit Count")
        ax1.set_title(f"ENG-05A: MC Yield = {mc['yield_pct']:.1f}% ($N={mc['n_runs']}$, $C_{{pk}}={mc['cpk_bias_1degh']:.2f}$)")
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=8)

        cal = eng05["virtual_calibration"]
        rows = cal["rows"]
        idx = np.arange(len(rows))
        raw = [r["omega_out_deg_per_h"] for r in rows]
        res_poly = np.array(raw) - np.array(cal["poly_pred_deg_per_h"])
        ax2.plot(idx, raw, "o-", color="#C53030", lw=1.3, label="Raw Thermal Bias")
        ax2.plot(idx, res_poly, "s-", color="#0E6251", lw=1.3, label=f"Poly Residual (-{cal['poly_reduction_pct']:.1f}%)")
        ax2.set_xlabel("Calibration Point Index ($-40..+85^\\circ$C $\\times$ 3 ramps)")
        ax2.set_ylabel("Bias [deg/h]")
        ax2.set_title("ENG-05B: Virtual Thermal Calibration Dataset & Poly Fit")
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    return generated


def plot_dyn_scenarios(run_dir: Path | str, fig_dir: Path | str) -> list[Path]:
    """Generate 300-DPI plots for Group C Dynamic Response, Output PSD & Electro-Optic Probe (DYN-01..DYN-04)."""
    rdir = Path(run_dir)
    fdir = Path(fig_dir)
    fdir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    d1 = _load_json(rdir / "dyn01_step_response.json")
    if d1 is not None:
        out = fdir / "dyn01_step_response.png"
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(11.5, 7.6), dpi=300)
        c10_4 = d1["cases"]["step10_4state"]
        c10_6 = d1["cases"]["step10_6state"]
        c100_4 = d1["cases"]["step100_4state"]
        c100_6 = d1["cases"]["step100_6state"]
        ck15 = d1["cases"]["step10_6state_k015"]
        ck45 = d1["cases"]["step10_6state_k045"]

        # Panel A: Normalized Step Response (0->10 & 0->100 deg/s, 4-State vs 6-State)
        ax1.plot(c100_6["trace"]["t_ms"], np.array(c100_6["trace"]["omega_in_deg_per_s"]) / 100.0, "k--", lw=1.1, label="Command $\\Omega_{\\mathrm{in}}$")
        ax1.plot(c10_4["trace"]["t_ms"], np.array(c10_4["trace"]["omega_out_deg_per_s"]) / 10.0, color="#1B365D", lw=1.5, label=f"10 deg/s 4s ($t_r={c10_4['rise_time_10_90_ms']:.2f}$ ms)")
        ax1.plot(c10_6["trace"]["t_ms"], np.array(c10_6["trace"]["omega_out_deg_per_s"]) / 10.0, color="#0E6251", lw=1.5, label=f"10 deg/s 6s ($t_r={c10_6['rise_time_10_90_ms']:.2f}$ ms)")
        if "step10_2state" in d1["cases"]:
            c10_2 = d1["cases"]["step10_2state"]
            ax1.plot(c10_2["trace"]["t_ms"], np.array(c10_2["trace"]["omega_out_deg_per_s"]) / 10.0, "-", color="#D97706", lw=1.6, label=f"10 deg/s 2s ($t_r={c10_2['rise_time_10_90_ms']:.3f}$ ms)")
        ax1.plot(c100_4["trace"]["t_ms"], np.array(c100_4["trace"]["omega_out_deg_per_s"]) / 100.0, ":", color="#2B6CB0", lw=1.6, label=f"100 deg/s 4s ($t_r={c100_4['rise_time_10_90_ms']:.2f}$ ms)")
        ax1.plot(c100_6["trace"]["t_ms"], np.array(c100_6["trace"]["omega_out_deg_per_s"]) / 100.0, "-.", color="#C53030", lw=1.5, label=f"100 deg/s 6s ($t_r={c100_6['rise_time_10_90_ms']:.2f}$ ms)")
        ax1.set_xlim(-0.2, 1.5)
        ax1.set_xlabel("Time Relative to Step [ms]")
        ax1.set_ylabel("Normalized Rate $\\Omega_{\\mathrm{out}} / \\Omega_{\\mathrm{step}}$")
        ax1.set_title("DYN-01A: Closed-Loop Step Response (2-State / 4-State / 6-State)")
        ax1.grid(True, alpha=0.3)
        ax1.legend(fontsize=7.5, loc="lower right")

        # Panel B: Loop-1 Gain Trade-off (K_tot_1 = 0.15, 0.25, 0.45 in 6-State)
        ax2.plot(c10_6["trace"]["t_ms"], c10_6["trace"]["omega_in_deg_per_s"], "k--", lw=1.1, label="Step 10 deg/s")
        ax2.plot(ck15["trace"]["t_ms"], ck15["trace"]["omega_out_deg_per_s"], color="#B7791F", lw=1.5, label=f"$K_{{\\mathrm{{tot}},1}}=0.15$ ($t_r={ck15['rise_time_10_90_ms']:.2f}$ ms)")
        ax2.plot(c10_6["trace"]["t_ms"], c10_6["trace"]["omega_out_deg_per_s"], color="#0E6251", lw=1.6, label=f"$K_{{\\mathrm{{tot}},1}}=0.25$ ($t_r={c10_6['rise_time_10_90_ms']:.2f}$ ms)")
        ax2.plot(ck45["trace"]["t_ms"], ck45["trace"]["omega_out_deg_per_s"], color="#1B365D", lw=1.5, label=f"$K_{{\\mathrm{{tot}},1}}=0.45$ ($t_r={ck45['rise_time_10_90_ms']:.2f}$ ms)")
        ax2.set_xlim(-0.2, 1.8)
        ax2.set_xlabel("Time Relative to Step [ms]")
        ax2.set_ylabel("Output Rate $\\Omega_{\\mathrm{out}}$ [deg/s]")
        ax2.set_title("DYN-01B: Official 6-State Loop-1 Gain Sweep ($K_{\\mathrm{tot},1}$)")
        ax2.grid(True, alpha=0.3)
        ax2.legend(fontsize=8, loc="lower right")

        # Panel C: Sagnac Phase vs Closed-Loop Feedback Step (100 deg/s 6-State)
        t_c = c100_6["trace"]["t_ms"]
        ax3.plot(t_c, c100_6["trace"]["phi_sagnac_rad"], "k--", lw=1.2, label="Sagnac Phase $\\Delta\\phi_S(t)$ [rad]")
        ax3.plot(t_c, c100_6["trace"]["delta_phi_step_rad"], color="#0E6251", lw=1.6, label="Feedback Phase $\\Delta\\phi_{\\mathrm{step}}(t)$ [rad]")
        ax3.set_xlim(-0.2, 1.5)
        ax3.set_xlabel("Time Relative to Step [ms]")
        ax3.set_ylabel("Optical Phase [rad]")
        ax3.set_title("DYN-01C: Sagnac vs Closed-Loop Feedback Phase (0->100 deg/s)")
        ax3.grid(True, alpha=0.3)
        ax3.legend(fontsize=8, loc="lower right")

        # Panel D: Tracking Error Convergence (Log Magnitude)
        for lbl, c_obj, col in (
            ("10 deg/s (6-State)", c10_6, "#0E6251"),
            ("100 deg/s (4-State)", c100_4, "#1B365D"),
            ("100 deg/s (6-State)", c100_6, "#C53030"),
        ):
            tt = np.array(c_obj["trace"]["t_ms"])
            ee = np.maximum(np.abs(c_obj["trace"]["tracking_err_deg_per_s"]), 1.0e-6)
            m = tt >= 0.0
            ax4.semilogy(tt[m], ee[m], color=col, lw=1.4, label=lbl)
        ax4.set_xlim(0.0, 2.0)
        ax4.set_xlabel("Time After Step [ms]")
        ax4.set_ylabel("$|\\Omega_{\\mathrm{out}} - \\Omega_{\\mathrm{in}}|$ [deg/s]")
        ax4.set_title("DYN-01D: Closed-Loop Step Tracking Error Convergence")
        ax4.grid(True, which="both", alpha=0.3)
        ax4.legend(fontsize=8)

        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    d2 = _load_json(rdir / "dyn02_freq_response.json")
    if d2 is not None:
        out = fdir / "dyn02_freq_response.png"
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9.6, 8.6), sharex=True, dpi=300)
        m4, m6 = d2["four_state"], d2["six_state"]
        f4, f6 = m4["freqs_Hz"], m6["freqs_Hz"]

        if "two_state" in d2:
            m2 = d2["two_state"]
            f2 = m2["freqs_Hz"]
            ax1.semilogx(f2, m2["mag_dB"], "^-", color="#D97706", lw=1.6, ms=4.5, label=f"2-State Meas (BW={m2['bw_3db_measured_Hz']:.0f} Hz)")
            ax2.semilogx(f2, m2["phase_deg"], "^-", color="#D97706", lw=1.6, ms=4.5, label="2-State Meas Phase")
            ax3.semilogx(f2, m2["group_delay_us"], "^-", color="#D97706", lw=1.5, ms=4.2, label=f"2-State ($\\tau_{{g,0}}={m2['low_freq_group_delay_us']:.1f}\\;\\mu$s)")
        ax1.semilogx(f4, m4["mag_dB"], "o-", color="#1B365D", lw=1.6, ms=4.5, label=f"4-State Meas (BW={m4['bw_3db_measured_Hz']:.0f} Hz)")
        ax1.semilogx(f4, m4["theory_mag_dB"], "--", color="#1B365D", alpha=0.65, lw=1.2, label="4-State Analytical Z-Domain")
        ax1.semilogx(f6, m6["mag_dB"], "s-", color="#0E6251", lw=1.6, ms=4.5, label=f"6-State Meas (BW={m6['bw_3db_measured_Hz']:.0f} Hz)")
        ax1.semilogx(f6, m6["theory_mag_dB"], "--", color="#0E6251", alpha=0.65, lw=1.2, label="6-State Analytical Z-Domain")
        ax1.axhline(-3.0, color="#C53030", ls=":", lw=1.2, label="-3 dB Bandwidth")
        ax1.set_ylabel("Magnitude $|H(f)|$ [dB]")
        ax1.set_title(f"DYN-02: Closed-Loop Bode Frequency Response (2/4/6-State DSP, 4s/6s BW Ratio = {d2['bw_ratio_4state_to_6state']:.2f}x)")
        ax1.grid(True, which="both", alpha=0.3)
        ax1.legend(fontsize=8, ncol=2, loc="lower left")

        ax2.semilogx(f4, m4["phase_deg"], "o-", color="#1B365D", lw=1.6, ms=4.5, label="4-State Meas Phase")
        ax2.semilogx(f4, m4["theory_phase_deg"], "--", color="#1B365D", alpha=0.65, lw=1.2, label="4-State Analytical")
        ax2.semilogx(f6, m6["phase_deg"], "s-", color="#0E6251", lw=1.6, ms=4.5, label="6-State Meas Phase")
        ax2.semilogx(f6, m6["theory_phase_deg"], "--", color="#0E6251", alpha=0.65, lw=1.2, label="6-State Analytical")
        ax2.axhline(-45.0, color="#718096", ls=":", lw=1.0, label="-45 deg Reference")
        ax2.set_ylabel("Unwrapped Phase $\\angle H(f)$ [deg]")
        ax2.grid(True, which="both", alpha=0.3)
        ax2.legend(fontsize=8, ncol=2, loc="lower left")

        ax3.semilogx(f4, m4["group_delay_us"], "o-", color="#1B365D", lw=1.5, ms=4.2, label=f"4-State ($\\tau_{{g,0}}={m4['low_freq_group_delay_us']:.1f}\\;\\mu$s)")
        ax3.semilogx(f4, m4["theory_group_delay_us"], "--", color="#1B365D", alpha=0.65, lw=1.1, label="4-State Theory")
        ax3.semilogx(f6, m6["group_delay_us"], "s-", color="#0E6251", lw=1.5, ms=4.2, label=f"6-State ($\\tau_{{g,0}}={m6['low_freq_group_delay_us']:.1f}\\;\\mu$s)")
        ax3.semilogx(f6, m6["theory_group_delay_us"], "--", color="#0E6251", alpha=0.65, lw=1.1, label="6-State Theory")
        ax3.set_xlabel("Input Rate Frequency $f$ [Hz]")
        ax3.set_ylabel("Group Delay $\\tau_g(f)$ [$\\mu$s]")
        ax3.grid(True, which="both", alpha=0.3)
        ax3.legend(fontsize=8, ncol=2, loc="upper right")

        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    d3 = _load_json(rdir / "dyn03_output_psd.json")
    if d3 is not None:
        out = fdir / "dyn03_output_psd.png"
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4), dpi=300)
        reg = d3["regimes"]
        wl, f4, f6 = reg["white_linear"], reg["full_4state"], reg["full_6state"]
        arw_ref = d3["analytical_white_ref"]

        if "full_2state" in reg:
            f2 = reg["full_2state"]
            ax1.loglog(f2["freqs_Hz"], f2["psd_deg2_h2_per_Hz"], color="#D97706", lw=1.4, label="Full Impairments (2-State)")
            ax2.loglog(f2["freqs_Hz"], f2["asd_deg_h_per_rtHz"], color="#D97706", lw=1.3, label="ASD 2-State [deg/h/$\\sqrt{\\mathrm{Hz}}$]")
        ax1.loglog(f4["freqs_Hz"], f4["psd_deg2_h2_per_Hz"], color="#C53030", lw=1.5, label="Full Impairments (4-State)")
        ax1.loglog(f6["freqs_Hz"], f6["psd_deg2_h2_per_Hz"], color="#0E6251", lw=1.5, label=f"Full Impairments (6-State, -{d3['low_freq_6state_suppression_dB']:.1f} dB LF)")
        ax1.loglog(wl["freqs_Hz"], wl["psd_deg2_h2_per_Hz"], color="#1B365D", lw=1.3, alpha=0.85, label="White-Noise Linear Floor")
        ax1.axhline(
            arw_ref["psd_white_deg2_h2_per_Hz"],
            color="#2D3748",
            ls="--",
            lw=1.2,
            label=f"Analytical EQ-15 ARW ({arw_ref['arw_analytical_deg_per_rt_h']:.5f} deg/$\\sqrt{{\\mathrm{{h}}}}$)",
        )
        ax1.set_xlabel("Frequency $f$ [Hz]")
        ax1.set_ylabel("Output Rate PSD $S_\\Omega(f)$ [(deg/h)$^2$/Hz]")
        ax1.set_title("DYN-03A: Broadband Output Angular-Rate PSD (2/4/6-State)")
        ax1.grid(True, which="both", alpha=0.3)
        ax1.legend(fontsize=7.5, loc="lower left")

        ax2.loglog(f4["freqs_Hz"], f4["asd_deg_h_per_rtHz"], color="#C53030", lw=1.4, label="ASD 4-State [deg/h/$\\sqrt{\\mathrm{Hz}}$]")
        ax2.loglog(f6["freqs_Hz"], f6["asd_deg_h_per_rtHz"], color="#0E6251", lw=1.4, label="ASD 6-State [deg/h/$\\sqrt{\\mathrm{Hz}}$]")
        ax2.set_ylim(min(f6["asd_deg_h_per_rtHz"]) * 0.4, max(f4["asd_deg_h_per_rtHz"]) * 4.5)
        ax2_r = ax2.twinx()
        ax2_r.semilogx(f4["freqs_Hz"], f4["cum_rms_deg_per_h"], "--", color="#9B2C2C", lw=1.3, label="Cum. RMS 4-State [deg/h]")
        ax2_r.semilogx(f6["freqs_Hz"], f6["cum_rms_deg_per_h"], "--", color="#2B6CB0", lw=1.3, label="Cum. RMS 6-State [deg/h]")
        ax2_r.set_ylim(-50.0, max(f4["cum_rms_deg_per_h"]) * 1.25)
        ax2.set_xlabel("Frequency $f$ [Hz]")
        ax2.set_ylabel("Output Rate ASD [deg/h/$\\sqrt{\\mathrm{Hz}}$]")
        ax2_r.set_ylabel("Cumulative Integrated RMS Noise [deg/h]")
        ax2.set_title("DYN-03B: Amplitude Spectral Density & Cumulative RMS Noise")
        ax2.grid(True, which="both", alpha=0.3)
        h1, l1 = ax2.get_legend_handles_labels()
        h2, l2 = ax2_r.get_legend_handles_labels()
        ax2.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper left")

        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    d4 = _load_json(rdir / "dyn04_sine_electro_optic.json")
    if d4 is not None:
        out = fdir / "dyn04_sine_electro_optic.png"
        fig, axes = plt.subplots(3, 2, figsize=(12.2, 9.6), dpi=300)
        mac = d4["macro_trace"]
        zm = d4["micro_zoom"]
        t_ms = mac["t_ms"]

        # Panel 1: Sinusoidal Input vs Output Angular Rate
        ax = axes[0, 0]
        ax.plot(t_ms, mac["omega_in_deg_per_s"], "k--", lw=1.2, label="Input $\\Omega_{\\mathrm{in}}(t)$")
        ax.plot(t_ms, mac["omega_out_deg_per_s"], color="#0E6251", lw=1.5, label="Output $\\Omega_{\\mathrm{out}}(t)$")
        ax.set_xlabel("Time [ms]")
        ax.set_ylabel("Angular Rate [deg/s]")
        ax.set_title(f"DYN-04A: Sine Rate ({d4['sine_amp_deg_per_s']:.0f} deg/s @ {d4['sine_freq_Hz']:.0f} Hz, THD={d4['output_thd_dB']:.1f} dB, SFDR={d4['output_sfdr_dB']:.1f} dB)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        # Panel 2: Sagnac Phase vs Closed-Loop Feedback Phase & Residual Error
        ax = axes[0, 1]
        ax.plot(t_ms, mac["phi_sagnac_rad"], "k--", lw=1.2, label="Sagnac $\\Delta\\phi_S(t)$ [rad]")
        ax.plot(t_ms, mac["phi_feedback_rad"], color="#1B365D", lw=1.4, label="Feedback $\\Delta\\phi_{\\mathrm{fb}}(t)$ [rad]")
        ax.set_ylim(-1.45, 1.85)
        ax_r = ax.twinx()
        ax_r.plot(t_ms, mac["phi_err_mrad"], color="#C53030", lw=1.1, alpha=0.85, label="Residual $\\Delta\\phi_{\\mathrm{err}}(t)$ [mrad]")
        ax_r.set_ylim(-280.0, 360.0)
        ax.set_xlabel("Time [ms]")
        ax.set_ylabel("Sagnac & Feedback Phase [rad]")
        ax_r.set_ylabel("Residual Phase Error [mrad]", color="#C53030")
        ax.set_title(f"DYN-04B: Sagnac Phase ($\\pm${d4['peak_phi_sagnac_rad']:.3f} rad) & Residual Error")
        ax.grid(True, alpha=0.3)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax_r.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7.5, ncol=2, loc="upper center")

        # Panel 3: MIOC Feedback Voltage V_fb_MIOC(t) & Total V_MIOC(t) (1 full cycle 0..4 ms showing zero-crossing reversal)
        ax = axes[1, 0]
        ax.plot(t_ms, mac["v_mioc_total_V"], color="#CBD5E0", lw=0.8, label="Total $V_{\\mathrm{MIOC}}(t)$ (Bias+FB)")
        ax.plot(t_ms, mac["v_fb_mioc_V"], color="#1B365D", lw=1.1, label="Serrodyne $V_{\\mathrm{fb,MIOC}}(t)$")
        ax.set_xlim(0.0, 4.0)
        ax.set_ylim(-5.6, 6.2)
        ax.set_xlabel("Time [ms] (1 Full Reversal Cycle)")
        ax.set_ylabel("MIOC Voltage [V]")
        ax.set_title(f"DYN-04C: MIOC Serrodyne Feedback $V_{{\\mathrm{{fb,MIOC}}}}(t)$ ({d4['flyback_count']} 2$\\pi$ Resets)")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8, ncol=2, loc="upper center")

        # Panel 4: Macro Photodiode Optical Power P_PD(t) & Frame-Demodulated PD Signal
        ax = axes[1, 1]
        ax.plot(t_ms, mac["p_pd_uW"], color="#2B6CB0", lw=0.8, alpha=0.65, label="$P_{\\mathrm{PD}}(t)$ [$\\mu$W]")
        ax.set_ylim(min(mac["p_pd_uW"]) * 0.85, max(mac["p_pd_uW"]) * 1.25)
        ax_r = ax.twinx()
        ax_r.plot(mac["frame_t_ms"], mac["p_pd_demod_uW"], color="#C53030", lw=1.5, label="Demodulated $\\Delta P_{\\mathrm{PD}}(t)$ [$\\mu$W]")
        p_dem_abs = max(abs(min(mac["p_pd_demod_uW"])), abs(max(mac["p_pd_demod_uW"])))
        ax_r.set_ylim(-p_dem_abs * 1.35, p_dem_abs * 1.65)
        ax.set_xlabel("Time [ms]")
        ax.set_ylabel("PD Optical Power $P_{\\mathrm{PD}}$ [$\\mu$W]")
        ax_r.set_ylabel("Demodulated $\\Delta P_{\\mathrm{PD}}$ [$\\mu$W]", color="#C53030")
        ax.set_title(f"DYN-04D: Photodiode Output ($r(\\Delta P_{{\\mathrm{{PD}}}}, \\Delta\\phi_{{\\mathrm{{err}}}}) = {d4['pd_demod_to_phi_err_corr']:.4f}$)")
        ax.grid(True, alpha=0.3)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax_r.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7.5, ncol=2, loc="upper center")

        # Panel 5: Sub-tau Micro Zoom — Total V_MIOC(t) & Pure Serrodyne V_fb_MIOC(t)
        ax = axes[2, 0]
        ax.plot(zm["t_us"], zm["v_mioc_total_V"], color="#1B365D", lw=1.3, label="Total $V_{\\mathrm{MIOC}}(t)$ [V]")
        ax.plot(zm["t_us"], zm["v_fb_mioc_V"], "--", color="#C53030", lw=1.3, label="Pure $V_{\\mathrm{fb,MIOC}}(t)$ [V]")
        ax.set_xlabel(f"Sub-$\\tau$ Zoom Time Offset from {zm['t_origin_ms']:.2f} ms [$\\mu$s]")
        ax.set_ylabel("MIOC Drive Voltage [V]")
        ax.set_title("DYN-04E: Sub-$\\tau$ Zoom — 6-State Bias + Serrodyne Ramp at Peak Rate")
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        # Panel 6: Sub-tau Micro Zoom — Photodiode Power P_PD(t), TIA V_TIA(t) & ADC Blanking
        ax = axes[2, 1]
        ax.plot(zm["t_us"], zm["p_pd_uW"], color="#0E6251", lw=1.4, label="$P_{\\mathrm{PD}}(t)$ [$\\mu$W]")
        ax_r = ax.twinx()
        ax_r.plot(zm["t_us"], zm["v_tia_V"], "--", color="#B7791F", lw=1.2, label="$V_{\\mathrm{TIA}}(t)$ [V]")
        blank = np.array(zm["in_blanking"]) > 0
        ax.fill_between(zm["t_us"], 0, max(zm["p_pd_uW"]) * 1.05, where=blank, color="#A0AEC0", alpha=0.18, label="ADC Blanking Window")
        ax.set_xlabel(f"Sub-$\\tau$ Zoom Time Offset from {zm['t_origin_ms']:.2f} ms [$\\mu$s]")
        ax.set_ylabel("PD Optical Power [$\\mu$W]", color="#0E6251")
        ax_r.set_ylabel("TIA Output Voltage [V]", color="#B7791F")
        ax.set_title("DYN-04F: Sub-$\\tau$ Zoom — PD Power, TIA Output & ADC Blanking")
        ax.grid(True, alpha=0.3)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax_r.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=7.5, loc="upper right")

        fig.tight_layout()
        fig.savefig(out, dpi=300)
        plt.close(fig)
        generated.append(out)

    return generated


def plot_fmi_gate(fmi_data: dict[str, Any], run_dir: Path | str, out_path: Path | str) -> Path:
    """Generate 300-DPI 3-panel FMI 3.0 FMU Verification Gate figure (IFOG-SIM-SPEC-006 Gate 6)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rdir = Path(run_dir)

    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(14.5, 4.4), dpi=300)

    # Panel 1: Black-Box FMU vs Standalone Tier 2 Trajectory Equivalence (< 1e-12 rad/s)
    eq4 = fmi_data["equivalence"]["modes"]["4state"]
    eq6 = fmi_data["equivalence"]["modes"]["6state"]
    t_ms = np.asarray(eq4["time_s"], dtype=np.float64) * 1.0e3
    ax1.plot(t_ms, eq4["standalone_omega_out_rad_per_s"], color="#1B365D", lw=2.2, label="Standalone 4s")
    ax1.plot(t_ms, eq4["fmu_omega_out_rad_per_s"], "o", ms=3.5, color="#DD6B20", label="FMU 4s")
    ax1.plot(t_ms, eq6["standalone_omega_out_rad_per_s"], color="#0E6251", lw=1.6, ls="--", label="Standalone 6s")
    ax1.plot(t_ms, eq6["fmu_omega_out_rad_per_s"], "^", ms=3.2, color="#38A169", label="FMU 6s")
    ax1.set_xlabel("Time [ms]")
    ax1.set_ylabel("$\\Omega_{\\mathrm{out}}$ [rad/s]")
    ax1.set_title(
        f"Gate 6B: FMU vs Standalone\n(Max Err = {fmi_data['equivalence']['max_final_omega_err_rad_per_s']:.2e} rad/s)"
    )
    ax1.grid(True, alpha=0.3)
    ax1.legend(fontsize=7.5, loc="lower right")

    # Panel 2: FMU Slow Rate Ramp Deadband (enable_dither=False vs True)
    db = fmi_data["deadband"]
    r_in = np.asarray(db["rates_in_deg_per_s"], dtype=np.float64)
    err_off = (np.asarray(db["dither_off_out_deg_per_s"], dtype=np.float64) - r_in) * 3600.0
    err_on = (np.asarray(db["dither_on_out_deg_per_s"], dtype=np.float64) - r_in) * 3600.0
    ax2.plot(r_in, err_off, "o-", color="#C53030", lw=1.5, ms=3.5, label="enable_dither=False")
    ax2.plot(r_in, err_on, "s-", color="#0E6251", lw=1.6, ms=3.5, label="enable_dither=True")
    ax2.axhline(0.0, color="#4A5568", ls=":", lw=0.9)
    ax2.set_xlabel("Input Rate $\\Omega_{\\mathrm{in}}$ [deg/s]")
    ax2.set_ylabel("Calibrated Rate Error [deg/h]")
    ax2.set_title(f"Gate 6C: FMU Deadband Sweep\n(Reduction = {db['deadband_reduction_pct']:.1f}%)")
    ax2.grid(True, alpha=0.3)
    ax2.legend(fontsize=8)

    # Panel 3: FMU -> Tier 3 Dual-Regime 5-Region IEEE 952 Overlapping AVAR
    avar_npz = rdir / "fmi_avar" / "avar_curve.npz"
    av = fmi_data["avar"]
    if avar_npz.exists():
        npz = np.load(avar_npz)
        ax3.loglog(npz["taus_fast"], npz["adev_fast_deg_h"], "o-", color="#1B365D", ms=2.8, lw=1.3, label="FMU Fast-Scale")
        ax3.loglog(npz["taus_slow"], npz["adev_slow_deg_h"], "s-", color="#0E6251", ms=2.5, lw=1.4, label="Tier-3 10h Slow")
        ax3.axvspan(0.1, 5.0, color="#FEFCBF", alpha=0.45, label="Overlap [0.1, 5] s")
        ax3.legend(fontsize=7.5)
    ax3.set_xlabel("Averaging Time $T$ [s]")
    ax3.set_ylabel("Overlapping ADEV [deg/h]")
    ax3.set_title(
        f"Gate 6D: FMU Dual-Regime AVAR\n(Overlap = {av['overlap_check']['max_relative_mismatch_pct']:.2f}% < 5%)"
    )
    ax3.grid(True, which="both", alpha=0.3)

    fig.suptitle(
        f"IFOG-SIM-SPEC-006 — Gate 6: FMI 3.0 Black-Box FMU Verification ({'PASS' if fmi_data['fmi_gate_pass'] else 'FAIL'})",
        fontweight="bold",
    )
    fig.tight_layout()
    fig.savefig(out, dpi=300)
    plt.close(fig)
    return out


