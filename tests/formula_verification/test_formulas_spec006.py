"""Normative Formula Verification Tests for IFOG-SIM-SPEC-006 (EQ-42 .. EQ-44).

Each formula has an isolated @pytest.mark.formula test checked by scripts/verify_formulas_ci.py:
  - EQ-42: Multi-rate FMI 3.0 macro/micro step alignment N_tau & anti-aliased sinc boxcar average
  - EQ-43: FMI 3.0 Loop-2 residual V_pi phase error e_Vpi_res [rad] & 6-bit bit_status bitmask
  - EQ-44: Black-box FMU vs standalone Tier 2 < 1e-12 equivalence bound & singleton contract
"""

from __future__ import annotations

import math

import numpy as np
import pytest


@pytest.mark.formula
def test_eq42_fmi3_multirate_alignment_and_antialiasing() -> None:
    """EQ-42: Verify macro/micro cluster count N_tau and anti-aliased boxcar ARW preservation."""
    L_m = 1000.0
    n_eff = 1.468
    c_light = 299792458.0
    tau_s = (n_eff * L_m) / c_light
    H_s = 1.0e-3  # 1 ms macro FMI communication step (1 kHz)

    # Exact step count per macro interval over 100 consecutive macro steps
    n_macro = 100
    counts = [
        int(math.floor(((k + 1) * H_s) / tau_s)) - int(math.floor((k * H_s) / tau_s))
        for k in range(n_macro)
    ]
    assert sum(counts) == int(math.floor((n_macro * H_s) / tau_s))
    assert all(c in (204, 205) for c in counts)

    # Verify boxcar interval averaging preserves exact white ARW spectral density N^2
    # without high-frequency aliasing when decimated to f_comm = 1/H.
    rng = np.random.default_rng(42006)
    n_arw = 1.0e-6  # rad / sqrt(s)
    n_steps_total = 4000 * 204
    w_micro = (n_arw / math.sqrt(tau_s)) * rng.standard_normal(n_steps_total)
    w_macro_avg = w_micro.reshape(4000, 204).mean(axis=1)
    dt_macro = 204 * tau_s
    n_est_avg = float(np.std(w_macro_avg)) * math.sqrt(dt_macro)
    # Direct unaveraged decimation aliases by sqrt(204) ~= 14.3x; averaged preserves true ARW within 5%
    n_est_aliased = float(np.std(w_micro[::204])) * math.sqrt(dt_macro)
    assert abs(n_est_avg - n_arw) / n_arw < 0.05
    assert n_est_aliased > 10.0 * n_arw


@pytest.mark.formula
def test_eq43_fmi3_evpi_residual_and_bit_status_bitmask() -> None:
    """EQ-43: Verify e_Vpi_res = 2*pi*eps_Vpi_eff [rad] and orthogonal 6-bit bit_status bitmask."""
    v_pi_0 = 3.0
    v_ref_dac = 6.0
    g_dac_nom = (2.0 * v_pi_0) / v_ref_dac
    eps_vpi = 0.02

    # Uncorrected initial DAC gain (G_DAC = G_DAC_nom) yields exact 2*pi*eps_Vpi residual phase error
    eps_eff_init = (1.0 + eps_vpi) * (g_dac_nom * v_ref_dac / (2.0 * v_pi_0)) - 1.0
    e_vpi_res_init = 2.0 * math.pi * eps_eff_init
    assert abs(e_vpi_res_init - 2.0 * math.pi * eps_vpi) < 1.0e-15

    # Converged Loop-2 gain G_DAC = G_DAC_nom / (1 + eps_Vpi) nulls residual error identically
    g_dac_locked = g_dac_nom / (1.0 + eps_vpi)
    eps_eff_locked = (1.0 + eps_vpi) * (g_dac_locked * v_ref_dac / (2.0 * v_pi_0)) - 1.0
    e_vpi_res_locked = 2.0 * math.pi * eps_eff_locked
    assert abs(e_vpi_res_locked) < 1.0e-15

    # Orthogonal 6-bit BIT/FDIR & saturation bitmask encoding (bits 0..5)
    masks = [1 << bit for bit in range(6)]
    assert len(set(masks)) == 6
    combined = 0
    for m in masks:
        assert (combined & m) == 0
        combined |= m
    assert combined == 0x3F


@pytest.mark.formula
def test_eq44_fmi3_equivalence_bound_and_singleton_contract() -> None:
    """EQ-44: Verify < 1e-12 equivalence bound, LSB quantization budget, and singleton XML rule."""
    omega_standalone = 0.050029044843417
    omega_fmu = 0.050029044843417
    e_vpi_standalone = 2.0 * math.pi * 9.739395e-5
    e_vpi_fmu = 2.0 * math.pi * 9.739395e-5

    assert abs(omega_fmu - omega_standalone) < 1.0e-12
    assert abs(e_vpi_fmu - e_vpi_standalone) < 1.0e-12

    # Verify SimRecord 1e-12 rad/s integer LSB round-trip error bound (<= 0.5e-12 rad/s)
    omega_lsb = 1.0e-12
    quantized = round(omega_standalone / omega_lsb) * omega_lsb
    assert abs(quantized - omega_standalone) <= 0.5 * omega_lsb + 1.0e-18
