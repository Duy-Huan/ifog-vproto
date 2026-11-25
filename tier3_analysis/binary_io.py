"""Fast binary I/O readers for Tier 2 sim_out.bin (32B) and micro_waveforms.bin (64B)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

OMEGA_OUT_LSB: float = 1.0e-12  # rad/s per raw int64 LSB in SimRecord

SIM_RECORD_DTYPE = np.dtype(
    [
        ("t", "<f8"),
        ("omega_in", "<f8"),
        ("omega_out_raw", "<i8"),
        ("vpi_err_raw", "<i4"),
        ("flags", "<u4"),
    ],
    align=False,
)

MICRO_RECORD_DTYPE = np.dtype(
    [
        ("t", "<f8"),
        ("v_drv", "<f8"),
        ("p_det", "<f8"),
        ("v_tia", "<f8"),
        ("v_adc", "<f8"),
        ("phi_ramp", "<f8"),
        ("adc_code", "<i4"),
        ("k_idx", "<u4"),
        ("in_blanking", "<u4"),
        ("dac_code", "<i4"),
    ],
    align=False,
)

DSP_TRACE_DTYPE = np.dtype(
    [
        ("t", "<f8"),
        ("phi_ramp", "<f8"),
        ("delta_phi_step", "<f8"),
        ("g_dac", "<f8"),
        ("e_omega", "<f8"),
        ("e_asym", "<f8"),
        ("adc_code", "<i4"),
        ("dac_code", "<i4"),
        ("e_vpi", "<i4"),
        ("prbs_bit", "<i2"),
        ("bit_fault_code", "<u2"),
    ],
    align=False,
)


def read_sim_records(bin_path: Path | str) -> dict[str, np.ndarray]:
    """Read 32-byte packed SimRecord binary stream into a dictionary of NumPy arrays."""
    path = Path(bin_path)
    raw = np.fromfile(path, dtype=SIM_RECORD_DTYPE)
    return {
        "t": raw["t"].astype(np.float64, copy=False),
        "omega_in": raw["omega_in"].astype(np.float64, copy=False),
        "omega_out_raw": raw["omega_out_raw"],
        "omega_out": raw["omega_out_raw"].astype(np.float64) * OMEGA_OUT_LSB,
        "vpi_err_raw": raw["vpi_err_raw"],
        "flags": raw["flags"],
    }


def read_micro_records(bin_path: Path | str) -> dict[str, np.ndarray]:
    """Read 64-byte packed MicroRecord binary stream for waveform diagnostics."""
    path = Path(bin_path)
    raw = np.fromfile(path, dtype=MICRO_RECORD_DTYPE)
    return {
        "t": raw["t"].astype(np.float64, copy=False),
        "v_drv": raw["v_drv"].astype(np.float64, copy=False),
        "p_det": raw["p_det"].astype(np.float64, copy=False),
        "v_tia": raw["v_tia"].astype(np.float64, copy=False),
        "v_adc": raw["v_adc"].astype(np.float64, copy=False),
        "phi_ramp": raw["phi_ramp"].astype(np.float64, copy=False),
        "adc_code": raw["adc_code"],
        "k_idx": raw["k_idx"],
        "in_blanking": raw["in_blanking"],
        "dac_code": raw["dac_code"],
    }


def read_dsp_trace(bin_path: Path | str) -> dict[str, np.ndarray]:
    """Read 64-byte packed DspTraceRecord internal DSP register stream (IFOG-SIM-SPEC-005)."""
    path = Path(bin_path)
    raw = np.fromfile(path, dtype=DSP_TRACE_DTYPE)
    return {
        "t": raw["t"].astype(np.float64, copy=False),
        "phi_ramp": raw["phi_ramp"].astype(np.float64, copy=False),
        "delta_phi_step": raw["delta_phi_step"].astype(np.float64, copy=False),
        "g_dac": raw["g_dac"].astype(np.float64, copy=False),
        "e_omega": raw["e_omega"].astype(np.float64, copy=False),
        "e_asym": raw["e_asym"].astype(np.float64, copy=False),
        "adc_code": raw["adc_code"],
        "dac_code": raw["dac_code"],
        "e_vpi": raw["e_vpi"],
        "prbs_bit": raw["prbs_bit"],
        "bit_fault_code": raw["bit_fault_code"],
    }


def compute_welch_psd(
    signal: np.ndarray, fs_Hz: float, nperseg: int | None = None
) -> tuple[np.ndarray, np.ndarray]:
    """Compute one-sided Welch PSD (units^2 / Hz) for Gate 3 1/f diagnostics."""
    from scipy.signal import welch

    n = len(signal)
    seg = min(n, nperseg if nperseg is not None else max(256, n // 8))
    freqs, psd = welch(signal, fs=fs_Hz, window="hann", nperseg=seg, detrend="constant")
    return freqs, psd


def fit_loglog_slope(x: np.ndarray, y: np.ndarray, x_min: float, x_max: float) -> float:
    """Fit linear slope in log10(y) vs log10(x) over [x_min, x_max]."""
    mask = (x >= x_min) & (x <= x_max) & (y > 0.0)
    if np.count_nonzero(mask) < 2:
        raise ValueError("Insufficient positive samples inside fit window")
    lx = np.log10(x[mask])
    ly = np.log10(y[mask])
    slope, _ = np.polyfit(lx, ly, 1)
    return float(slope)


def extract_coherent_tone_amplitude(
    t_s: np.ndarray, signal: np.ndarray, freq_Hz: float
) -> float:
    """Extract coherent single-frequency sinusoidal amplitude at freq_Hz via quadrature DFT."""
    n = len(signal)
    if n < 4:
        raise ValueError("At least 4 samples required for coherent tone extraction")
    sig_ac = signal - np.mean(signal)
    window = np.hanning(n)
    w_sum = np.sum(window)
    phase = 2.0 * np.pi * freq_Hz * t_s
    c_comp = np.sum(window * sig_ac * np.cos(phase))
    s_comp = np.sum(window * sig_ac * np.sin(phase))
    # Amplitude of A * sin(2*pi*f*t + phi) with Hann window normalization = 2 / sum(w)
    return float((2.0 / w_sum) * np.hypot(c_comp, s_comp))


def summarize_record_stats(data: dict[str, np.ndarray]) -> dict[str, Any]:
    """Return summary statistics of a loaded sim_out.bin stream."""
    omega_out = data["omega_out"]
    omega_in = data["omega_in"]
    half = len(omega_out) // 2
    tail_out = omega_out[half:]
    tail_in = omega_in[half:]
    return {
        "n_records": int(len(omega_out)),
        "duration_s": float(data["t"][-1] - data["t"][0]) if len(omega_out) > 1 else 0.0,
        "mean_omega_out_tail_rad_s": float(np.mean(tail_out)),
        "mean_omega_in_tail_rad_s": float(np.mean(tail_in)),
        "std_omega_out_tail_rad_s": float(np.std(tail_out)),
    }
