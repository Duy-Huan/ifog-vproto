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

# (e) Negative validation & CLI error branches in ifog_config.cpp / main.cpp / digital_dsp_sc.cpp
run_cfg("bad_dsp_mode", {"dsp": {"mode": "8state"}}, expect_fail=True)
run_cfg("bad_sine_target", {"noise": {"sine_inject_target": "bogus"}}, expect_fail=True)
run_cfg("bad_stim_type", {"simulation": {"stimulus": {"type": "chirp"}}}, expect_fail=True)
# Unwritable bin_out path (pass a directory as file? Use /dev/null/sub)
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

# 4. Compute and enforce strict 100.0% C++ line coverage with gcovr
gcovr -r "${REPO_ROOT}" "${BUILD_COV}" \
    --filter "${REPO_ROOT}/tier2_sysc_ams/(src|include)/" \
    --exclude "${REPO_ROOT}/tier2_sysc_ams/src/cpp_unit_tests\.cpp" \
    --exclude-unreachable-branches \
    --txt-metric line \
    --print-summary \
    --fail-under-line 100 \
    --json-summary "${COV_WORK}/cpp_coverage_summary.json" \
    --html-details "${COV_WORK}/cpp_coverage.html"

echo "C++ 100.0% line coverage verified!"
