#!/usr/bin/env bash
set -euo pipefail

# Ergonomic one-command IFOG simulation launcher with automatic Tier 2 build check
# and automatic Markdown (.md) + Interactive HTML (.html) reporting into report/.
#
# Examples:
#   ./scripts/run_sim.sh --mode single --run-id baseline_run
#   ./scripts/run_sim.sh --mode gate1
#   ./scripts/run_sim.sh --mode gate2
#   ./scripts/run_sim.sh --mode gate3
#   ./scripts/run_sim.sh --mode gate4
#   ./scripts/run_sim.sh --mode full --run-id full_4gate_verification
#   ./scripts/run_sim.sh --mode dsp6_compare --run-id gate5_6state
#   ./scripts/run_sim.sh --mode fmi_gate --run-id gate6_fmi3_fmu
#   ./scripts/run_sim.sh --mode td_blanking          # or td_step_sine, td_vpi_shock, td_high_rate, td_shupe_shock, td_limit_cycles, td_all
#   ./scripts/run_sim.sh --mode eng_imu_3axis        # or eng_hw_sizing, eng_vre_faraday, eng_fault_bit, eng_mc_yield_cal, eng_all
#   ./scripts/run_sim.sh --mode all_scenarios --run-id complete_suite --mc-runs 500

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "${REPO_ROOT}/scripts/env.sh" ]; then
    # shellcheck source=/dev/null
    source "${REPO_ROOT}/scripts/env.sh"
fi
SIM_BIN="${REPO_ROOT}/build/ifog_sim"
FMU_ARCHIVE="${REPO_ROOT}/build/ifog_core.fmu"

if [ ! -x "${SIM_BIN}" ] || [ ! -f "${FMU_ARCHIVE}" ]; then
    echo "[run_sim.sh] Tier 2 binary or FMI 3.0 FMU not found; building Release (-O3) & packaging FMU..."
    cmake -S "${REPO_ROOT}/tier2_sysc_ams" -B "${REPO_ROOT}/build" -DCMAKE_BUILD_TYPE=Release
    cmake --build "${REPO_ROOT}/build" -j"$(nproc)"
    cmake --build "${REPO_ROOT}/build" --target package_fmu
fi

exec python3 "${REPO_ROOT}/scripts/run_sim.py" --bin "${SIM_BIN}" --fmu "${FMU_ARCHIVE}" "$@"
