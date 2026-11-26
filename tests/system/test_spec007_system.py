"""End-to-End Real System Tests for IFOG-SIM-SPEC-007 (PHY-01, CAL-01 & FMI 3.0 Tunability)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from tier3_analysis.scenarios_spec007 import run_all_spec007_scenarios

REPO_ROOT = Path(__file__).resolve().parents[2]
SIM_BIN = REPO_ROOT / "build" / "ifog_sim"
FMU_PATH = REPO_ROOT / "build" / "ifog_core.fmu"


@pytest.mark.system
@pytest.mark.gate
def test_spec007_physics_and_inverse_calibration_system(tmp_path: Path) -> None:
    """Real end-to-end SPEC-007 PHY-01 & CAL-01 verification (>40% uncalibrated -> <5% calibrated)."""
    assert SIM_BIN.exists(), f"Compiled Tier 2 binary missing at {SIM_BIN}"
    res = run_all_spec007_scenarios(SIM_BIN, out_dir=tmp_path / "spec007_sys")
    assert res["phy01_physics"]["passed"] is True
    assert res["cal01_calibration"]["passed"] is True
    assert res["all_passed"] is True

    cal = res["cal01_calibration"]
    assert cal["error_before_pct"]["avar_nrmse_pct"] > 40.0
    assert cal["error_before_pct"]["deadband_nrmse_pct"] > 40.0
    assert cal["error_before_pct"]["thermal_bias_nrmse_pct"] > 40.0
    assert cal["error_after_pct"]["avar_nrmse_pct"] < 5.0
    assert cal["error_after_pct"]["deadband_nrmse_pct"] < 5.0
    assert cal["error_after_pct"]["thermal_bias_nrmse_pct"] < 5.0
    assert cal["max_param_recovery_err_pct"] < 5.0
    assert cal["tier2_closed_loop_rate_err_pct"] < 5.0


@pytest.mark.system
@pytest.mark.gate
def test_spec007_fmi3_tunable_parameters_live(tmp_path: Path) -> None:
    """Verify FMI 3.0 FMU exposes & applies SPEC-007 tunable parameters (VR 15..21) via FMPy."""
    assert FMU_PATH.exists(), f"Packaged FMU missing at {FMU_PATH}"
    script = f"""
from fmpy import read_model_description, simulate_fmu
from fmpy.validation import validate_fmu

fmu = r"{FMU_PATH}"
probs = validate_fmu(fmu)
assert not probs, f"FMI 3.0 validation errors: {{probs}}"
md = read_model_description(fmu)
var_map = {{v.name: v for v in md.modelVariables}}
expected_tunable = [
    "C_xtalk_F", "G_xtalk_S", "c_pink_coeff", "R_facet_dB",
    "alpha_vpi_ppm_K", "alpha_bobbin_ppm_K", "delta_z_quad_m",
]
for name in expected_tunable:
    assert name in var_map, f"Missing SPEC-007 FMI variable {{name}}"
    assert var_map[name].causality == "parameter"
    assert var_map[name].variability == "tunable"

res = simulate_fmu(
    fmu,
    start_time=0.0,
    stop_time=0.005,
    step_size=0.001,
    start_values={{
        "omega_in": 0.05,
        "en_white_noise": False,
        "en_pink_noise": True,
        "C_xtalk_F": 4.5e-12,
        "G_xtalk_S": 2.5e-8,
        "c_pink_coeff": 1.8,
        "R_facet_dB": -60.0,
        "alpha_vpi_ppm_K": 380.0,
        "alpha_bobbin_ppm_K": 12.0,
        "delta_z_quad_m": 0.003,
    }},
    output=["omega_out", "omega_out_avg", "e_vpi_res", "bit_status"],
)
assert len(res) >= 5
assert abs(float(res["omega_out"][-1]) - 0.05) < 5e-3, res["omega_out"][-1]
assert int(res["bit_status"][-1]) == 0
print("FMI 3.0 SPEC-007 live tunable parameter simulation OK:", res["omega_out"][-1])
"""
    proc = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"FMI 3.0 SPEC-007 test failed:\n{proc.stdout}\n{proc.stderr}"
