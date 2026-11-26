# Specification Changelog — IFOG-SIM-SPEC

This file tracks the revision history and audit trail of the normative IFOG virtual prototype specifications stored in `spec/`.

> **Normative Governance Rule (AGENT.md Rule 7):**
> `spec/IFOG-SIM-SPEC-004.tex` (archived v4.0 baseline), `spec/IFOG-SIM-SPEC-005.tex` (archived v5.0 baseline), and `spec/IFOG-SIM-SPEC-006.{md,tex}` (active v6.0 baseline, authorized by project owner for `v3.0.0`) are all checksum-locked (`spec/IFOG-SIM-SPEC-004.sha256`, `spec/IFOG-SIM-SPEC-005.sha256`, `spec/IFOG-SIM-SPEC-006.sha256`) and MUST NOT be modified without explicit written approval from the project owner.

---

## [v6.0] — `IFOG-SIM-SPEC-006` (Current Normative Baseline — Owner-Authorized)

- **Document ID:** `IFOG-SIM-SPEC-006`
- **Supersedes / Extends:** `IFOG-SIM-SPEC-005` & `IFOG-SIM-SPEC-004` (preserves 100% of `EQ-01`..`EQ-41`, Gates 1..5, `TD-01`..`TD-06`, `ENG-01`..`ENG-05`, and `DYN-01`..`DYN-04`)
- **Reference Standards:** FMI Standard 3.0.2; IEEE Std 952-2020; IEEE Std 1666.1-2016
- **SHA-256 (`IFOG-SIM-SPEC-006.md`):** `9056a6e9bbfbe7fc9b0bec810ee2aa40447cf0b709d01ddcace1431f88121cf6`
- **SHA-256 (`IFOG-SIM-SPEC-006.tex`):** `d53751bb2e8bd1d288dcafb4dd02d1f20aaa6f5c3de23947e965505a279fee44`

### Key Architectural & Standard Additions (v5.0 -> v6.0)
1. **Standalone FMI 3.0 Co-Simulation FMU (`build/ifog_core.fmu`):** Wraps Tier 2 (`IfogTopModule` — exact unmodified Accellera SystemC/SystemC-AMS TDF/DE closed-loop core) via vendorized BSD-2-Clause official FMI 3.0 C headers (`fmi_wrapper/include/fmi3/`) and full 75-symbol FMI 3.0 C-API bridge (`fmi_wrapper/src/fmi3_bridge.cpp`), compiled with `-fPIC` and packaged with `modelDescription.xml`, `binaries/x86_64-linux/ifog_core.so`, and Tier 1 `resources/{phys_params.json, shupe_lut.bin, baseline_cfg.json}`.
2. **15-Variable `modelDescription.xml` Contract (`fmiVersion="3.0"`):** Declares `canBeInstantiatedOnlyOncePerProcess="true"` honoring the Accellera SystemC singleton kernel, `omega_in`/`shupe_phase_in` ZOH inputs, `omega_out`/`omega_out_avg`/`e_vpi_res`/`bit_status` outputs, tunable `eps_vpi`/`k_xtalk`/`enable_dither`, and fixed `dsp_mode` (`2`/`4`/`6` states), `en_white_noise`, `en_pink_noise`, `en_vpi_loop`, and `seed`.
3. **Three Normative FMI 3.0 Equations (`EQ-42`..`EQ-44`):** Multi-rate macro/micro ZOH alignment & anti-aliased interval-averaged rate output (`EQ-42`), Loop-2 residual $V_\pi$ phase error (`rad`) & 6-bit BIT/FDIR status bitmask (`EQ-43`), and black-box FMU vs standalone Tier 2 `< 1e-12 rad/s` equivalence contract (`EQ-44`) — expanding the CI formula verification matrix to **44 / 44** equations.
4. **FMPy Master Orchestrator & Verification Gate 6 (`tier3_analysis/fmi_master_runner.py`):** Programmatic `fmpy.validation.validate_fmu` compliance check, bit-exact (`0.00e+00 rad/s` < `1e-12`) standalone vs FMU equivalence on 4-state & 6-state modes, Slow Rate Ramp deadband sweep (dither OFF vs ON), and seamless FMU -> Tier 3 Dual-Regime 5-Region IEEE Std 952 Overlapping AVAR synthesis.

---

## [v5.0] — `IFOG-SIM-SPEC-005` (Archived Immutable Baseline)

- **Document ID:** `IFOG-SIM-SPEC-005`
- **Supersedes / Extends:** `IFOG-SIM-SPEC-004` (preserves 100% of `EQ-01`..`EQ-30` and Gates 1..4)
- **Reference Standards:** IEEE Std 952-2020; IEEE Std 1666.1-2016
- **SHA-256 (`IFOG-SIM-SPEC-005.tex`):** `793eae74b88cedcac174fb536d15895ed8482e5d62ef03004b9cb98cc053b200`

### Key Mathematical & System Additions (v4.0 -> v5.0)
1. **Official 6-State Symmetric Balanced DSP (`EQ-31`..`EQ-34`):** Anti-periodic instantaneous bias sequence $\psi_0..\psi_5$ with zero DC drive mean, optimal zero-crosstalk angle $\alpha^* = \pi/3$ ($\pm 2\pi/3, 0$ — 33% lower peak MIOC voltage than 4-state), simultaneous cancellation of linear RAM, resistive crosstalk, capacitive crosstalk, and quadratic MIOC nonlinearity ($\gamma_{\text{nl}} V^2$), three orthogonal channels $(e_\Omega^{(6)} = 6S_\alpha\Delta\phi_{\text{NR}},\; e_{V_\pi}^{(6)} = 8\pi S_\alpha\epsilon_{V_\pi},\; e_{\text{asym}}^{(6)})$, exact closed-loop $-3\text{ dB}$ bandwidth, and Loop-1 anti-windup clamping.
2. **6 Normative Time-Domain Scenarios (`TD-01`..`TD-06`) & Internal DSP Trace Contract (`dsp_trace.bin`, 64 B):** Sub-$\tau$ TIA/blanking alignment, step ($0 \to 100^\circ/\text{s}$) & sine Bode $-3\text{ dB}$ bandwidth, thermal $V_\pi$ step-shock transient ($0\% \to 5\%$), high-rate $300\text{--}700^\circ/\text{s}$ serrodyne $2\pi$ tracking + anti-windup, real-time Shupe thermal shock + extrapolative thermal filter, and zero-rate quantization limit cycles / idle tones + PRBS dither SFDR.
3. **5 System Engineering & Production Scenarios (`ENG-01`..`ENG-05`, `EQ-35`..`EQ-41`):**
   - `ENG-01` (`EQ-35`): ADC/DAC ENOB sweep (10–16 bit), ADC sampling aperture jitter $\delta V_j = (dV_{\text{adc}}/dt)\delta t_j$, and TIA $(R_f, C_f)$ / SLD $P_0$ Pareto optimization.
   - `ENG-02` (`EQ-36`): Concurrent 3-axis IMU SystemC-AMS co-simulation (`Axis_X`, `Axis_Y`, `Axis_Z`) coupled via `SharedPowerBus_TDF` (shared SLD back-reflection + shared FPGA/DAC rail droop) measuring inter-axis bias crosstalk.
   - `ENG-03` (`EQ-37`, `EQ-38`): Vibration Rectification Error (VRE, $^\circ/\text{h}/g^2$) via quadratic TIA $G_2 V^2$ and dynamic Faraday magnetic sensitivity ($^\circ/\text{h}/\text{Gauss}$) with Mu-metal shielding attenuation sizing.
   - `ENG-04` (`EQ-39`): Real-time FPGA BIT/FDIR monitor inside `DigitalDSP_SC` detecting 5 injected faults (SLD 50% drop, fiber break, MIOC open electrode, ADC saturation, SEU bit-flip + FDIR soft-recovery) with Time-to-Alert (TTA) telemetry.
   - `ENG-05` (`EQ-40`, `EQ-41`): Parallel Monte Carlo Production Yield ($\hat{Y}$, Wilson 95% CI, $C_{pk}$) and $-40^\circ\text{C}..+85^\circ\text{C}$ Virtual Thermal Calibration dataset with Polynomial + EKF thermal bias compensation validation.
4. **41-Formula CI Verification Matrix (`EQ-01`..`EQ-41`):** Expanded mandatory formula verification in `scripts/verify_formulas_ci.py` and CI/CD.

---

## [v4.0] — `IFOG-SIM-SPEC-004` (Archived Immutable Baseline)

- **Document ID:** `IFOG-SIM-SPEC-004`
- **Supersedes:** `IFOG-SIM-SPEC-003`
- **Reference Standards:** IEEE Std 952-2020; IEEE Std 1666.1-2016
- **SHA-256 (`IFOG-SIM-SPEC-004.tex`):** `b0307a33959d87c3b111ffb818d7161af7e9581869f75e052299ea92f5560635`

### Key Mathematical Audits & Additions (v3.0 -> v4.0)
1. **4-State Demodulation Sign Correction (Lefèvre Ch. 8):** Corrected Sagnac error channel from $(y_2 - y_1) + (y_3 - y_4)$ (which canceled Sagnac phase to zero) to $e_\Omega = (y_2 - y_1) + (y_4 - y_3) \approx 4 S_\alpha \Delta\phi_{\text{NR}}$, preserving $e_{V_\pi} = (y_3 + y_4) - (y_1 + y_2) \approx 4\pi S_\alpha \epsilon_{V_\pi}$ orthogonality.
2. **Complete Second-Order TIA Analog Front-End (Graeme Ch. 2–4):** Added $H_{\text{TIA}}(s)$, $\omega_0$, $\zeta$, Butterworth optimal compensation $C_{f,\text{opt}}$, settling time $t_s(0.1\%)$, 6-component input current noise PSD $S_{i,\text{tot}}(f,m)$, cubic polynomial nonlinearity ($G_1, G_2, G_3$), DAC-to-TIA capacitive/resistive crosstalk, and ADC blanking ARW penalty $1/\sqrt{\eta_b}$.
3. **Z-Domain Closed-Loop Stability (Jury Criterion):** Formalized open-loop transfer function $L_1(z) = K_{\text{tot}}/[z^2(z-1)]$ with delay $d=2$, strict Jury bound $0 < K_{\text{tot}} < 1$ (recommended $[0.15, 0.35]$), and Loop-2 bandwidth separation $K_{\text{tot},2} \le 0.1\,K_{\text{tot},1}$.
4. **Complete 5-Component IEEE Std 952-2020 Noise Model:** Added Rate Random Walk ($K$, $+1/2$ slope) in both Wiener and 1st-order Gauss–Markov AR(1) modes alongside Quantization ($Q$), ARW ($N$), Bias Instability ($B$), and Rate Ramp ($R$).
5. **Inter-Tier Coupling Equations:** Locked leakage gain matrix $\mathbf{K} = [K_{\text{TIA}\to\Omega}, K_{\text{DAC}\to\Omega}, K_{\text{xtalk}\to\Omega}]$ at $f_{\text{test}}=100\text{ Hz}$, unit conversion $\text{rad/s} \leftrightarrow ^\circ/\text{h}$ ($\times 206264.8$), and $<5\%$ Dual-Regime overlap continuity on $T_m \in [0.1, 5]\text{ s}$.
6. **Optical Kerr Coherence Factor (Bergh et al. 1982):** Explicitly incorporated broadband SLD coherence factor $\eta_{\text{coh}}$ into $\Delta\phi_{\text{Kerr}}$.
7. **Repository Layout, CLI & 4-Gate Acceptance Matrix:** Defined 7-subsystem directory layout, 32-byte `sim_out.bin` binary contract, 5 diagnostic visualization tools (`viz/`), quantitative feasibility validation ($L=1000\text{ m}$), and 4 automated acceptance gates (Gate 1..Gate 4).
