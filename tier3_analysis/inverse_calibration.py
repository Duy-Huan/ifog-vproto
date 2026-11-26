"""Tier 3 Inverse Parameter Identification & Multi-Objective Calibration Engine (EQ-53).

Implements IFOG-SIM-SPEC-007 §2.6 / §3 Phase 3:
  Fits hidden parasitic hardware parameters against experimental (or synthetic hardware-truth)
  Static AVAR + PSD, Slow Rate-Ramp (Deadband & Bunny Ears), and Thermal Chamber Ramp datasets:

      theta = [C_xtalk, G_xtalk, c_1/f, R_facet_dB, alpha_th_pot, delta_z_quad, alpha_Vpi, alpha_bobbin]^T

  Objective (EQ-53 / draft EQ-48):
      min_{theta in B}  w_avar * || log10(sigma_sim(tau; theta) / sigma_meas(tau)) ||_2^2
                      + w_db   * || (Omega_out_sim - Omega_out_meas) / Omega_norm ||_2^2
                      + w_th   * || (Omega_bias_sim - Omega_bias_meas) / Omega_th_norm ||_2^2

Three decoupled physical identification stages (plus joint weighted residual & covariance):
  - Stage A (Static AVAR + PSD):        c_pink_coeff, R_facet_dB, eta_pd_scale
  - Stage B (Slow Rate-Ramp Deadband):  C_xtalk_F, G_xtalk_S, dac_asym_lsb
  - Stage C (Thermal Chamber Ramp):     diffusivity_m2_per_s, delta_z_quad_m,
                                        alpha_vpi_ppm_K, alpha_bobbin_ppm_K
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import least_squares

from tier1_offline.config_loader import (
    RAD_S_TO_DEG_H,
    compute_backscatter_sigma_rad,
    compute_k_opt,
)
from tier1_offline.shupe_thermal import (
    compute_dynamic_k_opt_rel,
    elasto_optic_stress_integral,
    shupe_integral,
    solve_1d_heat_diffusion,
)
from tier3_analysis.dual_regime_avar import (
    DEG_H_TO_RAD_S,
    RAD_S2_TO_DEG_H2,
    RAD_S32_TO_DEG_H32,
    RAD_S_RT_S_TO_DEG_RT_H,
    ieee952_avar_model,
)

# Physical reference constants used by the Stage A/B/C predictive forward models
DEFAULT_AVAR_CONTEXT: dict[str, float] = {
    "K_opt": 1.3521584,
    "delta_nu_eff_Hz": 7.51e12,
    "alpha_R_per_m": 4.5e-5,
    "S_capture": 1.5e-3,
    "N_0_deg_rt_h": 0.0042,
    "B_pink_0_deg_h": 0.0040,
    "Q_arcsec": 0.05,
    "K_rrw_deg_rt_h3": 0.008,
    "R_ramp_deg_h2": 0.010,
    "backscatter_bi_gain": 3.0e-5,
    "f_corner_back_Hz": 0.015,
}

DEFAULT_DEADBAND_CONTEXT: dict[str, float] = {
    "K_opt": 1.3521584,
    "R_f_ohm": 50000.0,
    "P_peak_W": 1.0e-4,
    "responsivity_A_W": 0.95,
    "V_step_V": 1.5,
    "dt_edge_s": 3.0e-7,
    "c_db_res_deg_h_per_A": 1.2e7,
    "c_be_cap_deg_h_per_A": 2.2e4,
    "dac_lsb_deg_h": 0.08,
}

DEFAULT_THERMAL_CONTEXT: dict[str, float] = {
    "L_m": 1000.0,
    "D_m": 0.10,
    "lambda_bar_m": 1.55e-6,
    "n_eff": 1.468,
    "dn_dT_per_K": 1.0e-5,
    "alpha_T_per_K": 5.5e-7,
    "coil_thickness_m": 0.015,
    "n_z": 24,
    "boundary_ramp_K_per_s": 5.0e-2,
    "boundary_asymmetry_K_per_s": 0.0,
    "C_eo_per_Pa": 3.5e-12,
    "stress_rate_Pa_per_K": 1.2e5,
    "alpha_lambda_pm_K": 35.0,
    "delta_T_sld_ratio": 0.25,
    "delta_T_mioc_ratio": 0.85,
    "vpi_bias_coeff_deg_h_per_ppm": 8.0e-6,
    "sf_rate_deg_h": 36000.0,
}


def forward_avar_psd(
    taus_s: np.ndarray,
    freqs_Hz: np.ndarray,
    c_pink_coeff: float,
    R_facet_dB: float,
    eta_pd_scale: float,
    ctx: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Forward predictive model for Stage A Static AVAR [deg/h] & PSD [(deg/h)^2/Hz].

    Electronic 1/f flicker (c_pink_coeff) produces a broadband 1/f PSD and flat BI plateau,
    while coherent cavity back-reflection (R_facet_dB, EQ-52) follows a band-limited
    Ornstein-Uhlenbeck Lorentzian spectrum centered below f_corner_back_Hz.
    """
    c = {**DEFAULT_AVAR_CONTEXT, **(ctx or {})}
    taus = np.asarray(taus_s, dtype=np.float64)
    freqs = np.asarray(freqs_Hz, dtype=np.float64)

    # ARW scales inversely with optical/PD conversion efficiency eta_pd_scale
    n_deg_rt_h = c["N_0_deg_rt_h"] / max(eta_pd_scale, 0.1)
    n_si = n_deg_rt_h / RAD_S_RT_S_TO_DEG_RT_H

    # Back-reflection coherent phase RMS -> band-limited OU BI bump (EQ-52)
    sigma_back_rad = compute_backscatter_sigma_rad(
        R_facet_dB=R_facet_dB,
        alpha_R_per_m=c["alpha_R_per_m"],
        S_capture=c["S_capture"],
        delta_nu_eff_Hz=c["delta_nu_eff_Hz"],
    )
    b_back_deg_h = c["backscatter_bi_gain"] * (sigma_back_rad / c["K_opt"]) * RAD_S_TO_DEG_H
    b_pink_deg_h = c_pink_coeff * c["B_pink_0_deg_h"]
    b_pink_si = b_pink_deg_h * DEG_H_TO_RAD_S

    q_rad = c["Q_arcsec"] / ((180.0 / math.pi) * 3600.0)
    k_si = c["K_rrw_deg_rt_h3"] / RAD_S32_TO_DEG_H32
    r_si = c["R_ramp_deg_h2"] / RAD_S2_TO_DEG_H2

    # Base IEEE-952 5-region variance + exponentially correlated OU back-reflection AVAR contribution
    avar_si = ieee952_avar_model(taus, q_rad, n_si, b_pink_si, k_si, r_si)
    tau_c = 1.0 / (2.0 * math.pi * max(c["f_corner_back_Hz"], 1.0e-5))
    u = taus / tau_c
    # Exact Allan variance kernel of a 1st-order Gauss-Markov / OU process
    ou_kernel = (2.0 / u) - (3.0 - 4.0 * np.exp(-u) + np.exp(-2.0 * u)) / (u ** 2)
    ou_kernel = np.maximum(ou_kernel, 0.0)
    b_back_si = b_back_deg_h * DEG_H_TO_RAD_S
    avar_tot_si = avar_si + (b_back_si ** 2) * ou_kernel
    adev_deg_h = np.sqrt(np.maximum(avar_tot_si, 1.0e-30)) * RAD_S_TO_DEG_H

    # Single-sided rate PSD: white ARW + broadband 1/f electronic pink + Lorentzian OU back-reflection
    s_white = (n_deg_rt_h ** 2) * 3600.0
    s_pink_1hz = (b_pink_deg_h ** 2) / (2.0 * math.pi)
    f_c = c["f_corner_back_Hz"]
    s_back_lorentz = (2.0 * (b_back_deg_h ** 2) / (math.pi * f_c)) / (1.0 + (freqs / f_c) ** 2)
    psd_deg_h2_Hz = s_white + s_pink_1hz / np.maximum(freqs, 1.0e-6) + s_back_lorentz
    return adev_deg_h, psd_deg_h2_Hz


def forward_slow_rate_ramp(
    omega_in_deg_h: np.ndarray,
    C_xtalk_F: float,
    G_xtalk_S: float,
    dac_asym_lsb: float,
    ctx: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Forward predictive model for Stage B Slow-Rate Ramp Deadband & Bunny Ears (EQ-51).

    Resistive leakage G_xtalk_S persists across the blanking window (setting deadband half-width),
    while capacitive edge current C_xtalk_F * dV/dt drives the post-blanking Bunny Ears overshoot.
    """
    c = {**DEFAULT_DEADBAND_CONTEXT, **(ctx or {})}
    omega_in = np.asarray(omega_in_deg_h, dtype=np.float64)

    i_res = G_xtalk_S * c["V_step_V"]
    i_cap = C_xtalk_F * (c["V_step_V"] / c["dt_edge_s"])
    omega_db = c["c_db_res_deg_h_per_A"] * i_res
    be_amp = c["c_be_cap_deg_h_per_A"] * i_cap
    bias_asym = dac_asym_lsb * c["dac_lsb_deg_h"]

    omega_eff = omega_in + bias_asym
    abs_w = np.abs(omega_eff)
    sgn_w = np.sign(omega_eff)

    w_safe = max(omega_db, 1.0e-6)
    u = abs_w / w_safe
    lock_factor = np.where(u <= 1.0, 0.05 * (u ** 3), 1.0 - 0.95 * np.exp(-3.0 * (u - 1.0)))
    bunny_lobe = be_amp * np.exp(-0.5 * ((u - 1.55) / 0.50) ** 2) * (1.0 - np.exp(-4.0 * (u ** 2)))
    omega_out = sgn_w * (abs_w * lock_factor + bunny_lobe)

    return {
        "omega_out_deg_h": omega_out,
        "deadband_halfwidth_deg_h": float(omega_db),
        "bunny_ears_peak_deg_h": float(np.max(np.abs(omega_out - omega_in))),
    }


def forward_thermal_ramp(
    t_s: np.ndarray,
    diffusivity_m2_per_s: float,
    delta_z_quad_m: float,
    alpha_vpi_ppm_K: float,
    alpha_bobbin_ppm_K: float,
    ctx: dict[str, float] | None = None,
) -> dict[str, np.ndarray]:
    """Forward predictive model for Stage C Thermal Chamber Ramp using real Tier-1 Crank-Nicolson solver."""
    c = {**DEFAULT_THERMAL_CONTEXT, **(ctx or {})}
    t_req = np.asarray(t_s, dtype=np.float64)
    duration_s = float(t_req[-1] - t_req[0])
    dt_s = float(np.median(np.diff(t_req))) if len(t_req) > 1 else 10.0

    t_grid, x_norm, dT_dt_rad = solve_1d_heat_diffusion(
        n_z=int(c["n_z"]),
        coil_thickness_m=float(c["coil_thickness_m"]),
        diffusivity_m2_per_s=float(diffusivity_m2_per_s),
        duration_s=duration_s,
        dt_s=dt_s,
        boundary_ramp_K_per_s=float(c["boundary_ramp_K_per_s"]),
        boundary_asymmetry_K_per_s=float(c["boundary_asymmetry_K_per_s"]),
    )
    L_m = float(c["L_m"])
    # Symmetric quadrupole radial mapping around coil midpoint L/2:
    # cancels (L - 2z) so delta_z_quad_m & thermal diffusivity D_th are independently observable.
    z_m = np.linspace(0.0, L_m, len(x_norm))
    r_sym = np.abs(2.0 * (z_m / L_m) - 1.0)
    k_opt = compute_k_opt(L_m, float(c["D_m"]), float(c["lambda_bar_m"]))
    dz_quad = float(delta_z_quad_m) * np.ones_like(z_m)

    phi_therm = np.empty(len(t_grid), dtype=np.float64)
    mean_dT_dt = np.empty(len(t_grid), dtype=np.float64)
    for i in range(len(t_grid)):
        dT_dt_z = np.interp(r_sym, x_norm, dT_dt_rad[i, :])
        mean_dT_dt[i] = float(np.mean(dT_dt_z))
        p_shupe = shupe_integral(
            z_m=z_m,
            dT_dt_K_per_s=dT_dt_z,
            L_m=L_m,
            lambda_bar_m=float(c["lambda_bar_m"]),
            n_eff=float(c["n_eff"]),
            dn_dT_per_K=float(c["dn_dT_per_K"]),
            alpha_T_per_K=float(c["alpha_T_per_K"]),
            delta_z_quad_m=dz_quad,
        )
        p_stress = elasto_optic_stress_integral(
            z_m=z_m,
            dsigma_dt_Pa_per_s=float(c["stress_rate_Pa_per_K"]) * dT_dt_z,
            L_m=L_m,
            lambda_bar_m=float(c["lambda_bar_m"]),
            C_eo_per_Pa=float(c["C_eo_per_Pa"]),
            delta_z_quad_m=dz_quad,
        )
        phi_therm[i] = p_shupe + p_stress

    dt_vec = np.diff(t_grid, prepend=t_grid[0])
    dT_coil = np.cumsum(mean_dT_dt * dt_vec)
    dT_mioc = float(c["delta_T_mioc_ratio"]) * dT_coil
    dT_sld = float(c["delta_T_sld_ratio"]) * dT_coil

    # Bias drift [deg/h]: transient Shupe + stress (scales with dz_quad & D_th) + ramp-growing V_pi term
    omega_bias_grid = (phi_therm / k_opt) * RAD_S_TO_DEG_H + (
        float(c["vpi_bias_coeff_deg_h_per_ppm"]) * alpha_vpi_ppm_K * dT_mioc
    )
    k_opt_rel_grid = np.asarray(
        compute_dynamic_k_opt_rel(
            dT_coil_K=dT_coil,
            dT_sld_K=dT_sld,
            alpha_bobbin_ppm_K=alpha_bobbin_ppm_K,
            alpha_lambda_pm_K=float(c["alpha_lambda_pm_K"]),
            lambda_bar_m=float(c["lambda_bar_m"]),
            kappa_back_m_per_W=0.0,
            P_back_W=0.0,
            n_eff=float(c["n_eff"]),
            dn_dT_per_K=float(c["dn_dT_per_K"]),
        ),
        dtype=np.float64,
    )
    sf_err_ppm_grid = (k_opt_rel_grid - 1.0) * 1.0e6

    return {
        "omega_bias_deg_h": np.interp(t_req, t_grid, omega_bias_grid),
        "sf_err_ppm": np.interp(t_req, t_grid, sf_err_ppm_grid),
        "dT_coil_K": np.interp(t_req, t_grid, dT_coil),
    }


def compute_multi_objective_cost(
    avar_sim: np.ndarray,
    avar_meas: np.ndarray,
    db_sim: np.ndarray,
    db_meas: np.ndarray,
    th_sim: np.ndarray,
    th_meas: np.ndarray,
    w_avar: float = 1.0,
    w_db: float = 1.0,
    w_th: float = 1.0,
    omega_norm: float = 0.25,
    omega_th_norm: float = 0.05,
) -> float:
    """Evaluate exact SPEC-007 EQ-53 (draft EQ-48) multi-objective calibration cost."""
    r_avar = np.log10(np.maximum(avar_sim, 1.0e-30) / np.maximum(avar_meas, 1.0e-30))
    r_db = (db_sim - db_meas) / max(omega_norm, 1.0e-12)
    r_th = (th_sim - th_meas) / max(omega_th_norm, 1.0e-12)
    return float(
        w_avar * np.sum(r_avar ** 2)
        + w_db * np.sum(r_db ** 2)
        + w_th * np.sum(r_th ** 2)
    )


def _compute_cov_and_ci95(jac: np.ndarray, residuals: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Compute Gauss-Newton parameter covariance matrix & 95% confidence half-widths."""
    n_obs, n_par = jac.shape
    dof = max(1, n_obs - n_par)
    s2 = float(np.sum(residuals ** 2)) / float(dof)
    jtj = jac.T @ jac
    reg = 1.0e-12 * max(1.0, float(np.max(np.diag(jtj))))
    cov = s2 * np.linalg.pinv(jtj + reg * np.eye(n_par))
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    ci95 = 1.96 * se
    return cov, ci95


class InverseCalibrator:
    """Three-Stage Bounded Trust-Region Inverse Parameter Identification Engine (SPEC-007 EQ-53)."""

    def __init__(
        self,
        avar_ctx: dict[str, float] | None = None,
        db_ctx: dict[str, float] | None = None,
        th_ctx: dict[str, float] | None = None,
        weights: tuple[float, float, float] = (1.0, 1.0, 1.0),
    ) -> None:
        self.avar_ctx = {**DEFAULT_AVAR_CONTEXT, **(avar_ctx or {})}
        self.db_ctx = {**DEFAULT_DEADBAND_CONTEXT, **(db_ctx or {})}
        self.th_ctx = {**DEFAULT_THERMAL_CONTEXT, **(th_ctx or {})}
        self.w_avar, self.w_db, self.w_th = weights

    def fit_stage_a_static(
        self,
        taus_s: np.ndarray,
        avar_meas_deg_h: np.ndarray,
        freqs_Hz: np.ndarray,
        psd_meas_deg_h2_Hz: np.ndarray,
        init_guess: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Stage A: Fit (c_pink_coeff, R_facet_dB, eta_pd_scale) to static AVAR + PSD."""
        g = init_guess or {"c_pink_coeff": 1.0, "R_facet_dB": -75.0, "eta_pd_scale": 1.0}
        x0 = np.array([g["c_pink_coeff"], g["R_facet_dB"], g["eta_pd_scale"]], dtype=np.float64)
        lb = np.array([0.05, -110.0, 0.25], dtype=np.float64)
        ub = np.array([25.0, -35.0, 2.5], dtype=np.float64)

        sqrt_w = math.sqrt(self.w_avar)

        def resid(x: np.ndarray) -> np.ndarray:
            av_sim, psd_sim = forward_avar_psd(
                taus_s, freqs_Hz, float(x[0]), float(x[1]), float(x[2]), self.avar_ctx
            )
            r_av = np.log10(np.maximum(av_sim, 1.0e-30) / np.maximum(avar_meas_deg_h, 1.0e-30))
            r_psd = 0.5 * np.log10(
                np.maximum(psd_sim, 1.0e-30) / np.maximum(psd_meas_deg_h2_Hz, 1.0e-30)
            )
            return sqrt_w * np.concatenate([r_av, r_psd])

        res = least_squares(resid, x0, bounds=(lb, ub), method="trf", x_scale="jac")
        cov, ci95 = _compute_cov_and_ci95(res.jac, res.fun)
        names = ("c_pink_coeff", "R_facet_dB", "eta_pd_scale")
        return {
            "params": {k: float(v) for k, v in zip(names, res.x)},
            "ci95": {k: float(v) for k, v in zip(names, ci95)},
            "covariance": cov.tolist(),
            "cost": float(2.0 * res.cost),
            "nfev": int(res.nfev),
        }

    def fit_stage_b_deadband(
        self,
        omega_in_deg_h: np.ndarray,
        omega_out_meas_deg_h: np.ndarray,
        init_guess: dict[str, float] | None = None,
        omega_norm: float = 0.25,
    ) -> dict[str, Any]:
        """Stage B: Fit (C_xtalk_F, G_xtalk_S, dac_asym_lsb) to Slow-Rate Ramp Deadband/Bunny Ears."""
        g = init_guess or {"C_xtalk_F": 2.0e-12, "G_xtalk_S": 1.0e-8, "dac_asym_lsb": 0.0}
        # Scale C_xtalk [pF] and G_xtalk [nS] to O(1) for crisp TRF conditioning
        x0 = np.array([g["C_xtalk_F"] * 1.0e12, g["G_xtalk_S"] * 1.0e9, g["dac_asym_lsb"]], dtype=np.float64)
        lb = np.array([0.0, 0.0, -5.0], dtype=np.float64)
        ub = np.array([50.0, 500.0, 5.0], dtype=np.float64)

        sqrt_w = math.sqrt(self.w_db)

        def resid(x: np.ndarray) -> np.ndarray:
            out = forward_slow_rate_ramp(
                omega_in_deg_h, float(x[0]) * 1.0e-12, float(x[1]) * 1.0e-9, float(x[2]), self.db_ctx
            )
            return sqrt_w * (out["omega_out_deg_h"] - omega_out_meas_deg_h) / max(omega_norm, 1.0e-12)

        res = least_squares(resid, x0, bounds=(lb, ub), method="trf", x_scale="jac")
        scales = np.array([1.0e-12, 1.0e-9, 1.0], dtype=np.float64)
        cov_s, ci_s = _compute_cov_and_ci95(res.jac, res.fun)
        cov = (scales[:, None] * cov_s) * scales[None, :]
        ci95 = ci_s * scales
        vals = res.x * scales
        names = ("C_xtalk_F", "G_xtalk_S", "dac_asym_lsb")
        return {
            "params": {k: float(v) for k, v in zip(names, vals)},
            "ci95": {k: float(v) for k, v in zip(names, ci95)},
            "covariance": cov.tolist(),
            "cost": float(2.0 * res.cost),
            "nfev": int(res.nfev),
        }

    def fit_stage_c_thermal(
        self,
        t_s: np.ndarray,
        omega_bias_meas_deg_h: np.ndarray,
        sf_err_meas_ppm: np.ndarray,
        init_guess: dict[str, float] | None = None,
        omega_th_norm: float = 0.05,
        sf_norm_ppm: float = 10.0,
    ) -> dict[str, Any]:
        """Stage C: Fit (diffusivity_m2_per_s, delta_z_quad_m, alpha_vpi_ppm_K, alpha_bobbin_ppm_K)."""
        g = init_guess or {
            "diffusivity_m2_per_s": 8.4e-7,
            "delta_z_quad_m": 0.002,
            "alpha_vpi_ppm_K": 300.0,
            "alpha_bobbin_ppm_K": 10.0,
        }
        # Scale parameters to O(1): D [1e-7 m^2/s], dz [mm], alpha_vpi [100 ppm/K], alpha_bobbin [10 ppm/K]
        scales = np.array([1.0e-7, 1.0e-3, 100.0, 10.0], dtype=np.float64)
        x0 = np.array(
            [
                g["diffusivity_m2_per_s"] / scales[0],
                g["delta_z_quad_m"] / scales[1],
                g["alpha_vpi_ppm_K"] / scales[2],
                g["alpha_bobbin_ppm_K"] / scales[3],
            ],
            dtype=np.float64,
        )
        lb = np.array([1.0, 0.1, -20.0, -10.0], dtype=np.float64)
        ub = np.array([50.0, 25.0, 20.0, 20.0], dtype=np.float64)

        sqrt_w = math.sqrt(self.w_th)

        def resid(x: np.ndarray) -> np.ndarray:
            out = forward_thermal_ramp(
                t_s,
                float(x[0] * scales[0]),
                float(x[1] * scales[1]),
                float(x[2] * scales[2]),
                float(x[3] * scales[3]),
                self.th_ctx,
            )
            r_bias = (out["omega_bias_deg_h"] - omega_bias_meas_deg_h) / max(omega_th_norm, 1.0e-12)
            r_sf = (out["sf_err_ppm"] - sf_err_meas_ppm) / max(sf_norm_ppm, 1.0e-12)
            return sqrt_w * np.concatenate([r_bias, r_sf])

        res = least_squares(resid, x0, bounds=(lb, ub), method="trf", x_scale="jac")
        cov_s, ci_s = _compute_cov_and_ci95(res.jac, res.fun)
        cov = (scales[:, None] * cov_s) * scales[None, :]
        ci95 = ci_s * scales
        vals = res.x * scales
        names = ("diffusivity_m2_per_s", "delta_z_quad_m", "alpha_vpi_ppm_K", "alpha_bobbin_ppm_K")
        return {
            "params": {k: float(v) for k, v in zip(names, vals)},
            "ci95": {k: float(v) for k, v in zip(names, ci95)},
            "covariance": cov.tolist(),
            "cost": float(2.0 * res.cost),
            "nfev": int(res.nfev),
        }

    def calibrate_all(
        self,
        dataset: dict[str, np.ndarray],
        initial_params: dict[str, float],
        out_path: Path | str | None = None,
    ) -> dict[str, Any]:
        """Run Stages A, B, and C end-to-end, evaluate before/after error, and persist calibrated_params.json."""
        taus = dataset["taus_s"]
        avar_meas = dataset["avar_meas_deg_h"]
        freqs = dataset["freqs_Hz"]
        psd_meas = dataset["psd_meas_deg_h2_Hz"]
        omega_in = dataset["omega_in_deg_h"]
        omega_out_meas = dataset["omega_out_meas_deg_h"]
        t_th = dataset["t_thermal_s"]
        bias_meas = dataset["omega_bias_meas_deg_h"]
        sf_meas = dataset["sf_err_meas_ppm"]

        # Evaluate uncalibrated baseline predictions
        av_pre, _ = forward_avar_psd(
            taus, freqs, initial_params["c_pink_coeff"], initial_params["R_facet_dB"],
            initial_params["eta_pd_scale"], self.avar_ctx,
        )
        db_pre = forward_slow_rate_ramp(
            omega_in, initial_params["C_xtalk_F"], initial_params["G_xtalk_S"],
            initial_params["dac_asym_lsb"], self.db_ctx,
        )["omega_out_deg_h"]
        th_pre = forward_thermal_ramp(
            t_th, initial_params["diffusivity_m2_per_s"], initial_params["delta_z_quad_m"],
            initial_params["alpha_vpi_ppm_K"], initial_params["alpha_bobbin_ppm_K"], self.th_ctx,
        )

        # Execute Stages A, B, C
        st_a = self.fit_stage_a_static(taus, avar_meas, freqs, psd_meas, initial_params)
        st_b = self.fit_stage_b_deadband(omega_in, omega_out_meas, initial_params)
        st_c = self.fit_stage_c_thermal(t_th, bias_meas, sf_meas, initial_params)

        cal_params = {**st_a["params"], **st_b["params"], **st_c["params"]}
        ci95 = {**st_a["ci95"], **st_b["ci95"], **st_c["ci95"]}

        # Evaluate calibrated predictions
        av_post, _ = forward_avar_psd(
            taus, freqs, cal_params["c_pink_coeff"], cal_params["R_facet_dB"],
            cal_params["eta_pd_scale"], self.avar_ctx,
        )
        db_post = forward_slow_rate_ramp(
            omega_in, cal_params["C_xtalk_F"], cal_params["G_xtalk_S"],
            cal_params["dac_asym_lsb"], self.db_ctx,
        )["omega_out_deg_h"]
        th_post = forward_thermal_ramp(
            t_th, cal_params["diffusivity_m2_per_s"], cal_params["delta_z_quad_m"],
            cal_params["alpha_vpi_ppm_K"], cal_params["alpha_bobbin_ppm_K"], self.th_ctx,
        )

        def _nrmse_pct(sim: np.ndarray, meas: np.ndarray) -> float:
            denom = max(float(np.sqrt(np.mean(meas ** 2))), 1.0e-12)
            return float(100.0 * math.sqrt(float(np.mean((sim - meas) ** 2))) / denom)

        def _rel_rms_pct(sim: np.ndarray, meas: np.ndarray) -> float:
            rel = (sim - meas) / np.maximum(np.abs(meas), 1.0e-12)
            return float(100.0 * math.sqrt(float(np.mean(rel ** 2))))

        err_before = {
            "avar_nrmse_pct": _rel_rms_pct(av_pre, avar_meas),
            "deadband_nrmse_pct": _nrmse_pct(db_pre - omega_in, omega_out_meas - omega_in),
            "thermal_bias_nrmse_pct": _nrmse_pct(th_pre["omega_bias_deg_h"], bias_meas),
            "thermal_sf_nrmse_pct": _nrmse_pct(th_pre["sf_err_ppm"], sf_meas),
        }
        err_after = {
            "avar_nrmse_pct": _rel_rms_pct(av_post, avar_meas),
            "deadband_nrmse_pct": _nrmse_pct(db_post - omega_in, omega_out_meas - omega_in),
            "thermal_bias_nrmse_pct": _nrmse_pct(th_post["omega_bias_deg_h"], bias_meas),
            "thermal_sf_nrmse_pct": _nrmse_pct(th_post["sf_err_ppm"], sf_meas),
        }
        cost_before = compute_multi_objective_cost(
            av_pre, avar_meas, db_pre, omega_out_meas, th_pre["omega_bias_deg_h"], bias_meas,
            self.w_avar, self.w_db, self.w_th,
        )
        cost_after = compute_multi_objective_cost(
            av_post, avar_meas, db_post, omega_out_meas, th_post["omega_bias_deg_h"], bias_meas,
            self.w_avar, self.w_db, self.w_th,
        )

        result = {
            "spec_id": "IFOG-SIM-SPEC-007",
            "uncalibrated_params": {k: float(initial_params[k]) for k in cal_params},
            "calibrated_params": cal_params,
            "ci95": ci95,
            "stages": {"stage_a": st_a, "stage_b": st_b, "stage_c": st_c},
            "cost_before": cost_before,
            "cost_after": cost_after,
            "error_before_pct": err_before,
            "error_after_pct": err_after,
            "max_error_before_pct": float(max(err_before.values())),
            "max_error_after_pct": float(max(err_after.values())),
            "pass_lt_5pct": bool(max(err_after.values()) < 5.0),
        }
        if out_path is not None:
            op = Path(out_path)
            op.parent.mkdir(parents=True, exist_ok=True)
            op.write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result
