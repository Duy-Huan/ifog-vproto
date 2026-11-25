# Specification Changelog — IFOG-SIM-SPEC

This file tracks the revision history and audit trail of the normative IFOG virtual prototype specifications stored in `spec/`.

> **Normative Governance Rule (AGENT.md Rule 7):**
> `spec/IFOG-SIM-SPEC-004.tex` is checksum-locked (`spec/IFOG-SIM-SPEC-004.sha256`) and MUST NOT be modified without explicit written approval from the project owner.

---

## [v4.0] — `IFOG-SIM-SPEC-004` (Current Normative Baseline)

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
