#!/usr/bin/env bash
set -euo pipefail

# Official One-Command Complete IFOG Prototype Simulation Suite (IFOG-SIM-SPEC-005)
# Executes:
#   - Gates 1..4 (Golden Linear, Deadband/Bunny Ears, 1/f Flicker & K-Matrix, Dual-Regime 5-Region AVAR)
#   - Gate 5: Official 6-State Symmetric DSP Benchmark (EQ-31..EQ-34)
#   - Group A: 6 Time-Domain Scenarios (TD-01..TD-06)
#   - Group B: 5 System Engineering & Production Scenarios (ENG-01..ENG-05, EQ-35..EQ-41)
# Automatically compiles build/ifog_sim if needed and exports report/<run_id>/{report.md, report.html}.
#
# Usage:
#   ./scripts/run_all_scenarios.sh [--run-id <id>] [--mc-runs 500] [--dsp-mode 6state] [extra run_sim args...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/run_sim.sh" --mode all_scenarios "$@"
