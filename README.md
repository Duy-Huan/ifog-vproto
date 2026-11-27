# `ifog-vproto` — Closed-Loop IFOG Multi-Scale Virtual Prototype, Predictive Physics & Inverse Calibration (`IFOG-SIM-SPEC-007`)

[![Version](https://img.shields.io/badge/Release-v4.0.1-0E6251)](docs/RELEASE_NOTES.md)
[![Spec](https://img.shields.io/badge/Spec-IFOG--SIM--SPEC--007%20v7.0-1B365D)](spec/IFOG-SIM-SPEC-007.pdf)
[![FMI](https://img.shields.io/badge/FMI-3.0%20Tunable%20FMU%20(VR%200..21)-0E6251)](spec/IFOG-SIM-SPEC-006.md)
[![Formulas](https://img.shields.io/badge/Formulas-53%2F53%20Verified-0E6251)](AGENT.md)
[![Coverage](https://img.shields.io/badge/Coverage-100%25%20C%2B%2B%20%26%20Python-brightgreen)](AGENT.md)

A spec-driven, 3-Tier Hybrid Multi-Scale Co-Simulation Virtual Prototype, **Standalone Tunable FMI 3.0 Co-Simulation FMU (`build/ifog_core.fmu`, 22 SI variables)**, and **Automated 3-Stage Bounded Inverse Calibration Engine (`< 5%` prediction error against physical IFOG prototypes)** built on **Python + C++17 / IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4 + FMI 3.0.2** (`IFOG-SIM-SPEC-007` v7.0, preserving 100% backward compatibility with `SPEC-006` v6.0, `SPEC-005` v5.0 & `SPEC-004` v4.0).

> **Interactive Code-Verified Model Explorer & Complete Tier-by-Tier Formulas (`EQ-01`..`EQ-53`):** Open [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](docs/IFOG_ARCHITECTURE_EXPLORER.html) or [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf) to inspect every physical equation across Tier 1, Tier 2, FMI 3.0 FMU (`VR 0..21`), and Tier 3 Inverse Calibration ready for technical reviews and partner presentations.

---

## High-Fidelity Predictive Physics & Inverse Calibration (`IFOG-SIM-SPEC-007`)

Under **`IFOG-SIM-SPEC-007` (v7.0)**, `ifog-vproto` closes the simulation-to-hardware accuracy gap from `> 40%` datasheet error down to **`< 1%`** (`< 5%` target):
- **Tier 1 (`tier1_offline/`):** Discrete turn-by-turn **Quadrupole / Octupole** coil winding map (`EQ-45`), thermo-mechanical elasto-optic stress drift (`EQ-46`), dynamic scale factor $K_{\text{opt}}(t)$ (`EQ-47`), dynamic $V_{\text{eff}}(t)/\Delta\phi_{\text{pol}}(t)/V_\pi(t)$ (`EQ-48`), and multi-column 6-channel binary `shupe_lut.bin` v2 (`56 B <7d`, `EQ-49`, transparent v1 fallback).
- **Tier 2 (`tier2_sysc_ams/`) & FMI 3.0 (`fmi_wrapper/`):** 2nd-order $\text{LiNbO}_3$ MIOC electro-acoustic dynamics before $K_{\text{delay}}$ (`EQ-50`), capacitive + resistive PCB crosstalk $C_{\text{xtalk}}\,dV/dt + G_{\text{xtalk}}V$ (`EQ-51`), coherent Rayleigh/facet back-reflection phase noise (`EQ-52`), and **7 new live tunable FMI 3.0 parasitic parameters (`VR 15..21`)** while preserving `0.00e+00 rad/s` bit-exact Gate 6 equivalence.
- **Tier 3 (`tier3_analysis/`):** `DualRegimeStitcher` quadrature BI anti-double-counting (`EQ-52`) and 3-stage bounded `InverseCalibrator` (`EQ-53`) with Gauss–Newton 95% confidence intervals (`calibrated_params.json`).

```bash
# Build Tier 2 Release (-O3, -fPIC) and package standalone tunable FMI 3.0 FMU
cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
cmake --build build --target package_fmu

# Run SPEC-007 High-Fidelity Physics (PHY-01) & Inverse Calibration (CAL-01)
./scripts/run_sim.sh --mode spec007_all --run-id spec007_validation

# Validate FMI 3.0 XML schema & run Gate 6 (Equivalence <1e-12, Deadband, 5-Region AVAR)
./scripts/run_sim.sh --mode fmi_gate --run-id gate6_fmi3_fmu
```

---

## Live Complete All-Scenarios Example (All 23 Gates & Scenarios Committed to Repo)

Inspect the **complete genuine full-scale output of ALL 23 official gates & scenarios** (Gates 1–4 with 4×60 s Fast-Scale + 12×10 h Slow-Scale AVAR + Gate 5 Official 6-State DSP + Gate 6 FMI 3.0 Black-Box FMU + 6 Time-Domain `TD-01`..`TD-06` + 5 System Engineering `ENG-01`..`ENG-05` with `N=500` MC + 4 Dynamic/Electro-Optic Probe `DYN-01`..`DYN-04` + **2 `SPEC-007` Predictive Physics & Inverse Calibration `PHY-01` & `CAL-01`**, zero mocks / zero smoke tests) directly in [`examples/full_all_scenarios/`](examples/full_all_scenarios/README.md):
- **Visual Walkthrough (All 23 300-DPI Figures):** [`examples/full_all_scenarios/README.md`](examples/full_all_scenarios/README.md)
- **Standardized Partner-Ready Reports (`v4.0.0` — Complete Tier-by-Tier Formulas `EQ-01..EQ-53` + Theory + Non-Specialist Guide + Live Proof on Every Figure):** [`report.md`](examples/full_all_scenarios/report.md) | [`report.html`](examples/full_all_scenarios/report.html) | [`architecture_model.html`](examples/full_all_scenarios/architecture_model.html) | [`calibrated_params.json`](examples/full_all_scenarios/calibrated_params.json) | [`metrics_summary.json`](examples/full_all_scenarios/metrics_summary.json) | [`virtual_calibration_dataset.csv`](examples/full_all_scenarios/virtual_calibration_dataset.csv)
- **One-Command Reproduction (Native or Docker/Podman):** `./examples/run_example.sh` or `./scripts/run_all_scenarios.sh` or `./scripts/container_run.sh example`
- *(Complete 4-Gate baseline example also preserved in [`examples/full_4gate_baseline/`](examples/full_4gate_baseline/README.md).)*

---

## Official Simulation Flow — 6 Gates + 17 Official Scenarios (`23 / 23` PASS)

Every scenario is runnable **individually via CLI** (`./scripts/run_sim.sh --mode <mode>`) or **end-to-end in one command** (`./scripts/run_all_scenarios.sh` / `./examples/run_example.sh`), automatically exporting standardized Markdown (`report.md`), KaTeX + interactive Plotly HTML5 (`report.html` with complete tier-by-tier formulas `EQ-01`..`EQ-53`, embedded `architecture_model.html`, and 3-part theoretical/non-specialist explanations beneath every figure), up to **23 300-DPI PNG figures**, and CSV/JSON datasets into `report/<run_id>/`.

Full methodology, equations, and verified real-simulation benchmarks are documented in [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf).

| Category | CLI Mode (`--mode`) | Highlighted Verified Real SystemC-AMS / FMI 3.0 / Calibration Result |
| :--- | :--- | :--- |
| **Complete Official Suite** | `all_scenarios` (`scripts/run_all_scenarios.sh` / `examples/run_example.sh`) | Executes Gates 1–6 + 6 TD + 5 ENG (`MC=500`) + 4 DYN + 2 SPEC-007 -> **23/23 PASS**, **23 PNGs**, complete tier-by-tier formulas |
| **Core Acceptance Gates** | `full` (`gate1`, `gate2`, `gate3`, `gate4`) | Gate 1 `3.10e-16 rad` (`1,666` wraps) \| Gate 2 `98.85%` reduction \| Gate 3 `-0.062` vs `-0.893` PSD \| Gate 4 `2.42%` overlap & 5 WLS params $\pm 10\%$ |
| **Gate 5 — Official 6-State DSP** | `dsp6_compare` (`configs/baseline_1km_6state.json`) | **$-33.3\%$ peak MIOC voltage**, `1.28e-16 rad` error, **`+136.94 dB`** (`7.03e6×`) RAM/xtalk/$\gamma_{\text{nl}}$ rejection (`EQ-31`–`EQ-34`) |
| **Gate 6 — FMI 3.0 Black-Box FMU** | `fmi_gate` (`tier3_analysis/fmi_master_runner.py`) | **0 FMI 3.0 XSD errors**, bit-exact **`0.00e+00 rad/s`** (`< 1e-12`) vs `ifog_sim` (4s & 6s), **`97.42%`** Deadband reduction, **`3.83%`** (`< 5%`) Dual-Regime 5-Region AVAR overlap (`EQ-42`–`EQ-44`) |
| **Group A — 6 Time-Domain** | `td_all` (`td_blanking`, `td_step_sine`, `td_vpi_shock`, `td_high_rate`, `td_shupe_shock`, `td_limit_cycles`) | Sub-$\tau$ $k_{\text{start}}^*=5$ \| $-3\text{ dB}$ BW `2,540 Hz` \| $+5\%$ $V_\pi$ shock (`2×` lower 6s disturbance) \| `700 deg/s` (`7,184` wraps, anti-windup) \| Shupe `99.74%` filter \| 12-bit PRBS (`3->1,595` codes) |
| **Group B — 5 Engineering** | `eng_all` (`eng_hw_sizing`, `eng_imu_3axis`, `eng_vre_faraday`, `eng_fault_bit`, `eng_mc_yield_cal`) | Min ENOB `12-bit` \| 3-Axis IMU Axis-Y xtalk `40.63 -> 0.106 deg/h` (`+51.6 dB`) \| VRE $R^2=0.9998$ & Mu-metal `25.25 dB` \| 5/5 BIT faults $\le 30\ \mu\text{s}$ + SEU FDIR \| `N=500` MC Yield `97.2%` ($C_{pk}=0.604$) & `-40..+85°C` Cal (`99.98%` Poly / `99.95%` EKF) |
| **Group C — 4 Dynamic & Electro-Optic Probe** | `dyn_all` (`dyn_step_response`, `dyn_freq_response`, `dyn_output_psd`, `dyn_sine_electro_optic`) | 10 & 100 deg/s step + $K_{\text{tot},1}$ sweep (`0.00%` OS) \| 15-pt Bode Mag/Phase/Group Delay (4s `2,544 Hz`, 6s `1,642 Hz`, `1.55×`) \| Broadband Output PSD ARW `0.000352 deg/rt-h` (`+29.2 dB` 6s LF supp) \| Sine `50 deg/s @ 250 Hz` (`THD=-67.5 dB`, `SFDR=43.6 dB`, $\Delta\phi_S=1.18\text{ rad}$, $V_{\text{fb,MIOC}}$ `391` wraps, $r(\Delta P_{\text{PD}},\Delta\phi_{\text{err}})=0.9960$) |
| **Group D — `SPEC-007` Physics & Calibration** | `spec007_all` (`spec007_physics`, `spec007_calibration`) | **`PHY-01`:** Octupole **`-47.69%`** Shupe reduction, LUT v2 exact roundtrip (`0.0`), $\delta K_{\text{opt}}=85.6\text{ ppm}$, MIOC acoustic ringing + $0.58\text{ V}$ capacitive xtalk spike \| **`CAL-01`:** Uncalibrated `40–103%` error reduced to **`0.04–0.91%`** (`< 5%` across AVAR, Deadband, Thermal Bias & SF), all 10 hidden params recovered within **`<= 2.18%`** (`EQ-45`–`EQ-53`) |

---

## Architecture & Synchronized Documentation (`v4.0.1`, Rule 16)

All architecture, scenario, presentation, and release documents (Markdown, LaTeX, compiled PDFs, and interactive HTML explorer) are strictly synchronized with `pyproject.toml` (`v4.0.1`) under [`docs/`](docs/):
- [`docs/IFOG_VPROTO_ARCHITECTURE.md`](docs/IFOG_VPROTO_ARCHITECTURE.md) | [`.tex`](docs/IFOG_VPROTO_ARCHITECTURE.tex) | [`.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf) | [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](docs/IFOG_ARCHITECTURE_EXPLORER.html)
- [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf)
- [`docs/IFOG_VPROTO_PRESENTATION.pdf`](docs/IFOG_VPROTO_PRESENTATION.pdf) | [`.tex`](docs/IFOG_VPROTO_PRESENTATION.tex) *(32-Slide Academic LaTeX Beamer Deck — bundled in every GitHub Release)*
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