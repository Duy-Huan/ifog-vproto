# AGENT.md — Governance, Engineering Rules & Workflow Contract for `ifog-vproto`

**Project:** Closed-Loop IFOG Multi-Scale Virtual Prototype (`ifog-vproto`)
**Normative Specifications:** [`spec/IFOG-SIM-SPEC-005.tex`](spec/IFOG-SIM-SPEC-005.tex) & [`spec/IFOG-SIM-SPEC-005.pdf`](spec/IFOG-SIM-SPEC-005.pdf) (v5.0, active); [`spec/IFOG-SIM-SPEC-004.tex`](spec/IFOG-SIM-SPEC-004.tex) & [`spec/IFOG-SIM-SPEC-004.pdf`](spec/IFOG-SIM-SPEC-004.pdf) (v4.0, archival baseline)
**Reference Standards:** IEEE Std 952-2020 (IFOG Test & AVAR); IEEE Std 1666.1-2016 (SystemC-AMS)
**Architecture:** 3-Tier Hybrid Co-Simulation (Python Tier 1 Offline Optics/Thermal -> C++17 / SystemC + SystemC-AMS PoC Tier 2 Fast-Scale Core [Single-Axis & 3-Axis IMU] -> Python Tier 3 Dual-Regime AVAR, 11 Official Scenarios & `viz/`)

---

## 1. Project Objectives

1. **Full Spec-Driven Implementation:** Implement all subsystems specified in `IFOG-SIM-SPEC-005` (and `IFOG-SIM-SPEC-004`) (`spec/`, `configs/`, `tier1_offline/`, `tier2_sysc_ams/`, `tier3_analysis/`, `viz/`, `tests/`) with strict 1-to-1 mathematical fidelity to all **41 normative equations (`EQ-01` .. `EQ-41`)**.
2. **Genuine Multi-Scale Simulation Core:** Build and execute a real C++ `-O3` IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4 closed-loop simulator (`OpticalEnvelope_TDF`, `AnalogFrontEnd_TDF` with hybrid `sca_ltf_nd`, `PinkNoise_TDF`, `ADC_Bridge_TDF2DE`, `DAC_Driver_TDF` with `set_delay(1)`, bit-true `DigitalDSP_SC` supporting 2-state, 4-state Lefèvre, and **official 6-state symmetric demodulation** + real-time FPGA BIT/FDIR, and concurrent 3-axis IMU `SharedPowerBus_TDF` / `--imu3axis`).
3. **5-Gate + 11-Scenario Quantitative Verification:** Pass Gates 1–4 (Golden Linear, Deadband & Bunny Ears >=90%, $1/f$ Flicker & $\mathbf{K}$-matrix <2%, 60 s Fast + 10 h Slow Dual-Regime AVAR), **Gate 5** (Official 6-State DSP `+136.9 dB` RAM/crosstalk rejection & `-33.3%` peak voltage), **6 Time-Domain scenarios (`TD-01`..`TD-06`)**, and **5 System Engineering & Production scenarios (`ENG-01`..`ENG-05`)**.
4. **Zero-Defect CI/CD & Maintainable Release Lifecycle:** Enforce 100% test coverage (Python + C++), 41-formula CI verification, real full-duration simulation execution (zero smoke-test shortcuts), strict 2-branch Git discipline (`dev` -> `main`), mandatory Rule 16 version–doc synchronization, and SemVer `x.y.z` tagged releases.

---

## 2. Mandatory Project Rules

### Core Governance Rules (Owner-Mandated)

- **Rule 1 — Strict 2-Branch Git Model & SemVer Tag Releases:**
  - All development MUST occur exclusively on branch `dev`.
  - Changes reach `main` ONLY by merging `dev` into `main` through a Pull Request after all CI/CD checks pass.
  - **NO OTHER BRANCHES MAY EVER BE CREATED** (no `feature/*`, `fix/*`, `hotfix/*`, `release/*`, or ad-hoc branches locally or on `origin`). CI explicitly fails if any branch outside `{main, dev}` exists.
  - Releases MUST be cut from `main` using annotated Git tags following semantic versioning `v<MAJOR>.<MINOR>.<PATCH>` (numeric `x.y.z`, e.g., `v2.0.0`).
- **Rule 2 — Comprehensive Unit, System, Regression Testing & 100% Coverage:**
  - Every module across Tier 1 (`tier1_offline/`), Tier 2 (`tier2_sysc_ams/`), Tier 3 (`tier3_analysis/`), and Visualization (`viz/`) MUST have thorough unit tests, end-to-end system tests, and bit-exact/numerical regression tests.
  - **100% code coverage is mandatory** in both domains:
    - Python: `pytest --cov` MUST report `100%` line coverage across `tier1_offline`, `tier3_analysis`, and `viz`.
    - C++: `gcovr` MUST report `100%` line coverage across `tier2_sysc_ams/src` and `tier2_sysc_ams/include`.
- **Rule 3 — Strict Spec Fidelity & Per-Formula CI/CD Verification:**
  - Every design decision, data contract, CLI interface, and physical equation MUST strictly follow `spec/IFOG-SIM-SPEC-005` (and `IFOG-SIM-SPEC-004`).
  - All **41 normative equations (`EQ-01` through `EQ-41`)** MUST each have an independent, isolated verification test under `tests/formula_verification/` executed as a dedicated mandatory job in CI/CD, outputting a formula traceability matrix.
- **Rule 4 — Mandatory Pre-Work Git Synchronization:**
  - Before starting ANY development, debugging, documentation, or release task, agents MUST run `git fetch --all --prune` and pull the latest changes from `origin/dev` (and inspect `origin/main` alignment).
- **Rule 5 — 100% Real Full-Scale Simulation (No Smoke Tests Allowed):**
  - Never substitute reduced-time smoke tests, mocked physics, or synthetic shortcuts for real simulation verification.
  - Gates 1–4 (including real 60 s Fast-Scale + 10 h / 3.6M-sample Slow-Scale AVAR), Gate 5 (4-state vs 6-state DSP), all 6 Time-Domain scenarios (`TD-01`..`TD-06`), and all 5 System Engineering scenarios (`ENG-01`..`ENG-05`, including real concurrent 3-axis SystemC-AMS IMU `--imu3axis`) MUST execute end-to-end using the compiled `ifog_sim` binary and Python analysis pipeline.
- **Rule 6 — Continuous Skill Accumulation & Mandatory Skill Usage:**
  - After every subsystem design, bug discovery, numerical calibration, or architectural iteration, distilled engineering lessons MUST be recorded into `skills/<skill-name>/SKILL.md` and indexed in `skills/README.md`.
  - **Mandatory Pre-Work Skill Rule:** Before modifying any subsystem, every agent MUST first read `skills/README.md` and the relevant `skills/*/SKILL.md` file(s) and follow all documented invariants, sign conventions, and checklists.
- **Rule 7 — Specification Immutability (Dual Checksum Lock):**
  - `spec/IFOG-SIM-SPEC-004.tex` and `spec/IFOG-SIM-SPEC-005.tex` (and their rendered PDFs) MUST NOT be modified under any circumstance without explicit approval from the project owner.
  - CI/CD enforces byte-level immutability via `sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256`.
- **Rule 8 — Gated Release Tag Procedure:**
  - No release tag (`vX.Y.Z`) may be created until ALL local and CI/CD pipelines (dual spec checksum locks, branch policy check, 41-formula verification, 100% C++ coverage, 100% Python coverage, Rule 16 doc-sync, and full real Gate 1–5 + 11-scenario system simulations) pass with zero failures on `main`. See Section 5 for the exact step-by-step release procedure.

### Additional Engineering Rules (Derived from `IFOG-SIM-SPEC-004` & `IFOG-SIM-SPEC-005`)

- **Rule 9 — 64-Bit Floating-Point Envelope Precision & Modulo-$2\pi$ Wrapping:**
  - All optical and analog signal paths MUST use IEEE-754 64-bit `double`.
  - Differential MIOC phases ($\Delta\phi_{\text{mod}}$) and digital phase ramps ($\phi_{\text{ramp}}$) MUST apply $\operatorname{wrap}_{2\pi}(x) = x - 2\pi\operatorname{round}(x / 2\pi)$ so rounding error remains $< 10^{-15}\text{ rad}$.
- **Rule 10 — SystemC-AMS Timing Contract & Algebraic Loop Breaking:**
  - `OpticalEnvelope_TDF` and `AnalogFrontEnd_TDF` operate at `rate = K` ($K \in \{16, 32\}$) with cluster period $\tau = n_{\text{eff}} L / c$.
  - `PinkNoise_TDF`, `NominalBus_TDF`, and `SharedPowerBus_TDF` operate at `rate = 1` per $\tau$.
  - `DAC_Driver_TDF` MUST set `set_delay(1)` on its DE input port (`dac_code`) and `rail_droop_in` to break closed-loop algebraic dependencies cleanly.
- **Rule 11 — Fail-Closed Stability & Schema Validation:**
  - Every configuration JSON MUST validate against `configs/schema_v5.json` (backward-compatible with `"4.0"` and `"5.0"`) before simulation starts.
  - `ifog_sim` MUST verify Jury stability ($0 < K_{\text{tot},1} < 1$) and dual-loop bandwidth separation ($K_{\text{tot},2} \le 0.1\,K_{\text{tot},1}$ for both `4state` and `6state`) at startup and fail-closed with a non-zero exit code if violated.
- **Rule 12 — Deterministic Seed Discipline & Packed Binary I/O Contracts:**
  - All PRNGs (fiber Jones perturbations, TIA 6-component white noise, 5-pole IIR $1/f$ noise, ADC aperture jitter, LFSR PRBS dither, Slow-Scale ARW/RRW, Monte Carlo tolerances) MUST be seeded explicitly from configuration.
  - Packed binary structs are enforced at compile time via `static_assert`: `SimRecord == 32 B` (`sim_out.bin`), `MicroRecord == 64 B` (`micro_waveforms.bin`), and `DspTraceRecord == 64 B` (`dsp_trace.bin`).
- **Rule 13 — Quantitative Acceptance & Physical Sign Fidelity:**
  - Maintain verified 4-state signs ($e_\Omega = (y_2-y_1)+(y_4-y_3)$, $e_{V_\pi} = (y_3+y_4)-(y_1+y_2)$) and official 6-state 3-channel signs ($e_\Omega^{(6)} = (y_4+y_5+y_6)-(y_1+y_2+y_3)$, $e_{V_\pi}^{(6)} = 2(y_2+y_5)-(y_1+y_3+y_4+y_6)$, $e_{\text{asym}}^{(6)} = (y_1-y_3)+(y_6-y_4)$) with negative-feedback ramp polarity so $\Delta\phi_{\text{step}} \to +K_{\text{opt}}\Omega_{\text{in}}$ and $G_{\text{DAC}} \to 1/(1+\epsilon_{V_\pi})$.
  - Keep unit conversion constant exact: $1\text{ rad/s} = (180/\pi)\times 3600 \approx 206264.806247\,^\circ/\text{h}$.
- **Rule 14 — Dual-Domain 100% Coverage & Zero Untested Dead Code:**
  - No dead branches, unexecuted error handlers, or uncovered helper utilities are permitted. Any code added to `tier1_offline/`, `tier2_sysc_ams/`, `tier3_analysis/`, or `viz/` MUST have immediate deterministic tests keeping both Python and C++ coverage at exactly `100.0%`.
- **Rule 15 — Self-Contained Reproducibility & Automated Reporting:**
  - Never hardcode machine-specific paths; all build scripts, CMake files, and CLI invocations must be portable across Linux distros and Docker/Podman containers.
  - All orchestrated simulation runs via `scripts/run_sim.sh` / `scripts/run_all_scenarios.sh` MUST automatically generate both Markdown (`report.md`) and interactive HTML (`report.html`) reports plus refreshed `report/index.{md,html}` under `report/`.
- **Rule 16 — Mandatory Version–Document Synchronization (Release Documentation Lock):**
  - `pyproject.toml` (`[project].version`, SemVer `X.Y.Z`) is the **single source of truth** for the project release version.
  - Every version bump (`vX.Y.Z`) or architectural/feature change MUST synchronously update ALL canonical architecture, scenario, and release documents BEFORE merging `dev -> main` or tagging `vX.Y.Z`:
    1. `pyproject.toml` (`version = "X.Y.Z"`)
    2. `docs/IFOG_VPROTO_ARCHITECTURE.md` & `.tex` + freshly compiled `.pdf`
    3. `docs/IFOG_SIMULATION_SCENARIOS.md` & `.tex` + freshly compiled `.pdf`
    4. `docs/RELEASE_NOTES.md` & `.tex` + freshly compiled `.pdf`
    5. `docs/DOCS_BUILD.sha256` (locking all 3 compiled PDFs to their exact `.tex` sources via `bash scripts/build_docs.sh`)
    6. `docs/CHANGELOG.md` (`## [X.Y.Z]`)
    7. `README.md` (version badge `vX.Y.Z`), `Containerfile`/`Dockerfile`/`compose.yaml` (`X.Y.Z`), and `skills/` (`skills/README.md` + affected `SKILL.md`)
  - CI/CD enforces this fail-closed via `python3 scripts/verify_doc_sync.py` on every push/PR and `python3 scripts/verify_doc_sync.py --expected-tag vX.Y.Z` on every release tag.

---

## 3. Mandatory Pre-Work Agent Checklist

Every agent MUST execute these steps in order before writing or editing any code:

1. **Sync Git (Rule 4):**
   ```bash
   git fetch --all --prune
   git checkout dev
   git pull origin dev
   ```
2. **Verify Branch Policy (Rule 1):** Confirm ONLY `main` and `dev` exist (`git branch -a`). Never create any third branch.
3. **Verify Dual Spec Integrity & Doc Sync (Rules 7 & 16):** Run `sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256` and `python3 scripts/verify_doc_sync.py`.
4. **Load Project Skills (Rule 6):** Read `skills/README.md` and all `skills/*/SKILL.md` relevant to the target subsystem(s).
5. **Implement, Test & Verify (Rules 2, 3, 5, 14):** Run unit tests, 41-formula verification, 100% coverage checks (Python + C++), and full-scale simulation gates & scenarios.
6. **Synchronize Docs & Accumulate Skills (Rules 6 & 16):** Update `docs/*.{md,tex}`, recompile all 3 PDFs via `bash scripts/build_docs.sh`, verify `python3 scripts/verify_doc_sync.py`, and record new lessons into `skills/*/SKILL.md` before committing.

---

## 4. Normative Formula Registry (`EQ-01` .. `EQ-41`)

Every formula in `IFOG-SIM-SPEC-004` (`EQ-01`..`EQ-30`) and `IFOG-SIM-SPEC-005` (`EQ-31`..`EQ-41`) is uniquely tracked and verified in `tests/formula_verification/`:

| ID | Spec Section | Formula Summary | Implementation Binding |
| :--- | :--- | :--- | :--- |
| `EQ-01` | SPEC-004 §1 Eq. (1) | 4-state bias phase sequence $\phi_1..\phi_4$ | `tier2_sysc_ams/src/digital_dsp_sc.cpp` |
| `EQ-02` | SPEC-004 §1 Eqs. (2)–(5) | 1st-order Taylor expansion at 4 bias states | `tests/formula_verification/test_formulas_dsp.py` |
| `EQ-03` | SPEC-004 §1 Eq. (6) | Orthogonal 4-state demodulation ($e_\Omega, e_{V_\pi}, S_\alpha$) | `tier2_sysc_ams/src/digital_dsp_sc.cpp` |
| `EQ-04` | SPEC-004 §3.1.1 Eq. (7) | Spectral-sliced Jones matrices $\mathbf{J}_{\text{CW}}, \mathbf{J}_{\text{CCW}}$ | `tier1_offline/jones_spectral.py` |
| `EQ-05` | SPEC-004 §3.1.1 Eq. (8) | Fringe visibility $V$ and polarization phase $\phi_{\text{pol}}$ | `tier1_offline/jones_spectral.py` |
| `EQ-06` | SPEC-004 §3.1.2 Eq. (9) | Transit time $\tau$ and total non-reciprocal phase $\Delta\phi_{\text{NR}}[m]$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` |
| `EQ-07` | SPEC-004 §3.1.2 Eq. (10a) | Sagnac optical scale factor $K_{\text{opt}} = 2\pi L D / (\bar{\lambda} c)$ | `tier1_offline/jones_spectral.py`, `tier2_sysc_ams/` |
| `EQ-08` | SPEC-004 §3.1.2 Eq. (10b) | Optical Kerr phase $\Delta\phi_{\text{Kerr}}$ with $\eta_{\text{coh}}$ | `tier1_offline/jones_spectral.py`, `tier2_sysc_ams/` |
| `EQ-09` | SPEC-004 §3.1.2 Eq. (11) | Thermal Shupe integral $\Delta\phi_{\text{Shupe}}(t)$ with $\delta z_{\text{quad}}$ | `tier1_offline/shupe_thermal.py` |
| `EQ-10` | SPEC-004 §3.1.2 Eq. (12) | Magneto-optic Faraday phase $\Delta\phi_{\text{Faraday}}(t)$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` |
| `EQ-11` | SPEC-004 §3.1.2 Eq. (13) | MIOC phase $\phi_{\text{MIOC}}[m]$ with $\epsilon_{V_\pi}, \gamma_{\text{nl}}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` |
| `EQ-12` | SPEC-004 §3.1.2 Eq. (14) | Differential modulation phase $\Delta\phi_{\text{mod}}[m]$ & $\operatorname{wrap}_{2\pi}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` |
| `EQ-13` | SPEC-004 §3.1.2 Eq. (15) | Photodiode power $P_{\text{det}}[m]$ with $\alpha_{\text{RAM}}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` |
| `EQ-14` | SPEC-004 §3.2.1 Eq. (16) | TIA inverting-node total current $I_{\text{in}}[m]$ with crosstalk | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` |
| `EQ-15` | SPEC-004 §3.2.1 Eq. (17) | 6-component noise PSD $S_{i,\text{tot}}(f,m)$ & variance $\sigma_{i,\text{w}}^2$ | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` |
| `EQ-16` | SPEC-004 §3.2.2 Eqs. (18)–(19) | 2nd-order TIA transfer function $H_{\text{TIA}}(s), \omega_0, \zeta$ | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` |
| `EQ-17` | SPEC-004 §3.2.2 Eq. (20) | Butterworth $C_{f,\text{opt}}$ and $t_s(0.1\%)$ | `tier2_sysc_ams/include/ifog_math.hpp` |
| `EQ-18` | SPEC-004 §3.2.3 Eqs. (21)–(22) | TIA $1/f$ offset & cubic polynomial nonlinearity + clip | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` |
| `EQ-19` | SPEC-004 §3.2.3 Eq. (23) | ADC blanking window, $\eta_b$, $N_{\text{ADC}}$ quantizer, $1/\sqrt{\eta_b}$ | `tier2_sysc_ams/src/adc_dac_bridge.cpp` |
| `EQ-20` | SPEC-004 §3.3.1 Eqs. (24)–(27) | 2-state & 4-state Loop-1/Loop-2 integrator updates | `tier2_sysc_ams/src/digital_dsp_sc.cpp` |
| `EQ-21` | SPEC-004 §3.3.1 Eqs. (28)–(29) | Digital phase ramp $\operatorname{wrap}_{2\pi}$ & DAC code with PRBS | `tier2_sysc_ams/src/digital_dsp_sc.cpp` |
| `EQ-22` | SPEC-004 §3.3.2 Eqs. (30)–(31) | Z-domain $L_1(z)$, Jury stability $0<K_{\text{tot}}<1$, Loop-2 separation | `tier2_sysc_ams/include/ifog_math.hpp` |
| `EQ-23` | SPEC-004 §3.3.2 Eq. (32) | Closed-loop output rate $\Omega_{\text{out}} = \Delta\phi_{\text{step}}/\mathrm{SF}_{\text{CL}}$ | `tier2_sysc_ams/src/digital_dsp_sc.cpp` |
| `EQ-24` | SPEC-004 §3.4 Eq. (33) | IEEE Std 952-2020 5-component AVAR equation | `tier3_analysis/dual_regime_avar.py` |
| `EQ-25` | SPEC-004 §3.4 Eq. (34) | RRW Wiener and 1st-order Gauss–Markov AR(1) models | `tier3_analysis/dual_regime_avar.py` |
| `EQ-26` | SPEC-004 §4.1 Eq. (35) | Inter-tier phase-to-rate conversion ($\text{rad/s} \leftrightarrow ^\circ/\text{h}$) | `tier3_analysis/dual_regime_avar.py` |
| `EQ-27` | SPEC-004 §4.2 Eq. (36) | Leakage gain matrix $\mathbf{K}$ via $100\text{ Hz}$ FFT injection | `tier3_analysis/extract_k_matrix.py` |
| `EQ-28` | SPEC-004 §4.3 Eq. (37) | Slow-scale $10\text{ h}$ / $100\text{ Hz}$ rate synthesis $\Omega_{\text{slow}}[i]$ | `tier3_analysis/dual_regime_avar.py` |
| `EQ-29` | SPEC-004 §4.3 Eq. (38) | IEEE Std 952 Overlapping Allan Variance $\sigma^2(T_m)$ | `tier3_analysis/dual_regime_avar.py` |
| `EQ-30` | SPEC-004 §4.3 Eq. (39) | Dual-regime overlap continuity $<5\%$ on $T_m \in [0.1, 5]\text{ s}$ | `tier3_analysis/dual_regime_avar.py` |
| `EQ-31` | SPEC-005 §2.1 | Official 6-state anti-periodic instantaneous & differential bias phases | `tier2_sysc_ams/include/ifog_math.hpp`, `digital_dsp_sc.cpp` |
| `EQ-32` | SPEC-005 §2.2 | 6-state Taylor expansion & optimal angle $\alpha^* = \pi/3$ ($-33.3\%$ $V_{\text{peak}}$) | `tests/formula_verification/test_formulas_spec005.py` |
| `EQ-33` | SPEC-005 §2.3 | 6-state 3-channel orthogonal demodulation ($e_\Omega^{(6)}, e_{V_\pi}^{(6)}, e_{\text{asym}}^{(6)}$) | `tier2_sysc_ams/src/digital_dsp_sc.cpp` |
| `EQ-34` | SPEC-005 §2.4 | 6-state Loop-1/2 gains, $-3\text{ dB}$ BW & anti-windup clamp | `tier2_sysc_ams/src/digital_dsp_sc.cpp`, `scenarios_time_domain.py` |
| `EQ-35` | SPEC-005 §4.1 | ADC sampling aperture jitter voltage variance & RSS ARW penalty | `tier2_sysc_ams/src/adc_dac_bridge.cpp`, `scenarios_engineering.py` |
| `EQ-36` | SPEC-005 §4.2 | 3-axis IMU shared-SLD droop & shared power-rail PSRR coupling | `tier2_sysc_ams/src/imu_3axis.cpp`, `analog_frontend_tdf.cpp` |
| `EQ-37` | SPEC-005 §4.3 | Vibration Rectification Error (VRE) quadratic law $K_{\text{VRE}} g_{\text{rms}}^2$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp`, `scenarios_engineering.py` |
| `EQ-38` | SPEC-005 §4.3 | Dynamic Faraday magnetic sensitivity $S_B$ & Mu-metal shielding $A_{\text{dB}}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp`, `scenarios_engineering.py` |
| `EQ-39` | SPEC-005 §4.4 | Real-time FPGA BIT/FDIR 5-fault classification & SEU soft-recovery | `tier2_sysc_ams/src/digital_dsp_sc.cpp`, `scenarios_engineering.py` |
| `EQ-40` | SPEC-005 §4.5 | Monte Carlo production yield, 95% Wilson CI & process capability $C_{pk}$ | `tier3_analysis/scenarios_engineering.py` |
| `EQ-41` | SPEC-005 §4.5 | $-40..+85^\circ\text{C}$ 2D thermal polynomial & 4-state EKF compensation | `tier3_analysis/scenarios_engineering.py` |

---

## 5. Release Tag Workflow (`x.y.z` SemVer Procedure — Rule 8)

Every release MUST follow this exact, gated sequence without skipping any step:

1. **Pre-Release Verification on `dev`:**
   - Ensure `git status` is clean on branch `dev` and synced with `origin/dev`.
   - Bump `pyproject.toml` version to `X.Y.Z`, update `docs/IFOG_VPROTO_ARCHITECTURE.{md,tex}`, `docs/IFOG_SIMULATION_SCENARIOS.{md,tex}`, `docs/RELEASE_NOTES.{md,tex}`, `docs/CHANGELOG.md`, `Containerfile`/`Dockerfile`/`compose.yaml`, `README.md`, and `skills/`, compile all 3 PDFs via `bash scripts/build_docs.sh`, and verify Rule 16 synchronization:
     ```bash
     python3 scripts/verify_doc_sync.py --expected-tag vX.Y.Z
     ```
   - Verify dual spec checksum locks: `sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256`.
   - Run full local verification suite:
     - C++ Release build + SystemC-AMS unit/system/gate tests (`./build/ifog_cpp_tests`)
     - C++ Coverage build -> `gcovr` confirms `100.0%` line & function coverage
     - Python unit, regression, visualization, doc-sync, runner, and **41-formula** tests -> `pytest --cov` confirms `100.0%` line coverage
     - Full real Gate 1–5 + 6 Time-Domain + 5 System Engineering real simulations (`pytest tests/system -v -s`) + auto-generated `report/` `.md` & `.html` verification
2. **Push `dev` & Open Pull Request (`dev` -> `main`):**
   - Push `dev` to `origin/dev`: `git push origin dev`
   - Wait for the GitHub Actions `CI` workflow on `dev` to finish with status `success`.
   - Open a PR from `dev` to `main` via `gh pr create --base main --head dev --title "Release vX.Y.Z: ..." --body "..."`.
   - Wait for ALL required CI checks on the PR (Branch Policy, Dual Spec Checksum, Rule 16 Doc-Sync, C++ Build & 100% Coverage, Python 100% Coverage, 41-Formula Verification, Full Real System Simulations, and Container Build & Live Sim) to pass (`success`).
3. **Merge PR into `main` (Preserving `dev`):**
   - Merge via `gh pr merge --merge` (**NEVER** use `--delete-branch`; `dev` MUST remain intact).
   - Pull `main` locally (`git checkout main && git pull origin main`) and wait for the `CI` workflow triggered on `main` to pass `success`.
4. **Create & Push Annotated SemVer Tag (`vX.Y.Z`):**
   - Tag the verified `main` commit:
     ```bash
     git tag -a vX.Y.Z -m "Release vX.Y.Z — Closed-Loop IFOG Virtual Prototype (IFOG-SIM-SPEC-005)"
     git push origin vX.Y.Z
     ```
   - Verify the GitHub Actions `Release` workflow triggered by `vX.Y.Z` enforces `--expected-tag vX.Y.Z` doc sync, re-runs all verification gates, packages all 14 release artifacts (`IFOG-SIM-SPEC-004.pdf`, `IFOG-SIM-SPEC-005.pdf`, `IFOG_VPROTO_ARCHITECTURE.{pdf,md,tex}`, `IFOG_SIMULATION_SCENARIOS.{pdf,md,tex}`, `RELEASE_NOTES.{pdf,md,tex}`, `formula_verification_matrix.{md,json}`, `cpp_coverage_summary.json`), and publishes the GitHub Release `vX.Y.Z`.
5. **Return to `dev` and Sync:**
   - Fast-forward `dev` to match `main` (`git checkout dev && git merge --ff-only main && git push origin dev`), ensuring `dev` and `main` stay clean and aligned for subsequent maintenance.
