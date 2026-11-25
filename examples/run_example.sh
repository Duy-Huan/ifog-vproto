#!/usr/bin/env bash
set -euo pipefail

# Reproducibly run the full real 4-Gate IFOG baseline example (Gate 1..Gate 4)
# on any Linux host (after scripts/setup_env.sh) or inside Docker/Podman.
#
# Usage:
#   ./examples/run_example.sh                # outputs to data/full_4gate_baseline & report/full_4gate_baseline
#   ./examples/run_example.sh --sync-example # also refreshes examples/full_4gate_baseline/ curated artifacts

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYNC_EXAMPLE=0
if [ "${1:-}" = "--sync-example" ]; then
    SYNC_EXAMPLE=1
    shift
fi

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
    echo "[run_example] Synchronized curated example outputs into ${DST}"
fi
