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

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SIM_BIN="${REPO_ROOT}/build/ifog_sim"

if [ ! -x "${SIM_BIN}" ]; then
    echo "[run_sim.sh] Tier 2 binary not found; building Release (-O3)..."
    cmake -S "${REPO_ROOT}/tier2_sysc_ams" -B "${REPO_ROOT}/build" -DCMAKE_BUILD_TYPE=Release
    cmake --build "${REPO_ROOT}/build" -j"$(nproc)"
fi

exec python3 "${REPO_ROOT}/scripts/run_sim.py" --bin "${SIM_BIN}" "$@"
