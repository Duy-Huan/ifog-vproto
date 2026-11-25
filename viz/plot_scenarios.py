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
    """Plot 4-State vs Official 6-State Symmetric DSP comparison (EQ-31..EQ-34)."""
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 4.2), dpi=300)

    labels = ["4-State\n($\\alpha=\\pi/4$)", "6-State\n($\\alpha=\\pi/3$)"]
    b4 = max(float(data["four_state"]["ram_xtalk_bias_deg_per_h"]), 1.0e-12)
    b6 = max(float(data["six_state"]["ram_xtalk_bias_deg_per_h"]), 1.0e-12)
    bars1 = ax1.bar(labels, [b4, b6], color=["#C53030", "#0E6251"], width=0.5)
    ax1.set_yscale("log")
    ax1.set_ylabel("RAM + Crosstalk Bias Error [deg/h]")
    ax1.set_title(f"RAM & Crosstalk Rejection ({data['ram_xtalk_rejection_dB']:.1f} dB gain)")
    ax1.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars1, (b4, b6)):
        ax1.text(bar.get_x() + bar.get_width() / 2.0, val * 1.3, f"{val:.2e}", ha="center", fontsize=8.5)

    v4 = float(data["four_state"]["peak_bias_vpi_frac"])
    v6 = float(data["six_state"]["peak_bias_vpi_frac"])
    bars2 = ax2.bar(labels, [v4, v6], color=["#1B365D", "#2B6CB0"], width=0.5)
    ax2.set_ylim(0, 1.25)
    ax2.set_ylabel("Peak Bias Voltage [$V_\\pi$ fraction]")
    ax2.set_title(f"MIOC Peak Bias Swing (-{data['peak_voltage_reduction_pct']:.1f}%)")
    ax2.grid(True, axis="y", alpha=0.3)
    for bar, val in zip(bars2, (v4, v6)):
        ax2.text(bar.get_x() + bar.get_width() / 2.0, val + 0.04, f"{val:.3f} $V_\\pi$", ha="center", fontsize=9)

    fig.suptitle("IFOG-SIM-SPEC-005 — Official 6-State vs 4-State DSP Benchmark", fontweight="bold")
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
