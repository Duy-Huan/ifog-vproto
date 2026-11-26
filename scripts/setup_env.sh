#!/usr/bin/env bash
set -euo pipefail

# Universal, distro-independent Linux environment bootstrapper for ifog-vproto.
# Pulls & builds SystemC 2.3.4, SystemC-AMS PoC 2.3.4, nlohmann/json v3.11.3
# from Git, sets up an isolated Python virtual environment, writes an
# environment activation script, and optionally compiles & verifies Tier 2.
#
# Works on Ubuntu/Debian, Fedora/RHEL/Rocky, Arch, HPC clusters (non-root),
# Docker, and Podman containers.
#
# Usage:
#   bash scripts/setup_env.sh [options]
#     --prefix DIR         Install prefix (default: /opt/ifog-env if root, else ~/.local/ifog-env)
#     --with-system-deps   Install base build tools via apt-get / dnf / pacman
#     --skip-systemc       Skip building SystemC 2.3.4
#     --skip-systemc-ams   Skip building SystemC-AMS PoC 2.3.4
#     --skip-nlohmann      Skip installing nlohmann/json from Git
#     --skip-python        Skip creating Python venv & pip installs
#     --skip-editable      Install Python deps into venv without pip install -e . (for container layer caching)
#     --build-tier2        Compile Tier 2 Release (-O3) C++ simulator after setup
#     --verify             Run C++ tests, spec SHA-256 check, and Rule 16 doc-sync check

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "$(id -u)" -eq 0 ]; then
    PREFIX="/opt/ifog-env"
else
    PREFIX="${HOME}/.local/ifog-env"
fi

WITH_SYS_DEPS=0
SKIP_SC=0
SKIP_SCAMS=0
SKIP_NLOHMANN=0
SKIP_PYTHON=0
SKIP_EDITABLE=0
BUILD_TIER2=0
VERIFY=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --prefix) PREFIX="$2"; shift 2 ;;
        --with-system-deps) WITH_SYS_DEPS=1; shift ;;
        --skip-systemc) SKIP_SC=1; shift ;;
        --skip-systemc-ams) SKIP_SCAMS=1; shift ;;
        --skip-nlohmann) SKIP_NLOHMANN=1; shift ;;
        --skip-python) SKIP_PYTHON=1; shift ;;
        --skip-editable) SKIP_EDITABLE=1; shift ;;
        --build-tier2) BUILD_TIER2=1; shift ;;
        --verify) VERIFY=1; shift ;;
        -h|--help)
            sed -n '4,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
            exit 0
            ;;
        *)
            echo "ERROR: Unknown argument '$1'" >&2
            exit 1
            ;;
    esac
done

mkdir -p "${PREFIX}"

if [ "${WITH_SYS_DEPS}" -eq 1 ]; then
    echo "[setup_env] Installing base Linux build prerequisites..."
    SUDO=""
    if [ "$(id -u)" -ne 0 ] && command -v sudo >/dev/null 2>&1; then
        SUDO="sudo"
    fi
    if command -v apt-get >/dev/null 2>&1; then
        ${SUDO} apt-get update
        ${SUDO} env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            build-essential cmake git autoconf automake libtool pkg-config \
            python3 python3-venv python3-dev gcovr lcov ca-certificates
    elif command -v dnf >/dev/null 2>&1; then
        ${SUDO} dnf install -y \
            gcc gcc-c++ make cmake git autoconf automake libtool pkgconf-pkg-config \
            python3 python3-devel python3-pip gcovr lcov ca-certificates
    elif command -v pacman >/dev/null 2>&1; then
        ${SUDO} pacman -Sy --noconfirm --needed \
            base-devel cmake git autoconf automake libtool pkgconf \
            python python-pip gcovr lcov ca-certificates
    else
        echo "WARNING: Unsupported package manager; ensure gcc/g++, cmake, git, make, python3 are installed." >&2
    fi
fi

export IFOG_ENV_PREFIX="${PREFIX}"
export SYSTEMC_HOME="${PREFIX}/systemc"
export SYSTEMC_AMS_HOME="${PREFIX}/systemc-ams"
NLOHMANN_PREFIX="${PREFIX}/nlohmann_json"
VENV_DIR="${PREFIX}/venv"

# 1. SystemC 2.3.4 from Accellera Git
if [ "${SKIP_SC}" -eq 0 ]; then
    bash "${REPO_ROOT}/scripts/install_systemc.sh"
fi

# 2. SystemC-AMS PoC 2.3.4 from Git
if [ "${SKIP_SCAMS}" -eq 0 ]; then
    bash "${REPO_ROOT}/scripts/install_systemc_ams.sh"
fi

# 3. nlohmann/json v3.11.3 from Git (if not already present in prefix or system)
if [ "${SKIP_NLOHMANN}" -eq 0 ]; then
    if [ -f "${NLOHMANN_PREFIX}/include/nlohmann/json.hpp" ] || [ -f "/usr/include/nlohmann/json.hpp" ]; then
        echo "[setup_env] nlohmann/json already available."
    else
        echo "[setup_env] Installing nlohmann/json v3.11.3 from Git -> ${NLOHMANN_PREFIX}"
        NL_TMP="${TMPDIR:-/tmp}/nlohmann-json-$$"
        rm -rf "${NL_TMP}"
        git clone --depth 1 --branch v3.11.3 https://github.com/nlohmann/json.git "${NL_TMP}"
        cmake -S "${NL_TMP}" -B "${NL_TMP}/build" \
            -DCMAKE_INSTALL_PREFIX="${NLOHMANN_PREFIX}" \
            -DJSON_BuildTests=OFF
        cmake --install "${NL_TMP}/build"
        rm -rf "${NL_TMP}"
    fi
fi

# 4. Python virtual environment + dependencies
if [ "${SKIP_PYTHON}" -eq 0 ]; then
    echo "[setup_env] Setting up Python virtual environment at ${VENV_DIR}"
    if [ ! -x "${VENV_DIR}/bin/python3" ]; then
        python3 -m venv "${VENV_DIR}"
    fi
    "${VENV_DIR}/bin/python3" -m pip install --upgrade pip setuptools wheel
    "${VENV_DIR}/bin/python3" -m pip install \
        "numpy>=1.26" "scipy>=1.12" "matplotlib>=3.8" "plotly>=5.18" "jsonschema>=4.20" "fmpy>=0.3.20" \
        "pytest>=8.0" "pytest-cov>=4.1" "pytest-xdist>=3.5"
    if [ "${SKIP_EDITABLE}" -eq 0 ] && [ -f "${REPO_ROOT}/pyproject.toml" ]; then
        "${VENV_DIR}/bin/python3" -m pip install -e "${REPO_ROOT}" --no-build-isolation --no-deps
    fi
fi

# 5. Write self-contained prefix env activation file
cat > "${PREFIX}/env.sh" <<EOF
# Auto-generated by scripts/setup_env.sh — source this file to activate ifog-vproto toolchain
export IFOG_ENV_PREFIX="${PREFIX}"
export SYSTEMC_HOME="${SYSTEMC_HOME}"
export SYSTEMC_AMS_HOME="${SYSTEMC_AMS_HOME}"
export CMAKE_PREFIX_PATH="${NLOHMANN_PREFIX}:\${CMAKE_PREFIX_PATH:-}"
export LD_LIBRARY_PATH="${SYSTEMC_HOME}/lib:${SYSTEMC_AMS_HOME}/lib:\${LD_LIBRARY_PATH:-}"
export PKG_CONFIG_PATH="${SYSTEMC_HOME}/lib/pkgconfig:${SYSTEMC_AMS_HOME}/lib/pkgconfig:\${PKG_CONFIG_PATH:-}"
export MPLBACKEND="Agg"
if [ -d "${VENV_DIR}/bin" ]; then
    export VIRTUAL_ENV="${VENV_DIR}"
    case ":\${PATH}:" in
        *":${VENV_DIR}/bin:"*) ;;
        *) export PATH="${VENV_DIR}/bin:\${PATH}" ;;
    esac
fi
EOF
echo "[setup_env] Wrote environment activation file: ${PREFIX}/env.sh"

# Activate for optional build/verify steps
# shellcheck source=/dev/null
source "${PREFIX}/env.sh"

if [ "${BUILD_TIER2}" -eq 1 ]; then
    echo "[setup_env] Building Tier 2 SystemC-AMS Core (Release -O3) & FMI 3.0 FMU..."
    cmake -S "${REPO_ROOT}/tier2_sysc_ams" -B "${REPO_ROOT}/build" -DCMAKE_BUILD_TYPE=Release
    cmake --build "${REPO_ROOT}/build" -j"$(nproc)"
    cmake --build "${REPO_ROOT}/build" --target package_fmu
fi

if [ "${VERIFY}" -eq 1 ]; then
    echo "[setup_env] Verifying installed environment..."
    "${REPO_ROOT}/build/ifog_cpp_tests"
    python3 -c "from fmpy.validation import validate_fmu; probs = validate_fmu('${REPO_ROOT}/build/ifog_core.fmu'); assert not probs, probs"
    (cd "${REPO_ROOT}" && sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256 spec/IFOG-SIM-SPEC-006.sha256)
    python3 "${REPO_ROOT}/scripts/verify_doc_sync.py"
fi

echo ""
echo "[setup_env] Done! Activate this environment in any shell with:"
echo "    source ${PREFIX}/env.sh"
echo "  (or from repo root: source scripts/env.sh)"
