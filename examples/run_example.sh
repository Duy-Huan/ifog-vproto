#!/usr/bin/env bash
set -euo pipefail

# Reproducibly run the COMPLETE IFOG Virtual Prototype Official Scenario Suite
# (IFOG-SIM-SPEC-005: Gates 1..4 + Gate 5 6-State DSP + TD-01..06 + ENG-01..05 + DYN-01..04, MC=500)
# on any Linux host (after scripts/setup_env.sh) or inside Docker/Podman,
# automatically generating report.md, interactive Plotly report.html (19 charts), all 20 300-DPI PNG plots,
# virtual_calibration_dataset.csv, and report/index.{md,html}.
#
# Usage:
#   ./examples/run_example.sh                # runs all scenarios -> report/full_all_scenarios/
#   ./examples/run_example.sh --sync-example # also refreshes examples/full_all_scenarios/ curated artifacts
#   ./examples/run_example.sh --4gate-only   # optional legacy SPEC-004 4-Gate only run

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC_EXAMPLE=0
LEGACY_4GATE=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --sync-example) SYNC_EXAMPLE=1; shift ;;
        --4gate-only) LEGACY_4GATE=1; shift ;;
        *) break ;;
    esac
done

if [ "${LEGACY_4GATE}" -eq 1 ]; then
    "${REPO_ROOT}/scripts/run_sim.sh" --mode full --run-id full_4gate_baseline "$@"
    if [ "${SYNC_EXAMPLE}" -eq 1 ]; then
        DST="${REPO_ROOT}/examples/full_4gate_baseline"
        mkdir -p "${DST}/figures"
        cp "${REPO_ROOT}/report/full_4gate_baseline/report.md" "${DST}/"
        cp "${REPO_ROOT}/report/full_4gate_baseline/report.html" "${DST}/"
        cp "${REPO_ROOT}/report/full_4gate_baseline/metrics_summary.json" "${DST}/"
        cp "${REPO_ROOT}/report/full_4gate_baseline/figures/"*.png "${DST}/figures/"
        for jf in phys_params.json shupe_summary.json sim_summary.json gate1_metrics.json \
                  sweep_results.json nonlinearity_summary.json k_matrix.json gate3_metrics.json avar_metrics.json; do
            if [ -f "${REPO_ROOT}/data/full_4gate_baseline/${jf}" ]; then
                cp "${REPO_ROOT}/data/full_4gate_baseline/${jf}" "${DST}/"
            fi
        done
        echo "[run_example] Synchronized legacy 4-Gate example outputs into ${DST}"
    fi
    exit 0
fi

"${REPO_ROOT}/scripts/run_all_scenarios.sh" --run-id full_all_scenarios "$@"

if [ "${SYNC_EXAMPLE}" -eq 1 ]; then
    DST="${REPO_ROOT}/examples/full_all_scenarios"
    mkdir -p "${DST}/figures"
    cp "${REPO_ROOT}/report/full_all_scenarios/report.md" "${DST}/"
    cp "${REPO_ROOT}/report/full_all_scenarios/report.html" "${DST}/"
    cp "${REPO_ROOT}/report/full_all_scenarios/metrics_summary.json" "${DST}/"
    cp "${REPO_ROOT}/report/full_all_scenarios/figures/"*.png "${DST}/figures/"
    if [ -f "${REPO_ROOT}/report/full_all_scenarios/virtual_calibration_dataset.csv" ]; then
        cp "${REPO_ROOT}/report/full_all_scenarios/virtual_calibration_dataset.csv" "${DST}/"
    fi
    for jf in phys_params.json shupe_summary.json sim_summary.json gate1_metrics.json \
              sweep_results.json nonlinearity_summary.json k_matrix.json gate3_metrics.json avar_metrics.json \
              dsp6_compare.json td01_blanking.json td02_step_sine.json td03_vpi_shock.json \
              td04_high_rate.json td05_shupe_shock.json td06_limit_cycles.json td_summary.json \
              eng01_hw_sizing.json eng02_imu_3axis.json eng03_vre_faraday.json \
              eng04_fault_bit.json eng05_mc_yield_cal.json eng_summary.json \
              dyn01_step_response.json dyn02_freq_response.json dyn03_output_psd.json \
              dyn04_sine_electro_optic.json dyn_summary.json; do
        if [ -f "${REPO_ROOT}/data/full_all_scenarios/${jf}" ]; then
            cp "${REPO_ROOT}/data/full_all_scenarios/${jf}" "${DST}/"
        fi
    done
    echo "[run_example] Synchronized complete all-scenarios curated example into ${DST}"
fi
