---
name: ifog-6state-and-scenarios
description: Official 6-state symmetric DSP modulation/demodulation (EQ-31..EQ-34), 64-byte DspTraceRecord logging, concurrent 3-axis SystemC-AMS IMU crosstalk (SharedPowerBus_TDF), Hann-windowed VRE extraction, partial-frame BIT/FDIR disambiguation, 6 Time-Domain & 5 System Engineering scenarios (IFOG-SIM-SPEC-005).
---

# Official 6-State DSP & 11 Official Scenarios Engineering Skill (`IFOG-SIM-SPEC-005`)

## 1. Official 6-State Symmetric Modulation & Demodulation Invariants (`EQ-31`–`EQ-34`)
- **Anti-Periodic Zero-Mean Instantaneous Phases (`EQ-31`):**
  $$\psi^{(6)} = \left[+\frac{\pi+\alpha}{2},\; -\frac{\pi+\alpha}{2},\; +\frac{\pi-3\alpha}{2},\; -\frac{\pi+\alpha}{2},\; +\frac{\pi+\alpha}{2},\; -\frac{\pi-3\alpha}{2}\right]$$
  - Always check $\sum_{s=1}^6 \psi_s = 0$ and $\psi_{s+3} = -\psi_s$.
  - Produces exact differential coil phases $[+(\pi-\alpha), -(\pi+\alpha), +(\pi-\alpha), -(\pi-\alpha), +(\pi+\alpha), -(\pi-\alpha)]$.
- **Optimal Angle $\alpha^* = \pi/3$ (`EQ-32`):**
  - Reduces peak MIOC voltage by **33.3%** ($\frac{2}{3}V_\pi$ vs $V_\pi$) because $\psi_3 = \psi_6 = 0$.
  - Cancels linear RAM, resistive crosstalk, capacitive crosstalk, and quadratic MIOC $\gamma_{\text{nl}}V^2$ identically in $e_\Omega^{(6)}$ (measured **`+136.94 dB`** rejection vs 4-state in `dsp6_compare`).
- **3-Channel Orthogonal Demodulation (`EQ-33`):**
  - $e_\Omega^{(6)} = (y_4+y_5+y_6) - (y_1+y_2+y_3) = 6S_\alpha\Delta\phi_{\text{NR}}$
  - $e_{V_\pi}^{(6)} = 2(y_2+y_5) - (y_1+y_3+y_4+y_6) = 8\pi S_\alpha\epsilon_{V_\pi}$
  - $e_{\text{asym}}^{(6)} = (y_1-y_3) + (y_6-y_4)$ (online RAM/crosstalk/TIA-settling monitor; orthogonal to both rate and $V_\pi$).
  - Note on `EQ-33` numerical tests: keep $|\epsilon_{V_\pi}| \le 10^{-6}$ when verifying linearized $8\pi S_\alpha\epsilon_{V_\pi}$ to avoid $O(\epsilon_{V_\pi}^2)$ second-order cosine curvature.
- **Anti-Windup Clamping (`EQ-34`):**
  - `DigitalDSP_SC` clamps $|\Delta\phi_{\text{step}}| \le K_{\text{opt}}\Omega_{\max}$ and sets `FLAG_ANTI_WINDUP` (`0x20`).

## 2. Time-Domain Scenario Numerical Lessons (`TD-01`..`TD-06`)
- **64-Byte Cycle-Accurate DSP Trace (`dsp_trace.bin`):**
  - `DspTraceRecord` (`static_assert(sizeof(DspTraceRecord) == 64)`) captures `t, omega_in, omega_out, phi_ramp, delta_phi_step, g_dac, adc_code, dac_code, prbs_bit, bit_fault_code, flags`. Always zero-initialize padding bytes so binary files stay bit-deterministic.
- **Closed-Loop $-3\text{ dB}$ Bandwidth Model (`TD-02`):**
  - Because `DigitalDSP_SC` integrates one complete modulation frame ($M\tau$, $M \in \{2,4,6\}$), the exact closed-loop small-signal response is the 1st-order frame-integrator $T_1(z_f) = K_{\text{tot}}/[z_f - (1-K_{\text{tot}})]$ (phase $\approx -87^\circ$ at high frequency, near-zero overshoot `0.008%`), NOT a resonant 2-slot delayed oscillator. Analytical $-3\text{ dB}$ BW matches measured SystemC-AMS Bode within ~8% (`2,354 Hz` vs `2,540 Hz`).
- **Sub-$\tau$ Settling & Optimal Blanking (`TD-01`):**
  - DAC-driver LTF (`drv_omega0 = 1.2e7`) contributes a settling tail past TIA $t_s(0.1\%) = 174\text{ ns}$, placing optimal clean blanking at $k_{\text{start}}^* = 5$ (`< 0.5%` error) vs baseline $k_{\text{start}} = 4$ (`2.98%`).
- **Zero-Noise 12-Bit Quantization Floor (`TD-06`):**
  - With white/pink noise disabled and 12-bit quantization, deadband lock yields an identically flat `omega_out` (`psd == 0`). Always floor PSD arrays (`np.maximum(psd, 1e-30)`) before computing log-ratio spur metrics.

## 3. System Engineering Scenario Lessons (`ENG-01`..`ENG-05`)
- **Concurrent 3-Axis SystemC-AMS IMU (`ENG-02`, `tier2_sysc_ams/src/imu_3axis.cpp`):**
  - Instantiate all 3 full axes (`Axis_X`, `Axis_Y`, `Axis_Z`) in ONE `sc_start()` call coupled by `SharedPowerBus_TDF` (`rate=1`).
  - `DAC_Driver_TDF::rail_droop_in` MUST declare `set_rate(1)` and `set_delay(1)` to break the algebraic loop through `SharedPowerBus_TDF`.
  - **GCC 13 `gcovr` pitfall:** Never put arithmetic expressions inside nested `nlohmann::json{{...}}` initializer lists (GCC 13 drops line coverage attribution); always assign `j["key"] = val;` explicitly to keep `100.0%` C++ coverage.
- **Hann-Windowed Quadratic VRE Extraction (`ENG-03`):**
  - High `alpha_ram` induces DC bias -> continuous serrodyne flybacks that beat with mechanical vibration; keep `alpha_ram = 2e-4` (zero flybacks), $f_{\text{vib}} = 1{,}500\text{ Hz}$, and use **Hann-windowed DC averaging** so partial-cycle spectral leakage vanishes and pure $G_2 V^2$ quadratic VRE achieves $R^2 = 0.9998$.
- **Real-Time FPGA BIT/FDIR Partial-Frame Disambiguation (`ENG-04`):**
  - When `sld_drop_50pct` or `fiber_break` injects mid-frame, 1 sample drops before the full 6-sample frame average `y_mean` crosses threshold, which would falsely trip `BIT_DSP_SEU` if only `y_mean` were checked. Checking `y_min < ratio * y_nom && y_max <= 1.05 * y_nom` classifies optical drops cleanly on the exact frame (`TTA = 0.62 us`) while keeping `BIT_MIOC_OPEN` (`vpi_err_threshold = 20000`, above startup `~5,500` counts) and `BIT_DSP_SEU` (`TTA = 30.0 us` + automatic soft-rollback recovery) 100% distinct.
- **4-State Thermal EKF (`ENG-05`, `EQ-41`):**
  - A 3-state EKF `[1, dT, dT_dt]` misses the quadratic $c_2 \Delta T^2$ thermal polarization curvature; always use a 4-state EKF `[1, dT, dT^2, dT_dt]` so both 2D polynomial (`99.98%`) and online EKF (`99.95%`) remove thermal bias cleanly across $-40..+85^\circ\text{C}$.
