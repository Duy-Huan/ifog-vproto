# Release Notes — `ifog-vproto` (Closed-Loop IFOG Virtual Prototype)

## Document Control Metadata

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-VPROTO-REL-001` |
| **Current Version** | `v2.0.0` |
| **Status** | `RELEASED (Production Gate Verified)` |
| **Normative Specification** | [`spec/IFOG-SIM-SPEC-005.tex`](../spec/IFOG-SIM-SPEC-005.tex) (v5.0) & [`spec/IFOG-SIM-SPEC-004.tex`](../spec/IFOG-SIM-SPEC-004.tex) (v4.0) |
| **Architecture Reference** | [`docs/IFOG_VPROTO_ARCHITECTURE.md`](IFOG_VPROTO_ARCHITECTURE.md) / [`docs/IFOG_VPROTO_ARCHITECTURE.pdf`](IFOG_VPROTO_ARCHITECTURE.pdf) |
| **Scenarios Reference** | [`docs/IFOG_SIMULATION_SCENARIOS.md`](IFOG_SIMULATION_SCENARIOS.md) / [`docs/IFOG_SIMULATION_SCENARIOS.pdf`](IFOG_SIMULATION_SCENARIOS.pdf) |
| **LaTeX / PDF Companion** | [`docs/RELEASE_NOTES.tex`](RELEASE_NOTES.tex) / [`docs/RELEASE_NOTES.pdf`](RELEASE_NOTES.pdf) |

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
