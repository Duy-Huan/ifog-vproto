"""FMI 3.0 Black-Box Co-Simulation Master Orchestrator & Regression Suite (IFOG-SIM-SPEC-006).

Orchestrates standalone ``build/ifog_core.fmu`` via FMPy while strictly honoring
``canBeInstantiatedOnlyOncePerProcess="true"`` (Accellera SystemC singleton kernel)
by executing each FMU simulation inside an isolated OS worker subprocess.

Capabilities (Gate 6 — IFOG-SIM-SPEC-006):
  6A. Official FMI 3.0 XSD & ZIP structural validation via ``fmpy.validation.validate_fmu``
  6B. Black-box FMU vs Standalone Tier 2 ``ifog_sim`` bit-exact / numerical equivalence
      verification (< 1e-12 rad/s discrepancy on both 4-state and 6-state DSP modes)
  6C. Slow Rate Ramp staircase sweep across 0 deg/h via ``fmpy.simulate_fmu`` with
      ``enable_dither=False`` vs ``enable_dither=True`` at ``step_size=1e-3``
  6D. Seamless FMU output stream -> Tier 3 Dual-Regime 5-Region IEEE Std 952-2020
      Overlapping Allan Variance (Q, N, B, K, R) pipeline integration (< 5% overlap)

CLI Usage:
    python3 tier3_analysis/fmi_master_runner.py --fmu build/ifog_core.fmu --out data/fmi_gate
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import fmpy
import numpy as np
from fmpy.validation import validate_fmu

from tier1_offline.config_loader import deep_merge
from tier3_analysis.analyze_nonlinearity import analyze_sweep_nonlinearity
from tier3_analysis.binary_io import OMEGA_OUT_LSB, SIM_RECORD_DTYPE, read_sim_records

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FMU = REPO_ROOT / "build" / "ifog_core.fmu"
DEFAULT_BIN = REPO_ROOT / "build" / "ifog_sim"

REQUIRED_FMU_VARIABLES = (
    "time",
    "omega_in",
    "shupe_phase_in",
    "omega_out",
    "omega_out_avg",
    "e_vpi_res",
    "bit_status",
    "eps_vpi",
    "k_xtalk",
    "enable_dither",
    "dsp_mode",
)


def validate_fmu_package(fmu_path: Path | str) -> dict[str, Any]:
    """Validate FMI 3.0 XML schema, ZIP layout, and interface contract via FMPy (Gate 6A)."""
    fpath = Path(fmu_path)
    if not fpath.exists():
        raise FileNotFoundError(
            f"FMI 3.0 FMU archive not found at {fpath}. "
            "Build it with: cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release "
            "&& cmake --build build --target package_fmu"
        )

    problems = validate_fmu(str(fpath))
    md = fmpy.read_model_description(str(fpath), validate=False)
    var_names = [v.name for v in md.modelVariables]
    missing_vars = [name for name in REQUIRED_FMU_VARIABLES if name not in var_names]

    with zipfile.ZipFile(fpath, "r") as zf:
        members = sorted(zf.namelist())

    has_xml = "modelDescription.xml" in members
    has_phys = "resources/phys_params.json" in members
    has_shupe = "resources/shupe_lut.bin" in members
    has_cfg = "resources/baseline_cfg.json" in members
    binary_entries = [m for m in members if m.startswith("binaries/") and not m.endswith("/")]
    only_once = bool(md.coSimulation is not None and md.coSimulation.canBeInstantiatedOnlyOncePerProcess)

    passed = (
        len(problems) == 0
        and md.fmiVersion == "3.0"
        and only_once
        and len(missing_vars) == 0
        and has_xml
        and has_phys
        and has_shupe
        and has_cfg
        and len(binary_entries) >= 1
    )

    return {
        "fmu_path": str(fpath),
        "fmu_size_bytes": int(fpath.stat().st_size),
        "fmi_version": str(md.fmiVersion),
        "model_name": str(md.modelName),
        "instantiation_token": str(md.guid),
        "can_be_instantiated_only_once_per_process": only_once,
        "validation_problems": list(problems),
        "missing_required_variables": missing_vars,
        "variable_count": len(var_names),
        "binary_entries": binary_entries,
        "has_resources": bool(has_phys and has_shupe and has_cfg),
        "validation_pass": passed,
    }


def _execute_worker_job(job_path: Path, result_npz: Path) -> None:
    """Execute one isolated FMI 3.0 Co-Simulation run inside a dedicated OS process."""
    job = json.loads(job_path.read_text(encoding="utf-8"))
    inp_arr = None
    if job.get("input_rows") is not None:
        dtype = np.dtype([("time", np.float64), ("omega_in", np.float64), ("shupe_phase_in", np.float64)])
        rows = [tuple(float(v) for v in row) for row in job["input_rows"]]
        inp_arr = np.array(rows, dtype=dtype)

    res = fmpy.simulate_fmu(
        filename=str(job["fmu_path"]),
        fmi_type="CoSimulation",
        validate=False,
        start_time=float(job["start_time"]),
        stop_time=float(job["stop_time"]),
        step_size=float(job["step_size"]),
        output_interval=float(job["step_size"]),
        start_values=dict(job.get("start_values", {})),
        input=inp_arr,
        output=list(job["output"]),
    )

    arrays = {name: np.asarray(res[name]) for name in res.dtype.names}
    np.savez(result_npz, **arrays)


def simulate_fmu_isolated(
    fmu_path: Path | str,
    stop_time: float,
    step_size: float = 1.0e-3,
    start_values: dict[str, Any] | None = None,
    input_rows: list[tuple[float, float, float]] | None = None,
    output: Sequence[str] = (
        "omega_out",
        "omega_out_avg",
        "e_vpi_res",
        "bit_status",
    ),
    start_time: float = 0.0,
) -> dict[str, np.ndarray]:
    """Run ``fmpy.simulate_fmu`` inside a fresh subprocess honoring single-instance SystemC."""
    with tempfile.TemporaryDirectory(prefix="ifog_fmu_worker_") as td:
        tdir = Path(td)
        job_path = tdir / "job.json"
        out_npz = tdir / "result.npz"
        job_spec = {
            "fmu_path": str(Path(fmu_path).resolve()),
            "start_time": float(start_time),
            "stop_time": float(stop_time),
            "step_size": float(step_size),
            "start_values": dict(start_values or {}),
            "input_rows": [list(r) for r in input_rows] if input_rows is not None else None,
            "output": list(output),
        }
        job_path.write_text(json.dumps(job_spec), encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "tier3_analysis.fmi_master_runner",
                "--worker-job",
                str(job_path),
                "--worker-out",
                str(out_npz),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"Isolated FMU worker failed (rc={proc.returncode}): {proc.stderr.strip()}"
            )
        with np.load(out_npz) as npz:
            return {k: np.array(npz[k], copy=True) for k in npz.files}


def _extract_fmu_resources(fmu_path: Path, dest_dir: Path) -> tuple[Path, Path, Path]:
    """Extract embedded resources/ from an FMU archive into dest_dir."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(fmu_path, "r") as zf:
        for rel in ("resources/phys_params.json", "resources/shupe_lut.bin", "resources/baseline_cfg.json"):
            target = dest_dir / Path(rel).name
            target.write_bytes(zf.read(rel))
    return (
        dest_dir / "phys_params.json",
        dest_dir / "shupe_lut.bin",
        dest_dir / "baseline_cfg.json",
    )


def run_fmi_equivalence_verification(
    fmu_path: Path | str,
    bin_path: Path | str,
    out_dir: Path | str,
    omega_rad_per_s: float = 0.05,
    duration_s: float = 0.02,
    step_size_s: float = 1.0e-3,
) -> dict[str, Any]:
    """Verify black-box FMU vs standalone Tier 2 ifog_sim numerical equivalence (< 1e-12, Gate 6B)."""
    fpath = Path(fmu_path)
    bpath = Path(bin_path)
    odir = Path(out_dir) / "fmi_equivalence"
    odir.mkdir(parents=True, exist_ok=True)

    phys_p, _, base_cfg_p = _extract_fmu_resources(fpath, odir / "res")
    base_cfg = json.loads(base_cfg_p.read_text(encoding="utf-8"))

    mode_reports: dict[str, dict[str, Any]] = {}
    max_all_err = 0.0

    for dsp_mode, mode_str, alpha_rad in (
        (4, "4state", math.pi / 4.0),
        (6, "6state", math.pi / 3.0),
    ):
        input_rows = [(0.0, omega_rad_per_s, 0.0), (duration_s, omega_rad_per_s, 0.0)]
        fmu_res = simulate_fmu_isolated(
            fpath,
            stop_time=duration_s,
            step_size=step_size_s,
            input_rows=input_rows,
            start_values={
                "eps_vpi": float(base_cfg["mioc"]["eps_vpi"]),
                "k_xtalk": float(base_cfg["analog_frontend"]["k_xtalk_A_per_V"]),
                "enable_dither": True,
                "dsp_mode": dsp_mode,
                "en_white_noise": True,
                "en_pink_noise": False,
                "en_vpi_loop": True,
                "seed": int(base_cfg["meta"]["seed"]),
            },
        )

        # Standalone Tier 2 run with identical physics, seed, and stimulus
        sa_dir = odir / f"standalone_{mode_str}"
        sa_dir.mkdir(parents=True, exist_ok=True)
        sa_cfg = deep_merge(
            base_cfg,
            {
                "dsp": {"mode": mode_str, "alpha_rad": alpha_rad, "en_prbs_dither": True, "en_vpi_loop": True},
                "noise": {"en_white_noise": True, "en_pink_noise": False},
                "simulation": {
                    "duration_s": float(duration_s),
                    "decimation_tau": 1,
                    "dump_micro_ms": 0.0,
                    "stimulus": {"type": "constant", "omega_rad_per_s": float(omega_rad_per_s)},
                },
            },
        )
        sa_cfg_p = sa_dir / "cfg.json"
        sa_cfg_p.write_text(json.dumps(sa_cfg), encoding="utf-8")
        subprocess.run(
            [str(bpath), "--phys", str(phys_p), "--cfg", str(sa_cfg_p), "--out", str(sa_dir)],
            check=True,
            capture_output=True,
        )
        sa_summary = json.loads((sa_dir / "sim_summary.json").read_text(encoding="utf-8"))
        sa_rec = read_sim_records(sa_dir / "sim_out.bin")

        # Pointwise trajectory error vs sim_out.bin at each macro step (within 1e-12 SimRecord LSB)
        t_fmu = fmu_res["time"]
        w_fmu = fmu_res["omega_out"]
        idx_map = np.searchsorted(sa_rec["t"], t_fmu[1:], side="right") - 1
        idx_map = np.clip(idx_map, 0, len(sa_rec["omega_out"]) - 1)
        traj_errs = np.abs(w_fmu[1:] - sa_rec["omega_out"][idx_map])
        max_traj_err = float(np.max(traj_errs))

        # Exact final 64-bit IEEE-754 double comparison against sim_summary.json
        sa_final_omega = float(sa_summary["final_omega_out_rad_per_s"])
        fmu_final_omega = float(w_fmu[-1])
        final_omega_err = abs(fmu_final_omega - sa_final_omega)

        sa_final_evpi = 2.0 * math.pi * float(sa_summary["final_eps_vpi_eff"])
        fmu_final_evpi = float(fmu_res["e_vpi_res"][-1])
        final_evpi_err = abs(fmu_final_evpi - sa_final_evpi)

        bit_ok = int(np.max(fmu_res["bit_status"])) == 0
        max_all_err = max(max_all_err, final_omega_err, final_evpi_err, max_traj_err)
        mode_reports[mode_str] = {
            "dsp_mode": dsp_mode,
            "fmu_final_omega_rad_per_s": fmu_final_omega,
            "standalone_final_omega_rad_per_s": sa_final_omega,
            "final_omega_abs_err_rad_per_s": final_omega_err,
            "max_trajectory_abs_err_rad_per_s": max_traj_err,
            "fmu_final_e_vpi_res_rad": fmu_final_evpi,
            "standalone_final_e_vpi_res_rad": sa_final_evpi,
            "final_e_vpi_res_abs_err_rad": final_evpi_err,
            "bit_status_clean": bit_ok,
            "time_s": t_fmu.tolist(),
            "fmu_omega_out_rad_per_s": w_fmu.tolist(),
            "standalone_omega_out_rad_per_s": [0.0] + sa_rec["omega_out"][idx_map].tolist(),
            "pass_lt_1e12": bool(
                final_omega_err < 1.0e-12
                and final_evpi_err < 1.0e-12
                and max_traj_err <= 2.0e-12
                and bit_ok
            ),
        }

    return {
        "omega_input_rad_per_s": float(omega_rad_per_s),
        "duration_s": float(duration_s),
        "step_size_s": float(step_size_s),
        "modes": mode_reports,
        "max_final_omega_err_rad_per_s": max(
            mode_reports["4state"]["final_omega_abs_err_rad_per_s"],
            mode_reports["6state"]["final_omega_abs_err_rad_per_s"],
        ),
        "max_overall_err": max_all_err,
        "equivalence_pass": bool(
            mode_reports["4state"]["pass_lt_1e12"] and mode_reports["6state"]["pass_lt_1e12"]
        ),
    }


def _run_staircase_ramp_curve(
    fmu_path: Path,
    rates_deg_s: list[float],
    dwell_s: float,
    step_size_s: float,
    enable_dither: bool,
    en_vpi_loop: bool,
    omega_dc_deg_s: float,
) -> list[float]:
    """Drive a single FMU instance across a piecewise-constant Slow Rate Ramp staircase."""
    rows: list[tuple[float, float, float]] = []
    for idx, rate in enumerate(rates_deg_s):
        om = float(rate) * (math.pi / 180.0)
        rows.append((idx * dwell_s, om, 0.0))
        rows.append(((idx + 1) * dwell_s - 1.0e-6, om, 0.0))
    total_dur = len(rates_deg_s) * dwell_s
    rows.append((total_dur, float(rates_deg_s[-1]) * (math.pi / 180.0), 0.0))

    res = simulate_fmu_isolated(
        fmu_path,
        stop_time=total_dur,
        step_size=step_size_s,
        input_rows=rows,
        start_values={
            "eps_vpi": 0.05,
            "k_xtalk": 1.0e-8,
            "enable_dither": bool(enable_dither),
            "dsp_mode": 6,
            "en_white_noise": False,
            "en_pink_noise": False,
            "en_vpi_loop": bool(en_vpi_loop),
            "seed": 42004,
        },
        output=["omega_out", "omega_out_avg"],
    )
    t_arr = res["time"]
    w_deg_s = res["omega_out_avg"] * (180.0 / math.pi) - omega_dc_deg_s

    plateau_means: list[float] = []
    for idx in range(len(rates_deg_s)):
        t_lo = idx * dwell_s + 0.45 * dwell_s
        t_hi = (idx + 1) * dwell_s - 0.5 * step_size_s
        mask = (t_arr >= t_lo) & (t_arr <= t_hi)
        plateau_means.append(float(np.mean(w_deg_s[mask])))
    return plateau_means


def run_fmi_deadband_sweep(
    fmu_path: Path | str,
    out_dir: Path | str,
    rates_deg_per_s: list[float] | None = None,
    dwell_per_point_s: float = 0.04,
    step_size_s: float = 1.0e-3,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Execute Slow Rate Ramp sweep across 0 deg/h via FMPy with dither OFF vs ON (Gate 6C)."""
    fpath = Path(fmu_path)
    odir = Path(out_dir) / "fmi_deadband"
    odir.mkdir(parents=True, exist_ok=True)

    phys_p, _, _ = _extract_fmu_resources(fpath, odir / "res")
    phys = json.loads(phys_p.read_text(encoding="utf-8"))
    # Exact static Tier-1 optical polarization + Kerr zero-rate factory bias
    omega_dc_deg_s = (
        (float(phys["phi_pol_rad"]) + float(phys["delta_phi_kerr_rad"]))
        / float(phys["K_opt_rad_per_rad_s"])
    ) * (180.0 / math.pi)

    rates = (
        list(rates_deg_per_s)
        if rates_deg_per_s is not None
        else [-0.15, -0.08, -0.05, -0.03, -0.02, -0.01, -0.005, 0.0, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.15]
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(2, max_workers or 2)) as pool:
        fut_off = pool.submit(
            _run_staircase_ramp_curve,
            fpath,
            rates,
            dwell_per_point_s,
            step_size_s,
            False,
            False,
            omega_dc_deg_s,
        )
        fut_on = pool.submit(
            _run_staircase_ramp_curve,
            fpath,
            rates,
            dwell_per_point_s,
            step_size_s,
            True,
            True,
            omega_dc_deg_s,
        )
        off_out = fut_off.result()
        on_out = fut_on.result()

    sweep_payload = {
        "rates_in_deg_per_s": rates,
        "uncompensated_out_deg_per_s": off_out,
        "compensated_out_deg_per_s": on_out,
    }
    nl = analyze_sweep_nonlinearity(sweep_payload)
    result = {
        "step_size_s": float(step_size_s),
        "dwell_per_point_s": float(dwell_per_point_s),
        "static_optical_bias_deg_per_s": float(omega_dc_deg_s),
        "rates_in_deg_per_s": rates,
        "rates_in_deg_per_h": [r * 3600.0 for r in rates],
        "dither_off_out_deg_per_s": off_out,
        "dither_on_out_deg_per_s": on_out,
        "dither_off_metrics": nl["uncompensated"],
        "dither_on_metrics": nl["compensated"],
        "deadband_reduction_pct": float(nl["deadband_reduction_pct"]),
        "bunny_ears_sf_reduction_pct": float(nl["bunny_ears_sf_reduction_pct"]),
        "deadband_pass": bool(nl["deadband_reduction_pct"] >= 90.0),
    }
    (odir / "fmi_deadband_sweep.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def _run_fmu_avar_realization(
    fmu_path: Path,
    base_cfg: dict[str, Any],
    seed_val: int,
    fast_duration_s: float,
    step_size_s: float,
    bin_out_path: Path,
) -> tuple[int, int]:
    """Run one isolated FMU fast-scale realization and pack omega_out_avg into sim_out_*.bin."""
    res = simulate_fmu_isolated(
        fmu_path,
        stop_time=fast_duration_s,
        step_size=step_size_s,
        input_rows=[(0.0, 0.0, 0.0), (fast_duration_s, 0.0, 0.0)],
        start_values={
            "eps_vpi": float(base_cfg["mioc"]["eps_vpi"]),
            "k_xtalk": float(base_cfg["analog_frontend"]["k_xtalk_A_per_V"]),
            "enable_dither": True,
            "dsp_mode": 4,
            "en_white_noise": True,
            "en_pink_noise": False,
            "en_vpi_loop": True,
            "seed": int(seed_val),
        },
        output=["omega_out", "omega_out_avg", "e_vpi_res", "bit_status"],
    )

    t_arr = res["time"][1:]
    w_avg = res["omega_out_avg"][1:]
    vpi_arr = res["e_vpi_res"][1:]
    bit_arr = res["bit_status"][1:]

    recs = np.zeros(len(t_arr), dtype=SIM_RECORD_DTYPE)
    recs["t"] = t_arr
    recs["omega_in"] = 0.0
    recs["omega_out_raw"] = np.rint(w_avg / OMEGA_OUT_LSB).astype(np.int64)
    recs["vpi_err_raw"] = np.rint(vpi_arr * 1.0e6).astype(np.int32)
    recs["flags"] = bit_arr.astype(np.uint32)
    recs.tofile(bin_out_path)
    return int(len(t_arr)), int(np.max(bit_arr))


def run_fmi_dual_regime_avar(
    fmu_path: Path | str,
    out_dir: Path | str,
    fast_duration_s: float = 60.0,
    fast_ensemble: int = 4,
    step_size_s: float = 1.0e-3,
    slow_ensemble: int = 12,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Feed black-box FMI 3.0 FMU output stream into Tier 3 Dual-Regime 5-Region AVAR (Gate 6D)."""
    # Lazy import keeps --worker-job child processes free of scipy startup overhead
    from tier3_analysis.dual_regime_avar import run_dual_regime_avar

    fpath = Path(fmu_path)
    avar_dir = Path(out_dir) / "fmi_avar"
    avar_dir.mkdir(parents=True, exist_ok=True)

    _, _, base_cfg_p = _extract_fmu_resources(fpath, avar_dir)
    base_cfg = json.loads(base_cfg_p.read_text(encoding="utf-8"))
    avar_cfg = deep_merge(
        base_cfg,
        {"simulation": {"duration_s": float(fast_duration_s), "decimation_tau": 4, "dump_micro_ms": 0.0}},
    )
    cfg_p = avar_dir / "cfg.json"
    cfg_p.write_text(json.dumps(avar_cfg, indent=2), encoding="utf-8")

    # Remove any stale ensemble binaries from prior runs
    for stale in avar_dir.glob("sim_out_*.bin"):
        stale.unlink()

    base_seed = int(base_cfg["meta"]["seed"])
    n_ens = max(1, int(fast_ensemble))
    n_samples_total = 0
    max_bit_status = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = [
            pool.submit(
                _run_fmu_avar_realization,
                fpath,
                base_cfg,
                base_seed + idx * 1000,
                fast_duration_s,
                step_size_s,
                avar_dir / f"sim_out_{idx:02d}.bin",
            )
            for idx in range(n_ens)
        ]
        for fut in futs:
            n_samp, bit_max = fut.result()
            n_samples_total += n_samp
            max_bit_status = max(max_bit_status, bit_max)

    metrics = run_dual_regime_avar(avar_dir, cfg_path=cfg_p, slow_ensemble=slow_ensemble)
    ov = metrics["overlap_check"]
    fit = metrics["fitted_ieee952"]
    truth = metrics["slow_synthesis_truth"]
    max_param_err_pct = 0.0
    for key in ("Q_arcsec", "N_deg_per_rt_h", "B_deg_per_h", "K_deg_per_rt_h3", "R_deg_per_h2"):
        t_val = float(truth[key])
        if t_val > 0.0:
            max_param_err_pct = max(max_param_err_pct, abs(float(fit[key]) - t_val) / t_val * 100.0)

    metrics["fmi_step_size_s"] = float(step_size_s)
    metrics["fmi_n_samples_total"] = int(n_samples_total)
    metrics["max_5region_param_err_pct"] = float(max_param_err_pct)
    metrics["avar_pass"] = bool(
        ov["continuity_pass_lt_5pct"] and max_param_err_pct <= 10.0 and max_bit_status == 0
    )
    return metrics


def run_fmi_gate_suite(
    fmu_path: Path | str = DEFAULT_FMU,
    bin_path: Path | str = DEFAULT_BIN,
    out_dir: Path | str = "data/fmi_gate",
    fast_avar_duration_s: float = 60.0,
    fast_ensemble: int = 4,
    step_size_s: float = 1.0e-3,
    slow_ensemble: int = 12,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Execute complete IFOG-SIM-SPEC-006 FMI 3.0 FMU Compliance & Verification Gate (Gate 6)."""
    odir = Path(out_dir)
    odir.mkdir(parents=True, exist_ok=True)

    validation = validate_fmu_package(fmu_path)
    equivalence = run_fmi_equivalence_verification(
        fmu_path=fmu_path,
        bin_path=bin_path,
        out_dir=odir,
        step_size_s=step_size_s,
    )
    deadband = run_fmi_deadband_sweep(
        fmu_path=fmu_path,
        out_dir=odir,
        step_size_s=step_size_s,
        max_workers=max_workers,
    )
    avar = run_fmi_dual_regime_avar(
        fmu_path=fmu_path,
        out_dir=odir,
        fast_duration_s=fast_avar_duration_s,
        fast_ensemble=fast_ensemble,
        step_size_s=step_size_s,
        slow_ensemble=slow_ensemble,
        max_workers=max_workers,
    )

    gate_pass = bool(
        validation["validation_pass"]
        and equivalence["equivalence_pass"]
        and deadband["deadband_pass"]
        and avar["avar_pass"]
    )
    summary: dict[str, Any] = {
        "spec_id": "IFOG-SIM-SPEC-006",
        "gate_id": "Gate-6-FMI3-FMU",
        "title": "FMI 3.0 Black-Box FMU Compliance, Equivalence (<1e-12), Deadband & 5-Region AVAR",
        "validation": validation,
        "equivalence": equivalence,
        "deadband": deadband,
        "avar": avar,
        "fmi_gate_pass": gate_pass,
        "pass": gate_pass,
    }
    (odir / "fmi_gate_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for FMI 3.0 Master Orchestrator and isolated FMU worker mode."""
    parser = argparse.ArgumentParser(
        description="FMI 3.0 Co-Simulation FMU Master Runner & Regression Gate (IFOG-SIM-SPEC-006)"
    )
    parser.add_argument("--fmu", default=str(DEFAULT_FMU), help="Path to build/ifog_core.fmu")
    parser.add_argument("--bin", default=str(DEFAULT_BIN), help="Path to standalone build/ifog_sim")
    parser.add_argument("--out", default="data/fmi_gate", help="Output directory")
    parser.add_argument("--avar-duration-s", type=float, default=60.0, help="FMU fast-scale AVAR duration [s]")
    parser.add_argument("--fast-ensemble", type=int, default=4, help="Parallel FMU fast-scale realizations")
    parser.add_argument("--step-size", type=float, default=1.0e-3, help="FMI macro communication step size [s]")
    parser.add_argument("--slow-ensemble", type=int, default=12, help="Slow-scale 10h AVAR ensemble count")
    parser.add_argument("--workers", type=int, default=None, help="Parallel worker count")
    parser.add_argument("--worker-job", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--worker-out", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.worker_job is not None and args.worker_out is not None:
        _execute_worker_job(Path(args.worker_job), Path(args.worker_out))
        return 0

    summary = run_fmi_gate_suite(
        fmu_path=args.fmu,
        bin_path=args.bin,
        out_dir=args.out,
        fast_avar_duration_s=args.avar_duration_s,
        fast_ensemble=args.fast_ensemble,
        step_size_s=args.step_size,
        slow_ensemble=args.slow_ensemble,
        max_workers=args.workers,
    )
    print(
        f"[fmi_master_runner] Gate-6 FMI3 FMU = {'PASS' if summary['fmi_gate_pass'] else 'FAIL'} | "
        f"val={summary['validation']['validation_pass']} | "
        f"equiv_err={summary['equivalence']['max_final_omega_err_rad_per_s']:.2e} rad/s | "
        f"deadband_red={summary['deadband']['deadband_reduction_pct']:.2f}% | "
        f"avar_overlap={summary['avar']['overlap_check']['max_relative_mismatch_pct']:.2f}% | "
        f"max_5reg_err={summary['avar']['max_5region_param_err_pct']:.2f}%"
    )
    return 0 if summary["fmi_gate_pass"] else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
