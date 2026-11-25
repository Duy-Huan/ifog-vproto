"""Full-Scale Real System & 4-Gate Acceptance Test Suite (IFOG-SIM-SPEC-004 Section 5.2).

Strictly obeys AGENT.md Rule 5: 100% real full-duration simulations using the compiled
SystemC + SystemC-AMS PoC 2.3.4 binary (build/ifog_sim) — NO smoke tests or mocks.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import deep_merge, load_config
from tier1_offline.jones_spectral import solve_tier1_optics
from tier1_offline.shupe_thermal import solve_tier1_shupe, write_shupe_lut
from tier3_analysis.analyze_nonlinearity import analyze_sweep_nonlinearity
from tier3_analysis.binary_io import compute_welch_psd, fit_loglog_slope, read_sim_records
from tier3_analysis.dual_regime_avar import run_dual_regime_avar
from tier3_analysis.extract_k_matrix import extract_k_matrix
from tier3_analysis.run_sweep_parallel import run_slow_rate_ramp_sweep
from viz.export_report import export_run_report
from viz.plot_bunny_ears import plot_bunny_ears
from viz.plot_psd_flicker import plot_psd_flicker

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASE_CFG = REPO_ROOT / "configs" / "baseline_1km.json"
SWEEP_CFG = REPO_ROOT / "configs" / "ablation_sweeps" / "slow_rate_ramp.json"


@pytest.mark.gate
@pytest.mark.system
def test_gate1_golden_linear_baseline_and_continuous_flyback(tmp_path: Path) -> None:
    """Gate 1: Delta_phi_S = 1e-8 rad static err < 1e-9 rad; large step continuous 2*pi resets; V_pi 2% -> < 1e-5."""
    base = deep_merge(
        load_config(BASE_CFG),
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
    phys_p = tmp_path / "phys.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")
    k_opt = phys["K_opt_rad_per_rad_s"]

    # Case 1A: Ultra-small Sagnac phase Delta_phi_S = 1e-8 rad
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
    (tmp_path / "cfg_small.json").write_text(json.dumps(cfg_small), encoding="utf-8")
    subprocess.run(
        [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(tmp_path / "cfg_small.json"), "--out", str(tmp_path / "out_small")],
        check=True,
        capture_output=True,
    )
    s_small = json.loads((tmp_path / "out_small" / "sim_summary.json").read_text(encoding="utf-8"))
    assert abs(s_small["final_delta_phi_step_rad"] - target_dphi) < 1.0e-9
    assert abs(s_small["final_eps_vpi_eff"]) < 1.0e-5

    # Case 1B: Large step causing continuous 2*pi flyback resets (> 1000 wraps)
    omega_big = 1.0  # rad/s -> Delta_phi_S = 1.352 rad/tau -> ~1 wrap every 4.6 tau!
    cfg_big = deep_merge(
        base,
        {
            "simulation": {
                "duration_s": 0.04,
                "decimation_tau": 4,
                "dump_micro_ms": 0.0,
                "stimulus": {
                    "type": "step",
                    "omega_start_rad_per_s": 0.0,
                    "omega_end_rad_per_s": omega_big,
                    "step_time_s": 0.002,
                },
            }
        },
    )
    (tmp_path / "cfg_big.json").write_text(json.dumps(cfg_big), encoding="utf-8")
    subprocess.run(
        [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(tmp_path / "cfg_big.json"), "--out", str(tmp_path / "out_big")],
        check=True,
        capture_output=True,
    )
    s_big = json.loads((tmp_path / "out_big" / "sim_summary.json").read_text(encoding="utf-8"))
    assert s_big["flyback_count"] > 1000
    assert abs(s_big["final_delta_phi_step_rad"] - k_opt * omega_big) < 1.0e-9
    assert abs(s_big["final_eps_vpi_eff"]) < 1.0e-5


@pytest.mark.gate
@pytest.mark.system
def test_gate2_deadband_and_bunny_ears_full_sweep_mitigation(tmp_path: Path) -> None:
    """Gate 2: Full Slow Rate Ramp sweep [-0.5, +0.5] deg/s; >= 90% Deadband & Bunny Ears reduction."""
    sweep_spec = json.loads(SWEEP_CFG.read_text(encoding="utf-8"))
    sweep_spec["base_config"] = str(BASE_CFG)
    sweep_res = run_slow_rate_ramp_sweep(SIM_BIN, sweep_spec, tmp_path / "gate2")
    nl = analyze_sweep_nonlinearity(sweep_res)

    # Uncompensated must clearly exhibit Deadband & Bunny Ears nonlinearity
    assert nl["uncompensated"]["deadband_peak_err_deg_per_s"] > 0.05
    assert nl["uncompensated"]["bunny_ears_peak_sf_ppm"] > 1.0e5

    # Compensated (4-state V_pi + ADC Blanking + PRBS Dither) must reduce both by >= 90%
    assert nl["deadband_reduction_pct"] >= 90.0
    assert nl["bunny_ears_sf_reduction_pct"] >= 90.0
    assert nl["gate2_pass"] is True

    png = plot_bunny_ears(tmp_path / "gate2" / "sweep_results.json", tmp_path / "gate2" / "bunny_ears.png")
    assert png.exists() and png.stat().st_size > 10_000


@pytest.mark.gate
@pytest.mark.system
def test_gate3_flicker_1f_filtering_vs_leakage_and_k_matrix_repeatability(tmp_path: Path) -> None:
    """Gate 3: Real 2.0 s shifted f_c in [10 Hz, 5 kHz] PSD (flat linear vs -1 nonlinear) & K-matrix < 2%."""
    base = load_config(BASE_CFG)
    phys = solve_tier1_optics(base)
    phys_p = tmp_path / "phys.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")

    # 3A. Linear 2.0 s run with strong TIA 1/f noise in [10 Hz, 5 kHz] -> additive 1/f modulated out (flat PSD!)
    cfg_lin = deep_merge(
        base,
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
            "simulation": {"duration_s": 2.0, "decimation_tau": 4, "dump_micro_ms": 0.0},
        },
    )

    # 3B. Nonlinear 2.0 s run with resistive crosstalk + G2/G3 nonlinearity -> clear -1 (1/f) PSD slope!
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

    for label, cfg_obj in [("lin", cfg_lin), ("nl", cfg_nl)]:
        cf = tmp_path / f"cfg_{label}.json"
        cf.write_text(json.dumps(cfg_obj), encoding="utf-8")
        subprocess.run(
            [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(cf), "--out", str(tmp_path / f"out_{label}")],
            check=True,
            capture_output=True,
        )

    rec_lin = read_sim_records(tmp_path / "out_lin" / "sim_out.bin")
    rec_nl = read_sim_records(tmp_path / "out_nl" / "sim_out.bin")
    dt = float(np.median(np.diff(rec_lin["t"])))
    f_lin, p_lin = compute_welch_psd(rec_lin["omega_out"][500:], fs_Hz=1.0 / dt, nperseg=8192)
    f_nl, p_nl = compute_welch_psd(rec_nl["omega_out"][500:], fs_Hz=1.0 / dt, nperseg=8192)

    slope_lin = fit_loglog_slope(f_lin, p_lin, 15.0, 1500.0)
    slope_nl = fit_loglog_slope(f_nl, p_nl, 15.0, 1500.0)
    # Linear PSD must be flat (slope ~ 0); nonlinear PSD must exhibit clear 1/f slope (~ -1)
    assert abs(slope_lin) < 0.25, f"Expected flat linear PSD, got slope={slope_lin:.3f}"
    assert -1.25 <= slope_nl <= -0.75, f"Expected ~-1 nonlinear 1/f PSD slope, got slope={slope_nl:.3f}"

    # 3C. 100 Hz sinusoidal injection K-matrix repeatability < 2%
    k1 = extract_k_matrix(SIM_BIN, base, phys_p, tmp_path / "k1", freq_Hz=100.0, duration_s=0.1)
    k2 = extract_k_matrix(SIM_BIN, base, phys_p, tmp_path / "k2", freq_Hz=100.0, duration_s=0.1)
    v1 = np.asarray(k1["K_physical_vector"], dtype=np.float64)
    v2 = np.asarray(k2["K_physical_vector"], dtype=np.float64)
    rel_err = np.abs(v1 - v2) / np.maximum(np.abs(v1), 1e-15)
    assert float(np.max(rel_err)) < 0.02

    psd_stats = plot_psd_flicker(
        tmp_path / "out_lin" / "sim_out.bin",
        tmp_path / "out_nl" / "sim_out.bin",
        tmp_path / "psd_flicker.png",
    )
    assert abs(psd_stats["slope_linear"]) < 0.25
    assert -1.25 <= psd_stats["slope_nonlinear"] <= -0.75


@pytest.mark.gate
@pytest.mark.system
def test_gate4_dual_regime_60s_fast_and_10h_slow_avar_5regions(tmp_path: Path) -> None:
    """Gate 4: Real 60 s Fast-Scale + 10 h (3.6M samples) Slow-Scale AVAR; <5% overlap & +-10% 5-region WLS."""
    run_dir = tmp_path / "gate4_run"
    run_dir.mkdir(parents=True, exist_ok=True)
    base = load_config(BASE_CFG)

    # Tier 1: Optics & Thermal Shupe
    phys = solve_tier1_optics(base)
    phys_p = run_dir / "phys_params.json"
    phys_p.write_text(json.dumps(phys, indent=2), encoding="utf-8")
    t_sh, phi_sh, _ = solve_tier1_shupe(base)
    write_shupe_lut(run_dir / "shupe_lut.bin", t_sh, phi_sh)
    (run_dir / "cfg.json").write_text(json.dumps(base, indent=2), encoding="utf-8")

    # Tier 2: Real 60.0 s Fast-Scale SystemC-AMS runs (4 parallel Monte Carlo seeds per Spec Fig. 1)
    def _run_fast_seed(idx: int) -> Path:
        seed_cfg = deep_merge(
            base,
            {
                "meta": {"seed": int(base["meta"]["seed"]) + idx * 1009},
                "simulation": {"duration_s": 60.0, "decimation_tau": 4, "dump_micro_ms": 0.2 if idx == 0 else 0.0},
            },
        )
        sub_dir = run_dir / f"fast_seed_{idx}"
        sub_dir.mkdir(parents=True, exist_ok=True)
        cf = sub_dir / "cfg.json"
        cf.write_text(json.dumps(seed_cfg), encoding="utf-8")
        subprocess.run(
            [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(cf), "--out", str(sub_dir)],
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

    workers = min(4, max(1, os.cpu_count() or 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(_run_fast_seed, range(4)))

    # Tier 2 -> Tier 3: Extract K-matrix at 100 Hz
    extract_k_matrix(SIM_BIN, base, phys_p, run_dir, freq_Hz=100.0, duration_s=0.1)

    # Tier 3: Real 10-hour (3.6M samples @ 100 Hz) Slow-Scale + Overlapping AVAR + WLS 5-region fit
    metrics = run_dual_regime_avar(run_dir, cfg_path=run_dir / "cfg.json", slow_ensemble=12)

    assert metrics["fast_duration_s"] >= 59.9
    assert metrics["slow_n_samples"] == 3_600_000
    # EQ-30 overlap continuity strictly < 5% on T_m in [0.1, 5.0] s
    ov = metrics["overlap_check"]
    assert ov["continuity_pass_lt_5pct"] is True, f"Overlap mismatch {ov['max_relative_mismatch_pct']:.2f}% >= 5%"

    # EQ-24 WLS recovery of all 5 IEEE 952 parameters (Q, N, B, K, R) within +-10% of analytical truth
    fit = metrics["fitted_ieee952"]
    truth = metrics["slow_synthesis_truth"]
    for label, key in [
        ("Q", "Q_arcsec"),
        ("N", "N_deg_per_rt_h"),
        ("B", "B_deg_per_h"),
        ("K", "K_deg_per_rt_h3"),
        ("R", "R_deg_per_h2"),
    ]:
        rel = abs(fit[key] - truth[key]) / truth[key]
        assert rel <= 0.10, f"Gate 4 WLS {label} mismatch {rel*100:.2f}% > 10% (fit={fit[key]}, truth={truth[key]})"

    # Viz & Report export
    report = export_run_report(run_dir, formats=("png", "html"))
    assert (run_dir / "metrics_summary.json").exists()
    assert (run_dir / "figures" / "avar_5regions.png").exists()
    assert (run_dir / "figures" / "waveforms.png").exists()
    assert (run_dir / "report.html").exists()
    assert report["avar_metrics"]["overlap_check"]["continuity_pass_lt_5pct"] is True


@pytest.mark.regression
@pytest.mark.system
def test_deterministic_regression_and_spec_integrity(tmp_path: Path) -> None:
    """Regression: Bit-exact identical sim_out.bin across repeated seeded runs + spec SHA-256 lock."""
    # Verify spec immutability checksum (Rule 7)
    sha_file = REPO_ROOT / "spec" / "IFOG-SIM-SPEC-004.sha256"
    expected_hash = sha_file.read_text(encoding="utf-8").strip().split()[0]
    actual_hash = hashlib.sha256((REPO_ROOT / "spec" / "IFOG-SIM-SPEC-004.tex").read_bytes()).hexdigest()
    assert actual_hash == expected_hash
    assert (REPO_ROOT / "spec" / "IFOG-SIM-SPEC-004.pdf").stat().st_size > 100_000

    # Bit-exact deterministic Tier 2 regression check
    cfg = deep_merge(load_config(BASE_CFG), {"simulation": {"duration_s": 0.05, "decimation_tau": 4, "dump_micro_ms": 0.0}})
    phys = solve_tier1_optics(cfg)
    phys_p = tmp_path / "phys.json"
    cfg_p = tmp_path / "cfg.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")
    cfg_p.write_text(json.dumps(cfg), encoding="utf-8")

    hashes = []
    for i in range(2):
        od = tmp_path / f"reg_{i}"
        subprocess.run(
            [str(SIM_BIN), "--phys", str(phys_p), "--cfg", str(cfg_p), "--out", str(od)],
            check=True,
            capture_output=True,
        )
        hashes.append(hashlib.sha256((od / "sim_out.bin").read_bytes()).hexdigest())
    assert hashes[0] == hashes[1], "Non-deterministic binary output detected in regression test!"
