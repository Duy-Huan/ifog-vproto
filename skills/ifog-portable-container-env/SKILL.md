---
name: ifog-portable-container-env
description: Distro-independent Linux source build toolchain (Accellera SystemC 2.3.4, SystemC-AMS PoC 2.3.4, nlohmann/json v3.11.3, isolated Python venv) and OCI Docker/Podman container workflows (Containerfile, Dockerfile, compose.yaml, container_run.sh).
---

# Portable Linux Toolchain & Docker / Podman Container Environment

## 1. Distro-Independent Source Build Toolchain (`scripts/`)
- Never assume Ubuntu/Debian `libsystemc-dev` or `nlohmann-json3-dev` exists on target Linux machines (Fedora, Rocky/RHEL, Arch, HPC clusters without root).
- **`scripts/install_systemc.sh`**: Clones official Accellera SystemC `2.3.4` from Git (`https://github.com/accellera-official/systemc.git`), compiles with CMake (`-DCMAKE_CXX_STANDARD=17 -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_SHARED_LIBS=ON`), installs to `$SYSTEMC_HOME`, and symlinks `lib-linux64 -> lib` for SystemC-AMS autotools compatibility across all distros.
- **`scripts/install_systemc_ams.sh`**: Automatically detects source-built SystemC (`$SYSTEMC_HOME`, `/opt/ifog-env/systemc`, `$HOME/.local/ifog-env/systemc`) or falls back to distro `/usr/include/systemc.h`, builds SystemC-AMS PoC `2.3.4` (pinned commit `a72d365f`) with `--disable-static` (cutting libtool compile time in half by compiling shared `.so` objects once instead of twice), explicit `LDFLAGS="-L${SC_REAL_LIBDIR} -Wl,-rpath,${SC_REAL_LIBDIR}"` (**critical trap:** without explicit `LDFLAGS`, SystemC-AMS's `libtool` links `-lsystemc` against a distro `/usr/lib/x86_64-linux-gnu/libsystemc-2.3.4.so` while `ifog_sim` links `$SYSTEMC_HOME/lib/libsystemc.so.2.3`, loading two conflicting `sc_simcontext` singletons and causing an immediate segfault!), past-ordered autotools timestamps (`-20s..-5s`), and `ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true` so `configure` and `make` never fail on newer automake images.
- **`scripts/setup_env.sh`**: Single universal bootstrapper installing SystemC 2.3.4 + SystemC-AMS 2.3.4 + `nlohmann/json` `v3.11.3` from Git + isolated Python venv (`<prefix>/venv`) + auto-generated `<prefix>/env.sh`. Supports non-root installs (`~/.local/ifog-env`) and root/container installs (`/opt/ifog-env`).
- **`scripts/env.sh`**: Tracked sourceable helper auto-discovering `/opt/ifog-env` or `~/.local/ifog-env` and exporting `SYSTEMC_HOME`, `SYSTEMC_AMS_HOME`, `CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`, `PKG_CONFIG_PATH`, `VIRTUAL_ENV`, and `PATH`. Automatically sourced by `scripts/run_sim.sh`.
- **`tier2_sysc_ams/CMakeLists.txt`**: Searches `lib`, `lib64`, `lib-linux64`, `lib/x86_64-linux-gnu`, `lib/aarch64-linux-gnu` across `$SYSTEMC_HOME`, `$SYSTEMC_AMS_HOME`, `$IFOG_ENV_PREFIX`, `~/.local/ifog-env`, `/opt/ifog-env`, and `/usr`.

## 2. Docker & Podman OCI Containerization
- **`Containerfile`** and **`Dockerfile`** are maintained byte-identical (enforced in unit tests) for seamless compatibility with both `podman build` and `docker build`.
- Layer order is optimized for fast rebuilds: (1) minimal OS toolchain, (2) Git-built C++ deps (`SystemC` + `SystemC-AMS` + `nlohmann/json`), (3) isolated Python venv deps, (4) repo copy + editable install + pre-built `build/ifog_sim` Release `-O3` + `ifog_cpp_tests` verification.
- **`compose.yaml`** follows the OCI Compose specification (works identically with `docker compose` and `podman compose`).
- **`scripts/container_run.sh`** auto-detects `podman` or `docker`, appends `:Z` volume relabeling and `--userns=keep-id` automatically for rootless SELinux Podman hosts, and provides `build`, `shell`, `sim`, `example`, `test`, and `verify` subcommands.

## 3. Complete Example Package (`examples/full_4gate_baseline/`)
- Commits a complete real 4-Gate baseline execution (`report.md`, `report.html`, `metrics_summary.json`, all Tier 1–3 JSONs, and all 4 300-DPI PNG figures) while excluding multi-hundred-MB raw `.bin` streams so repository stakeholders can evaluate physical accuracy and feasibility directly on GitHub or reproduce bit-identically via `./examples/run_example.sh`.
