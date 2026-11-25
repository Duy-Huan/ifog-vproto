# `ifog-vproto` — Closed-Loop IFOG Multi-Scale Virtual Prototype

[![Version](https://img.shields.io/badge/Release-v1.1.0-0E6251)](docs/RELEASE_NOTES.md)
[![Spec](https://img.shields.io/badge/Spec-IFOG--SIM--SPEC--004%20v4.0-1B365D)](spec/IFOG-SIM-SPEC-004.pdf)
[![Standards](https://img.shields.io/badge/Standards-IEEE%20952--2020%20%7C%20IEEE%201666.1-0E6251)](spec/IFOG-SIM-SPEC-004.pdf)
[![Coverage](https://img.shields.io/badge/Coverage-100%25%20C%2B%2B%20%26%20Python-brightgreen)](AGENT.md)

A spec-driven, 3-Tier Hybrid Multi-Scale Co-Simulation Virtual Prototype for a **Closed-Loop Interferometric Fiber-Optic Gyroscope (2-State & 4-State Lefèvre Modulation)** built on **Python + C++17 / IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4**.

---

## Architecture Overview (`IFOG-SIM-SPEC-004` & `IFOG-VPROTO-ARCH-001`)

Full architecture design documents (Markdown, LaTeX, and compiled PDF) are synchronized with every release version (`v1.1.0`) under [`docs/`](docs/):
- [`docs/IFOG_VPROTO_ARCHITECTURE.md`](docs/IFOG_VPROTO_ARCHITECTURE.md) | [`docs/IFOG_VPROTO_ARCHITECTURE.tex`](docs/IFOG_VPROTO_ARCHITECTURE.tex) | [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](docs/IFOG_VPROTO_ARCHITECTURE.pdf)
- [`docs/RELEASE_NOTES.md`](docs/RELEASE_NOTES.md) | [`docs/RELEASE_NOTES.tex`](docs/RELEASE_NOTES.tex) | [`docs/RELEASE_NOTES.pdf`](docs/RELEASE_NOTES.pdf) | [`docs/CHANGELOG.md`](docs/CHANGELOG.md)

| Subsystem | Directory | Responsibility |
| :--- | :--- | :--- |
| **Specification** | [`spec/`](spec/) | Checksum-locked LaTeX source (`IFOG-SIM-SPEC-004.tex`), rendered PDF (`IFOG-SIM-SPEC-004.pdf`), and `CHANGELOG.md` |
| **Release & Arch Docs** | [`docs/`](docs/) | Version-synchronized architecture specification & release notes (`.md`, `.tex`, `.pdf`, `CHANGELOG.md`, `DOCS_BUILD.sha256` — enforced by Rule 16) |
| **Configuration** | [`configs/`](configs/) | Normative JSON Schema v4 (`schema_v4.json`), reference 1 km coil baseline (`baseline_1km.json`), and parallel sweep definitions (`ablation_sweeps/`) |
| **Tier 1 (Offline Physics)** | [`tier1_offline/`](tier1_offline/) | Spectral-sliced Jones matrix solver (`jones_spectral.py` -> `phys_params.json`) & 1D Crank–Nicolson / FEM thermal Shupe solver (`shupe_thermal.py` -> `shupe_lut.bin`) |
| **Tier 2 (Fast-Scale Core)** | [`tier2_sysc_ams/`](tier2_sysc_ams/) | High-speed C++17 `-O3` SystemC + SystemC-AMS PoC 2.3.4 closed-loop core (`OpticalEnvelope_TDF`, `AnalogFrontEnd_TDF`, `PinkNoise_TDF`, `ADC_Bridge_TDF2DE`, `DAC_Driver_TDF` with `set_delay(1)`, bit-true `DigitalDSP_SC`) writing 32-byte binary `sim_out.bin` |
| **Tier 3 (Long-Term & Runner)** | [`tier3_analysis/`](tier3_analysis/) | Parallel sweep runner (`run_sweep_parallel.py`), $100\text{ Hz}$ FFT leakage matrix $\mathbf{K}$ extractor (`extract_k_matrix.py`), Deadband & Bunny Ears analyzer (`analyze_nonlinearity.py`), 10 h / $100\text{ Hz}$ Dual-Regime IEEE Std 952 Overlapping AVAR (`dual_regime_avar.py`), unified simulation orchestrator (`sim_runner_cli.py`), and Rule 16 doc-sync verifier (`doc_sync.py`) |
| **Auto-Reporting & Viz** | [`viz/`](viz/), [`report/`](report/) | 300-DPI Matplotlib diagnostics and automated Markdown (`.md`) + Interactive Plotly HTML5 (`.html`) report & dashboard generation in `report/<run_id>/` + `report/index.{md,html}` |
| **Simulation & CI Scripts** | [`scripts/`](scripts/) | One-command simulation runners (`run_sim.sh`, `run_sim.py`), doc builder (`build_docs.sh`), Rule 16 sync checker (`verify_doc_sync.py`), 30-formula verifier (`verify_formulas_ci.py`), and 100% C++ coverage script (`run_cpp_coverage.sh`) |
| **Verification Suite** | [`tests/`](tests/) | Unit tests, 30 individual per-formula CI verifications (`EQ-01`..`EQ-30`), deterministic bit-exact regression tests, and full real 4-Gate acceptance tests (Gate 1..Gate 4) |
| **Governance & Skills** | [`AGENT.md`](AGENT.md), [`skills/`](skills/) | Strict 16-rule engineering contract, 2-branch (`dev` -> `main`) & SemVer `vX.Y.Z` tag workflow, mandatory Rule 16 version–doc sync, and 6 accumulated project skills |

---

## Quickstart: One-Command Simulation & Auto-Reporting (`report/`)

### 0. Environment Setup (Ubuntu 24.04)
```bash
sudo apt-get update && sudo apt-get install -y \
  build-essential cmake autoconf automake libtool pkg-config \
  libsystemc-dev nlohmann-json3-dev gcovr lcov

bash scripts/install_systemc_ams.sh
pip install -e ".[dev]" --no-build-isolation
```

### 1. Run Simulations (Auto-Builds Tier 2 & Auto-Generates `.md` + `.html` Reports in `report/`)
```bash
# Single closed-loop baseline run -> report/baseline_run/{report.md, report.html, figures/}
./scripts/run_sim.sh --mode single --run-id baseline_run --duration-s 0.5

# Run any individual acceptance gate (gate1, gate2, gate3, gate4) or a sweep
./scripts/run_sim.sh --mode gate1 --run-id gate1_verify
./scripts/run_sim.sh --mode gate2 --run-id gate2_verify
./scripts/run_sim.sh --mode gate3 --run-id gate3_verify
./scripts/run_sim.sh --mode gate4 --run-id gate4_verify

# Run the complete real 4-Gate verification suite into ONE unified report
./scripts/run_sim.sh --mode full --run-id full_v1_1_0
```

All runs automatically refresh `report/index.md` and `report/index.html`.

### 2. Low-Level Tier-by-Tier Spec CLI (`IFOG-SIM-SPEC-004` Section 5.2)
```bash
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