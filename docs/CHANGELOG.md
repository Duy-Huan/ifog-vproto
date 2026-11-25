# Changelog — `ifog-vproto`

All notable changes to this project are documented in this file following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html), and are strictly synchronized with `pyproject.toml`, `docs/`, and Git release tags per [`AGENT.md`](../AGENT.md) **Rule 16**.

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
