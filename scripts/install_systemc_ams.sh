#!/usr/bin/env bash
set -euo pipefail

# Deterministic, distro-independent source installation of IEEE Std 1666.1
# SystemC-AMS PoC 2.3.4 (C++17 ABI: SC_CPLUSPLUS=201703L).
#
# Automatically detects source-built SystemC (via SYSTEMC_HOME or standard
# portable prefixes) or falls back to distro-installed SystemC (/usr/include).

DEFAULT_PREFIX="${HOME}/.local/systemc-ams"
if [ -n "${IFOG_ENV_PREFIX:-}" ]; then
    DEFAULT_PREFIX="${IFOG_ENV_PREFIX}/systemc-ams"
fi
SYSTEMC_AMS_PREFIX="${SYSTEMC_AMS_HOME:-${DEFAULT_PREFIX}}"
SYSTEMC_AMS_REPO="${SYSTEMC_AMS_REPO:-https://github.com/Risto97/systemc-ams.git}"
SYSTEMC_AMS_COMMIT="${SYSTEMC_AMS_COMMIT:-a72d365f}"
WORK_DIR="${TMPDIR:-/tmp}/systemc-ams-build-$$"

if [ -f "${SYSTEMC_AMS_PREFIX}/include/systemc-ams.h" ] && \
   ( [ -f "${SYSTEMC_AMS_PREFIX}/lib/libsystemc-ams.a" ] || \
     [ -f "${SYSTEMC_AMS_PREFIX}/lib/libsystemc-ams.so" ] || \
     [ -f "${SYSTEMC_AMS_PREFIX}/lib-linux64/libsystemc-ams.a" ] || \
     [ -f "${SYSTEMC_AMS_PREFIX}/lib-linux64/libsystemc-ams.so" ] ); then
    echo "[install_systemc_ams] SystemC-AMS 2.3.4 already installed at ${SYSTEMC_AMS_PREFIX}"
    exit 0
fi

echo "[install_systemc_ams] Building SystemC-AMS PoC 2.3.4 -> ${SYSTEMC_AMS_PREFIX}"
trap 'rm -rf "${WORK_DIR}"' EXIT
rm -rf "${WORK_DIR}"
git clone "${SYSTEMC_AMS_REPO}" "${WORK_DIR}"
git -C "${WORK_DIR}" checkout "${SYSTEMC_AMS_COMMIT}"

# Preserve autotools generated-file timestamp ordering strictly in the past
# so configure's clock sanity check passes and make never runs aclocal-1.16.
find "${WORK_DIR}" -name 'configure.ac' -o -name '*.m4' -o -name 'Makefile.am' | xargs -r touch -d "-20 seconds"
touch -d "-15 seconds" "${WORK_DIR}/aclocal.m4"
touch -d "-10 seconds" "${WORK_DIR}/configure"
find "${WORK_DIR}" -name 'config.h.in' -exec touch -d "-8 seconds" {} +
find "${WORK_DIR}" -name 'Makefile.in' -exec touch -d "-5 seconds" {} +

# Locate SystemC headers & libs across portable source installs or distro multiarch paths
DETECTED_SC_HOME="${SYSTEMC_HOME:-}"
if [ -z "${DETECTED_SC_HOME}" ]; then
    for cand in \
        "${IFOG_ENV_PREFIX:-}/systemc" \
        "${HOME}/.local/ifog-env/systemc" \
        "/opt/ifog-env/systemc" \
        "${HOME}/.local/systemc"; do
        if [ -n "${cand}" ] && [ -f "${cand}/include/systemc.h" ]; then
            DETECTED_SC_HOME="${cand}"
            break
        fi
    done
fi

SYSTEMC_VIEW="${WORK_DIR}/systemc-view"
mkdir -p "${SYSTEMC_VIEW}/include" "${SYSTEMC_VIEW}/lib-linux64"

SC_REAL_LIBDIR=""
if [ -n "${DETECTED_SC_HOME}" ] && [ -f "${DETECTED_SC_HOME}/include/systemc.h" ]; then
    echo "[install_systemc_ams] Using SystemC at ${DETECTED_SC_HOME}"
    for item in "${DETECTED_SC_HOME}"/include/*; do
        ln -sf "${item}" "${SYSTEMC_VIEW}/include/$(basename "${item}")"
    done
    for libdir in "${DETECTED_SC_HOME}/lib" "${DETECTED_SC_HOME}/lib64" "${DETECTED_SC_HOME}/lib-linux64"; do
        if [ -d "${libdir}" ]; then
            for f in "${libdir}"/libsystemc*; do
                if [ -e "${f}" ]; then
                    ln -sf "${f}" "${SYSTEMC_VIEW}/lib-linux64/$(basename "${f}")"
                    [ -z "${SC_REAL_LIBDIR}" ] && SC_REAL_LIBDIR="${libdir}"
                fi
            done
        fi
    done
    ln -sf "${SYSTEMC_VIEW}/lib-linux64" "${SYSTEMC_VIEW}/lib"
    SYSTEMC_ROOT="${SYSTEMC_VIEW}"
elif [ -f "/usr/include/systemc.h" ]; then
    echo "[install_systemc_ams] Using distro-installed SystemC in /usr"
    ln -sf /usr/include/systemc "${SYSTEMC_VIEW}/include/systemc"
    ln -sf /usr/include/systemc.h "${SYSTEMC_VIEW}/include/systemc.h"
    ln -sf /usr/include/sysc "${SYSTEMC_VIEW}/include/sysc"
    ln -sf /usr/include/tlm "${SYSTEMC_VIEW}/include/tlm" 2>/dev/null || true
    ln -sf /usr/include/tlm.h "${SYSTEMC_VIEW}/include/tlm.h" 2>/dev/null || true
    ln -sf /usr/include/tlm_core "${SYSTEMC_VIEW}/include/tlm_core" 2>/dev/null || true
    ln -sf /usr/include/tlm_utils "${SYSTEMC_VIEW}/include/tlm_utils" 2>/dev/null || true
    for libdir in /usr/lib/x86_64-linux-gnu /usr/lib/aarch64-linux-gnu /usr/lib64 /usr/lib; do
        if [ -d "${libdir}" ]; then
            for f in "${libdir}"/libsystemc*; do
                if [ -e "${f}" ]; then
                    ln -sf "${f}" "${SYSTEMC_VIEW}/lib-linux64/$(basename "${f}")"
                    [ -z "${SC_REAL_LIBDIR}" ] && SC_REAL_LIBDIR="${libdir}"
                fi
            done
        fi
    done
    ln -sf "${SYSTEMC_VIEW}/lib-linux64" "${SYSTEMC_VIEW}/lib"
    SYSTEMC_ROOT="${SYSTEMC_VIEW}"
else
    echo "ERROR: SystemC 2.3.4 not found. Run scripts/install_systemc.sh or set SYSTEMC_HOME." >&2
    exit 1
fi

EXTRA_LDFLAGS=""
if [ -n "${SC_REAL_LIBDIR}" ]; then
    EXTRA_LDFLAGS="-L${SC_REAL_LIBDIR} -Wl,-rpath,${SC_REAL_LIBDIR}"
fi

BUILD_DIR="${WORK_DIR}/build"
mkdir -p "${BUILD_DIR}"
(
    cd "${BUILD_DIR}"
    "${WORK_DIR}/configure" \
        --prefix="${SYSTEMC_AMS_PREFIX}" \
        --libdir="${SYSTEMC_AMS_PREFIX}/lib" \
        --with-systemc="${SYSTEMC_ROOT}" \
        --with-arch-suffix="" \
        --disable-static \
        --disable-systemc_compile_check \
        CXXFLAGS="-O3 -std=c++17 -DSC_CPLUSPLUS=201703L -fPIC" \
        LDFLAGS="${EXTRA_LDFLAGS}"
    make -j"$(nproc)" ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true
    make install ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true
)

echo "[install_systemc_ams] SystemC-AMS PoC 2.3.4 successfully installed at ${SYSTEMC_AMS_PREFIX}"
ls -la "${SYSTEMC_AMS_PREFIX}/include" "${SYSTEMC_AMS_PREFIX}/lib"
