# Closed-Loop IFOG Multi-Scale Virtual Prototype — System Architecture Specification

## Document Control Metadata

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-VPROTO-ARCH-001` |
| **Current Version** | `v4.1.0` |
| **Status** | `RELEASED (TRL 7-8 / DO-254 Production Gate Verified)` |
| **Normative Specification** | [`spec/IFOG-SIM-SPEC-007.md`](../spec/IFOG-SIM-SPEC-007.md) & [`spec/IFOG-SIM-SPEC-007.pdf`](../spec/IFOG-SIM-SPEC-007.pdf) (v7.0); [`spec/IFOG-SIM-SPEC-006.md`](../spec/IFOG-SIM-SPEC-006.md) (v6.0); [`spec/IFOG-SIM-SPEC-005.tex`](../spec/IFOG-SIM-SPEC-005.tex) (v5.0); [`spec/IFOG-SIM-SPEC-004.tex`](../spec/IFOG-SIM-SPEC-004.tex) (v4.0) |
| **Interactive Model Explorer** | [`docs/IFOG_ARCHITECTURE_EXPLORER.html`](IFOG_ARCHITECTURE_EXPLORER.html) (Code-Audited Interactive 3-Tier + Dual FMI 3.0.2 + TRL 7-8 Mathematical Block Diagram) |
| **Academic Presentation Deck** | [`docs/IFOG_VPROTO_PRESENTATION.pdf`](IFOG_VPROTO_PRESENTATION.pdf) / [`docs/IFOG_VPROTO_PRESENTATION.tex`](IFOG_VPROTO_PRESENTATION.tex) (38-Slide Beamer/TikZ/PGFPlots Deck) |
| **Scenarios Companion** | [`docs/IFOG_SIMULATION_SCENARIOS.md`](IFOG_SIMULATION_SCENARIOS.md) / [`docs/IFOG_SIMULATION_SCENARIOS.pdf`](IFOG_SIMULATION_SCENARIOS.pdf) |
| **Governance Authority** | [`AGENT.md`](../AGENT.md) (Rules 1–16) |
| **Reference Standards** | FMI Standard 3.0.2; IEEE Std 952-2020; IEEE Std 1666.1-2016; NASA-STD-7009A CAS-4; ASME V&V 20; MIL-STD-810H / DO-160G; DO-254 |
| **LaTeX / PDF Companion** | [`docs/IFOG_VPROTO_ARCHITECTURE.tex`](IFOG_VPROTO_ARCHITECTURE.tex) / [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](IFOG_VPROTO_ARCHITECTURE.pdf) |

## Document Version & Revision History

| Version | Release Date | Milestone / Gate | Affected Modules / Scope | Detailed Summary of Changes |
| :--- | :--- | :--- | :--- | :--- |
| `v1.0.0` | `2026-11-25` | Initial Release (Gates 1–4, 30 Formulas, 100% Dual Coverage) | `spec/`, `configs/`, `tier1_offline/`, `tier2_sysc_ams/`, `tier3_analysis/`, `viz/`, `tests/`, `.github/workflows/` | Complete 3-tier spec-driven Closed-Loop IFOG Virtual Prototype implementation (`IFOG-SIM-SPEC-004` v4.0), real IEEE 1666.1 SystemC/SystemC-AMS 2.3.4 core, 30/30 formula verification, 100% C++ (`gcovr`) & Python (`pytest-cov`) coverage, full real 4-Gate acceptance & CI/CD release pipeline. |
| `v1.1.0` | `2026-11-25` | Auto-Reporting, Unified Sim Runner & Rule 16 Doc-Sync | `viz/export_report.py`, `tier3_analysis/sim_runner_cli.py`, `tier3_analysis/doc_sync.py`, `scripts/run_sim.{py,sh}`, `scripts/verify_doc_sync.py`, `scripts/build_docs.sh`, `report/`, `docs/`, `AGENT.md`, `skills/`, `.github/workflows/` | Added centralized automatic `.md` and interactive `.html` report generation + dashboard index under `report/`; added unified simulation runner (`scripts/run_sim.sh`, `scripts/run_sim.py`, `ifog-sim-run`) supporting `single`, `gate1`–`gate4`, `full`, and `sweep` modes; authored synchronized release architecture & release notes documents (`.md`, `.tex`, `.pdf`) under `docs/`; enacted **AGENT.md Rule 16** with automated CI/CD version-document sync enforcement. |
| `v1.2.0` | `2026-11-25` | Portable Container (Docker/Podman), Universal Linux Source Setup & Full 4-Gate Example | `Containerfile`, `Dockerfile`, `.dockerignore`, `compose.yaml`, `scripts/install_systemc.sh`, `scripts/install_systemc_ams.sh`, `scripts/setup_env.sh`, `scripts/env.sh`, `scripts/container_run.sh`, `tier2_sysc_ams/CMakeLists.txt`, `examples/`, `skills/ifog-portable-container-env/`, `.github/workflows/ci.yml` | Added distro-independent Git-source installers for Accellera SystemC 2.3.4, SystemC-AMS PoC 2.3.4, `nlohmann/json` v3.11.3, and isolated Python venv (`scripts/setup_env.sh` + `scripts/env.sh`); added dual Docker/Podman OCI container suite (`Containerfile`, `Dockerfile`, `compose.yaml`, `scripts/container_run.sh`) verified in CI; executed and committed the complete real 4-Gate feasibility example (`examples/full_4gate_baseline/`) with full `.md`/`.html`/JSON/300-DPI PNG outputs. |
| `v2.0.0` | `2026-11-25` | `IFOG-SIM-SPEC-005` Official 6-State Symmetric DSP, 6 Time-Domain & 5 Engineering Scenarios (41 Formulas) | `spec/IFOG-SIM-SPEC-005.*`, `configs/schema_v5.json`, `configs/baseline_1km_6state.json`, `tier2_sysc_ams/` (`digital_dsp_sc`, `imu_3axis`, `optical_envelope_tdf`, `analog_frontend_tdf`, `adc_dac_bridge`), `tier3_analysis/scenarios_*.py`, `tier3_analysis/sim_runner_cli.py`, `viz/plot_scenarios.py`, `viz/export_report.py`, `scripts/run_all_scenarios.sh`, `docs/IFOG_SIMULATION_SCENARIOS.*`, `skills/ifog-6state-and-scenarios/` | Upgraded normative spec to `IFOG-SIM-SPEC-005` v5.0 (41/41 verified formulas `EQ-01`–`EQ-41`); implemented official 6-state symmetric DSP (`+136.94 dB` RAM/crosstalk rejection, `-33.3%` peak voltage), 64 B `dsp_trace.bin`, real-time FPGA BIT/FDIR, ADC aperture jitter, VRE/Faraday physics, and concurrent 3-axis SystemC-AMS IMU (`--imu3axis`); integrated all 6 Time-Domain (`TD-01`..`TD-06`) & 5 System Engineering (`ENG-01`..`ENG-05`) scenarios into 22-mode CLI + `scripts/run_all_scenarios.sh` and authored `docs/IFOG_SIMULATION_SCENARIOS.{md,tex,pdf}` with 100.0% C++ (`1,546/1,546` lines) & Python coverage. |
| `v2.1.0` | `2026-11-25` | Full All-Scenarios Example (`16/16` PASS), 15-Chart Interactive Plotly HTML & Upgraded Batch Scripts | `viz/export_report.py`, `examples/run_example.sh`, `examples/full_all_scenarios/`, `scripts/run_all_scenarios.sh`, `scripts/container_run.sh`, `tier3_analysis/sim_runner_cli.py`, `docs/`, `skills/ifog-reporting-and-doc-sync/` | Upgraded `viz/export_report.py` to generate detailed Markdown tables for Gate 5, `TD-01`..`TD-06`, and `ENG-01`..`ENG-05` plus **15 interactive Plotly HTML5 charts** and all **16 300-DPI PNG figures**; upgraded `examples/run_example.sh`, `scripts/run_all_scenarios.sh`, and `scripts/container_run.sh example` to execute ALL 16 official gates & scenarios (`MC=500`) end-to-end by default; executed and committed the complete real all-scenarios bundle under `examples/full_all_scenarios/`. |
| `v2.2.0` | `2026-11-26` | Group C Dynamic Response, Output PSD & Sinusoidal Electro-Optic Probe (`DYN-01`..`DYN-04`, `20/20` PASS) | `tier3_analysis/scenarios_dynamic_probe.py`, `tier3_analysis/sim_runner_cli.py`, `viz/plot_scenarios.py`, `viz/export_report.py`, `examples/full_all_scenarios/`, `tests/`, `docs/`, `skills/` | Added Group C dedicated dynamic & internal electro-optic probe workflows (`DYN-01` Step Response, `DYN-02` Full Bode Magnitude/Phase/Group Delay, `DYN-03` Broadband Output Rate PSD/ASD & Cumulative RMS Noise, `DYN-04` Sinusoidal Input Internal Chain `PD`, `V_fb MIOC`, Sagnac phase, `V_TIA`, ADC blanking); expanded CLI to **27 modes**, **20 official gates/scenarios**, **20 300-DPI PNGs**, **19 interactive Plotly HTML5 charts**, and refreshed `examples/full_all_scenarios/` (`20/20` PASS). |
| `v3.0.0` | `2026-11-26` | `IFOG-SIM-SPEC-006` Standalone FMI 3.0 Co-Simulation FMU (`build/ifog_core.fmu`, 44 Formulas, `21/21` PASS) | `spec/IFOG-SIM-SPEC-006.*`, `fmi_wrapper/`, `tier2_sysc_ams/{include,src}/ifog_top_module.*`, `tier2_sysc_ams/CMakeLists.txt`, `CMakeLists.txt`, `tier3_analysis/fmi_master_runner.py`, `tier3_analysis/sim_runner_cli.py`, `viz/`, `tests/`, `skills/ifog-fmi3-cosim-fmu/`, `.github/workflows/` | Upgraded normative spec to `IFOG-SIM-SPEC-006` v6.0 (44/44 verified formulas `EQ-01`–`EQ-44`); wrapped unmodified Tier 2 SystemC/SystemC-AMS core (`IfogTopModule`) into standalone FMI 3.0 Co-Simulation FMU `build/ifog_core.fmu` via vendorized FMI 3.0 C headers, 75-symbol `fmi3_bridge.cpp`, 15-variable `modelDescription.xml.in` (`canBeInstantiatedOnlyOncePerProcess="true"`), and CMake `package_fmu` target; added subprocess-isolated FMPy master orchestrator (`fmi_master_runner.py`, `--mode fmi_gate`, Gate 6: 0 XSD errors, `0.00e+00 rad/s` bit-exact equivalence, `97.42%` deadband reduction, `3.83%` 5-region AVAR overlap), 100.0% C++ coverage across `tier2_sysc_ams/` + `fmi_wrapper/src/` (`2,102/2,102` lines), 100.0% Python coverage, and refreshed `examples/full_all_scenarios/` (`21/21` PASS). |
| `v3.0.1` | `2026-11-26` | Standardized Explanatory Reports (`.md`/`.html`) & Code-Audited Interactive HTML Architecture Explorer | `viz/architecture_explorer.py`, `viz/report_narratives.py`, `viz/export_report.py`, `docs/IFOG_ARCHITECTURE_EXPLORER.html`, `scripts/build_docs.sh`, `examples/run_example.sh`, `examples/full_4gate_baseline/`, `examples/full_all_scenarios/`, `tests/unit/test_architecture_and_narratives.py`, `.github/workflows/release.yml` | Added code-audited interactive HTML5 mathematical block diagram (`viz/architecture_explorer.py` -> `docs/IFOG_ARCHITECTURE_EXPLORER.html` + per-run `architecture_model.html`) reconciled 1-to-1 with live `IFOG-SIM-SPEC-006` C++/Python source code (`EQ-01`..`EQ-44`, 4 path highlight modes, live parameter strip & audit table); added `viz/report_narratives.py` providing standardized 3-part theoretical foundation, plain-language non-specialist reading guide, and dynamic measured proof for all 21 diagnostic figures in both `report.md` and KaTeX-rendered `report.html`; regenerated both curated examples (`examples/full_4gate_baseline/` & `examples/full_all_scenarios/`) with the standardized `v3.0.1` report format at 100.0% dual coverage. |
| `v4.0.0` | `2026-11-26` | `IFOG-SIM-SPEC-007` High-Fidelity Predictive Physics, Tunable FMI 3.0 FMU & Inverse Calibration (53 Formulas, `23/23` PASS) | `spec/IFOG-SIM-SPEC-007.*`, `configs/schema_v6.json`, `configs/baseline_1km_spec007.json`, `tier1_offline/`, `tier2_sysc_ams/`, `fmi_wrapper/`, `tier3_analysis/inverse_calibration.py`, `tier3_analysis/scenarios_spec007.py`, `viz/plot_spec007_calibration.py`, `viz/report_narratives.py`, `viz/export_report.py`, `skills/ifog-spec007-physics-calibration/`, `docs/` | Upgraded normative spec to `IFOG-SIM-SPEC-007` v7.0 (**53/53 verified formulas `EQ-01`–`EQ-53`**): added discrete Quadrupole/Octupole coil winding (`PHY-01`: `-47.69%` Shupe reduction), thermo-mechanical elasto-optic stress drift, dynamic $K_{\text{opt}}(t)/V_{\text{eff}}(t)/\Delta\phi_{\text{pol}}(t)/V_\pi(t)$, 6-channel `shupe_lut.bin` v2 (56 B `<7d` with v1 fallback), 2nd-order MIOC electro-acoustic dynamics before $K_{\text{delay}}$, capacitive + resistive PCB crosstalk ($C_{\text{xtalk}}\,dV/dt + G_{\text{xtalk}}V$), Rayleigh/facet back-reflection, **7 live tunable FMI 3.0 parasitic variables (`VR 15..21`)**, `DualRegimeStitcher` quadrature BI subtraction, automated 3-stage bounded `InverseCalibrator` (`CAL-01`: `40–103% -> 0.04–0.91% < 5%` across all 4 validation domains, 10 params recovered `<= 2.18%`), presentation-grade tier-by-tier mathematical compendium across all docs/reports, and **100.0% C++ (`2,329/2,329` lines)** & **100.00% Python (`4,650/4,650` stmts)** coverage. |
| `v4.0.1` | `2026-11-26` | 32-Slide Academic LaTeX Presentation Deck, Code-Only CI/CD Diff Filter & 22-Asset Release Bundle | `docs/IFOG_VPROTO_PRESENTATION.{tex,pdf}`, `tier3_analysis/ci_diff_filter.py`, `scripts/ci_diff_filter.py`, `tests/unit/test_ci_diff_filter.py`, `.github/workflows/{ci,release}.yml`, `scripts/build_docs.sh`, `docs/` | Authored 32-slide academic LaTeX Beamer deck (`docs/IFOG_VPROTO_PRESENTATION.{tex,pdf}`) with TikZ/`pgfplots`/`circuitikz` diagrams, explicit IEEE 1666.1 SystemC-AMS LTF (`sca_ltf_nd`) + Hybrid ZOH LTF & Lefèvre/IEEE 952 references, SI input tables (`schema_v6.json`), explicit Tier 1 $\to$ Tier 2 $\to$ Tier 3 parameter handoff (`phys_params.json`, `shupe_lut.bin` v2, `sim_out.bin`, `k_matrix.json`) with mathematical separation & orthogonality proofs, 2/4/6-State DSP models & waveforms, and 11 enlarged experimental slides; added stdlib-only code-vs-docs CI/CD diff filter (`detect-changes` job, 100.00% Python coverage: `4,770/4,770` stmts); attached `IFOG_VPROTO_PRESENTATION.{pdf,tex}` directly to the automated GitHub Release workflow (22 verified assets). |
| `v4.1.0` | `2026-11-27` | Group E TRL 7–8 / DO-254 Industrial Qualification Suite (`IND-01`..`IND-06`), Full 2/4/6-State FPGA DSP & Multi-Instance FMI 3.0.2 FMU (`29/29` PASS) | `rtl/ifog_dsp_6state.sv`, `fmi_wrapper/{src/fmi3_multi_bridge.cpp,modelDescription_multi.xml.in,buildDescription.xml}`, `tier1_offline/shupe_thermal.py`, `tier2_sysc_ams/`, `tier3_analysis/{lab_validation,scenarios_industrial,scenarios_dynamic_probe,scenarios_time_domain,sim_runner_cli}.py`, `configs/lab_datasets/reference_ifog_lab/`, `viz/{plot_industrial,plot_scenarios,report_narratives,export_report,architecture_explorer}.py`, `skills/ifog-industrial-trl7-do254/`, `docs/` | Closed all 6 industrial aerospace/defense gaps to achieve 10/10 TRL 7–8 / DO-254 readiness: **`IND-01`** physical lab CSV CAS-4 / ASME V&V 20 validation (`101.9% -> 4.51%`, $|E|/u_{\text{val}} \le 0.723$), **`IND-02`** bit-true signed `Q16.32` FPGA fixed-point DSP + synthesizable SystemVerilog RTL (`rtl/ifog_dsp_6state.sv`) with **0-LSB** match across **2-State, 4-State, and 6-State**, **`IND-03`** 3D ANSYS/COMSOL cylindrical FEM $\to$ `shupe_lut.bin` v2 (`6.00x` Octupole suppression), **`IND-04`** MIL-STD-810H / DO-160G random vibration PSD + 2-DOF resonance (`4.82x` $g_{\text{rms}}$ & `3.11x` VRE reduction), **`IND-05`** Multi-Instance Pure-C++17 Source-Code FMI 3.0.2 FMU (`build/ifog_core_multi.fmu`, `canBeInstantiatedOnlyOncePerProcess="false"`, 0 XSD errors, 3 concurrent axes 6s/4s/2s in 1 process), and **`IND-06`** 12-corner PVT + 10-yr/50 krad(Si) space aging; expanded `DSP-01` & `DYN-01..03` to full 2/4/6-State coverage, verified **100.0% C++ (`2,733/2,733` lines, `299/299` functions)** & **100.00% Python (`5,632/5,632` stmts)** coverage, **29/29 PASS** curated example, and **23 verified release assets**. |

---

## 1. System Context & Engineering Objectives

`ifog-vproto` is a deterministic, multi-scale virtual prototype, **dual FMI 3.0.2 Co-Simulation FMU suite (`build/ifog_core.fmu` SystemC-AMS + `build/ifog_core_multi.fmu` Multi-Instance Pure-C++17 Source-Code FMU, 22 SI variables)**, **bit-true FPGA/RTL co-verification reference**, and **NASA-STD-7009A CAS-4 / ASME V&V 20 calibrated platform** for a **Closed-Loop Interferometric Fiber-Optic Gyroscope (IFOG)** supporting full **2-State, 4-State Lefèvre, and Official 6-State Symmetric modulation** (`IFOG-SIM-SPEC-007` v7.0 / `SPEC-006` v6.0 / `SPEC-005` v5.0 / `SPEC-004` v4.0), as well as concurrent 3-axis IMU co-simulation.

### Multi-Scale Time-Domain Separation

| Architecture Tier | Execution Engine | Characteristic Time Step / Horizon | Physical Scope & Outputs |
| :--- | :--- | :--- | :--- |
| **Tier 1 (Offline Solvers)** | Python 3.12 + NumPy / SciPy (`tier1_offline/`) | Static spectral ($N_{\text{spec}} \in [64, 128]$) & 1D/3D thermal ($0..10\text{ h}$) | Spectral-sliced Jones polarization & Rayleigh/facet coherence (`phys_params.json`), discrete Quadrupole/Octupole coil winding, 1D Crank–Nicolson & **3D ANSYS/COMSOL cylindrical FEM RBF projection** (`--fem-3d-csv`) $\to$ Shupe + elasto-optic stress + dynamic $K_{\text{opt}}/V_{\text{eff}}/\phi_{\text{pol}}/V_\pi$ (`shupe_lut.bin` v2, v1 fallback) |
| **Tier 2 (Fast-Scale Core & FPGA RTL)** | C++17 `-O3 -fPIC` + SystemC 2.3.4 + SystemC-AMS 2.3.4 (`tier2_sysc_ams/`) + SV RTL (`rtl/`) | $\Delta t_{\text{fast}} = \tau/K \approx 153\text{–}306\text{ ns}$, $\tau \approx 4.89\ \mu\text{s}$, horizon $0.008..60\text{ s}$ | Single-axis (`IfogTopModule`), 3-axis IMU (`--imu3axis`), MIOC electro-acoustic dynamics, capacitive+resistive crosstalk, Rayleigh/facet back-reflection, $O(1)$ LUT v2 interpolation, hybrid TIA/DAC LTFs, **2/4/6-State DSP with bit-true signed `Q16.32` FPGA fixed-point mode matching `rtl/ifog_dsp_6state.sv`** & BIT/FDIR (`sim_out.bin`, `micro_waveforms.bin`, `dsp_trace.bin`) |
| **Dual FMI 3.0.2 FMUs** | C++17 FMI 3.0.2 Wrappers (`fmi_wrapper/` -> `ifog_core.fmu` & `ifog_core_multi.fmu`) | Macro communication step $H \ge 0.5\text{ ms}$ (internal $\Delta t_{\text{fast}} = 306\text{ ns}$) | SystemC-AMS `ifog_core.fmu` (bit-exact `0.00e+00 rad/s` vs `ifog_sim`) + **Multi-Instance Pure-C++17 Source-Code `ifog_core_multi.fmu`** (`canBeInstantiatedOnlyOncePerProcess="false"`, `sources/buildDescription.xml`, concurrent 3-axis 6s/4s/2s in 1 process), 75 C-API exports, 22 SI variables (`VR 0..21`), 0 XSD errors |
| **Tier 3 (Lab CAS-4, Calibration & AVAR)** | Python 3.12 + FMPy + SciPy (`tier3_analysis/`) | $\Delta t_{\text{slow}} = 10\text{ ms}$ ($100\text{ Hz}$), horizon $10\text{ h}$ ($3.6\times 10^6$ samples) | **38-mode unified CLI runner** (`sim_runner_cli.py`), **Physical Lab CSV CAS-4 / ASME V&V 20 validator (`lab_validation.py`)**, 3-Stage `InverseCalibrator`, MIL-STD-810H Random Vibration PSD + 2-DOF resonance, 12-Corner PVT & 10-Yr/50 krad Space TID, Dual-Regime IEEE Std 952 AVAR, **29 / 29 PASS** |
| **Diagnostics & Auto-Reporting** | Python 3.12 + Matplotlib / Plotly / KaTeX (`viz/`, `report/`, `scripts/`) | Post-run automatic execution | **29 300-DPI PNG figures**, interactive KaTeX+Plotly HTML5 & Markdown reports with complete tier-by-tier formulas (`EQ-01`..`EQ-53`), embedded code-audited `architecture_model.html` (`v4.1.0`), and centralized `report/index.{md,html}` |

---

## 2. End-to-End 3-Tier Architecture Diagram

```mermaid
flowchart LR
    CFG["configs/baseline_1km.json\n+ schema_v4.json"] --> RUNNER["scripts/run_sim.sh\n-> scripts/run_sim.py\n(tier3_analysis/sim_runner_cli.py)"]

    subgraph T1["Tier 1 — Offline Physical Solvers (Python)"]
        JONES["jones_spectral.py\n(EQ-04,05,07,08)"]
        SHUPE["shupe_thermal.py\n(EQ-09 CN 1D / FEM)"]
    end

    RUNNER --> JONES
    RUNNER --> SHUPE
    JONES -->|"phys_params.json"| T2
    SHUPE -->|"shupe_lut.bin (SHUP)"| T2

    subgraph T2["Tier 2 — Closed-Loop Co-Sim Core (C++17 / SystemC-AMS 2.3.4)"]
        OPT["OpticalEnvelope_TDF\n(rate=K, EQ-06,10..13)"]
        PINK["PinkNoise_TDF\n(rate=1, 5-pole IIR)"]
        AFE["AnalogFrontEnd_TDF\n(rate=K, EQ-14..18\nHybrid ZOH / sca_ltf_nd)"]
        ADC["ADC_Bridge_TDF2DE\n(Blanking + N_adc, EQ-19)"]
        DSP["DigitalDSP_SC (DE)\n(2/4-State, PRBS, EQ-01..03,20..23)"]
        DAC["DAC_Driver_TDF\n(set_delay(1), d=2)"]
        OPT --> AFE
        PINK --> AFE
        PINK --> DAC
        AFE --> ADC
        ADC -->|"sc_buffer"| DSP
        DSP -->|"sc_buffer"| DAC
        DAC --> OPT
        DAC -->|"xtalk"| AFE
    end

    T2 -->|"sim_out.bin (32B)\nmicro_waveforms.bin (64B)"| T3

    subgraph T3["Tier 3 — Analysis & Dual-Regime AVAR (Python)"]
        SWEEP["run_sweep_parallel.py\n+ analyze_nonlinearity.py"]
        KMAT["extract_k_matrix.py\n(100 Hz FFT, EQ-27)"]
        AVAR["dual_regime_avar.py\n(10 h / 3.6M pts, EQ-24..30)"]
    end

    T3 --> VIZ["viz/export_report.py\n(PNG + MD + Interactive HTML)"]
    VIZ --> REP["report/<run_id>/\nreport.md, report.html,\nmetrics_summary.json, figures/\n+ report/index.{md,html}"]
```

---

## 3. Subsystem Architectural Breakdown

### 3.1 Configuration & Schema Governance (`configs/`, `tier1_offline/config_loader.py`)
- **Normative Schema:** [`configs/schema_v4.json`](../configs/schema_v4.json) enforces JSON Schema Draft 2020-12 over `meta`, `optics`, `fiber_coil`, `thermal_shupe`, `magneto_optic`, `mioc`, `analog_frontend`, `adc_dac`, `dsp`, `noise`, `ablation_flags`, `simulation`, and `slow_scale`.
- **Fail-Closed Cross-Field Checks (`validate_config`):** Enforces $0 \le k_{\text{start}} \le k_{\text{end}} < K$, $V_{\min} < V_{\max}$, $f_{\min,\text{pink}} < f_{\max,\text{pink}}$, Jury stability $0 < K_{\text{tot},1} < 1$, and 4-state Loop-2 bandwidth separation $K_{\text{tot},2} \le 0.1 K_{\text{tot},1}$ (Rule 11).

### 3.2 Tier 1 — Offline Optical & Thermal Solvers (`tier1_offline/`)
- **Spectral-Sliced Jones Matrix Solver ([`jones_spectral.py`](../tier1_offline/jones_spectral.py)):**
  - Discretizes the Gaussian SLD spectrum into $N_{\text{spec}} \in [64, 128]$ slices across $\bar{\nu} \pm 3\sigma_\nu$ in vectorized NumPy `complex128`.
  - Computes frequency-proportional group birefringence $\Delta\beta(\omega_k) = \frac{2\pi}{L_B}\frac{\omega_k}{\bar{\omega}}$ across $M$ PM fiber segments with Lorentz reciprocity $\mathbf{J}_{\text{CCW}}(\omega_k) = \mathbf{J}_{\text{CW}}^T(\omega_k)$ (`EQ-04`).
  - Evaluates exact closed-form fringe visibility $V$ and polarization bias phase $\phi_{\text{pol}}$ (`EQ-05`), Sagnac scale factor $K_{\text{opt}}$ (`EQ-07`), and coherence-weighted optical Kerr bias $\Delta\phi_{\text{Kerr}}$ (`EQ-08`), emitting `phys_params.json`.
- **Thermal-Mechanical Shupe Solver ([`shupe_thermal.py`](../tier1_offline/shupe_thermal.py)):**
  - Dual input modes: unconditionally stable 1D Crank–Nicolson radial heat diffusion (`scipy.linalg.solve_banded`) or external FEM CSV import (`t_s, z_m, dT_dt_K_per_s`).
  - Integrates `EQ-09` with quadrupolar winding imperfection $\delta z_{\text{quad}}$ and writes a fail-closed little-endian binary LUT `shupe_lut.bin`:

| Byte Offset | Field | Type | Description |
| :--- | :--- | :--- | :--- |
| `0..3` | `magic` | `char[4]` | Constant ASCII `"SHUP"` |
| `4..7` | `version` | `uint32` | Format version (`1`) |
| `8..15` | `n_samples` | `uint64` | Number of `(t_s, delta_phi_shupe_rad)` pairs |
| `16..23` | `dt_s` | `double` | Uniform time step `[s]` |
| `24..` | `samples[]` | `pair<double,double>` | Packed little-endian `<dd` pairs |

### 3.3 Tier 2 — IEEE Std 1666.1 SystemC / SystemC-AMS Core (`tier2_sysc_ams/`)
Built as a static library `libifog_core.a` + CLI executable `build/ifog_sim` + unit test binary `build/ifog_cpp_tests` using C++17 (`SC_CPLUSPLUS=201703L`) linked against Ubuntu 24.04 SystemC 2.3.4 and SystemC-AMS PoC 2.3.4 (pinned commit `a72d365f`).

#### Module Inventory & TDF/DE Scheduling Contract
| Module | File | Domain | Rate / Port Contract | Key Equations |
| :--- | :--- | :--- | :--- | :--- |
| `OpticalEnvelope_TDF` | [`optical_envelope_tdf.cpp`](../tier2_sysc_ams/src/optical_envelope_tdf.cpp) | TDF | `rate = K`, $\Delta t_{\text{fast}} = \tau/K$, $\tau$-delay ring buffer for $\Delta\phi_{\text{mod}}[m]$ | `EQ-06`, `EQ-10`–`EQ-13` |
| `PinkNoise_TDF` | [`pink_noise_tdf.cpp`](../tier2_sysc_ams/src/pink_noise_tdf.cpp) | TDF | `rate = 1` per $\tau$, 3 channels (TIA, DAC, xtalk), 5-pole log-spaced IIR | `EQ-14`, `EQ-18` |
| `AnalogFrontEnd_TDF` | [`analog_frontend_tdf.cpp`](../tier2_sysc_ams/src/analog_frontend_tdf.cpp) | TDF | `rate = K`, 6-component white noise, hybrid `ExactSecondOrderLtf` / `sca_ltf_nd`, cubic polynomial NL + clip | `EQ-14`–`EQ-18` |
| `ADC_Bridge_TDF2DE` | [`adc_dac_bridge.cpp`](../tier2_sysc_ams/src/adc_dac_bridge.cpp) | TDF $\to$ DE | Blanking window $[k_{\text{start}}, k_{\text{end}}]$, $N_{\text{ADC}}$ quantizer, drives `sc_buffer<double>` | `EQ-19` |
| `DAC_Driver_TDF` | [`adc_dac_bridge.cpp`](../tier2_sysc_ams/src/adc_dac_bridge.cpp) | DE $\to$ TDF | `dac_code_in.set_delay(1)` breaks algebraic loop; hybrid 2nd-order driver LTF | `EQ-21`, Rule 10 |
| `DigitalDSP_SC` | [`digital_dsp_sc.cpp`](../tier2_sysc_ams/src/digital_dsp_sc.cpp) | SystemC DE | `SC_METHOD` on `sig_adc_code` (`sc_buffer`); 2-slot `PipeTag` FIFO ($d = 2$); 2-state & 4-state demod + dual integrators + reflected PRBS dither + 128 KB buffered 32-byte `SimRecord` writer | `EQ-01`–`EQ-03`, `EQ-20`–`EQ-23` |

#### Key Numerical & Architectural Decisions
1. **Algebraic Loop Breaking & Exact $d = 2$ Pipeline Latency:** Setting `dac_code_in.set_delay(1)` on `DAC_Driver_TDF` combined with the DE delta-cycle boundary creates an exact 2-slot loop latency matching $L_1(z) = K_{\text{tot}}/[z^2(z-1)]$ (`EQ-22`). `sc_core::sc_buffer<double>` is mandatory at TDF/DE boundaries so repeated quiet ADC codes never stall `DigitalDSP_SC`.
2. **Hybrid Stiff/Non-Stiff 2nd-Order LTF Solver:** SystemC-AMS PoC 2.3.4's `sca_ltf_nd` exhibits both an $O(N^2)$ slowdown when given a sub-step `tstep` and severe Trapezoidal Nyquist ringing when $\omega_0 \Delta t_{\text{fast}} \gg 2$ (baseline $\omega_0 \Delta t_{\text{fast}} = 23.26$). `AnalogFrontEnd_TDF` and `DAC_Driver_TDF` automatically dispatch to `ExactSecondOrderLtf` (exact analytical ZOH matrix exponential $e^{\mathbf{A}\Delta t}$ for underdamped, critically damped, and overdamped poles) when $\omega_0 \Delta t_{\text{fast}} > 0.2$, and invoke `sca_tdf::sca_ltf_nd` natively when $\omega_0 \Delta t_{\text{fast}} \le 0.2$. Throughput reaches **~1.1 s wall-clock per simulated second** (`~65 s` per 60 s run).
3. **Packed Binary Output Contracts (`ifog_types.hpp`, `micro_trace.hpp`):**
   - `sim_out.bin`: 32-byte packed `SimRecord` (`static_assert(sizeof(SimRecord) == 32)`): `double t`, `double omega_in`, `int64_t omega_out_raw` (LSB $= 10^{-12}\text{ rad/s}$), `int32_t vpi_err_raw` (LSB $= 10^{-9}\text{ rad}$), `uint32_t flags`.
   - `micro_waveforms.bin`: 64-byte packed `MicroRecord` (`static_assert(sizeof(MicroRecord) == 64)`): 8 IEEE-754 `double` fields (`t`, `v_drv`, `p_det`, `v_tia`, `v_tia_nl`, `i_xtalk`, `phi_mod`, `in_window`).

### 3.4 Tier 3 — Analysis, Unified Runner & Automatic Reporting (`tier3_analysis/`, `viz/`, `scripts/`, `report/`)
- **Parallel Sweeps & Nonlinearity ([`run_sweep_parallel.py`](../tier3_analysis/run_sweep_parallel.py), [`analyze_nonlinearity.py`](../tier3_analysis/analyze_nonlinearity.py)):** Multi-core worker pool executing 23-point Slow Rate Ramp sweeps (`[-0.5, +0.5] deg/s`) and Monte Carlo ablations, quantifying Deadband peak/width and Bunny Ears scale-factor error reduction ($\ge 90\%$).
- **Leakage Matrix $\mathbf{K}$ Extraction ([`extract_k_matrix.py`](../tier3_analysis/extract_k_matrix.py)):** Injects coherent $100\text{ Hz}$ sinusoids into `tia`, `dac`, and `xtalk` nodes and computes Hann-windowed coherent quadrature DFT gain (`EQ-27`).
- **Dual-Regime Overlapping AVAR ([`dual_regime_avar.py`](../tier3_analysis/dual_regime_avar.py)):** Synthesizes 10 h / $100\text{ Hz}$ ($3.6\times 10^6$-sample) Slow-Scale rate traces combining calibrated ARW, exact IEEE 952 12-pole IIR $1/f$ pink noise ($\text{gain} = B\sqrt{\ln(r)/\pi}$), RRW Wiener/Gauss–Markov (`EQ-25`), Rate Ramp, 27-bit angle readout quantization, and Tier 1/2 physical drift (`EQ-28`), then performs variance-space ensemble Overlapping AVAR (`EQ-29`), overlap continuity check `< 5%` on $[0.1, 5.0]\text{ s}$ (`EQ-30`), and 5-region relative-weighted NNLS fitting (`EQ-24`).
- **Unified Simulation Runner ([`sim_runner_cli.py`](../tier3_analysis/sim_runner_cli.py), [`scripts/run_sim.py`](../scripts/run_sim.py), [`scripts/run_sim.sh`](../scripts/run_sim.sh)):**
  - Single ergonomic entrypoint supporting `--mode {single, gate1, gate2, gate3, gate4, full, sweep}` with automatic Tier 2 binary build check and **guaranteed automatic report generation into `report/<run_id>/`**.
- **Automated Reporting Engine ([`viz/export_report.py`](../viz/export_report.py), `report/`):**
  - Automatically renders `report/<run_id>/report.md`, `report/<run_id>/report.html` (interactive Plotly multi-panel subplots + KPI tables + 300-DPI figure gallery + collapsible JSON), `report/<run_id>/metrics_summary.json`, and `report/<run_id>/figures/*.png`, while refreshing the centralized dashboard `report/index.md` and `report/index.html`.

---

## 4. Complete Tier-by-Tier Mathematical Formulation Compendium (`EQ-01` .. `EQ-53`)

> **Partner-Ready Reference:** Every mathematical equation executed by `ifog-vproto` is organized below strictly by architectural tier, verified 1-to-1 against live C++/Python source code and individually tested in `tests/formula_verification/` (`53 / 53` PASS).

### 4.1 Tier 1 — Offline Optical, Spectral, Winding & Thermo-Mechanical Solvers (`tier1_offline/`)

1. **Spectral-Sliced Jones Polarization & Lorentz Reciprocity (`EQ-04`, `EQ-05` — `jones_spectral.py`):**
   $$\mathbf{J}_{\text{CW}}(\omega_k) = \prod_{j=1}^{M} \mathbf{R}(-\theta_j)\,\operatorname{diag}\!\left(e^{-i\Delta\beta(\omega_k)\Delta z_j/2},\,e^{+i\Delta\beta(\omega_k)\Delta z_j/2}\right)\mathbf{R}(\theta_j), \qquad \mathbf{J}_{\text{CCW}}(\omega_k) = \mathbf{J}_{\text{CW}}^{T}(\omega_k)$$
   $$V = \frac{\left|\sum_k w_k \mathbf{E}_{\text{CW}}^\dagger(\omega_k)\mathbf{E}_{\text{CCW}}(\omega_k)\right|}{\frac{1}{2}\sum_k w_k \bigl(\|\mathbf{E}_{\text{CW}}\|^2 + \|\mathbf{E}_{\text{CCW}}\|^2\bigr)}, \qquad \phi_{\text{pol}} = \arg\!\left(\sum_k w_k \mathbf{E}_{\text{CW}}^\dagger(\omega_k)\mathbf{E}_{\text{CCW}}(\omega_k)\right)$$
2. **Sagnac Scale Factor, Kerr Bias & Coherence Length (`EQ-07`, `EQ-08`, `EQ-52`):**
   $$K_{\text{opt},0} = \frac{2\pi L D}{\bar{\lambda} c}, \qquad \Delta\phi_{\text{Kerr}} = \eta_{\text{coh}}\,\frac{2\pi n_2}{\bar{\lambda} A_{\text{eff}}}\,L\,(P_{\text{CW}} - P_{\text{CCW}}), \qquad L_c = \frac{\bar{\lambda}^2}{\Delta\lambda_{\text{FWHM}}}$$
3. **Discrete Quadrupole / Octupole Coil Winding & Thermo-Mechanical Stress Drift (`EQ-09`, `EQ-45`, `EQ-46` — `shupe_thermal.py`):**
   $$\Delta\phi_{\text{thermo}}(t) = \Delta\phi_{\text{Shupe}}(t) + \Delta\phi_{\text{stress}}(t), \qquad \Delta\phi_{\text{Shupe}}(t) = \frac{\beta_0}{c}\!\left(\frac{dn}{dT} + n_{\text{eff}}\alpha_f\right)\sum_{i=0}^{N_{\text{turns}}-1} (L - 2z_i)\,\dot{T}(r_i, z_{\text{ax},i}, t)\,\Delta z_i$$
   $$\Delta\phi_{\text{stress}}(t) = \frac{\beta_0}{c}\left(-\frac{n_{\text{eff}}^3}{2}(p_{11}+2p_{12})\right) E_{\text{fiber}}(\alpha_{\text{bobbin}}-\alpha_f)\sum_{i=0}^{N_{\text{turns}}-1} (L-2z_i)\,\dot{\varepsilon}_{\text{th}}(r_i, t)\,\Delta z_i$$
4. **Dynamic Thermal Scale Factor, Dynamic Optical Parameters & 6-Channel Binary LUT v2 (`EQ-47`, `EQ-48`, `EQ-49`):**
   $$K_{\text{opt}}(t) = K_{\text{opt},0}\!\left[1 + (\alpha_{\text{bobbin}} + \alpha_f)\,\Delta\bar{T}(t) - \frac{\Delta\bar{\lambda}(t)}{\bar{\lambda}_0}\right] = K_{\text{opt},0}\bigl(1 + \delta K_{\text{opt}}(t)\bigr)$$
   $$V_\pi(t) = V_{\pi,0}\bigl(1 + \alpha_{V_\pi}\Delta T_{\text{MIOC}}(t)\bigr), \qquad \text{LUT v2 (`56 B <7d`): } \bigl(t,\;\Delta\phi_{\text{Shupe}},\;\Delta\phi_{\text{stress}},\;\delta K_{\text{opt}},\;V_{\text{eff}},\;\Delta\phi_{\text{pol}},\;V_\pi\bigr)$$

### 4.2 Tier 2 — Fast-Scale SystemC-AMS Optical, AFE, Parasitics & Bit-True DSP Core (`tier2_sysc_ams/`)

1. **Optical Envelope, MIOC 2nd-Order Electro-Acoustic Dynamics & Back-Reflection (`EQ-06`, `EQ-10`–`EQ-13`, `EQ-50`, `EQ-52`):**
   $$H_{\text{MIOC}}(s) = \frac{\omega_{\text{mioc}}^2}{s^2 + 2\zeta_{\text{mioc}}\omega_{\text{mioc}}s + \omega_{\text{mioc}}^2}, \qquad \phi_{\text{MIOC}}[m] = \frac{\pi(1+\epsilon_{V_\pi})}{V_\pi(t)}\,V_{\text{eff,mioc}}[m] + \gamma_{\text{nl}}\,V_{\text{eff,mioc}}^2[m]$$
   $$\Delta\phi_{\text{NR}}[m] = K_{\text{opt}}(t)\Omega_{\text{in}}[m] + \Delta\phi_{\text{Shupe}} + \Delta\phi_{\text{stress}} + \Delta\phi_{\text{pol}} + \Delta\phi_{\text{Kerr}} + \Delta\phi_{\text{Faraday}} + \Delta\phi_{\text{VRE}} + \Delta\phi_{\text{back}}[m]$$
   $$\Delta\phi_{\text{mod}}[m] = \operatorname{wrap}_{2\pi}\!\bigl(\phi_{\text{MIOC}}[m] - \phi_{\text{MIOC}}[m - K_{\text{delay}}]\bigr), \qquad P_{\text{det}}[m] = \frac{P_0}{2}\bigl(1 + \alpha_{\text{RAM}} V_{\text{eff,mioc}}[m]\bigr)\bigl(1 + V_{\text{eff}}(t)\cos(\Delta\phi_{\text{NR}} + \Delta\phi_{\text{mod}})\bigr)$$
   $$\sigma_{\phi,\text{back}} = \sqrt{2\bigl(R_{\text{facet}} + R_{\text{Rayleigh}}\,L_c\bigr)}$$
2. **TIA Summing Node, Capacitive + Resistive Crosstalk, 6-Component Noise & Hybrid LTF (`EQ-14`–`EQ-19`, `EQ-51`):**
   $$I_{\text{in}}[m] = \mathcal{R} P_{\text{det}}[m] + i_{\text{xtalk}}[m] + i_{w}[m], \qquad i_{\text{xtalk}}[m] = G_{\text{xtalk}}\,V_{\text{drv}}[m] + C_{\text{xtalk}}\,\frac{V_{\text{drv}}[m] - V_{\text{drv}}[m-1]}{\Delta t_{\text{fast}}}$$
   $$H_{\text{TIA}}(s) = \frac{-R_f\,\omega_0^2}{s^2 + 2\zeta\omega_0 s + \omega_0^2}, \qquad V_{\text{out,nl}} = \operatorname{clip}\!\bigl(V_{\text{lin}} + G_2 V_{\text{lin}}^2 + G_3 V_{\text{lin}}^3 + v_{1/f},\;V_{\min},\;V_{\max}\bigr)$$
   $$\sigma_{V,\text{jit}} = \left|\frac{dV}{dt}\right|\sigma_{t,\text{jit}} \quad (\text{EQ-35}), \qquad \eta_b = \frac{k_{\text{end}} - k_{\text{start}} + 1}{K} \quad (\text{EQ-19})$$
3. **Bit-True 4-State & Official 6-State Orthogonal DSP, Jury Stability & BIT/FDIR (`EQ-01`–`EQ-03`, `EQ-20`–`EQ-23`, `EQ-31`–`EQ-34`, `EQ-36`–`EQ-39`):**
   - **4-State Lefèvre:** $e_\Omega = (y_2-y_1)+(y_4-y_3)$, $e_{V_\pi} = (y_3+y_4)-(y_1+y_2)$.
   - **Official 6-State Symmetric ($\alpha^* = \pi/3$, $-33.3\%$ $V_{\text{peak}}$, $+136.9\text{ dB}$ RAM/xtalk rejection):**
     $$e_\Omega^{(6)} = (y_4+y_5+y_6)-(y_1+y_2+y_3), \qquad e_{V_\pi}^{(6)} = 2(y_2+y_5)-(y_1+y_3+y_4+y_6), \qquad e_{\text{asym}}^{(6)} = (y_1-y_3)+(y_6-y_4)$$
   - **Loop-1/2 Updates, Jury Stability & Scale Factor:**
     $$L_1(z) = \frac{K_{\text{tot},1}}{z^2(z-1)}, \quad 0 < K_{\text{tot},1} < 1, \quad K_{\text{tot},2} \le 0.1\,K_{\text{tot},1}, \qquad \Omega_{\text{out}} = \frac{\Delta\phi_{\text{step}}}{\mathrm{SF}_{\text{CL}}}$$

### 4.3 FMI 3.0 Co-Simulation Wrapper (`fmi_wrapper/` — `build/ifog_core.fmu`, `VR 0..21`)

- **Multi-Rate ZOH Step Alignment & Anti-Aliased Macro-Step Average (`EQ-42`–`EQ-44`):**
  $$N_{\tau,k} = \left\lfloor \frac{t_k + H}{\tau} \right\rfloor - \left\lfloor \frac{t_k}{\tau} \right\rfloor, \qquad \bar{\Omega}_{\text{out},k} = \frac{1}{N_{\tau,k}}\sum_{j=1}^{N_{\tau,k}} \Omega_{\text{out}}[j], \qquad e_{V_\pi,\text{res}} = 2\pi\epsilon_{V_\pi,\text{eff}}$$
- **7 Live Tunable Parasitic Parameters (`VR 15..21`):** `C_xtalk_F`, `G_xtalk_S`, `c_pink_coeff`, `R_facet_dB`, `alpha_vpi_ppm_K`, `alpha_bobbin_ppm_K`, and `delta_z_quad_m` (`canBeInstantiatedOnlyOncePerProcess="true"`, `0.00e+00 rad/s` bit-exact equivalence when untuned).

### 4.4 Tier 3 — Dual-Regime AVAR, Anti-Double-Counting BI & 3-Stage Bounded Inverse Calibration (`tier3_analysis/`)

1. **IEEE Std 952-2020 5-Component Overlapping AVAR & Coherent $\mathbf{K}$-Matrix (`EQ-24`–`EQ-30`, `EQ-40`–`EQ-41`):**
   $$\sigma^2(T_m) = \frac{3Q^2}{T_m^2} + \frac{N^2}{T_m} + \frac{2\ln 2}{\pi}B^2 + \frac{K^2 T_m}{3} + \frac{R^2 T_m^2}{2}$$
2. **Quadrature Anti-Double-Counting BI Stitching (`EQ-52` — `DualRegimeStitcher`):**
   $$B_{\text{T3,mech}} = \sqrt{\max\!\left(0,\; B_{\text{total}}^2 - B_{\text{T2,meas}}^2\right)}$$
3. **3-Stage Bounded Weighted Least-Squares Inverse Calibration & Gauss–Newton 95% CI (`EQ-53` — `InverseCalibrator`):**
   $$\hat{\boldsymbol{\theta}} = \arg\min_{\boldsymbol{\theta}\in[\boldsymbol{\theta}_{\min},\boldsymbol{\theta}_{\max}]} \sum_{m=1}^{M} w_m\,\left\| \frac{\mathbf{y}_{\text{sim},m}(\boldsymbol{\theta}) - \mathbf{y}_{\text{exp},m}}{\boldsymbol{\sigma}_m} \right\|_2^2, \qquad \operatorname{Cov}(\hat{\boldsymbol{\theta}}) \approx \hat{s}^2 \bigl(\mathbf{J}^T \mathbf{J} + \lambda \mathbf{I}\bigr)^{-1}, \qquad \mathrm{CI}_{95\%} = \hat{\theta}_j \pm 1.96\sqrt{[\operatorname{Cov}]_{jj}}$$

---

## 5. Complete 53-Formula White-Box Traceability Matrix (`EQ-01` .. `EQ-53`)

| Formula ID | Spec Ref | Mathematical Scope | Source Code Binding | CI Formula Test |
| :--- | :--- | :--- | :--- | :--- |
| `EQ-01` | SPEC-004 §1 Eq. (1) | 4-state differential bias sequence $\phi_1..\phi_4$ | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_dsp.py::test_eq01_*` |
| `EQ-02` | SPEC-004 §1 Eqs. (2)–(5) | 1st-order Taylor expansion at 4 bias points | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_dsp.py::test_eq02_*` |
| `EQ-03` | SPEC-004 §1 Eq. (6) | Orthogonal demodulation ($e_\Omega, e_{V_\pi}, S_\alpha$) | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_dsp.py::test_eq03_*` |
| `EQ-04` | SPEC-004 §3.1.1 Eq. (7) | Spectral-sliced Jones matrices $\mathbf{J}_{\text{CW}}, \mathbf{J}_{\text{CCW}}$ | `tier1_offline/jones_spectral.py` | `test_formulas_optics.py::test_eq04_*` |
| `EQ-05` | SPEC-004 §3.1.1 Eq. (8) | Fringe visibility $V$ and polarization phase $\phi_{\text{pol}}$ | `tier1_offline/jones_spectral.py` | `test_formulas_optics.py::test_eq05_*` |
| `EQ-06` | SPEC-004 §3.1.2 Eq. (9) | Transit time $\tau$ & total non-reciprocal phase $\Delta\phi_{\text{NR}}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` | `test_formulas_optics.py::test_eq06_*` |
| `EQ-07` | SPEC-004 §3.1.2 Eq. (10a) | Sagnac optical scale factor $K_{\text{opt}}$ | `tier1_offline/jones_spectral.py` | `test_formulas_optics.py::test_eq07_*` |
| `EQ-08` | SPEC-004 §3.1.2 Eq. (10b) | Coherence-weighted optical Kerr phase $\Delta\phi_{\text{Kerr}}$ | `tier1_offline/jones_spectral.py` | `test_formulas_optics.py::test_eq08_*` |
| `EQ-09` | SPEC-004 §3.1.2 Eq. (11) | Thermal Shupe integral with $\delta z_{\text{quad}}$ | `tier1_offline/shupe_thermal.py` | `test_formulas_optics.py::test_eq09_*` |
| `EQ-10` | SPEC-004 §3.1.2 Eq. (12) | Magneto-optic Faraday phase $\Delta\phi_{\text{Faraday}}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` | `test_formulas_optics.py::test_eq10_*` |
| `EQ-11` | SPEC-004 §3.1.2 Eq. (13) | MIOC phase with $\epsilon_{V_\pi}, \gamma_{\text{nl}}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` | `test_formulas_optics.py::test_eq11_*` |
| `EQ-12` | SPEC-004 §3.1.2 Eq. (14) | Differential modulation $\Delta\phi_{\text{mod}}$ & $\operatorname{wrap}_{2\pi}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` | `test_formulas_optics.py::test_eq12_*` |
| `EQ-13` | SPEC-004 §3.1.2 Eq. (15) | Photodiode power $P_{\text{det}}$ with $\alpha_{\text{RAM}}$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` | `test_formulas_optics.py::test_eq13_*` |
| `EQ-14` | SPEC-004 §3.2.1 Eq. (16) | TIA inverting-node current $I_{\text{in}}$ + crosstalk | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` | `test_formulas_analog.py::test_eq14_*` |
| `EQ-15` | SPEC-004 §3.2.1 Eq. (17) | 6-component noise PSD $S_{i,\text{tot}}$ & $\sigma_{i,\text{w}}^2$ | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` | `test_formulas_analog.py::test_eq15_*` |
| `EQ-16` | SPEC-004 §3.2.2 Eqs. (18)–(19) | 2nd-order TIA LTF $H_{\text{TIA}}(s), \omega_0, \zeta$ | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` | `test_formulas_analog.py::test_eq16_*` |
| `EQ-17` | SPEC-004 §3.2.2 Eq. (20) | Butterworth $C_{f,\text{opt}}$ & settling time $t_s(0.1\%)$ | `tier2_sysc_ams/include/ifog_math.hpp` | `test_formulas_analog.py::test_eq17_*` |
| `EQ-18` | SPEC-004 §3.2.3 Eqs. (21)–(22) | TIA $1/f$ offset & cubic polynomial NL + clip | `tier2_sysc_ams/src/analog_frontend_tdf.cpp` | `test_formulas_analog.py::test_eq18_*` |
| `EQ-19` | SPEC-004 §3.2.3 Eq. (23) | ADC blanking $\eta_b$, $N_{\text{ADC}}$ quantizer, $1/\sqrt{\eta_b}$ | `tier2_sysc_ams/src/adc_dac_bridge.cpp` | `test_formulas_analog.py::test_eq19_*` |
| `EQ-20` | SPEC-004 §3.3.1 Eqs. (24)–(27) | 2-state & 4-state Loop-1/Loop-2 integrators | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_dsp.py::test_eq20_*` |
| `EQ-21` | SPEC-004 §3.3.1 Eqs. (28)–(29) | Digital phase ramp $\operatorname{wrap}_{2\pi}$ & PRBS DAC code | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_dsp.py::test_eq21_*` |
| `EQ-22` | SPEC-004 §3.3.2 Eqs. (30)–(31) | $L_1(z)$ Jury stability & Loop-2 separation | `tier2_sysc_ams/include/ifog_math.hpp` | `test_formulas_dsp.py::test_eq22_*` |
| `EQ-23` | SPEC-004 §3.3.2 Eq. (32) | Closed-loop output rate $\Omega_{\text{out}} = \Delta\phi_{\text{step}}/\mathrm{SF}_{\text{CL}}$ | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_dsp.py::test_eq23_*` |
| `EQ-24` | SPEC-004 §3.4 Eq. (33) | IEEE Std 952-2020 5-component AVAR model | `tier3_analysis/dual_regime_avar.py` | `test_formulas_avar_coupling.py::test_eq24_*` |
| `EQ-25` | SPEC-004 §3.4 Eq. (34) | RRW Wiener & 1st-order Gauss–Markov AR(1) | `tier3_analysis/dual_regime_avar.py` | `test_formulas_avar_coupling.py::test_eq25_*` |
| `EQ-26` | SPEC-004 §4.1 Eq. (35) | Phase-to-rate unit conversion ($\text{rad/s} \leftrightarrow ^\circ/\text{h}$) | `tier3_analysis/dual_regime_avar.py` | `test_formulas_avar_coupling.py::test_eq26_*` |
| `EQ-27` | SPEC-004 §4.2 Eq. (36) | Leakage gain matrix $\mathbf{K}$ via $100\text{ Hz}$ FFT | `tier3_analysis/extract_k_matrix.py` | `test_formulas_avar_coupling.py::test_eq27_*` |
| `EQ-28` | SPEC-004 §4.3 Eq. (37) | Slow-scale $10\text{ h}$ / $100\text{ Hz}$ synthesis $\Omega_{\text{slow}}[i]$ | `tier3_analysis/dual_regime_avar.py` | `test_formulas_avar_coupling.py::test_eq28_*` |
| `EQ-29` | SPEC-004 §4.3 Eq. (38) | IEEE Std 952 Overlapping Allan Variance $\sigma^2(T_m)$ | `tier3_analysis/dual_regime_avar.py` | `test_formulas_avar_coupling.py::test_eq29_*` |
| `EQ-30` | SPEC-004 §4.3 Eq. (39) | Dual-regime overlap continuity $< 5\%$ on $[0.1, 5]\text{ s}$ | `tier3_analysis/dual_regime_avar.py` | `test_formulas_avar_coupling.py::test_eq30_*` |
| `EQ-31` | SPEC-005 §2.1 | Official 6-state anti-periodic instantaneous & differential bias phases | `tier2_sysc_ams/include/ifog_math.hpp` | `test_formulas_spec005.py::test_eq31_*` |
| `EQ-32` | SPEC-005 §2.2 | 6-state Taylor expansion & optimal angle $\alpha^*=\pi/3$ ($-33.3\%$ $V_{\text{peak}}$) | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_spec005.py::test_eq32_*` |
| `EQ-33` | SPEC-005 §2.3 | 6-state 3-channel orthogonal demodulation ($e_\Omega^{(6)}, e_{V_\pi}^{(6)}, e_{\text{asym}}^{(6)}$) | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_spec005.py::test_eq33_*` |
| `EQ-34` | SPEC-005 §2.4 | 6-state Loop-1/2 gains, $-3\text{ dB}$ BW & anti-windup clamp | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_spec005.py::test_eq34_*` |
| `EQ-35` | SPEC-005 §4.1 | ADC sampling aperture jitter $\sigma_{V,\text{jit}}$ & RSS ARW penalty | `tier2_sysc_ams/src/adc_dac_bridge.cpp` | `test_formulas_spec005.py::test_eq35_*` |
| `EQ-36` | SPEC-005 §4.2 | Concurrent 3-axis IMU shared-SLD & power-rail PSRR coupling | `tier2_sysc_ams/src/imu_3axis.cpp` | `test_formulas_spec005.py::test_eq36_*` |
| `EQ-37` | SPEC-005 §4.3 | Vibration Rectification Error (VRE) quadratic law $K_{\text{VRE}}g_{\text{rms}}^2$ | `tier2_sysc_ams/src/optical_envelope_tdf.cpp` | `test_formulas_spec005.py::test_eq37_*` |
| `EQ-38` | SPEC-005 §4.3 | Dynamic Faraday sensitivity $S_B$ & Mu-metal shielding $A_{\text{dB}}$ | `tier3_analysis/scenarios_engineering.py` | `test_formulas_spec005.py::test_eq38_*` |
| `EQ-39` | SPEC-005 §4.4 | Real-time FPGA BIT/FDIR 5-fault classification & SEU soft-recovery | `tier2_sysc_ams/src/digital_dsp_sc.cpp` | `test_formulas_spec005.py::test_eq39_*` |
| `EQ-40` | SPEC-005 §4.5 | Monte Carlo production yield, 95% Wilson CI & $C_{pk}$ | `tier3_analysis/scenarios_engineering.py` | `test_formulas_spec005.py::test_eq40_*` |
| `EQ-41` | SPEC-005 §4.5 | $-40..+85^\circ\text{C}$ 2D thermal polynomial & 4-state EKF compensation | `tier3_analysis/scenarios_engineering.py` | `test_formulas_spec005.py::test_eq41_*` |
| `EQ-42` | SPEC-006 §4.1 | FMI 3.0 multi-rate ZOH alignment ($N_{\tau,k}$) & anti-aliased readout $\bar{\Omega}_{\text{out},k}$ | `tier2_sysc_ams/src/ifog_top_module.cpp` | `test_formulas_spec006.py::test_eq42_*` |
| `EQ-43` | SPEC-006 §4.2 | FMI 3.0 Loop-2 residual $V_\pi$ phase error & 6-bit `bit_status` | `tier2_sysc_ams/src/ifog_top_module.cpp` | `test_formulas_spec006.py::test_eq43_*` |
| `EQ-44` | SPEC-006 §4.3 | Black-box FMU vs standalone Tier 2 `< 1e-12 rad/s` equivalence | `fmi_wrapper/src/fmi3_bridge.cpp` | `test_formulas_spec006.py::test_eq44_*` |
| `EQ-45` | SPEC-007 §2.1 *(draft 40)* | Discrete Quadrupole/Octupole coil winding map & $\Delta\phi_{\text{thermo}}$ | `tier1_offline/shupe_thermal.py` | `test_formulas_spec007.py::test_eq45_*` |
| `EQ-46` | SPEC-007 §2.1 *(draft 41)* | Thermo-mechanical elasto-optic stress-optic drift $\Delta\phi_{\text{stress}}(t)$ | `tier1_offline/shupe_thermal.py` | `test_formulas_spec007.py::test_eq46_*` |
| `EQ-47` | SPEC-007 §2.2 *(draft 42)* | Dynamic Sagnac scale factor thermal drift $K_{\text{opt}}(t)$ | `tier1_offline/shupe_thermal.py`, `ifog_math.hpp` | `test_formulas_spec007.py::test_eq47_*` |
| `EQ-48` | SPEC-007 §2.2 *(draft 43)* | Dynamic optical parameters $V_{\text{eff}}(t), \Delta\phi_{\text{pol}}(t), V_\pi(t)$ | `tier1_offline/shupe_thermal.py`, `optical_envelope_tdf.cpp` | `test_formulas_spec007.py::test_eq48_*` |
| `EQ-49` | SPEC-007 §2.3 *(draft 44)* | 6-channel `shupe_lut.bin` v2 (`56 B <7d`) & $O(1)$ interp with v1 fallback | `tier1_offline/shupe_thermal.py`, `ifog_config.cpp` | `test_formulas_spec007.py::test_eq49_*` |
| `EQ-50` | SPEC-007 §2.4 *(draft 45)* | MIOC $\text{LiNbO}_3$ 2nd-order electro-acoustic dynamics before $K_{\text{delay}}$ | `tier2_sysc_ams/include/ifog_math.hpp`, `optical_envelope_tdf.cpp` | `test_formulas_spec007.py::test_eq50_*` |
| `EQ-51` | SPEC-007 §2.5 *(draft 46)* | Capacitive + resistive PCB crosstalk $G_{\text{xtalk}}V + C_{\text{xtalk}}\,dV/dt$ | `tier2_sysc_ams/include/ifog_math.hpp`, `analog_frontend_tdf.cpp` | `test_formulas_spec007.py::test_eq51_*` |
| `EQ-52` | SPEC-007 §2.6 *(draft 47)* | Coherent Rayleigh/facet back-reflection $\sigma_{\phi,\text{back}}$ & quadrature BI stitching | `jones_spectral.py`, `dual_regime_avar.py` | `test_formulas_spec007.py::test_eq52_*` |
| `EQ-53` | SPEC-007 §2.7 *(draft 48)* | 3-Stage bounded Inverse Calibration WLS & Gauss–Newton 95% CI | `tier3_analysis/inverse_calibration.py` | `test_formulas_spec007.py::test_eq53_*` |

---

## 6. Verification, Coverage & CI/CD Governance Architecture

### 6.1 Quantitative Acceptance Results (Verified Real Simulations)
| Acceptance Gate / Metric | Normative Spec Requirement | Verified Result | Status |
| :--- | :--- | :--- | :---: |
| **Quadruple Spec Lock (Rule 7)** | `SPEC-004/005/006/007` SHA-256 unchanged | All 4 verified `OK` + compiled PDFs | **PASS** |
| **Doc–Version Sync (Rule 16)** | `pyproject.toml`, all 3 `docs/*.{md,tex,pdf}`, HTML explorer, `README.md`, Git Tag aligned | Verified via `scripts/verify_doc_sync.py` | **PASS** |
| **C++ Line & Function Coverage** | `100.0%` via `gcovr --fail-under-line 100` (`tier2` + `fmi_wrapper`) | `100.0%` (`2,329/2,329` lines, `211/211` functions) | **PASS** |
| **Python Line Coverage** | `100.0%` via `pytest-cov` (`fail_under = 100`) | `100.00%` (`4,650/4,650` stmts across `tier1`, `tier3`, `viz`) | **PASS** |
| **Per-Formula Verification (Rule 3)** | All 53 equations (`EQ-01`..`EQ-53`) independently pass | `53 / 53` PASSED | **PASS** |
| **Gate 1 — Golden Linear & Flyback** | Static err $< 10^{-9}\text{ rad}$, flybacks $> 1000$, $\epsilon_{V_\pi,\text{eff}} < 10^{-5}$ | `3.10e-16 rad`, `1,666` wraps, `5.84e-14` | **PASS** |
| **Gate 2 — Deadband & Bunny Ears** | $\ge 90\%$ reduction across $[-0.5, +0.5]^\circ/\text{s}$ | `98.85%` reduction on both metrics | **PASS** |
| **Gate 3 — $1/f$ Flicker & $\mathbf{K}$-Matrix** | Linear slope $\approx 0$, nonlinear slope $\in [-1.25, -0.75]$, $\mathbf{K}$ repeat $< 2\%$ | `-0.062` linear vs `-0.893` nonlinear, `0.000%` repeat | **PASS** |
| **Gate 4 — Dual-Regime 5-Region AVAR** | Real $60\text{ s}$ Fast + $10\text{ h}$ Slow, overlap $< 5\%$, WLS $(Q,N,B,K,R)$ within $\pm 10\%$ | Overlap `2.42% < 5%`; all 5 WLS params within $\pm 10\%$ | **PASS** |
| **Gate 5 — Official 6-State DSP** | Static err $< 10^{-9}\text{ rad}$, $-33.3\%$ $V_{\text{peak}}$, $> 40\text{ dB}$ RAM/xtalk rejection | `1.28e-16 rad`, **`+136.94 dB`** rejection (`7.03e6×`) | **PASS** |
| **Gate 6 — FMI 3.0 Tunable FMU** | 0 XSD errors, `<1e-12` equiv, live `VR 15..21`, deadband $\ge 90\%$, AVAR $<5\%$ | `0` XSD, `0.00e+00 rad/s`, `97.42%` deadband, `3.83%` AVAR | **PASS** |
| **Group A — 6 Time-Domain (`TD-01..06`)** | Blanking, Step/Bode BW, $V_\pi$ shock, 700°/s + anti-windup, Shupe, Limit Cycles | `6 / 6` PASSED (BW `2,540 Hz`, Shupe `99.74%`, `7,184` wraps) | **PASS** |
| **Group B — 5 Engineering (`ENG-01..05`)** | BOM sizing, 3-axis IMU, VRE/Faraday, 5-fault BIT/FDIR, MC $C_{pk}$ + Cal | `5 / 5` PASSED (IMU `+51.6 dB`, BIT $\le 30\ \mu\text{s}$, Yield `97.2%`) | **PASS** |
| **Group C — 4 Dynamic Probe (`DYN-01..04`)** | Step, 15-pt Bode M/P/GD, Output PSD/ASD, Sine internal electro-optic chain | `4 / 4` PASSED (4s `2,544 Hz`, 6s `1,642 Hz`, THD `-67.5 dB`) | **PASS** |
| **Group D — `SPEC-007` (`PHY-01`, `CAL-01`)** | Octupole/stress/LUT v2/MIOC+$C_{\text{xtalk}}$ + 3-Stage Inverse Calibration `< 5%` | `2 / 2` PASSED (Oct `-47.69%`, Calib `0.04–0.91%`, 10 params `<= 2.18%`) | **PASS** |

### 6.2 Strict 2-Branch CI/CD & Gated SemVer Release Architecture
- **Git Policy (Rule 1):** Only `main` and `dev` exist locally and on `origin`. All changes develop on `dev`, pass full CI (`.github/workflows/ci.yml`), and merge `dev -> main` via Pull Request without deleting `dev`.
- **Release Pipeline (Rules 8 & 16):** Pushing annotated SemVer tag `vX.Y.Z` on `main` triggers `.github/workflows/release.yml`, which verifies SemVer format, `main` ancestry, quadruple spec SHA-256 locks, **Rule 16 document–version sync (`--expected-tag vX.Y.Z` across all 3 PDFs + HTML explorer)**, 100% C++/Python coverage, 53 formulas, and all Gate 1–6 + 17-scenario system simulations before publishing GitHub Release `vX.Y.Z` with all **20 release artifacts**.

---

## 6. Portable Linux Source Toolchain, OCI Containers & Curated Example

### 6.1 Distro-Independent Source Build (`scripts/setup_env.sh`)
To eliminate OS package lock-in (e.g., Ubuntu-only `libsystemc-dev`), `scripts/setup_env.sh` builds all native and Python dependencies deterministically from pinned Git sources into a self-contained prefix (`/opt/ifog-env` as root or `~/.local/ifog-env` rootless):
1. **Accellera SystemC 2.3.4** (`scripts/install_systemc.sh` -> `https://github.com/accellera-official/systemc.git` tag `2.3.4`, CMake C++17 shared library, normalized `lib/` & `lib-linux64` symlink).
2. **SystemC-AMS PoC 2.3.4** (`scripts/install_systemc_ams.sh` -> pinned commit `a72d365f`, past-ordered autotools timestamps & multi-distro staging view).
3. **`nlohmann/json` v3.11.3** (auto-installed from Git when absent from `/usr/include`).
4. **Isolated Python 3 virtual environment** (`<prefix>/venv`) with all runtime & test packages + editable `ifog-vproto`.
5. **Portable Environment Activator** (`<prefix>/env.sh` & tracked `scripts/env.sh`) setting `SYSTEMC_HOME`, `SYSTEMC_AMS_HOME`, `CMAKE_PREFIX_PATH`, `LD_LIBRARY_PATH`, `PKG_CONFIG_PATH`, `VIRTUAL_ENV`, and `PATH`.

### 6.2 Dual Docker / Podman Container Suite
- [`Containerfile`](../Containerfile) and byte-identical [`Dockerfile`](../Dockerfile) build the full ready-to-run `ifog-vproto` environment (including pre-compiled `build/ifog_sim`) with layer-cached C++ and Python dependencies.
- [`compose.yaml`](../compose.yaml) and [`scripts/container_run.sh`](../scripts/container_run.sh) support both Docker and rootless SELinux Podman (`:Z`, `--userns=keep-id`) with `build`, `shell`, `sim`, `example`, `test`, and `verify` subcommands.

### 6.3 Curated Real 4-Gate Feasibility Example (`examples/full_4gate_baseline/`)
- Commits the complete verified output of `./examples/run_example.sh` (`report.md`, `report.html`, `metrics_summary.json`, all Tier 1–3 JSON summaries, and all 4 300-DPI diagnostic figures) directly in the repository for zero-setup technical feasibility evaluation.

---

## 7. Reproducible Simulation, Container & Verification Commands

```bash
# 1. Option A — Zero-dependency Docker / Podman workflow
./scripts/container_run.sh build
./scripts/container_run.sh sim --mode dsp6_compare --run-id container_dsp6
./scripts/container_run.sh sim --mode td_all --run-id container_td

# 2. Option B — Portable native Linux setup (Ubuntu, Fedora, RHEL/Rocky, Arch, HPC)
bash scripts/setup_env.sh --with-system-deps --build-tier2 --verify
source scripts/env.sh
./scripts/run_all_scenarios.sh --run-id complete_v2_0_0 --mc-runs 500

# 3. Verify Rule 16 document-version synchronization & rebuild all 3 PDF docs
bash scripts/build_docs.sh
python3 scripts/verify_doc_sync.py

# 4. Run full local CI gates (Dual Spec Lock, C++ 100%, 41 Formulas, Python 100%, All System Scenarios)
sha256sum -c spec/IFOG-SIM-SPEC-004.sha256 spec/IFOG-SIM-SPEC-005.sha256
bash scripts/run_cpp_coverage.sh
python3 scripts/verify_formulas_ci.py
pytest tests/unit tests/formula_verification --cov --cov-report=term-missing
pytest tests/system -v
```
