"""Unit & CLI tests achieving 100% coverage of tier3_analysis/ and viz/ modules."""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import numpy as np
import pytest

from tier1_offline.config_loader import deep_merge, load_config
from tier1_offline.jones_spectral import solve_tier1_optics
from tier1_offline.shupe_thermal import write_shupe_lut
from tier3_analysis import (
    analyze_nonlinearity,
    binary_io,
    dual_regime_avar,
    extract_k_matrix,
    run_sweep_parallel,
)
from viz import (
    export_report,
    plot_avar_5regions,
    plot_bunny_ears,
    plot_psd_flicker,
    plot_waveforms,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
BASE_CFG = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.unit
def test_binary_io_helpers_and_edge_cases(tmp_path: Path) -> None:
    # Write a small synthetic 32B SimRecord file and verify reading + stats + PSD + slope + tone
    n = 512
    dt = 1.0e-3
    t = np.arange(n, dtype=np.float64) * dt
    sig = 0.05 * np.sin(2.0 * math.pi * 50.0 * t)
    recs = np.zeros(n, dtype=binary_io.SIM_RECORD_DTYPE)
    recs["t"] = t
    recs["omega_in"] = 0.0
    recs["omega_out_raw"] = np.round(sig / binary_io.OMEGA_OUT_LSB).astype(np.int64)
    recs["vpi_err_raw"] = 0
    recs["flags"] = 0
    bin_p = tmp_path / "sim_out.bin"
    recs.tofile(bin_p)

    loaded = binary_io.read_sim_records(bin_p)
    stats = binary_io.summarize_record_stats(loaded)
    assert stats["n_records"] == n and stats["duration_s"] > 0.0

    # Tone extraction exactness & error branch
    amp = binary_io.extract_coherent_tone_amplitude(loaded["t"], loaded["omega_out"], 50.0)
    assert abs(amp - 0.05) < 5.0e-4
    with pytest.raises(ValueError, match="At least 4 samples"):
        binary_io.extract_coherent_tone_amplitude(t[:3], sig[:3], 50.0)

    # PSD + log-log slope + insufficient samples error branch
    freqs, psd = binary_io.compute_welch_psd(loaded["omega_out"], fs_Hz=1.0 / dt)
    assert len(freqs) > 10 and np.max(psd) > 0.0
    slope = binary_io.fit_loglog_slope(np.array([1.0, 10.0, 100.0]), np.array([100.0, 10.0, 1.0]), 1.0, 100.0)
    assert math.isclose(slope, -1.0, abs_tol=1e-12)
    with pytest.raises(ValueError, match="Insufficient positive samples"):
        binary_io.fit_loglog_slope(np.array([1.0]), np.array([1.0]), 10.0, 20.0)


@pytest.mark.unit
def test_analyze_nonlinearity_unit_and_cli(tmp_path: Path) -> None:
    rates = np.array([-0.5, -0.1, -0.02, 0.0, 0.02, 0.1, 0.5])
    # Uncompensated has large deadband & bunny ears; compensated is near ideal
    uncomp = np.array([-0.48, -0.08, 0.0, 0.0, 0.0, 0.08, 0.48])
    comp = rates * 1.0001
    sweep_data = {
        "rates_in_deg_per_s": rates.tolist(),
        "uncompensated_out_deg_per_s": uncomp.tolist(),
        "compensated_out_deg_per_s": comp.tolist(),
    }
    sw_path = tmp_path / "sweep_results.json"
    sw_path.write_text(json.dumps(sweep_data), encoding="utf-8")

    rc = analyze_nonlinearity.main(["--sweep-results", str(sw_path), "--out", str(tmp_path)])
    assert rc == 0
    res = json.loads((tmp_path / "nonlinearity_summary.json").read_text(encoding="utf-8"))
    assert res["gate2_pass"] is True

    # Zero-before reduction branch + zero-error curve (unlocked_mask False branch)
    zero_sw = {
        "rates_in_deg_per_s": rates.tolist(),
        "uncompensated_out_deg_per_s": rates.tolist(),
        "compensated_out_deg_per_s": rates.tolist(),
    }
    res_zero = analyze_nonlinearity.analyze_sweep_nonlinearity(zero_sw)
    assert res_zero["deadband_reduction_pct"] == 0.0
    assert res_zero["uncompensated"]["deadband_width_deg_per_s"] == 0.0


@pytest.mark.unit
def test_extract_k_matrix_cli_and_error_branch(tmp_path: Path) -> None:
    cfg = load_config(BASE_CFG)
    phys = solve_tier1_optics(cfg)
    phys_p = tmp_path / "phys_params.json"
    phys_p.write_text(json.dumps(phys), encoding="utf-8")

    # CLI test with short duration for fast unit coverage
    rc = extract_k_matrix.main(
        [
            "--bin",
            str(SIM_BIN),
            "--cfg",
            str(BASE_CFG),
            "--phys",
            str(phys_p),
            "--out",
            str(tmp_path / "k_out"),
            "--freq-hz",
            "100.0",
            "--duration-s",
            "0.05",
        ]
    )
    assert rc == 0
    km = json.loads((tmp_path / "k_out" / "k_matrix.json").read_text(encoding="utf-8"))
    assert len(km["K_physical_vector"]) == 3

    # Unsupported node error branch
    with pytest.raises(ValueError, match="Unsupported target node"):
        extract_k_matrix.measure_single_node_leakage(
            SIM_BIN, cfg, phys_p, tmp_path / "bad_node", "invalid_node", 0.01, duration_s=0.005
        )


@pytest.mark.unit
def test_run_sweep_parallel_both_sweep_types_and_cli(tmp_path: Path) -> None:
    sweep_dir = tmp_path / "sweeps"
    sweep_dir.mkdir()

    # Tiny 3-point slow rate ramp + 2-seed Monte Carlo sweep in one directory to exercise directory dispatch & CLI
    ramp_spec = {
        "sweep_name": "mini_ramp",
        "base_config": str(BASE_CFG),
        "rates_deg_per_s": [-0.05, 0.0, 0.05],
        "duration_per_point_s": 0.004,
        "decimation_tau": 4,
        "uncompensated_overrides": {
            "dsp": {"en_vpi_loop": False, "en_adc_blanking": False, "en_prbs_dither": False},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
        },
        "compensated_overrides": {
            "dsp": {"en_vpi_loop": True, "en_adc_blanking": True, "en_prbs_dither": True},
            "noise": {"en_white_noise": False, "en_pink_noise": False},
        },
    }
    mc_spec = {
        "sweep_name": "mini_mc",
        "base_config": str(BASE_CFG),
        "seeds": [11, 22],
        "duration_per_point_s": 0.004,
        "decimation_tau": 4,
        "scenarios": [{"label": "clean", "overrides": {"noise": {"en_white_noise": False}}}],
    }
    (sweep_dir / "01_ramp.json").write_text(json.dumps(ramp_spec), encoding="utf-8")
    (sweep_dir / "02_mc.json").write_text(json.dumps(mc_spec), encoding="utf-8")

    rc = run_sweep_parallel.main(
        ["--bin", str(SIM_BIN), "--sweep", str(sweep_dir), "--out", str(tmp_path / "out_dir"), "--workers", "2"]
    )
    assert rc == 0
    assert (tmp_path / "out_dir" / "01_ramp" / "sweep_results.json").exists()
    assert (tmp_path / "out_dir" / "02_mc" / "mini_mc_results.json").exists()

    # Single-file dispatch branch
    res_single = run_sweep_parallel.run_sweep_path(
        SIM_BIN, sweep_dir / "01_ramp.json", tmp_path / "out_single", max_workers=2
    )
    assert len(res_single) == 1


@pytest.mark.unit
def test_dual_regime_avar_edge_branches_and_cli(tmp_path: Path) -> None:
    # Error branches
    with pytest.raises(ValueError, match="at least 3 samples"):
        dual_regime_avar.overlapping_avar(np.array([0.0, 1.0]), 0.01)

    rng = np.random.default_rng(1)
    assert np.all(dual_regime_avar.generate_rrw_series(10, 0.01, 0.0, rng) == 0.0)
    with pytest.raises(ValueError, match="Unsupported rrw_mode"):
        dual_regime_avar.generate_rrw_series(10, 0.01, 1e-4, rng, mode="bogus")
    assert np.all(dual_regime_avar.generate_calibrated_pink_series(10, 0.01, 0.0, rng) == 0.0)

    with pytest.raises(ValueError, match="Empty overlap window"):
        dual_regime_avar.check_overlap_continuity(
            np.array([0.001, 0.01]), np.array([1.0, 0.5]), np.array([10.0, 100.0]), np.array([0.1, 0.05])
        )

    # Full run_dual_regime_avar via CLI + default config fallback + optional files (k_matrix, shupe_lut)
    run_dir = tmp_path / "run_avar"
    run_dir.mkdir()
    cfg = deep_merge(
        load_config(BASE_CFG),
        {
            "ablation_flags": {"en_shupe": True, "en_faraday": True},
            "magneto_optic": {"verdet_rad_per_Tm": 0.6, "B_ext_T": 1e-6, "effective_loop_m": 0.2},
            "simulation": {"duration_s": 0.6, "decimation_tau": 4, "dump_micro_ms": 0.05},
            "slow_scale": {"f_dec_Hz": 20.0, "duration_hours": 0.1, "rrw_mode": "gauss_markov"},
        },
    )
    phys = solve_tier1_optics(cfg)
    (run_dir / "phys_params.json").write_text(json.dumps(phys), encoding="utf-8")
    (run_dir / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
    write_shupe_lut(run_dir / "shupe_lut.bin", np.array([0.0, 360.0]), np.array([0.0, 1e-7]))
    (run_dir / "k_matrix.json").write_text(
        json.dumps({"K_node_unit_vector": [1e-4, 1e-4, 1e-4]}), encoding="utf-8"
    )
    subprocess.run(
        [str(SIM_BIN), "--phys", str(run_dir / "phys_params.json"), "--cfg", str(run_dir / "cfg.json"), "--out", str(run_dir)],
        check=True,
        capture_output=True,
    )

    # Explicit --cfg + --slow-ensemble 2 branch via CLI
    (run_dir / "sim_out_0.bin").write_bytes((run_dir / "sim_out.bin").read_bytes())
    (run_dir / "sim_out_1.bin").write_bytes((run_dir / "sim_out.bin").read_bytes())
    rc = dual_regime_avar.main(
        ["--run", str(run_dir), "--cfg", str(run_dir / "cfg.json"), "--slow-ensemble", "2"]
    )
    assert rc == 0
    assert (run_dir / "avar_curve.npz").exists()

    # Auto cfg.json branch
    m_auto = dual_regime_avar.run_dual_regime_avar(run_dir)
    assert m_auto["slow_n_samples"] == 7200 and m_auto["fast_ensemble_count"] == 2

    # Exercise fallback to default baseline_1km.json & k_matrix=None branch
    run_dir_fb = tmp_path / "run_fb"
    run_dir_fb.mkdir()
    (run_dir_fb / "phys_params.json").write_text(json.dumps(phys), encoding="utf-8")
    (run_dir_fb / "sim_out.bin").write_bytes((run_dir / "sim_out.bin").read_bytes())
    # Patch slow_scale.duration_hours via monkeypatch? No: just test synthesize_slow_scale_series with k_matrix=None directly,
    # and run_dual_regime_avar without cfg.json on a minimal fast run? Wait: baseline_1km has 10h (takes only ~2s in NumPy!)
    m_fb = dual_regime_avar.run_dual_regime_avar(run_dir_fb)
    assert m_fb["slow_n_samples"] == 3_600_000


@pytest.mark.unit
def test_all_viz_modules_and_export_report_100pct(tmp_path: Path) -> None:
    """Exercise all 5 viz/ modules via Python API and CLI entry points."""
    rdir = tmp_path / "viz_run"
    rdir.mkdir()
    cfg = deep_merge(
        load_config(BASE_CFG),
        {
            "simulation": {"duration_s": 0.5, "decimation_tau": 4, "dump_micro_ms": 0.1},
            "slow_scale": {"f_dec_Hz": 20.0, "duration_hours": 0.2},
        },
    )
    phys = solve_tier1_optics(cfg)
    (rdir / "phys_params.json").write_text(json.dumps(phys), encoding="utf-8")
    (rdir / "cfg.json").write_text(json.dumps(cfg), encoding="utf-8")
    subprocess.run(
        [str(SIM_BIN), "--phys", str(rdir / "phys_params.json"), "--cfg", str(rdir / "cfg.json"), "--out", str(rdir)],
        check=True,
        capture_output=True,
    )
    dual_regime_avar.run_dual_regime_avar(rdir)

    # Duplicate sim_out.bin as psd_linear.bin / psd_nonlinear.bin for viz/plot_psd_flicker & export_report
    sim_bytes = (rdir / "sim_out.bin").read_bytes()
    (rdir / "psd_linear.bin").write_bytes(sim_bytes)
    (rdir / "psd_nonlinear.bin").write_bytes(sim_bytes)

    # Sweep results for viz/plot_bunny_ears & export_report
    sw_data = {
        "rates_in_deg_per_s": [-0.5, -0.1, 0.0, 0.1, 0.5],
        "uncompensated_out_deg_per_s": [-0.45, -0.05, 0.02, 0.05, 0.45],
        "compensated_out_deg_per_s": [-0.5, -0.1, 0.0, 0.1, 0.5],
    }
    (rdir / "sweep_results.json").write_text(json.dumps(sw_data), encoding="utf-8")

    # 1. plot_waveforms CLI + empty file error branch
    assert plot_waveforms.main(["--run", str(rdir)]) == 0
    assert (rdir / "figures" / "waveforms.png").exists()
    empty_micro = tmp_path / "empty_micro.bin"
    empty_micro.write_bytes(b"")
    with pytest.raises(ValueError, match="zero samples"):
        plot_waveforms.plot_waveforms(empty_micro, tmp_path / "w.png")

    # 2. plot_bunny_ears CLI
    assert plot_bunny_ears.main(
        ["--sweep-results", str(rdir / "sweep_results.json"), "--out", str(rdir / "figures" / "be.png")]
    ) == 0
    assert (rdir / "figures" / "be.png").exists()

    # 3. plot_psd_flicker CLI
    assert plot_psd_flicker.main(
        [
            "--linear",
            str(rdir / "psd_linear.bin"),
            "--nonlinear",
            str(rdir / "psd_nonlinear.bin"),
            "--out",
            str(rdir / "figures" / "psd.png"),
        ]
    ) == 0
    assert (rdir / "figures" / "psd.png").exists()

    # 4. plot_avar_5regions CLI (ensure all 5 asymptote branches execute by providing non-zero Q,N,B,K,R)
    m_full = json.loads((rdir / "avar_metrics.json").read_text(encoding="utf-8"))
    for k_key, val in [
        ("Q_rad", 1e-8), ("Q_arcsec", 0.002),
        ("N_rad_per_rt_s", 1e-7), ("N_deg_per_rt_h", 0.0004),
        ("B_rad_per_s", 2e-8), ("B_deg_per_h", 0.004),
        ("K_rad_per_s32", 1e-10), ("K_deg_per_rt_h3", 0.01),
        ("R_rad_per_s2", 1e-11), ("R_deg_per_h2", 0.01),
    ]:
        m_full["fitted_ieee952"][k_key] = val
    (rdir / "avar_metrics.json").write_text(json.dumps(m_full), encoding="utf-8")
    assert plot_avar_5regions.main(["--run", str(rdir)]) == 0
    assert (rdir / "figures" / "avar_5regions.png").exists()

    # 5. export_report CLI (png,html) + empty-directory optional branches
    assert export_report.main(["--run", str(rdir), "--format", "png,html"]) == 0
    assert (rdir / "metrics_summary.json").exists()
    assert (rdir / "report.html").exists()

    empty_run = tmp_path / "empty_run"
    empty_run.mkdir()
    summary_empty = export_report.export_run_report(empty_run, formats=("png", "html"))
    assert summary_empty["phys_params"] is None
