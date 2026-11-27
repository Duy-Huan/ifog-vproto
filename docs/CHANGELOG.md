# Changelog — `ifog-vproto`

All notable changes to this project are documented in this file following [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and [Semantic Versioning](https://semver.org/spec/v2.0.0.html), and are strictly synchronized with `pyproject.toml`, `docs/`, and Git release tags per [`AGENT.md`](../AGENT.md) **Rule 16**.

## [4.1.0] - 2026-11-27

### Added
- **Group E Industrial TRL 7–8 / DO-254 Qualification Suite (`IND-01`..`IND-06`, `tier3_analysis/scenarios_industrial.py`, `viz/plot_industrial.py`):**
  - **`IND-01` Physical Lab Hardware Validation (`tier3_analysis/lab_validation.py`, `configs/lab_datasets/reference_ifog_lab/`):** Standardized 3-rig CSV ingestor (`static_avar_10h.csv`, `rate_table_deadband.csv` `[-2, +2] deg/s`, `thermal_chamber_ramp.csv` `-40..+85 degC`) with NASA-STD-7009A CAS-4 & ASME V&V 20 validation (`101.9% -> 4.51%`, max $|E|/u_{\text{val}} = 0.723 \le 1.0$) and CLI `--lab-dir`.
  - **`IND-02` Bit-True Fixed-Point FPGA DSP & Synthesizable SystemVerilog RTL (`rtl/ifog_dsp_6state.sv`):** Exact signed `Q(W-F).F` saturating/truncating quantizer (`quantize_fixed_signed` in `ifog_math.hpp`, `DigitalDSP_SC::quantize_reg`, `fxp_overflow_count` in `sim_summary.json`, `schema_v6.json`) verified across **all three DSP modes (2-State, 4-State, 6-State)**: `Q16.32` (48-bit) vs `Q8.24` (32-bit) vs `Float64`, achieving **0-LSB** RTL equivalence and `0` overflows (`31x–376x` precision improvement over 32-bit).
  - **`IND-03` 3D Cylindrical ANSYS/COMSOL FEM $\to$ `shupe_lut.bin` v2 (`tier1_offline/shupe_thermal.py`):** Added `load_fem_3d_csv`, `generate_asymmetric_3d_fem_csv`, `solve_tier1_shupe_3d_fem` (smooth linear RBF 3D projection of $T(r,\theta,z,t)$ & $\sigma_{\text{eff}}(r,\theta,z,t)$ onto discrete wound fiber turns), and `--fem-3d-csv` CLI option; fixed 3D axial traverse parity in `build_winding_map`, proving **`6.00x`** Octupole vs Quadrupole 3D drift suppression in real Tier 2 C++.
  - **`IND-04` MIL-STD-810H / DO-160G Broadband Random Vibration PSD & 2-DOF Resonance:** Piecewise log-log PSD (`20–2000 Hz`, `4.88 g_rms`) through 2-DOF elastomer isolator (`65 Hz`) + bobbin (`480 Hz, Q=12`) transmissibility + Miles' Equation check, proving **`4.82x`** coil $g_{\text{rms}}$ attenuation (`14.37 -> 2.98 g_rms`) and **`3.11x`** Tier 2 C++ VRE bias reduction.
  - **`IND-05` Multi-Instance Pure-C++17 Source-Code FMI 3.0.2 FMU (`build/ifog_core_multi.fmu`):** Created `fmi_wrapper/src/fmi3_multi_bridge.cpp`, `modelDescription_multi.xml.in` (`canBeInstantiatedOnlyOncePerProcess="false"`, 22 SI VRs, 75 C-API exports), `buildDescription.xml`, `package_fmu_multi.cmake`, and `ifog_fmi_multi_tests`; eliminates SystemC singleton lock, bundles portable C++17 `sources/` for Windows/Simulink & RT-Linux, passes FMPy validation with **0 XSD errors**, and executes **3 concurrent axes (6-State / 4-State / 2-State) in ONE OS process** (`< 0.15%` error, 0 cross-talk).
  - **`IND-06` 12-Corner Worst-Case PVT Matrix & 10-Yr SLD/MIOC Aging + Space 50 krad(Si) TID:** Full `-40/+25/+85 degC` $\times$ $\pm 5\%$ rail $\times$ $\pm 3\sigma$ process sweep + exponential SLD droop & power-law PM fiber RIA(TID) verified via real Tier 1 + Tier 2 C++ mission milestones.
- **Complete 2-State / 4-State / 6-State DSP Coverage:** Extended `DSP-01` (`dsp6_compare`), `DYN-01` (step), `DYN-02` (Bode FRF extended to `20 kHz`), `DYN-03` (broadband PSD), `IND-02` (FPGA fixed-point/RTL), and `IND-05` (3-axis Multi-FMU) + 300-DPI plotters (`viz/plot_scenarios.py`, `viz/plot_industrial.py`) to compare all 3 DSP architectures side by side.
- **11th Project Skill (`skills/ifog-industrial-trl7-do254/SKILL.md`):** Documented TRL 7–8 / DO-254 workflows and updated `skills/README.md`.

### Changed
- Expanded CLI runner to **38 modes** (`ind_lab_validation`..`ind_all` + included in `all_scenarios`), verification suite to **29 / 29 PASS** gates & scenarios, `viz/report_narratives.py` to **29 figure guides**, C++ coverage to **100.0% (`2,733/2,733` lines, `299/299` functions)**, Python coverage to **100.00% (`5,632/5,632` statements)**, and GitHub Release bundle to **23 verified assets** (adding `ifog_core_multi.fmu`).
- Synchronized `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `AGENT.md`, `README.md`, `docs/*.{md,tex,pdf}`, `docs/IFOG_VPROTO_PRESENTATION.{tex,pdf}`, `docs/IFOG_ARCHITECTURE_EXPLORER.html`, and `examples/full_all_scenarios/` to `v4.1.0` per Rule 16.

## [4.0.1] - 2026-11-26

### Added
- **32-Slide Academic LaTeX Beamer Presentation Deck (`docs/IFOG_VPROTO_PRESENTATION.{tex,pdf}`):**
  - Authored a 32-slide (`16:9`, `8pt`) academic presentation deck featuring 10 native TikZ/`pgfplots`/`circuitikz` diagrams, explicit IEEE 1666.1 SystemC-AMS LTF (`sca_ltf_nd`) + Hybrid Exact ZOH LTF & Lefèvre/IEEE 952 references, SI input parameter tables (`schema_v6.json`), explicit Tier 1 (`phys_params.json`, `shupe_lut.bin` v2) $\to$ Tier 2 $\to$ Tier 3 parameter handoff slides with mathematical separation/orthogonality proofs, 2-State / 4-State / 6-State DSP comparisons, and 11 enlarged single-figure experimental slides (`TD-01`, `DYN-01..04`, Gates 2/4/5/6, `PHY-01`, `CAL-01`).
- **Code-Only CI/CD Diff Filter (`tier3_analysis/ci_diff_filter.py`, `scripts/ci_diff_filter.py`, `tests/unit/test_ci_diff_filter.py`):**
  - Added stdlib-only fail-safe git diff filter (`detect-changes` job in `.github/workflows/ci.yml`) that runs CI/CD if and only if code/config/test/script/workflow/locked-`spec/` files change, skipping docs-only edits cleanly at **100.00% Python coverage (`4,770/4,770` stmts)**.

### Changed
- Updated `scripts/build_docs.sh` and `.github/workflows/release.yml` to compile, validate, and attach `IFOG_VPROTO_PRESENTATION.pdf` and `IFOG_VPROTO_PRESENTATION.tex` directly inside the GitHub Release bundle (**22 verified assets**).
- Synchronized `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `AGENT.md`, `README.md`, and all `docs/*.{md,tex,pdf}` to `v4.0.1` per Rule 16.

## [4.0.0] - 2026-11-26

### Added
- **Owner-Authorized Normative Specification Upgrade — `IFOG-SIM-SPEC-007` (v7.0):**
  - Authored checksum-locked [`spec/IFOG-SIM-SPEC-007.md`](../spec/IFOG-SIM-SPEC-007.md), [`spec/IFOG-SIM-SPEC-007.tex`](../spec/IFOG-SIM-SPEC-007.tex), 3-pass LuaLaTeX compiled [`spec/IFOG-SIM-SPEC-007.pdf`](../spec/IFOG-SIM-SPEC-007.pdf), and [`spec/IFOG-SIM-SPEC-007.sha256`](../spec/IFOG-SIM-SPEC-007.sha256) (preserving `SPEC-004`, `SPEC-005`, and `SPEC-006` 100% untouched under Quadruple Spec Lock), introducing 9 new canonical equations **`EQ-45`..`EQ-53`** (cross-referenced to draft `EQ-40`..`EQ-48`) targeting **`< 5%` hardware prediction accuracy**.
  - Added backward-compatible [`configs/schema_v6.json`](../configs/schema_v6.json) (supporting `"4.0"`, `"5.0"`, `"6.0"`) and reference predictive-physics configuration [`configs/baseline_1km_spec007.json`](../configs/baseline_1km_spec007.json).
- **Tier 1 High-Fidelity Coil Winding, Thermo-Mechanical Stress & Multi-Column LUT v2 (`tier1_offline/`):**
  - Added discrete turn-by-turn **Quadrupole / Octupole** winding coordinate mapping (`build_winding_map`, `EQ-45`), thermo-mechanical elasto-optic stress drift (`elasto_optic_stress_integral`, `EQ-46`), dynamic thermal scale-factor drift $K_{\text{opt}}(t)$ (`compute_dynamic_k_opt_rel`, `EQ-47`), dynamic $V_{\text{eff}}(t)/\Delta\phi_{\text{pol}}(t)/V_\pi(t)$ (`compute_dynamic_optical_params`, `EQ-48`), and 6-channel binary `shupe_lut.bin` v2 (`24 B` header + `56 B <7d` records, `EQ-49`) with seamless v1 fallback.
  - Extended `jones_spectral.py` with source coherence length $L_c$ and Rayleigh/facet back-reflection phase noise $\sigma_{\phi,\text{back}}$ (`EQ-52`).
- **Tier 2 Predictive Parasitic Physics & Live Tunable FMI 3.0 FMU (`tier2_sysc_ams/`, `fmi_wrapper/`):**
  - Implemented 2nd-order $\text{LiNbO}_3$ MIOC electro-acoustic step dynamics (`MiocDynamicsFilter` / `step_mioc_dynamics` before $K_{\text{delay}}$, `EQ-50`), capacitive + resistive PCB crosstalk $i_{\text{xtalk}}[k] = G_{\text{xtalk}}V_{\text{drv}}[k] + C_{\text{xtalk}}(V_{\text{drv}}[k]-V_{\text{drv}}[k-1])/\Delta t_{\text{fast}}$ (`EQ-51`), coherent Rayleigh/facet back-reflection phase noise (`EQ-52`), and $O(1)$ 6-channel LUT v2 interpolation (`ShupeLutRecordV2`, `static_assert == 56 B`, with automatic v1 fallback).
  - Expanded `fmi_wrapper/modelDescription.xml.in` and `fmi3_bridge.cpp` from 15 to **22 SI variables** by adding 7 live tunable parasitic parameters (`VR 15..21`: `C_xtalk_F`, `G_xtalk_S`, `c_pink_coeff`, `R_facet_dB`, `alpha_vpi_ppm_K`, `alpha_bobbin_ppm_K`, `delta_z_quad_m`) while preserving `0.00e+00 rad/s` bit-exact Gate 6 backward compatibility.
- **Tier 3 Anti-Double-Counting BI Stitching & Automated 3-Stage Bounded Inverse Calibration (`tier3_analysis/`, `viz/`):**
  - Added `DualRegimeStitcher` / `compute_residual_tier3_bi` enforcing quadrature subtraction $B_{\text{T3,mech}} = \sqrt{\max(0, B_{\text{total}}^2 - B_{\text{T2,meas}}^2)}$ (`EQ-52`).
  - Added `tier3_analysis/inverse_calibration.py` (`InverseCalibrator`, `EQ-53`): 3-stage bounded Trust-Region Reflective optimizer (Stage A Static AVAR, Stage B Slow Rate Ramp, Stage C Thermal Chamber) with Gauss–Newton covariance & 95% confidence intervals (`calibrated_params.json`).
  - Added `tier3_analysis/scenarios_spec007.py` (`PHY-01` & `CAL-01`), `viz/plot_spec007_calibration.py` (2 new 300-DPI figures), `tests/formula_verification/test_formulas_spec007.py` (`EQ-45`..`EQ-53`), `tests/unit/test_spec007_unit.py`, `tests/system/test_spec007_system.py`, and project skill `skills/ifog-spec007-physics-calibration/SKILL.md` (10 skills total).
- **Presentation-Grade Tier-by-Tier Mathematical Compendium (`EQ-01`..`EQ-53`):**
  - Added complete, cleanly formatted tier-by-tier equation compendia (Tier 1, Tier 2, FMI 3.0 Wrapper, Tier 3) directly into `docs/IFOG_VPROTO_ARCHITECTURE.{md,tex,pdf}`, `viz/report_narratives.py` (`TIER_FORMULA_COMPENDIUM`), `viz/export_report.py` (Section 12 in `report.md` & KaTeX `#sec-formulas` in `report.html`), and `viz/architecture_explorer.py` (`docs/IFOG_ARCHITECTURE_EXPLORER.html`).

### Changed
- Expanded CLI runner to **31 modes** (`spec007_physics`, `spec007_calibration`, `spec007_all` + included in `all_scenarios`), CI formula matrix to **53 / 53 equations (`EQ-01`..`EQ-53`)**, curated `examples/full_all_scenarios/` to **23 / 23 PASS** (`23` 300-DPI PNGs + `calibrated_params.json`), C++ coverage to **100.0%** (`2,329/2,329` lines, `211/211` functions), Python coverage to **100.00%** (`4,650/4,650` statements), and GitHub Release bundle to **20 verified assets**.
- Synchronized `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `AGENT.md`, `README.md`, `skills/`, `.github/workflows/{ci,release}.yml`, and all `docs/*.{md,tex,pdf}` to `v4.0.0` per Rule 16.

## [3.0.1] - 2026-11-26

### Added
- **Code-Audited Interactive HTML5 Mathematical Architecture Explorer (`viz/architecture_explorer.py`):**
  - Added standalone [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](IFOG_ARCHITECTURE_EXPLORER.html) (auto-generated by `scripts/build_docs.sh` and attached to GitHub Release `v3.0.1`) and automatic per-run `report/<run_id>/architecture_model.html` with live simulation KPI banner and 1-to-1 formula-to-source audit table (`EQ-01`..`EQ-44`).
  - Audited every mathematical block directly against the live `IFOG-SIM-SPEC-006` C++/Python source code (`jones_spectral.py`, `shupe_thermal.py`, `optical_envelope_tdf.cpp`, `analog_frontend_tdf.cpp`, `adc_dac_bridge.cpp`, `digital_dsp_sc.cpp`, `ifog_top_module.cpp`, `fmi3_bridge.cpp`, `dual_regime_avar.py`), supporting 4 interactive flow highlight modes (`All`, `Feedback & Deadband`, `Noise & AVAR`, `FMI 3.0 FMU`) and plain-language intuition for non-specialists.
- **Standardized Diagnostic Report Narratives (`viz/report_narratives.py`):**
  - Added a complete catalog of standardized 3-part explanations for all **21 official diagnostic figures**: (1) **Cơ sở Lý thuyết & Công thức (`EQ-xx`)**, (2) **Ý nghĩa Biểu đồ & Cách đọc cho Người không chuyên**, and (3) **Kết quả Thực tế & Điều được Chứng minh** dynamically populated from live measured metrics.
  - Added `tests/unit/test_architecture_and_narratives.py` achieving **100.00% Python line coverage** across both new visualization modules.

### Changed
- Upgraded `viz/export_report.py` so every generated `report.md` includes a non-specialist 3-Tier architecture overview, Gate 6 FMI 3.0 summary table, and standardized 3-part narrative blocks beneath all figures; upgraded `report.html` with KaTeX auto-rendering, sticky quick-navigation bar, embedded interactive `architecture_model.html` iframe, and standardized explanation cards under every Plotly plot and 300-DPI figure; added `Model Explorer` links in `report/index.{md,html}`.
- Updated `examples/run_example.sh` to sync `architecture_model.html` and regenerated BOTH curated examples (`examples/full_4gate_baseline/` & `examples/full_all_scenarios/`) with the standardized `v3.0.1` report format.
- Synchronized `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `README.md`, `skills/ifog-reporting-and-doc-sync/SKILL.md`, `.github/workflows/release.yml`, and all `docs/*.{md,tex,pdf}` to `v3.0.1` per Rule 16.

## [3.0.0] - 2026-11-26

### Added
- **Owner-Authorized Normative Spec Upgrade — `IFOG-SIM-SPEC-006` (v6.0):** Added checksum-locked `spec/IFOG-SIM-SPEC-006.{md,tex,pdf,sha256}` (while keeping `SPEC-004` and `SPEC-005` untouched and checksum-locked) formalizing FMI 3.0 Co-Simulation FMU architecture, 15-variable `modelDescription.xml` interface contract, 3 new equations (`EQ-42`–`EQ-44`), and **Gate 6 (FMI 3.0 Compliance & Black-Box Equivalence Gate)**.
- **Standalone FMI 3.0 Co-Simulation FMU Subsystem (`fmi_wrapper/`, `build/ifog_core.fmu`):**
  - Vendorized official BSD-2-Clause FMI 3.0 C headers (`fmi3Functions.h`, `fmi3FunctionTypes.h`, `fmi3PlatformTypes.h`) under `fmi_wrapper/include/fmi3/`.
  - Implemented reusable `IfogTopModule` (`SC_MODULE`) in `tier2_sysc_ams/{include,src}/ifog_top_module.{hpp,cpp}` wrapping the exact unmodified Accellera SystemC/SystemC-AMS closed-loop core with optional zero-overhead external ZOH drive, anti-aliased macro-step rate accumulator (`omega_out_avg`), residual $V_\pi$ phase error (`e_vpi_res`), and post-blanking BIT/FDIR status bitmask (`bit_status`).
  - Implemented full 75-symbol FMI 3.0 Co-Simulation C-API bridge (`fmi_wrapper/src/fmi3_bridge.cpp`), `fmi_wrapper/modelDescription.xml.in` (`fmiVersion="3.0"`, `canBeInstantiatedOnlyOncePerProcess="true"`), and cross-platform CMake packager (`fmi_wrapper/package_fmu.cmake`, target `package_fmu`) bundling `modelDescription.xml`, `binaries/x86_64-linux/ifog_core.so` (`-fPIC`), and Tier 1 `resources/{phys_params.json, shupe_lut.bin, baseline_cfg.json}` into `build/ifog_core.fmu`.
  - Added C++ FMI 3.0 unit test binary (`tier2_sysc_ams/src/fmi_unit_tests.cpp`) achieving **100.0% C++ line & function coverage** across both `tier2_sysc_ams/` and `fmi_wrapper/src/`.
- **FMPy Master Orchestrator & Gate 6 Verification (`tier3_analysis/fmi_master_runner.py`, `--mode fmi_gate`):**
  - Subprocess-isolated FMPy master orchestrator honoring `canBeInstantiatedOnlyOncePerProcess="true"`, executing official `fmpy.validation.validate_fmu` (0 errors), bit-exact (`0.00e+00 rad/s < 1e-12`) standalone vs FMU equivalence on 4-state & 6-state modes, Slow Rate Ramp deadband sweep (`97.42%` reduction, `99.59%` Bunny Ears SF reduction), and seamless FMU -> Tier 3 Dual-Regime 5-Region IEEE Std 952 Overlapping AVAR (`3.83% < 5%` overlap, all 5 WLS parameters $\le 10\%$).
  - Added 300-DPI 3-panel `plot_fmi_gate()` in `viz/plot_scenarios.py`, interactive Plotly Gate 6 chart + scorecard row in `viz/export_report.py`, `tests/formula_verification/test_formulas_spec006.py` (`EQ-42`..`EQ-44`), `tests/unit/test_fmi_master_unit.py`, `tests/system/test_fmi3_fmu_system.py`, and new project skill `skills/ifog-fmi3-cosim-fmu/SKILL.md` (9 skills total).

### Changed
- Expanded CI formula verification matrix to **44 / 44 equations (`EQ-01`..`EQ-44`)**, CLI runner to **28 modes** (`--mode fmi_gate`, `--fmu`), `all_scenarios` / `examples/full_all_scenarios/` to **21 official gates & scenarios** (**21 300-DPI PNGs**, **20 interactive Plotly HTML5 charts**), and updated `pyproject.toml`, `scripts/setup_env.sh`, `Containerfile`, `Dockerfile`, `compose.yaml`, `.github/workflows/{ci,release}.yml` (uploading `ifog_core.fmu` + `IFOG-SIM-SPEC-006.{pdf,md}` as release assets), `AGENT.md`, `README.md`, and all `docs/*.{md,tex,pdf}` to `v3.0.0`.

## [2.2.0] - 2026-11-26

### Added
- **Group C — Closed-Loop Dynamic Response, Broadband Output PSD & Internal Electro-Optic Probe Scenarios (`DYN-01`..`DYN-04`, `tier3_analysis/scenarios_dynamic_probe.py`):**
  - `DYN-01` (`--mode dyn_step_response`): Dedicated multi-amplitude closed-loop step response (`0->10 deg/s` linear & `0->100 deg/s` large-signal tactical, 4-State vs Official 6-State DSP, plus $K_{\text{tot},1} \in \{0.15, 0.25, 0.45\}$ gain sweep) capturing $t_d, t_r, t_{s,2\%}, t_{s,0.1\%}$, overshoot, tracking error convergence, and Sagnac $\Delta\phi_S(t)$ vs closed-loop feedback $\Delta\phi_{\text{step}}(t)$.
  - `DYN-02` (`--mode dyn_freq_response`): Full 15-point log-spaced (`20 Hz..10 kHz`) closed-loop Bode Magnitude [dB], unwrapped Phase [deg], and Group Delay [$\mu\text{s}$] sweep for both 4-State (`2,544 Hz`, $\tau_{g,0}=65.2\;\mu\text{s}$) and Official 6-State (`1,642 Hz`, $\tau_{g,0}=103.3\;\mu\text{s}$, $1.55\times$ ratio) overlaid with the exact half-frame-centered Z-domain analytical FRF.
  - `DYN-03` (`--mode dyn_output_psd`): Stationary broadband output angular-rate PSD [$(\text{deg/h})^2/\text{Hz}$], ASD [$\text{deg/h}/\sqrt{\text{Hz}}$], analytical `EQ-15`/`EQ-19` ARW reference (`0.000363 deg/rt-h`, `0.97x` ratio), low-frequency $1/f$ suppression (`+29.2 dB` 6-State vs 4-State), high-frequency closed-loop roll-off (`-13.5 dB`), and cumulative integrated RMS rate noise.
  - `DYN-04` (`--mode dyn_sine_electro_optic`): Real sinusoidal angular-rate excitation (`50 deg/s @ 250 Hz`, $\Delta\phi_{S,\max}=1.180\text{ rad}$, `THD=-67.5 dB`, `SFDR=43.6 dB`) probing all internal physical electro-optic nodes: $\Omega_{\text{in}}(t)$ vs $\Omega_{\text{out}}(t)$, Sagnac phase $\Delta\phi_S(t)$ vs feedback $\Delta\phi_{\text{fb}}(t)$ & residual $\Delta\phi_{\text{err}}(t)$, MIOC serrodyne feedback voltage $V_{\text{fb,MIOC}}(t)$ (`391` $2\pi$ resets) & total $V_{\text{MIOC}}(t)$, Photodiode optical power $P_{\text{PD}}(t)$ / photocurrent $I_{\text{PD}}(t)$ ($r(\Delta P_{\text{PD,demod}}, \Delta\phi_{\text{err}}) = 0.9960$), TIA voltage $V_{\text{TIA}}(t)$, and $60\;\mu\text{s}$ sub-$\tau$ ADC blanking zoom.
- **5 New Official CLI Modes & Unified Plotting / Reporting:** Added `dyn_step_response`, `dyn_freq_response`, `dyn_output_psd`, `dyn_sine_electro_optic`, `dyn_all` (27 total CLI modes), 4 new 300-DPI figures (`plot_dyn_scenarios()`, 20 total figures), Section 10 Group C Markdown tables, 4 new multi-panel interactive HTML5 Plotly charts (19 total interactive Plotly charts), unit/coverage tests (`tests/unit/test_dyn_probe_scenarios_unit.py`), and real system test (`test_all_4_dynamic_probe_scenarios_system`).

### Changed
- Upgraded `mode == "all_scenarios"`, `scripts/run_all_scenarios.sh`, and `examples/run_example.sh` to execute all **20 official gates & scenarios** (Gates 1–5 + 6 TD + 5 ENG + 4 DYN) and refreshed `examples/full_all_scenarios/` with complete real 20/20 PASS outputs (`v2.2.0`).
- Synchronized `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `scripts/container_run.sh`, `README.md`, `skills/`, and all `docs/*.{md,tex,pdf}` to `v2.2.0` per Rule 16.

## [2.1.0] - 2026-11-25

### Added
- **Complete Real All-Scenarios Curated Example (`examples/full_all_scenarios/`):** Executed and committed the complete real 16-gate/scenario verification bundle (`Gates 1–4` including 4×60 s Fast + 12×10 h Slow AVAR, `Gate 5` Official 6-State DSP, `TD-01`..`TD-06`, and `ENG-01`..`ENG-05` with `N=500` MC) including `README.md`, full `report.md`, interactive 15-chart Plotly `report.html`, all **16 300-DPI PNG plots**, `virtual_calibration_dataset.csv`, and all Gate/TD/ENG JSON telemetry.
- **15-Chart Interactive Plotly HTML5 & Full Scenario Markdown Reporting (`viz/export_report.py`):** Added modular `_build_plotly_sections()` rendering interactive Plotly charts for Core Gates (2, 3, 4, 5), Group A (`TD-01`..`TD-06`), and Group B (`ENG-01`..`ENG-05`), plus dedicated Markdown tables for Gate 5, Group A TD, Group B ENG, 5-fault BIT/FDIR, and MC Yield / Thermal Calibration.

### Changed
- Upgraded `examples/run_example.sh`, `scripts/run_all_scenarios.sh` (default `--mc-runs 500`), and `scripts/container_run.sh example` to execute ALL 16 official gates & scenarios by default and export `.md`, interactive `.html`, 16 PNG plots, CSV, and `report/index.{md,html}`.
- Added generated PNG plot count logging in `tier3_analysis/sim_runner_cli.py`, updated `skills/ifog-reporting-and-doc-sync/SKILL.md`, and synchronized `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `README.md`, and all `docs/*.{md,tex,pdf}` to `v2.1.0`.

## [2.0.0] - 2026-11-25

### Added
- **Owner-Authorized Spec Upgrade (`IFOG-SIM-SPEC-005` v5.0):** Added checksum-locked `spec/IFOG-SIM-SPEC-005.{tex,pdf,sha256}` (while keeping `spec/IFOG-SIM-SPEC-004.*` untouched and locked), `configs/schema_v5.json`, and `configs/baseline_1km_6state.json`.
- **Official 6-State Symmetric DSP (`EQ-31`–`EQ-34`, Gate 5):** Implemented anti-periodic 6-state modulation (`dsp.mode = "6state"`, $\alpha^* = \pi/3$, $-33.3\%$ peak MIOC voltage) with 3-channel orthogonal demodulation ($e_\Omega^{(6)}, e_{V_\pi}^{(6)}, e_{\text{asym}}^{(6)}$) and Loop-1 anti-windup clamping (`FLAG_ANTI_WINDUP`) in `DigitalDSP_SC`, achieving `+136.94 dB` (`7.03e6x`) RAM/crosstalk/$\gamma_{\text{nl}}$ rejection.
- **6 Official Time-Domain Scenarios (`TD-01`..`TD-06`):** Added 64-byte `DspTraceRecord` (`dsp_trace.bin`) and `tier3_analysis/scenarios_time_domain.py` (`td_blanking`, `td_step_sine`, `td_vpi_shock`, `td_high_rate`, `td_shupe_shock`, `td_limit_cycles`, `td_all`, `dsp6_compare`).
- **5 Official System Engineering & Production Scenarios (`ENG-01`..`ENG-05`, `EQ-35`–`EQ-41`):** Added concurrent 3-axis SystemC-AMS IMU (`tier2_sysc_ams/src/imu_3axis.cpp`, `--imu3axis`), ADC aperture jitter, VRE + dynamic Faraday physics, 5-mode fault injection + real-time FPGA BIT/FDIR (`DigitalDSP_SC::evaluate_frame_bit`), and `tier3_analysis/scenarios_engineering.py` (`eng_hw_sizing`, `eng_imu_3axis`, `eng_vre_faraday`, `eng_fault_bit`, `eng_mc_yield_cal`, `eng_all`).
- **Unified Official Flow, Reporting & Scenarios Documentation:** Added `scripts/run_all_scenarios.sh`, expanded `sim_runner_cli.py` to 22 CLI modes, added 300-DPI scenario plotters (`viz/plot_scenarios.py`), integrated SPEC-005 metrics/figures/CSV into `viz/export_report.py`, authored `docs/IFOG_SIMULATION_SCENARIOS.{md,tex,pdf}`, and added skill `skills/ifog-6state-and-scenarios/SKILL.md`.
- **41-Formula CI Verification (`EQ-01`..`EQ-41`):** Added `tests/formula_verification/test_formulas_spec005.py`, `tests/unit/test_spec005_scenarios_unit.py`, and `tests/system/test_spec005_scenarios_system.py`.

### Changed
- Bumped `pyproject.toml`, `Containerfile`, `Dockerfile`, `compose.yaml`, `scripts/container_run.sh`, `AGENT.md`, `README.md`, and all `docs/*.{md,tex,pdf}` to `v2.0.0`, expanding Rule 16 (`tier3_analysis/doc_sync.py`, `scripts/build_docs.sh`) to track all 3 compiled PDFs and Rule 7 to lock both `SPEC-004` and `SPEC-005`.
- Updated `.github/workflows/ci.yml` and `.github/workflows/release.yml` for dual spec locks, 8 project skills, 41-formula verification, and 14 release bundle assets.

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
