# Project Skills Library (`skills/`)

> **Mandatory Usage Rule (AGENT.md Rule 6):**
> Before designing, editing, debugging, or verifying ANY module in `ifog-vproto`, every agent MUST first read this index and load the relevant `SKILL.md` file(s) below. After every design iteration, bug discovery, or calibration improvement, agents MUST distill and record new findings back into the corresponding `SKILL.md`.

## Skill Index

| Skill Directory | Scope / Subsystems | When to Load |
| :--- | :--- | :--- |
| [`ifog-spec-formula-verification/`](ifog-spec-formula-verification/SKILL.md) | `spec/`, `tests/formula_verification/`, `scripts/verify_formulas_ci.py` | Verifying `EQ-01`..`EQ-41`, checking sign conventions, unit conversions, Jury stability, or CI formula matrix |
| [`ifog-tier1-optical-thermal/`](ifog-tier1-optical-thermal/SKILL.md) | `tier1_offline/`, `configs/` | Working on Spectral-Sliced Jones optics, 1D/FEM thermal Shupe solver, JSON Schema v5/v4, or `phys_params.json`/`shupe_lut.bin` |
| [`ifog-tier2-sysc-ams-core/`](ifog-tier2-sysc-ams-core/SKILL.md) | `tier2_sysc_ams/`, `scripts/install_systemc_ams.sh`, `scripts/run_cpp_coverage.sh` | Modifying C++17 / SystemC / SystemC-AMS PoC 2.3.4 TDF/DE modules, `sca_ltf_nd`, PRBS dither, 32B/64B binary logs, or 100% `gcovr` coverage |
| [`ifog-6state-and-scenarios/`](ifog-6state-and-scenarios/SKILL.md) | `tier2_sysc_ams/src/imu_3axis.cpp`, `digital_dsp_sc.cpp`, `tier3_analysis/scenarios_*.py`, `viz/plot_scenarios.py`, `docs/IFOG_SIMULATION_SCENARIOS.*` | Working on official 6-state symmetric DSP (`EQ-31`–`EQ-34`), 6 Time-Domain (`TD-01`..`TD-06`), 5 System Engineering (`ENG-01`..`ENG-05`, `EQ-35`–`EQ-41`), 3-axis IMU crosstalk, VRE/Faraday, BIT/FDIR, or MC Yield/Thermal Cal |
| [`ifog-tier3-dual-regime-avar/`](ifog-tier3-dual-regime-avar/SKILL.md) | `tier3_analysis/`, `viz/` | Working on parallel sweeps, Deadband/Bunny Ears, $1/f$ Welch PSD, $\mathbf{K}$-matrix extraction, Dual-Regime Overlapping AVAR, WLS 5-region fit, or `viz/` plots |
| [`ifog-reporting-and-doc-sync/`](ifog-reporting-and-doc-sync/SKILL.md) | `viz/export_report.py`, `tier3_analysis/sim_runner_cli.py`, `tier3_analysis/doc_sync.py`, `scripts/run_sim.*`, `scripts/run_all_scenarios.sh`, `report/`, `docs/` | Running unified simulations, customizing auto-generated `.md`/`.html` reports under `report/`, updating architecture/scenarios/release `.md`/`.tex`/`.pdf` docs, or verifying Rule 16 version–document sync |
| [`ifog-portable-container-env/`](ifog-portable-container-env/SKILL.md) | `Containerfile`, `Dockerfile`, `compose.yaml`, `scripts/setup_env.sh`, `scripts/install_systemc*.sh`, `scripts/container_run.sh`, `examples/` | Setting up portable Git-built SystemC/SystemC-AMS/Python environments on any Linux distro, building/running Docker or Podman containers, or reproducing full 4-Gate examples |
| [`ifog-cicd-release-workflow/`](ifog-cicd-release-workflow/SKILL.md) | `.github/workflows/`, `AGENT.md`, Git branches & tags | Running CI/CD checks, enforcing 2-branch (`dev`->`main`) policy, dual spec locks, Rule 16 doc-sync, merging PRs, or cutting SemVer `vX.Y.Z` release tags |
