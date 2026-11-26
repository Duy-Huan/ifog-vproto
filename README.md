# `ifog-vproto` — Closed-Loop IFOG Multi-Scale Virtual Prototype & FMI 3.0 FMU

[![Version](https://img.shields.io/badge/Release-v3.0.0-0E6251)](docs/RELEASE_NOTES.md)
[![Spec](https://img.shields.io/badge/Spec-IFOG--SIM--SPEC--006%20v6.0-1B365D)](spec/IFOG-SIM-SPEC-006.pdf)
[![FMI](https://img.shields.io/badge/FMI-3.0%20Co--Simulation%20FMU-0E6251)](spec/IFOG-SIM-SPEC-006.md)
[![Formulas](https://img.shields.io/badge/Formulas-44%2F44%20Verified-0E6251)](AGENT.md)
[![Coverage](https://img.shields.io/badge/Coverage-100%25%20C%2B%2B%20%26%20Python-brightgreen)](AGENT.md)

A spec-driven, 3-Tier Hybrid Multi-Scale Co-Simulation Virtual Prototype & **Standalone FMI 3.0 Co-Simulation FMU (`build/ifog_core.fmu`)** for a **Closed-Loop Interferometric Fiber-Optic Gyroscope (2-State, 4-State Lefèvre, and Official 6-State Symmetric Modulation)** built on **Python + C++17 / IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4 + FMI 3.0.2** (`IFOG-SIM-SPEC-006` v6.0, preserving `SPEC-005` v5.0 & `SPEC-004` v4.0).

---

## Standalone FMI 3.0 Co-Simulation FMU (`build/ifog_core.fmu`)

Under **`IFOG-SIM-SPEC-006` (v6.0)**, Tier 2 (`tier2_sysc_ams`) is wrapped via [`fmi_wrapper/`](fmi_wrapper/) into a tool-agnostic **FMI 3.0 Co-Simulation FMU (`build/ifog_core.fmu`)** ready for FMPy, Simulink, Dymola, Ansys Twin Builder, OpenModelica, or 6-DOF INS/GNC testbeds without modifying any underlying optical/AFE/DSP physics:

```bash
# Build Tier 2 Release (-O3, -fPIC) and package standalone FMI 3.0 FMU
cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
cmake --build build --target package_fmu

# Validate FMI 3.0 XML schema & run Gate 6 (Equivalence <1e-12, Deadband, 5-Region AVAR)
./scripts/run_sim.sh --mode fmi_gate --run-id gate6_fmi3_fmu
```

---

## Live Complete All-Scenarios Example (All 21 Gates & Scenarios Committed to Repo)

Inspect the **complete genuine full-scale output of ALL 21 official gates & scenarios** (Gates 1–4 with 4×60 s Fast-Scale + 12×10 h Slow-Scale AVAR + Gate 5 Official 6-State DSP + **Gate 6 FMI 3.0 Black-Box FMU** + 6 Time-Domain `TD-01`..`TD-06` + 5 System Engineering `ENG-01`..`ENG-05` with `N=500` MC + 4 Dynamic Response, Output PSD & Electro-Optic Probe `DYN-01`..`DYN-04`, zero mocks / zero smoke tests) directly in [`examples/full_all_scenarios/`](examples/full_all_scenarios/README.md):
- **Visual Walkthrough (All 21 300-DPI Figures):** [`examples/full_all_scenarios/README.md`](examples/full_all_scenarios/README.md)
- **Auto-Generated Markdown & 20-Chart Interactive Plotly HTML5 Reports:** [`report.md`](examples/full_all_scenarios/report.md) | [`report.html`](examples/full_all_scenarios/report.html) | [`metrics_summary.json`](examples/full_all_scenarios/metrics_summary.json) | [`virtual_calibration_dataset.csv`](examples/full_all_scenarios/virtual_calibration_dataset.csv)
- **One-Command Reproduction (Native or Docker/Podman):** `./examples/run_example.sh` or `./scripts/run_all_scenarios.sh` or `./scripts/container_run.sh example`
- *(Archival SPEC-004 4-Gate only example preserved in [`examples/full_4gate_baseline/`](examples/full_4gate_baseline/README.md).)*

---

## Official Simulation Flow — 6 Gates + 6 Time-Domain + 5 Engineering + 4 Dynamic/Electro-Optic Scenarios

Every scenario is runnable **individually via CLI** (`./scripts/run_sim.sh --mode <mode>`) or **end-to-end in one command** (`./scripts/run_all_scenarios.sh` / `./examples/run_example.sh`), automatically exporting Markdown (`report.md`), interactive Plotly HTML5 (`report.html` with up to **20 interactive multi-panel charts**), up to **21 300-DPI PNG figures**, and CSV/JSON datasets into `report/<run_id>/`.

Full methodology, equations, and verified real-simulation benchmarks are documented in [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf).

| Category | CLI Mode (`--mode`) | Highlighted Verified Real SystemC-AMS / FMI 3.0 Result |
| :--- | :--- | :--- |
| **Complete Official Suite** | `all_scenarios` (`scripts/run_all_scenarios.sh` / `examples/run_example.sh`) | Executes Gates 1–6 + 6 TD + 5 ENG (`MC=500`) + 4 DYN -> **21/21 PASS**, **21 PNGs**, **20 interactive Plotly charts** |
| **Core Acceptance Gates** | `full` (`gate1`, `gate2`, `gate3`, `gate4`) | Gate 1 `3.10e-16 rad` (`1,666` wraps) \| Gate 2 `98.85%` reduction \| Gate 3 `-0.062` vs `-0.893` PSD \| Gate 4 `2.42%` overlap & 5 WLS params $\pm 10\%$ |
| **Gate 5 — Official 6-State DSP** | `dsp6_compare` (`configs/baseline_1km_6state.json`) | **$-33.3\%$ peak MIOC voltage**, `1.28e-16 rad` error, **`+136.94 dB`** (`7.03e6×`) RAM/xtalk/$\gamma_{\text{nl}}$ rejection (`EQ-31`–`EQ-34`) |
| **Gate 6 — FMI 3.0 Black-Box FMU** | `fmi_gate` (`tier3_analysis/fmi_master_runner.py`) | **0 FMI 3.0 XSD errors**, bit-exact **`0.00e+00 rad/s`** (`< 1e-12`) vs `ifog_sim` (4s & 6s), **`97.42%`** Deadband reduction, **`3.83%`** (`< 5%`) Dual-Regime 5-Region AVAR overlap (`EQ-42`–`EQ-44`) |
| **Group A — 6 Time-Domain** | `td_all` (`td_blanking`, `td_step_sine`, `td_vpi_shock`, `td_high_rate`, `td_shupe_shock`, `td_limit_cycles`) | Sub-$\tau$ $k_{\text{start}}^*=5$ \| $-3\text{ dB}$ BW `2,540 Hz` \| $+5\%$ $V_\pi$ shock (`2×` lower 6s disturbance) \| `700 deg/s` (`7,184` wraps, anti-windup) \| Shupe `99.74%` filter \| 12-bit PRBS (`3->1,595` codes) |
| **Group B — 5 Engineering** | `eng_all` (`eng_hw_sizing`, `eng_imu_3axis`, `eng_vre_faraday`, `eng_fault_bit`, `eng_mc_yield_cal`) | Min ENOB `12-bit` \| 3-Axis IMU Axis-Y xtalk `40.63 -> 0.106 deg/h` (`+51.6 dB`) \| VRE $R^2=0.9998$ & Mu-metal `25.25 dB` \| 5/5 BIT faults $\le 30\ \mu\text{s}$ + SEU FDIR \| `N=500` MC Yield `97.2%` ($C_{pk}=0.604$) & `-40..+85°C` Cal (`99.98%` Poly / `99.95%` EKF) |
| **Group C — 4 Dynamic & Electro-Optic Probe** | `dyn_all` (`dyn_step_response`, `dyn_freq_response`, `dyn_output_psd`, `dyn_sine_electro_optic`) | 10 & 100 deg/s step + $K_{\text{tot},1}$ sweep (`0.00%` OS) \| 15-pt Bode Mag/Phase/Group Delay (4s `2,544 Hz`, 6s `1,642 Hz`, `1.55×`) \| Broadband Output PSD ARW `0.000352 deg/rt-h` (`+29.2 dB` 6s LF supp) \| Sine `50 deg/s @ 250 Hz` (`THD=-67.5 dB`, `SFDR=43.6 dB`, $\Delta\phi_S=1.18\text{ rad}$, $V_{\text{fb,MIOC}}$ `391` wraps, $r(\Delta P_{\text{PD}},\Delta\phi_{\text{err}})=0.9960$) |

---

## Architecture & Synchronized Documentation (`v3.0.0`, Rule 16)

All architecture, scenario, and release documents (Markdown, LaTeX, and compiled PDFs) are strictly synchronized with `pyproject.toml` (`v3.0.0`) under [`docs/`](docs/):
- [`docs/IFOG_VPROTO_ARCHITECTURE.md`](docs/IFOG_VPROTO_ARCHITECTURE.md) | [`.tex`](docs/IFOG_VPROTO_ARCHITECTURE.tex) | [`.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf)
- [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf)
- [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) | [`.tex`](docs/RELEASE_NOTES.tex) | [`.pdf`](docs/RELEASE_NOTES.pdf) | [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

| Subsystem | Directory | Responsibility |
| :--- | :--- | :--- |
| **Specifications** | [`spec/`](spec/) | Checksum-locked `IFOG-SIM-SPEC-006.{md,tex,pdf,sha256}` (v6.0), `IFOG-SIM-SPEC-005.{tex,pdf,sha256}` (v5.0) & `IFOG-SIM-SPEC-004.{tex,pdf,sha256}` (v4.0) + `CHANGELOG.md` |
| **FMI 3.0 FMU Wrapper** | [`fmi_wrapper/`](fmi_wrapper/) | Vendorized FMI 3.0 C headers (`include/fmi3/`), full 75-symbol C-API bridge (`src/fmi3_bridge.cpp`), `modelDescription.xml.in` (15 variables), and CMake packager (`package_fmu.cmake`) -> `build/ifog_core.fmu` |
| **Release & Scenario Docs** | [`docs/`](docs/) | Version-synchronized architecture, scenarios guide, and release notes (`.md`, `.tex`, `.pdf`, `CHANGELOG.md`, `DOCS_BUILD.sha256` — enforced by Rule 16) |
| **Container & Setup** | [`Containerfile`](Containerfile), [`Dockerfile`](Dockerfile), [`compose.yaml`](compose.yaml), [`scripts/`](scripts/) | Turnkey Docker/Podman OCI image + distro-independent Git-source installers for SystemC 2.3.4, SystemC-AMS 2.3.4, `nlohmann/json`, Python venv with **FMPy**, and pre-packaged `build/ifog_core.fmu` |
| **Configuration** | [`configs/`](configs/) | `schema_v5.json` (backward-compatible with v4.0/v5.0), `baseline_1km.json` (4-state), `baseline_1km_6state.json` (official 6-state), and `ablation_sweeps/` |
| **Tier 1 (Offline Physics)** | [`tier1_offline/`](tier1_offline/) | Spectral-sliced Jones matrix solver (`jones_spectral.py` -> `phys_params.json`) & 1D Crank–Nicolson / FEM thermal Shupe solver (`shupe_thermal.py` -> `shupe_lut.bin`) |
| **Tier 2 (Fast-Scale Core)** | [`tier2_sysc_ams/`](tier2_sysc_ams/) | C++17 `-O3 -fPIC` SystemC + SystemC-AMS PoC 2.3.4 closed-loop core (`IfogTopModule`, 2/4/6-state `DigitalDSP_SC`, real-time BIT/FDIR, 64 B `dsp_trace.bin`, aperture jitter, VRE/Faraday, fault injection, and concurrent 3-axis IMU `--imu3axis`) |
| **Tier 3 (Scenarios, FMI & AVAR)** | [`tier3_analysis/`](tier3_analysis/) | **`fmi_master_runner.py` (FMPy Gate 6)**, `scenarios_time_domain.py`, `scenarios_engineering.py`, `scenarios_dynamic_probe.py`, `dual_regime_avar.py`, `extract_k_matrix.py`, `run_sweep_parallel.py`, `analyze_nonlinearity.py`, 28-mode `sim_runner_cli.py`, and Rule 16 `doc_sync.py` |
| **Auto-Reporting & Viz** | [`viz/`](viz/), [`report/`](report/) | 21 300-DPI Matplotlib diagnostics (`plot_scenarios.py`, `plot_avar_5regions.py`, ...) and automatic Markdown (`.md`) + 20-Chart Interactive Plotly HTML5 (`.html`) reports in `report/<run_id>/` + `report/index.{md,html}` |
| **Verification Suite** | [`tests/`](tests/) | Unit tests, **44 individual per-formula CI verifications (`EQ-01`..`EQ-44`)**, bit-exact regression tests, and **10 full real Gate 1–6 + 6 TD + 5 ENG + 4 DYN system tests** |
| **Governance & Skills** | [`AGENT.md`](AGENT.md), [`skills/`](skills/) | Strict 16-rule contract, 2-branch (`dev` -> `main`) & SemVer `vX.Y.Z` workflow, mandatory Rule 16 doc-sync, and **9 accumulated project skills** |

---

## Quickstart

### Option A — Docker or Podman (Turnkey Environment)
```bash
./scripts/container_run.sh build
./scripts/container_run.sh sim --mode fmi_gate --run-id gate6_fmi3_fmu
./scripts/container_run.sh sim --mode dsp6_compare --run-id gate5_6state
./scripts/container_run.sh example   # runs ALL 21 gates & scenarios -> report/full_all_scenarios/
```

### Option B — Native Linux (Any Distro: Ubuntu/Debian, Fedora/RHEL/Rocky, Arch, HPC Rootless)
```bash
bash scripts/setup_env.sh --with-system-deps --build-tier2 --verify
source scripts/env.sh

# Run FMI 3.0 Black-Box FMU Gate 6 or any individual scenario via CLI
./scripts/run_sim.sh --mode fmi_gate --run-id gate6_fmi3_fmu
./scripts/run_sim.sh --mode dyn_sine_electro_optic --run-id dyn04
./scripts/run_sim.sh --mode eng_imu_3axis --run-id eng02

# Or run the entire 21-gate/scenario official suite in one command
./scripts/run_all_scenarios.sh --run-id full_all_scenarios --mc-runs 500
```

---

## Verification & Quality Gates

```bash
# Triple Spec immutability lock (Rule 7) & Mandatory Version-Document Sync (Rule 16)
sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256 spec/IFOG-SIM-SPEC-006.sha256
python3 scripts/verify_doc_sync.py

# Recompile all 3 LaTeX docs -> PDFs & refresh docs/DOCS_BUILD.sha256
bash scripts/build_docs.sh

# 44-Formula individual verification matrix EQ-01..EQ-44 (Rule 3)
python3 scripts/verify_formulas_ci.py

# 100.0% C++ line coverage (tier2_sysc_ams/ + fmi_wrapper/src/) via gcovr (Rules 2 & 14)
bash scripts/run_cpp_coverage.sh

# 100.0% Python line coverage (incl. fmi_master_runner.py) via pytest-cov (Rules 2 & 14)
pytest tests/unit tests/formula_verification --cov --cov-report=term-missing

# Full real Gate 1-6 (incl. FMI 3.0 FMU) + 6 TD + 5 ENG + 4 DYN system & regression suite (Rule 5)
pytest tests/system -v
```