# Release Notes — `ifog-vproto` (Closed-Loop IFOG Virtual Prototype)

## Document Control Metadata

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-VPROTO-REL-001` |
| **Current Version** | `v2.2.0` |
| **Status** | `RELEASED (Production Gate Verified)` |
| **Normative Specification** | [`spec/IFOG-SIM-SPEC-005.tex`](../spec/IFOG-SIM-SPEC-005.tex) (v5.0) & [`spec/IFOG-SIM-SPEC-004.tex`](../spec/IFOG-SIM-SPEC-004.tex) (v4.0) |
| **Architecture Reference** | [`docs/IFOG_VPROTO_ARCHITECTURE.md`](IFOG_VPROTO_ARCHITECTURE.md) / [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](IFOG_VPROTO_ARCHITECTURE.pdf) |
| **Scenarios Reference** | [`docs/IFOG_SIMULATION_SCENARIOS.md`](IFOG_SIMULATION_SCENARIOS.md) / [`docs/IFOG_SIMULATION_SCENARIOS.pdf`](IFOG_SIMULATION_SCENARIOS.pdf) |
| **LaTeX / PDF Companion** | [`docs/RELEASE_NOTES.tex`](RELEASE_NOTES.tex) / [`docs/RELEASE_NOTES.pdf`](RELEASE_NOTES.pdf) |

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
