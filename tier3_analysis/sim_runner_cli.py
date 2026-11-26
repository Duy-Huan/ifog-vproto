"""Unified End-to-End IFOG Simulation Runner with Automatic Report Generation in report/.

Orchestrates Tier 1 (Jones + Shupe) -> Tier 2 (SystemC-AMS C++ binary) -> Tier 3
(Nonlinearity, K-Matrix, Dual-Regime AVAR) -> Viz auto-export (report/<run_id>/{report.md, report.html}).
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import math
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from tier1_offline.config_loader import deep_merge, load_config
from tier1_offline.jones_spectral import solve_tier1_optics
from tier1_offline.shupe_thermal import solve_tier1_shupe, write_shupe_lut
from tier3_analysis.analyze_nonlinearity import analyze_sweep_nonlinearity
from tier3_analysis.binary_io import compute_welch_psd, fit_loglog_slope, read_sim_records
from tier3_analysis.dual_regime_avar import run_dual_regime_avar
from tier3_analysis.extract_k_matrix import extract_k_matrix
from tier3_analysis.run_sweep_parallel import run_slow_rate_ramp_sweep, run_sweep_path
from tier3_analysis.scenarios_dynamic_probe import (
    run_all_dynamic_probe_scenarios,
    run_dyn_freq_response,
    run_dyn_output_psd,
    run_dyn_sine_electro_optic,
    run_dyn_step_response,
)
from tier3_analysis.scenarios_engineering import (
    run_all_engineering_scenarios,
    run_eng_fault_bit,
    run_eng_hw_sizing,
    run_eng_imu_3axis,
    run_eng_mc_yield_cal,
    run_eng_vre_faraday,
)
from tier3_analysis.scenarios_time_domain import (
    run_all_time_domain_scenarios,
    run_dsp6_comparison,
    run_td_blanking,
    run_td_high_rate,
    run_td_limit_cycles,
    run_td_shupe_shock,
    run_td_step_sine,
    run_td_vpi_shock,
)
from viz.export_report import export_run_report

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CFG = REPO_ROOT / "configs" / "baseline_1km.json"
DEFAULT_SWEEP = REPO_ROOT / "configs" / "ablation_sweeps" / "slow_rate_ramp.json"
DEFAULT_BIN = REPO_ROOT / "build" / "ifog_sim"

ALL_MODES = (
    "single",
    "gate1",
    "gate2",
    "gate3",
    "gate4",
    "full",
    "sweep",
    "dsp6_compare",
    "td_blanking",
    "td_step_sine",
    "td_vpi_shock",
    "td_high_rate",
    "td_shupe_shock",
    "td_limit_cycles",
    "td_all",
    "eng_hw_sizing",
    "eng_imu_3axis",
    "eng_vre_faraday",
    "eng_fault_bit",
    "eng_mc_yield_cal",
    "eng_all",
    "dyn_step_response",
    "dyn_freq_response",
    "dyn_output_psd",
    "dyn_sine_electro_optic",
    "dyn_all",
    "all_scenarios",
)


def ensure_sim_binary(
    bin_path: Path | str,
    repo_root: Path = REPO_ROOT,
    auto_build: bool = False,
) -> Path:
    """Ensure the compiled Tier 2 C++ SystemC-AMS binary exists (optionally building via CMake)."""
    bpath = Path(bin_path)
    if bpath.exists():
        return bpath
    if not auto_build:
        raise FileNotFoundError(
            f"Tier 2 binary not found at {bpath}. Build it with: "
            "cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j"
        )
    build_dir = bpath.parent
    subprocess.run(
        ["cmake", "-S", str(repo_root / "tier2_sysc_ams"), "-B", str(build_dir), "-DCMAKE_BUILD_TYPE=Release"],
        check=True,
    )
    subprocess.run(["cmake", "--build", str(build_dir), "-j"], check=True)
    return bpath


def _run_tier1_stage(cfg: dict[str, Any], run_dir: Path) -> tuple[dict[str, Any], Path, Path]:
    """Execute Tier 1 offline optical (Jones) and thermal (Shupe) solvers into run_dir."""
    run_dir.mkdir(parents=True, exist_ok=True)
    phys = solve_tier1_optics(cfg)
    phys_path = run_dir / "phys_params.json"
    phys_path.write_text(json.dumps(phys, indent=2), encoding="utf-8")

    t_sh, phi_sh, shupe_summary = solve_tier1_shupe(cfg)
    shupe_path = run_dir / "shupe_lut.bin"
    write_shupe_lut(shupe_path, t_sh, phi_sh)
    (run_dir / "shupe_summary.json").write_text(json.dumps(shupe_summary, indent=2), encoding="utf-8")
    return phys, phys_path, shupe_path


def run_single_simulation(
    bin_path: Path,
    cfg: dict[str, Any],
    run_dir: Path,
    duration_s: float | None = None,
    dump_micro_ms: float | None = None,
) -> dict[str, Any]:
    """Execute a full Tier 1 -> Tier 2 single closed-loop simulation."""
    run_cfg = dict(cfg)
    sim_ov: dict[str, Any] = {}
    if duration_s is not None:
        sim_ov["duration_s"] = float(duration_s)
    if dump_micro_ms is not None:
        sim_ov["dump_micro_ms"] = float(dump_micro_ms)
    if sim_ov:
        run_cfg = deep_merge(run_cfg, {"simulation": sim_ov})

    _, phys_path, shupe_path = _run_tier1_stage(run_cfg, run_dir)
    cfg_path = run_dir / "cfg.json"
    cfg_path.write_text(json.dumps(run_cfg, indent=2), encoding="utf-8")

    cmd = [
        str(bin_path),
        "--phys",
        str(phys_path),
        "--cfg",
        str(cfg_path),
        "--out",
        str(run_dir),
    ]
    if run_cfg["ablation_flags"]["en_shupe"]:
        cmd.extend(["--shupe", str(shupe_path)])
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return json.loads((run_dir / "sim_summary.json").read_text(encoding="utf-8"))


def run_gate1_stage(bin_path: Path, base_cfg: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    """Execute Gate 1 (small-signal 1e-8 rad + continuous 2*pi flybacks + V_pi 2% tracking)."""
    run_dir.mkdir(parents=True, exist_ok=True)
    base = deep_merge(
        base_cfg,
        {
            "mioc": {"eps_vpi": 0.02, "gamma_nl_rad_per_V2": 0.0},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
            "dsp": {"mode": "4state", "en_vpi_loop": True, "en_adc_blanking": True, "en_prbs_dither": False},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": True,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
        },
    )
    phys = solve_tier1_optics(base)
    phys["visibility_V"] = 1.0
    phys["phi_pol_rad"] = 0.0
    phys["delta_phi_kerr_rad"] = 0.0
    g1_dir = run_dir / "gate1_work"
    g1_dir.mkdir(parents=True, exist_ok=True)
    phys_p = g1_dir / "phys_ideal.json"
    phys_p.write_text(json.dumps(phys, indent=2), encoding="utf-8")
    if not (run_dir / "phys_params.json").exists():
        (run_dir / "phys_params.json").write_text(json.dumps(phys, indent=2), encoding="utf-8")

    k_opt = phys["K_opt_rad_per_rad_s"]
    target_dphi = 1.0e-8
    cfg_small = deep_merge(
        base,
        {
            "simulation": {
                "duration_s": 0.025,
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {"type": "constant", "omega_rad_per_s": target_dphi / k_opt},
            }
        },
    )
    (g1_dir / "cfg_small.json").write_text(json.dumps(cfg_small), encoding="utf-8")
    subprocess.run(
        [str(bin_path), "--phys", str(phys_p), "--cfg", str(g1_dir / "cfg_small.json"), "--out", str(g1_dir / "small")],
        check=True,
        capture_output=True,
    )
    s_small = json.loads((g1_dir / "small" / "sim_summary.json").read_text(encoding="utf-8"))

    omega_big = 1.0
    cfg_big = deep_merge(
        base,
        {
            "simulation": {
                "duration_s": 0.04,
                "decimation_tau": 4,
                "dump_micro_ms": 0.1,
                "stimulus": {
                    "type": "step",
                    "omega_start_rad_per_s": 0.0,
                    "omega_end_rad_per_s": omega_big,
                    "step_time_s": 0.002,
                },
            }
        },
    )
    (g1_dir / "cfg_big.json").write_text(json.dumps(cfg_big), encoding="utf-8")
    subprocess.run(
        [str(bin_path), "--phys", str(phys_p), "--cfg", str(g1_dir / "cfg_big.json"), "--out", str(g1_dir / "big")],
        check=True,
        capture_output=True,
    )
    s_big = json.loads((g1_dir / "big" / "sim_summary.json").read_text(encoding="utf-8"))

    small_err = abs(float(s_small["final_delta_phi_step_rad"]) - target_dphi)
    big_err = abs(float(s_big["final_delta_phi_step_rad"]) - k_opt * omega_big)
    eps_vpi = max(abs(float(s_small["final_eps_vpi_eff"])), abs(float(s_big["final_eps_vpi_eff"])))
    flybacks = int(s_big["flyback_count"])
    gate1_metrics = {
        "small_signal_target_rad": target_dphi,
        "small_signal_err_rad": small_err,
        "large_step_err_rad": big_err,
        "flyback_count": flybacks,
        "final_eps_vpi_eff": eps_vpi,
        "gate1_pass": bool(small_err < 1.0e-9 and big_err < 1.0e-9 and flybacks > 1000 and eps_vpi < 1.0e-5),
    }
    (run_dir / "gate1_metrics.json").write_text(json.dumps(gate1_metrics, indent=2), encoding="utf-8")
    if not (run_dir / "sim_summary.json").exists():
        (run_dir / "sim_summary.json").write_bytes((g1_dir / "big" / "sim_summary.json").read_bytes())
        (run_dir / "micro_waveforms.bin").write_bytes((g1_dir / "big" / "micro_waveforms.bin").read_bytes())
    return gate1_metrics


def run_gate2_stage(
    bin_path: Path,
    cfg_path: Path,
    sweep_path: Path,
    run_dir: Path,
    workers: int | None = None,
) -> dict[str, Any]:
    """Execute Gate 2 Slow Rate Ramp sweep & Deadband / Bunny Ears nonlinearity evaluation."""
    run_dir.mkdir(parents=True, exist_ok=True)
    sweep_spec = json.loads(sweep_path.read_text(encoding="utf-8"))
    sweep_spec["base_config"] = str(cfg_path)
    sweep_res = run_slow_rate_ramp_sweep(bin_path, sweep_spec, run_dir, max_workers=workers)
    nl = analyze_sweep_nonlinearity(sweep_res)
    (run_dir / "nonlinearity_summary.json").write_text(json.dumps(nl, indent=2), encoding="utf-8")
    return nl


def run_gate3_stage(
    bin_path: Path,
    base_cfg: dict[str, Any],
    run_dir: Path,
    duration_s: float = 2.0,
    k_duration_s: float = 0.1,
) -> dict[str, Any]:
    """Execute Gate 3 1/f flicker linear vs nonlinear PSD & 100 Hz K-matrix repeatability."""
    run_dir.mkdir(parents=True, exist_ok=True)
    phys = solve_tier1_optics(base_cfg)
    phys_p = run_dir / "phys_params.json"
    if not phys_p.exists():
        phys_p.write_text(json.dumps(phys, indent=2), encoding="utf-8")

    g3_dir = run_dir / "gate3_work"
    g3_dir.mkdir(parents=True, exist_ok=True)

    cfg_lin = deep_merge(
        base_cfg,
        {
            "noise": {
                "en_white_noise": True,
                "en_pink_noise": True,
                "pink_f_min_Hz": 10.0,
                "pink_f_max_Hz": 5000.0,
                "sigma_pink_tia_V": 5.0e-3,
                "sigma_pink_dac_rel": 0.0,
                "sigma_pink_xtalk_rel": 0.0,
            },
            "dsp": {"en_prbs_dither": False, "en_vpi_loop": True},
            "ablation_flags": {
                "en_pol_error": False,
                "en_kerr": False,
                "en_shupe": False,
                "en_faraday": False,
                "en_mioc_vpi_err": False,
                "en_ram": False,
                "en_xtalk": False,
                "en_ltf_transient": False,
                "en_tia_poly_nl": False,
                "en_quantization": False,
            },
            "simulation": {"duration_s": float(duration_s), "decimation_tau": 4, "dump_micro_ms": 0.0},
        },
    )
    cfg_nl = deep_merge(
        cfg_lin,
        {
            "analog_frontend": {
                "C_xtalk_F": 0.0,
                "k_xtalk_A_per_V": 5.0e-6,
                "G2_per_V": 1.0e-2,
                "G3_per_V2": 2.0e-3,
            },
            "noise": {
                "sigma_pink_tia_V": 5.0e-4,
                "sigma_pink_dac_rel": 0.0,
                "sigma_pink_xtalk_rel": 0.35,
            },
            "ablation_flags": {"en_xtalk": True, "en_tia_poly_nl": True},
        },
    )

    for label, cfg_obj in (("lin", cfg_lin), ("nl", cfg_nl)):
        cf = g3_dir / f"cfg_{label}.json"
        cf.write_text(json.dumps(cfg_obj), encoding="utf-8")
        subprocess.run(
            [str(bin_path), "--phys", str(phys_p), "--cfg", str(cf), "--out", str(g3_dir / label)],
            check=True,
            capture_output=True,
        )

    (run_dir / "psd_linear.bin").write_bytes((g3_dir / "lin" / "sim_out.bin").read_bytes())
    (run_dir / "psd_nonlinear.bin").write_bytes((g3_dir / "nl" / "sim_out.bin").read_bytes())

    rec_lin = read_sim_records(run_dir / "psd_linear.bin")
    rec_nl = read_sim_records(run_dir / "psd_nonlinear.bin")
    dt = float(np.median(np.diff(rec_lin["t"])))
    n_pts = len(rec_lin["omega_out"])
    skip = min(500, n_pts // 10)
    nperseg = min(8192, n_pts - skip)
    f_lin, p_lin = compute_welch_psd(rec_lin["omega_out"][skip:], fs_Hz=1.0 / dt, nperseg=nperseg)
    f_nl, p_nl = compute_welch_psd(rec_nl["omega_out"][skip:], fs_Hz=1.0 / dt, nperseg=nperseg)
    slope_lin = fit_loglog_slope(f_lin, p_lin, 15.0, 1500.0)
    slope_nl = fit_loglog_slope(f_nl, p_nl, 15.0, 1500.0)

    k1 = extract_k_matrix(bin_path, base_cfg, phys_p, g3_dir / "k1", freq_Hz=100.0, duration_s=k_duration_s)
    k2 = extract_k_matrix(bin_path, base_cfg, phys_p, g3_dir / "k2", freq_Hz=100.0, duration_s=k_duration_s)
    v1 = np.asarray(k1["K_physical_vector"], dtype=np.float64)
    v2 = np.asarray(k2["K_physical_vector"], dtype=np.float64)
    max_rel_pct = float(np.max(np.abs(v1 - v2) / np.maximum(np.abs(v1), 1.0e-15)) * 100.0)
    (run_dir / "k_matrix.json").write_text(json.dumps(k1, indent=2), encoding="utf-8")

    gate3_metrics = {
        "slope_linear": slope_lin,
        "slope_nonlinear": slope_nl,
        "k_repeatability_max_rel_pct": max_rel_pct,
        "K_physical_vector": k1["K_physical_vector"],
        "gate3_pass": bool(abs(slope_lin) < 0.25 and (-1.25 <= slope_nl <= -0.75) and max_rel_pct < 2.0),
    }
    (run_dir / "gate3_metrics.json").write_text(json.dumps(gate3_metrics, indent=2), encoding="utf-8")
    return gate3_metrics


def run_gate4_stage(
    bin_path: Path,
    base_cfg: dict[str, Any],
    run_dir: Path,
    fast_duration_s: float = 60.0,
    fast_ensemble: int = 4,
    slow_ensemble: int = 12,
    slow_duration_hours: float | None = None,
    k_duration_s: float = 0.1,
    workers: int | None = None,
) -> dict[str, Any]:
    """Execute Gate 4 Dual-Regime Fast-Scale + 10 h Slow-Scale Overlapping AVAR & 5-region WLS."""
    cfg_g4 = dict(base_cfg)
    if slow_duration_hours is not None:
        cfg_g4 = deep_merge(cfg_g4, {"slow_scale": {"duration_hours": float(slow_duration_hours)}})

    _, phys_p, _ = _run_tier1_stage(cfg_g4, run_dir)
    (run_dir / "cfg.json").write_text(json.dumps(cfg_g4, indent=2), encoding="utf-8")

    def _run_fast_seed(idx: int) -> Path:
        seed_cfg = deep_merge(
            cfg_g4,
            {
                "meta": {"seed": int(cfg_g4["meta"]["seed"]) + idx * 1009},
                "simulation": {
                    "duration_s": float(fast_duration_s),
                    "decimation_tau": 4,
                    "dump_micro_ms": 0.2 if idx == 0 else 0.0,
                },
            },
        )
        sub_dir = run_dir / f"fast_seed_{idx}"
        sub_dir.mkdir(parents=True, exist_ok=True)
        cf = sub_dir / "cfg.json"
        cf.write_text(json.dumps(seed_cfg), encoding="utf-8")
        subprocess.run(
            [str(bin_path), "--phys", str(phys_p), "--cfg", str(cf), "--out", str(sub_dir)],
            check=True,
            capture_output=True,
        )
        dst = run_dir / f"sim_out_{idx}.bin"
        dst.write_bytes((sub_dir / "sim_out.bin").read_bytes())
        if idx == 0:
            (run_dir / "sim_out.bin").write_bytes((sub_dir / "sim_out.bin").read_bytes())
            (run_dir / "sim_summary.json").write_bytes((sub_dir / "sim_summary.json").read_bytes())
            (run_dir / "micro_waveforms.bin").write_bytes((sub_dir / "micro_waveforms.bin").read_bytes())
        return dst

    max_w = workers if workers is not None else min(fast_ensemble, max(1, os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_w) as pool:
        list(pool.map(_run_fast_seed, range(fast_ensemble)))

    if not (run_dir / "k_matrix.json").exists():
        extract_k_matrix(bin_path, cfg_g4, phys_p, run_dir, freq_Hz=100.0, duration_s=k_duration_s)

    return run_dual_regime_avar(run_dir, cfg_path=run_dir / "cfg.json", slow_ensemble=slow_ensemble)


def run_simulation_workflow(
    mode: str,
    cfg_path: Path | str = DEFAULT_CFG,
    bin_path: Path | str = DEFAULT_BIN,
    data_root: Path | str = REPO_ROOT / "data",
    report_root: Path | str = REPO_ROOT / "report",
    run_id: str | None = None,
    sweep_path: Path | str = DEFAULT_SWEEP,
    duration_s: float | None = None,
    fast_duration_s: float = 60.0,
    fast_ensemble: int = 4,
    slow_ensemble: int = 12,
    slow_duration_hours: float | None = None,
    gate3_duration_s: float = 2.0,
    k_duration_s: float = 0.1,
    mc_runs: int = 64,
    dsp_mode: str | None = None,
    workers: int | None = None,
    auto_build: bool = False,
) -> dict[str, Any]:
    """Execute the requested IFOG simulation mode and auto-export .md and .html reports into report/."""
    if mode not in ALL_MODES:
        raise ValueError(f"Unsupported simulation mode '{mode}'. Choose from {list(ALL_MODES)}.")

    resolved_bin = ensure_sim_binary(bin_path, auto_build=auto_build)
    cfg_p = Path(cfg_path)
    cfg = load_config(cfg_p)
    if dsp_mode is not None:
        alpha_default = math.pi / 3.0 if dsp_mode == "6state" else math.pi / 4.0
        cfg = deep_merge(cfg, {"dsp": {"mode": dsp_mode, "alpha_rad": alpha_default}})

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    rid = run_id if run_id else f"{mode}_{stamp}"
    run_dir = Path(data_root) / rid
    report_dir = Path(report_root) / rid
    run_dir.mkdir(parents=True, exist_ok=True)

    if mode == "single":
        run_single_simulation(resolved_bin, cfg, run_dir, duration_s=duration_s)
    elif mode == "gate1":
        run_gate1_stage(resolved_bin, cfg, run_dir)
    elif mode == "gate2":
        run_gate2_stage(resolved_bin, cfg_p, Path(sweep_path), run_dir, workers=workers)
    elif mode == "gate3":
        run_gate3_stage(resolved_bin, cfg, run_dir, duration_s=gate3_duration_s, k_duration_s=k_duration_s)
    elif mode == "gate4":
        run_gate4_stage(
            resolved_bin,
            cfg,
            run_dir,
            fast_duration_s=fast_duration_s,
            fast_ensemble=fast_ensemble,
            slow_ensemble=slow_ensemble,
            slow_duration_hours=slow_duration_hours,
            k_duration_s=k_duration_s,
            workers=workers,
        )
    elif mode == "sweep":
        run_sweep_path(resolved_bin, Path(sweep_path), run_dir, max_workers=workers)
        sw_json = run_dir / "sweep_results.json"
        if sw_json.exists():
            nl = analyze_sweep_nonlinearity(json.loads(sw_json.read_text(encoding="utf-8")))
            (run_dir / "nonlinearity_summary.json").write_text(json.dumps(nl, indent=2), encoding="utf-8")
    elif mode == "dsp6_compare":
        run_dsp6_comparison(resolved_bin, cfg, run_dir)
    elif mode == "td_blanking":
        run_td_blanking(resolved_bin, cfg, run_dir)
    elif mode == "td_step_sine":
        run_td_step_sine(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "td_vpi_shock":
        run_td_vpi_shock(resolved_bin, cfg, run_dir)
    elif mode == "td_high_rate":
        run_td_high_rate(resolved_bin, cfg, run_dir)
    elif mode == "td_shupe_shock":
        run_td_shupe_shock(resolved_bin, cfg, run_dir)
    elif mode == "td_limit_cycles":
        run_td_limit_cycles(resolved_bin, cfg, run_dir)
    elif mode == "td_all":
        run_all_time_domain_scenarios(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "eng_hw_sizing":
        run_eng_hw_sizing(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "eng_imu_3axis":
        run_eng_imu_3axis(resolved_bin, cfg, run_dir)
    elif mode == "eng_vre_faraday":
        run_eng_vre_faraday(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "eng_fault_bit":
        run_eng_fault_bit(resolved_bin, cfg, run_dir)
    elif mode == "eng_mc_yield_cal":
        run_eng_mc_yield_cal(resolved_bin, cfg, run_dir, mc_runs=mc_runs, workers=workers)
    elif mode == "eng_all":
        run_all_engineering_scenarios(resolved_bin, cfg, run_dir, mc_runs=mc_runs, workers=workers)
    elif mode == "dyn_step_response":
        run_dyn_step_response(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "dyn_freq_response":
        run_dyn_freq_response(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "dyn_output_psd":
        run_dyn_output_psd(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "dyn_sine_electro_optic":
        run_dyn_sine_electro_optic(resolved_bin, cfg, run_dir)
    elif mode == "dyn_all":
        run_all_dynamic_probe_scenarios(resolved_bin, cfg, run_dir, workers=workers)
    elif mode == "full":
        run_gate1_stage(resolved_bin, cfg, run_dir)
        run_gate2_stage(resolved_bin, cfg_p, Path(sweep_path), run_dir, workers=workers)
        run_gate3_stage(resolved_bin, cfg, run_dir, duration_s=gate3_duration_s, k_duration_s=k_duration_s)
        run_gate4_stage(
            resolved_bin,
            cfg,
            run_dir,
            fast_duration_s=fast_duration_s,
            fast_ensemble=fast_ensemble,
            slow_ensemble=slow_ensemble,
            slow_duration_hours=slow_duration_hours,
            k_duration_s=k_duration_s,
            workers=workers,
        )
    else:  # all_scenarios
        run_gate1_stage(resolved_bin, cfg, run_dir)
        run_gate2_stage(resolved_bin, cfg_p, Path(sweep_path), run_dir, workers=workers)
        run_gate3_stage(resolved_bin, cfg, run_dir, duration_s=gate3_duration_s, k_duration_s=k_duration_s)
        run_gate4_stage(
            resolved_bin,
            cfg,
            run_dir,
            fast_duration_s=fast_duration_s,
            fast_ensemble=fast_ensemble,
            slow_ensemble=slow_ensemble,
            slow_duration_hours=slow_duration_hours,
            k_duration_s=k_duration_s,
            workers=workers,
        )
        run_dsp6_comparison(resolved_bin, cfg, run_dir)
        run_all_time_domain_scenarios(resolved_bin, cfg, run_dir, workers=workers)
        run_all_engineering_scenarios(resolved_bin, cfg, run_dir, mc_runs=mc_runs, workers=workers)
        run_all_dynamic_probe_scenarios(resolved_bin, cfg, run_dir, workers=workers)

    summary = export_run_report(
        run_dir,
        formats=("png", "md", "html"),
        report_dir=report_dir,
        run_meta={"run_id": rid, "mode": mode},
        update_index=True,
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for unified IFOG simulation & automatic report generation."""
    parser = argparse.ArgumentParser(
        description="IFOG-SIM-SPEC-005 Unified Simulation Runner (auto-generates report/<run_id>/{report.md, report.html})"
    )
    parser.add_argument(
        "--mode",
        default="single",
        choices=list(ALL_MODES),
        help="Simulation workflow mode (4-Gate, 6-State DSP, TD-01..06, ENG-01..05, or all_scenarios)",
    )
    parser.add_argument("--cfg", default=str(DEFAULT_CFG), help="Baseline config JSON")
    parser.add_argument("--sweep", default=str(DEFAULT_SWEEP), help="Sweep JSON or directory (for gate2/sweep/full)")
    parser.add_argument("--bin", default=str(DEFAULT_BIN), help="Path to compiled Tier 2 binary (build/ifog_sim)")
    parser.add_argument("--data-dir", default=str(REPO_ROOT / "data"), help="Root directory for raw simulation data")
    parser.add_argument("--report-dir", default=str(REPO_ROOT / "report"), help="Root directory for auto-generated .md/.html reports")
    parser.add_argument("--run-id", default=None, help="Explicit run identifier (defaults to <mode>_YYYYMMDD_HHMMSS)")
    parser.add_argument("--duration-s", type=float, default=None, help="Optional duration override for --mode single")
    parser.add_argument("--fast-duration-s", type=float, default=60.0, help="Fast-Scale duration for Gate 4 [s]")
    parser.add_argument("--fast-ensemble", type=int, default=4, help="Parallel Fast-Scale Monte Carlo runs for Gate 4")
    parser.add_argument("--slow-ensemble", type=int, default=12, help="Slow-Scale Monte Carlo runs for Gate 4")
    parser.add_argument("--slow-duration-hours", type=float, default=None, help="Optional Slow-Scale duration override [h]")
    parser.add_argument("--gate3-duration-s", type=float, default=2.0, help="Gate 3 PSD simulation duration [s]")
    parser.add_argument("--k-duration-s", type=float, default=0.1, help="K-matrix tone injection duration [s]")
    parser.add_argument("--mc-runs", type=int, default=64, help="Monte Carlo unit count for ENG-05 Yield (e.g., 64, 500, 1000)")
    parser.add_argument("--dsp-mode", choices=["2state", "4state", "6state"], default=None, help="Optional DSP mode override")
    parser.add_argument("--workers", type=int, default=None, help="Parallel worker count")
    parser.add_argument("--auto-build", action="store_true", help="Automatically build Tier 2 binary if missing")
    args = parser.parse_args(argv)

    summary = run_simulation_workflow(
        mode=args.mode,
        cfg_path=args.cfg,
        bin_path=args.bin,
        data_root=args.data_dir,
        report_root=args.report_dir,
        run_id=args.run_id,
        sweep_path=args.sweep,
        duration_s=args.duration_s,
        fast_duration_s=args.fast_duration_s,
        fast_ensemble=args.fast_ensemble,
        slow_ensemble=args.slow_ensemble,
        slow_duration_hours=args.slow_duration_hours,
        gate3_duration_s=args.gate3_duration_s,
        k_duration_s=args.k_duration_s,
        mc_runs=args.mc_runs,
        dsp_mode=args.dsp_mode,
        workers=args.workers,
        auto_build=args.auto_build,
    )
    rdir = Path(summary["report_dir"])
    n_figs = sum(1 for a in summary.get("generated_artifacts", []) if str(a).endswith(".png"))
    print(f"[IFOG-SIM] Completed mode={args.mode} status={summary['report_meta']['overall_status']}")
    print(f"[IFOG-SIM] Figures (300-DPI): {n_figs} plots in {rdir / 'figures'}")
    print(f"[IFOG-SIM] Markdown report:   {rdir / 'report.md'}")
    print(f"[IFOG-SIM] HTML report:       {rdir / 'report.html'}")
    print(f"[IFOG-SIM] Report index:      {rdir.parent / 'index.html'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
