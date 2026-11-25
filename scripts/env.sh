#!/usr/bin/env bash
# Source this script to export SystemC, SystemC-AMS, nlohmann/json, and Python venv
# variables on any Linux host or inside Docker/Podman containers:
#   source scripts/env.sh

_IFOG_PREFIX=""
for _cand in \
    "${IFOG_ENV_PREFIX:-}" \
    "/opt/ifog-env" \
    "${HOME}/.local/ifog-env"; do
    if [ -n "${_cand}" ] && [ -f "${_cand}/env.sh" ]; then
        _IFOG_PREFIX="${_cand}"
        break
    fi
done

if [ -n "${_IFOG_PREFIX}" ]; then
    # shellcheck source=/dev/null
    source "${_IFOG_PREFIX}/env.sh"
else
    # Fallback to standalone ~/.local/systemc-ams when using distro SystemC
    if [ -d "${HOME}/.local/systemc-ams" ]; then
        export SYSTEMC_AMS_HOME="${SYSTEMC_AMS_HOME:-${HOME}/.local/systemc-ams}"
        export LD_LIBRARY_PATH="${SYSTEMC_AMS_HOME}/lib:${LD_LIBRARY_PATH:-}"
    fi
    export MPLBACKEND="${MPLBACKEND:-Agg}"
fi
unset _IFOG_PREFIX _cand
