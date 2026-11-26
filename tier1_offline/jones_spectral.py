"""Tier 1 Offline Optical Solver: Spectral-Sliced Jones Matrix Model (EQ-04, EQ-05, EQ-07, EQ-08).

Computes broadband SLD + polarization-maintaining (PM) fiber coil Jones matrices
J_CW(omega_k) and J_CCW(omega_k) = J_CW(omega_k)^T, static interferometric fringe
visibility V, polarization bias phase phi_pol, Sagnac scale factor K_opt, optical
Kerr phase Delta_phi_Kerr, and coil transit time tau.

CLI Contract (IFOG-SIM-SPEC-004 Section 5.2):
    python3 tier1_offline/jones_spectral.py --cfg configs/baseline_1km.json --out data/run01/
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from tier1_offline.config_loader import (
    C_LIGHT,
    compute_backscatter_sigma_rad,
    compute_delta_nu_eff,
    compute_k_opt,
    compute_kerr_phase,
    compute_tau,
    get_spec007_physics,
    load_config,
)


def build_spectral_slices(
    lambda_bar_m: float, delta_lambda_fwhm_m: float, n_spec: int
) -> tuple[np.ndarray, np.ndarray, float]:
    """Generate normalized Gaussian optical frequency slices (omega_k, w_k, delta_nu_eff).

    Follows EQ-04 (Section 3.1.1):
      nu_bar = c / lambda_bar
      Delta_nu_eff = sqrt(pi / (2 ln 2)) * Delta_nu_FWHM
      sum_k w_k = 1
    """
    nu_bar = C_LIGHT / lambda_bar_m
    delta_nu_fwhm = (C_LIGHT / (lambda_bar_m ** 2)) * delta_lambda_fwhm_m
    delta_nu_eff = compute_delta_nu_eff(lambda_bar_m, delta_lambda_fwhm_m)
    sigma_nu = delta_nu_fwhm / (2.0 * math.sqrt(2.0 * math.log(2.0)))

    nu_grid = np.linspace(nu_bar - 3.0 * sigma_nu, nu_bar + 3.0 * sigma_nu, n_spec)
    weights = np.exp(-0.5 * ((nu_grid - nu_bar) / sigma_nu) ** 2)
    weights /= np.sum(weights)
    omega_k = 2.0 * math.pi * nu_grid
    return omega_k, weights, delta_nu_eff


def compute_jones_matrices(
    omega_k: np.ndarray,
    lambda_bar_m: float,
    n_eff: float,
    L_m: float,
    beat_length_m: float,
    h_param_inv_m: float,
    er_dB: float,
    m_segments: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Compute J_CW(omega_k) and J_CCW(omega_k) = J_CW(omega_k)^T (EQ-04).

    Returns:
        J_cw: shape (N_spec, 2, 2) complex128
        J_ccw: shape (N_spec, 2, 2) complex128
        thetas: shape (M,) random mode-coupling angles ~ N(0, h * dz)
    """
    n_spec = omega_k.shape[0]
    dz = L_m / float(m_segments)
    omega_bar = 2.0 * math.pi * (C_LIGHT / lambda_bar_m)

    # Polarizer extinction ratio ER_dB = -20 log10(eps_pol)
    eps_pol = 10.0 ** (-er_dB / 20.0)
    j_pol = np.array([[1.0, 0.0], [0.0, eps_pol]], dtype=np.complex128)

    # Frequency-resolved propagation constants beta_x(omega_k), beta_y(omega_k)
    delta_beta_k = (2.0 * math.pi / beat_length_m) * (omega_k / omega_bar)
    beta_mean_k = (n_eff * omega_k) / C_LIGHT
    beta_x_k = beta_mean_k + 0.5 * delta_beta_k
    beta_y_k = beta_mean_k - 0.5 * delta_beta_k

    # B_m(omega_k) = diag(exp(-j beta_x dz), exp(-j beta_y dz))
    exp_x = np.exp(-1j * beta_x_k * dz)
    exp_y = np.exp(-1j * beta_y_k * dz)

    rng = np.random.default_rng(seed)
    sigma_theta = math.sqrt(h_param_inv_m * dz)
    thetas = rng.normal(loc=0.0, scale=sigma_theta, size=m_segments)

    # Accumulate product prod_{m=M}^{1} R(-theta_m) B_m(omega_k) R(theta_m)
    # Vectorized over all N_spec slices simultaneously.
    prod = np.zeros((n_spec, 2, 2), dtype=np.complex128)
    prod[:, 0, 0] = 1.0
    prod[:, 1, 1] = 1.0

    for theta in thetas:
        c_t = math.cos(theta)
        s_t = math.sin(theta)
        c2 = c_t * c_t
        s2 = s_t * s_t
        cs = c_t * s_t

        # M_seg = R(-theta) B R(theta)
        # where R(theta) = [[c, s], [-s, c]], R(-theta) = [[c, -s], [s, c]]
        m00 = c2 * exp_x + s2 * exp_y
        m01 = cs * (exp_x - exp_y)
        m10 = m01
        m11 = s2 * exp_x + c2 * exp_y

        # Left-multiply: prod_new = M_seg @ prod
        p00 = m00 * prod[:, 0, 0] + m01 * prod[:, 1, 0]
        p01 = m00 * prod[:, 0, 1] + m01 * prod[:, 1, 1]
        p10 = m10 * prod[:, 0, 0] + m11 * prod[:, 1, 0]
        p11 = m10 * prod[:, 0, 1] + m11 * prod[:, 1, 1]
        prod[:, 0, 0] = p00
        prod[:, 0, 1] = p01
        prod[:, 1, 0] = p10
        prod[:, 1, 1] = p11

    # Sandwich with polarizer: J_CW = J_pol @ prod @ J_pol
    j_cw = np.einsum("ij,njk,kl->nil", j_pol, prod, j_pol)
    # Reciprocity: J_CCW(omega_k) = J_CW(omega_k)^T
    j_ccw = np.transpose(j_cw, (0, 2, 1)).copy()
    return j_cw, j_ccw, thetas


def extract_visibility_and_pol_phase(
    j_cw: np.ndarray,
    j_ccw: np.ndarray,
    weights: np.ndarray,
    e_in: np.ndarray | None = None,
) -> tuple[float, float, float, float]:
    """Extract fringe visibility V and polarization bias phase phi_pol (EQ-05).

    Evaluates static interference:
        P_static(Delta_phi) = sum_k w_k || E_CW(omega_k) e^{-j Delta_phi/2}
                                         + E_CCW(omega_k) e^{+j Delta_phi/2} ||^2
                            = A_0 + 2 |C| cos(Delta_phi - arg(C))
    where:
        V = (P_max - P_min) / (P_max + P_min) = 2 |C| / A_0
        phi_pol = argmin_{Delta_phi} P_static(Delta_phi) - pi = arg(C)
    """
    if e_in is None:
        # Realistic slight elliptical launch misalignment (3 deg) at MIOC splice
        # so first-order amplitude-type polarization error (~eps_pol * sqrt(h*L)) is captured
        # while vanishing identically when h = 0 (ideal PM coil).
        psi = 0.05
        e_in = np.array([math.cos(psi), 1j * math.sin(psi)], dtype=np.complex128)

    e_cw = np.einsum("nij,j->ni", j_cw, e_in)
    e_ccw = np.einsum("nij,j->ni", j_ccw, e_in)

    norm_cw_sq = np.sum(np.abs(e_cw) ** 2, axis=1)
    norm_ccw_sq = np.sum(np.abs(e_ccw) ** 2, axis=1)
    cross = np.sum(np.conj(e_cw) * e_ccw, axis=1)

    a0 = float(np.sum(weights * (norm_cw_sq + norm_ccw_sq)))
    c_tot = complex(np.sum(weights * cross))
    c_mag = abs(c_tot)

    p_max = a0 + 2.0 * c_mag
    p_min = max(0.0, a0 - 2.0 * c_mag)
    visibility = (p_max - p_min) / (p_max + p_min)
    phi_pol = float(math.atan2(c_tot.imag, c_tot.real))
    return visibility, phi_pol, p_max, p_min


def evaluate_static_interference(
    j_cw: np.ndarray,
    j_ccw: np.ndarray,
    weights: np.ndarray,
    delta_phi_grid: np.ndarray,
    e_in: np.ndarray | None = None,
) -> np.ndarray:
    """Evaluate P_static(Delta_phi) directly across a phase grid per EQ-05."""
    if e_in is None:
        psi = 0.05
        e_in = np.array([math.cos(psi), 1j * math.sin(psi)], dtype=np.complex128)
    e_cw = np.einsum("nij,j->ni", j_cw, e_in)
    e_ccw = np.einsum("nij,j->ni", j_ccw, e_in)

    phase_cw = np.exp(-0.5j * delta_phi_grid)[:, None, None]
    phase_ccw = np.exp(0.5j * delta_phi_grid)[:, None, None]
    e_sum = e_cw[None, :, :] * phase_cw + e_ccw[None, :, :] * phase_ccw
    intensity = np.sum(np.abs(e_sum) ** 2, axis=2)
    return np.einsum("gn,n->g", intensity, weights)


def solve_tier1_optics(cfg: dict[str, Any]) -> dict[str, Any]:
    """Run full Tier 1 optical preprocessing and return phys_params dictionary."""
    opt = cfg["optics"]
    seed = int(cfg["meta"]["seed"])

    omega_k, weights, delta_nu_eff = build_spectral_slices(
        lambda_bar_m=float(opt["lambda_bar_m"]),
        delta_lambda_fwhm_m=float(opt["delta_lambda_fwhm_m"]),
        n_spec=int(opt["n_spec"]),
    )
    j_cw, j_ccw, _ = compute_jones_matrices(
        omega_k=omega_k,
        lambda_bar_m=float(opt["lambda_bar_m"]),
        n_eff=float(opt["n_eff"]),
        L_m=float(opt["L_m"]),
        beat_length_m=float(opt["beat_length_m"]),
        h_param_inv_m=float(opt["h_param_inv_m"]),
        er_dB=float(opt["er_dB"]),
        m_segments=int(opt["m_segments"]),
        seed=seed,
    )
    visibility, phi_pol, p_max, p_min = extract_visibility_and_pol_phase(
        j_cw, j_ccw, weights
    )
    k_opt = compute_k_opt(float(opt["L_m"]), float(opt["D_m"]), float(opt["lambda_bar_m"]))
    tau_s = compute_tau(float(opt["L_m"]), float(opt["n_eff"]))
    delta_phi_kerr = compute_kerr_phase(
        n2_m2_per_W=float(opt["n2_m2_per_W"]),
        L_eff_m=float(opt["L_eff_m"]),
        lambda_bar_m=float(opt["lambda_bar_m"]),
        A_eff_m2=float(opt["A_eff_m2"]),
        kappa_split=float(opt["kappa_split"]),
        P_coil_W=float(opt["P_coil_W"]),
        eta_coh=float(opt["eta_coh"]),
    )

    sp7 = get_spec007_physics(cfg)
    l_coherence_m = C_LIGHT / delta_nu_eff
    sigma_phi_back = (
        compute_backscatter_sigma_rad(
            R_facet_dB=float(sp7["R_facet_dB"]),
            alpha_R_per_m=float(sp7["alpha_R_per_m"]),
            S_capture=float(sp7["S_capture"]),
            delta_nu_eff_Hz=delta_nu_eff,
        )
        if sp7["en_spec007_physics"]
        else 0.0
    )

    return {
        "spec_id": str(cfg["meta"].get("spec_id", "IFOG-SIM-SPEC-004")),
        "seed": seed,
        "visibility_V": visibility,
        "phi_pol_rad": phi_pol,
        "P_static_max": p_max,
        "P_static_min": p_min,
        "K_opt_rad_per_rad_s": k_opt,
        "tau_s": tau_s,
        "f_eigen_Hz": 1.0 / (2.0 * tau_s),
        "delta_nu_eff_Hz": delta_nu_eff,
        "L_coherence_m": l_coherence_m,
        "sigma_phi_back_rad": sigma_phi_back,
        "delta_phi_kerr_rad": delta_phi_kerr,
        "n_spec": int(opt["n_spec"]),
        "m_segments": int(opt["m_segments"]),
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Tier 1 spectral-sliced Jones optical solver."""
    parser = argparse.ArgumentParser(
        description="Tier 1 Spectral-Sliced Jones Optical Solver (IFOG-SIM-SPEC-004)"
    )
    parser.add_argument("--cfg", required=True, help="Path to IFOG config JSON (schema v4)")
    parser.add_argument("--out", required=True, help="Output run directory for phys_params.json")
    args = parser.parse_args(argv)

    cfg = load_config(args.cfg)
    phys_params = solve_tier1_optics(cfg)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phys_params.json"
    with out_file.open("w", encoding="utf-8") as fh:
        json.dump(phys_params, fh, indent=2)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
