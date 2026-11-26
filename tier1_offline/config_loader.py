"""Shared configuration loader, JSON Schema v4 validator, and physical constants.

Implements normative constants and closed-form reference equations from
IFOG-SIM-SPEC-004 (Sections 3 and 4).
"""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
from typing import Any

import jsonschema

# Exact SI / CODATA physical constants
C_LIGHT: float = 299_792_458.0  # m/s
Q_ELECTRON: float = 1.602_176_634e-19  # C
K_BOLTZMANN: float = 1.380_649e-23  # J/K
RAD_S_TO_DEG_H: float = (180.0 / math.pi) * 3600.0  # 206264.80624709636 deg/h per rad/s
DEG_H_TO_RAD_S: float = 1.0 / RAD_S_TO_DEG_H
DEG_S_TO_RAD_S: float = math.pi / 180.0
RAD_S_TO_DEG_S: float = 180.0 / math.pi

DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "configs" / "schema_v6.json"

DEFAULT_SPEC007_PHYSICS: dict[str, Any] = {
    "en_spec007_physics": False,
    "lut_version": 1,
    "winding_pattern": "quadrupole",
    "n_turns": 3200,
    "n_layers": 32,
    "flange_offset_m": 0.0,
    "C_eo_per_Pa": 0.0,
    "stress_rate_Pa_per_K": 0.0,
    "alpha_bobbin_ppm_K": 0.0,
    "alpha_lambda_pm_K": 0.0,
    "kappa_back_m_per_W": 0.0,
    "P_back_W": 0.0,
    "beta_V_per_K": 0.0,
    "gamma_pol_rad_per_K": 0.0,
    "alpha_vpi_ppm_K": 0.0,
    "delta_T_sld_ratio": 0.0,
    "delta_T_mioc_ratio": 0.0,
    "C_xtalk_F": 0.0,
    "G_xtalk_S": 0.0,
    "R_facet_dB": -200.0,
    "alpha_R_per_m": 0.0,
    "S_capture": 0.0,
    "tau_env_s": 1.0,
    "sigma_theta_env_rad": 0.0,
    "mioc_f_elec_Hz": 0.0,
    "mioc_f_acoustic_Hz": 0.0,
    "mioc_zeta_acoustic": 0.1,
    "mioc_g_acoustic": 0.0,
}


def get_spec007_physics(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return resolved spec007_physics dict, defaulting omitted v4/v5 fields to zero/ideal."""
    out = copy.deepcopy(DEFAULT_SPEC007_PHYSICS)
    raw = cfg.get("spec007_physics")
    if isinstance(raw, dict):
        out.update(raw)
    return out


def compute_backscatter_sigma_rad(
    R_facet_dB: float,
    alpha_R_per_m: float,
    S_capture: float,
    delta_nu_eff_Hz: float,
) -> float:
    """Compute coherent cavity facet + Rayleigh backscattering phase RMS sigma_phi,back [rad] (EQ-52)."""
    r_facet = 10.0 ** (R_facet_dB / 10.0) if R_facet_dB > -199.0 else 0.0
    l_coh = C_LIGHT / delta_nu_eff_Hz
    return 2.0 * math.sqrt(max(0.0, r_facet + 0.5 * alpha_R_per_m * S_capture * l_coh))


def deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-merged copy of ``base`` updated recursively with ``overrides``."""
    merged = copy.deepcopy(base)
    for key, val in overrides.items():
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = deep_merge(merged[key], val)
        else:
            merged[key] = copy.deepcopy(val)
    return merged


def load_schema(schema_path: Path | str = DEFAULT_SCHEMA_PATH) -> dict[str, Any]:
    """Load the normative JSON Schema (v6.0, backward-compatible with v4.0 & v5.0)."""
    with Path(schema_path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_config(
    cfg: dict[str, Any], schema_path: Path | str = DEFAULT_SCHEMA_PATH
) -> dict[str, Any]:
    """Validate configuration dict against schema_v6.json (or v4.0/v5.0) plus physical bounds.

    Enforces Rule 11 (fail-closed validation):
      - JSON Schema draft 2020-12 compliance
      - Blanking window bounds: 0 <= k_start <= k_end < K_oversample
      - Pink noise frequency band: pink_f_min_Hz < pink_f_max_Hz
      - ADC voltage rails: V_min_V < V_max_V
      - Jury stability: 0 < K_tot_1 < 1
      - 4-state / 6-state dual-loop separation: K_tot_2 <= 0.1 * K_tot_1 when en_vpi_loop is True
      - SPEC-007 winding topology: n_turns >= n_layers when spec007_physics is present
    """
    schema = load_schema(schema_path)
    jsonschema.validate(instance=cfg, schema=schema)

    adc = cfg["adc_dac"]
    if not (0 <= adc["k_start"] <= adc["k_end"] < adc["K_oversample"]):
        raise ValueError(
            f"Invalid ADC blanking window [{adc['k_start']}, {adc['k_end']}] "
            f"for K_oversample={adc['K_oversample']}"
        )

    afe = cfg["analog_frontend"]
    if afe["V_min_V"] >= afe["V_max_V"]:
        raise ValueError(
            f"Invalid ADC clipping rails: V_min_V ({afe['V_min_V']}) >= V_max_V ({afe['V_max_V']})"
        )

    noise = cfg["noise"]
    if noise["pink_f_min_Hz"] >= noise["pink_f_max_Hz"]:
        raise ValueError(
            f"Invalid pink noise band: f_min ({noise['pink_f_min_Hz']}) >= f_max ({noise['pink_f_max_Hz']})"
        )

    dsp = cfg["dsp"]
    if dsp["mode"] in ("4state", "6state") and dsp["en_vpi_loop"]:
        if dsp["K_tot_2"] > 0.1 * dsp["K_tot_1"] + 1e-15:
            raise ValueError(
                f"Loop-2 bandwidth separation violated (EQ-22/EQ-34): "
                f"K_tot_2 ({dsp['K_tot_2']}) > 0.1 * K_tot_1 ({0.1 * dsp['K_tot_1']})"
            )

    if "spec007_physics" in cfg:
        sp7 = get_spec007_physics(cfg)
        if int(sp7["n_turns"]) < int(sp7["n_layers"]):
            raise ValueError(
                f"Invalid SPEC-007 winding map: n_turns ({sp7['n_turns']}) < n_layers ({sp7['n_layers']})"
            )

    return cfg


def load_config(
    cfg_path: Path | str, schema_path: Path | str = DEFAULT_SCHEMA_PATH
) -> dict[str, Any]:
    """Load and validate an IFOG configuration JSON file."""
    with Path(cfg_path).open("r", encoding="utf-8") as fh:
        cfg = json.load(fh)
    return validate_config(cfg, schema_path=schema_path)


def compute_k_opt(L_m: float, D_m: float, lambda_bar_m: float) -> float:
    """Compute Sagnac optical scale factor K_opt [rad/(rad/s)] (EQ-07)."""
    return (2.0 * math.pi * L_m * D_m) / (lambda_bar_m * C_LIGHT)


def compute_tau(L_m: float, n_eff: float) -> float:
    """Compute fiber coil transit time tau = n_eff * L / c [s] (EQ-06)."""
    return (n_eff * L_m) / C_LIGHT


def compute_kerr_phase(
    n2_m2_per_W: float,
    L_eff_m: float,
    lambda_bar_m: float,
    A_eff_m2: float,
    kappa_split: float,
    P_coil_W: float,
    eta_coh: float,
) -> float:
    """Compute non-reciprocal Kerr phase Delta_phi_Kerr [rad] (EQ-08, Bergh et al. 1982)."""
    return (
        (2.0 * math.pi * n2_m2_per_W * L_eff_m)
        / (lambda_bar_m * A_eff_m2)
        * (1.0 - 2.0 * kappa_split)
        * P_coil_W
        * eta_coh
    )


def compute_delta_nu_eff(lambda_bar_m: float, delta_lambda_fwhm_m: float) -> float:
    """Compute effective SLD optical spectral bandwidth Delta_nu_eff [Hz] (EQ-04)."""
    delta_nu_fwhm = (C_LIGHT / (lambda_bar_m ** 2)) * delta_lambda_fwhm_m
    return math.sqrt(math.pi / (2.0 * math.log(2.0))) * delta_nu_fwhm


def compute_tia_dynamics(
    R_f_ohm: float, C_tot_F: float, C_f_F: float, f_gbw_Hz: float
) -> dict[str, float]:
    """Compute 2nd-order TIA parameters (EQ-16, EQ-17, Graeme 1996)."""
    two_pi_gbw = 2.0 * math.pi * f_gbw_Hz
    omega_0 = math.sqrt(two_pi_gbw / (R_f_ohm * (C_tot_F + C_f_F)))
    zeta = 0.5 * omega_0 * (R_f_ohm * C_f_F + 1.0 / two_pi_gbw)
    c_f_opt = math.sqrt(C_tot_F / (two_pi_gbw * R_f_ohm))
    t_s_0p1pct = 6.9 / (zeta * omega_0)
    return {
        "omega_0_rad_per_s": omega_0,
        "zeta": zeta,
        "C_f_opt_F": c_f_opt,
        "t_s_0p1pct_s": t_s_0p1pct,
    }


def compute_tia_noise_variance(
    P_det_W: float,
    responsivity_A_per_W: float,
    I_dark_A: float,
    T_tia_K: float,
    R_f_ohm: float,
    delta_nu_eff_Hz: float,
    i_n_op_A_per_rtHz: float,
    e_n_op_V_per_rtHz: float,
    C_tot_F: float,
    C_f_F: float,
    B_fast_Hz: float,
) -> dict[str, float]:
    """Compute 6-component TIA input current noise PSD and integrated variance (EQ-15)."""
    s_shot_dark = 2.0 * Q_ELECTRON * (responsivity_A_per_W * P_det_W + I_dark_A)
    s_thermal = (4.0 * K_BOLTZMANN * T_tia_K) / R_f_ohm
    s_rin = ((responsivity_A_per_W * P_det_W) ** 2) / delta_nu_eff_Hz
    s_op_white = (i_n_op_A_per_rtHz ** 2) + (e_n_op_V_per_rtHz ** 2) / (R_f_ohm ** 2)
    s_flat = s_shot_dark + s_thermal + s_rin + s_op_white
    var_flat = s_flat * B_fast_Hz
    var_cap = (
        (1.0 / 3.0)
        * (e_n_op_V_per_rtHz ** 2)
        * ((2.0 * math.pi) ** 2)
        * ((C_tot_F + C_f_F) ** 2)
        * (B_fast_Hz ** 3)
    )
    return {
        "S_shot_dark_A2_per_Hz": s_shot_dark,
        "S_thermal_A2_per_Hz": s_thermal,
        "S_rin_A2_per_Hz": s_rin,
        "S_op_white_A2_per_Hz": s_op_white,
        "S_flat_A2_per_Hz": s_flat,
        "var_flat_A2": var_flat,
        "var_cap_A2": var_cap,
        "var_total_A2": var_flat + var_cap,
    }
