---
name: ifog-cicd-release-workflow
description: Strict 2-branch (dev -> main) Git governance, zero-extra-branch enforcement, spec SHA-256 lock, 100% dual-domain (Python + C++) coverage, 30-formula CI verification, real 4-Gate simulation, and SemVer vX.Y.Z release tag procedure.
---

# CI/CD Governance & SemVer Release Workflow

## 1. Strict Branch & Spec Immutability Rules (AGENT.md Rules 1, 4, 7)
- **Allowed Branches:** ONLY `main` and `dev` may exist locally or on `origin`. Never create `feat/*`, `fix/*`, or temporary branches.
- **Pre-Work Sync:** Always start every session with:
  ```bash
  git fetch --all --prune && git checkout dev && git pull origin dev
  sha256sum -c spec/IFOG-SIM-SPEC-004.sha256
  ```
- **Spec Lock:** `spec/IFOG-SIM-SPEC-004.tex` is byte-locked by `spec/IFOG-SIM-SPEC-004.sha256`. CI fails immediately on any unauthorized edit.

## 2. Mandatory CI/CD Pipeline Gates (`.github/workflows/ci.yml`)
1. `governance-and-spec-lock`: Verifies branch list $\subseteq \{\text{main}, \text{dev}\}$, verifies `spec/IFOG-SIM-SPEC-004.sha256`, verifies `spec/IFOG-SIM-SPEC-004.pdf` exists, verifies `AGENT.md` and `skills/README.md` exist.
2. `cpp-build-and-100pct-coverage`: Installs SystemC 2.3.4 + caches/builds SystemC-AMS PoC 2.3.4, builds Release `-O3` (`build/ifog_sim`), runs `ifog_cpp_tests`, and runs `scripts/run_cpp_coverage.sh` enforcing **100.0% C++ line coverage** (`gcovr --fail-under-line 100`).
3. `formula-verification-30eq`: Runs `python3 scripts/verify_formulas_ci.py`, asserting ALL 30 spec formulas (`EQ-01` .. `EQ-30`) individually PASS and uploading `formula_verification_matrix.md/.json`.
4. `python-unit-and-100pct-coverage`: Runs `pytest tests/unit tests/formula_verification --cov` enforcing **100.0% Python line coverage** (`fail_under = 100` in `pyproject.toml`).
5. `real-4gate-system-and-regression`: Runs `pytest tests/system -v` executing ALL 4 real full-scale acceptance gates (Gate 1 linear baseline + continuous $2\pi$ flyback, Gate 2 full slow rate ramp sweep $[-0.5, +0.5]^\circ/\text{s}$, Gate 3 real 2 s $1/f$ PSD + $100\text{ Hz}$ $\mathbf{K}$-matrix repeatability, Gate 4 real 60 s Fast-Scale + 10 h / $3.6\times 10^6$-sample Slow-Scale Dual-Regime AVAR + deterministic regression). Zero smoke tests permitted!

## 3. SemVer Release Tag Procedure (`vX.Y.Z` — Rule 8)
1. Confirm all tests & CI pass on `dev` (`git push origin dev` -> wait for CI `success`).
2. Open PR `dev` -> `main` via `gh pr create --base main --head dev ...` and wait for ALL PR checks to pass.
3. Merge PR using `gh pr merge <num> --merge` (**NEVER** pass `--delete-branch`; preserve `dev`!).
4. Checkout `main`, pull `origin/main`, wait for `CI` on `main` to pass `success`.
5. Create annotated SemVer tag and push:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z — Closed-Loop IFOG Virtual Prototype (IFOG-SIM-SPEC-004)"
   git push origin vX.Y.Z
   ```
6. Wait for `.github/workflows/release.yml` to re-verify all gates and publish the GitHub Release `vX.Y.Z` with attached spec PDF, formula verification matrix, and coverage reports.
7. Sync `dev` back with `main` (`git checkout dev && git merge main && git push origin dev`).
