# Changelog — `ifog-vproto`

All notable changes to this project are documented in this file following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html), and are strictly synchronized with `pyproject.toml`, `docs/`, and Git release tags per [`AGENT.md`](../AGENT.md) **Rule 16**.

## [2.1.0] - 2026-11-25

### Added
- **Complete Real All-Scenarios Curated Example (`examples/full_all_scenarios/`):** Executed and committed the complete real 16-gate/scenario verification bundle (`Gates 1–4` including 4×60 s Fast + 12×10 h Slow AVAR, `Gate 5` Official 6-State DSP, `TD-01`..`TD-06`, and `ENG-01`..`ENG-05` with `N=500` MC) including `README.md`, full `report.md`, interactive 15-chart Plotly `report.html`, all **16 300-DPI PNG plots**, `virtual_calibration_dataset.csv`, and all Gate/TD/ENG JSON telemetry.
- **15-Chart Interactive Plotly HTML5 & Full Scenario Markdown Reporting (`viz/export_report.py`):** Added modular `_build_plotly_sections()` rendering interactive Plotly charts for Core Gates (2, 3, 4, 5), Group A (`TD-01`..`TD-06`), and Group B (`ENG-01`..`ENG-05`), plus dedicated Markdown tables for Gate 5, Group A TD, Group B ENG, 5-fault BIT/FDIR, and MC Yield / Thermal Calibration.

### Changed
- Upgraded `examples/run_example.sh`, `scripts/run_all_scenarios.sh` (default `--mc-runs 500`), and `scripts/container_run.sh example` to execute ALL 16 official gates & scenarios by default and export `.md`, interactive `.html`, 16 PNG plots, CSV, and `report/index.{md,html}`.
- Added generated PNG plot count logging in `tier3_analysis/sim_runner_cli.py`, updated `skills/ifog-reporting-and-doc-sync/SKILL.md`, and synchronized `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `README.md`, and all `docs/*.{md,tex,pdf}` to `v2.1.0`.

## [2.0.0] - 2026-11-25

### Added
- **Owner-Authorized Spec Upgrade (`IFOG-SIM-SPEC-005` v5.0):** Added checksum-locked `spec/IFOG-SIM-SPEC-005.{tex,pdf,sha256}` (while keeping `spec/IFOG-SIM-SPEC-004.*` untouched and locked), `configs/schema_v5.json`, and `configs/baseline_1km_6state.json`.
- **Official 6-State Symmetric DSP (`EQ-31`–`EQ-34`, Gate 5):** Implemented anti-periodic 6-state modulation (`dsp.mode = "6state"`, $\alpha^* = \pi/3$, $-33.3\%$ peak MIOC voltage) with 3-channel orthogonal demodulation ($e_\Omega^{(6)}, e_{V_\pi}^{(6)}, e_{\text{asym}}^{(6)}$) and Loop-1 anti-windup clamping (`FLAG_ANTI_WINDUP`) in `DigitalDSP_SC`, achieving `+136.94 dB` (`7.03e6x`) RAM/crosstalk/$\gamma_{\text{nl}}$ rejection.
- **6 Official Time-Domain Scenarios (`TD-01`..`TD-06`):** Added 64-byte `DspTraceRecord` (`dsp_trace.bin`) and `tier3_analysis/scenarios_time_domain.py` (`td_blanking`, `td_step_sine`, `td_vpi_shock`, `td_high_rate`, `td_shupe_shock`, `td_limit_cycles`, `td_all`, `dsp6_compare`).
- **5 Official System Engineering & Production Scenarios (`ENG-01`..`ENG-05`, `EQ-35`–`EQ-41`):** Added concurrent 3-axis SystemC-AMS IMU (`tier2_sysc_ams/src/imu_3axis.cpp`, `--imu3axis`), ADC aperture jitter, VRE + dynamic Faraday physics, 5-mode fault injection + real-time FPGA BIT/FDIR (`DigitalDSP_SC::evaluate_frame_bit`), and `tier3_analysis/scenarios_engineering.py` (`eng_hw_sizing`, `eng_imu_3axis`, `eng_vre_faraday`, `eng_fault_bit`, `eng_mc_yield_cal`, `eng_all`).
- **Unified Official Flow, Reporting & Scenarios Documentation:** Added `scripts/run_all_scenarios.sh`, expanded `sim_runner_cli.py` to 22 CLI modes, added 300-DPI scenario plotters (`viz/plot_scenarios.py`), integrated SPEC-005 metrics/figures/CSV into `viz/export_report.py`, authored `docs/IFOG_SIMULATION_SCENARIOS.{md,tex,pdf}`, and added skill `skills/ifog-6state-and-scenarios/SKILL.md`.
- **41-Formula CI Verification (`EQ-01`..`EQ-41`):** Added `tests/formula_verification/test_formulas_spec005.py`, `tests/unit/test_spec005_scenarios_unit.py`, and `tests/system/test_spec005_scenarios_system.py`.

### Changed
- Bumped `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `scripts/container_run.sh`, `AGENT.md`, `README.md`, and all `docs/*.{md,tex,pdf}` to `v2.0.0`, expanding Rule 16 (`tier3_analysis/doc_sync.py`, `scripts/build_docs.sh`) to track all 3 compiled PDFs and Rule 7 to lock both `SPEC-004` and `SPEC-005`.
- Updated `.github/workflows/ci.yml` and `.github/workflows/release.yml` for dual spec locks, 8 project skills, 41-formula verification, and 14 release bundle assets.

## [1.2.0] - 2026-11-25

### Added
- **Docker & Podman Portable Container Suite:** Added byte-identical `Containerfile` and `Dockerfile`, `.dockerignore`, OCI `compose.yaml`, and unified launcher `scripts/container_run.sh` (auto-detects `podman` with `:Z` / `--userns=keep-id` or `docker`), continuously verified by a `container-build-and-verify` CI job.
- **Distro-Independent Linux Git-Source Setup Toolchain:** Added `scripts/install_systemc.sh` (Accellera SystemC `2.3.4`), universal bootstrapper `scripts/setup_env.sh` (SystemC `2.3.4` + SystemC-AMS `2.3.4` + `nlohmann/json` `v3.11.3` + isolated Python venv + generated `env.sh`), and tracked `scripts/env.sh`.
- **Curated Real 4-Gate Feasibility Example (`examples/full_4gate_baseline/`):** Executed and committed complete real Gate 1–4 outputs (`README.md`, `report.md`, interactive `report.html`, `metrics_summary.json`, all Tier 1–3 JSONs, and all four 300-DPI PNG plots) plus `examples/run_example.sh`.
- **Project Skill (Rule 6):** Added `skills/ifog-portable-container-env/SKILL.md` and registered it in `skills/README.md` & CI governance checks.

### Changed
- Upgraded `scripts/install_systemc_ams.sh` and `tier2_sysc_ams/CMakeLists.txt` for multi-distro Linux discovery (`lib`, `lib64`, `lib-linux64`, x86\_64 & ARM64) and portable `IFOG_ENV_PREFIX` installs; `scripts/run_sim.sh` auto-sources `scripts/env.sh`.
- Fixed Slow-Scale sampling frequency display (`100.0 Hz` derived from `slow_dt_s`) in `viz/export_report.py`.
- Bumped project version in `pyproject.toml` from `1.1.0` to `1.2.0` and synchronized all `docs/*.{md,tex,pdf}`, `docs/DOCS_BUILD.sha256`, and `README.md` per Rule 16.

## [1.1.0] - 2026-11-25

### Added
- **Automated Simulation Reporting (`report/`):** Upgraded `viz/export_report.py` to generate Markdown (`report.md`), interactive Plotly HTML5 (`report.html`), 300-DPI PNG figures, `metrics_summary.json`, and centralized `report/index.{md,html}` dashboards automatically for every simulation run; added `report/README.md` and `.gitignore` rules.
- **Unified Simulation Runner Suite:** Added `tier3_analysis/sim_runner_cli.py`, `scripts/run_sim.py`, executable `scripts/run_sim.sh`, and `ifog-sim-run` CLI entrypoint supporting `--mode {single, gate1, gate2, gate3, gate4, full, sweep}`.
- **Release Architecture & Release Notes Documentation (`docs/`):** Added synchronized `docs/IFOG_VPROTO_ARCHITECTURE.{md,tex,pdf}`, `docs/RELEASE_NOTES.{md,tex,pdf}`, `docs/CHANGELOG.md`, `docs/DOCS_BUILD.sha256`, and `scripts/build_docs.sh`.
- **Mandatory Version–Document Synchronization (`AGENT.md` Rule 16):** Added `tier3_analysis/doc_sync.py` and `scripts/verify_doc_sync.py` enforced automatically in `.github/workflows/ci.yml` and `.github/workflows/release.yml`.
- **Project Skill (Rule 6):** Added `skills/ifog-reporting-and-doc-sync/SKILL.md` and updated `skills/README.md` & `skills/ifog-cicd-release-workflow/SKILL.md`.

### Changed
- Bumped project version in `pyproject.toml` from `1.0.0` to `1.1.0`.
- Updated `.github/workflows/release.yml` to attach architecture and release documentation bundles (`.pdf`, `.md`, `.tex`) alongside the spec PDF, formula verification matrix, and C++ coverage summary.

## [1.0.0] - 2026-11-25

### Added
- Initial complete 3-Tier Closed-Loop IFOG Multi-Scale Virtual Prototype implementing `IFOG-SIM-SPEC-004` v4.0 (`spec/`, `configs/`, `tier1_offline/`, `tier2_sysc_ams/`, `tier3_analysis/`, `viz/`, `tests/`, `scripts/`, `AGENT.md`, `skills/`, `.github/workflows/`).
- Verified 30/30 individual spec formulas (`EQ-01`..`EQ-30`), 100.0% C++ (`gcovr`) & Python (`pytest-cov`) coverage, and full real 4-Gate acceptance & bit-exact deterministic regression.
