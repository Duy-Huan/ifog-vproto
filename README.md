# `ifog-vproto` — Closed-Loop IFOG Multi-Scale Virtual Prototype

[![Spec](https://img.shields.io/badge/Spec-IFOG--SIM--SPEC--004%20v4.0-1B365D)](spec/IFOG-SIM-SPEC-004.pdf)
[![Standards](https://img.shields.io/badge/Standards-IEEE%20952--2020%20%7C%20IEEE%201666.1-0E6251)](spec/IFOG-SIM-SPEC-004.pdf)
[![Coverage](https://img.shields.io/badge/Coverage-100%25%20C%2B%2B%20%26%20Python-brightgreen)](AGENT.md)

A spec-driven, 3-Tier Hybrid Multi-Scale Co-Simulation Virtual Prototype for a **Closed-Loop Interferometric Fiber-Optic Gyroscope (2-State & 4-State Lefèvre Modulation)** built on **Python + C++17 / IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4**.

---

## Architecture Overview (`IFOG-SIM-SPEC-004`)

| Subsystem | Directory | Responsibility |
| :--- | :--- | :--- |
| **Specification** | [`spec/`](spec/) | Checksum-locked LaTeX source (`IFOG-SIM-SPEC-004.tex`), rendered PDF (`IFOG-SIM-SPEC-004.pdf`), and `CHANGELOG.md` |
| **Configuration** | [`configs/`](configs/) | Normative JSON Schema v4 (`schema_v4.json`), reference 1 km coil baseline (`baseline_1km.json`), and parallel sweep definitions (`ablation_sweeps/`) |
| **Tier 1 (Offline Physics)** | [`tier1_offline/`](tier1_offline/) | Spectral-sliced Jones matrix solver (`jones_spectral.py` -> `phys_params.json`) & 1D Crank–Nicolson / FEM thermal Shupe solver (`shupe_thermal.py` -> `shupe_lut.bin`) |
| **Tier 2 (Fast-Scale Core)** | [`tier2_sysc_ams/`](tier2_sysc_ams/) | High-speed C++17 `-O3` SystemC + SystemC-AMS PoC 2.3.4 closed-loop core (`OpticalEnvelope_TDF`, `AnalogFrontEnd_TDF`, `PinkNoise_TDF`, `ADC_Bridge_TDF`, `DAC_Driver_TDF` with `set_delay(1)`, bit-true `DigitalDSP_SC`) writing 32-byte binary `sim_out.bin` |
| **Tier 3 (Long-Term & AVAR)** | [`tier3_analysis/`](tier3_analysis/) | Parallel sweep runner (`run_sweep_parallel.py`), $100\text{ Hz}$ FFT leakage matrix $\mathbf{K}$ extractor (`extract_k_matrix.py`), Deadband & Bunny Ears analyzer (`analyze_nonlinearity.py`), and 10 h / $100\text{ Hz}$ Dual-Regime IEEE Std 952 Overlapping AVAR + 5-region WLS fitter (`dual_regime_avar.py`) |
| **Diagnostics & Reports** | [`viz/`](viz/) | 300-DPI Matplotlib diagnostics (`plot_waveforms.py`, `plot_bunny_ears.py`, `plot_psd_flicker.py`, `plot_avar_5regions.py`) and interactive Plotly HTML report exporter (`export_report.py`) |
| **Verification Suite** | [`tests/`](tests/) | Unit tests, 30 individual per-formula CI verifications (`EQ-01`..`EQ-30`), deterministic bit-exact regression tests, and full real 4-Gate acceptance tests (Gate 1..Gate 4) |
| **Governance & Skills** | [`AGENT.md`](AGENT.md), [`skills/`](skills/) | Strict 15-rule engineering contract, 2-branch (`dev` -> `main`) & SemVer `vX.Y.Z` tag workflow, and accumulated project skills |

---

## Quickstart CLI (`IFOG-SIM-SPEC-004` Section 5.2)

### 0. Environment Setup (Ubuntu 24.04)
```bash
sudo apt-get update && sudo apt-get install -y \
  build-essential cmake autoconf automake libtool pkg-config \
  libsystemc-dev nlohmann-json3-dev gcovr lcov

bash scripts/install_systemc_ams.sh
pip install -e ".[dev]" --no-build-isolation
```

### 1. Build Tier 2 SystemC-AMS Core (`-O3`)
```bash
cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j
```

### 2. Run Tier 1 Offline Optical & Thermal Solvers
```bash
python3 tier1_offline/jones_spectral.py --cfg configs/baseline_1km.json --out data/run01/
python3 tier1_offline/shupe_thermal.py  --cfg configs/baseline_1km.json --out data/run01/
```

### 3. Run Tier 2 Closed-Loop Co-Simulation (Single or Multi-Core Sweep)
```bash
./build/ifog_sim --phys data/run01/phys_params.json --cfg configs/baseline_1km.json --out data/run01/
python3 tier3_analysis/run_sweep_parallel.py --bin ./build/ifog_sim --sweep configs/ablation_sweeps/ --out data/sweep01/
```

### 4. Run Tier 3 Dual-Regime AVAR (5 Regions) & Export Diagnostic Report
```bash
python3 tier3_analysis/extract_k_matrix.py --bin ./build/ifog_sim --cfg configs/baseline_1km.json --phys data/run01/phys_params.json --out data/run01/
python3 tier3_analysis/dual_regime_avar.py --run data/run01/
python3 viz/export_report.py --run data/run01/ --format png,html
```

---

## Verification & Quality Gates

```bash
# Spec immutability lock (Rule 7)
sha256sum -c spec/IFOG-SIM-SPEC-004.sha256

# 30-Formula individual verification matrix EQ-01..EQ-30 (Rule 3)
python3 scripts/verify_formulas_ci.py

# 100.0% C++ line coverage via gcovr (Rule 2 & 14)
bash scripts/run_cpp_coverage.sh

# 100.0% Python line coverage via pytest-cov (Rule 2 & 14)
pytest tests/unit tests/formula_verification --cov --cov-report=term-missing

# Full real 4-Gate acceptance & deterministic regression suite (Rule 5 — no smoke tests)
pytest tests/system -v
```

---

## Governance & Maintenance Rules

All contributors and AI agents MUST follow [`AGENT.md`](AGENT.md) and load [`skills/README.md`](skills/README.md) before making any changes:
- Only two branches exist: `dev` (development) and `main` (protected release branch).
- Every change merges strictly `dev` -> `main` after all CI/CD gates pass.
- Releases are tagged on `main` using annotated SemVer tags `vX.Y.Z` (see `AGENT.md` §5).