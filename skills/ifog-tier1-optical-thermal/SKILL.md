---
name: ifog-tier1-optical-thermal
description: Engineering patterns, numerical methods, and binary/JSON I/O contracts for Tier 1 offline solvers (jones_spectral.py, shupe_thermal.py, config_loader.py).
---

# Tier 1 Offline Physics Solvers (Optics & Thermal-Mechanical)

## 1. Spectral-Sliced Jones Matrix Solver (`tier1_offline/jones_spectral.py`)
- **Spectral Slicing (`EQ-04`):**
  - Use $N_{\text{spec}} \in [64, 128]$ slices over $\bar{\nu} \pm 3\sigma_\nu$ with $\sigma_\nu = \Delta\nu_{\text{FWHM}} / (2\sqrt{2\ln 2})$ and $\Delta\nu_{\text{eff}} = \sqrt{\pi/(2\ln 2)}\Delta\nu_{\text{FWHM}}$.
  - Vectorize the segment product $\prod_{m=M}^{1} \mathbf{R}(-\theta_m)\mathbf{B}_m(\omega_k)\mathbf{R}(\theta_m)$ across all $N_{\text{spec}}$ slices simultaneously in NumPy (`complex128`) so 200–1000 segments execute in $< 20\text{ ms}$.
  - Always include frequency-proportional group birefringence $\Delta\beta(\omega_k) = \frac{2\pi}{L_B}\frac{\omega_k}{\bar{\omega}}$ so broadband SLD depolarization matches Burns (1983).
  - Enforce Lorentz reciprocity strictly: $\mathbf{J}_{\text{CCW}}(\omega_k) = \mathbf{J}_{\text{CW}}^T(\omega_k)$.
- **Fringe Visibility & Polarization Bias Phase (`EQ-05`):**
  - Exact closed-form cross-correlation avoids grid discretization error:
    - $A_0 = \sum_k w_k (\|\mathbf{E}_{\text{CW}}\|^2 + \|\mathbf{E}_{\text{CCW}}\|^2)$
    - $C = \sum_k w_k \mathbf{E}_{\text{CW}}^\dagger \mathbf{E}_{\text{CCW}}$
    - $V = 2|C|/A_0$, $\phi_{\text{pol}} = \arg C = \arg\min_{\Delta\phi} P_{\text{static}}(\Delta\phi) - \pi$.
  - Use a realistic slight elliptical launch misalignment ($\psi = 0.05\text{ rad}$) so first-order amplitude-type polarization bias ($\propto \epsilon_{\text{pol}}\sqrt{h L}$) is captured while vanishing identically to $0$ when $h = 0$.

## 2. Thermal-Mechanical Shupe Solver (`tier1_offline/shupe_thermal.py`)
- **Dual Input Modes:**
  1. Built-in unconditionally stable **Crank–Nicolson** 1D radial heat diffusion solver (`scipy.linalg.solve_banded`) for asymmetric boundary temperature ramps.
  2. External FEM table import via CSV (`fem_csv_path` with columns `t_s, z_m, dT_dt_K_per_s`).
- **Shupe Integral Invariants (`EQ-09`):**
  - Uniform $\partial T/\partial t = C$ on a perfectly symmetric coil ($\delta z_{\text{quad}} = 0$) MUST integrate to $0$ identically ($\int_0^L (L - 2z)\,dz = 0$).
  - Linear spatial gradient $\partial T/\partial t = a z$ integrates analytically to $\text{prefactor} \cdot (-a L^3 / 6)$.
- **Binary LUT Contract (`shupe_lut.bin`):**
  - Packed little-endian header `<4sIQd`: `magic=b"SHUP"`, `version=1`, `n_samples`, `dt_s`, followed by `n_samples` `<dd` pairs `(t_s, delta_phi_shupe_rad)`. Both Python and C++ (`ifog_config.cpp`) validate magic/version/truncation fail-closed.

## 3. Configuration Validation (`configs/schema_v4.json`, `tier1_offline/config_loader.py`)
- Always validate every config against `configs/schema_v4.json` plus cross-field bounds (`0 <= k_start <= k_end < K_oversample`, `V_min_V < V_max_V`, `pink_f_min_Hz < pink_f_max_Hz`, Jury stability, Loop-2 separation).
- Always run `pip install -e . --no-build-isolation --no-deps` after adding any new top-level Python package so direct spec CLI invocations (`python3 tier1_offline/jones_spectral.py ...`) resolve imports without `PYTHONPATH` hacks.
