#!/usr/bin/env bash
set -euo pipefail

# Deterministic installation of IEEE Std 1666.1 SystemC-AMS PoC 2.3.4
# against system-installed SystemC 2.3.4 (Ubuntu 24.04 libsystemc-dev, C++17).

SYSTEMC_AMS_PREFIX="${SYSTEMC_AMS_HOME:-$HOME/.local/systemc-ams}"
SYSTEMC_AMS_REPO="https://github.com/Risto97/systemc-ams.git"
SYSTEMC_AMS_COMMIT="a72d365f"
WORK_DIR="${TMPDIR:-/tmp}/systemc-ams-build"

if [ -f "$SYSTEMC_AMS_PREFIX/include/systemc-ams.h" ] && \
   ( [ -f "$SYSTEMC_AMS_PREFIX/lib/libsystemc-ams.a" ] || \
     [ -f "$SYSTEMC_AMS_PREFIX/lib/libsystemc-ams.so" ] || \
     [ -f "$SYSTEMC_AMS_PREFIX/lib-linux64/libsystemc-ams.a" ] || \
     [ -f "$SYSTEMC_AMS_PREFIX/lib-linux64/libsystemc-ams.so" ] ); then
    echo "SystemC-AMS 2.3.4 already installed at $SYSTEMC_AMS_PREFIX"
    exit 0
fi

echo "Building SystemC-AMS PoC 2.3.4 -> $SYSTEMC_AMS_PREFIX"
rm -rf "$WORK_DIR"
git clone "$SYSTEMC_AMS_REPO" "$WORK_DIR"
git -C "$WORK_DIR" checkout "$SYSTEMC_AMS_COMMIT"

# Preserve autotools generated-file timestamp ordering after git checkout so
# make never tries to regenerate aclocal.m4 / configure with version-pinned aclocal-1.16.
touch -d "+2 seconds" "$WORK_DIR/aclocal.m4"
touch -d "+4 seconds" "$WORK_DIR/configure"
find "$WORK_DIR" -name 'config.h.in' -exec touch -d "+5 seconds" {} +
find "$WORK_DIR" -name 'Makefile.in' -exec touch -d "+6 seconds" {} +

# Create a SystemC staging view compatible with SystemC-AMS configure/CMake if using Debian/Ubuntu multiarch
SYSTEMC_VIEW="$WORK_DIR/systemc-view"
mkdir -p "$SYSTEMC_VIEW/include" "$SYSTEMC_VIEW/lib-linux64"
if [ -n "${SYSTEMC_HOME:-}" ] && [ -d "$SYSTEMC_HOME/include" ]; then
    SYSTEMC_ROOT="$SYSTEMC_HOME"
else
    ln -sf /usr/include/systemc "$SYSTEMC_VIEW/include/systemc"
    ln -sf /usr/include/systemc.h "$SYSTEMC_VIEW/include/systemc.h"
    ln -sf /usr/include/sysc "$SYSTEMC_VIEW/include/sysc"
    ln -sf /usr/include/tlm "$SYSTEMC_VIEW/include/tlm" 2>/dev/null || true
    ln -sf /usr/include/tlm.h "$SYSTEMC_VIEW/include/tlm.h" 2>/dev/null || true
    ln -sf /usr/include/tlm_core "$SYSTEMC_VIEW/include/tlm_core" 2>/dev/null || true
    ln -sf /usr/include/tlm_utils "$SYSTEMC_VIEW/include/tlm_utils" 2>/dev/null || true
    for f in /usr/lib/x86_64-linux-gnu/libsystemc*; do
        ln -sf "$f" "$SYSTEMC_VIEW/lib-linux64/$(basename "$f")"
    done
    ln -sf "$SYSTEMC_VIEW/lib-linux64" "$SYSTEMC_VIEW/lib"
    SYSTEMC_ROOT="$SYSTEMC_VIEW"
fi

BUILD_DIR="$WORK_DIR/build"
mkdir -p "$BUILD_DIR"
(
    cd "$BUILD_DIR"
    "$WORK_DIR/configure" \
        --prefix="$SYSTEMC_AMS_PREFIX" \
        --with-systemc="$SYSTEMC_ROOT" \
        --with-arch-suffix="" \
        --disable-systemc_compile_check \
        CXXFLAGS="-O3 -std=c++17 -DSC_CPLUSPLUS=201703L -fPIC"
    make -j"$(nproc)" ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true
    make install ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true
)

rm -rf "$WORK_DIR"
echo "SystemC-AMS PoC 2.3.4 successfully installed at $SYSTEMC_AMS_PREFIX"
ls -la "$SYSTEMC_AMS_PREFIX/include" "$SYSTEMC_AMS_PREFIX/lib"
