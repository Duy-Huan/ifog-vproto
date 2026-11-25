# Release Notes — `ifog-vproto` (Closed-Loop IFOG Virtual Prototype)

## Document Control Metadata

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-VPROTO-REL-001` |
| **Current Version** | `v1.1.0` |
| **Status** | `RELEASED (Production Gate Verified)` |
| **Normative Specification** | [`spec/IFOG-SIM-SPEC-004.tex`](../spec/IFOG-SIM-SPEC-004.tex) (v4.0) |
| **Architecture Reference** | [`docs/IFOG_VPROTO_ARCHITECTURE.md`](IFOG_VPROTO_ARCHITECTURE.md) / [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](IFOG_VPROTO_ARCHITECTURE.pdf) |
| **LaTeX / PDF Companion** | [`docs/RELEASE_NOTES.tex`](RELEASE_NOTES.tex) / [`docs/RELEASE_NOTES.pdf`](RELEASE_NOTES.pdf) |

---

## Release `v1.1.0` (2026-11-25)

### Highlights & New Capabilities
1. **Automatic `.md` and Interactive `.html` Simulation Reporting in `report/`:**
   - Upgraded [`viz/export_report.py`](../viz/export_report.py) to emit comprehensive Markdown (`report.md`), interactive Plotly HTML5 (`report.html` with AVAR, Deadband/Bunny Ears, and $1/f$ Flicker PSD subplots + styled KPI tables + 300-DPI gallery), and structured `metrics_summary.json` directly into `report/<run_id>/`.
   - Added automated centralized dashboard indexing (`report/index.md` and `report/index.html`) linking all simulation runs with version, mode, UTC timestamp, and PASS/FAIL status.
2. **Unified Simulation Runner Script System (`scripts/run_sim.sh`, `scripts/run_sim.py`, `tier3_analysis/sim_runner_cli.py`):**
   - One-command workflow orchestration supporting `--mode {single, gate1, gate2, gate3, gate4, full, sweep}` with automatic Tier 2 C++ Release build check and automatic report generation in `report/`.
   - Exposed console CLI entrypoint `ifog-sim-run` in `pyproject.toml`.
3. **Complete Synchronized System Architecture & Release Documentation (`docs/`):**
   - Authored [`docs/IFOG_VPROTO_ARCHITECTURE.md`](IFOG_VPROTO_ARCHITECTURE.md), [`docs/IFOG_VPROTO_ARCHITECTURE.tex`](IFOG_VPROTO_ARCHITECTURE.tex) (with TikZ diagrams & 30-formula traceability matrix), compiled `docs/IFOG_VPROTO_ARCHITECTURE.pdf`, [`docs/RELEASE_NOTES.md`](RELEASE_NOTES.md), [`docs/RELEASE_NOTES.tex`](RELEASE_NOTES.tex), compiled `docs/RELEASE_NOTES.pdf`, [`docs/CHANGELOG.md`](CHANGELOG.md), and `scripts/build_docs.sh`.
4. **Mandatory Version–Document Synchronization Governance (`AGENT.md` Rule 16 & CI Gate):**
   - Added **Rule 16** to [`AGENT.md`](../AGENT.md) mandating strict synchronization of `pyproject.toml`, `docs/*.{md,tex,pdf}`, `docs/DOCS_BUILD.sha256`, `docs/CHANGELOG.md`, `README.md`, and `skills/` on every version bump and release tag.
   - Added pure-stdlib verifier [`tier3_analysis/doc_sync.py`](../tier3_analysis/doc_sync.py) + [`scripts/verify_doc_sync.py`](../scripts/verify_doc_sync.py) wired into both `.github/workflows/ci.yml` and `.github/workflows/release.yml` (with `--expected-tag` check on SemVer tags).
   - Added project skill [`skills/ifog-reporting-and-doc-sync/SKILL.md`](../skills/ifog-reporting-and-doc-sync/SKILL.md) per Rule 6.

### Release Artifacts Attached to `v1.1.0`
- `IFOG-SIM-SPEC-004.pdf` (normative specification v4.0, SHA-256 locked)
- `IFOG_VPROTO_ARCHITECTURE.pdf`, `IFOG_VPROTO_ARCHITECTURE.md`, `IFOG_VPROTO_ARCHITECTURE.tex`
- `RELEASE_NOTES.pdf`, `RELEASE_NOTES.md`, `RELEASE_NOTES.tex`
- `formula_verification_matrix.md`, `formula_verification_matrix.json` (30/30 PASS)
- `cpp_coverage_summary.json` (100.0% C++ line & function coverage)

---

## Release `v1.0.0` (2026-11-25)

### Initial Full Virtual Prototype Release
- Implemented the full 3-Tier Closed-Loop IFOG Multi-Scale Virtual Prototype strictly adhering to `IFOG-SIM-SPEC-004` v4.0:
  - **Spec Lock:** Verbatim `spec/IFOG-SIM-SPEC-004.tex` + SHA-256 lock + 12-page LuaLaTeX PDF.
  - **Tier 1:** Spectral-sliced Jones optics (`jones_spectral.py`) & 1D Crank–Nicolson / FEM thermal Shupe solver (`shupe_thermal.py`).
  - **Tier 2:** C++17 `-O3` IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4 closed-loop core (`OpticalEnvelope_TDF`, `PinkNoise_TDF`, `AnalogFrontEnd_TDF`, `ADC_Bridge_TDF2DE`, `DAC_Driver_TDF` with `set_delay(1)`, bit-true 2/4-state `DigitalDSP_SC`, 32-byte packed `SimRecord`).
  - **Tier 3 & Viz:** Parallel sweeps, $100\text{ Hz}$ $\mathbf{K}$-matrix extractor, Deadband/Bunny Ears analyzer, 10 h / 3.6M-sample Dual-Regime Overlapping AVAR + 5-region IEEE 952 WLS fitter, and 300-DPI Matplotlib / Plotly diagnostics.
  - **Verification & Governance:** 100.0% C++ line coverage (`1002/1002`), 100.0% Python line coverage (`1097/1097`), 30/30 per-formula CI tests, full real 4-Gate acceptance & bit-exact regression suite, `AGENT.md` (Rules 1–15), 5 project skills, and strict 2-branch (`dev` -> `main`) GitHub Actions CI/CD.
