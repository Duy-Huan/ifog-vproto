# Full Real All-Scenarios Example (`examples/full_all_scenarios/`)

This curated example contains the **complete, genuine, full-scale simulation output** (zero mocks, zero smoke-test shortcuts) covering **all 21 official acceptance gates & engineering scenarios** (`IFOG-SIM-SPEC-004` v4.0 + `IFOG-SIM-SPEC-005` v5.0 + `IFOG-SIM-SPEC-006` v6.0, software release `v3.0.1`), generated directly by `./examples/run_example.sh --sync-example` and committed to the repository for complete feasibility and architectural evaluation.

## Included Deliverables
- [`architecture_model.html`](architecture_model.html) — Code-audited interactive 3-Tier + FMI 3.0 mathematical architecture explorer with live measured parameters from this run
- [`report.md`](report.md) — Standardized comprehensive Markdown report covering Core Gates 1–4, Gate 5 (Official 6-State DSP), **Gate 6 (FMI 3.0 Black-Box Co-Simulation FMU)**, Group A (`TD-01`..`TD-06`), Group B (`ENG-01`..`ENG-05`), Group C (`DYN-01`..`DYN-04`), and all 21 embedded figures each with full theoretical foundation, plain-language non-specialist reading guide, and dynamic measured proof
- [`report.html`](report.html) — Self-contained KaTeX + interactive HTML5 Plotly report featuring an embedded interactive architecture explorer, sticky quick-navigation bar, **20 interactive multi-panel Plotly charts** (each with 3-column theory/non-specialist/proof cards), annotated 21-figure 300-DPI gallery, and collapsible JSON inspector
- [`metrics_summary.json`](metrics_summary.json) — Complete structured JSON payload across all 21 gates & scenarios
- [`virtual_calibration_dataset.csv`](virtual_calibration_dataset.csv) — Real 21-point `-40..+85 °C` virtual environmental chamber calibration table from `ENG-05`
- Per-stage JSON artifacts:
  - Core Gates 1–6: [`phys_params.json`](phys_params.json), [`shupe_summary.json`](shupe_summary.json), [`sim_summary.json`](sim_summary.json), [`gate1_metrics.json`](gate1_metrics.json), [`sweep_results.json`](sweep_results.json), [`nonlinearity_summary.json`](nonlinearity_summary.json), [`k_matrix.json`](k_matrix.json), [`gate3_metrics.json`](gate3_metrics.json), [`avar_metrics.json`](avar_metrics.json), [`dsp6_compare.json`](dsp6_compare.json), [`fmi_gate_summary.json`](fmi_gate_summary.json)
  - Group A & Group B: [`td01_blanking.json`](td01_blanking.json), [`td02_step_sine.json`](td02_step_sine.json), [`td03_vpi_shock.json`](td03_vpi_shock.json), [`td04_high_rate.json`](td04_high_rate.json), [`td05_shupe_shock.json`](td05_shupe_shock.json), [`td06_limit_cycles.json`](td06_limit_cycles.json), [`eng01_hw_sizing.json`](eng01_hw_sizing.json), [`eng02_imu_3axis.json`](eng02_imu_3axis.json), [`eng03_vre_faraday.json`](eng03_vre_faraday.json), [`eng04_fault_bit.json`](eng04_fault_bit.json), [`eng05_mc_yield_cal.json`](eng05_mc_yield_cal.json)
  - Group C Dynamic, PSD & Electro-Optic Probe: [`dyn01_step_response.json`](dyn01_step_response.json), [`dyn02_freq_response.json`](dyn02_freq_response.json), [`dyn03_output_psd.json`](dyn03_output_psd.json), [`dyn04_sine_electro_optic.json`](dyn04_sine_electro_optic.json), [`dyn_summary.json`](dyn_summary.json)
- **21 Publication-Grade 300-DPI Figures** under [`figures/`](figures/)

---

## Executive Scorecard (`v3.0.1` — 21 / 21 PASS)

| # | Gate / Scenario | Specification Scope | Measured Real Simulation Result | Status |
| :---: | :--- | :--- | :--- | :---: |
| 1 | **Gate 1** | Golden Linear & Continuous $2\pi$ Flyback | Static err `3.10e-16 rad` (`< 1e-9`), **`1,666`** wraps, $\epsilon_{V_\pi,\text{eff}}=5.84\times 10^{-14}$ | **PASS** |
| 2 | **Gate 2** | Deadband & Bunny Ears Mitigation (23-pt sweep) | **`98.85%`** Deadband reduction & **`98.85%`** Bunny Ears SF reduction | **PASS** |
| 3 | **Gate 3** | $1/f$ Flicker Filtering vs Leakage & $\mathbf{K}$-Matrix | Linear slope `-0.0621`, nonlinear `-0.8928`, $\mathbf{K}$ repeatability **`0.000%`** | **PASS** |
| 4 | **Gate 4** | Dual-Regime 5-Region Overlapping AVAR ($4\times 60\text{ s}$ + $12\times 10\text{ h}$) | Overlap mismatch **`2.42%`** (`< 5%`); WLS err: $Q:+3.18\%$, $N:-0.71\%$, $B:+5.31\%$, $K:-7.06\%$, $R:+9.29\%$ | **PASS** |
| 5 | **Gate 5** | Official 6-State Symmetric DSP (`EQ-31`..`EQ-34`) | Static err `1.28e-16 rad`, $\epsilon_{V_\pi}=1.31\times 10^{-11}$, RAM/xtalk rejection **`+136.94 dB`**, `-33.3%` peak $V_{\text{MIOC}}$ | **PASS** |
| 6 | **Gate 6** | **FMI 3.0 Black-Box Co-Simulation FMU (`EQ-42`..`EQ-44`)** | **0 XSD errors**, equiv **`0.00e+00 rad/s`** (`< 1e-12`, 4s & 6s, `bit_status == 0`), Deadband red. **`97.42%`** (Bunny Ears **`99.59%`**), AVAR overlap **`3.83%`** (`< 5%`, max WLS err `8.92%`) | **PASS** |
| 7 | **`TD-01`** | Sub-$\tau$ Switching Transient & ADC Blanking | $t_s = 174.1\text{ ns}$, optimal blanking $k^* = 5$, clean err `2.978%`, ARW penalty $\times 1.155$ | **PASS** |
| 8 | **`TD-02`** | Closed-Loop Step ($0\to 100^\circ/\text{s}$) & $-3\text{ dB}$ Bandwidth | $t_r = 0.22\text{ ms}$, overshoot `0.0%`, BW **`2,540 Hz`** (analytical `2,354 Hz`) | **PASS** |
| 9 | **`TD-03`** | Loop-2 $V_\pi$ Gain-Lock Under $5\%$ Thermal Shock | 4-state $\epsilon = 1.78\times 10^{-15}$, 6-state $\epsilon = 1.68\times 10^{-11}$, 6-state convergence **`6.3 ms`** | **PASS** |
| 10 | **`TD-04`** | High-Rate Dynamics ($300\text{--}700^\circ/\text{s}$), $2\pi$ Flyback & Anti-Windup | $700^\circ/\text{s}$ err **`0.000%`**, `7,184` wraps (`179.6 kHz`), `200` anti-windup clamps | **PASS** |
| 11 | **`TD-05`** | Real-Time Thermal Shupe Shock & Extrapolative Filter | Peak `1,483.614 deg/h`, extrapolative suppression **`99.7%`**, correlation $r = 1.0000$ | **PASS** |
| 12 | **`TD-06`** | Quantization Limit Cycles (Idle Tones) & PRBS Dither | Bias reduction `3.6%`, unique DAC codes expanded `3 -> 1,595` | **PASS** |
| 13 | **`ENG-01`** | Hardware Sizing (ENOB 10–16 bit, Jitter, TIA/SLD Pareto) | Min ENOB = **`12-bit`**, Jitter ARW deg `+2,216.3%` @ `10 ns`, best Pareto ARW `1.4118e-4 deg/rt-h` | **PASS** |
| 14 | **`ENG-02`** | 3-Axis IMU Shared-SLD / Shared-Rail Crosstalk ($X = 500^\circ/\text{s}$) | Rail droop `92.4 mV`, stationary Axis-Y bias `40.63 -> 0.1064 deg/h` (6-state mitigation) | **PASS** |
| 15 | **`ENG-03`** | Vibration Rectification Error (VRE) & Faraday / Mu-Metal | VRE `-0.3486 deg/h/g^2`, Faraday `0.183 deg/h/G`, Mu-metal shielding **`25.3 dB`** | **PASS** |
| 16 | **`ENG-04`** | Fault Injection & Real-Time FPGA BIT/FDIR (5 Fault Modes) | **`5/5`** faults detected, max TTA **`30.0 us`**, SEU FDIR recovery = **`True`** | **PASS** |
| 17 | **`ENG-05`** | Monte Carlo Yield ($N=500$, $C_{pk}$) & `-40..+85 °C` Calibration | Yield **`97.20%`** (`486/500`, 95% CI `[95.36%, 98.32%]`, $C_{pk}=0.604$), Poly `99.98%` / EKF `99.95%` | **PASS** |
| 18 | **`DYN-01`** | Dedicated Closed-Loop Step Response (10 & 100 deg/s, 4s vs 6s, $K_{\text{tot},1}$ sweep) | 6s $t_r = 0.206\text{ ms}$ (10 deg/s) / `0.294 ms` (100 deg/s), OS **`0.00%`**, max SS err **`0.0000%`**, $K_{\text{tot},1}$ speedup `0.382 -> 0.118 ms` | **PASS** |
| 19 | **`DYN-02`** | Full Closed-Loop Bode Frequency Response (Mag, Phase & Group Delay, 15 pts) | 4s BW **`2,544 Hz`** ($\tau_{g,0}=65.2\ \mu\text{s}$), 6s BW **`1,642 Hz`** ($\tau_{g,0}=103.3\ \mu\text{s}$), exact **`1.55×`** ratio | **PASS** |
| 20 | **`DYN-03`** | Broadband Output Angular-Rate PSD, ASD & Cumulative RMS Noise | White ARW **`0.000352 deg/rt-h`** (`0.97×` EQ-15), 6s LF $1/f$ suppression **`+29.2 dB`**, HF roll-off **`-13.5 dB`** | **PASS** |
| 21 | **`DYN-04`** | Sinusoidal Rate (`50 deg/s @ 250 Hz`) & Internal Electro-Optic Probe | Gain `0.9889`, phase `-9.36°`, **THD `-67.5 dB`**, **SFDR `43.6 dB`**, $\Delta\phi_S = 1.180\text{ rad}$, `391` $V_{\text{fb,MIOC}}$ wraps, **$r(\Delta P_{\text{PD}},\Delta\phi_{\text{err}}) = 0.9960$** | **PASS** |

---

## Visual Walkthrough (All 21 300-DPI Real Outputs)

### Part I — Core Acceptance Gates (Gates 1–6)

#### 1. Micro-Scale Electro-Optic Transients & ADC Blanking Alignment (Gate 1)
![Micro-Scale Waveforms](figures/waveforms.png)

#### 2. Closed-Loop Deadband & Bunny Ears Mitigation (Gate 2)
![Deadband and Bunny Ears](figures/bunny_ears.png)

#### 3. $1/f$ Flicker Modulation Rejection vs Nonlinear Crosstalk Leakage (Gate 3)
![1/f Flicker PSD](figures/psd_flicker.png)

#### 4. IEEE Std 952-2020 Dual-Regime Overlapping AVAR Across All 5 Regions (Gate 4)
![Dual-Regime 5-Region AVAR](figures/avar_5regions.png)

#### 5. Official 6-State Symmetric DSP vs 4-State Lefèvre Benchmark (Gate 5)
![6-State vs 4-State DSP Benchmark](figures/dsp6_compare.png)

#### 6. FMI 3.0 Black-Box Co-Simulation FMU Compliance, Equivalence, Deadband & 5-Region AVAR (Gate 6)
![FMI 3.0 Co-Simulation FMU Gate 6](figures/fmi_fmu_gate.png)

---

### Part II — Group A: Official Time-Domain Scenarios (`TD-01`..`TD-06`)

#### 7. `TD-01` — Sub-$\tau$ Switching Transient & ADC Blanking Alignment
![TD-01 Sub-tau Blanking](figures/td01_blanking.png)

#### 8. `TD-02` — Closed-Loop Step Response & Dynamic $-3\text{ dB}$ Bandwidth
![TD-02 Step and Bode](figures/td02_step_bode.png)

#### 9. `TD-03` — Loop-2 $V_\pi$ Gain-Lock Transient Under $5\%$ Thermal Shock
![TD-03 Vpi Shock](figures/td03_vpi_shock.png)

#### 10. `TD-04` — High-Rate Dynamics ($300\text{--}700^\circ/\text{s}$), $2\pi$ Serrodyne Flyback & Anti-Windup
![TD-04 High Rate Serrodyne](figures/td04_high_rate.png)

#### 11. `TD-05` — Real-Time Thermal Shupe Shock & Extrapolative Compensation Filter
![TD-05 Shupe Shock](figures/td05_shupe_shock.png)

#### 12. `TD-06` — Quantization Limit Cycles (Idle Tones) & PRBS Dither Spectral Purity
![TD-06 Limit Cycles](figures/td06_limit_cycles.png)

---

### Part III — Group B: System Engineering & Production Scenarios (`ENG-01`..`ENG-05`)

#### 13. `ENG-01` — Hardware Sizing Trade-Off (ENOB 10–16 bit, Aperture Jitter & TIA/SLD Pareto)
![ENG-01 Hardware Sizing](figures/eng01_hw_sizing.png)

#### 14. `ENG-02` — 3-Axis IMU Shared-SLD & Shared-Rail Inter-Axis Crosstalk
![ENG-02 3-Axis IMU Crosstalk](figures/eng02_imu_3axis.png)

#### 15. `ENG-03` — Vibration Rectification Error (VRE) & Magnetic Faraday Sensitivity
![ENG-03 VRE and Faraday](figures/eng03_vre_faraday.png)

#### 16. `ENG-04` — Fault Injection & Real-Time FPGA BIT/FDIR Verification (5 Fault Modes)
![ENG-04 Fault Injection BIT/FDIR](figures/eng04_fault_bit.png)

#### 17. `ENG-05` — Monte Carlo Production Yield ($N=500$, $C_{pk}$) & `-40..+85 °C` Virtual Thermal Calibration
![ENG-05 Monte Carlo Yield & Calibration](figures/eng05_mc_yield_cal.png)

---

### Part IV — Group C: Dynamic Response, Output PSD & Sinusoidal Electro-Optic Probe (`DYN-01`..`DYN-04`)

#### 18. `DYN-01` — Dedicated Closed-Loop Step Response (10 & 100 deg/s, 4-State vs 6-State & $K_{\text{tot},1}$ Sweep)
![DYN-01 Step Response](figures/dyn01_step_response.png)

#### 19. `DYN-02` — Full Closed-Loop Frequency Response (Bode Magnitude, Unwrapped Phase & Group Delay)
![DYN-02 Bode Frequency Response](figures/dyn02_freq_response.png)

#### 20. `DYN-03` — Broadband Output Angular-Rate PSD, ASD & Cumulative Integrated RMS Noise
![DYN-03 Output Rate PSD](figures/dyn03_output_psd.png)

#### 21. `DYN-04` — Sinusoidal Angular Rate (`50 deg/s @ 250 Hz`) & Internal Electro-Optic Signal Chain (`PD`, `V_fb MIOC`, Sagnac Phase, `V_TIA`, ADC Blanking)
![DYN-04 Sinusoidal Electro-Optic Signal Chain](figures/dyn04_sine_electro_optic.png)

---

## Reproduce This Exact All-Scenarios Example

### Option A — Inside Docker or Podman (Zero Host Dependencies)
```bash
./scripts/container_run.sh build
./scripts/container_run.sh example
# Generates full Markdown + 20-Chart Interactive Plotly HTML5 report + 21 300-DPI PNGs in:
# report/full_all_scenarios/{report.md, report.html, figures/*.png}
```

### Option B — Native Linux (Portable Source Setup)
```bash
bash scripts/setup_env.sh --with-system-deps --build-tier2
source scripts/env.sh
./examples/run_example.sh
# Optional: pass --sync-example to also mirror outputs into examples/full_all_scenarios/
```

### Option C — Run Gate 6 (FMI 3.0 FMU) or Group C Scenarios Individually via CLI
```bash
cmake --build build --target package_fmu
./scripts/run_sim.sh --mode fmi_gate --run-id demo_fmu
./scripts/run_sim.sh --mode dyn_step_response --run-id demo_step
./scripts/run_sim.sh --mode dyn_freq_response --run-id demo_bode
./scripts/run_sim.sh --mode dyn_output_psd --run-id demo_psd
./scripts/run_sim.sh --mode dyn_sine_electro_optic --run-id demo_sine_eo
./scripts/run_sim.sh --mode dyn_all --run-id demo_dyn_all
```
