#!/usr/bin/env bash
set -euo pipefail

# Official One-Command Complete IFOG Prototype Simulation Suite (IFOG-SIM-SPEC-005)
# Executes ALL 20 verification gates & scenarios end-to-end:
#   - Gates 1..4 (Golden Linear, Deadband/Bunny Ears, 1/f Flicker & K-Matrix, Dual-Regime 5-Region AVAR)
#   - Gate 5: Official 6-State Symmetric DSP Benchmark (EQ-31..EQ-34)
#   - Group A: 6 Time-Domain Scenarios (TD-01..TD-06)
#   - Group B: 5 System Engineering & Production Scenarios (ENG-01..ENG-05, EQ-35..EQ-41, default MC=500)
#   - Group C: 4 Closed-Loop Dynamic Response, Output PSD & Internal Electro-Optic Probe Scenarios (DYN-01..DYN-04)
# Automatically compiles build/ifog_sim if needed and exports:
#   - report/<run_id>/report.md                      (Full Markdown tables & embedded 300-DPI PNGs)
#   - report/<run_id>/report.html                    (19 Interactive Plotly HTML5 charts + 20-PNG gallery)
#   - report/<run_id>/figures/*.png                  (All 20 300-DPI diagnostic plots)
#   - report/<run_id>/virtual_calibration_dataset.csv
#   - report/index.{md,html}
#
# Usage:
#   ./scripts/run_all_scenarios.sh [--run-id <id>] [--mc-runs 500] [--dsp-mode 6state] [extra run_sim args...]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

HAS_MC_RUNS=0
for arg in "$@"; do
    if [ "${arg}" = "--mc-runs" ]; then
        HAS_MC_RUNS=1
        break
    fi
done

if [ "${HAS_MC_RUNS}" -eq 1 ]; then
    exec "${SCRIPT_DIR}/run_sim.sh" --mode all_scenarios "$@"
else
    exec "${SCRIPT_DIR}/run_sim.sh" --mode all_scenarios --mc-runs 500 "$@"
fi
