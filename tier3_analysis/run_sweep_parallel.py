"""Tier 3 Parallel Multi-Core Sweep Orchestrator (IFOG-SIM-SPEC-004 Section 5.1 & 5.2).

Coordinates parallel multi-process execution of the compiled Tier 2 SystemC-AMS
binary ``ifog_sim`` across slow rate ramp sweeps (Deadband & Bunny Ears, Gate 2)
and Monte Carlo ablation sweeps.

CLI Contract:
    python3 tier3_analysis/run_sweep_parallel.py --bin ./build/ifog_sim \
        --sweep configs/ablation_sweeps/ --out data/sweep01/
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from tier1_offline.config_loader import (
    DEG_S_TO_RAD_S,
    RAD_S_TO_DEG_S,
    deep_merge,
    load_config,
)
from tier1_offline.jones_spectral import solve_tier1_optics
from tier3_analysis.binary_io import read_sim_records


def _run_single_point(task: dict[str, Any]) -> dict[str, Any]:
    """Worker function: execute one ifog_sim point and extract steady-state output rate."""
    sim_bin = task["sim_bin"]
    phys_path = task["phys_path"]
    cfg = task["cfg"]
    point_dir = Path(task["point_dir"])
    point_dir.mkdir(parents=True, exist_ok=True)

    cfg_path = point_dir / "cfg.json"
    with cfg_path.open("w", encoding="utf-8") as fh:
        json.dump(cfg, fh, indent=2)

    subprocess.run(
        [
            str(sim_bin),
            "--phys",
            str(phys_path),
            "--cfg",
            str(cfg_path),
            "--out",
            str(point_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    rec = read_sim_records(point_dir / "sim_out.bin")
    omega_out = rec["omega_out"]
    # Average over the second half (steady state after closed-loop settling)
    half = len(omega_out) // 2
    mean_out_rad_s = float(omega_out[half:].mean())
    return {
        "label": task["label"],
        "index": task["index"],
        "omega_in_deg_per_s": float(task["omega_in_deg_per_s"]),
        "omega_out_deg_per_s": float(mean_out_rad_s * RAD_S_TO_DEG_S),
        "omega_out_rad_per_s": mean_out_rad_s,
    }


def run_slow_rate_ramp_sweep(
    sim_bin: Path | str,
    sweep_spec: dict[str, Any],
    out_dir: Path | str,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Execute uncompensated vs compensated Slow Rate Ramp sweep across CPU cores."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    base_cfg = load_config(sweep_spec["base_config"])
    phys_params = solve_tier1_optics(base_cfg)
    phys_path = out_path / "phys_params.json"
    with phys_path.open("w", encoding="utf-8") as fh:
        json.dump(phys_params, fh, indent=2)

    rates_deg_s: list[float] = [float(r) for r in sweep_spec["rates_deg_per_s"]]
    dur_s = float(sweep_spec["duration_per_point_s"])
    dec_tau = int(sweep_spec["decimation_tau"])

    tasks: list[dict[str, Any]] = []
    for label, ov_key in [
        ("uncompensated", "uncompensated_overrides"),
        ("compensated", "compensated_overrides"),
    ]:
        base_variant = deep_merge(base_cfg, sweep_spec[ov_key])
        for idx, rate_deg_s in enumerate(rates_deg_s):
            point_cfg = deep_merge(
                base_variant,
                {
                    "simulation": {
                        "duration_s": dur_s,
                        "decimation_tau": dec_tau,
                        "dump_micro_ms": 0.0,
                        "stimulus": {
                            "type": "constant",
                            "omega_rad_per_s": rate_deg_s * DEG_S_TO_RAD_S,
                        },
                    }
                },
            )
            tasks.append(
                {
                    "sim_bin": str(sim_bin),
                    "phys_path": str(phys_path),
                    "cfg": point_cfg,
                    "point_dir": str(out_path / "points" / f"{label}_{idx:03d}"),
                    "label": label,
                    "index": idx,
                    "omega_in_deg_per_s": rate_deg_s,
                }
            )

    workers = max_workers or max(1, os.cpu_count() or 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_run_single_point, tasks))

    uncomp = sorted([r for r in results if r["label"] == "uncompensated"], key=lambda r: r["index"])
    comp = sorted([r for r in results if r["label"] == "compensated"], key=lambda r: r["index"])

    payload: dict[str, Any] = {
        "spec_id": "IFOG-SIM-SPEC-004",
        "sweep_name": sweep_spec["sweep_name"],
        "sweep_type": "slow_rate_ramp",
        "rates_in_deg_per_s": rates_deg_s,
        "uncompensated_out_deg_per_s": [r["omega_out_deg_per_s"] for r in uncomp],
        "compensated_out_deg_per_s": [r["omega_out_deg_per_s"] for r in comp],
    }

    with (out_path / "sweep_results.json").open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return payload


def run_monte_carlo_sweep(
    sim_bin: Path | str,
    sweep_spec: dict[str, Any],
    out_dir: Path | str,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Execute parallel Monte Carlo seed sweep across ablation scenarios."""
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    base_cfg = load_config(sweep_spec["base_config"])
    phys_params = solve_tier1_optics(base_cfg)
    phys_path = out_path / "phys_params.json"
    with phys_path.open("w", encoding="utf-8") as fh:
        json.dump(phys_params, fh, indent=2)

    dur_s = float(sweep_spec["duration_per_point_s"])
    dec_tau = int(sweep_spec["decimation_tau"])
    seeds = [int(s) for s in sweep_spec["seeds"]]

    tasks: list[dict[str, Any]] = []
    for scenario in sweep_spec["scenarios"]:
        sc_label = str(scenario["label"])
        sc_cfg = deep_merge(base_cfg, scenario["overrides"])
        for idx, seed in enumerate(seeds):
            pt_cfg = deep_merge(
                sc_cfg,
                {
                    "meta": {"seed": seed},
                    "simulation": {
                        "duration_s": dur_s,
                        "decimation_tau": dec_tau,
                        "dump_micro_ms": 0.0,
                    },
                },
            )
            tasks.append(
                {
                    "sim_bin": str(sim_bin),
                    "phys_path": str(phys_path),
                    "cfg": pt_cfg,
                    "point_dir": str(out_path / "mc" / f"{sc_label}_seed{seed}"),
                    "label": sc_label,
                    "index": idx,
                    "omega_in_deg_per_s": 0.0,
                }
            )

    workers = max_workers or max(1, os.cpu_count() or 1)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(_run_single_point, tasks))

    grouped: dict[str, list[float]] = {}
    for item in results:
        grouped.setdefault(item["label"], []).append(item["omega_out_deg_per_s"])

    payload = {
        "spec_id": "IFOG-SIM-SPEC-004",
        "sweep_name": sweep_spec["sweep_name"],
        "sweep_type": "monte_carlo",
        "seeds": seeds,
        "scenarios": grouped,
    }
    with (out_path / f"{sweep_spec['sweep_name']}_results.json").open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    return payload


def run_sweep_path(
    sim_bin: Path | str,
    sweep_path: Path | str,
    out_dir: Path | str,
    max_workers: int | None = None,
) -> list[dict[str, Any]]:
    """Run one sweep JSON file or all sweep JSON files inside a directory."""
    target = Path(sweep_path)
    files = sorted(target.glob("*.json")) if target.is_dir() else [target]
    outputs: list[dict[str, Any]] = []
    out_root = Path(out_dir)

    for fpath in files:
        with fpath.open("r", encoding="utf-8") as fh:
            spec = json.load(fh)
        sub_out = out_root if not target.is_dir() else (out_root / fpath.stem)
        if "rates_deg_per_s" in spec:
            outputs.append(run_slow_rate_ramp_sweep(sim_bin, spec, sub_out, max_workers=max_workers))
        else:
            outputs.append(run_monte_carlo_sweep(sim_bin, spec, sub_out, max_workers=max_workers))
    return outputs


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for parallel Tier 2 sweep execution."""
    parser = argparse.ArgumentParser(
        description="Parallel Multi-Core Tier 2 Sweep Orchestrator (IFOG-SIM-SPEC-004)"
    )
    parser.add_argument("--bin", required=True, help="Path to compiled ifog_sim binary")
    parser.add_argument("--sweep", required=True, help="Sweep JSON file or directory")
    parser.add_argument("--out", default="data/sweep_out", help="Output directory")
    parser.add_argument("--workers", type=int, default=None, help="Parallel worker count")
    args = parser.parse_args(argv)

    run_sweep_path(args.bin, args.sweep, args.out, max_workers=args.workers)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
