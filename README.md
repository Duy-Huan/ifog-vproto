# `ifog-vproto` — Closed-Loop IFOG Multi-Scale Virtual Prototype

[![Version](https://img.shields.io/badge/Release-v1.2.0-0E6251)](docs/RELEASE_NOTES.md)
[![Spec](https://img.shields.io/badge/Spec-IFOG--SIM--SPEC--004%20v4.0-1B365D)](spec/IFOG-SIM-SPEC-004.pdf)
[![Standards](https://img.shields.io/badge/Standards-IEEE%20952--2020%20%7C%20IEEE%201666.1-0E6251)](spec/IFOG-SIM-SPEC-004.pdf)
[![Coverage](https://img.shields.io/badge/Coverage-100%25%20C%2B%2B%20%26%20Python-brightgreen)](AGENT.md)

A spec-driven, 3-Tier Hybrid Multi-Scale Co-Simulation Virtual Prototype for a **Closed-Loop Interferometric Fiber-Optic Gyroscope (2-State & 4-State Lefèvre Modulation)** built on **Python + C++17 / IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4**.

---

## Live Feasibility Example (Real 4-Gate Outputs Committed to Repo)

Inspect the complete real full-scale baseline simulation output (4×60 s Fast-Scale SystemC-AMS + 12×10 h Slow-Scale AVAR = 3.6M samples, zero smoke tests) directly in [`examples/full_4gate_baseline/`](examples/full_4gate_baseline/README.md):
- **Walkthrough & Embedded 300-DPI Figures:** [`examples/full_4gate_baseline/README.md`](examples/full_4gate_baseline/README.md)
- **Auto-Generated Markdown & Interactive HTML5 Reports:** [`report.md`](examples/full_4gate_baseline/report.md) | [`report.html`](examples/full_4gate_baseline/report.html) | [`metrics_summary.json`](examples/full_4gate_baseline/metrics_summary.json)
- **Measured Results:** Gate 1 `3.10e-16 rad` (`1,666` wraps) **PASS** | Gate 2 `98.85%` Deadband & Bunny Ears reduction **PASS** | Gate 3 `-0.062` linear vs `-0.893` nonlinear $1/f$ PSD (`0.000%` $\mathbf{K}$ repeat) **PASS** | Gate 4 `2.42%` overlap (`< 5%`) & all 5 IEEE 952 WLS parameters within `±10%` **PASS**.

---

## Architecture Overview (`IFOG-SIM-SPEC-004` & `IFOG-VPROTO-ARCH-001`)

Full architecture design documents (Markdown, LaTeX, and compiled PDF) are synchronized with every release version (`v1.2.0`) under [`docs/`](docs/):
- [`docs/IFOG_VPROTO_ARCHITECTURE.md`](docs/IFOG_VPROTO_ARCHITECTURE.md) | [`docs/IFOG_VPROTO_ARCHITECTURE.tex`](docs/IFOG_VPROTO_ARCHITECTURE.tex) | [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf)
- [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) | [`docs/RELEASE_NOTES.tex`](docs/RELEASE_NOTES.tex) | [`docs/RELEASE_NOTES.pdf`](docs/RELEASE_NOTES.pdf) | [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

| Subsystem | Directory | Responsibility |
| :--- | :--- | :--- |
| **Specification** | [`spec/`](spec/) | Checksum-locked LaTeX source (`IFOG-SIM-SPEC-004.tex`), rendered PDF (`IFOG-SIM-SPEC-004.pdf`), and `CHANGELOG.md` |
| **Release & Arch Docs** | [`docs/`](docs/) | Version-synchronized architecture specification & release notes (`.md`, `.tex`, `.pdf`, `CHANGELOG.md`, `DOCS_BUILD.sha256` — enforced by Rule 16) |
| **Container & Setup** | [`Containerfile`](Containerfile), [`Dockerfile`](Dockerfile), [`compose.yaml`](compose.yaml), [`scripts/`](scripts/) | Ready-to-run Docker/Podman OCI environment + distro-independent Git-source installers for SystemC 2.3.4, SystemC-AMS 2.3.4, `nlohmann/json`, and Python venv (`setup_env.sh`, `env.sh`, `container_run.sh`) |
| **Feasibility Example** | [`examples/`](examples/) | Complete real 4-Gate baseline outputs (`examples/full_4gate_baseline/`) + one-command reproduction script (`examples/run_example.sh`) |
| **Configuration** | [`configs/`](configs/) | Normative JSON Schema v4 (`schema_v4.json`), reference 1 km coil baseline (`baseline_1km.json`), and parallel sweep definitions (`ablation_sweeps/`) |
| **Tier 1 (Offline Physics)** | [`tier1_offline/`](tier1_offline/) | Spectral-sliced Jones matrix solver (`jones_spectral.py` -> `phys_params.json`) & 1D Crank–Nicolson / FEM thermal Shupe solver (`shupe_thermal.py` -> `shupe_lut.bin`) |
| **Tier 2 (Fast-Scale Core)** | [`tier2_sysc_ams/`](tier2_sysc_ams/) | High-speed C++17 `-O3` SystemC + SystemC-AMS PoC 2.3.4 closed-loop core (`OpticalEnvelope_TDF`, `AnalogFrontEnd_TDF`, `PinkNoise_TDF`, `ADC_Bridge_TDF2DE`, `DAC_Driver_TDF` with `set_delay(1)`, bit-true `DigitalDSP_SC`) writing 32-byte binary `sim_out.bin` |
| **Tier 3 (Long-Term & Runner)** | [`tier3_analysis/`](tier3_analysis/) | Parallel sweep runner (`run_sweep_parallel.py`), $100\text{ Hz}$ FFT leakage matrix $\mathbf{K}$ extractor (`extract_k_matrix.py`), Deadband & Bunny Ears analyzer (`analyze_nonlinearity.py`), 10 h / $100\text{ Hz}$ Dual-Regime IEEE Std 952 Overlapping AVAR (`dual_regime_avar.py`), unified simulation orchestrator (`sim_runner_cli.py`), and Rule 16 doc-sync verifier (`doc_sync.py`) |
| **Auto-Reporting & Viz** | [`viz/`](viz/), [`report/`](report/) | 300-DPI Matplotlib diagnostics and automated Markdown (`.md`) + Interactive Plotly HTML5 (`.html`) report & dashboard generation in `report/<run_id>/` + `report/index.{md,html}` |
| **Verification Suite** | [`tests/`](tests/) | Unit tests, 30 individual per-formula CI verifications (`EQ-01`..`EQ-30`), deterministic bit-exact regression tests, and full real 4-Gate acceptance tests (Gate 1..Gate 4) |
| **Governance & Skills** | [`AGENT.md`](AGENT.md), [`skills/`](skills/) | Strict 16-rule engineering contract, 2-branch (`dev` -> `main`) & SemVer `vX.Y.Z` tag workflow, mandatory Rule 16 version–doc sync, and 7 accumulated project skills |

---

## Quickstart

### Option A — Docker or Podman (Instant Turnkey Environment)
Works seamlessly with both **Docker** and **rootless Podman** (auto-detected by `scripts/container_run.sh`):
```bash
# Build ready-to-run image (SystemC 2.3.4 + SystemC-AMS 2.3.4 + Python 3.12 venv + Tier 2 -O3)
./scripts/container_run.sh build

# Run a single simulation or full 4-Gate example -> reports appear directly in host report/
./scripts/container_run.sh sim --mode single --run-id container_demo --duration-s 0.5
./scripts/container_run.sh example

# Or use OCI Compose (docker compose / podman compose)
docker compose build
docker compose run --rm ifog-vproto ./scripts/run_sim.sh --mode gate1
```

### Option B — Native Linux (Any Distro: Ubuntu/Debian, Fedora/RHEL/Rocky, Arch, HPC Rootless)
Pulls and builds Accellera SystemC `2.3.4`, SystemC-AMS PoC `2.3.4`, `nlohmann/json` `v3.11.3`, and an isolated Python virtual environment directly from Git:
```bash
# Full one-command setup (omit --with-system-deps on non-root HPC if gcc/cmake/python3 already exist)
bash scripts/setup_env.sh --with-system-deps --build-tier2 --verify

# Activate environment in any shell
source scripts/env.sh

# Run simulations -> auto-generates report/<run_id>/{report.md, report.html, figures/} + report/index.{md,html}
./scripts/run_sim.sh --mode single --run-id baseline_run --duration-s 0.5
./scripts/run_sim.sh --mode full --run-id full_v1_2_0
```

### Low-Level Tier-by-Tier Spec CLI (`IFOG-SIM-SPEC-004` Section 5.2)
```bash
source scripts/env.sh
cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
python3 tier1_offline/jones_spectral.py --cfg configs/baseline_1km.json --out data/run01/
python3 tier1_offline/shupe_thermal.py  --cfg configs/baseline_1km.json --out data/run01/
./build/ifog_sim --phys data/run01/phys_params.json --cfg configs/baseline_1km.json --out data/run01/
python3 tier3_analysis/extract_k_matrix.py --bin ./build/ifog_sim --cfg configs/baseline_1km.json --phys data/run01/phys_params.json --out data/run01/
python3 tier3_analysis/dual_regime_avar.py --run data/run01/
python3 viz/export_report.py --run data/run01/ --report-dir report/run01 --format png,md,html --update-index
```

---

## Verification & Quality Gates

```bash
# Spec immutability lock (Rule 7) & Mandatory Version-Document Sync (Rule 16)
sha256sum -c spec/IFOG-SIM-SPEC-004.sha256
python3 scripts/verify_doc_sync.py

# Recompile release LaTeX docs -> PDFs & refresh docs/DOCS_BUILD.sha256
bash scripts/build_docs.sh

# 30-Formula individual verification matrix EQ-01..EQ-30 (Rule 3)
python3 scripts/verify_formulas_ci.py

# 100.0% C++ line coverage via gcovr (Rules 2 & 14)
bash scripts/run_cpp_coverage.sh

# 100.0% Python line coverage via pytest-cov (Rules 2 & 14)
pytest tests/unit tests/formula_verification --cov --cov-report=term-missing

# Full real 4-Gate acceptance & deterministic regression suite (Rule 5 — no smoke tests)
pytest tests/system -v
```

---

## Governance & Maintenance Rules

All contributors and AI agents MUST follow [`AGENT.md`](AGENT.md) and load [`skills/README.md`](skills/README.md) before making any changes:
- Only two branches exist: `dev` (development) and `main` (protected release branch).
- Every change merges strictly `dev` -> `main` after all CI/CD gates pass.
- **Rule 16:** Every version bump (`vX.Y.Z`) MUST keep `pyproject.toml`, `docs/*.{md,tex,pdf}`, `docs/DOCS_BUILD.sha256`, `docs/CHANGELOG.md`, `README.md`, and `skills/` 100% synchronized before merging or tagging.
- Releases are tagged on `main` using annotated SemVer tags `vX.Y.Z` (see `AGENT.md` §5).