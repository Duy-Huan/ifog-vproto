#!/usr/bin/env bash
set -euo pipefail

# Portable, distro-independent source installation of Accellera SystemC 2.3.4
# (IEEE Std 1666, C++17 ABI: SC_CPLUSPLUS=201703L) for any Linux distribution.
#
# Usage:
#   SYSTEMC_HOME=/opt/ifog-env/systemc bash scripts/install_systemc.sh
#   bash scripts/install_systemc.sh  # defaults to $HOME/.local/ifog-env/systemc (or /opt/ifog-env/systemc if root)

DEFAULT_PREFIX="${HOME}/.local/ifog-env/systemc"
if [ "$(id -u)" -eq 0 ]; then
    DEFAULT_PREFIX="/opt/ifog-env/systemc"
fi

SYSTEMC_PREFIX="${SYSTEMC_HOME:-${DEFAULT_PREFIX}}"
SYSTEMC_REPO="${SYSTEMC_REPO:-https://github.com/accellera-official/systemc.git}"
SYSTEMC_TAG="${SYSTEMC_TAG:-2.3.4}"
WORK_DIR="${TMPDIR:-/tmp}/systemc-src-build-$$"

if [ -f "${SYSTEMC_PREFIX}/include/systemc.h" ] && \
   ( [ -f "${SYSTEMC_PREFIX}/lib/libsystemc.so" ] || \
     [ -f "${SYSTEMC_PREFIX}/lib/libsystemc.a" ] || \
     [ -f "${SYSTEMC_PREFIX}/lib64/libsystemc.so" ] || \
     [ -f "${SYSTEMC_PREFIX}/lib-linux64/libsystemc.so" ] ); then
    echo "[install_systemc] SystemC ${SYSTEMC_TAG} already installed at ${SYSTEMC_PREFIX}"
    exit 0
fi

echo "[install_systemc] Cloning Accellera SystemC ${SYSTEMC_TAG} -> ${SYSTEMC_PREFIX}"
trap 'rm -rf "${WORK_DIR}"' EXIT
rm -rf "${WORK_DIR}"
git clone --depth 1 --branch "${SYSTEMC_TAG}" "${SYSTEMC_REPO}" "${WORK_DIR}"

cmake -S "${WORK_DIR}" -B "${WORK_DIR}/build" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=17 \
    -DCMAKE_CXX_STANDARD_REQUIRED=ON \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DCMAKE_INSTALL_PREFIX="${SYSTEMC_PREFIX}" \
    -DCMAKE_INSTALL_LIBDIR=lib \
    -DBUILD_SHARED_LIBS=ON \
    -DENABLE_PTHREADS=ON

cmake --build "${WORK_DIR}/build" -j"$(nproc)"
cmake --install "${WORK_DIR}/build"

# Ensure lib-linux64 symlink exists for SystemC-AMS autotools compatibility on all Linux distros
if [ -d "${SYSTEMC_PREFIX}/lib" ] && [ ! -e "${SYSTEMC_PREFIX}/lib-linux64" ]; then
    ln -s lib "${SYSTEMC_PREFIX}/lib-linux64"
fi

echo "[install_systemc] SystemC ${SYSTEMC_TAG} successfully installed at ${SYSTEMC_PREFIX}"
ls -la "${SYSTEMC_PREFIX}/include/systemc.h" "${SYSTEMC_PREFIX}/lib"
