# Changelog — `ifog-vproto`

All notable changes to this project are documented in this file following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html), and are strictly synchronized with `pyproject.toml`, `docs/`, and Git release tags per [`AGENT.md`](../AGENT.md) **Rule 16**.

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
