---
name: ifog-reporting-and-doc-sync
description: Auto-generated Markdown (.md) & Interactive HTML (.html) reporting under report/, unified simulation runner CLI (scripts/run_sim.sh, scripts/run_sim.py), industrial LaTeX/Markdown architecture & release documentation (docs/), and mandatory Rule 16 version-document synchronization.
---

# Automated Reporting, Unified Simulation Runner & Rule 16 Doc-Sync

## 1. Automated Report Generation (`viz/export_report.py` -> `report/`)
- Every orchestrated simulation run (`scripts/run_sim.sh` / `scripts/run_sim.py` / `ifog-sim-run`) writes raw artifacts into `data/<run_id>/` and automatically publishes reports into `report/<run_id>/`:
  - `report/<run_id>/report.md` — Version-stamped Markdown report with Executive Gate Pass/Fail table, Tier 1–3 KPI tables, Dual-Regime 5-Region WLS breakdown, and embedded 300-DPI PNG figure links.
  - `report/<run_id>/report.html` — Self-contained interactive HTML5 diagnostic report with Plotly multi-panel subplots (Dual-Regime AVAR, Deadband/Bunny Ears, $1/f$ Flicker PSD), KPI tables, 300-DPI figure gallery, and collapsible `metrics_summary.json` inspector.
  - `report/<run_id>/metrics_summary.json` and `report/<run_id>/figures/*.png`.
  - `report/index.md` and `report/index.html` — Auto-refreshed dashboard listing all runs newest-first.
- Spec §5.2 CLI contract (`python3 viz/export_report.py --run data/run01/ --format png,html`) remains 100% backward-compatible when `--report-dir` is omitted.
- `.gitignore` ignores generated `report/*` runs while tracking `report/README.md`.

## 2. Unified Simulation Runner (`tier3_analysis/sim_runner_cli.py`, `scripts/run_sim.{py,sh}`)
- Core orchestration resides in `tier3_analysis/sim_runner_cli.py` (so `pytest-cov` enforces **100.0% line coverage** over all workflow orchestration logic), wrapped by thin entrypoints `scripts/run_sim.py`, `scripts/run_sim.sh`, and `ifog-sim-run`.
- Supported `--mode` workflows:
  - `single` (Tier 1 + Tier 2 baseline)
  - `gate1`, `gate2`, `gate3`, `gate4` (individual normative acceptance gates)
  - `full` (complete real 4-Gate acceptance suite into ONE unified `report/<run_id>/` bundle with all 4 figures)
  - `sweep` (any parallel sweep JSON or directory)
- `scripts/run_sim.sh` automatically compiles `build/ifog_sim` via CMake Release (`-O3`) if absent before invoking `scripts/run_sim.py`.

## 3. Industrial Release Docs & Rule 16 Version–Document Sync (`docs/`, `tier3_analysis/doc_sync.py`)
- **Single Source of Truth:** `pyproject.toml` `[project].version` (`X.Y.Z`, SemVer).
- **Mandatory Synchronized Files on Every Version Bump (`vX.Y.Z`):**
  1. `pyproject.toml` (`version = "X.Y.Z"`)
  2. `docs/IFOG_VPROTO_ARCHITECTURE.md` (header `Current Version` + Revision History row `| \`vX.Y.Z\` |`)
  3. `docs/IFOG_VPROTO_ARCHITECTURE.tex` (`\newcommand{\DocVersion}{vX.Y.Z}` + Revision History row `\texttt{vX.Y.Z} &`) + compiled `docs/IFOG_VPROTO_ARCHITECTURE.pdf`
  4. `docs/RELEASE_NOTES.md` & `docs/RELEASE_NOTES.tex` (`vX.Y.Z`) + compiled `docs/RELEASE_NOTES.pdf`
  5. `docs/DOCS_BUILD.sha256` (generated automatically by `bash scripts/build_docs.sh`, locking compiled PDFs to current `.tex` SHA-256 digests so stale PDFs fail CI!)
  6. `docs/CHANGELOG.md` (`## [X.Y.Z]`)
  7. `README.md` (version badge `vX.Y.Z`) and `AGENT.md` (`Rule 16`)
- **Pure-Stdlib CI Verifier:** `tier3_analysis/doc_sync.py` uses ONLY Python 3.12 stdlib (`tomllib`, `hashlib`, `re`, `json`, `pathlib`) so `scripts/verify_doc_sync.py` runs inside the lightweight `governance-and-spec-lock` CI job before pip install.
- **Workflow Command:** Whenever editing `docs/*.tex` or bumping version:
  ```bash
  bash scripts/build_docs.sh
  python3 scripts/verify_doc_sync.py --expected-tag vX.Y.Z
  ```
