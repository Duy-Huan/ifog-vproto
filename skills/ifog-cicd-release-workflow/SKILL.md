---
name: ifog-cicd-release-workflow
description: Strict 2-branch (dev -> main) Git governance, zero-extra-branch enforcement, dual spec SHA-256 locks, 100% dual-domain (Python + C++) coverage, 41-formula CI verification, real Gate 1-5 + 11-scenario simulation, and SemVer vX.Y.Z release tag procedure.
---

# CI/CD Governance & SemVer Release Workflow

## 1. Strict Branch & Spec Immutability Rules (AGENT.md Rules 1, 4, 7)
- **Allowed Branches:** ONLY `main` and `dev` may exist locally or on `origin`. Never create `feat/*`, `fix/*`, or temporary branches.
- **Pre-Work Sync:** Always start every session with:
  ```bash
  git fetch --all --prune && git checkout dev && git pull origin dev
  sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256
  ```
- **Dual Spec Lock:** Both `spec/IFOG-SIM-SPEC-004.tex` and `spec/IFOG-SIM-SPEC-005.tex` are byte-locked by `.sha256`. CI fails immediately on any unauthorized edit.

## 2. Mandatory CI/CD Pipeline Gates (`.github/workflows/ci.yml`)
1. `governance-and-spec-lock`: Verifies branch list $\subseteq \{\text{main}, \text{dev}\}$, verifies both `spec/IFOG-SIM-SPEC-004.sha256` and `spec/IFOG-SIM-SPEC-005.sha256`, verifies compiled spec PDFs exist, verifies `AGENT.md` and all **8 project skills** exist, and executes `python3 scripts/verify_doc_sync.py` (**Rule 16** across all 3 docs).
2. `build-and-verify`: Installs SystemC 2.3.4 + caches/builds SystemC-AMS PoC 2.3.4, builds Release `-O3` (`build/ifog_sim`), runs `ifog_cpp_tests`, enforces **100.0% C++ line coverage** (`gcovr`), verifies all **41 / 41 spec formulas** (`EQ-01`..`EQ-41`), enforces **100.0% Python line coverage** (`pytest-cov`), and runs full real Gate 1–5 + 6 Time-Domain + 5 System Engineering simulations + deterministic regression.
3. `container-build-and-verify`: Builds `Containerfile` from Git sources (SystemC 2.3.4 + SystemC-AMS 2.3.4 + `nlohmann/json` + Python 3.12 venv + Tier 2 Release) with Buildx GHA cache and executes a live in-container Gate 1 simulation producing host-mounted `report/` outputs.

## 3. SemVer Release Tag Procedure (`vX.Y.Z` — Rules 8 & 16)
1. Bump `pyproject.toml` version to `X.Y.Z`, synchronize `docs/IFOG_VPROTO_ARCHITECTURE.{md,tex}`, `docs/IFOG_SIMULATION_SCENARIOS.{md,tex}`, `docs/RELEASE_NOTES.{md,tex}`, `docs/CHANGELOG.md`, `Containerfile`/`Dockerfile`/`compose.yaml`, `README.md`, and `skills/`, run `bash scripts/build_docs.sh`, and verify `python3 scripts/verify_doc_sync.py --expected-tag vX.Y.Z`.
2. Confirm all tests & CI pass on `dev` (`git push origin dev` -> wait for CI `success`).
3. Open PR `dev` -> `main` via `gh pr create --base main --head dev ...` and wait for ALL PR checks to pass.
4. Merge PR using `gh pr merge <num> --merge` (**NEVER** pass `--delete-branch`; preserve `dev`!).
5. Checkout `main`, pull `origin/main`, wait for `CI` on `main` to pass `success`.
6. Create annotated SemVer tag and push:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z — Closed-Loop IFOG Virtual Prototype (IFOG-SIM-SPEC-005)"
   git push origin vX.Y.Z
   ```
7. Wait for `.github/workflows/release.yml` to enforce `--expected-tag vX.Y.Z` doc-sync, re-verify all gates, and publish GitHub Release `vX.Y.Z` with all 14 attached assets (both spec PDFs, all 3 doc bundles `.pdf/.md/.tex`, formula matrix, and coverage reports).
8. Sync `dev` back with `main` (`git checkout dev && git merge --ff-only main && git push origin dev`).

## 4. Empirical CI/CD Toolchain Gotchas (Accumulated Lessons)
- **Pin `runs-on: ubuntu-24.04` (never `ubuntu-latest`):** GitHub's `ubuntu-latest` migrates to newer LTS images (e.g., `ubuntu-26.04`) with newer `automake` / GCC / SystemC versions that break `aclocal-1.16` and SystemC 2.3.4 ABI parity. Pinning `ubuntu-24.04` ensures bit-consistent SystemC 2.3.4 (`SC_CPLUSPLUS=201703L`), `gcovr`, and `actions/cache` keys across CI and Release workflows.
- **Autotools Timestamp Trap on `git clone`:** When building SystemC-AMS PoC 2.3.4 from a fresh `git clone`, `configure.ac` can share the same mtime as `aclocal.m4`/`Makefile.in`, causing `make` to invoke version-pinned `aclocal-1.16` and fail with exit code 127. `scripts/install_systemc_ams.sh` explicitly orders timestamps **strictly in the past** (`configure.ac`/`*.m4` `-20s` < `aclocal.m4` `-15s` < `configure` `-10s` < `config.h.in` `-8s` < `Makefile.in` `-5s` < `now`, avoiding `configure`'s future-clock sanity error) and passes `ACLOCAL=true AUTOMAKE=true AUTOCONF=true AUTOHEADER=true` to `make`.
- **Private Repo Actions Quota:** A 1–2 s failure with `runner_id: 0`, `steps: []`, and `log not found` before any step executes indicates GitHub rejected runner allocation (e.g., private-repo free-tier quota / spending limit), not a workflow YAML error.
- **Transient GitHub API 500/502 on Release Publish:** During GitHub API degraded-performance events, a single unretried `gh release create <tag> <14-assets>` can fail with HTTP 500/502 right after all 4-minute verification gates pass. Always separate `gh release create` (idempotent 8-attempt retry checking `gh release view`) from per-asset `gh release upload --clobber` (5-attempt retry) in `.github/workflows/release.yml`.

