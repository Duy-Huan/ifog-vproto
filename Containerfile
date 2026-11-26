# syntax=docker/dockerfile:1
# Portable OCI Containerfile (compatible with both Docker and Podman)
# Builds Accellera SystemC 2.3.4, SystemC-AMS PoC 2.3.4, nlohmann/json v3.11.3
# from Git + isolated Python 3.12 virtual environment (with FMPy) + Tier 2 Release (-O3) core
# + standalone FMI 3.0 Co-Simulation FMU (build/ifog_core.fmu).
#
# Build:
#   docker build -t ifog-vproto:3.0.1 .
#   podman build -f Containerfile -t ifog-vproto:3.0.1 .
#
# Run:
#   docker run --rm -v "$PWD/report:/workspace/ifog-vproto/report" ifog-vproto:3.0.1 \
#     ./scripts/run_all_scenarios.sh --run-id docker_all_scenarios

FROM ubuntu:24.04

LABEL org.opencontainers.image.title="ifog-vproto" \
      org.opencontainers.image.description="Closed-Loop IFOG Multi-Scale Virtual Prototype + FMI 3.0 FMU (IFOG-SIM-SPEC-006)" \
      org.opencontainers.image.version="3.0.1" \
      org.opencontainers.image.source="https://github.com/Duy-Huan/ifog-vproto"

ENV DEBIAN_FRONTEND=noninteractive \
    IFOG_ENV_PREFIX=/opt/ifog-env \
    SYSTEMC_HOME=/opt/ifog-env/systemc \
    SYSTEMC_AMS_HOME=/opt/ifog-env/systemc-ams \
    CMAKE_PREFIX_PATH=/opt/ifog-env/nlohmann_json \
    LD_LIBRARY_PATH=/opt/ifog-env/systemc/lib:/opt/ifog-env/systemc-ams/lib \
    PKG_CONFIG_PATH=/opt/ifog-env/systemc/lib/pkgconfig:/opt/ifog-env/systemc-ams/lib/pkgconfig \
    VIRTUAL_ENV=/opt/ifog-env/venv \
    MPLBACKEND=Agg \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/ifog-env/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 1. Base C++17 / CMake / Autotools / Python / Coverage toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git autoconf automake libtool pkg-config \
    python3 python3-venv python3-dev gcovr lcov ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace/ifog-vproto

# 2. Layer-cached C++ dependency build from Git (SystemC 2.3.4 + SystemC-AMS 2.3.4 + nlohmann/json v3.11.3)
COPY scripts/install_systemc.sh scripts/install_systemc_ams.sh scripts/setup_env.sh scripts/
RUN chmod +x scripts/install_systemc.sh scripts/install_systemc_ams.sh scripts/setup_env.sh \
    && bash scripts/setup_env.sh --prefix /opt/ifog-env --skip-python

# 3. Layer-cached isolated Python 3.12 virtual environment (with FMPy)
RUN bash scripts/setup_env.sh --prefix /opt/ifog-env \
    --skip-systemc --skip-systemc-ams --skip-nlohmann --skip-editable \
    && ln -sf /opt/ifog-env/env.sh /etc/profile.d/ifog-env.sh

# 4. Copy full repository, install editable package, pre-build Tier 2 Release (-O3) core & FMI 3.0 FMU
COPY . /workspace/ifog-vproto
RUN chmod +x scripts/*.sh scripts/*.py examples/*.sh 2>/dev/null || true \
    && python3 -m pip install -e /workspace/ifog-vproto --no-build-isolation --no-deps \
    && cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build -j"$(nproc)" \
    && cmake --build build --target package_fmu \
    && ./build/ifog_cpp_tests \
    && python3 -c "from fmpy.validation import validate_fmu; probs = validate_fmu('build/ifog_core.fmu'); assert not probs, probs" \
    && sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256 spec/IFOG-SIM-SPEC-006.sha256

CMD ["bash"]
