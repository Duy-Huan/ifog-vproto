# `ifog-vproto` — Closed-Loop IFOG Multi-Scale Virtual Prototype, Predictive Physics & Inverse Calibration (`IFOG-SIM-SPEC-007`)

[![Version](https://img.shields.io/badge/Release-v4.1.0-0E6251)](docs/RELEASE_NOTES.md)
[![Spec](https://img.shields.io/badge/Spec-IFOG--SIM--SPEC--007%20v7.0-1B365D)](spec/IFOG-SIM-SPEC-007.pdf)
[![FMI](https://img.shields.io/badge/FMI-3.0.2%20Dual%20%26%20Multi--Instance%20FMU-0E6251)](spec/IFOG-SIM-SPEC-006.md)
[![Formulas](https://img.shields.io/badge/Formulas-53%2F53%20Verified-0E6251)](AGENT.md)
[![Coverage](https://img.shields.io/badge/Coverage-100%25%20C%2B%2B%20%26%20Python-brightgreen)](AGENT.md)

A spec-driven, 3-Tier Hybrid Multi-Scale Co-Simulation Virtual Prototype, **Dual FMI 3.0.2 Co-Simulation FMU Suite (`build/ifog_core.fmu` SystemC-AMS + `build/ifog_core_multi.fmu` Multi-Instance Pure-C++17 Source-Code FMU)**, **Bit-True FPGA/RTL Co-Verification Reference (`rtl/ifog_dsp_6state.sv`, 2/4/6-State)**, and **NASA-STD-7009A CAS-4 / ASME V&V 20 Calibrated Platform (`TRL 7–8 / DO-254`)** built on **Python + C++17 / IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4 + FMI 3.0.2** (`IFOG-SIM-SPEC-007` v7.0, preserving 100% backward compatibility with `SPEC-006` v6.0, `SPEC-005` v5.0 & `SPEC-004` v4.0).

> **Interactive Code-Verified Model Explorer, Academic Slides & Complete Formulas (`EQ-01`..`EQ-53`):** Open [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](docs/IFOG_ARCHITECTURE_EXPLORER.html), [`docs/IFOG_VPROTO_PRESENTATION.pdf`](docs/IFOG_VPROTO_PRESENTATION.pdf), or [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf) to inspect every physical equation across Tier 1 (incl. 3D FEM), Tier 2 (2/4/6-State Bit-True FPGA), Dual FMI 3.0.2 FMUs, and Tier 3 CAS-4 Lab Validation.

---

## TRL 7–8 / DO-254 Industrial Qualification Suite (`v4.1.0` — Group E `IND-01`..`IND-06`)

In **`v4.1.0`**, `ifog-vproto` closes all **6 aerospace/defense industrial gaps** alongside full **2-State / 4-State / 6-State DSP** coverage:
- **`IND-01` Physical Lab CAS-4 Validation (`tier3_analysis/lab_validation.py`):** Ingests standardized 3-rig hardware CSVs (`configs/lab_datasets/reference_ifog_lab/`: 10 h granite-table AVAR, `[-2, +2] deg/s` slow rate-table Deadband/Bunny Ears, `-40..+85 degC` thermal chamber) via `--lab-dir`, cutting uncalibrated error (`101.9%`) to **`4.51%`** (`< 5%`) with ASME V&V 20 max $|E|/u_{\text{val}} = 0.723 \le 1.0$.
- **`IND-02` Bit-True Fixed-Point FPGA DSP & Synthesizable SV RTL (`rtl/ifog_dsp_6state.sv`):** Exact signed `Q16.32` (48-bit) vs `Q8.24` (32-bit) vs Float64 across **2-State, 4-State, and 6-State DSP** (`0-LSB` RTL match, `0` overflows, `31x–376x` higher precision over 32-bit).
- **`IND-03` 3D ANSYS/COMSOL Cylindrical FEM $\to$ `shupe_lut.bin` v2 (`tier1_offline/shupe_thermal.py`):** Smooth 3D RBF projection of eccentric IMU housing hotspots $T(r,\theta,z,t)$ & anisotropic potting stress $\sigma(r,\theta,z,t)$ onto wound fiber turns (`--fem-3d-csv`), proving **`6.00x`** Octupole vs Quadrupole suppression in real Tier 2 C++.
- **`IND-04` MIL-STD-810H / DO-160G Broadband Random Vibration PSD:** Log-log PSD (`20–2000 Hz`, `4.88 g_rms`) through 2-DOF isolator (`65 Hz`) + bobbin (`480 Hz, Q=12`) transmissibility + Miles' Equation check (**`4.82x`** coil $g_{\text{rms}}$ attenuation, **`3.11x`** Tier 2 VRE bias reduction).
- **`IND-05` Multi-Instance Pure-C++17 Source-Code FMI 3.0.2 FMU (`build/ifog_core_multi.fmu`):** Removes Accellera SystemC singleton lock (`canBeInstantiatedOnlyOncePerProcess="false"`), bundles portable `sources/buildDescription.xml` for Windows/Simulink & RT-Linux, passes FMPy validation (`0` XSD errors), and executes **3 concurrent axes (6-State / 4-State / 2-State) in 1 OS process** (`< 0.15%` error, 0 cross-talk).
- **`IND-06` 12-Corner PVT Matrix & 10-Yr SLD/MIOC Aging + 50 krad(Si) Space TID:** `-40/+25/+85 degC` $\times$ $\pm 5\%$ rail $\times$ $\pm 3\sigma$ process + exponential SLD droop & PM fiber power-law RIA verified on real Tier 1 + Tier 2 C++ milestones.

```bash
# Build Tier 2 Release (-O3, -fPIC) and package BOTH FMI 3.0.2 FMUs (SystemC-AMS & Multi-Instance Source-Code)
cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
cmake --build build --target package_fmu package_fmu_multi

# Run Group E TRL 7-8 / DO-254 Industrial Suite (IND-01..IND-06) or supply custom lab CSV directory
./scripts/run_sim.sh --mode ind_all --lab-dir configs/lab_datasets/reference_ifog_lab --run-id ind_v41

# Run complete 29-item official suite (Gates 1-6 + Groups A-E)
./scripts/run_all_scenarios.sh --run-id full_all_scenarios
```

---

## Live Complete All-Scenarios Example (All 29 Gates & Scenarios Committed to Repo)

Inspect the **complete genuine full-scale output of ALL 29 official gates & scenarios** (Gates 1–6 + Group A `TD-01`..`TD-06` + Group B `ENG-01`..`ENG-05` with `N=500` MC + Group C `DYN-01`..`DYN-04` with full **2/4/6-State DSP** + Group D `PHY-01`/`CAL-01` + **Group E `IND-01`..`IND-06`**, zero mocks / zero smoke tests) directly in [`examples/full_all_scenarios/`](examples/full_all_scenarios/README.md):
- **Visual Walkthrough (All 29 300-DPI Figures):** [`examples/full_all_scenarios/README.md`](examples/full_all_scenarios/README.md)
- **Standardized Partner-Ready Reports (`v4.1.0` — Complete Tier-by-Tier Formulas `EQ-01..EQ-53` + Theory + Non-Specialist Guide + Live Proof on Every Figure):** [`report.md`](examples/full_all_scenarios/report.md) | [`report.html`](examples/full_all_scenarios/report.html) | [`architecture_model.html`](examples/full_all_scenarios/architecture_model.html) | [`calibrated_params.json`](examples/full_all_scenarios/calibrated_params.json) | [`lab_validation_report.json`](examples/full_all_scenarios/lab_validation_report.json) | [`metrics_summary.json`](examples/full_all_scenarios/metrics_summary.json)
- **One-Command Reproduction (Native or Docker/Podman):** `./examples/run_example.sh` or `./scripts/run_all_scenarios.sh` or `./scripts/container_run.sh example`
- *(Complete 4-Gate baseline example also preserved in [`examples/full_4gate_baseline/`](examples/full_4gate_baseline/README.md).)*

---

## Official Simulation Flow — 6 Gates + 23 Official Scenarios (`29 / 29` PASS)

Every scenario is runnable **individually via CLI** (`./scripts/run_sim.sh --mode <mode>`, **38 modes**) or **end-to-end in one command** (`./scripts/run_all_scenarios.sh` / `./examples/run_example.sh`), automatically exporting standardized Markdown (`report.md`), KaTeX + interactive Plotly HTML5 (`report.html`), up to **29 300-DPI PNG figures**, and CSV/JSON datasets into `report/<run_id>/`.

Full methodology, equations, and verified real-simulation benchmarks are documented in [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf).

| Category | CLI Mode (`--mode`) | Highlighted Verified Real SystemC-AMS / FMI 3.0.2 / Industrial Result |
| :--- | :--- | :--- |
| **Complete Official Suite** | `all_scenarios` (`scripts/run_all_scenarios.sh` / `examples/run_example.sh`) | Executes Gates 1–6 + 6 TD + 5 ENG (`MC=500`) + 4 DYN + 2 SPEC-007 + 6 IND -> **29/29 PASS**, **29 PNGs**, complete tier-by-tier formulas |
| **Core Acceptance Gates** | `full` (`gate1`, `gate2`, `gate3`, `gate4`) | Gate 1 `3.10e-16 rad` (`1,666` wraps) \| Gate 2 `98.85%` reduction \| Gate 3 `-0.062` vs `-0.893` PSD \| Gate 4 `2.42%` overlap & 5 WLS params $\pm 10\%$ |
| **Gate 5 — 2/4/6-State DSP** | `dsp6_compare` (`configs/baseline_1km_6state.json`) | **2-State (`1059 deg/h`) vs 4-State (`355 deg/h`) vs 6-State (`5e-5 deg/h`)**: **$-33.3\%$ peak MIOC voltage**, **`+136.94 dB`** RAM/xtalk rejection (`EQ-31`–`EQ-34`) |
| **Gate 6 — FMI 3.0 Black-Box FMU** | `fmi_gate` (`tier3_analysis/fmi_master_runner.py`) | **0 FMI 3.0 XSD errors**, bit-exact **`0.00e+00 rad/s`** (`< 1e-12`) vs `ifog_sim` (4s & 6s), **`97.42%`** Deadband reduction, **`3.83%`** (`< 5%`) Dual-Regime 5-Region AVAR overlap (`EQ-42`–`EQ-44`) |
| **Group A — 6 Time-Domain** | `td_all` (`td_blanking`..`td_limit_cycles`) | Sub-$\tau$ $k_{\text{start}}^*=5$ \| $-3\text{ dB}$ BW `2,540 Hz` \| $+5\%$ $V_\pi$ shock (`2×` lower 6s disturbance) \| `700 deg/s` (`7,184` wraps, anti-windup) \| Shupe `99.74%` filter \| 12-bit PRBS (`3->1,595` codes) |
| **Group B — 5 Engineering** | `eng_all` (`eng_hw_sizing`..`eng_mc_yield_cal`) | Min ENOB `12-bit` \| 3-Axis IMU Axis-Y xtalk `40.63 -> 0.106 deg/h` (`+51.6 dB`) \| VRE $R^2=0.9998$ & Mu-metal `25.25 dB` \| 5/5 BIT faults $\le 30\ \mu\text{s}$ + SEU FDIR \| `N=500` MC Yield `97.2%` & `-40..+85°C` Cal (`99.98%` Poly) |
| **Group C — 4 Dynamic & Probe (2/4/6-State)** | `dyn_all` (`dyn_step_response`..`dyn_sine_electro_optic`) | **2s/4s/6s** step (`0.015/0.137/0.206 ms`) \| 17-pt Bode up to 20 kHz (**2s `17.1 kHz`**, 4s `2.54 kHz`, 6s `1.64 kHz`) \| Broadband PSD (**2s/4s/6s**, `+36.9 dB` 6s LF supp) \| Sine `50 deg/s @ 250 Hz` (`THD=-67.5 dB`, `SFDR=43.6 dB`) |
| **Group D — `SPEC-007` Physics & Cal** | `spec007_all` (`spec007_physics`, `spec007_calibration`) | **`PHY-01`:** Octupole **`-47.69%`** Shupe reduction, LUT v2 (`0.0` err), MIOC acoustic + $0.58\text{ V}$ cap xtalk \| **`CAL-01`:** Uncalibrated `40–103%` error reduced to **`0.04–0.91%`** (`< 5%`), 10 hidden params recovered `<= 2.18%` |
| **Group E — TRL 7–8 / DO-254 Industrial** | `ind_all` (`ind_lab_validation`..`ind_pvt_aging_corners`) | **`IND-01`** CAS-4 Lab (`101.9%->4.51%`, $|E|/u_{\text{val}}=0.723$) \| **`IND-02`** FPGA Q16.32 vs Q8.24 + SV RTL (`0-LSB`, 2/4/6-State) \| **`IND-03`** 3D FEM (`6.00x` Octupole) \| **`IND-04`** MIL-STD-810H PSD (`4.82x` $g_{\text{rms}}$, `3.11x` VRE) \| **`IND-05`** Multi-Instance Source-Code FMU (3 axes 6s/4s/2s, `<0.15%`) \| **`IND-06`** 12-PVT & 10-Yr/50 krad EOL |

---

## Architecture & Synchronized Documentation (`v4.1.0`, Rule 16)

All architecture, scenario, presentation, and release documents (Markdown, LaTeX, compiled PDFs, and interactive HTML explorer) are strictly synchronized with `pyproject.toml` (`v4.1.0`) under [`docs/`](docs/):
- [`docs/IFOG_VPROTO_ARCHITECTURE.md`](docs/IFOG_VPROTO_ARCHITECTURE.md) | [`.tex`](docs/IFOG_VPROTO_ARCHITECTURE.tex) | [`.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf) | [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](docs/IFOG_ARCHITECTURE_EXPLORER.html)
- [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf)
- [`docs/IFOG_VPROTO_PRESENTATION.pdf`](docs/IFOG_VPROTO_PRESENTATION.pdf) | [`.tex`](docs/IFOG_VPROTO_PRESENTATION.tex) *(38-Slide Academic LaTeX Beamer Deck — bundled in every GitHub Release)*
- [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) | [`.tex`](docs/RELEASE_NOTES.tex) | [`.pdf`](docs/RELEASE_NOTES.pdf) | [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

| Subsystem | Directory | Responsibility |
| :--- | :--- | :--- |
| **Specifications** | [`spec/`](spec/) | Checksum-locked `IFOG-SIM-SPEC-007.{md,tex,pdf,sha256}` (v7.0), `SPEC-006.{md,tex,pdf,sha256}` (v6.0), `SPEC-005.{tex,pdf,sha256}` (v5.0) & `SPEC-004.{tex,pdf,sha256}` (v4.0) |
| **FMI 3.0 FMU Wrapper** | [`fmi_wrapper/`](fmi_wrapper/) | Vendorized FMI 3.0 C headers (`include/fmi3/`), full 75-symbol C-API bridge (`src/fmi3_bridge.cpp`), `modelDescription.xml.in` (**22 SI variables `VR 0..21`**), and CMake packager (`package_fmu.cmake`) -> `build/ifog_core.fmu` |
| **Release & Scenario Docs** | [`docs/`](docs/) | Version-synchronized architecture (with complete tier-by-tier mathematical formulations `EQ-01..EQ-53`), scenarios guide, interactive HTML explorer, and release notes (`.md`, `.tex`, `.pdf`, `CHANGELOG.md`, `DOCS_BUILD.sha256` — enforced by Rule 16) |
| **Container & Setup** | [`Containerfile`](Containerfile), [`Dockerfile`](Dockerfile), [`compose.yaml`](compose.yaml), [`scripts/`](scripts/) | Turnkey Docker/Podman OCI image + distro-independent Git-source installers for SystemC 2.3.4, SystemC-AMS 2.3.4, `nlohmann/json`, Python venv with **FMPy**, and pre-packaged `build/ifog_core.fmu` |
| **Configuration** | [`configs/`](configs/) | `schema_v6.json` (backward-compatible with v4.0/v5.0/v6.0), `baseline_1km.json` (4-state), `baseline_1km_6state.json` (official 6-state), `baseline_1km_spec007.json` (high-fidelity predictive physics), and `ablation_sweeps/` |
| **Tier 1 (Offline Physics)** | [`tier1_offline/`](tier1_offline/) | Spectral-sliced Jones matrix & back-reflection solver (`jones_spectral.py` -> `phys_params.json`) & discrete Quadrupole/Octupole thermo-mechanical Shupe solver (`shupe_thermal.py` -> 6-channel `shupe_lut.bin` v2) |
| **Tier 2 (Fast-Scale Core)** | [`tier2_sysc_ams/`](tier2_sysc_ams/) | C++17 `-O3 -fPIC` SystemC + SystemC-AMS PoC 2.3.4 closed-loop core (`IfogTopModule`, MIOC 2nd-order dynamics, capacitive+resistive crosstalk, Rayleigh/facet back-reflection, $O(1)$ LUT v2 interpolation, 2/4/6-state `DigitalDSP_SC`, BIT/FDIR, 3-axis IMU `--imu3axis`) |
| **Tier 3 (Calibration, FMI & AVAR)** | [`tier3_analysis/`](tier3_analysis/) | **`inverse_calibration.py` (`InverseCalibrator`)**, **`scenarios_spec007.py` (`PHY-01`/`CAL-01`)**, `fmi_master_runner.py` (FMPy Gate 6), `scenarios_time_domain.py`, `scenarios_engineering.py`, `scenarios_dynamic_probe.py`, `dual_regime_avar.py` (`DualRegimeStitcher`), **31-mode** `sim_runner_cli.py`, and Rule 16 `doc_sync.py` |
| **Auto-Reporting & Viz** | [`viz/`](viz/), [`report/`](report/) | **23 300-DPI Matplotlib diagnostics** (`plot_spec007_calibration.py`, `plot_scenarios.py`, ...) and automatic Markdown (`.md`) + Interactive KaTeX/Plotly HTML5 (`.html`) reports with tier-by-tier mathematical compendium in `report/<run_id>/` + `report/index.{md,html}` |
| **Verification Suite** | [`tests/`](tests/) | Unit tests, **53 individual per-formula CI verifications (`EQ-01`..`EQ-53`)**, bit-exact regression tests, and **12 full real system tests** (Gates 1–6 + 6 TD + 5 ENG + 4 DYN + `PHY-01` + `CAL-01` + live FMI 3.0 `VR 15..21` tunability) |
| **Governance & Skills** | [`AGENT.md`](AGENT.md), [`skills/`](skills/) | Strict 16-rule contract, 2-branch (`dev` -> `main`) & SemVer `vX.Y.Z` workflow, mandatory Rule 16 doc-sync, and **10 accumulated project skills** |

---

## Quickstart

### Option A — Docker or Podman (Turnkey Environment)
```bash
./scripts/container_run.sh build
./scripts/container_run.sh sim --mode spec007_all --run-id spec007_demo
./scripts/container_run.sh sim --mode fmi_gate --run-id gate6_fmi3_fmu
./scripts/container_run.sh example   # runs ALL 23 gates & scenarios -> report/full_all_scenarios/
```

### Option B — Native Linux (Any Distro: Ubuntu/Debian, Fedora/RHEL/Rocky, Arch, HPC Rootless)
```bash
bash scripts/setup_env.sh --with-system-deps --build-tier2 --verify
source scripts/env.sh

# Run SPEC-007 High-Fidelity Physics & Inverse Calibration or any individual scenario via CLI
./scripts/run_sim.sh --mode spec007_all --run-id spec007_demo
./scripts/run_sim.sh --mode fmi_gate --run-id gate6_fmi3_fmu
./scripts/run_sim.sh --mode dyn_sine_electro_optic --run-id dyn04

# Or run the entire 23-gate/scenario official suite in one command
./scripts/run_all_scenarios.sh --run-id full_all_scenarios --mc-runs 500
```

---

## Verification & Quality Gates

```bash
# Quadruple Spec immutability lock (Rule 7) & Mandatory Version-Document Sync (Rule 16)
sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256 spec/IFOG-SIM-SPEC-006.sha256 spec/IFOG-SIM-SPEC-007.sha256
python3 scripts/verify_doc_sync.py

# Recompile all 3 LaTeX docs -> PDFs + interactive HTML explorer & refresh docs/DOCS_BUILD.sha256
bash scripts/build_docs.sh

# 53-Formula individual verification matrix EQ-01..EQ-53 (Rule 3)
python3 scripts/verify_formulas_ci.py

# 100.0% C++ line coverage (tier2_sysc_ams/ + fmi_wrapper/src/) via gcovr (Rules 2 & 14)
bash scripts/run_cpp_coverage.sh

# 100.0% Python line coverage (incl. inverse_calibration.py & scenarios_spec007.py) via pytest-cov (Rules 2 & 14)
pytest tests/unit tests/formula_verification --cov --cov-report=term-missing

# Full real Gate 1-6 (incl. FMI 3.0 FMU) + 6 TD + 5 ENG + 4 DYN + 2 SPEC-007 system & regression suite (Rule 5)
pytest tests/system -v
```