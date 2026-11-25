# Project Skills Library (`skills/`)

> **Mandatory Usage Rule (AGENT.md Rule 6):**
> Before designing, editing, debugging, or verifying ANY module in `ifog-vproto`, every agent MUST first read this index and load the relevant `SKILL.md` file(s) below. After every design iteration, bug discovery, or calibration improvement, agents MUST distill and record new findings back into the corresponding `SKILL.md`.

## Skill Index

| Skill Directory | Scope / Subsystems | When to Load |
| :--- | :--- | :--- |
| [`ifog-spec-formula-verification/`](ifog-spec-formula-verification/SKILL.md) | `spec/`, `tests/formula_verification/`, `scripts/verify_formulas_ci.py` | Verifying `EQ-01`..`EQ-30`, checking sign conventions, unit conversions, Jury stability, or CI formula matrix |
| [`ifog-tier1-optical-thermal/`](ifog-tier1-optical-thermal/SKILL.md) | `tier1_offline/`, `configs/` | Working on Spectral-Sliced Jones optics, 1D/FEM thermal Shupe solver, JSON Schema v4, or `phys_params.json`/`shupe_lut.bin` |
| [`ifog-tier2-sysc-ams-core/`](ifog-tier2-sysc-ams-core/SKILL.md) | `tier2_sysc_ams/`, `scripts/install_systemc_ams.sh`, `scripts/run_cpp_coverage.sh` | Modifying C++17 / SystemC / SystemC-AMS PoC 2.3.4 TDF/DE modules, `sca_ltf_nd`, PRBS dither, 32B `SimRecord`, or 100% `gcovr` coverage |
| [`ifog-tier3-dual-regime-avar/`](ifog-tier3-dual-regime-avar/SKILL.md) | `tier3_analysis/`, `viz/` | Working on parallel sweeps, Deadband/Bunny Ears, $1/f$ Welch PSD, $\mathbf{K}$-matrix extraction, Dual-Regime Overlapping AVAR, WLS 5-region fit, or `viz/` reports |
| [`ifog-cicd-release-workflow/`](ifog-cicd-release-workflow/SKILL.md) | `.github/workflows/`, `AGENT.md`, Git branches & tags | Running CI/CD checks, enforcing 2-branch (`dev`->`main`) policy, merging PRs, or cutting SemVer `vX.Y.Z` release tags |
