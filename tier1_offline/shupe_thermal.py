"""Tier 1 Offline Thermal-Mechanical Solver: Shupe, Discrete Winding, Stress-Optic & LUT v2.

Implements:
  - EQ-09 (SPEC-004): Thermal Shupe integral Delta_phi_Shupe(t)
  - EQ-45 (SPEC-007 §2.1a): Discrete turn-by-turn quadrupole/octupole winding map (r_i, z_ax_i, delta_z_quad)
  - EQ-46 (SPEC-007 §2.1b): Elasto-optic thermo-mechanical stress integral Delta_phi_stress(t)
                            and total Delta_phi_therm(t) = Delta_phi_Shupe(t) + Delta_phi_stress(t)
  - EQ-47 (SPEC-007 §2.2a): Dynamic Sagnac scale factor K_opt(t) / K_opt,0
  - EQ-48 (SPEC-007 §2.2b): Time-varying visibility V_eff(t), polarization bias phi_pol(t), and V_pi(t)
  - EQ-49 (SPEC-007 §2.3):  Binary LUT format v2 (24 B header + 56 B <7d records) with v1 fallback

CLI Contract (IFOG-SIM-SPEC-004/007):
    python3 tier1_offline/shupe_thermal.py --cfg configs/baseline_1km_spec007.json --out data/run01/
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import struct
from pathlib import Path
from typing import Any

import numpy as np
from scipy.interpolate import RBFInterpolator
from scipy.linalg import solve_banded

from tier1_offline.config_loader import (
    C_LIGHT,
    RAD_S_TO_DEG_H,
    compute_k_opt,
    get_spec007_physics,
    load_config,
)

SHUPE_LUT_MAGIC = b"SHUP"
SHUPE_LUT_VERSION = 1
SHUPE_LUT_VERSION_V2 = 2
SHUPE_HEADER_STRUCT = struct.Struct("<4sIQd")  # magic, version, n_samples, dt_s (24 bytes)
SHUPE_RECORD_STRUCT = struct.Struct("<dd")  # v1: t_s, delta_phi_shupe_rad (16 bytes)
SHUPE_RECORD_V2_STRUCT = struct.Struct("<7d")  # v2: 7 float64 channels (56 bytes)


def build_winding_map(
    L_m: float,
    D_m: float,
    coil_thickness_m: float,
    n_turns: int,
    n_layers: int,
    winding_pattern: str = "quadrupole",
    flange_offset_m: float = 0.0,
    delta_z_quad_m: float = 0.0,
) -> dict[str, np.ndarray]:
    """Map discrete fiber turns i in {0..N_turns-1} to physical (r_i, z_ax_i, delta_z_quad) (EQ-45).

    Supports ``"quadrupole"`` (4-layer repeating ABBA symmetric block: layers [k, k+1, k+1, k])
    and ``"octupole"`` (8-layer doubly-balanced ABBA-BAAB block, cancelling both linear and
    quadratic radial temperature gradients across the coil stack). End-flange layer transitions
    introduce bounded geometric offsets ``flange_offset_m``.
    """
    if winding_pattern not in ("quadrupole", "octupole"):
        raise ValueError(f"Unsupported winding_pattern: {winding_pattern}")
    if n_turns < 4 or n_layers < 2 or n_turns < n_layers:
        raise ValueError(f"Invalid coil winding dimensions: n_turns={n_turns}, n_layers={n_layers}")

    idx = np.arange(n_turns, dtype=np.float64)
    z_m = (idx + 0.5) * (L_m / float(n_turns))
    half = n_turns // 2
    turns_per_layer = max(1, n_turns // n_layers)

    # Layer assignment from midpoint outward using quadrupole (4-layer) or octupole (8-layer) parity
    r_inner = 0.5 * D_m - 0.5 * coil_thickness_m
    dr_layer = coil_thickness_m / float(max(1, n_layers - 1))
    coil_height = max(coil_thickness_m, 0.02)

    layer_idx = np.zeros(n_turns, dtype=np.int64)
    z_ax = np.zeros(n_turns, dtype=np.float64)
    flange_err = np.zeros(n_turns, dtype=np.float64)

    for i in range(n_turns):
        # Distance in turns from coil midpoint (0 .. half)
        d_mid = abs(i - (half - 0.5))
        side = 1 if i >= half else 0  # 0 = CCW half [0, L/2), 1 = CW half [L/2, L]
        layer_pair = min(n_layers // 2 - 1, int(d_mid // max(1, turns_per_layer)))
        turn_in_layer = int(d_mid) % max(1, turns_per_layer)
        frac_ax = (turn_in_layer + 0.5) / float(max(1, turns_per_layer))

        if winding_pattern == "quadrupole":
            # ABBA parity per 2-layer pair: even pair (side 0->inner, 1->outer), odd pair flipped
            parity = (layer_pair % 2) ^ side
            lay = min(n_layers - 1, 2 * layer_pair + parity)
            # Small systematic residual from single-order pair asymmetry
            pair_sign = 1.0 if (layer_pair % 2 == 0) else -1.0
            flange_err[i] = flange_offset_m * pair_sign * (0.5 if side == 1 else -0.5)
        else:
            # Octupole (ABBA-BAAB): flips parity every 4 layers (cancels quadratic gradient)
            quad_block = (layer_pair // 2) % 2
            parity = ((layer_pair % 2) ^ quad_block) ^ side
            lay = min(n_layers - 1, 2 * layer_pair + parity)
            # Doubly-balanced octupole reduces flange asymmetry by factor of 4
            oct_sign = 1.0 if ((layer_pair + quad_block) % 2 == 0) else -1.0
            flange_err[i] = 0.25 * flange_offset_m * oct_sign * (0.5 if side == 1 else -0.5)

        layer_idx[i] = lay
        z_ax[i] = coil_height * (frac_ax if (layer_pair % 2 == 0) else (1.0 - frac_ax))

    r_m = r_inner + layer_idx.astype(np.float64) * dr_layer
    # Spatial asymmetry residual combining winding symmetry & configured delta_z_quad_m
    sym_factor = 1.0 if winding_pattern == "quadrupole" else 0.25
    delta_z_quad = sym_factor * delta_z_quad_m * np.sin(2.0 * math.pi * z_m / L_m) + flange_err

    return {
        "z_m": z_m,
        "r_m": r_m,
        "z_ax_m": z_ax,
        "layer_idx": layer_idx,
        "delta_z_quad_m": delta_z_quad,
    }


def shupe_integral(
    z_m: np.ndarray,
    dT_dt_K_per_s: np.ndarray,
    L_m: float,
    lambda_bar_m: float,
    n_eff: float,
    dn_dT_per_K: float,
    alpha_T_per_K: float,
    delta_z_quad_m: np.ndarray | float = 0.0,
) -> float:
    """Compute exact Shupe thermal phase shift Delta_phi_Shupe [rad] (EQ-09).

    Supports both scalar and spatially varying quadrupole/octupole residual delta_z_quad(z).
    """
    prefactor = (2.0 * math.pi / (lambda_bar_m * C_LIGHT)) * (dn_dT_per_K + n_eff * alpha_T_per_K)
    kernel = (L_m - 2.0 * z_m) + delta_z_quad_m
    integrand = dT_dt_K_per_s * kernel
    return float(prefactor * np.trapezoid(integrand, z_m))


def elasto_optic_stress_integral(
    z_m: np.ndarray,
    dsigma_dt_Pa_per_s: np.ndarray,
    L_m: float,
    lambda_bar_m: float,
    C_eo_per_Pa: float,
    delta_z_quad_m: np.ndarray | float = 0.0,
) -> float:
    """Compute thermo-mechanical elasto-optic stress phase shift Delta_phi_stress [rad] (EQ-46)."""
    if C_eo_per_Pa == 0.0:
        return 0.0
    prefactor = (2.0 * math.pi / (lambda_bar_m * C_LIGHT)) * C_eo_per_Pa
    kernel = (L_m - 2.0 * z_m) + delta_z_quad_m
    return float(prefactor * np.trapezoid(dsigma_dt_Pa_per_s * kernel, z_m))


def compute_dynamic_k_opt_rel(
    dT_coil_K: np.ndarray | float,
    dT_sld_K: np.ndarray | float,
    alpha_bobbin_ppm_K: float,
    alpha_lambda_pm_K: float,
    lambda_bar_m: float,
    kappa_back_m_per_W: float,
    P_back_W: np.ndarray | float,
    n_eff: float,
    dn_dT_per_K: float,
) -> np.ndarray | float:
    """Compute dynamic relative Sagnac scale factor K_opt(t) / K_opt,0 (EQ-47)."""
    alpha_bobbin = alpha_bobbin_ppm_K * 1.0e-6
    alpha_lambda = alpha_lambda_pm_K * 1.0e-12
    term_bobbin = alpha_bobbin * dT_coil_K
    term_lambda = (alpha_lambda * dT_sld_K + kappa_back_m_per_W * P_back_W) / lambda_bar_m
    term_neff = (dn_dT_per_K / n_eff) * dT_coil_K
    return 1.0 + term_bobbin - term_lambda + term_neff


def compute_dynamic_optical_params(
    V_eff_0: float,
    phi_pol_0: float,
    V_pi_0: float,
    dT_coil_K: np.ndarray | float,
    dT_mioc_K: np.ndarray | float,
    beta_V_per_K: float,
    gamma_pol_rad_per_K: float,
    alpha_vpi_ppm_K: float,
) -> tuple[np.ndarray | float, np.ndarray | float, np.ndarray | float]:
    """Compute time-varying (V_eff(t), phi_pol(t), V_pi(t)) per EQ-48."""
    v_eff_t = np.clip(V_eff_0 * (1.0 - beta_V_per_K * np.abs(dT_coil_K)), 1.0e-3, 1.0)
    phi_pol_t = phi_pol_0 + gamma_pol_rad_per_K * dT_coil_K
    v_pi_t = V_pi_0 * (1.0 + (alpha_vpi_ppm_K * 1.0e-6) * dT_mioc_K)
    return v_eff_t, phi_pol_t, v_pi_t


def solve_1d_heat_diffusion(
    n_z: int,
    coil_thickness_m: float,
    diffusivity_m2_per_s: float,
    duration_s: float,
    dt_s: float,
    boundary_ramp_K_per_s: float,
    boundary_asymmetry_K_per_s: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Solve 1D radial heat diffusion dT/dt = D * d^2T/dx^2 via Crank-Nicolson.

    Returns:
        t_grid: shape (N_t,) timestamps [s]
        x_norm: shape (n_z,) normalized coordinate in [0, 1] across coil radial stack
        dT_dt: shape (N_t, n_z) local temperature rate of change [K/s]
    """
    n_steps = max(2, int(round(duration_s / dt_s)) + 1)
    t_grid = np.linspace(0.0, dt_s * (n_steps - 1), n_steps)
    x_norm = np.linspace(0.0, 1.0, n_z)
    dx = coil_thickness_m / float(n_z - 1)
    r = diffusivity_m2_per_s * dt_s / (2.0 * dx * dx)

    # Interior nodes: 1 .. n_z - 2
    n_int = n_z - 2
    ab = np.zeros((3, n_int), dtype=np.float64)
    ab[0, 1:] = -r
    ab[1, :] = 1.0 + 2.0 * r
    ab[2, :-1] = -r

    temp = np.zeros((n_steps, n_z), dtype=np.float64)
    rate_left = boundary_ramp_K_per_s
    rate_right = boundary_ramp_K_per_s + boundary_asymmetry_K_per_s

    for i in range(n_steps - 1):
        t_next = t_grid[i + 1]
        t_curr = t_grid[i]
        left_next = rate_left * t_next
        right_next = rate_right * t_next

        u = temp[i, :]
        rhs = (1.0 - 2.0 * r) * u[1:-1] + r * (u[:-2] + u[2:])
        rhs[0] += r * left_next
        rhs[-1] += r * right_next

        temp[i + 1, 0] = left_next
        temp[i + 1, -1] = right_next
        temp[i + 1, 1:-1] = solve_banded((1, 1), ab, rhs)

    # Compute dT/dt with second-order finite differences along time
    dT_dt = np.gradient(temp, dt_s, axis=0)
    return t_grid, x_norm, dT_dt


def load_fem_dT_dt_csv(csv_path: Path | str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Import external FEM temperature-rate table from CSV (columns: t_s, z_m, dT_dt_K_per_s)."""
    rows: list[tuple[float, float, float]] = []
    with Path(csv_path).open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append((float(row["t_s"]), float(row["z_m"]), float(row["dT_dt_K_per_s"])))

    t_vals = sorted({r[0] for r in rows})
    z_vals = sorted({r[1] for r in rows})
    t_idx = {t: i for i, t in enumerate(t_vals)}
    z_idx = {z: j for j, z in enumerate(z_vals)}

    dT_dt = np.zeros((len(t_vals), len(z_vals)), dtype=np.float64)
    for t_val, z_val, rate in rows:
        dT_dt[t_idx[t_val], z_idx[z_val]] = rate
    return np.array(t_vals, dtype=np.float64), np.array(z_vals, dtype=np.float64), dT_dt


def write_shupe_lut(out_path: Path | str, t_s: np.ndarray, delta_phi_rad: np.ndarray) -> None:
    """Write legacy v1 binary shupe_lut.bin lookup table (24 B header + 16 B <2d records)."""
    n_samples = int(len(t_s))
    dt_s = float(t_s[1] - t_s[0]) if n_samples > 1 else 0.0
    with Path(out_path).open("wb") as fh:
        fh.write(SHUPE_HEADER_STRUCT.pack(SHUPE_LUT_MAGIC, SHUPE_LUT_VERSION, n_samples, dt_s))
        for t_val, phi_val in zip(t_s, delta_phi_rad):
            fh.write(SHUPE_RECORD_STRUCT.pack(float(t_val), float(phi_val)))


def write_shupe_lut_v2(
    out_path: Path | str,
    t_s: np.ndarray,
    delta_phi_shupe_rad: np.ndarray,
    delta_phi_stress_rad: np.ndarray,
    visibility_V_t: np.ndarray,
    phi_pol_rad_t: np.ndarray,
    v_pi_V_t: np.ndarray,
    k_opt_scale_rel_t: np.ndarray,
) -> None:
    """Write SPEC-007 binary shupe_lut.bin v2 table (24 B header + 56 B <7d records, EQ-49)."""
    n_samples = int(len(t_s))
    dt_s = float(t_s[1] - t_s[0]) if n_samples > 1 else 0.0
    with Path(out_path).open("wb") as fh:
        fh.write(SHUPE_HEADER_STRUCT.pack(SHUPE_LUT_MAGIC, SHUPE_LUT_VERSION_V2, n_samples, dt_s))
        for i in range(n_samples):
            fh.write(
                SHUPE_RECORD_V2_STRUCT.pack(
                    float(t_s[i]),
                    float(delta_phi_shupe_rad[i]),
                    float(delta_phi_stress_rad[i]),
                    float(visibility_V_t[i]),
                    float(phi_pol_rad_t[i]),
                    float(v_pi_V_t[i]),
                    float(k_opt_scale_rel_t[i]),
                )
            )


def read_shupe_lut_v2(lut_path: Path | str) -> dict[str, Any]:
    """Read binary shupe_lut.bin (v1 or v2) into a normalized 7-column dictionary (EQ-49)."""
    with Path(lut_path).open("rb") as fh:
        header_bytes = fh.read(SHUPE_HEADER_STRUCT.size)
        if len(header_bytes) < SHUPE_HEADER_STRUCT.size:
            raise ValueError(f"Truncated shupe_lut.bin header in: {lut_path}")
        magic, version, n_samples, dt_s = SHUPE_HEADER_STRUCT.unpack(header_bytes)
        if magic != SHUPE_LUT_MAGIC or version not in (SHUPE_LUT_VERSION, SHUPE_LUT_VERSION_V2):
            raise ValueError(f"Invalid shupe_lut.bin header: magic={magic!r}, version={version}")
        if version == SHUPE_LUT_VERSION:
            raw = fh.read(n_samples * SHUPE_RECORD_STRUCT.size)
            arr = np.frombuffer(raw, dtype="<f8").reshape((n_samples, 2))
            zeros = np.zeros(n_samples, dtype=np.float64)
            ones = np.ones(n_samples, dtype=np.float64)
            return {
                "version": 1,
                "dt_s": float(dt_s),
                "t_s": arr[:, 0].copy(),
                "delta_phi_shupe_rad": arr[:, 1].copy(),
                "delta_phi_stress_rad": zeros,
                "visibility_V_t": ones.copy(),
                "phi_pol_rad_t": zeros.copy(),
                "v_pi_V_t": zeros.copy(),
                "k_opt_scale_rel_t": ones,
            }
        raw = fh.read(n_samples * SHUPE_RECORD_V2_STRUCT.size)
        arr = np.frombuffer(raw, dtype="<f8").reshape((n_samples, 7))
        return {
            "version": 2,
            "dt_s": float(dt_s),
            "t_s": arr[:, 0].copy(),
            "delta_phi_shupe_rad": arr[:, 1].copy(),
            "delta_phi_stress_rad": arr[:, 2].copy(),
            "visibility_V_t": arr[:, 3].copy(),
            "phi_pol_rad_t": arr[:, 4].copy(),
            "v_pi_V_t": arr[:, 5].copy(),
            "k_opt_scale_rel_t": arr[:, 6].copy(),
        }


def read_shupe_lut(lut_path: Path | str) -> tuple[np.ndarray, np.ndarray, float]:
    """Read binary shupe_lut.bin (v1 or v2) -> (t_s, total_delta_phi_therm_rad, dt_s)."""
    lut = read_shupe_lut_v2(lut_path)
    total_phi = lut["delta_phi_shupe_rad"] + lut["delta_phi_stress_rad"]
    return lut["t_s"], total_phi, float(lut["dt_s"])


def solve_tier1_shupe(cfg: dict[str, Any]) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Solve thermal Shupe drift over the configured horizon and return (t_s, delta_phi, summary)."""
    opt = cfg["optics"]
    th = cfg["thermal"]
    L_m = float(opt["L_m"])
    lambda_bar_m = float(opt["lambda_bar_m"])
    n_eff = float(opt["n_eff"])
    k_opt = compute_k_opt(L_m, float(opt["D_m"]), lambda_bar_m)

    fem_path = th.get("fem_csv_path")
    if fem_path:
        t_grid, z_m, dT_dt = load_fem_dT_dt_csv(fem_path)
        source_mode = "fem_csv"
    else:
        t_grid, x_norm, dT_dt = solve_1d_heat_diffusion(
            n_z=int(th["n_z"]),
            coil_thickness_m=float(th["coil_thickness_m"]),
            diffusivity_m2_per_s=float(th["diffusivity_m2_per_s"]),
            duration_s=float(th["duration_s"]),
            dt_s=float(th["dt_s"]),
            boundary_ramp_K_per_s=float(th["boundary_ramp_K_per_s"]),
            boundary_asymmetry_K_per_s=float(th.get("boundary_asymmetry_K_per_s", 0.0)),
        )
        z_m = x_norm * L_m
        source_mode = "1d_diffusion"

    # Quadrupole winding asymmetry perturbation delta_z_quad(z)
    delta_z_quad = float(th["delta_z_quad_m"]) * np.sin(2.0 * math.pi * z_m / L_m)
    delta_phi = np.array(
        [
            shupe_integral(
                z_m=z_m,
                dT_dt_K_per_s=dT_dt[i, :],
                L_m=L_m,
                lambda_bar_m=lambda_bar_m,
                n_eff=n_eff,
                dn_dT_per_K=float(th["dn_dT_per_K"]),
                alpha_T_per_K=float(th["alpha_T_per_K"]),
                delta_z_quad_m=delta_z_quad,
            )
            for i in range(len(t_grid))
        ],
        dtype=np.float64,
    )

    omega_shupe_deg_h = (delta_phi / k_opt) * RAD_S_TO_DEG_H
    summary = {
        "spec_id": "IFOG-SIM-SPEC-004",
        "source_mode": source_mode,
        "n_samples": int(len(t_grid)),
        "duration_s": float(t_grid[-1] - t_grid[0]),
        "max_abs_delta_phi_rad": float(np.max(np.abs(delta_phi))),
        "max_abs_omega_shupe_deg_per_h": float(np.max(np.abs(omega_shupe_deg_h))),
        "final_delta_phi_rad": float(delta_phi[-1]),
    }
    return t_grid, delta_phi, summary


def solve_tier1_shupe_v2(
    cfg: dict[str, Any],
    phys_params: dict[str, Any] | None = None,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Solve SPEC-007 thermo-mechanical Shupe + elasto-optic stress + dynamic optical LUT v2."""
    opt = cfg["optics"]
    th = cfg["thermal"]
    mioc = cfg["mioc"]
    sp7 = get_spec007_physics(cfg)

    L_m = float(opt["L_m"])
    D_m = float(opt["D_m"])
    lambda_bar_m = float(opt["lambda_bar_m"])
    n_eff = float(opt["n_eff"])
    k_opt = compute_k_opt(L_m, D_m, lambda_bar_m)

    v_eff_0 = float(phys_params["visibility_V"]) if phys_params else 0.999
    phi_pol_0 = float(phys_params["phi_pol_rad"]) if phys_params else 0.0
    v_pi_0 = float(mioc["V_pi_0_V"])

    winding = build_winding_map(
        L_m=L_m,
        D_m=D_m,
        coil_thickness_m=float(th["coil_thickness_m"]),
        n_turns=int(sp7["n_turns"]),
        n_layers=int(sp7["n_layers"]),
        winding_pattern=str(sp7["winding_pattern"]),
        flange_offset_m=float(sp7["flange_offset_m"]),
        delta_z_quad_m=float(th["delta_z_quad_m"]),
    )

    fem_path = th.get("fem_csv_path")
    if fem_path:
        t_grid, z_fem, dT_dt_fem = load_fem_dT_dt_csv(fem_path)
        source_mode = "fem_csv"
        dT_dt_turns = np.array(
            [np.interp(winding["z_m"], z_fem, dT_dt_fem[i, :]) for i in range(len(t_grid))],
            dtype=np.float64,
        )
    else:
        t_grid, x_norm, dT_dt_rad = solve_1d_heat_diffusion(
            n_z=int(th["n_z"]),
            coil_thickness_m=float(th["coil_thickness_m"]),
            diffusivity_m2_per_s=float(th["diffusivity_m2_per_s"]),
            duration_s=float(th["duration_s"]),
            dt_s=float(th["dt_s"]),
            boundary_ramp_K_per_s=float(th["boundary_ramp_K_per_s"]),
            boundary_asymmetry_K_per_s=float(th.get("boundary_asymmetry_K_per_s", 0.0)),
        )
        source_mode = "1d_diffusion"
        # Map radial coordinate r_i of every discrete fiber turn onto normalized radial stack [0, 1]
        r_min = float(np.min(winding["r_m"]))
        r_span = max(float(np.max(winding["r_m"]) - r_min), 1.0e-12)
        r_norm = (winding["r_m"] - r_min) / r_span
        dT_dt_turns = np.array(
            [np.interp(r_norm, x_norm, dT_dt_rad[i, :]) for i in range(len(t_grid))],
            dtype=np.float64,
        )

    z_turns = winding["z_m"]
    dz_quad = winding["delta_z_quad_m"]
    c_eo = float(sp7["C_eo_per_Pa"])
    stress_rate_per_K = float(sp7["stress_rate_Pa_per_K"])

    delta_phi_shupe = np.empty(len(t_grid), dtype=np.float64)
    delta_phi_stress = np.empty(len(t_grid), dtype=np.float64)
    for i in range(len(t_grid)):
        delta_phi_shupe[i] = shupe_integral(
            z_m=z_turns,
            dT_dt_K_per_s=dT_dt_turns[i, :],
            L_m=L_m,
            lambda_bar_m=lambda_bar_m,
            n_eff=n_eff,
            dn_dT_per_K=float(th["dn_dT_per_K"]),
            alpha_T_per_K=float(th["alpha_T_per_K"]),
            delta_z_quad_m=dz_quad,
        )
        dsigma_dt = stress_rate_per_K * dT_dt_turns[i, :]
        delta_phi_stress[i] = elasto_optic_stress_integral(
            z_m=z_turns,
            dsigma_dt_Pa_per_s=dsigma_dt,
            L_m=L_m,
            lambda_bar_m=lambda_bar_m,
            C_eo_per_Pa=c_eo,
            delta_z_quad_m=dz_quad,
        )

    # Mean coil temperature change Delta_T_coil(t) integrated from mean dT/dt
    mean_dT_dt = np.mean(dT_dt_turns, axis=1)
    dt_arr = np.diff(t_grid, prepend=t_grid[0])
    dT_coil = np.cumsum(mean_dT_dt * dt_arr)
    dT_sld = float(sp7["delta_T_sld_ratio"]) * dT_coil
    dT_mioc = float(sp7["delta_T_mioc_ratio"]) * dT_coil

    k_opt_rel = np.asarray(
        compute_dynamic_k_opt_rel(
            dT_coil_K=dT_coil,
            dT_sld_K=dT_sld,
            alpha_bobbin_ppm_K=float(sp7["alpha_bobbin_ppm_K"]),
            alpha_lambda_pm_K=float(sp7["alpha_lambda_pm_K"]),
            lambda_bar_m=lambda_bar_m,
            kappa_back_m_per_W=float(sp7["kappa_back_m_per_W"]),
            P_back_W=float(sp7["P_back_W"]),
            n_eff=n_eff,
            dn_dT_per_K=float(th["dn_dT_per_K"]),
        ),
        dtype=np.float64,
    )
    v_eff_t, phi_pol_t, v_pi_t = compute_dynamic_optical_params(
        V_eff_0=v_eff_0,
        phi_pol_0=phi_pol_0,
        V_pi_0=v_pi_0,
        dT_coil_K=dT_coil,
        dT_mioc_K=dT_mioc,
        beta_V_per_K=float(sp7["beta_V_per_K"]),
        gamma_pol_rad_per_K=float(sp7["gamma_pol_rad_per_K"]),
        alpha_vpi_ppm_K=float(sp7["alpha_vpi_ppm_K"]),
    )

    delta_phi_tot = delta_phi_shupe + delta_phi_stress
    omega_therm_deg_h = (delta_phi_tot / k_opt) * RAD_S_TO_DEG_H
    channels = {
        "t_s": t_grid,
        "delta_phi_shupe_rad": delta_phi_shupe,
        "delta_phi_stress_rad": delta_phi_stress,
        "visibility_V_t": np.asarray(v_eff_t, dtype=np.float64),
        "phi_pol_rad_t": np.asarray(phi_pol_t, dtype=np.float64),
        "v_pi_V_t": np.asarray(v_pi_t, dtype=np.float64),
        "k_opt_scale_rel_t": k_opt_rel,
        "dT_coil_K": dT_coil,
    }
    summary = {
        "spec_id": "IFOG-SIM-SPEC-007",
        "lut_version": 2,
        "source_mode": source_mode,
        "winding_pattern": str(sp7["winding_pattern"]),
        "n_turns": int(sp7["n_turns"]),
        "n_layers": int(sp7["n_layers"]),
        "n_samples": int(len(t_grid)),
        "duration_s": float(t_grid[-1] - t_grid[0]),
        "max_abs_delta_phi_shupe_rad": float(np.max(np.abs(delta_phi_shupe))),
        "max_abs_delta_phi_stress_rad": float(np.max(np.abs(delta_phi_stress))),
        "max_abs_delta_phi_rad": float(np.max(np.abs(delta_phi_tot))),
        "max_abs_omega_shupe_deg_per_h": float(np.max(np.abs(omega_therm_deg_h))),
        "final_delta_phi_rad": float(delta_phi_tot[-1]),
        "k_opt_rel_drift_ppm": float((k_opt_rel[-1] - 1.0) * 1.0e6),
        "v_pi_final_V": float(np.asarray(v_pi_t)[-1]),
    }
    return channels, summary


FEM_3D_REQUIRED_COLUMNS = ("t_s", "r_m", "theta_rad", "z_ax_m", "T_K", "sigma_eff_Pa")


def load_fem_3d_csv(csv_path: Path | str) -> dict[str, Any]:
    """Import 3D ANSYS/COMSOL cylindrical thermo-mechanical FEM export CSV (v4.1.0 IND-03).

    Expected header: ``t_s,r_m,theta_rad,z_ax_m,T_K,sigma_eff_Pa``
    Supports unstructured cylindrical nodal grids across arbitrary timestamps.
    """
    path = Path(csv_path)
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or any(c not in reader.fieldnames for c in FEM_3D_REQUIRED_COLUMNS):
            raise ValueError(
                f"3D FEM CSV {path} missing required columns {FEM_3D_REQUIRED_COLUMNS}"
            )
        rows = [
            (
                float(r["t_s"]),
                float(r["r_m"]),
                float(r["theta_rad"]),
                float(r["z_ax_m"]),
                float(r["T_K"]),
                float(r["sigma_eff_Pa"]),
            )
            for r in reader
        ]

    t_vals = sorted({r[0] for r in rows})
    if len(t_vals) < 2:
        raise ValueError(f"3D FEM CSV {path} requires at least 2 timestamps, got {len(t_vals)}")
    node_keys = sorted({(r[1], r[2], r[3]) for r in rows})
    t_idx = {t: i for i, t in enumerate(t_vals)}
    n_idx = {k: j for j, k in enumerate(node_keys)}

    T_K = np.zeros((len(t_vals), len(node_keys)), dtype=np.float64)
    sigma_Pa = np.zeros((len(t_vals), len(node_keys)), dtype=np.float64)
    for t_v, r_v, th_v, z_v, temp_v, sig_v in rows:
        ti = t_idx[t_v]
        ni = n_idx[(r_v, th_v, z_v)]
        T_K[ti, ni] = temp_v
        sigma_Pa[ti, ni] = sig_v

    t_arr = np.array(t_vals, dtype=np.float64)
    r_arr = np.array([k[0] for k in node_keys], dtype=np.float64)
    th_arr = np.array([k[1] for k in node_keys], dtype=np.float64)
    z_arr = np.array([k[2] for k in node_keys], dtype=np.float64)
    dT_dt = np.gradient(T_K, t_arr, axis=0)
    dsigma_dt = np.gradient(sigma_Pa, t_arr, axis=0)
    return {
        "t_s": t_arr,
        "r_m": r_arr,
        "theta_rad": th_arr,
        "z_ax_m": z_arr,
        "T_K": T_K,
        "sigma_eff_Pa": sigma_Pa,
        "dT_dt_K_per_s": dT_dt,
        "dsigma_dt_Pa_per_s": dsigma_dt,
    }


def generate_asymmetric_3d_fem_csv(
    out_csv: Path | str,
    D_m: float = 0.10,
    coil_thickness_m: float = 0.015,
    coil_height_m: float = 0.020,
    duration_s: float = 600.0,
    n_times: int = 25,
    n_r: int = 5,
    n_theta: int = 8,
    n_z_ax: int = 4,
    ambient_ramp_K_per_s: float = 5.0e-3,
    hotspot_delta_K_per_s: float = 3.5e-3,
    anisotropic_potting_Pa_per_K: float = 4.5e5,
) -> Path:
    """Generate an ANSYS/COMSOL-format 3D cylindrical nodal CSV with eccentric IMU housing hotspots.

    Models an off-center FPGA/PSU heat source at (r_outer, theta=0, z_ax=0), an opposing
    SLD TEC sink at (r_inner, theta=pi, z_ax=H), and anisotropic potting stress sigma_eff(r,theta,z,t).
    """
    out_path = Path(out_csv)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r_inner = 0.5 * D_m - 0.5 * coil_thickness_m
    r_outer = 0.5 * D_m + 0.5 * coil_thickness_m
    t_grid = np.linspace(0.0, duration_s, n_times)
    r_grid = np.linspace(r_inner, r_outer, n_r)
    th_grid = np.linspace(0.0, 2.0 * math.pi, n_theta, endpoint=False)
    z_grid = np.linspace(0.0, coil_height_m, n_z_ax)
    tau_diff = 90.0

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(FEM_3D_REQUIRED_COLUMNS)
        for t_val in t_grid:
            trans = 1.0 - math.exp(-t_val / tau_diff)
            for r_val in r_grid:
                r_norm = (r_val - r_inner) / max(r_outer - r_inner, 1.0e-12)
                for th_val in th_grid:
                    azim = math.cos(th_val)  # +1 at eccentric FPGA/PSU, -1 at opposing SLD TEC
                    for z_val in z_grid:
                        z_norm = z_val / max(coil_height_m, 1.0e-12)
                        # Radial + azimuthal + axial asymmetric thermal field
                        dT_base = ambient_ramp_K_per_s * t_val * (0.85 + 0.30 * r_norm * r_norm)
                        dT_ecc = (
                            hotspot_delta_K_per_s
                            * t_val
                            * trans
                            * (0.65 * r_norm + 0.35 * (1.0 - z_norm))
                            * (0.5 + 0.5 * azim)
                        )
                        T_K = 298.15 + dT_base + dT_ecc
                        # Anisotropic potting CTE mismatch stress (stronger at flanges & eccentric mount)
                        aniso_factor = 1.0 + 0.45 * abs(azim) + 0.35 * abs(2.0 * z_norm - 1.0)
                        sigma_Pa = anisotropic_potting_Pa_per_K * (dT_base + dT_ecc) * aniso_factor
                        writer.writerow(
                            [
                                f"{t_val:.6f}",
                                f"{r_val:.6f}",
                                f"{th_val:.6f}",
                                f"{z_val:.6f}",
                                f"{T_K:.6f}",
                                f"{sigma_Pa:.3f}",
                            ]
                        )
    return out_path


def solve_tier1_shupe_3d_fem(
    cfg: dict[str, Any],
    fem_3d_csv: Path | str,
    phys_params: dict[str, Any] | None = None,
    n_theta_per_turn: int = 8,
) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    """Map 3D ANSYS/COMSOL cylindrical FEM fields T(r,theta,z,t) & sigma(r,theta,z,t) to LUT v2.

    Projects every discrete fiber turn (r_i, theta_j, z_ax_i) onto the 3D FEM mesh via
    Cartesian k-NN inverse-distance interpolation, then integrates exact 3D Shupe + elasto-optic
    stress phase drift into the native 56-byte shupe_lut.bin v2 contract.
    """
    opt = cfg["optics"]
    th = cfg["thermal"]
    mioc = cfg["mioc"]
    sp7 = get_spec007_physics(cfg)

    L_m = float(opt["L_m"])
    D_m = float(opt["D_m"])
    lambda_bar_m = float(opt["lambda_bar_m"])
    n_eff = float(opt["n_eff"])
    k_opt = compute_k_opt(L_m, D_m, lambda_bar_m)

    v_eff_0 = float(phys_params["visibility_V"]) if phys_params else 0.999
    phi_pol_0 = float(phys_params["phi_pol_rad"]) if phys_params else 0.0
    v_pi_0 = float(mioc["V_pi_0_V"])

    fem = load_fem_3d_csv(fem_3d_csv)
    t_grid = fem["t_s"]
    winding = build_winding_map(
        L_m=L_m,
        D_m=D_m,
        coil_thickness_m=float(th["coil_thickness_m"]),
        n_turns=int(sp7["n_turns"]),
        n_layers=int(sp7["n_layers"]),
        winding_pattern=str(sp7["winding_pattern"]),
        flange_offset_m=float(sp7["flange_offset_m"]),
        delta_z_quad_m=float(th["delta_z_quad_m"]),
    )

    # Normalize cylindrical FEM coordinates so radial, azimuthal, and axial axes have balanced metric scale
    r_min = float(np.min(fem["r_m"]))
    r_span = max(float(np.max(fem["r_m"]) - r_min), 1.0e-9)
    z_min = float(np.min(fem["z_ax_m"]))
    z_span = max(float(np.max(fem["z_ax_m"]) - z_min), 1.0e-9)

    def _cyl_to_metric(r_v: np.ndarray, th_v: np.ndarray, z_v: np.ndarray) -> np.ndarray:
        r_n = (r_v - r_min) / r_span
        z_n = (z_v - z_min) / z_span
        return np.column_stack([r_n, 0.5 * np.cos(th_v), 0.5 * np.sin(th_v), z_n])

    fem_pts = _cyl_to_metric(fem["r_m"], fem["theta_rad"], fem["z_ax_m"])

    # Build 3D fiber path samples (n_turns * n_theta_per_turn) along the wound helix
    n_turns = len(winding["z_m"])
    theta_turn = np.linspace(0.0, 2.0 * math.pi, n_theta_per_turn, endpoint=False)
    r_rep = np.repeat(winding["r_m"], n_theta_per_turn)
    z_ax_rep = np.repeat(winding["z_ax_m"], n_theta_per_turn)
    th_rep = np.tile(theta_turn, n_turns)
    z_fiber = (np.arange(n_turns * n_theta_per_turn, dtype=np.float64) + 0.5) * (
        L_m / float(n_turns * n_theta_per_turn)
    )
    dz_quad_rep = np.repeat(winding["delta_z_quad_m"], n_theta_per_turn)

    query_pts = _cyl_to_metric(r_rep, th_rep, z_ax_rep)
    # Smooth linear RBF interpolation works on arbitrary unstructured ANSYS/COMSOL 3D meshes
    dT_dt_seg = RBFInterpolator(fem_pts, fem["dT_dt_K_per_s"].T, kernel="linear")(query_pts).T
    dsigma_dt_seg = RBFInterpolator(fem_pts, fem["dsigma_dt_Pa_per_s"].T, kernel="linear")(query_pts).T
    T_seg = RBFInterpolator(fem_pts, fem["T_K"].T, kernel="linear")(query_pts).T

    c_eo = float(sp7["C_eo_per_Pa"])
    delta_phi_shupe = np.empty(len(t_grid), dtype=np.float64)
    delta_phi_stress = np.empty(len(t_grid), dtype=np.float64)
    for i in range(len(t_grid)):
        delta_phi_shupe[i] = shupe_integral(
            z_m=z_fiber,
            dT_dt_K_per_s=dT_dt_seg[i, :],
            L_m=L_m,
            lambda_bar_m=lambda_bar_m,
            n_eff=n_eff,
            dn_dT_per_K=float(th["dn_dT_per_K"]),
            alpha_T_per_K=float(th["alpha_T_per_K"]),
            delta_z_quad_m=dz_quad_rep,
        )
        delta_phi_stress[i] = elasto_optic_stress_integral(
            z_m=z_fiber,
            dsigma_dt_Pa_per_s=dsigma_dt_seg[i, :],
            L_m=L_m,
            lambda_bar_m=lambda_bar_m,
            C_eo_per_Pa=c_eo,
            delta_z_quad_m=dz_quad_rep,
        )

    dT_coil = np.mean(T_seg - T_seg[0:1, :], axis=1)
    dT_sld = float(sp7["delta_T_sld_ratio"]) * dT_coil
    dT_mioc = float(sp7["delta_T_mioc_ratio"]) * dT_coil

    k_opt_rel = np.asarray(
        compute_dynamic_k_opt_rel(
            dT_coil_K=dT_coil,
            dT_sld_K=dT_sld,
            alpha_bobbin_ppm_K=float(sp7["alpha_bobbin_ppm_K"]),
            alpha_lambda_pm_K=float(sp7["alpha_lambda_pm_K"]),
            lambda_bar_m=lambda_bar_m,
            kappa_back_m_per_W=float(sp7["kappa_back_m_per_W"]),
            P_back_W=float(sp7["P_back_W"]),
            n_eff=n_eff,
            dn_dT_per_K=float(th["dn_dT_per_K"]),
        ),
        dtype=np.float64,
    )
    v_eff_t, phi_pol_t, v_pi_t = compute_dynamic_optical_params(
        V_eff_0=v_eff_0,
        phi_pol_0=phi_pol_0,
        V_pi_0=v_pi_0,
        dT_coil_K=dT_coil,
        dT_mioc_K=dT_mioc,
        beta_V_per_K=float(sp7["beta_V_per_K"]),
        gamma_pol_rad_per_K=float(sp7["gamma_pol_rad_per_K"]),
        alpha_vpi_ppm_K=float(sp7["alpha_vpi_ppm_K"]),
    )

    delta_phi_tot = delta_phi_shupe + delta_phi_stress
    omega_therm_deg_h = (delta_phi_tot / k_opt) * RAD_S_TO_DEG_H
    channels = {
        "t_s": t_grid,
        "delta_phi_shupe_rad": delta_phi_shupe,
        "delta_phi_stress_rad": delta_phi_stress,
        "visibility_V_t": np.asarray(v_eff_t, dtype=np.float64),
        "phi_pol_rad_t": np.asarray(phi_pol_t, dtype=np.float64),
        "v_pi_V_t": np.asarray(v_pi_t, dtype=np.float64),
        "k_opt_scale_rel_t": k_opt_rel,
        "dT_coil_K": dT_coil,
    }
    summary = {
        "spec_id": "IFOG-SIM-SPEC-007-FEM3D",
        "lut_version": 2,
        "source_mode": "fem_3d_csv",
        "winding_pattern": str(sp7["winding_pattern"]),
        "n_fem_nodes": int(len(fem_pts)),
        "n_fiber_segments": int(len(z_fiber)),
        "n_samples": int(len(t_grid)),
        "duration_s": float(t_grid[-1] - t_grid[0]),
        "max_spatial_dT_K": float(np.max(np.ptp(fem["T_K"], axis=1))),
        "max_stress_MPa": float(np.max(np.abs(fem["sigma_eff_Pa"])) * 1.0e-6),
        "max_abs_delta_phi_shupe_rad": float(np.max(np.abs(delta_phi_shupe))),
        "max_abs_delta_phi_stress_rad": float(np.max(np.abs(delta_phi_stress))),
        "max_abs_delta_phi_rad": float(np.max(np.abs(delta_phi_tot))),
        "max_abs_omega_shupe_deg_per_h": float(np.max(np.abs(omega_therm_deg_h))),
        "final_delta_phi_rad": float(delta_phi_tot[-1]),
        "k_opt_rel_drift_ppm": float((k_opt_rel[-1] - 1.0) * 1.0e6),
        "v_pi_final_V": float(np.asarray(v_pi_t)[-1]),
    }
    return channels, summary


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Tier 1 thermal Shupe / SPEC-007 thermo-mechanical solver."""
    parser = argparse.ArgumentParser(
        description="Tier 1 Thermal Shupe & SPEC-007 Thermo-Mechanical Solver"
    )
    parser.add_argument("--cfg", required=True, help="Path to IFOG config JSON (schema v4/v5/v6)")
    parser.add_argument("--out", required=True, help="Output run directory for shupe_lut.bin")
    parser.add_argument(
        "--lut-version",
        type=int,
        choices=(1, 2),
        default=None,
        help="Override binary LUT version (defaults to spec007_physics.lut_version or 1)",
    )
    parser.add_argument(
        "--fem-3d-csv",
        default=None,
        help="Optional 3D ANSYS/COMSOL cylindrical FEM CSV (t_s,r_m,theta_rad,z_ax_m,T_K,sigma_eff_Pa)",
    )
    args = parser.parse_args(argv)

    cfg = load_config(args.cfg)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    sp7 = get_spec007_physics(cfg)
    lut_ver = args.lut_version if args.lut_version is not None else int(sp7["lut_version"])

    if args.fem_3d_csv:
        phys_path = out_dir / "phys_params.json"
        phys = json.loads(phys_path.read_text(encoding="utf-8")) if phys_path.exists() else None
        ch, summary = solve_tier1_shupe_3d_fem(cfg, args.fem_3d_csv, phys_params=phys)
        write_shupe_lut_v2(
            out_dir / "shupe_lut.bin",
            ch["t_s"],
            ch["delta_phi_shupe_rad"],
            ch["delta_phi_stress_rad"],
            ch["visibility_V_t"],
            ch["phi_pol_rad_t"],
            ch["v_pi_V_t"],
            ch["k_opt_scale_rel_t"],
        )
    elif lut_ver == 2 or sp7["en_spec007_physics"]:
        phys_path = out_dir / "phys_params.json"
        phys = json.loads(phys_path.read_text(encoding="utf-8")) if phys_path.exists() else None
        ch, summary = solve_tier1_shupe_v2(cfg, phys_params=phys)
        write_shupe_lut_v2(
            out_dir / "shupe_lut.bin",
            ch["t_s"],
            ch["delta_phi_shupe_rad"],
            ch["delta_phi_stress_rad"],
            ch["visibility_V_t"],
            ch["phi_pol_rad_t"],
            ch["v_pi_V_t"],
            ch["k_opt_scale_rel_t"],
        )
    else:
        t_grid, delta_phi, summary = solve_tier1_shupe(cfg)
        write_shupe_lut(out_dir / "shupe_lut.bin", t_grid, delta_phi)

    with (out_dir / "shupe_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
