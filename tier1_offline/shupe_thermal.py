"""Tier 1 Offline Thermal-Mechanical Solver: 1D Diffusion / FEM Import & Shupe Integral (EQ-09).

Implements Shupe's thermal non-reciprocity integral (Shupe 1980, IFOG-SIM-SPEC-004 Section 3.1.2):
    Delta_phi_Shupe(t) = (2*pi / (lambda_bar * c)) * (dn_eff/dT + n_eff * alpha_T)
                         * integral_0^L (dT(z,t)/dt) * (L - 2*z + delta_z_quad(z)) dz

Outputs binary lookup table ``shupe_lut.bin`` and summary ``shupe_summary.json``.

CLI Contract (IFOG-SIM-SPEC-004 Section 5.2):
    python3 tier1_offline/shupe_thermal.py --cfg configs/baseline_1km.json --out data/run01/
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
from scipy.linalg import solve_banded

from tier1_offline.config_loader import C_LIGHT, RAD_S_TO_DEG_H, compute_k_opt, load_config

SHUPE_LUT_MAGIC = b"SHUP"
SHUPE_LUT_VERSION = 1
SHUPE_HEADER_STRUCT = struct.Struct("<4sIQd")  # magic, version, n_samples, dt_s (24 bytes)
SHUPE_RECORD_STRUCT = struct.Struct("<dd")  # t_s, delta_phi_shupe_rad (16 bytes)


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

    Supports both scalar and spatially varying quadrupole winding residual delta_z_quad(z).
    """
    prefactor = (2.0 * math.pi / (lambda_bar_m * C_LIGHT)) * (dn_dT_per_K + n_eff * alpha_T_per_K)
    kernel = (L_m - 2.0 * z_m) + delta_z_quad_m
    integrand = dT_dt_K_per_s * kernel
    return float(prefactor * np.trapezoid(integrand, z_m))


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
        left_curr = rate_left * t_curr
        right_curr = rate_right * t_curr
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
    """Write binary shupe_lut.bin lookup table."""
    n_samples = int(len(t_s))
    dt_s = float(t_s[1] - t_s[0]) if n_samples > 1 else 0.0
    with Path(out_path).open("wb") as fh:
        fh.write(SHUPE_HEADER_STRUCT.pack(SHUPE_LUT_MAGIC, SHUPE_LUT_VERSION, n_samples, dt_s))
        for t_val, phi_val in zip(t_s, delta_phi_rad):
            fh.write(SHUPE_RECORD_STRUCT.pack(float(t_val), float(phi_val)))


def read_shupe_lut(lut_path: Path | str) -> tuple[np.ndarray, np.ndarray, float]:
    """Read binary shupe_lut.bin lookup table -> (t_s, delta_phi_rad, dt_s)."""
    with Path(lut_path).open("rb") as fh:
        header_bytes = fh.read(SHUPE_HEADER_STRUCT.size)
        magic, version, n_samples, dt_s = SHUPE_HEADER_STRUCT.unpack(header_bytes)
        if magic != SHUPE_LUT_MAGIC or version != SHUPE_LUT_VERSION:
            raise ValueError(f"Invalid shupe_lut.bin header: magic={magic!r}, version={version}")
        raw = fh.read(n_samples * SHUPE_RECORD_STRUCT.size)
    arr = np.frombuffer(raw, dtype="<f8").reshape((n_samples, 2))
    return arr[:, 0].copy(), arr[:, 1].copy(), float(dt_s)


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


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for Tier 1 thermal Shupe solver."""
    parser = argparse.ArgumentParser(
        description="Tier 1 Thermal Shupe Solver (IFOG-SIM-SPEC-004)"
    )
    parser.add_argument("--cfg", required=True, help="Path to IFOG config JSON (schema v4)")
    parser.add_argument("--out", required=True, help="Output run directory for shupe_lut.bin")
    args = parser.parse_args(argv)

    cfg = load_config(args.cfg)
    t_grid, delta_phi, summary = solve_tier1_shupe(cfg)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_shupe_lut(out_dir / "shupe_lut.bin", t_grid, delta_phi)
    with (out_dir / "shupe_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
