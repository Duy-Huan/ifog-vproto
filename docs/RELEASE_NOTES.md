# Release Notes — `ifog-vproto` (Closed-Loop IFOG Virtual Prototype)

## Document Control Metadata

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-VPROTO-REL-001` |
| **Current Version** | `v4.1.0` |
| **Status** | `RELEASED (TRL 7-8 / DO-254 Production Gate Verified)` |
| **Normative Specification** | [`spec/IFOG-SIM-SPEC-007.md`](../spec/IFOG-SIM-SPEC-007.md) & [`spec/IFOG-SIM-SPEC-007.pdf`](../spec/IFOG-SIM-SPEC-007.pdf) (v7.0); [`spec/IFOG-SIM-SPEC-006.md`](../spec/IFOG-SIM-SPEC-006.md) (v6.0); [`spec/IFOG-SIM-SPEC-005.tex`](../spec/IFOG-SIM-SPEC-005.tex) (v5.0); [`spec/IFOG-SIM-SPEC-004.tex`](../spec/IFOG-SIM-SPEC-004.tex) (v4.0) |
| **Architecture Reference** | [`docs/IFOG_VPROTO_ARCHITECTURE.md`](IFOG_VPROTO_ARCHITECTURE.md) / [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](IFOG_VPROTO_ARCHITECTURE.pdf) |
| **Interactive Model Explorer** | [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](IFOG_ARCHITECTURE_EXPLORER.html) |
| **Academic Presentation Deck** | [`docs/IFOG_VPROTO_PRESENTATION.pdf`](IFOG_VPROTO_PRESENTATION.pdf) / [`docs/IFOG_VPROTO_PRESENTATION.tex`](IFOG_VPROTO_PRESENTATION.tex) |
| **Scenarios Reference** | [`docs/IFOG_SIMULATION_SCENARIOS.md`](IFOG_SIMULATION_SCENARIOS.md) / [`docs/IFOG_SIMULATION_SCENARIOS.pdf`](IFOG_SIMULATION_SCENARIOS.pdf) |
| **LaTeX / PDF Companion** | [`docs/RELEASE_NOTES.tex`](RELEASE_NOTES.tex) / [`docs/RELEASE_NOTES.pdf`](RELEASE_NOTES.pdf) |

---

## Release `v4.1.0` (2026-11-27)

### Highlights & New Capabilities (TRL 7–8 / DO-254 Industrial Qualification Suite & Full 2/4/6-State DSP)
1. **`IND-01` Physical Hardware Lab Data Ingestion & NASA-STD-7009A CAS-4 / ASME V&V 20 Validation (`tier3_analysis/lab_validation.py`):**
   - Standardized 3-rig CSV ingestor (`configs/lab_datasets/reference_ifog_lab/`: 10 h granite-table AVAR, `[-2, +2] deg/s` slow rate table Deadband/Bunny Ears, `-40..+85 degC` thermal chamber) + `--lab-dir` CLI option. Cuts uncalibrated datasheet error from `101.9%` down to **`4.51%`** (`< 5%`), achieving ASME V&V 20 max $|E|/u_{\text{val}} = 0.723 \le 1.0$ (**CAS Level 4**) and real Tier 2 closed-loop error `0.0031%`.
2. **`IND-02` Bit-True Fixed-Point FPGA DSP & Synthesizable SystemVerilog RTL (`rtl/ifog_dsp_6state.sv`, 2 / 4 / 6-State):**
   - Added exact signed `Q(W-F).F` FPGA saturating/truncating register quantizer (`quantize_fixed_signed`, `DigitalDSP_SC::quantize_reg`, `fxp_overflow_count`, `schema_v6.json`) and synthesizable SystemVerilog-2012 RTL (`rtl/ifog_dsp_6state.sv`) supporting selectable **2-State, 4-State, and 6-State** modes. Proves **0-LSB** RTL equivalence, `0` overflows, and `31x–376x` higher precision for 48-bit `Q16.32` over 32-bit `Q8.24` across all 3 DSP modes.
3. **`IND-03` 3D Cylindrical ANSYS/COMSOL FEM $\to$ `shupe_lut.bin` v2 (`tier1_offline/shupe_thermal.py`):**
   - Added `load_fem_3d_csv`, `generate_asymmetric_3d_fem_csv`, `solve_tier1_shupe_3d_fem` (smooth linear RBF 3D projection onto discrete fiber turns), and `--fem-3d-csv` CLI option, proving **`6.00x`** Octupole vs Quadrupole 3D eccentric-hotspot suppression in real Tier 2 C++.
4. **`IND-04` MIL-STD-810H / DO-160G Broadband Random Vibration PSD & 2-DOF Resonance:**
   - Log-log piecewise PSD (`20–2000 Hz`, `4.88 g_rms`) through 2-DOF elastomer isolator (`65 Hz`) + bobbin (`480 Hz, Q=12`) transmissibility + Miles' Equation check, achieving **`4.82x`** coil $g_{\text{rms}}$ attenuation (`14.37 -> 2.98 g_rms`) and **`3.11x`** Tier 2 C++ VRE bias reduction.
5. **`IND-05` Multi-Instance Thread-Safe Pure-C++17 Source-Code FMI 3.0.2 FMU (`build/ifog_core_multi.fmu`):**
   - Eliminates the Accellera SystemC singleton (`canBeInstantiatedOnlyOncePerProcess="false"`), bundles portable `sources/buildDescription.xml` + `sources/fmi3_multi_bridge.cpp` for Windows/Simulink & RT-Linux, passes `fmpy.validation.validate_fmu` with **0 XSD errors**, and runs **3 concurrent axes (6-State / 4-State / 2-State) simultaneously in 1 OS process** (`< 0.15%` error, 0 cross-talk).
6. **`IND-06` 12-Corner Worst-Case PVT Matrix & 10-Yr SLD/MIOC Aging + Space 50 krad(Si) TID:**
   - Evaluates 12 corners (`-40/+25/+85 degC` $\times$ $\pm 5\%$ rail $\times$ $\pm 3\sigma$ process) + BOL/5-yr/10-yr/50 krad(Si) RIA degradation via real Tier 1 + Tier 2 C++ milestones (WC PVT ARW `0.00049 deg/rt-h`, EOL ARW `0.00052 deg/rt-h`).
7. **Complete 2-State / 4-State / 6-State DSP Coverage, 29/29 Suite, 100% Dual Coverage & 23 Release Assets:**
   - Extended `DSP-01`, `DYN-01`, `DYN-02` (up to `20 kHz`), `DYN-03`, `IND-02`, and `IND-05` across all three DSP modes (`2-State`, `4-State`, `6-State`); verified **100.0% C++ (`2,733/2,733` lines, `299/299` functions)** & **100.00% Python (`5,632/5,632` stmts)** coverage, **29/29 PASS** curated example, synchronized 38-slide presentation deck, and **23 verified release assets**.

---

## Release `v4.0.1` (2026-11-26)

### Highlights & New Capabilities
1. **32-Slide Academic LaTeX Beamer Presentation Deck (`docs/IFOG_VPROTO_PRESENTATION.{pdf,tex}` — Attached to Release Bundle):**
   - Authored a publication-grade 32-slide (`16:9`, `8pt`) Vietnamese academic presentation deck with **10 native TikZ / `pgfplots` / `circuitikz` vector diagrams**, explicitly referencing **Accellera SystemC-AMS LTF (`sca_ltf_nd`, IEEE Std 1666.1-2016 — M. Barnasconi *et al.*)** + Hybrid Exact ZOH LTF and **Lefèvre (3rd Ed.) / IEEE Std 952-2020**.
   - Includes a dedicated **SI Simulation Input Parameters** slide (`configs/baseline_1km_spec007.json`, `schema_v6.json`), explicit **Tier 1 (`phys_params.json`, `shupe_lut.bin` v2) $\to$ Tier 2** and **Tier 1 & 2 $\to$ Tier 3** parameter handoff slides with formal mathematical separation, spectral-preservation, variance-orthogonality, and passband-linearization proofs, complete **2-State / 4-State / 6-State DSP** models & 3-curve waveform comparison, and **11 enlarged single-figure experimental result slides** (`TD-01`, `DYN-01..04`, Gates 2/4/5/6, `PHY-01`, `CAL-01`).
   - Updated [`scripts/build_docs.sh`](../scripts/build_docs.sh) and [`.github/workflows/release.yml`](../.github/workflows/release.yml) so `IFOG_VPROTO_PRESENTATION.pdf` and `IFOG_VPROTO_PRESENTATION.tex` are automatically validated and shipped inside every GitHub Release bundle (**22 verified release assets**).
2. **Code-Only CI/CD Diff Filter (`tier3_analysis/ci_diff_filter.py`, `scripts/ci_diff_filter.py`):**
   - Added stdlib-only fail-safe git diff analyzer integrated as the `detect-changes` pre-flight job in [`.github/workflows/ci.yml`](../.github/workflows/ci.yml): triggers heavy CI/CD builds **if and only if** code/config/test/script/workflow/locked-`spec/` files change, skipping docs-only edits cleanly while preserving **100.00% Python line coverage** (`4,770 / 4,770` statements).

---

## Release `v4.0.0` (2026-11-26)

### Highlights & New Capabilities
1. **Owner-Authorized Specification Upgrade — `IFOG-SIM-SPEC-007` (v7.0, High-Fidelity Predictive Physics & Inverse Calibration):**
   - Authored checksum-locked [`spec/IFOG-SIM-SPEC-007.md`](../spec/IFOG-SIM-SPEC-007.md), [`spec/IFOG-SIM-SPEC-007.tex`](../spec/IFOG-SIM-SPEC-007.tex), 3-pass LuaLaTeX [`spec/IFOG-SIM-SPEC-007.pdf`](../spec/IFOG-SIM-SPEC-007.pdf), and [`spec/IFOG-SIM-SPEC-007.sha256`](../spec/IFOG-SIM-SPEC-007.sha256) (Quadruple Spec Lock preserving `SPEC-004/005/006` untouched) plus backward-compatible [`configs/schema_v6.json`](../configs/schema_v6.json) & [`configs/baseline_1km_spec007.json`](../configs/baseline_1km_spec007.json).
   - Expanded CI per-formula verification matrix from 44 to **53 / 53 independent equations (`EQ-01` .. `EQ-53`)**.
2. **Tier 1 Discrete Winding, Thermo-Mechanical Stress & Multi-Column `shupe_lut.bin` v2 (`EQ-45`..`EQ-49`):**
   - Implemented turn-by-turn **Quadrupole / Octupole** coil winding coordinate mapping (`build_winding_map`, achieving **`-47.69%`** octupole Shupe reduction in `PHY-01`), thermo-mechanical elasto-optic stress-optic drift, dynamic thermal scale-factor drift $K_{\text{opt}}(t)$ (`85.6 ppm`), dynamic $V_{\text{eff}}(t)/\Delta\phi_{\text{pol}}(t)/V_\pi(t)$, and 6-channel binary `shupe_lut.bin` v2 (`24 B` header + `56 B <7d` records) with zero-error roundtrip and automatic v1 fallback.
3. **Tier 2 Parasitic Physics & Live Tunable FMI 3.0 FMU (`EQ-50`..`EQ-52`, `VR 15..21`):**
   - Implemented 2nd-order $\text{LiNbO}_3$ MIOC electro-acoustic step dynamics before $K_{\text{delay}}$, capacitive + resistive PCB crosstalk $C_{\text{xtalk}}\,dV/dt + G_{\text{xtalk}}V$ (exact reduction to `SPEC-004` when $C_{\text{xtalk}}=0$), coherent Rayleigh/facet back-reflection phase noise, and $O(1)$ LUT v2 interpolation.
   - Added **7 live tunable FMI 3.0 parasitic parameters (`VR 15..21`)** to `build/ifog_core.fmu` (22 SI variables total, 0 `fmpy.validation.validate_fmu` errors) while keeping `0.00e+00 rad/s` bit-exact Gate 6 equivalence with `ifog_sim`.
4. **Tier 3 Anti-Double-Counting BI Stitching & Automated 3-Stage Bounded Inverse Calibration (`EQ-52`, `EQ-53`, `CAL-01`):**
   - Added `DualRegimeStitcher` quadrature BI subtraction ($B_{\text{T3,mech}} = \sqrt{\max(0, B_{\text{total}}^2 - B_{\text{T2,meas}}^2)}$) and 3-stage bounded `InverseCalibrator` (`tier3_analysis/inverse_calibration.py`) with Gauss–Newton 95% CI (`calibrated_params.json`).
   - Verified `CAL-01` cuts uncalibrated prediction error (`40–103%`) down to **`< 1%`** (`AVAR 0.81%`, `Deadband 0.91%`, `Thermal Bias 0.29%`, `Scale Factor 0.04%`), recovering all 10 hidden parasitic parameters within **`<= 2.18%`** (`< 5%` target).
5. **Presentation-Grade Tier-by-Tier Mathematical Documentation, 23/23 Curated Example & 100.0% Dual Coverage:**
   - Added complete tier-by-tier mathematical formulations (`EQ-01`..`EQ-53`) in `docs/IFOG_VPROTO_ARCHITECTURE.{md,tex,pdf}`, `docs/IFOG_ARCHITECTURE_EXPLORER.html`, and every generated `report.md` / KaTeX `report.html`.
   - Re-ran `./examples/run_example.sh --sync-example` (`23 / 23` PASS, **23 300-DPI PNGs**, `calibrated_params.json`), verified **100.0% C++** (`2,329/2,329` lines, `211/211` functions) and **100.00% Python** (`4,650/4,650` statements) coverage, added 10th skill `skills/ifog-spec007-physics-calibration/`, and shipped **20 verified release assets**.

---

## Release `v3.0.1` (2026-11-26)

### Highlights & New Capabilities
1. **Code-Audited Interactive HTML5 Mathematical Architecture Explorer (`viz/architecture_explorer.py`):**
   - Authored standalone [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](IFOG_ARCHITECTURE_EXPLORER.html) and automatic per-run `report/<run_id>/architecture_model.html` inspired by the SPEC-004 interactive architecture flow and **audited 1-to-1 against live `IFOG-SIM-SPEC-006` C++/Python source code** (`EQ-01`..`EQ-44`).
   - Reconciled every physical formula and signal path (exact Spectral-Sliced Jones reciprocity in `jones_spectral.py`, 1D Crank–Nicolson/FEM Shupe integral without outer $n_{\text{eff}}$ in `shupe_thermal.py`, TIA inverting-node crosstalk injection in `analog_frontend_tdf.cpp`, `set_delay(1)` loop break in `adc_dac_bridge.cpp`, Official 6-State Symmetric DSP & 5-fault BIT/FDIR in `digital_dsp_sc.cpp`, 15-variable FMI 3.0 wrapper in `fmi3_bridge.cpp`, and Dual-Regime AVAR stitching in `dual_regime_avar.py`), complete with 4 interactive path filters, live parameter strip, and formula-to-source audit table.
2. **Standardized Professional `.md` & `.html` Diagnostic Reports with Full Theory & Non-Specialist Explanations (`viz/report_narratives.py`, `viz/export_report.py`):**
   - Added [`viz/report_narratives.py`](../viz/report_narratives.py) providing standardized 3-part commentary for all **21 official diagnostic figures**: (1) **Cơ sở Lý thuyết & Công thức (`EQ-xx`)**, (2) **Ý nghĩa Biểu đồ & Cách đọc cho Người không chuyên**, and (3) **Kết quả Thực tế & Điều được Chứng minh** dynamically populated from measured run metrics.
   - Upgraded `report.md` (Section 0 3-Tier overview, Gate 6 FMI 3.0 table, and annotated Section 11 figures) and `report.html` (KaTeX auto-rendering, sticky quick-nav bar, embedded interactive `architecture_model.html` panel, annotated Plotly cards & 300-DPI gallery), plus `Model Explorer` links in `report/index.{md,html}`.
3. **Regenerated Both Curated Examples & 100.0% Dual Coverage:**
   - Re-ran both `./examples/run_example.sh --4gate-only --sync-example` ([`examples/full_4gate_baseline/`](../examples/full_4gate_baseline/README.md), `4 / 4` PASS) and `./examples/run_example.sh --sync-example` ([`examples/full_all_scenarios/`](../examples/full_all_scenarios/README.md), `21 / 21` PASS) with the new `v3.0.1` standardized reports and `architecture_model.html`.
   - Maintained **100.0% C++** (`gcovr`, `2,102/2,102` lines) & **100.00% Python** (`pytest-cov`, including `viz/architecture_explorer.py` and `viz/report_narratives.py`), **44/44 verified formulas**, **10/10 real system tests**, and attached `IFOG_ARCHITECTURE_EXPLORER.html` to GitHub Release `v3.0.1` (18 release assets).

---

## Release `v3.0.0` (2026-11-26)

### Highlights & New Capabilities
1. **Owner-Authorized Specification Upgrade — `IFOG-SIM-SPEC-006` (v6.0):**
   - Authored checksum-locked [`spec/IFOG-SIM-SPEC-006.md`](../spec/IFOG-SIM-SPEC-006.md), [`spec/IFOG-SIM-SPEC-006.tex`](../spec/IFOG-SIM-SPEC-006.tex), 3-pass LuaLaTeX compiled [`spec/IFOG-SIM-SPEC-006.pdf`](../spec/IFOG-SIM-SPEC-006.pdf), and [`spec/IFOG-SIM-SPEC-006.sha256`](../spec/IFOG-SIM-SPEC-006.sha256) while preserving `SPEC-004` and `SPEC-005` 100% untouched & SHA-256 locked.
   - Expanded CI formula verification matrix from 41 to **44 / 44 independent equations (`EQ-01` .. `EQ-44`)** covering multi-rate ZOH alignment & anti-aliased macro-step averaging (`EQ-42`), residual $V_\pi$ phase error & 6-bit BIT/FDIR status bitmask (`EQ-43`), and black-box FMU vs standalone `< 1e-12 rad/s` equivalence (`EQ-44`).
2. **Standalone Tool-Agnostic FMI 3.0 Co-Simulation FMU (`build/ifog_core.fmu`):**
   - Wrapped the exact unmodified Tier 2 Accellera SystemC/SystemC-AMS core (`IfogTopModule`, compiled `-fPIC`) with vendorized official BSD-2-Clause FMI 3.0 C headers (`fmi_wrapper/include/fmi3/`), full 75-symbol FMI 3.0 C-API bridge (`fmi_wrapper/src/fmi3_bridge.cpp`), 15-variable `modelDescription.xml.in` (`fmiVersion="3.0"`, `canBeInstantiatedOnlyOncePerProcess="true"`), and CMake `package_fmu` target bundling `modelDescription.xml`, `binaries/x86_64-linux/ifog_core.so`, and Tier 1 `resources/{phys_params.json, shupe_lut.bin, baseline_cfg.json}`.
   - Shipped `ifog_core.fmu` directly as a verified GitHub Release asset alongside all specs and docs.
3. **FMPy Master Orchestrator & Gate 6 Verification (`tier3_analysis/fmi_master_runner.py`, `--mode fmi_gate`):**
   - Subprocess-isolated FMPy master orchestrator honoring `canBeInstantiatedOnlyOncePerProcess="true"`:
     - **Gate 6A (FMI 3.0 Compliance):** `fmpy.validation.validate_fmu("build/ifog_core.fmu")` passes with **0 errors, 0 warnings**.
     - **Gate 6B (Bit-Exact Equivalence):** Standalone `build/ifog_sim` vs `build/ifog_core.fmu` (4-state & 6-state, noisy `seed=42004`, `step_size=1e-3`) matches with **`0.00e+00 rad/s` (`< 1e-12`)** discrepancy and clean `bit_status == 0`.
     - **Gate 6C (Slow Rate Ramp Deadband Sweep):** `fmpy.simulate_fmu(..., step_size=1e-3)` across `0 deg/h` achieves **`97.42%`** Deadband reduction and **`99.59%`** Bunny Ears scale-factor reduction (`enable_dither=False` vs `True`).
     - **Gate 6D (FMU -> Tier 3 Dual-Regime 5-Region AVAR):** `omega_out_avg` stream feeds directly into `run_dual_regime_avar()` achieving **`3.83%`** (`< 5%`) overlap continuity and all 5 IEEE Std 952 parameters ($Q, N, B, K, R$) within `<= 8.92%` (`<= 10%`).
4. **21-Gate/Scenario Official Flow, 100.0% Dual Coverage & Governance Sync (`v3.0.0`):**
   - Expanded CLI to **28 modes**, `viz/plot_scenarios.py` to **21 300-DPI PNGs** (`fmi_fmu_gate.png`), `viz/export_report.py` to **20 interactive Plotly HTML5 charts**, and refreshed `examples/full_all_scenarios/` (`21 / 21` PASS).
   - Achieved **100.0% C++ line & function coverage** (`gcovr`) across BOTH `tier2_sysc_ams/` AND `fmi_wrapper/src/` (`2,102/2,102` lines, `200/200` functions), **100.0% Python line coverage** (`pytest-cov` including `fmi_master_runner.py`), **44/44 verified formulas**, **10 real system tests**, added project skill [`skills/ifog-fmi3-cosim-fmu/SKILL.md`](../skills/ifog-fmi3-cosim-fmu/SKILL.md) (9 skills), and verified Rule 16 doc sync for `v3.0.0`.

---

## Release `v2.2.0` (2026-11-26)

### Highlights & New Capabilities
1. **Group C — Dedicated Closed-Loop Dynamic Characterization, Broadband Output PSD & Internal Electro-Optic Probe (`DYN-01`..`DYN-04`):**
   - **`DYN-01` (`--mode dyn_step_response`):** Multi-amplitude closed-loop step characterization ($0\to 10^\circ/\text{s}$ linear & $0\to 100^\circ/\text{s}$ large-signal tactical, 4-State vs Official 6-State DSP, plus $K_{\text{tot},1}\in\{0.15, 0.25, 0.45\}$ gain sweep) reporting $t_d, t_r, t_{s,2\%}, t_{s,0.1\%}$, overshoot (`0.00%`), tracking error convergence, and Sagnac $\Delta\phi_S(t)$ vs feedback $\Delta\phi_{\text{step}}(t)$.
   - **`DYN-02` (`--mode dyn_freq_response`):** Full 15-point log-spaced (`20 Hz..10 kHz`) closed-loop Bode Magnitude [dB], unwrapped Phase [deg], and Group Delay [$\mu\text{s}$] comparing 4-State (`2,544 Hz`, $\tau_{g,0}=65.2\;\mu\text{s}$) and Official 6-State (`1,642 Hz`, $\tau_{g,0}=103.3\;\mu\text{s}$, $1.55\times$ ratio) against the exact half-frame-centered Z-domain analytical FRF.
   - **`DYN-03` (`--mode dyn_output_psd`):** Stationary broadband output angular-rate PSD [$(\text{deg/h})^2/\text{Hz}$], ASD [$\text{deg/h}/\sqrt{\text{Hz}}$], and cumulative integrated RMS noise (`3 Hz..25 kHz`), validating the white-noise ARW floor (`0.000352` vs analytical `EQ-15` `0.000363 deg/rt-h`), high-frequency closed-loop roll-off (`-13.5 dB`), and Official 6-State low-frequency $1/f$ crosstalk suppression (`+29.2 dB` vs 4-State).
   - **`DYN-04` (`--mode dyn_sine_electro_optic`):** Real sinusoidal angular-rate excitation (`50 deg/s @ 250 Hz`, $\Delta\phi_{S,\max}=1.1800\text{ rad}$, `THD=-67.5 dB`, `SFDR=43.6 dB`) exposing every internal physical node: $\Omega_{\text{in}}(t)$ vs $\Omega_{\text{out}}(t)$, Sagnac phase $\Delta\phi_S(t)$ vs feedback $\Delta\phi_{\text{fb}}(t)$ & quadrature residual $\Delta\phi_{\text{err}}(t)$, MIOC serrodyne voltage $V_{\text{fb,MIOC}}(t)$ (`391` $2\pi$ resets) & total $V_{\text{MIOC}}(t)$, Photodiode optical power $P_{\text{PD}}(t)$ / photocurrent $I_{\text{PD}}(t)$ & demodulated $\Delta P_{\text{PD}}(t)$ ($r = 0.9960$), TIA voltage $V_{\text{TIA}}(t)$, and $60\;\mu\text{s}$ sub-$\tau$ ADC blanking zoom.
2. **20-Scenario Default Official Flow, 19-Chart Interactive HTML5 & Refreshed Curated Example (`examples/full_all_scenarios/`):**
   - Expanded `sim_runner_cli.py` to **27 CLI modes** (`dyn_step_response`, `dyn_freq_response`, `dyn_output_psd`, `dyn_sine_electro_optic`, `dyn_all`), `viz/plot_scenarios.py` to **20 300-DPI PNG figures**, and `viz/export_report.py` to **Section 10 Group C Markdown tables** + **19 interactive multi-panel Plotly HTML5 charts**.
   - Re-ran `./examples/run_example.sh --sync-example` end-to-end (`20 / 20` PASS, zero mocks / zero smoke tests) and committed the refreshed bundle in [`examples/full_all_scenarios/`](../examples/full_all_scenarios/README.md).
3. **100.0% Dual Coverage, 9 Real System Tests & Rule 16 Sync:**
   - Maintained **100.0% C++** (`gcovr`) and **100.0% Python** (`pytest-cov`) coverage, **41/41 verified formulas**, **9/9 real system tests** (including `test_all_4_dynamic_probe_scenarios_system`), and full Rule 16 version–document synchronization (`v2.2.0`).

---

## Release `v2.1.0` (2026-11-25)

### Highlights & New Capabilities
1. **Complete Real All-Scenarios Curated Example Committed to Repo (`examples/full_all_scenarios/`):**
   - Executed end-to-end via `./examples/run_example.sh --sync-example` (zero mocks, zero smoke tests): **Gates 1–4** (including $4\times 60\text{ s}$ Fast-Scale SystemC-AMS + $12\times 10\text{ h}$ / $3.6\times 10^6$-sample Slow-Scale AVAR) + **Gate 5 Official 6-State Symmetric DSP** + **6 Time-Domain (`TD-01`..`TD-06`)** + **5 System Engineering & Production (`ENG-01`..`ENG-05`, `MC=500`)** = **`16 / 16` PASS**.
   - Committed complete deliverables for direct visual & technical review: [`README.md`](../examples/full_all_scenarios/README.md), full [`report.md`](../examples/full_all_scenarios/report.md), interactive [`report.html`](../examples/full_all_scenarios/report.html) (**15 interactive Plotly HTML5 charts** + 16-plot gallery), all **16 300-DPI PNG figures** under `figures/`, [`virtual_calibration_dataset.csv`](../examples/full_all_scenarios/virtual_calibration_dataset.csv), and all Gate/TD/ENG JSON telemetry.
2. **Upgraded Full-Suite Interactive HTML5 & Markdown Reporting (`viz/export_report.py`):**
   - Expanded `_build_interactive_html()` with modular `_build_plotly_sections()` rendering **15 interactive multi-panel Plotly HTML5 charts** covering Gate 2, Gate 3, Gate 4, Gate 5, `TD-01`..`TD-06`, and `ENG-01`..`ENG-05` (with single-load CDN for fast rendering) alongside the 16-figure 300-DPI PNG gallery.
   - Expanded `_build_markdown_report()` with dedicated Gate 5 6-State DSP comparison, Group A Time-Domain (`TD-01`..`TD-06`), Group B System Engineering (`ENG-01`..`ENG-05`), ENG-04 5-fault FPGA BIT/FDIR, and ENG-05 Monte Carlo Yield / Virtual Thermal Calibration tables.
3. **One-Command All-Scenarios Execution Across All Scripts:**
   - Upgraded [`examples/run_example.sh`](../examples/run_example.sh), [`scripts/run_all_scenarios.sh`](../scripts/run_all_scenarios.sh) (default `--mc-runs 500`), and [`scripts/container_run.sh`](../scripts/container_run.sh) (`example` subcommand) so running any example or batch script executes **ALL 16 official gates & scenarios** and automatically generates `report.md`, interactive `report.html`, all 16 300-DPI PNG plots, CSV calibration data, and `report/index.{md,html}`.
4. **Rule 6, Rule 14 & Rule 16 Verification:**
   - Maintained **100.0% C++ (`1,546/1,546` lines, `109/109` functions)** & **100.0% Python line coverage**, **41/41 verified formulas**, updated [`skills/ifog-reporting-and-doc-sync/SKILL.md`](../skills/ifog-reporting-and-doc-sync/SKILL.md), and synchronized all `.md`/`.tex`/`.pdf`, `DOCS_BUILD.sha256`, `Containerfile`/`Dockerfile`/`compose.yaml`, and `README.md` to `v2.1.0`.

---

## Release `v2.0.0` (2026-11-25)

### Highlights & New Capabilities
1. **Owner-Authorized Normative Spec Upgrade — `IFOG-SIM-SPEC-005` (v5.0):**
   - Added checksum-locked [`spec/IFOG-SIM-SPEC-005.tex`](../spec/IFOG-SIM-SPEC-005.tex), 3-pass LuaLaTeX compiled [`spec/IFOG-SIM-SPEC-005.pdf`](../spec/IFOG-SIM-SPEC-005.pdf), and [`spec/IFOG-SIM-SPEC-005.sha256`](../spec/IFOG-SIM-SPEC-005.sha256) while keeping `IFOG-SIM-SPEC-004` byte-identical and checksum-locked as archival baseline.
   - Added backward-compatible [`configs/schema_v5.json`](../configs/schema_v5.json) (supporting `"4.0"` & `"5.0"`) and official 6-state reference config [`configs/baseline_1km_6state.json`](../configs/baseline_1km_6state.json).
   - Expanded per-formula CI traceability from 30 to **41 / 41 independent formula tests (`EQ-01` .. `EQ-41`)**.
2. **Official 6-State Symmetric DSP Modulation & Demodulation (`EQ-31`–`EQ-34`, Gate 5):**
   - Implemented anti-periodic 6-state symmetric modulation (`dsp.mode = "6state"`, optimal angle $\alpha^* = \pi/3$) in Tier 2 C++ `DigitalDSP_SC` with 3-channel orthogonal demodulation ($e_\Omega^{(6)}, e_{V_\pi}^{(6)}, e_{\text{asym}}^{(6)}$) and Loop-1 anti-windup clamping (`FLAG_ANTI_WINDUP`).
   - Verified **$-33.3\%$ peak MIOC drive voltage** ($0.667\,V_\pi$ vs $V_\pi$), static phase error `1.28e-16 rad`, $\epsilon_{V_\pi,\text{eff}} = 1.31\times 10^{-11}$, and **`+136.94 dB` (`7.03 × 10⁶×`) RAM/crosstalk/$\gamma_{\text{nl}}$ bias rejection** (`354.56 deg/h` $\to$ `5.04e-5 deg/h`) alongside online asymmetry monitoring (`e_asym_rms = 169.87 counts`).
3. **Group A — 6 Official Time-Domain Scenarios (`TD-01`..`TD-06`, `--mode td_all` or individual CLI):**
   - Added 64-byte cycle-accurate `DspTraceRecord` logger (`dsp_trace.bin`) and `tier3_analysis/scenarios_time_domain.py`:
     - `td_blanking` (`TD-01`): TIA $t_s(0.1\%) = 174.1\text{ ns}$, optimal clean blanking $k_{\text{start}}^* = 5$, ARW $\times 1.155$.
     - `td_step_sine` (`TD-02`): Step $0 \to 100^\circ/\text{s}$ ($t_r = 0.22\text{ ms}$, overshoot `0.008%`), measured $-3\text{ dB}$ BW = **`2,540 Hz`** vs analytical **`2,354 Hz`**.
     - `td_vpi_shock` (`TD-03`): $+5\%$ $V_\pi$ thermal shock converges to `< 1.7e-11` in `4.2 ms` (4s) / `6.3 ms` (6s) with **2× lower Loop-1 disturbance** in 6-state (`0.269` vs `0.535 deg/s`).
     - `td_high_rate` (`TD-04`): Smooth $300/500/700^\circ/\text{s}$ serrodyne tracking (`0.00028%` RMS err @ `700 deg/s`, `7,184` wraps @ `179.6 kHz`, zero slips) + exact anti-windup clamp (`200` events).
     - `td_shupe_shock` (`TD-05`): Real-time Shupe shock peak `1,483.61 deg/h` (`r = 0.99998`); extrapolative filter suppresses **`99.74%`**.
     - `td_limit_cycles` (`TD-06`): 12-bit quantization deadband unlocked by reflected PRBS dither (`3 -> 1,595` unique DAC codes).
4. **Group B — 5 Official System Engineering & Production Scenarios (`ENG-01`..`ENG-05`, `--mode eng_all` or individual CLI):**
   - Added concurrent 3-axis SystemC-AMS IMU engine (`tier2_sysc_ams/src/imu_3axis.cpp`, `./build/ifog_sim --imu3axis`), ADC aperture jitter, vibration/Faraday physics, 5-mode fault injection + real-time FPGA BIT/FDIR state machine, and `tier3_analysis/scenarios_engineering.py`:
     - `eng_hw_sizing` (`ENG-01`, `EQ-35`): Minimum passing ENOB = **`12-bit`**; aperture jitter elevates ARW cleanly (`+2,216%` @ `10 ns`); Pareto TIA/SLD ARW = `1.412e-4 deg/rt-h`.
     - `eng_imu_3axis` (`ENG-02`, `EQ-36`): Concurrent 3-axis SystemC-AMS IMU (Axis X @ `500 deg/s`): shared-rail droop `92.4 mV`; stationary Axis-Y crosstalk reduced from **`40.63 deg/h`** (4-state) to **`0.106 deg/h`** (6-state — **`+51.6 dB` rejection**).
     - `eng_vre_faraday` (`ENG-03`, `EQ-37`, `EQ-38`): Pure quadratic $G_2 V^2$ VRE `-0.0189 deg/h/g²` (**$R^2 = 0.9998$**); Faraday sensitivity `0.18305 deg/h/G` (`< 10⁻⁸%` vs theory), requiring **`25.25 dB` Mu-metal shielding**.
     - `eng_fault_bit` (`ENG-04`, `EQ-39`): All `5/5` injected faults (`sld_drop_50pct`, `fiber_break`, `mioc_electrode_open`, `adc_saturation`, `dsp_seu_bitflip`) detected in **`<= 30.0 us`** with automatic SEU FDIR soft-rollback recovery (`True`).
     - `eng_mc_yield_cal` (`ENG-05`, `EQ-40`, `EQ-41`): Parallel Monte Carlo Yield (`N = 500`): **`97.2%`** (`486/500`, 95% Wilson CI `[95.36%, 98.32%]`, $C_{pk} = 0.604$); `-40..+85°C` Virtual Thermal Calibration CSV (`21` pts) with 2D polynomial (`99.98%` reduction) and 4-state EKF (`99.95%` reduction).
5. **Unified Official Flow, Scenarios Documentation & Governance Sync (`v2.0.0`):**
   - Added [`scripts/run_all_scenarios.sh`](../scripts/run_all_scenarios.sh), expanded `sim_runner_cli.py` to 22 CLI modes (`--dsp-mode`, `--mc-runs`), added 300-DPI scenario plotters (`viz/plot_scenarios.py`), and integrated all SPEC-005 metrics/figures/CSVs into `viz/export_report.py`.
   - Authored [`docs/IFOG_SIMULATION_SCENARIOS.md`](IFOG_SIMULATION_SCENARIOS.md) / [`.tex`](IFOG_SIMULATION_SCENARIOS.tex) / [`.pdf`](IFOG_SIMULATION_SCENARIOS.pdf), added project skill [`skills/ifog-6state-and-scenarios/SKILL.md`](../skills/ifog-6state-and-scenarios/SKILL.md) (8 skills total), and enforced **100.0% C++ (`1,546/1,546` lines, `109/109` functions)** & **100.0% Python (`2,631/2,631` statements)** coverage.

---

## Release `v1.2.0` (2026-11-25)

### Highlights & New Capabilities
1. **Docker & Podman Portable Container Suite (`Containerfile`, `Dockerfile`, `.dockerignore`, `compose.yaml`, `scripts/container_run.sh`):**
   - Ready-to-run OCI image built on `ubuntu:24.04` pre-installing Accellera SystemC `2.3.4`, SystemC-AMS PoC `2.3.4`, `nlohmann/json` `v3.11.3`, isolated Python 3.12 virtual environment (`/opt/ifog-env/venv`), and pre-compiled Tier 2 Release (`-O3`) `build/ifog_sim`.
   - Unified [`scripts/container_run.sh`](../scripts/container_run.sh) auto-detects `podman` (with rootless SELinux `:Z` and `--userns=keep-id`) or `docker` for one-command `build`, `shell`, `sim`, `example`, `test`, and `verify` workflows.
   - Verified automatically on GitHub Actions via a dedicated `container-build-and-verify` CI job.
2. **Distro-Independent Linux Git-Source Setup Toolchain (`scripts/setup_env.sh`, `scripts/install_systemc.sh`, `scripts/install_systemc_ams.sh`, `scripts/env.sh`):**
   - Pulls and builds Accellera SystemC `2.3.4` (C++17), SystemC-AMS PoC `2.3.4`, `nlohmann/json` `v3.11.3`, and an isolated Python virtual environment on **any Linux distribution** (Ubuntu/Debian, Fedora/RHEL/Rocky, Arch, or rootless HPC clusters) without requiring Ubuntu-specific `apt` SystemC packages.
   - Multi-distro CMake library discovery (`lib`, `lib64`, `lib-linux64`, x86\_64 & ARM64) in [`tier2_sysc_ams/CMakeLists.txt`](../tier2_sysc_ams/CMakeLists.txt) and automatic `source scripts/env.sh` activation in `scripts/run_sim.sh`.
3. **Complete Curated Real 4-Gate Baseline Example Committed to Repo (`examples/full_4gate_baseline/`, `examples/run_example.sh`):**
   - Full genuine execution of all 4 normative acceptance gates (`--mode full`) committed with `README.md`, `report.md`, interactive `report.html`, `metrics_summary.json`, all Tier 1–3 JSON artifacts, and all four 300-DPI PNG figures (`waveforms.png`, `bunny_ears.png`, `psd_flicker.png`, `avar_5regions.png`) for immediate technical feasibility review:
     - **Gate 1:** `3.10e-16 rad` static error (`< 1e-9`), `1,666` continuous $2\pi$ wraps (`> 1000`), `5.84e-14` residual $\epsilon_{V_\pi,\text{eff}}$ (`< 1e-5`).
     - **Gate 2:** **`98.85%`** Deadband reduction & **`98.85%`** Bunny Ears scale-factor reduction across $[-0.5, +0.5]^\circ/\text{s}$.
     - **Gate 3:** Flat linear PSD slope `-0.0621` vs nonlinear $1/f$ slope `-0.8928` (~60 dB separation), $100\text{ Hz}$ $\mathbf{K}$-matrix repeatability **`0.000%`**.
     - **Gate 4:** Real $4\times 60\text{ s}$ Fast-Scale + $12\times 10\text{ h}$ ($3.6\times 10^6$ samples @ $100\text{ Hz}$) Slow-Scale: overlap mismatch **`2.42%`** (`< 5%`); 5-region WLS errors: $Q:+3.18\%$, $N:-0.71\%$, $B:+5.31\%$, $K:-7.06\%$, $R:+9.29\%$ (all within $\pm 10\%$).
4. **Rule 6 & Rule 16 Compliance:** Added project skill [`skills/ifog-portable-container-env/SKILL.md`](../skills/ifog-portable-container-env/SKILL.md) and synchronized all `.md`, `.tex`, `.pdf`, `CHANGELOG.md`, `DOCS_BUILD.sha256`, and `README.md` deliverables to `v1.2.0`.

---

## Release `v1.1.0` (2026-11-25)

### Automated Reporting, Unified Simulation Runner & Rule 16 Doc-Sync
- Added centralized automatic `.md` and interactive Plotly `.html` report generation (`viz/export_report.py`) + dashboard index under `report/`.
- Added unified simulation runner (`tier3_analysis/sim_runner_cli.py`, `scripts/run_sim.{py,sh}`, `ifog-sim-run`) supporting `single`, `gate1`–`gate4`, `full`, and `sweep` modes.
- Authored synchronized architecture & release documentation (`docs/IFOG_VPROTO_ARCHITECTURE.{md,tex,pdf}`, `docs/RELEASE_NOTES.{md,tex,pdf}`, `docs/CHANGELOG.md`, `scripts/build_docs.sh`).
- Enacted **AGENT.md Rule 16** with pure-stdlib CI/CD verifier `tier3_analysis/doc_sync.py` / `scripts/verify_doc_sync.py`.

---

## Release `v1.0.0` (2026-11-25)

### Initial Full Virtual Prototype Release
- Implemented the full 3-Tier Closed-Loop IFOG Multi-Scale Virtual Prototype strictly adhering to `IFOG-SIM-SPEC-004` v4.0: checksum-locked spec & PDF, Tier 1 Jones/Shupe solvers, Tier 2 C++17 IEEE Std 1666.1 SystemC/SystemC-AMS 2.3.4 closed-loop core, Tier 3 parallel sweeps, $\mathbf{K}$-matrix extractor, 10 h Dual-Regime Overlapping AVAR + 5-region WLS estimator, 30/30 formula verification, 100.0% C++ & Python coverage, full real 4-Gate acceptance & bit-exact regression suite, `AGENT.md`, 5 project skills, and strict 2-branch (`dev` -> `main`) CI/CD.
