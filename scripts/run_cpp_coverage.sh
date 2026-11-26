#!/usr/bin/env bash
set -euo pipefail

# Build Tier 2 with GCC gcov instrumentation and verify 100.0% C++ line coverage
# across tier2_sysc_ams/src/ and tier2_sysc_ams/include/ (AGENT.md Rules 2 & 14).

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_COV="${REPO_ROOT}/build-cov"
COV_WORK="${REPO_ROOT}/data/cov_cpp_work"

rm -rf "$BUILD_COV" "$COV_WORK"
mkdir -p "$COV_WORK"

cmake -S "${REPO_ROOT}/tier2_sysc_ams" -B "$BUILD_COV" \
    -DCMAKE_BUILD_TYPE=Debug \
    -DIFOG_ENABLE_COVERAGE=ON
cmake --build "$BUILD_COV" -j

# 1. Run C++ unit & Gate 1 test binary
"${BUILD_COV}/ifog_cpp_tests"

# 2. Generate Tier 1 phys_params.json & shupe_lut.bin
python3 "${REPO_ROOT}/tier1_offline/jones_spectral.py" \
    --cfg "${REPO_ROOT}/configs/baseline_1km.json" \
    --out "$COV_WORK"
python3 "${REPO_ROOT}/tier1_offline/shupe_thermal.py" \
    --cfg "${REPO_ROOT}/configs/baseline_1km.json" \
    --out "$COV_WORK"

# 3. Exercise every runtime branch of ifog_sim cleanly via deterministic micro-scenarios
python3 - "$BUILD_COV/ifog_sim" "$COV_WORK" "${REPO_ROOT}/configs/baseline_1km.json" <<'PY'
import json, subprocess, sys
from pathlib import Path
from tier1_offline.config_loader import deep_merge

sim_bin = sys.argv[1]
work = Path(sys.argv[2])
base = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))
phys = str(work / "phys_params.json")
shupe = str(work / "shupe_lut.bin")

def run_cfg(name, ov, extra_args=None, expect_fail=False):
    cfg = deep_merge(base, ov)
    cf = work / f"{name}.json"
    cf.write_text(json.dumps(cfg), encoding="utf-8")
    od = work / f"out_{name}"
    cmd = [sim_bin, "--phys", phys, "--cfg", str(cf), "--out", str(od)] + (extra_args or [])
    res = subprocess.run(cmd, capture_output=True, text=True)
    if expect_fail:
        assert res.returncode != 0, f"{name} expected failure but succeeded"
    else:
        assert res.returncode == 0, f"{name} failed: {res.stderr}"

# (a) 4-state full impairments + shupe + faraday + pink + white + PRBS reflection (both +/-pi/4) + flyback + CLI overrides
run_cfg("full_4s_reflect", {
    "dsp": {"mode": "4state", "en_vpi_loop": True, "en_adc_blanking": True, "en_prbs_dither": True, "prbs_amplitude_rad": 0.45},
    "noise": {"en_white_noise": True, "en_pink_noise": True, "sine_inject_target": "tia", "sine_inject_amp": 0.01},
    "ablation_flags": {
        "en_pol_error": True, "en_kerr": True, "en_shupe": True, "en_faraday": True,
        "en_mioc_vpi_err": True, "en_ram": True, "en_xtalk": True,
        "en_ltf_transient": True, "en_tia_poly_nl": True, "en_quantization": True,
    },
    "simulation": {"duration_s": 0.02, "decimation_tau": 1, "dump_micro_ms": 0.0,
                   "stimulus": {"type": "step", "omega_start_rad_per_s": 0.5, "omega_end_rad_per_s": -0.5, "step_time_s": 0.01}},
}, extra_args=["--shupe", shupe, "--duration-s", "0.025", "--dump-micro-ms", "0.05"])

# (b) Force both lower and upper ADC clipping branches (< V_min and > V_max)
run_cfg("clip_high", {
    "analog_frontend": {"V_off_0_V": 10.0, "V_min_V": -1.0, "V_max_V": 1.0},
    "simulation": {"duration_s": 0.001, "decimation_tau": 1, "dump_micro_ms": 0.0},
})
run_cfg("clip_low", {
    "analog_frontend": {"V_off_0_V": -10.0, "V_min_V": -1.0, "V_max_V": 1.0},
    "simulation": {"duration_s": 0.001, "decimation_tau": 1, "dump_micro_ms": 0.0},
})

# (c) 2-state mode, linear (no LTF, no poly, no quant, no blanking, no dither, no noise), ramp stimulus + dac sine inject
run_cfg("mode_2s_dac", {
    "dsp": {"mode": "2state", "en_vpi_loop": False, "en_adc_blanking": False, "en_prbs_dither": False},
    "noise": {"en_white_noise": False, "en_pink_noise": False, "sine_inject_target": "dac", "sine_inject_amp": 0.002},
    "ablation_flags": {
        "en_pol_error": False, "en_kerr": False, "en_shupe": False, "en_faraday": False,
        "en_mioc_vpi_err": False, "en_ram": False, "en_xtalk": False,
        "en_ltf_transient": False, "en_tia_poly_nl": False, "en_quantization": False,
    },
    "simulation": {"duration_s": 0.002, "decimation_tau": 1, "dump_micro_ms": 0.0,
                   "stimulus": {"type": "ramp", "omega_start_rad_per_s": -0.1, "omega_end_rad_per_s": 0.1}},
})

# (d) Non-stiff SystemC-AMS sca_ltf_nd branch (omega0 * dt_fast <= 0.2) + sine stimulus + xtalk sine inject
run_cfg("nonstiff_sca_ltf_xtalk", {
    "analog_frontend": {"f_gbw_Hz": 5.0e3, "C_f_F": 1.0e-11},
    "adc_dac": {"drv_omega0_rad_per_s": 2.0e5},
    "noise": {"en_white_noise": False, "en_pink_noise": False, "sine_inject_target": "xtalk", "sine_inject_amp": 0.1},
    "simulation": {"duration_s": 0.002, "decimation_tau": 1, "dump_micro_ms": 0.0,
                   "stimulus": {"type": "sine", "omega_rad_per_s": 0.0, "freq_Hz": 100.0, "amp_rad_per_s": 0.05}},
})

# (e) 6-state symmetric DSP (alpha=pi/3) + DspTraceCollector (>4096 flush) + eps_vpi step shock + aperture jitter + vibration + dynamic Faraday
run_cfg("mode_6s_full_spec005", {
    "dsp": {"mode": "6state", "alpha_rad": 1.0471975511965976, "en_vpi_loop": True, "en_prbs_dither": True, "prbs_amplitude_rad": 0.001},
    "mioc": {"eps_vpi": 0.01, "eps_vpi_step_time_s": 0.005, "eps_vpi_step_delta": 0.04},
    "adc_dac": {"aperture_jitter_s": 5.0e-10},
    "magneto_optic": {"B_ext_T": 1.0e-4, "effective_loop_m": 0.5, "B_ac_T": 5.0e-5, "B_freq_Hz": 200.0},
    "vibration": {"en_vibration": True, "freq_Hz": 300.0, "g_rms": 2.0, "loss_mod_per_g": 0.01, "phase_mod_rad_per_g": 1.0e-4},
    "ablation_flags": {"en_faraday": True, "en_mioc_vpi_err": True, "en_tia_poly_nl": True},
    "fault_injection": {"type": "none", "inject_time_s": 0.0, "duration_s": 0.0},
    "bit_fdir": {"en_bit": True, "en_fdir_recovery": True},
    "simulation": {"duration_s": 0.025, "decimation_tau": 1, "dump_micro_ms": 0.05, "dump_dsp_trace": True},
})

# (f) Anti-windup positive & negative clamping
run_cfg("anti_windup_pos_neg", {
    "dsp": {"mode": "4state", "max_delta_phi_step_rad": 0.05, "en_prbs_dither": False},
    "noise": {"en_white_noise": False, "en_pink_noise": False},
    "simulation": {
        "duration_s": 0.015, "decimation_tau": 1, "dump_micro_ms": 0.0,
        "stimulus": {"type": "step", "omega_start_rad_per_s": 0.5, "omega_end_rad_per_s": -0.5, "step_time_s": 0.007},
    },
})

# (g) All 5 BIT/FDIR fault injection modes (EQ-39)
for ftype, extra_fi in [
    ("sld_drop_50pct", {"inject_time_s": 0.002, "duration_s": 0.0}),
    ("fiber_break", {"inject_time_s": 0.002, "duration_s": 0.0}),
    ("mioc_electrode_open", {"inject_time_s": 0.002, "duration_s": 0.0}),
    ("adc_saturation", {"inject_time_s": 0.002, "duration_s": 0.002}),
    ("dsp_seu_bitflip", {"inject_time_s": 0.002, "duration_s": 0.0, "seu_delta_phi_rad": 0.4}),
]:
    run_cfg(f"fault_{ftype}", {
        "dsp": {"mode": "6state", "alpha_rad": 1.0471975511965976, "en_prbs_dither": False},
        "noise": {"en_white_noise": False, "en_pink_noise": False},
        "fault_injection": {"type": ftype, **extra_fi},
        "bit_fdir": {"en_bit": True, "en_fdir_recovery": True, "vpi_err_threshold": 2000.0, "seu_err_threshold": 2000.0},
        "simulation": {"duration_s": 0.01, "decimation_tau": 1, "dump_micro_ms": 0.0, "dump_dsp_trace": True},
    })

# (h) Concurrent 3-Axis Shared-SLD / Shared-Rail IMU (--imu3axis, EQ-36)
run_cfg("imu_3axis_cov", {
    "dsp": {"mode": "6state", "alpha_rad": 1.0471975511965976, "en_prbs_dither": False},
    "noise": {"en_white_noise": False, "en_pink_noise": False},
    "imu_3axis": {"omega_x_rad_per_s": 2.0, "omega_y_rad_per_s": 0.0, "omega_z_rad_per_s": 0.0, "rho_opt_coupling": 2.0e-3, "z_rail_ohm": 0.25},
    "simulation": {"duration_s": 0.005, "decimation_tau": 6, "dump_micro_ms": 0.0},
}, extra_args=["--imu3axis"])

# (i) Negative validation & CLI error branches in ifog_config.cpp / main.cpp / digital_dsp_sc.cpp
run_cfg("bad_dsp_mode", {"dsp": {"mode": "8state"}}, expect_fail=True)
run_cfg("bad_sine_target", {"noise": {"sine_inject_target": "bogus"}}, expect_fail=True)
run_cfg("bad_stim_type", {"simulation": {"stimulus": {"type": "chirp"}}}, expect_fail=True)
run_cfg("bad_fault_type", {"fault_injection": {"type": "cosmic_ray"}}, expect_fail=True)
res_err = subprocess.run([sim_bin, "--bad-flag"], capture_output=True, text=True)
assert res_err.returncode != 0
# Unwritable sim_out.bin path (pre-create directory named sim_out.bin so ofstream::open fails cleanly)
unw_dir = work / "unwritable_sim_out"
(unw_dir / "sim_out.bin").mkdir(parents=True, exist_ok=True)
res_unw = subprocess.run(
    [sim_bin, "--phys", phys, "--cfg", str(work / "clip_low.json"), "--out", str(unw_dir)],
    capture_output=True, text=True
)
assert res_unw.returncode != 0
print("All C++ coverage scenarios executed cleanly.")
PY

# 3b. Exercise every branch of fmi_wrapper/src/fmi3_bridge.cpp and IfogTopModule (SPEC-006)
FMU_COV_RES="${COV_WORK}/fmu_cov_res"
mkdir -p "${FMU_COV_RES}"
cp "${COV_WORK}/phys_params.json" "${FMU_COV_RES}/phys_params.json"
cp "${COV_WORK}/shupe_lut.bin" "${FMU_COV_RES}/shupe_lut.bin"
cp "${REPO_ROOT}/configs/baseline_1km.json" "${FMU_COV_RES}/baseline_cfg.json"
for fmi_mode in 4 6 2 4noterm fault bitfault; do
    "${BUILD_COV}/ifog_fmi_tests" "${FMU_COV_RES}" "${fmi_mode}"
done
# Also cover instantiation when optional shupe_lut.bin is absent
FMU_COV_NOSHUPE="${COV_WORK}/fmu_cov_noshupe"
mkdir -p "${FMU_COV_NOSHUPE}"
cp "${COV_WORK}/phys_params.json" "${FMU_COV_NOSHUPE}/phys_params.json"
cp "${REPO_ROOT}/configs/baseline_1km.json" "${FMU_COV_NOSHUPE}/baseline_cfg.json"
"${BUILD_COV}/ifog_fmi_tests" "${FMU_COV_NOSHUPE}" 4
# Verify dlopen + sc_main stub on the compiled FMI 3.0 shared library
python3 - "${BUILD_COV}" <<'PY'
import ctypes, pathlib, sys
so_list = list((pathlib.Path(sys.argv[1]) / "binaries").rglob("ifog_core.so"))
assert len(so_list) == 1, f"Expected 1 ifog_core.so, found {so_list}"
lib = ctypes.CDLL(str(so_list[0]))
lib.fmi3GetVersion.restype = ctypes.c_char_p
assert lib.fmi3GetVersion() == b"3.0"
assert lib.sc_main(0, None) == 0
PY

# 4. Compute and enforce strict 100.0% C++ line coverage with gcovr (Tier 2 + FMI 3.0 wrapper)
gcovr -r "${REPO_ROOT}" "${BUILD_COV}" \
    --filter "${REPO_ROOT}/tier2_sysc_ams/(src|include)/" \
    --filter "${REPO_ROOT}/fmi_wrapper/src/" \
    --exclude "${REPO_ROOT}/tier2_sysc_ams/src/cpp_unit_tests\.cpp" \
    --exclude "${REPO_ROOT}/tier2_sysc_ams/src/fmi_unit_tests\.cpp" \
    --exclude-unreachable-branches \
    --txt-metric line \
    --print-summary \
    --fail-under-line 100 \
    --json-summary "${COV_WORK}/cpp_coverage_summary.json" \
    --html-details "${COV_WORK}/cpp_coverage.html"

echo "C++ 100.0% line coverage verified (Tier 2 + FMI 3.0 wrapper)!"
