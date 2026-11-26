#!/usr/bin/env bash
set -euo pipefail

# Official One-Command Complete IFOG Prototype Simulation Suite (IFOG-SIM-SPEC-007)
# Executes ALL 23 verification gates & scenarios end-to-end:
#   - Gates 1..4 (Golden Linear, Deadband/Bunny Ears, 1/f Flicker & K-Matrix, Dual-Regime 5-Region AVAR)
#   - Gate 5: Official 6-State Symmetric DSP Benchmark (EQ-31..EQ-34)
#   - Gate 6: FMI 3.0 Black-Box FMU Compliance, Equivalence (<1e-12), Deadband & 5-Region AVAR (EQ-42..EQ-44)
#   - Group A: 6 Time-Domain Scenarios (TD-01..TD-06)
#   - Group B: 5 System Engineering & Production Scenarios (ENG-01..ENG-05, EQ-35..EQ-41, default MC=500)
#   - Group C: 4 Closed-Loop Dynamic Response, Output PSD & Internal Electro-Optic Probe Scenarios (DYN-01..DYN-04)
#   - Group D: 2 SPEC-007 High-Fidelity Predictive Physics & Inverse Calibration Scenarios (PHY-01, CAL-01, EQ-45..EQ-53)
# Automatically compiles build/ifog_sim & packages build/ifog_core.fmu if needed and exports:
#   - report/<run_id>/report.md                      (Full Markdown tables, 23 annotated PNGs & Section 12 EQ-01..EQ-53)
#   - report/<run_id>/report.html                    (KaTeX + Plotly HTML5 + architecture_model.html + 23-PNG gallery)
#   - report/<run_id>/figures/*.png                  (All 23 300-DPI diagnostic plots)
#   - report/<run_id>/calibrated_params.json & virtual_calibration_dataset.csv
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
