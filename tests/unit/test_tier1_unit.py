"""Unit & CLI tests achieving 100% coverage of tier1_offline/ modules."""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from tier1_offline import config_loader, jones_spectral, shupe_thermal

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_CFG = REPO_ROOT / "configs" / "baseline_1km.json"


@pytest.mark.unit
def test_config_loader_valid_and_all_error_branches() -> None:
    cfg = config_loader.load_config(BASE_CFG)
    assert cfg["schema_version"] == "4.0"

    # Deep merge test (nested dict & leaf overwrite)
    merged = config_loader.deep_merge(cfg, {"dsp": {"K_tot_1": 0.30}, "meta": {"seed": 99}})
    assert merged["dsp"]["K_tot_1"] == 0.30
    assert merged["meta"]["seed"] == 99
    assert cfg["dsp"]["K_tot_1"] == 0.25

    # Invalid blanking window
    bad_blank = config_loader.deep_merge(cfg, {"adc_dac": {"k_start": 10, "k_end": 5}})
    with pytest.raises(ValueError, match="blanking window"):
        config_loader.validate_config(bad_blank)

    # Invalid ADC rails
    bad_rails = config_loader.deep_merge(cfg, {"analog_frontend": {"V_min_V": 5.0, "V_max_V": 5.0}})
    with pytest.raises(ValueError, match="clipping rails"):
        config_loader.validate_config(bad_rails)

    # Invalid pink noise band
    bad_pink = config_loader.deep_merge(cfg, {"noise": {"pink_f_min_Hz": 100.0, "pink_f_max_Hz": 50.0}})
    with pytest.raises(ValueError, match="pink noise band"):
        config_loader.validate_config(bad_pink)

    # Violated Loop-2 bandwidth separation (EQ-22)
    bad_loop2 = config_loader.deep_merge(
        cfg, {"dsp": {"mode": "4state", "en_vpi_loop": True, "K_tot_1": 0.25, "K_tot_2": 0.05}}
    )
    with pytest.raises(ValueError, match="bandwidth separation"):
        config_loader.validate_config(bad_loop2)

    # 2-state mode skips Loop-2 check cleanly
    ok_2s = config_loader.deep_merge(cfg, {"dsp": {"mode": "2state", "en_vpi_loop": False, "K_tot_2": 0.0}})
    assert config_loader.validate_config(ok_2s)["dsp"]["mode"] == "2state"

    # Helper analytical functions
    assert config_loader.compute_tau(1000.0, 1.468) > 0.0
    assert config_loader.compute_k_opt(1000.0, 0.10, 1.55e-6) > 0.0
    assert config_loader.compute_kerr_phase(2.6e-20, 1000.0, 1.55e-6, 5e-11, 0.5005, 1e-3, 1.0) < 0.0
    assert config_loader.compute_delta_nu_eff(1.55e-6, 40e-9) > 1e12
    dyn = config_loader.compute_tia_dynamics(50000.0, 3e-12, 2.523e-13, 150e6)
    assert dyn["t_s_0p1pct_s"] > 0.0
    nv = config_loader.compute_tia_noise_variance(
        2e-5, 0.95, 5e-9, 300.0, 50000.0, 7.51e12, 2e-12, 4e-9, 3e-12, 2.523e-13, 1.63e6
    )
    assert nv["var_total_A2"] == nv["var_flat_A2"] + nv["var_cap_A2"]


@pytest.mark.unit
def test_jones_spectral_unit_and_cli(tmp_path: Path) -> None:
    rc = jones_spectral.main(["--cfg", str(BASE_CFG), "--out", str(tmp_path)])
    assert rc == 0
    phys = json.loads((tmp_path / "phys_params.json").read_text(encoding="utf-8"))
    assert 0.99 < phys["visibility_V"] <= 1.0
    assert math.isclose(phys["K_opt_rad_per_rad_s"], 1.352158, rel_tol=1e-4)

    # Test explicit e_in branch on both extract_visibility_and_pol_phase and evaluate_static_interference
    omega_k, w_k, _ = jones_spectral.build_spectral_slices(1.55e-6, 40e-9, 64)
    j_cw, j_ccw, _ = jones_spectral.compute_jones_matrices(
        omega_k, 1.55e-6, 1.468, 1000.0, 2e-3, 1e-5, 60.0, 200, seed=11
    )
    e_te = np.array([1.0, 0.0], dtype=np.complex128)
    v, phi, pmax, pmin = jones_spectral.extract_visibility_and_pol_phase(j_cw, j_ccw, w_k, e_in=e_te)
    assert v > 0.99 and pmax > pmin and abs(phi) < 1e-3
    grid = np.linspace(-math.pi, math.pi, 32)
    p_vals = jones_spectral.evaluate_static_interference(j_cw, j_ccw, w_k, grid, e_in=e_te)
    assert len(p_vals) == 32


@pytest.mark.unit
def test_shupe_thermal_1d_fem_csv_and_cli(tmp_path: Path) -> None:
    # 1. CLI 1D diffusion mode
    rc = shupe_thermal.main(["--cfg", str(BASE_CFG), "--out", str(tmp_path / "run_1d")])
    assert rc == 0
    t_lut, phi_lut, dt_lut = shupe_thermal.read_shupe_lut(tmp_path / "run_1d" / "shupe_lut.bin")
    assert len(t_lut) > 10 and dt_lut > 0.0 and np.all(np.isfinite(phi_lut))

    # 2. Single-sample LUT edge case (dt_s = 0.0) & invalid magic error branch
    single_lut = tmp_path / "single.bin"
    shupe_thermal.write_shupe_lut(single_lut, np.array([0.0]), np.array([1e-8]))
    ts, ps, dts = shupe_thermal.read_shupe_lut(single_lut)
    assert len(ts) == 1 and dts == 0.0 and ps[0] == 1e-8

    bad_lut = tmp_path / "bad.bin"
    bad_lut.write_bytes(b"BAD!" + b"\x00" * 20)
    with pytest.raises(ValueError, match="Invalid shupe_lut.bin"):
        shupe_thermal.read_shupe_lut(bad_lut)

    # 3. External FEM CSV import branch
    fem_csv = tmp_path / "fem.csv"
    fem_csv.write_text(
        "t_s,z_m,dT_dt_K_per_s\n"
        "0.0,0.0,0.0\n0.0,500.0,0.001\n0.0,1000.0,0.002\n"
        "10.0,0.0,0.0\n10.0,500.0,0.002\n10.0,1000.0,0.004\n",
        encoding="utf-8",
    )
    cfg = config_loader.deep_merge(
        config_loader.load_config(BASE_CFG), {"thermal": {"fem_csv_path": str(fem_csv)}}
    )
    t_f, phi_f, summary_f = shupe_thermal.solve_tier1_shupe(cfg)
    assert summary_f["source_mode"] == "fem_csv"
    assert len(t_f) == 2 and abs(phi_f[1]) > abs(phi_f[0])
