# `ifog-vproto` — Closed-Loop IFOG Multi-Scale Virtual Prototype

[![Version](https://img.shields.io/badge/Release-v2.1.0-0E6251)](docs/RELEASE_NOTES.md)
[![Spec](https://img.shields.io/badge/Spec-IFOG--SIM--SPEC--005%20v5.0-1B365D)](spec/IFOG-SIM-SPEC-005.pdf)
[![Formulas](https://img.shields.io/badge/Formulas-41%2F41%20Verified-0E6251)](AGENT.md)
[![Coverage](https://img.shields.io/badge/Coverage-100%25%20C%2B%2B%20%26%20Python-brightgreen)](AGENT.md)

A spec-driven, 3-Tier Hybrid Multi-Scale Co-Simulation Virtual Prototype for a **Closed-Loop Interferometric Fiber-Optic Gyroscope (2-State, 4-State Lefèvre, and Official 6-State Symmetric Modulation)** built on **Python + C++17 / IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4** (`IFOG-SIM-SPEC-005` v5.0 & `IFOG-SIM-SPEC-004` v4.0).

---

## Live Complete All-Scenarios Example (All 16 Gates & Scenarios Committed to Repo)

Inspect the **complete genuine full-scale output of ALL 16 official gates & scenarios** (Gates 1–4 with 4×60 s Fast-Scale + 12×10 h Slow-Scale AVAR + Gate 5 Official 6-State DSP + 6 Time-Domain `TD-01`..`TD-06` + 5 System Engineering `ENG-01`..`ENG-05` with `N=500` MC, zero mocks / zero smoke tests) directly in [`examples/full_all_scenarios/`](examples/full_all_scenarios/README.md):
- **Visual Walkthrough (All 16 300-DPI Figures):** [`examples/full_all_scenarios/README.md`](examples/full_all_scenarios/README.md)
- **Auto-Generated Markdown & 15-Chart Interactive Plotly HTML5 Reports:** [`report.md`](examples/full_all_scenarios/report.md) | [`report.html`](examples/full_all_scenarios/report.html) | [`metrics_summary.json`](examples/full_all_scenarios/metrics_summary.json) | [`virtual_calibration_dataset.csv`](examples/full_all_scenarios/virtual_calibration_dataset.csv)
- **One-Command Reproduction (Native or Docker/Podman):** `./examples/run_example.sh` or `./scripts/run_all_scenarios.sh` or `./scripts/container_run.sh example`
- *(Archival SPEC-004 4-Gate only example preserved in [`examples/full_4gate_baseline/`](examples/full_4gate_baseline/README.md).)*

---

## Official Simulation Flow — 5 Gates + 6 Time-Domain + 5 System Engineering Scenarios

Every scenario is runnable **individually via CLI** (`./scripts/run_sim.sh --mode <mode>`) or **end-to-end in one command** (`./scripts/run_all_scenarios.sh` / `./examples/run_example.sh`), automatically exporting Markdown (`report.md`), interactive Plotly HTML5 (`report.html` with up to 15 interactive multi-panel charts), up to **16 300-DPI PNG figures**, and CSV/JSON datasets into `report/<run_id>/`.

Full methodology, equations, and verified real-simulation benchmarks are documented in [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf).

| Category | CLI Mode (`--mode`) | Highlighted Verified Real SystemC-AMS Result |
| :--- | :--- | :--- |
| **Complete Official Suite** | `all_scenarios` (`scripts/run_all_scenarios.sh` / `examples/run_example.sh`) | Executes Gates 1–5 + all 6 Time-Domain + all 5 Engineering scenarios (`MC=500`) -> 16/16 PASS, 16 PNGs, 15 interactive Plotly charts |
| **Core Acceptance Gates** | `full` (`gate1`, `gate2`, `gate3`, `gate4`) | Gate 1 `3.10e-16 rad` (`1,666` wraps) \| Gate 2 `98.85%` reduction \| Gate 3 `-0.062` vs `-0.893` PSD \| Gate 4 `2.42%` overlap & 5 WLS params $\pm 10\%$ |
| **Gate 5 — Official 6-State DSP** | `dsp6_compare` (`configs/baseline_1km_6state.json`) | **$-33.3\%$ peak MIOC voltage**, `1.28e-16 rad` error, **`+136.94 dB`** (`7.03e6×`) RAM/xtalk/$\gamma_{\text{nl}}$ rejection (`EQ-31`–`EQ-34`) |
| **Group A — 6 Time-Domain** | `td_all` (`td_blanking`, `td_step_sine`, `td_vpi_shock`, `td_high_rate`, `td_shupe_shock`, `td_limit_cycles`) | Sub-$\tau$ $k_{\text{start}}^*=5$ \| $-3\text{ dB}$ BW `2,540 Hz` \| $+5\%$ $V_\pi$ shock (`2×` lower 6s disturbance) \| `700 deg/s` (`7,184` wraps, anti-windup) \| Shupe `99.74%` filter \| 12-bit PRBS (`3->1,595` codes) |
| **Group B — 5 Engineering** | `eng_all` (`eng_hw_sizing`, `eng_imu_3axis`, `eng_vre_faraday`, `eng_fault_bit`, `eng_mc_yield_cal`) | Min ENOB `12-bit` \| 3-Axis IMU Axis-Y xtalk `40.63 -> 0.106 deg/h` (`+51.6 dB`) \| VRE $R^2=0.9998$ & Mu-metal `25.25 dB` \| 5/5 BIT faults $\le 30\ \mu\text{s}$ + SEU FDIR \| `N=500` MC Yield `97.2%` ($C_{pk}=0.604$) & `-40..+85°C` Cal (`99.98%` Poly / `99.95%` EKF) |

---

## Architecture & Synchronized Documentation (`v2.1.0`, Rule 16)

All architecture, scenario, and release documents (Markdown, LaTeX, and compiled PDFs) are strictly synchronized with `pyproject.toml` (`v2.1.0`) under [`docs/`](docs/):
- [`docs/IFOG_VPROTO_ARCHITECTURE.md`](docs/IFOG_VPROTO_ARCHITECTURE.md) | [`.tex`](docs/IFOG_VPROTO_ARCHITECTURE.tex) | [`.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf)
- [`docs/IFOG_SIMULATION_SCENARIOS.md`](docs/IFOG_SIMULATION_SCENARIOS.md) | [`.tex`](docs/IFOG_SIMULATION_SCENARIOS.tex) | [`.pdf`](docs/IFOG_SIMULATION_SCENARIOS.pdf)
- [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) | [`.tex`](docs/RELEASE_NOTES.tex) | [`.pdf`](docs/RELEASE_NOTES.pdf) | [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

| Subsystem | Directory | Responsibility |
| :--- | :--- | :--- |
| **Specifications** | [`spec/`](spec/) | Checksum-locked `IFOG-SIM-SPEC-005.{tex,pdf,sha256}` (v5.0) & `IFOG-SIM-SPEC-004.{tex,pdf,sha256}` (v4.0) + `CHANGELOG.md` |
| **Release & Scenario Docs** | [`docs/`](docs/) | Version-synchronized architecture, scenarios guide, and release notes (`.md`, `.tex`, `.pdf`, `CHANGELOG.md`, `DOCS_BUILD.sha256` — enforced by Rule 16) |
| **Container & Setup** | [`Containerfile`](Containerfile), [`Dockerfile`](Dockerfile), [`compose.yaml`](compose.yaml), [`scripts/`](scripts/) | Turnkey Docker/Podman OCI image + distro-independent Git-source installers for SystemC 2.3.4, SystemC-AMS 2.3.4, `nlohmann/json`, and Python venv |
| **Configuration** | [`configs/`](configs/) | `schema_v5.json` (backward-compatible with v4.0/v5.0), `baseline_1km.json` (4-state), `baseline_1km_6state.json` (official 6-state), and `ablation_sweeps/` |
| **Tier 1 (Offline Physics)** | [`tier1_offline/`](tier1_offline/) | Spectral-sliced Jones matrix solver (`jones_spectral.py` -> `phys_params.json`) & 1D Crank–Nicolson / FEM thermal Shupe solver (`shupe_thermal.py` -> `shupe_lut.bin`) |
| **Tier 2 (Fast-Scale Core)** | [`tier2_sysc_ams/`](tier2_sysc_ams/) | C++17 `-O3` SystemC + SystemC-AMS PoC 2.3.4 closed-loop core (2/4/6-state `DigitalDSP_SC`, real-time BIT/FDIR, 64 B `dsp_trace.bin`, aperture jitter, VRE/Faraday, fault injection, and concurrent 3-axis IMU `--imu3axis`) |
| **Tier 3 (Scenarios & AVAR)** | [`tier3_analysis/`](tier3_analysis/) | `scenarios_time_domain.py`, `scenarios_engineering.py`, `dual_regime_avar.py`, `extract_k_matrix.py`, `run_sweep_parallel.py`, `analyze_nonlinearity.py`, 22-mode `sim_runner_cli.py`, and Rule 16 `doc_sync.py` |
| **Auto-Reporting & Viz** | [`viz/`](viz/), [`report/`](report/) | 300-DPI Matplotlib diagnostics (`plot_scenarios.py`, `plot_avar_5regions.py`, ...) and automatic Markdown (`.md`) + Interactive Plotly HTML5 (`.html`) reports in `report/<run_id>/` + `report/index.{md,html}` |
| **Verification Suite** | [`tests/`](tests/) | Unit tests, **41 individual per-formula CI verifications (`EQ-01`..`EQ-41`)**, bit-exact regression tests, and full real Gate 1–5 + 6 TD + 5 ENG system tests |
| **Governance & Skills** | [`AGENT.md`](AGENT.md), [`skills/`](skills/) | Strict 16-rule contract, 2-branch (`dev` -> `main`) & SemVer `vX.Y.Z` workflow, mandatory Rule 16 doc-sync, and 8 accumulated project skills |

---

## Quickstart

### Option A — Docker or Podman (Turnkey Environment)
```bash
./scripts/container_run.sh build
./scripts/container_run.sh sim --mode dsp6_compare --run-id gate5_6state
./scripts/container_run.sh sim --mode td_all --run-id td_suite
./scripts/container_run.sh sim --mode eng_all --run-id eng_suite --mc-runs 500
```

### Option B — Native Linux (Any Distro: Ubuntu/Debian, Fedora/RHEL/Rocky, Arch, HPC Rootless)
```bash
bash scripts/setup_env.sh --with-system-deps --build-tier2 --verify
source scripts/env.sh

# Run any individual scenario via CLI -> auto-generates report/<run_id>/report.{md,html}
./scripts/run_sim.sh --mode dsp6_compare --run-id gate5_6state
./scripts/run_sim.sh --mode td_blanking --run-id td01
./scripts/run_sim.sh --mode td_step_sine --run-id td02
./scripts/run_sim.sh --mode eng_imu_3axis --run-id eng02
./scripts/run_sim.sh --mode eng_mc_yield_cal --run-id eng05 --mc-runs 500

# Or run a full category or the entire official suite in one command
./scripts/run_sim.sh --mode td_all --run-id all_time_domain
./scripts/run_sim.sh --mode eng_all --run-id all_engineering --mc-runs 500
./scripts/run_all_scenarios.sh --run-id complete_v2_0_0 --mc-runs 500
```

---

## Verification & Quality Gates

```bash
# Dual Spec immutability lock (Rule 7) & Mandatory Version-Document Sync (Rule 16)
sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256
python3 scripts/verify_doc_sync.py

# Recompile all 3 LaTeX docs -> PDFs & refresh docs/DOCS_BUILD.sha256
bash scripts/build_docs.sh

# 41-Formula individual verification matrix EQ-01..EQ-41 (Rule 3)
python3 scripts/verify_formulas_ci.py

# 100.0% C++ line coverage via gcovr (Rules 2 & 14)
bash scripts/run_cpp_coverage.sh

# 100.0% Python line coverage via pytest-cov (Rules 2 & 14)
pytest tests/unit tests/formula_verification --cov --cov-report=term-missing

# Full real Gate 1-5 + 6 TD + 5 ENG system & regression suite (Rule 5 — no smoke tests)
pytest tests/system -v
```