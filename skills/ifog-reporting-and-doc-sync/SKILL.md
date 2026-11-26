---
name: ifog-reporting-and-doc-sync
description: Auto-generated Markdown (.md) & Interactive HTML (.html) reporting under report/, unified simulation runner CLI (scripts/run_sim.sh, scripts/run_sim.py), industrial LaTeX/Markdown architecture & release documentation (docs/), and mandatory Rule 16 version-document synchronization.
---

# Automated Reporting, Unified Simulation Runner & Rule 16 Doc-Sync

## 1. Automated Standardized Report Generation & Interactive Architecture Explorer (`viz/export_report.py`, `viz/architecture_explorer.py`, `viz/report_narratives.py` -> `report/`)
- Every orchestrated simulation run (`scripts/run_sim.sh` / `scripts/run_all_scenarios.sh` / `examples/run_example.sh` / `ifog-sim-run`) writes raw artifacts into `data/<run_id>/` and automatically publishes standardized explanatory reports into `report/<run_id>/`:
  - `report/<run_id>/report.md` — Version-stamped Markdown report with Section 0 plain-language 3-Tier + FMI 3.0 model overview, link to `architecture_model.html`, Executive 21-row Pass/Fail table, Tier 1–3 KPIs, Dual-Regime 5-Region WLS, Gate 5 6-State DSP comparison, Gate 6 FMI 3.0 FMU table, Group A `TD-01`..`TD-06`, Group B `ENG-01`..`ENG-05` (5-fault BIT/FDIR & Monte Carlo Yield / Thermal Cal tables), Group C `DYN-01`..`DYN-04`, and all 21 embedded 300-DPI PNG figures each accompanied by a standardized 3-part narrative block (**Cơ sở lý thuyết & `EQ-xx`**, **Ý nghĩa biểu đồ cho người không chuyên**, **Kết quả thực tế & điều được chứng minh**).
  - `report/<run_id>/report.html` — Self-contained interactive HTML5 diagnostic report loading Plotly + KaTeX CDN once in `<head>`, featuring a sticky quick-navigation bar, embedded interactive `architecture_model.html` block diagram, up to **20 interactive multi-panel Plotly charts** across Core Gates (2–6), Group A (`TD-01`..`TD-06`), Group B (`ENG-01`..`ENG-05`), and Group C (`DYN-01`..`DYN-04`), plus the 21-plot 300-DPI PNG gallery (every Plotly card and gallery figure accompanied by its standardized 3-column KaTeX explanation card) and collapsible `metrics_summary.json` inspector.
  - `report/<run_id>/architecture_model.html` & standalone `docs/IFOG_ARCHITECTURE_EXPLORER.html` — Code-audited interactive HTML5 mathematical block diagram (`viz/architecture_explorer.py`) reconciled 1-to-1 with live C++/Python source code (`EQ-01`..`EQ-44`, 4 signal-path highlight modes, non-specialist intuition, live KPI banner, and formula-to-source audit table).
  - `report/<run_id>/metrics_summary.json`, `report/<run_id>/virtual_calibration_dataset.csv`, and `report/<run_id>/figures/*.png` (up to 21 plots).
  - `report/index.md` and `report/index.html` — Auto-refreshed dashboard listing all runs newest-first with direct links to `report.md`, `report.html`, and `architecture_model.html`.
- **Raw f-string Rule for HTML/KaTeX:** Always use `rf"""..."""` (raw f-strings) when embedding LaTeX/KaTeX expressions inside Python HTML templates to prevent `\tau`, `\Delta`, `\Omega` from turning into control characters or `SyntaxWarning`.
- Spec §5.2 CLI contract (`python3 viz/export_report.py --run data/run01/ --format png,html`) remains 100% backward-compatible when `--report-dir` is omitted.
- `.gitignore` ignores generated `report/*` runs while tracking `report/README.md`.

## 2. Unified Simulation Runner & All-Scenarios Example (`tier3_analysis/sim_runner_cli.py`, `scripts/`, `examples/`)
- Core orchestration resides in `tier3_analysis/sim_runner_cli.py` (enforcing **100.0% Python line coverage**), wrapped by `scripts/run_sim.py`, `scripts/run_sim.sh`, `scripts/run_all_scenarios.sh`, `examples/run_example.sh`, and `ifog-sim-run`.
- Supported **28 `--mode` workflows**:
  - Core SPEC-004: `single`, `gate1`..`gate4`, `full`, `sweep`
  - Gate 5 & Gate 6: `dsp6_compare`, `fmi_gate`
  - Group A Time-Domain: `td_blanking`, `td_step_sine`, `td_vpi_shock`, `td_high_rate`, `td_shupe_shock`, `td_limit_cycles`, `td_all`
  - Group B System Engineering: `eng_hw_sizing`, `eng_imu_3axis`, `eng_vre_faraday`, `eng_fault_bit`, `eng_mc_yield_cal`, `eng_all`
  - Group C Dynamic & Electro-Optic Probe: `dyn_step_response`, `dyn_freq_response`, `dyn_output_psd`, `dyn_sine_electro_optic`, `dyn_all`
  - Complete Official Suite: `all_scenarios` (default for `./scripts/run_all_scenarios.sh`, `./examples/run_example.sh`, and `./scripts/container_run.sh example`, with default `--mc-runs 500`).
- `scripts/run_sim.sh` automatically compiles `build/ifog_sim` via CMake Release (`-O3`) if absent before invoking `scripts/run_sim.py`.

## 3. Industrial Release Docs & Rule 16 Version–Document Sync (`docs/`, `tier3_analysis/doc_sync.py`)
- **Single Source of Truth:** `pyproject.toml` `[project].version` (`X.Y.Z`, SemVer).
- **Mandatory Synchronized Files on Every Version Bump (`vX.Y.Z`):**
  1. `pyproject.toml` (`version = "X.Y.Z"`)
  2. `docs/IFOG_VPROTO_ARCHITECTURE.{md,tex,pdf}`
  3. `docs/IFOG_SIMULATION_SCENARIOS.{md,tex,pdf}`
  4. `docs/RELEASE_NOTES.{md,tex,pdf}`
  5. `docs/DOCS_BUILD.sha256` (generated automatically by `bash scripts/build_docs.sh`, locking all 3 compiled PDFs to their current `.tex` SHA-256 digests so stale PDFs fail CI!)
  6. `docs/CHANGELOG.md` (`## [X.Y.Z]`)
  7. `README.md`, `Containerfile`/`Dockerfile`/`compose.yaml`, and `AGENT.md` (`Rule 16`)
- **Pure-Stdlib CI Verifier:** `tier3_analysis/doc_sync.py` uses ONLY Python 3.12 stdlib (`tomllib`, `hashlib`, `re`, `json`, `pathlib`) so `scripts/verify_doc_sync.py` runs inside the lightweight `governance-and-spec-lock` CI job before pip install.
- **Workflow Command:** Whenever editing `docs/*.tex` or bumping version:
  ```bash
  bash scripts/build_docs.sh
  python3 scripts/verify_doc_sync.py --expected-tag vX.Y.Z
  ```
