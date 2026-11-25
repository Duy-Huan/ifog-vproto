#!/usr/bin/env bash
set -euo pipefail

# Unified Docker / Podman container helper for ifog-vproto.
# Auto-detects podman or docker (override via --engine docker|podman or CONTAINER_ENGINE env).
#
# Usage:
#   ./scripts/container_run.sh [--engine docker|podman] [--tag TAG] <command> [args...]
#
# Commands:
#   build              Build the OCI container image (SystemC 2.3.4 + SystemC-AMS 2.3.4 + Python venv + Tier 2)
#   shell              Start an interactive bash shell with data/ and report/ mounted
#   sim [args...]      Run ./scripts/run_sim.sh inside the container (outputs appear in host report/ & data/)
#   example            Run ALL official scenarios (Gates 1-5 + 6 TD + 5 ENG, MC=500) inside the container -> report/
#   test               Run unit tests, 41 formulas, 100% C++ & Python coverage inside the container
#   verify             Run full verification including all real system scenario tests inside the container

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IFOG_IMAGE_TAG:-ifog-vproto:2.1.0}"
ENGINE="${CONTAINER_ENGINE:-}"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --engine) ENGINE="$2"; shift 2 ;;
        --tag) IMAGE_TAG="$2"; shift 2 ;;
        -h|--help)
            sed -n '4,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *) break ;;
    esac
done

if [ -z "${ENGINE}" ]; then
    if command -v podman >/dev/null 2>&1; then
        ENGINE="podman"
    elif command -v docker >/dev/null 2>&1; then
        ENGINE="docker"
    else
        echo "ERROR: Neither 'podman' nor 'docker' found on PATH." >&2
        exit 1
    fi
fi

CMD="${1:-help}"
if [ "$#" -gt 0 ]; then
    shift
fi

mkdir -p "${REPO_ROOT}/data" "${REPO_ROOT}/report"

VOL_OPT=""
EXTRA_RUN_ARGS=()
if [ "${ENGINE}" = "podman" ]; then
    VOL_OPT=":Z"
    EXTRA_RUN_ARGS+=(--userns=keep-id)
fi

case "${CMD}" in
    build)
        echo "[container_run] Building ${IMAGE_TAG} with ${ENGINE}..."
        "${ENGINE}" build -f "${REPO_ROOT}/Containerfile" -t "${IMAGE_TAG}" "${REPO_ROOT}"
        ;;
    shell)
        "${ENGINE}" run --rm -it "${EXTRA_RUN_ARGS[@]}" \
            -v "${REPO_ROOT}/data:/workspace/ifog-vproto/data${VOL_OPT}" \
            -v "${REPO_ROOT}/report:/workspace/ifog-vproto/report${VOL_OPT}" \
            "${IMAGE_TAG}" bash
        ;;
    sim)
        "${ENGINE}" run --rm "${EXTRA_RUN_ARGS[@]}" \
            -v "${REPO_ROOT}/data:/workspace/ifog-vproto/data${VOL_OPT}" \
            -v "${REPO_ROOT}/report:/workspace/ifog-vproto/report${VOL_OPT}" \
            "${IMAGE_TAG}" ./scripts/run_sim.sh "$@"
        ;;
    example)
        "${ENGINE}" run --rm "${EXTRA_RUN_ARGS[@]}" \
            -v "${REPO_ROOT}/data:/workspace/ifog-vproto/data${VOL_OPT}" \
            -v "${REPO_ROOT}/report:/workspace/ifog-vproto/report${VOL_OPT}" \
            "${IMAGE_TAG}" ./scripts/run_all_scenarios.sh --run-id full_all_scenarios "$@"
        ;;
    test)
        "${ENGINE}" run --rm "${EXTRA_RUN_ARGS[@]}" "${IMAGE_TAG}" bash -lc \
            "sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256 && python3 scripts/verify_doc_sync.py && bash scripts/run_cpp_coverage.sh && python3 scripts/verify_formulas_ci.py && pytest tests/unit tests/formula_verification --cov --cov-report=term-missing"
        ;;
    verify)
        "${ENGINE}" run --rm "${EXTRA_RUN_ARGS[@]}" "${IMAGE_TAG}" bash -lc \
            "sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256 && python3 scripts/verify_doc_sync.py && bash scripts/run_cpp_coverage.sh && python3 scripts/verify_formulas_ci.py && pytest tests/unit tests/formula_verification --cov --cov-report=term-missing && pytest tests/system -v"
        ;;
    *)
        sed -n '4,16p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
        exit 0
        ;;
esac
