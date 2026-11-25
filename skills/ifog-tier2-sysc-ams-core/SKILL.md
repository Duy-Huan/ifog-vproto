---
name: ifog-tier2-sysc-ams-core
description: Deep IEEE Std 1666.1 SystemC + SystemC-AMS PoC 2.3.4 engineering skill covering build/ABI, sca_ltf_nd pitfalls, sc_buffer DE boundaries, set_delay(1) pipeline latency, closed-loop polarity, PRBS dither, and 100% gcovr coverage.
---

# Tier 2 SystemC + SystemC-AMS Co-Simulation Core (`tier2_sysc_ams/`)

## 1. SystemC 2.3.4 & SystemC-AMS PoC 2.3.4 Build / ABI Contract
- Ubuntu 24.04 `libsystemc-dev` ships SystemC 2.3.4 compiled with C++17 ABI (`SC_CPLUSPLUS=201703L`).
- SystemC-AMS PoC 2.3.4 MUST be built with matching flags (`-O3 -std=c++17 -DSC_CPLUSPLUS=201703L -fPIC`) via `scripts/install_systemc_ams.sh` (pinned to commit `a72d365f` of `Risto97/systemc-ams`).
- Always pass `SC_CPLUSPLUS=201703L` in `CMakeLists.txt` (`target_compile_definitions`).

## 2. Critical SystemC-AMS PoC 2.3.4 Traps & Proven Fixes

1. **TRAP #1 — `sca_ltf_nd` Quadratic $O(N^2)$ Slowdown with Explicit Sub-Step `tstep`:**
   - Calling `ltf(num, den, vec, 1.0, dt_fast_time)` with `dt_fast_time < module_timestep` triggers an internal $O(N^2)$ bug in SystemC-AMS PoC 2.3.4 (`0.05 s` takes `59.7 s` -> `20 hours` for `60 s`!).
   - **FIX:** NEVER pass `tstep < module_timestep` to `sca_ltf_nd`.
2. **TRAP #2 — `sca_ltf_nd` Tustin/Trapezoidal Nyquist Ringing in Stiff Regimes:**
   - SystemC-AMS `sca_ltf_nd` uses Trapezoidal integration. On the spec Table 4 baseline ($\omega_0 = 7.61\times 10^7\text{ rad/s}$, $\Delta t_{\text{fast}} = 306\text{ ns}$), $\omega_0 \Delta t_{\text{fast}} = 23.26 \gg 2$, mapping the discrete pole to $z_p \approx -0.78$ and causing severe alternating-sign Nyquist ringing all the way through $k = 15$!
   - **FIX:** Hybrid stiff/non-stiff solver:
     - When $\omega_0 \Delta t_{\text{fast}} \le 0.2$ (non-stiff): call `sca_tdf::sca_ltf_nd` directly with explicit `state` vector.
     - When $\omega_0 \Delta t_{\text{fast}} > 0.2$ (stiff): use `ExactSecondOrderLtf` (`ifog_math.hpp`), the exact analytical continuous-time ZOH matrix exponential $e^{\mathbf{A}\Delta t}$ covering underdamped ($\zeta < 1$), critically damped ($\zeta = 1$), and overdamped ($\zeta > 1$) regimes. Zero Nyquist ringing AND **~1.1 s wall-clock per simulated second** (`~65 s` for full `60 s` / `1.96e8` micro-samples!).
3. **TRAP #3 — `sc_signal` Drops Repeated Integer ADC Codes at TDF->DE Boundary:**
   - `sc_signal<T>` only notifies `value_changed_event()` when the written value differs from the previous value. At zero rate / quiet input, repeated ADC codes silently stall `DigitalDSP_SC`!
   - **FIX:** Use `sc_core::sc_buffer<double>` for `sig_adc_code` and `sig_dac_code`; `sc_buffer` notifies on EVERY write unconditionally.
4. **TRAP #4 — Exact Pipeline Latency `PIPE_DEPTH = 2` with `set_delay(1)`:**
   - Verified directly in `sca_tdf_sc_in.h` (`buffer_size = delay + rate`, `write_cnt = delay`): with `dac_code_in.set_delay(1)` on `DAC_Driver_TDF` plus the DE delta-cycle boundary, the ADC response to the `dac_code` emitted by `DigitalDSP_SC` at slot $n$ returns at slot $n + 2$ — matching the spec's exact $d = 2$ delay in $L_1(z) = K_{\text{tot}}/[z^2(z-1)]$ (`EQ-22`).
   - Maintain a 2-slot `PipeTag` FIFO in `DigitalDSP_SC` tagging `(valid, state_idx, dither_step)` so demodulation aligns each returning `y_now` to its exact originating state and dither step.
5. **TRAP #5 — 4-State Instantaneous Bias Sequence & Closed-Loop Negative Feedback Polarity:**
   - Instantaneous bias phases $[+\pi, +\alpha, -\pi, +\alpha]$ remain strictly bounded in $[-\pi, +\pi]$ while their first differences produce the exact `EQ-01` sequence $[+(\pi-\alpha), -(\pi-\alpha), -(\pi+\alpha), +(\pi+\alpha)]$ (including $|\Delta\phi_{3,4}| = \pi + \alpha > \pi$!).
   - With `EQ-13` using $\cos(\Delta\phi_{\text{NR}} + \Delta\phi_{\text{mod}})$ and `EQ-20` using $\Delta\phi_{\text{step}}[r] = \Delta\phi_{\text{step}}[r-1] + K_{I,1} e_\Omega[r]$, the DAC feedback ramp MUST apply negative feedback polarity `phi_total = -phi_ramp - phi_dither + phi_bias` so $\Delta\phi_{\text{err}} = \Delta\phi_{\text{NR}} - \Delta\phi_{\text{step}} \to 0$ and $\Delta\phi_{\text{step}} \to +K_{\text{opt}}\Omega_{\text{in}}$.
   - Note that $(V_2 - V_1) + (V_4 - V_3) = +\frac{2\alpha}{\pi} V_\pi \ne 0$: this is real Lefèvre 4-state physics explaining why parasitic RAM ($\alpha_{\text{RAM}} V_{\text{drv}}$) and resistive crosstalk ($k_{\text{xtalk}}(1+n_{1/f})V_{\text{drv}}$) couple directly into $e_\Omega$.
6. **TRAP #6 — PRBS Dither Wrapping & Nonlinearity Leakage:**
   - Never wrap `phi_dither` across $\pm\pi$ ($2\pi$ flyback) at zero rate when `gamma_nl` or residual $\epsilon_{V_\pi}$ is present, and keep `prbs_amplitude_rad` modest (~3 DAC LSBs = `3e-4 rad`). Reflect `phi_dither` cleanly within $[-\pi/4, +\pi/4]$ and update direction only at frame start (`emit_state == 0`) so dither cancels identically in $e_{V_\pi}$ and cleanly in $e_\Omega$ via $+4 S_\alpha \sin(\delta_d)$ without degrading the ARW floor.

## 3. Performance & 100% Coverage Checklist
- Never allocate memory inside `processing()`; hoist all P_det-independent EQ-15 noise variance terms into constructor/initialize.
- Buffer `SimRecord` writes (4096 x 32 B = 128 KB chunks) and verify `static_assert(sizeof(SimRecord) == 32)`.
- Use a non-`NDEBUG` `CHECK()` macro in `cpp_unit_tests.cpp` so Release builds still execute all assertions with zero warnings.
- Run `bash scripts/run_cpp_coverage.sh` to enforce `100.0%` C++ line coverage and `100.0%` function coverage via `gcovr`.
