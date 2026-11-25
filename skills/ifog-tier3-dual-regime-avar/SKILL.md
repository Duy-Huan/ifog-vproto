---
name: ifog-tier3-dual-regime-avar
description: Engineering knowledge for Tier 3 K-matrix extraction, Deadband/Bunny Ears analysis, Welch PSD 1/f flicker diagnostics, 12-pole IIR pink noise calibration, IEEE Std 952 Overlapping AVAR, and 5-region WLS recovery.
---

# Tier 3 Dual-Regime Analysis, AVAR Synthesis & Diagnostics (`tier3_analysis/`, `viz/`)

## 1. 12-Pole IIR 1/f Pink Noise Exact IEEE 952 Calibration
- A sum of $P = 12$ log-spaced 1st-order AR(1) Lorentzian filters ($f_p = f_{\min} r^p$, $a_p = e^{-2\pi f_p \Delta t}$, $b_p = \sqrt{1 - a_p^2}$) has one-sided PSD $S_{\text{sum}}(f) = \frac{1}{f \ln r}$ (note: factor of 2 larger than two-sided PSD!).
- IEEE Std 952-2020 defines Bias Instability $\sigma_{\text{BI}}^2 = \frac{2\ln 2}{\pi} B^2$, corresponding to one-sided $h_{-1} = B^2/\pi$.
- **EXACT GAIN FORMULA:**
  $$\text{gain} = B \sqrt{\frac{\ln r}{\pi}}$$
  (Do NOT multiply by $\sqrt{2}$ — that causes an exact $1.414\times$ BI bias!)
- Initialize each AR(1) branch from its stationary distribution $z_0 \sim \mathcal{N}(0, a_p^2)$ to eliminate slow-pole turn-on transients.

## 2. Physics of 1/f Flicker Filtering vs Nonlinear Leakage (Gate 3)
- **Linear closed-loop (`en_xtalk=False, en_tia_poly_nl=False`):**
  - Additive TIA $1/f$ noise $n_{1/f,\text{TIA}}[n]$ is differentiated by the demodulator $(y_2 - y_1) + (y_4 - y_3)$, suppressing low-frequency $1/f$ by $f^2$ and folding only the high-frequency tail near $f_m = 1/(4\tau)$ down to baseband as a **flat white floor (slope $\approx 0$)**!
- **Nonlinear closed-loop (`en_xtalk=True` and/or `en_tia_poly_nl=True` with state asymmetry):**
  - Resistive crosstalk $k_{\text{xtalk}}(1 + n_{1/f,\text{xtalk}})V_{\text{drv}}$ survives 4-state demodulation with non-zero gain $\propto 2\alpha k_{\text{xtalk}}$.
  - Quadratic TIA nonlinearity $G_2 (V_k + n_{1/f,\text{TIA}})^2$ produces cross-term $2 G_2 (V_2 - V_1) n_{1/f,\text{TIA}}$ whenever $V_2 \ne V_1$ (RAM, $V_\pi$ asymmetry, or nonzero rate), leaking **unfiltered slope $-1$ ($-10\text{ dB/dec}$) $1/f$ noise** directly into $\Omega_{\text{out}}$.
- **$\mathbf{K}$-Matrix Extraction (`EQ-27`):**
  - Always validate `target in {"tia", "dac", "xtalk"}` BEFORE launching `ifog_sim`.
  - Use $f_{\text{test}} = 100\text{ Hz}$ over $0.1\text{ s}$ (discarding initial 20% settling transient) with Hann-windowed coherent quadrature DFT ($2/\sum w$).

## 3. Dual-Regime Overlapping AVAR & 5-Region WLS Fit (Gate 4)
- **Closed-Loop Bandwidth Rolloff Cutoff (`t_min_fit = 1.5e-3 s`):**
  - Below the closed-loop integrator bandwidth ($T < 1/(2\pi f_{\text{BW}}) \approx 0.1\text{ ms}$), $\Omega_{\text{out}}$ is low-pass filtered so ADEV bends downward. Including $T < 1.5\text{ ms}$ in relative-weighted NNLS severely biases $\hat{N}$ downward; always set `t_min_fit = 1.5e-3`.
- **5-Region Decade Separation Criterion:**
  - For Bias Instability $B$ to exhibit a distinct flat plateau between ARW ($N$) and RRW ($K$), parameters must satisfy $B \ge 2.03\sqrt{N K}$.
  - For Fast-Scale (pure ARW on $[0.1, 5]\text{ s}$) to match Slow-Scale within $< 5\%$ at $T = 5\text{ s}$, require $T_{N\to B} = 3600 N^2 / (0.4413 B^2) > 55\text{ s}$.
- **IEEE Std 952 Finite-Sample $\chi^2$ Variance & Ensemble Averaging:**
  - A single 60 s trace has only 11 degrees of freedom at $T = 5\text{ s}$ ($\pm 17\%$ $1\sigma$ jitter), and a single 10 h Wiener trace has random linear drift $\sim K/\sqrt{10}$ biasing $R$.
  - Use variance-space Monte Carlo ensemble averaging (`sim_out_*.bin` for parallel 60 s Fast-Scale runs + `--slow-ensemble 8` for 10 h Slow-Scale runs) and cap WLS fitting at $T_{\max} \le 0.42 T_{\text{total}}$ to achieve genuine `< 5%` raw overlap continuity and `±10%` 5-parameter recovery without any curve-smoothing shortcuts.
