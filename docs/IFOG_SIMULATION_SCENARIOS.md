# Closed-Loop IFOG Virtual Prototype — Official Simulation Scenarios & 6-State DSP Guide

## Document Control Metadata

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-VPROTO-SCEN-001` |
| **Current Version** | `v2.0.0` |
| **Status** | `RELEASED (Production Gate Verified)` |
| **Normative Specification** | [`spec/IFOG-SIM-SPEC-005.tex`](../spec/IFOG-SIM-SPEC-005.tex) & [`spec/IFOG-SIM-SPEC-005.pdf`](../spec/IFOG-SIM-SPEC-005.pdf) (v5.0); [`spec/IFOG-SIM-SPEC-004.tex`](../spec/IFOG-SIM-SPEC-004.tex) (v4.0) |
| **Architecture Reference** | [`docs/IFOG_VPROTO_ARCHITECTURE.md`](IFOG_VPROTO_ARCHITECTURE.md) / [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](IFOG_VPROTO_ARCHITECTURE.pdf) |
| **Governance Authority** | [`AGENT.md`](../AGENT.md) (Rules 1–16) |
| **LaTeX / PDF Companion** | [`docs/IFOG_SIMULATION_SCENARIOS.tex`](IFOG_SIMULATION_SCENARIOS.tex) / [`docs/IFOG_SIMULATION_SCENARIOS.pdf`](IFOG_SIMULATION_SCENARIOS.pdf) |

## Document Version & Revision History

| Version | Release Date | Milestone / Gate | Affected Modules / Scope | Detailed Summary of Changes |
| :--- | :--- | :--- | :--- | :--- |
| `v2.0.0` | `2026-11-25` | `IFOG-SIM-SPEC-005` Official 6-State DSP & 11 Official Scenarios | `spec/IFOG-SIM-SPEC-005.*`, `configs/schema_v5.json`, `configs/baseline_1km_6state.json`, `tier2_sysc_ams/` (`digital_dsp_sc`, `imu_3axis`, `optical_envelope_tdf`, `analog_frontend_tdf`, `adc_dac_bridge`), `tier3_analysis/scenarios_time_domain.py`, `tier3_analysis/scenarios_engineering.py`, `tier3_analysis/sim_runner_cli.py`, `viz/plot_scenarios.py`, `viz/export_report.py`, `scripts/run_all_scenarios.sh` | Initial release of the Official Simulation Scenarios & 6-State Symmetric DSP specification manual covering Gate 5 (`EQ-31`–`EQ-34`), 6 Time-Domain scenarios (`TD-01`..`TD-06`), 5 System Engineering & Production scenarios (`ENG-01`..`ENG-05`, `EQ-35`–`EQ-41`), unified individual & batch CLI orchestration, and verified real-simulation benchmarks. |

---

## 1. Official Scenario Taxonomy & Execution Architecture

Under **`IFOG-SIM-SPEC-005` (v5.0)**, `ifog-vproto` elevates its verification suite from the 4 foundational SPEC-004 acceptance gates to a complete **4-Layer Official Simulation Framework** organized cleanly by engineering domain:

1. **Core Acceptance Gates (`Gate 1` – `Gate 4`):** Baseline linear accuracy & continuous $2\pi$ flyback (`gate1`), Deadband & Bunny Ears mitigation (`gate2`), $1/f$ Flicker PSD & $100\text{ Hz}$ $\mathbf{K}$-matrix (`gate3`), and 60 s Fast-Scale + 10 h Slow-Scale Dual-Regime Overlapping AVAR (`gate4`), combined under `--mode full`.
2. **Gate 5 — Official 6-State Symmetric DSP Benchmark (`dsp6_compare`):** Head-to-head quantitative validation of the official 6-state symmetric modulation/demodulation law (`EQ-31`–`EQ-34`, $\alpha^* = \pi/3$) against 4-state Lefèvre modulation under identical RAM, capacitive/resistive crosstalk, and MIOC quadratic nonlinearity.
3. **Group A — 6 Time-Domain Verification Scenarios (`TD-01` .. `TD-06`, `--mode td_all`):** Exploits Tier 2's micro-trace (`micro_waveforms.bin`, 64 B) and cycle-accurate DSP register logger (`dsp_trace.bin`, 64 B) without modifying the underlying physical core to validate sub-$\tau$ switching transients, closed-loop step/Bode bandwidth, Loop-2 thermal $V_\pi$ shock, high-rate serrodyne dynamics + anti-windup, real-time Shupe shock + compensation, and quantization limit cycles + PRBS dither.
4. **Group B — 5 System Engineering & Production Scenarios (`ENG-01` .. `ENG-05`, `--mode eng_all`):** Leverages the `-O3` compiled C++ SystemC-AMS virtual prototype for production hardware sizing (ENOB, aperture jitter, TIA/SLD Pareto), real concurrent 3-axis SystemC-AMS IMU crosstalk (`--imu3axis`), vibration rectification (VRE) + dynamic Faraday/Mu-metal sizing, 5-mode real-time FPGA BIT/FDIR fault injection, and parallel Monte Carlo production yield ($C_{pk}$) + $-40^\circ\text{C}..+85^\circ\text{C}$ virtual thermal calibration.

```mermaid
flowchart TB
    CLI["Unified CLI Entrypoints\n./scripts/run_sim.sh --mode <mode>\n./scripts/run_all_scenarios.sh"]

    subgraph CORE["Core Gates (SPEC-004)"]
        G1["gate1..gate4 / full\n(Gates 1–4 + 10 h AVAR)"]
    end

    subgraph G5["Gate 5 — Official 6-State DSP"]
        DSP6["dsp6_compare\n(4-state vs 6-state EQ-31..34)"]
    end

    subgraph TDG["Group A — 6 Time-Domain Scenarios (td_all)"]
        TD1["td_blanking (TD-01)\nSub-tau & ADC Blanking"]
        TD2["td_step_sine (TD-02)\nStep & -3 dB Bode BW"]
        TD3["td_vpi_shock (TD-03)\nLoop-2 +5% V_pi Shock"]
        TD4["td_high_rate (TD-04)\n300–700 deg/s & Anti-Windup"]
        TD5["td_shupe_shock (TD-05)\nReal-Time Shupe & Filter"]
        TD6["td_limit_cycles (TD-06)\nIdle Tones & PRBS Dither"]
    end

    subgraph ENGG["Group B — 5 System Engineering Scenarios (eng_all)"]
        E1["eng_hw_sizing (ENG-01)\nENOB / Jitter / TIA-SLD"]
        E2["eng_imu_3axis (ENG-02)\n3-Axis Shared-SLD IMU"]
        E3["eng_vre_faraday (ENG-03)\nVRE & Faraday / Mu-Metal"]
        E4["eng_fault_bit (ENG-04)\n5 Faults & FPGA BIT/FDIR"]
        E5["eng_mc_yield_cal (ENG-05)\nMC Yield C_pk & -40..+85C Cal"]
    end

    CLI --> CORE
    CLI --> G5
    CLI --> TDG
    CLI --> ENGG

    CORE --> RPT["Automatic Reporting (viz/export_report.py)\nreport/<run_id>/{report.md, report.html, figures/*.png,\nmetrics_summary.json, virtual_calibration_dataset.csv}\n+ report/index.{md,html}"]
    G5 --> RPT
    TDG --> RPT
    ENGG --> RPT
```

---

## 2. Official CLI Execution Matrix (Individual & Full-Suite Commands)

Every single scenario can be run independently with one CLI command, by category group, or all together via `./scripts/run_all_scenarios.sh`. All runs automatically build `build/ifog_sim` (if absent) and export complete Markdown (`report.md`), interactive HTML (`report.html`), 300-DPI PNG figures, and JSON summaries under `report/<run_id>/`.

| Scope | Scenario ID | CLI Mode (`--mode`) | Equations | Official Reproducible Command |
| :--- | :--- | :--- | :--- | :--- |
| **Complete Suite** | All Gates + 11 Scenarios | `all_scenarios` | `EQ-01`–`EQ-41` | `./scripts/run_all_scenarios.sh --run-id full_spec005 --mc-runs 500` |
| **Core 4 Gates** | Gates 1–4 | `full` (`gate1`..`gate4`) | `EQ-01`–`EQ-30` | `./scripts/run_sim.sh --mode full --run-id core_4gates` |
| **Gate 5 (6-State)** | `DSP-6` | `dsp6_compare` | `EQ-31`–`EQ-34` | `./scripts/run_sim.sh --mode dsp6_compare --run-id gate5_6state` |
| **Group A (All TD)** | `TD-01`..`TD-06` | `td_all` | `EQ-09,16,19,21,31..34` | `./scripts/run_sim.sh --mode td_all --run-id td_suite` |
| **TD Scenario 1** | `TD-01` | `td_blanking` | `EQ-16,17,19` | `./scripts/run_sim.sh --mode td_blanking --run-id td01` |
| **TD Scenario 2** | `TD-02` | `td_step_sine` | `EQ-22,23,34` | `./scripts/run_sim.sh --mode td_step_sine --run-id td02` |
| **TD Scenario 3** | `TD-03` | `td_vpi_shock` | `EQ-03,20,33,34` | `./scripts/run_sim.sh --mode td_vpi_shock --run-id td03` |
| **TD Scenario 4** | `TD-04` | `td_high_rate` | `EQ-12,21,34` | `./scripts/run_sim.sh --mode td_high_rate --run-id td04` |
| **TD Scenario 5** | `TD-05` | `td_shupe_shock` | `EQ-09,26` | `./scripts/run_sim.sh --mode td_shupe_shock --run-id td05` |
| **TD Scenario 6** | `TD-06` | `td_limit_cycles` | `EQ-19,21` | `./scripts/run_sim.sh --mode td_limit_cycles --run-id td06` |
| **Group B (All ENG)** | `ENG-01`..`ENG-05` | `eng_all` | `EQ-35`–`EQ-41` | `./scripts/run_sim.sh --mode eng_all --run-id eng_suite --mc-runs 500` |
| **ENG Scenario 1** | `ENG-01` | `eng_hw_sizing` | `EQ-15,17,19,35` | `./scripts/run_sim.sh --mode eng_hw_sizing --run-id eng01` |
| **ENG Scenario 2** | `ENG-02` | `eng_imu_3axis` | `EQ-36` | `./scripts/run_sim.sh --mode eng_imu_3axis --run-id eng02` |
| **ENG Scenario 3** | `ENG-03` | `eng_vre_faraday` | `EQ-10,18,37,38` | `./scripts/run_sim.sh --mode eng_vre_faraday --run-id eng03` |
| **ENG Scenario 4** | `ENG-04` | `eng_fault_bit` | `EQ-39` | `./scripts/run_sim.sh --mode eng_fault_bit --run-id eng04` |
| **ENG Scenario 5** | `ENG-05` | `eng_mc_yield_cal` | `EQ-40,41` | `./scripts/run_sim.sh --mode eng_mc_yield_cal --run-id eng05 --mc-runs 500` |

Additional CLI flags available across modes:
- `--dsp-mode {2state,4state,6state}`: Override DSP modulation architecture from the command line (or pass `--cfg configs/baseline_1km_6state.json`).
- `--mc-runs N`: Set Monte Carlo production population size for `eng_mc_yield_cal` / `eng_all` / `all_scenarios` (default `64`, production campaign `500`+).
- `--workers W`: Override parallel worker thread/process pool size.

---

## 3. Gate 5 — Official 6-State Symmetric DSP Modulation & Demodulation (`EQ-31`–`EQ-34`)

### 3.1 Physical Motivation & Mathematical Formulation
Standard 4-state Lefèvre modulation (`configs/baseline_1km.json`) has an asymmetric instantaneous bias sequence $\psi^{(4)} = [+\pi, +\alpha, -\pi, +\alpha]$ with nonzero mean $\bar{\psi}^{(4)} = \alpha/2$ and peak swing $|\psi| = \pi$ ($V_{\text{peak}} = V_\pi$). Under Residual Amplitude Modulation ($\alpha_{\text{RAM}}$), resistive/capacitive DAC-to-TIA crosstalk ($k_{\text{xtalk}}, C_{\text{xtalk}}$), or quadratic MIOC phase distortion ($\gamma_{\text{nl}} V^2$), this asymmetry rectifies into an uncancelled DC rotation-rate bias.

`IFOG-SIM-SPEC-005` establishes an **official anti-periodic 6-state symmetric modulation sequence** (`configs/baseline_1km_6state.json`, `dsp.mode = "6state"`):

1. **Instantaneous Bias Phase (`EQ-31`):**
   $$\psi^{(6)} = \left[+\frac{\pi+\alpha}{2},\; -\frac{\pi+\alpha}{2},\; +\frac{\pi-3\alpha}{2},\; -\frac{\pi+\alpha}{2},\; +\frac{\pi+\alpha}{2},\; -\frac{\pi-3\alpha}{2}\right]$$
   Properties: exact half-period anti-periodicity $\psi_{s+3} = -\psi_s$, **zero DC drive mean** ($\sum_{s=1}^{6}\psi_s = 0$), and exact differential coil phases $\phi_s = \psi_s - \psi_{s-1}$:
   $$\phi^{(6)} = \bigl[+(\pi-\alpha),\; -(\pi+\alpha),\; +(\pi-\alpha),\; -(\pi-\alpha),\; +(\pi+\alpha),\; -(\pi-\alpha)\bigr]$$
2. **Optimal Angle $\alpha^* = \pi/3$ (`EQ-32`):**
   At $\alpha^* = \pi/3$ ($60^\circ$), $\psi_3 = \psi_6 = 0$ and the instantaneous drive sequence reduces to the compact 3-level pattern $\bigl[+\tfrac{2\pi}{3}, -\tfrac{2\pi}{3}, 0, -\tfrac{2\pi}{3}, +\tfrac{2\pi}{3}, 0\bigr]$. Peak MIOC drive voltage drops by **33.3%** ($\frac{2}{3}V_\pi$ vs $V_\pi$), while the odd-symmetric sum eliminates linear RAM, resistive crosstalk, capacitive crosstalk, and quadratic MIOC distortion identically to zero in the rate channel.
3. **3-Channel Orthogonal Demodulation (`EQ-33`):**
   From the 6 blanking-averaged ADC samples $y_1..y_6$ per frame ($T_{\text{frame}} = 6\tau \approx 29.38\ \mu\text{s}$), `DigitalDSP_SC` computes three mutually orthogonal channels ($\mathbf{w}_\Omega \perp \mathbf{w}_{V_\pi} \perp \mathbf{w}_{\text{asym}} \perp \mathbf{1}$):
   $$e_\Omega^{(6)} = (y_4 + y_5 + y_6) - (y_1 + y_2 + y_3) = 6 S_\alpha\,\Delta\phi_{\text{NR}}$$
   $$e_{V_\pi}^{(6)} = 2(y_2 + y_5) - (y_1 + y_3 + y_4 + y_6) = 8\pi S_\alpha\,\epsilon_{V_\pi}$$
   $$e_{\text{asym}}^{(6)} = (y_1 - y_3) + (y_6 - y_4) \quad \text{(online RAM / crosstalk / TIA-settling health monitor)}$$
4. **Loop-1 Integrator with Anti-Windup & Loop-2 Update (`EQ-34`):**
   $$\Delta\phi_{\text{step}}[n+1] = \operatorname{clamp}\!\left(\Delta\phi_{\text{step}}[n] + K_{I1}^{(6)} e_\Omega^{(6)}[n],\; -\Delta\phi_{\max},\; +\Delta\phi_{\max}\right), \quad G_{\text{DAC}}[n+1] = \operatorname{clamp}\!\left(G_{\text{DAC}}[n] - K_{I2}^{(6)} e_{V_\pi}^{(6)}[n],\; 0.5,\; 2.0\right)$$

### 3.2 Verified Benchmark Results (`./scripts/run_sim.sh --mode dsp6_compare`)

| Metric | 4-State Lefèvre ($\alpha = \pi/4$) | Official 6-State Symmetric ($\alpha^* = \pi/3$) | Engineering Improvement |
| :--- | :---: | :---: | :---: |
| Peak MIOC Bias Voltage | $1.000\,V_\pi$ | **$0.667\,V_\pi$** | **$-33.3\%$ drive voltage** |
| Golden Linear Static Phase Error | `7.72e-17 rad` | **`1.28e-16 rad`** | Both $< 10^{-9}\text{ rad}$ (**PASS**) |
| Loop-2 Residual $\epsilon_{V_\pi,\text{eff}}$ | `2.44e-15` | **`1.31e-11`** | Both $< 10^{-5}$ (**PASS**) |
| RAM + Crosstalk + $\gamma_{\text{nl}}$ Induced Bias | `354.56 deg/h` | **`5.04e-5 deg/h`** | **`7.03 × 10⁶×` (`+136.94 dB` rejection)** |
| Online Asymmetry Monitor $e_{\text{asym}}$ RMS | *(Not available in 4-state)* | **`169.87 counts`** | Real-time impairment detection |

---

## 4. Group A — 6 Time-Domain Simulation Scenarios (`TD-01` .. `TD-06`)

All 6 scenarios operate directly on the unmodified Tier 2 physical core (`OpticalEnvelope_TDF` + `AnalogFrontEnd_TDF` + `ADC_DAC_Bridge` + `DigitalDSP_SC`), unlocking sub-$\tau$ logging (`micro_waveforms.bin`, 64 B) and cycle-accurate DSP register logging (`dsp_trace.bin`, 64 B: `t, omega_in, omega_out, phi_ramp, delta_phi_step, g_dac, adc_code, dac_code, prbs_bit, bit_fault_code, flags`).

### TD-01 — Sub-$\tau$ Switching Transient & ADC Blanking Alignment (`--mode td_blanking`)
- **Objective:** Inspect sub-$\tau$ nanosecond-scale waveforms ($P_{\text{det}}(t)$, $V_{\text{TIA}}(t)$, $V_{\text{drv}}(t)$, `ADC_strobe`) across 4-state/6-state transitions and $2\pi$ flyback spikes; determine the exact minimum blanking index $k_{\text{start}}^*$ so the ADC never samples switching ringing while minimizing the ARW blanking penalty $1/\sqrt{\eta_b}$ (`EQ-19`).
- **Implementation:** Runs `ifog_sim` with `K = 32` ($\Delta t_{\text{fast}} \approx 153\text{ ns}$), `en_ltf_transient = true`, `dump_micro_ms = 0.08`, sweeps candidate $k_{\text{start}} \in [0, 12]$ against steady-state plateau error, and compares against analytical Butterworth settling time $t_s(0.1\%)$ (`EQ-17`).
- **Verified Measured Result:** TIA $t_s(0.1\%) = 174.1\text{ ns}$, optimal clean blanking start $k_{\text{start}}^* = 5$ (settling error drops from `2.978%` at $k=4$ to `< 0.5%` at $k=5$), ARW blanking factor $\times 1.155$ (**PASS**).

### TD-02 — Closed-Loop Step Response & Dynamic $-3\text{ dB}$ Bandwidth (`--mode td_step_sine`)
- **Objective:** Measure closed-loop transient tracking (rise time $t_r$, settling time $t_s$, overshoot, steady-state error) to a $0 \to 100^\circ/\text{s}$ rate step and extract closed-loop Bode magnitude/phase & $-3\text{ dB}$ bandwidth via multi-frequency sinusoidal excitation $\Omega_{\text{in}}(t) = \Omega_0 \sin(2\pi f t)$.
- **Methodology:** Tier 2 `eval_stimulus()` injects exact step (`t_step = 2.0 ms`, `100 deg/s`) and coherent sine tones ($f \in [50\text{ Hz}..9\text{ kHz}]$). Measured $-3\text{ dB}$ bandwidth is cross-checked against the exact 1st-order frame-integrator closed-loop transfer function $T_1(z_f) = K_{\text{tot}}/[z_f - (1-K_{\text{tot}})]$ (`EQ-34`).
- **Verified Measured Result:** Step $t_r = 0.22\text{ ms}$, overshoot `0.008%`, steady-state error `2.66e-7%`; measured $-3\text{ dB}$ BW = **`2,540 Hz`** vs analytical theory **`2,354 Hz`** (`7.8%` match, **PASS**).

### TD-03 — Loop-2 $V_\pi$ Gain-Lock Transient Under $+5\%$ Thermal Shock (`--mode td_vpi_shock`)
- **Objective:** Inject a sudden $+5\%$ step in MIOC half-wave voltage error $\epsilon_{V_\pi}: 0\% \to +5\%$ at $t = 3.0\text{ ms}$ during steady rotation ($\Omega_{\text{in}} = 10^\circ/\text{s}$); verify Loop-2 convergence of $G_{\text{DAC}}(t) \to 1/1.05 = 0.95238$ and confirm minimal cross-coupling disturbance to Loop-1 Sagnac rate output $\Omega_{\text{out}}(t)$ for both 4-state and 6-state DSP.
- **Verified Measured Result:**
  - **4-State:** Converges to $\epsilon_{V_\pi,\text{eff}} = 1.78\times 10^{-15}$ in `4.2 ms`; Loop-1 transient peak = `0.535 deg/s`.
  - **6-State:** Converges to $\epsilon_{V_\pi,\text{eff}} = 1.68\times 10^{-11}$ in `6.3 ms`; Loop-1 transient peak = **`0.269 deg/s`** (**2× lower cross-coupling**, **PASS**).

### TD-04 — High-Rate Dynamics ($300\text{–}700^\circ/\text{s}$), $2\pi$ Serrodyne Flyback & Anti-Windup (`--mode td_high_rate`)
- **Objective:** Verify high-rate serrodyne digital ramp generation and rapid modulo-$2\pi$ flyback resets at $300^\circ/\text{s}$, $500^\circ/\text{s}$, and $700^\circ/\text{s}$ without fringe-slip errors, plus explicit Loop-1 integrator anti-windup clamping (`FLAG_ANTI_WINDUP`, `EQ-34`) when commanded rate exceeds `max_rate_rad_per_s`.
- **Verified Measured Result:** Zero fringe slips across $300/500/700^\circ/\text{s}$; at $700^\circ/\text{s}$, RMS tracking error = **`0.00028%`** across **`7,184` wraps (`179.6 kHz` reset rate)**; anti-windup clamp holds output cleanly at `300.000 deg/s` with `200` `FLAG_ANTI_WINDUP` events logged (**PASS**).

### TD-05 — Real-Time Thermal Shupe Shock & Extrapolative Compensation Filter (`--mode td_shupe_shock`)
- **Objective:** Inject a rapid thermal boundary ramp shock ($\dot{T} = 2.0\text{ K/s}$ with $1.0\text{ K/s}$ coil asymmetry) via Tier 1 Crank–Nicolson FEM (`shupe_lut.bin`) into Tier 2 real-time execution and verify an extrapolative thermal-gradient compensation filter $\hat{\Omega}_{\text{comp}}(t) = \Omega_{\text{out}}(t) - \hat{c}_{\text{shupe}}\dot{T}_{\text{diff}}(t)$.
- **Verified Measured Result:** Real-time Shupe drift peaks at **`1,483.61 deg/h`** with correlation **`r = 0.99998`** against Tier 1 physics; extrapolative thermal filter reduces drift by **`99.74%`** (`3.85 deg/h` residual, **PASS**).

### TD-06 — Quantization Limit Cycles (Idle Tones) & PRBS Dither Spectral Purity (`--mode td_limit_cycles`)
- **Objective:** Observe integer `adc_code[n]`, `dac_code[n]`, and `prbs_bit[n]` registers at near-zero input rate ($\Omega_{\text{in}} = 0.005^\circ/\text{s}$) with 12-bit ADC/DAC quantization to detect parasitic deadband lock / limit cycles (idle tones) and quantify PRBS dither decorrelation & spectral whitening.
- **Verified Measured Result:** Without dither, 12-bit quantization traps DAC output in only **`3` unique codes** (deadband lock); enabling reflected 16-bit LFSR PRBS dither unlocks **`1,595` unique DAC codes** and restores linear small-rate tracking (**PASS**).

---

## 5. Group B — 5 System Engineering & Production Scenarios (`ENG-01` .. `ENG-05`)

### ENG-01 — Hardware Sizing & Component Cost Trade-Off (`--mode eng_hw_sizing`, `EQ-35`)
- **Methodology:** Executes three automated Tier 2 sweeps to determine the minimum-cost BOM meeting tactical gyro specifications:
  1. **ADC/DAC ENOB Sweep (`10, 12, 14, 16`-bit):** Measures quantization deadband & ARW degradation to locate the exact minimum passing bit depth.
  2. **ADC Sampling Aperture Jitter Sweep (`0, 20, 100, 1000, 10000 ps`):** Injects Gaussian sample-time jitter $\delta t_j \sim \mathcal{N}(0, \sigma_{t,\text{jit}}^2)$ into `ADC_Bridge_TDF2DE` (`EQ-35`: $\sigma_{V,\text{jit}} = |dV/dt|\sigma_{t,\text{jit}}$, $\text{ARW}_{\text{tot}} = \sqrt{\text{ARW}_0^2 + \text{ARW}_{\text{jit}}^2}$) to specify PCB oscillator jitter limits.
  3. **TIA $(R_f, C_{f,\text{opt}})$ vs SLD Power $P_0$ Pareto Grid:** Evaluates $3\times 3$ combinations of $R_f \in \{10, 20, 50\}\text{ k}\Omega$ and $P_0 \in \{2, 5, 10\}\text{ mW}$, trading thermal noise vs RIN vs settling time $t_s(0.1\%)$.
- **Verified Measured Result:** Minimum passing ADC/DAC resolution = **`12-bit`**; aperture jitter elevates ARW monotonically (`+2,216.3%` at `10 ns`); Pareto-optimal operating point achieves **`1.412e-4 deg/rt-h`** (**PASS**).

### ENG-02 — 3-Axis IMU Shared-SLD & Shared-Rail Inter-Axis Crosstalk (`--mode eng_imu_3axis`, `EQ-36`)
- **Architecture:** Executes `./build/ifog_sim --imu3axis` (`tier2_sysc_ams/src/imu_3axis.cpp`), instantiating **three complete concurrent IFOG axes (`Axis_X`, `Axis_Y`, `Axis_Z`)** inside a single IEEE Std 1666.1 SystemC-AMS simulation coupled via `SharedPowerBus_TDF`:
  $$P_{\text{SLD,scale}}[n] = 1 - \eta_{\text{back}}\sum_{a\in\{X,Y,Z\}} \left|\Delta V_{\text{drv},a}[n]\right| / V_\pi, \qquad \Delta V_{\text{rail}}[n] = R_{\text{rail}} \sum_{a\in\{X,Y,Z\}} I_{\text{drv},a}[n]$$
  When Axis X rotates rapidly at **$500^\circ/\text{s}$** (generating continuous $2\pi$ flyback spikes), `SharedPowerBus_TDF` propagates instantaneous SLD back-reflection droop and power-rail droop ($\text{PSRR} = -40\text{ dB}$ into TIA and DAC rails) into stationary Axis Y and Axis Z.
- **Verified Measured Result:** Peak shared-rail droop = **`92.4 mV`**; stationary Axis-Y inter-axis crosstalk bias drops from **`40.63 deg/h`** (4-state DSP) down to **`0.106 deg/h`** (official 6-state DSP — **`+51.6 dB` inter-axis crosstalk rejection**, **PASS**).

### ENG-03 — Vibration Rectification Error (VRE) & Dynamic Faraday / Mu-Metal Sizing (`--mode eng_vre_faraday`, `EQ-37`, `EQ-38`)
- **Methodology:**
  1. **VRE (`EQ-37`):** Injects sinusoidal mechanical vibration $a_{\text{vib}}(t) = \sqrt{2}g_{\text{rms}}\sin(2\pi f_{\text{vib}} t)$ ($f_{\text{vib}} = 1{,}500\text{ Hz}$, $g_{\text{rms}} \in [0, 2, 4, 6, 8]\ g$) modulating optical loss and coil phase into `OpticalEnvelope_TDF`. Quadratic TIA nonlinearity $G_2 V^2$ rectifies AC vibration into a DC bias $\Delta\Omega_{\text{VRE}} = K_{\text{VRE}}\,g_{\text{rms}}^2$, extracted via Hann-windowed DC averaging.
  2. **Dynamic Faraday & Mu-Metal Shielding (`EQ-38`):** Sweeps external magnetic field $B_{\text{ext}} \in [-5, -2, 0, +2, +5]\text{ G}$ ($1\text{ G} = 10^{-4}\text{ T}$), validates measured sensitivity $S_B$ against analytical $V_{\text{Verdet}} L_{\text{eff}}/K_{\text{opt}}$, and computes required Mu-metal attenuation $A_{\text{dB}} = 20\log_{10}(|S_B| B_{\max}/\Omega_{\text{budget}})$.
- **Verified Measured Result:** Total nonlinear VRE = **`-0.3486 deg/h/g²`**, pure quadratic $G_2 V^2$ VRE = **`-0.0189 deg/h/g²`** (**$R^2 = 0.9998$**); Faraday sensitivity = **`0.18305 deg/h/G`** (`< 10⁻⁸%` error vs theory), dictating **`25.25 dB` Mu-metal shielding** to hold bias $< 0.01^\circ/\text{h}$ in a $1\text{ G}$ ambient field (**PASS**).

### ENG-04 — 5-Mode Fault Injection & Real-Time FPGA BIT/FDIR Verification (`--mode eng_fault_bit`, `EQ-39`)
- **Architecture:** Implements a real-time Built-In Test (BIT) & Fault Detection, Isolation, and Recovery (FDIR) state machine directly inside `DigitalDSP_SC::evaluate_frame_bit()`, monitoring per-frame optical intensity (`y_mean`, `y_min`, `y_max`), Loop-2 error $|e_{V_\pi}|$, ADC rail saturation counter, and Loop-1 step-jump magnitude.
- **Verified Measured Results (Fault Injected at $t = 4.000\text{ ms}$):**

| Fault Mode | Expected Code | Detected Code | Time-to-Alert (TTA) | FDIR Action / Recovery | Status |
| :--- | :---: | :---: | :---: | :--- | :---: |
| `sld_drop_50pct` (SLD aging $-50\%$) | `1` | **`1`** | **`0.62 us`** | BIT flag raised immediately | **PASS** |
| `fiber_break` ($P_{\text{out}} \to 0$) | `2` | **`2`** | **`0.62 us`** | BIT flag raised immediately | **PASS** |
| `mioc_electrode_open` ($V_\pi \to 2V_\pi$) | `3` | **`3`** | **`30.00 us`** | Loop-2 threshold alert | **PASS** |
| `adc_saturation` (ADC rail lock) | `4` | **`4`** | **`0.62 us`** | Rail-clip BIT flag raised | **PASS** |
| `dsp_seu_bitflip` (Integrator SEU $+0.4\text{ rad}$) | `5` | **`5`** | **`30.00 us`** | **Soft-rollback recovered (`True`)** | **PASS** |

### ENG-05 — Parallel Monte Carlo Production Yield ($C_{pk}$) & $-40^\circ\text{C}..+85^\circ\text{C}$ Virtual Calibration (`--mode eng_mc_yield_cal`, `EQ-40`, `EQ-41`)
- **Methodology:**
  1. **Monte Carlo Production Yield (`EQ-40`):** Draws $N = 500$ virtual production units with realistic manufacturing tolerances ($\pm 5\%$ $V_\pi$, $\pm 10\%$ TIA $f_{\text{GBW}}$, log-normal fiber $h$-parameter, $\pm 20\%$ PCB crosstalk, random $\epsilon_{V_\pi}$), executes full Tier 1 + Tier 2 SystemC-AMS runs in parallel, and computes pass yield, exact 95% Wilson score confidence interval, and process capability index $C_{pk} = \min\bigl((\text{USL}-\mu)/(3\sigma),\,(\mu-\text{LSL})/(3\sigma)\bigr)$.
  2. **Virtual Thermal Calibration Dataset (`EQ-41`):** Sweeps 7 temperatures ($-40, -20, 0, 25, 50, 70, 85^\circ\text{C}$) $\times$ 3 thermal ramps ($-0.5, 0.0, +0.5\text{ K/s}$) = 21 operating points coupling SLD wavelength drift, LiNbO$_3$ $V_\pi(T)$ drift, polarization drift, and Tier 1 Shupe phase into real Tier 2 runs. Exports `virtual_calibration_dataset.csv` and verifies both a 2D thermal polynomial fit and a 4-state Extended Kalman Filter (EKF).
- **Verified Measured Result (`N = 500` Campaign):**
  - **Production Yield:** **`97.2%` (`486 / 500` units)**, 95% Wilson CI = **`[95.36%, 98.32%]`**, bias mean `-0.313 deg/h`, std `0.379 deg/h`, **$C_{pk} = 0.604$**.
  - **Virtual Thermal Calibration (`-40..+85°C`, 21 pts):** Raw thermal drift RMS = `326.33 deg/h` $\to$ 2D Polynomial residual = **`0.050 deg/h` (`99.98%` reduction)**; 4-state EKF residual = **`0.170 deg/h` (`99.95%` reduction)** (**PASS**).

---

## 6. Automated Reporting & Deliverable Contract (`report/`)

Every CLI invocation (`./scripts/run_sim.sh --mode <mode>` or `./scripts/run_all_scenarios.sh`) automatically produces:
- `report/<run_id>/report.md`: Structured Markdown report with KPI tables, SPEC-005 gate/scenario statuses, and embedded figures.
- `report/<run_id>/report.html`: Interactive HTML5 report with Plotly zoomable plots, status badges, 300-DPI gallery, and raw JSON telemetry inspector.
- `report/<run_id>/figures/*.png`: 300-DPI diagnostic figures (`dsp6_compare.png`, `td01_blanking.png`..`td06_limit_cycles.png`, `eng01_hw_sizing.png`..`eng05_mc_yield_cal.png`).
- `report/<run_id>/virtual_calibration_dataset.csv`: Clean CSV dataset (when `eng_mc_yield_cal`, `eng_all`, or `all_scenarios` is executed) ready for direct consumption by embedded calibration / EKF firmware teams.
- `report/index.md` & `report/index.html`: Automatically refreshed centralized index across all simulation runs.
