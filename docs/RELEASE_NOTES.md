# Release Notes — `ifog-vproto` (Closed-Loop IFOG Virtual Prototype)

## Document Control Metadata

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-VPROTO-REL-001` |
| **Current Version** | `v1.2.0` |
| **Status** | `RELEASED (Production Gate Verified)` |
| **Normative Specification** | [`spec/IFOG-SIM-SPEC-004.tex`](../spec/IFOG-SIM-SPEC-004.tex) (v4.0) |
| **Architecture Reference** | [`docs/IFOG_VPROTO_ARCHITECTURE.md`](IFOG_VPROTO_ARCHITECTURE.md) / [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](IFOG_VPROTO_ARCHITECTURE.pdf) |
| **LaTeX / PDF Companion** | [`docs/RELEASE_NOTES.tex`](RELEASE_NOTES.tex) / [`docs/RELEASE_NOTES.pdf`](RELEASE_NOTES.pdf) |

---

## Release `v1.2.0` (2026-11-25)

### Highlights & New Capabilities
1. **Docker & Podman Portable Container Suite (`Containerfile`, `Dockerfile`, `.dockerignore`, `compose.yaml`, `scripts/container_run.sh`):**
   - Ready-to-run OCI image built on `ubuntu:24.04` pre-installing Accellera SystemC `2.3.4`, SystemC-AMS PoC `2.3.4`, `nlohmann/json` `v3.11.3`, isolated Python 3.12 virtual environment (`/opt/ifog-env/venv`), and pre-compiled Tier 2 Release (`-O3`) `build/ifog_sim`.
   - Unified [`scripts/container_run.sh`](../scripts/container_run.sh) auto-detects `podman` (with rootless SELinux `:Z` and `--userns=keep-id`) or `docker` for one-command `build`, `shell`, `sim`, `example`, `test`, and `verify` workflows.
   - Verified automatically on GitHub Actions via a dedicated `container-build-and-verify` CI job.
2. **Distro-Independent Linux Git-Source Setup Toolchain (`scripts/setup_env.sh`, `scripts/install_systemc.sh`, `scripts/install_systemc_ams.sh`, `scripts/env.sh`):**
   - Pulls and builds Accellera SystemC `2.3.4` (C++17), SystemC-AMS PoC `2.3.4`, `nlohmann/json` `v3.11.3`, and an isolated Python virtual environment on **any Linux distribution** (Ubuntu/Debian, Fedora/RHEL/Rocky, Arch, or rootless HPC clusters) without requiring Ubuntu-specific `apt` SystemC packages.
   - Multi-distro CMake library discovery (`lib`, `lib64`, `lib-linux64`, x86\_64 & ARM64) in [`tier2_sysc_ams/CMakeLists.txt`](../tier2_sysc_ams/CMakeLists.txt) and automatic `source scripts/env.sh` activation in `scripts/run_sim.sh`.
3. **Complete Curated Real 4-Gate Baseline Example Committed to Repo (`examples/full_4gate_baseline/`, `examples/run_example.sh`):**
   - Full genuine execution of all 4 normative acceptance gates (`--mode full`) committed with `README.md`, `report.md`, interactive `report.html`, `metrics_summary.json`, all Tier 1–3 JSON artifacts, and all four 300-DPI PNG figures (`waveforms.png`, `bunny_ears.png`, `psd_flicker.png`, `avar_5regions.png`) for immediate technical feasibility review:
     - **Gate 1:** `3.10e-16 rad` static error (`< 1e-9`), `1,666` continuous $2\pi$ wraps (`> 1000`), `5.84e-14` residual $\epsilon_{V_\pi,\text{eff}}$ (`< 1e-5`).
     - **Gate 2:** **`98.85%`** Deadband reduction & **`98.85%`** Bunny Ears scale-factor reduction across $[-0.5, +0.5]^\circ/\text{s}$.
     - **Gate 3:** Flat linear PSD slope `-0.0621` vs nonlinear $1/f$ slope `-0.8928` (~60 dB separation), $100\text{ Hz}$ $\mathbf{K}$-matrix repeatability **`0.000%`**.
     - **Gate 4:** Real $4\times 60\text{ s}$ Fast-Scale + $12\times 10\text{ h}$ ($3.6\times 10^6$ samples @ $100\text{ Hz}$) Slow-Scale: overlap mismatch **`2.42%`** (`< 5%`); 5-region WLS errors: $Q:+3.18\%$, $N:-0.71\%$, $B:+5.31\%$, $K:-7.06\%$, $R:+9.29\%$ (all within $\pm 10\%$).
4. **Rule 6 & Rule 16 Compliance:** Added project skill [`skills/ifog-portable-container-env/SKILL.md`](../skills/ifog-portable-container-env/SKILL.md) and synchronized all `.md`, `.tex`, `.pdf`, `CHANGELOG.md`, `DOCS_BUILD.sha256`, and `README.md` deliverables to `v1.2.0`.

---

## Release `v1.1.0` (2026-11-25)

### Automated Reporting, Unified Simulation Runner & Rule 16 Doc-Sync
- Added centralized automatic `.md` and interactive Plotly `.html` report generation (`viz/export_report.py`) + dashboard index under `report/`.
- Added unified simulation runner (`tier3_analysis/sim_runner_cli.py`, `scripts/run_sim.{py,sh}`, `ifog-sim-run`) supporting `single`, `gate1`–`gate4`, `full`, and `sweep` modes.
- Authored synchronized architecture & release documentation (`docs/IFOG_VPROTO_ARCHITECTURE.{md,tex,pdf}`, `docs/RELEASE_NOTES.{md,tex,pdf}`, `docs/CHANGELOG.md`, `scripts/build_docs.sh`).
- Enacted **AGENT.md Rule 16** with pure-stdlib CI/CD verifier `tier3_analysis/doc_sync.py` / `scripts/verify_doc_sync.py`.

---

## Release `v1.0.0` (2026-11-25)

### Initial Full Virtual Prototype Release
- Implemented the full 3-Tier Closed-Loop IFOG Multi-Scale Virtual Prototype strictly adhering to `IFOG-SIM-SPEC-004` v4.0: checksum-locked spec & PDF, Tier 1 Jones/Shupe solvers, Tier 2 C++17 IEEE Std 1666.1 SystemC/SystemC-AMS 2.3.4 closed-loop core, Tier 3 parallel sweeps, $\mathbf{K}$-matrix extractor, 10 h Dual-Regime Overlapping AVAR + 5-region WLS estimator, 30/30 formula verification, 100.0% C++ & Python coverage, full real 4-Gate acceptance & bit-exact regression suite, `AGENT.md`, 5 project skills, and strict 2-branch (`dev` -> `main`) CI/CD.
