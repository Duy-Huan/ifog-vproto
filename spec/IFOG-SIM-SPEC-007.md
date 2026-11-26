# IFOG-SIM-SPEC-007 — High-Fidelity Predictive Physics & Inverse Calibration Specification (v7.0)

| Field | Value |
| :--- | :--- |
| **Document ID** | `IFOG-SIM-SPEC-007` |
| **Version** | `7.0` (Additive extension over `IFOG-SIM-SPEC-006`, `SPEC-005`, and `SPEC-004`) |
| **Release Alignment** | `ifog-vproto` `v4.0.0` |
| **Reference Standards** | IEEE Std 952-2020 (IFOG Test & AVAR); IEEE Std 1666.1-2016 (SystemC-AMS); FMI Standard 3.0.2 |
| **Equation Scope** | Preserves `EQ-01`..`EQ-44` bit-identically; defines 9 normative predictive & calibration equations **`EQ-45`..`EQ-53`** (cross-referenced to draft `EQ-40`..`EQ-48`) |
| **Backward Compatibility** | 100% compatible with `configs/schema_v4.json`, `configs/schema_v5.json`, `shupe_lut.bin` v1, and all 6 Gates + 15 Scenarios |

---

## 1. Engineering Scope & Objective

`IFOG-SIM-SPEC-007` bridges the accuracy gap between textbook/datasheet simulation and **high-accuracy physical IFOG hardware prediction (`< 5%` error against real prototypes)** across three coupled layers:

1. **Tier 1 (`tier1_offline/`) — Discrete Coil Winding, Thermo-Mechanical Stress & Dynamic LUT v2:**
   - Turn-by-turn discrete `quadrupole` (4-layer ABBA) and `octupole` (8-layer ABBA-BAAB) coil mapping with end-flange transition offsets (`EQ-45`).
   - Combined thermo-optical Shupe + elasto-optic potting stress integral (`EQ-46`).
   - Dynamic Sagnac scale factor thermal/wavelength/back-power drift $K_{\text{opt}}(t)$ (`EQ-47`) and time-varying visibility $V_{\text{eff}}(t)$, polarization bias $\Delta\phi_{\text{pol}}(t)$, and half-wave voltage $V_\pi(t)$ (`EQ-48`).
   - Multi-column binary lookup table format `shupe_lut.bin` v2 (`24 B` header + `56 B <7d` records) with seamless v1 fallback (`EQ-49`).
2. **Tier 2 (`tier2_sysc_ams/`) & FMI 3.0 Wrapper (`fmi_wrapper/`) — High-Fidelity Electro-Optic Transients & Live Tunability:**
   - $\text{LiNbO}_3$ MIOC 2nd-order electrode cutoff + electro-acoustic step resonance dynamics before coil transit delay $K_{\text{delay}}$ (`EQ-50`).
   - Physical capacitive + resistive PCB/package crosstalk current $i_{\text{xtalk}}[k]$ at the TIA summing node (`EQ-51`), reducing identically to legacy `SPEC-004` when $C_{\text{xtalk}} = 0$.
   - Coherent Rayleigh backscattering + MIOC pigtail facet reflection phase noise driven by an Ornstein–Uhlenbeck environmental process (`EQ-52`).
   - Seven new FMI 3.0 `causality="parameter"` `variability="tunable"` SI variables (`VR 15..21`) in `modelDescription.xml.in` and `fmi3_bridge.cpp`.
3. **Tier 3 (`tier3_analysis/`) — Anti-Double-Counting AVAR Stitch & 3-Stage Inverse Calibration:**
   - `DualRegimeStitcher` quadrature Bias Instability subtraction $B_{\text{T3,mech}} = \sqrt{\max(0, B_{\text{total}}^2 - B_{\text{T2,meas}}^2)}$ preventing BI double-counting at $\tau = 1\text{ s}$ (`EQ-52`).
   - `InverseCalibrator` bounded Trust-Region Reflective multi-objective optimization (`EQ-53`) fitting 10 hidden parasitic parameters across Static AVAR+PSD (Stage A), Slow Rate-Ramp Deadband/Bunny Ears (Stage B), and Thermal Chamber Ramp (Stage C), outputting `calibrated_params.json` with Gauss–Newton covariance and 95% confidence intervals.

---

## 2. Normative Mathematical Specifications (`EQ-45` .. `EQ-53`)

> **Equation Numbering Cross-Reference:** Because `IFOG-SIM-SPEC-004` (`EQ-01`..`EQ-30`), `SPEC-005` (`EQ-31`..`EQ-41`), and `SPEC-006` (`EQ-42`..`EQ-44`) are SHA-256 locked (Rule 7), the 9 normative `SPEC-007` equations are assigned sequential global IDs **`EQ-45`..`EQ-53`** with explicit traceability to the draft numbering (`EQ-40`..`EQ-48`):

| Global ID | Draft Ref | Section | Mathematical Scope | Primary Implementation |
| :--- | :---: | :---: | :--- | :--- |
| **`EQ-45`** | `EQ-40` | §2.1a | Discrete Quadrupole / Octupole turn-by-turn winding map $(r_i, z_{\text{ax},i}, \delta z_{\text{quad}})$ | `tier1_offline/shupe_thermal.py` |
| **`EQ-46`** | `EQ-41` | §2.1b | Total thermo-optical phase $\Delta\phi_{\text{therm}} = \Delta\phi_{\text{Shupe}} + \Delta\phi_{\text{stress}}$ | `tier1_offline/shupe_thermal.py` |
| **`EQ-47`** | `EQ-42` | §2.2a | Dynamic Sagnac scale factor $K_{\text{opt}}(t)$ thermal/SLD/back-power drift | `tier1_offline/shupe_thermal.py`, `ifog_math.hpp` |
| **`EQ-48`** | `EQ-43` | §2.2b | Time-varying $V_{\text{eff}}(t)$, $\Delta\phi_{\text{pol}}(t)$, and $V_\pi(t)$ | `tier1_offline/shupe_thermal.py` |
| **`EQ-49`** | `EQ-44` | §2.3 | Binary LUT v2 (`24 B` `<4sIQd` + `56 B` `<7d`), $O(1)$ 6-ch interp & v1 fallback | `shupe_thermal.py`, `ifog_config.cpp`, `ifog_math.hpp` |
| **`EQ-50`** | `EQ-45` | §2.4a | MIOC $\text{LiNbO}_3$ electrode cutoff + 2nd-order electro-acoustic dynamics | `ifog_math.hpp`, `optical_envelope_tdf.cpp` |
| **`EQ-51`** | `EQ-46` | §2.4b | Capacitive + resistive PCB crosstalk $i_{\text{xtalk}}[k]$ & $C_{\text{xtalk}}=0$ reduction | `ifog_math.hpp`, `analog_frontend_tdf.cpp` |
| **`EQ-52`** | `EQ-47` | §2.5 | Rayleigh + facet back-reflection $\sigma_{\phi,\text{back}}$ & Tier 3 BI anti-double-counting | `config_loader.py`, `optical_envelope_tdf.cpp`, `dual_regime_avar.py` |
| **`EQ-53`** | `EQ-48` | §2.6 | Weighted multi-objective inverse parameter identification (`< 5%` error) | `tier3_analysis/inverse_calibration.py`, `scenarios_spec007.py` |

### 2.1 Discrete Winding & Thermo-Mechanical Stress-Optic Drift (`EQ-45`, `EQ-46`)

For discrete fiber turns $i \in \{0, \dots, N_{\text{turns}}-1\}$ at arc-length coordinates $z_i = (i + \tfrac{1}{2}) L / N_{\text{turns}} \in (0, L)$ across $N_{\text{layers}}$ radial layers of coil thickness $d_{\text{coil}}$ and mean diameter $D$:

$$
r_i = \frac{D - d_{\text{coil}}}{2} + \ell(i)\,\frac{d_{\text{coil}}}{N_{\text{layers}} - 1}, \qquad
z_{\text{ax},i} = H_{\text{coil}}\begin{cases} f_{\text{ax}}(i), & \ell(i)\text{ even} \\ 1 - f_{\text{ax}}(i), & \ell(i)\text{ odd} \end{cases}
$$

where the layer parity $\ell(i)$ implements either a 4-layer **Quadrupole (`ABBA`)** block or a doubly-balanced 8-layer **Octupole (`ABBA-BAAB`)** block cancelling both linear and quadratic radial temperature gradients, plus end-flange layer-transition offsets $\delta z_{\text{flange}}(i)$.

The total thermo-optical non-reciprocal phase combines classical Shupe thermal expansion with elasto-optic potting stress (`EQ-46`):

$$
\Delta\phi_{\text{therm}}(t) = \Delta\phi_{\text{Shupe}}(t) + \Delta\phi_{\text{stress}}(t)
$$

$$
\Delta\phi_{\text{stress}}(t) = \frac{2\pi}{\bar{\lambda} c}\,C_{\text{eo}} \int_0^L \frac{\partial \sigma_{\text{eff}}(z, t)}{\partial t}\,\big(L - 2z + \delta z_{\text{quad}}(z)\big)\,dz
$$

where $C_{\text{eo}}\;[\text{Pa}^{-1}]$ is the effective elasto-optic stress coefficient and $\partial \sigma_{\text{eff}} / \partial t\;[\text{Pa/s}]$ is interpolated from thermo-mechanical 1D/2D/FEM stress profiles.

### 2.2 Dynamic Scale Factor & Time-Varying Optical Parameters (`EQ-47`, `EQ-48`)

$$
K_{\text{opt}}(t) = K_{\text{opt},0} \left[ 1 + \alpha_{\text{bobbin}}\,\Delta T_{\text{coil}}(t) - \frac{\alpha_{\lambda}\,\Delta T_{\text{SLD}}(t) + \kappa_{\text{back}}\,P_{\text{back}}(t)}{\bar{\lambda}_0} + \frac{1}{n_{\text{eff},0}}\frac{\partial n_{\text{eff}}}{\partial T}\Delta T_{\text{coil}}(t) \right]
$$

$$
V_{\text{eff}}(t) = V_{\text{eff},0}\big(1 - \beta_V |\Delta T_{\text{coil}}(t)|\big), \qquad
\Delta\phi_{\text{pol}}(t) = \Delta\phi_{\text{pol},0} + \gamma_{\text{pol}}\,\Delta T_{\text{coil}}(t), \qquad
V_\pi(t) = V_{\pi 0}\big(1 + \alpha_{V_\pi}\Delta T_{\text{MIOC}}(t)\big)
$$

### 2.3 Binary Lookup Table Format v2 (`shupe_lut.bin`) (`EQ-49`)

| Section | Offset | Size | Struct Format | Fields |
| :--- | ---: | ---: | :---: | :--- |
| **Header** | `0 B` | `24 B` | `<4sIQd` | `magic = b"SHUP"`, `version = 2` (or `1`), `n_samples` (`uint64`), `dt_s` (`float64`) |
| **Record (v2)** | `24 + 56*i` | `56 B` | `<7d` | `[t_s, delta_phi_shupe_rad, delta_phi_stress_rad, visibility_V_t, phi_pol_rad_t, v_pi_V_t, k_opt_scale_rel_t]` |
| **Record (v1 fallback)** | `24 + 16*i` | `16 B` | `<2d` | `[t_s, delta_phi_shupe_rad]` (auto-upgraded with `stress=0, V=cfg.V, phi_pol=cfg.phi_pol, V_pi=cfg.V_pi_0, k_opt_rel=1`) |

Tier 2 (`OpticalEnvelope_TDF`) performs $O(1)$ direct-index linear interpolation across all 6 dependent channels at every TDF step $t_k = k \Delta t_{\text{fast}}$ with `< 1e-12 rad` interpolation accuracy.

### 2.4 MIOC Electro-Acoustic Dynamics & Capacitive-Resistive Crosstalk (`EQ-50`, `EQ-51`)

The $\text{LiNbO}_3$ MIOC phase modulator filters $V_{\text{dac}}[k]$ through an electrode cutoff $\omega_{\text{mioc}} = 2\pi f_{\text{elec}}$ cascaded with an exact ZOH 2nd-order acoustic resonance $(\omega_{\text{ac}}, \zeta_{\text{ac}}, g_{\text{ac}})$ before applying coil transit delay $K_{\text{delay}} = \operatorname{round}(\tau_s f_s)$:

$$
V_{\text{elec}}[k] = e^{-\omega_{\text{mioc}}\Delta t}\,V_{\text{elec}}[k-1] + \big(1 - e^{-\omega_{\text{mioc}}\Delta t}\big)V_{\text{dac}}[k], \qquad
V_{\text{mioc,eff}}[k] = V_{\text{elec}}[k] + g_{\text{ac}}\big(V_{\text{ac}}[k] - V_{\text{elec}}[k]\big)
$$

$$
\Delta\phi_{\text{fb}}[k] = \frac{\pi}{V_\pi(t_k)}\,V_{\text{mioc,eff}}[k - K_{\text{delay}}]
$$

Physical PCB/package crosstalk current injected at the TIA inverting summing node in `AnalogFrontEnd_TDF` (`EQ-51`):

$$
i_{\text{xtalk}}[k] = G_{\text{xtalk}}\,V_{\text{dac}}[k] + C_{\text{xtalk}}\,\frac{V_{\text{dac}}[k] - V_{\text{dac}}[k-1]}{\Delta t_{\text{TDF}}}
$$

When $C_{\text{xtalk}} = 0$, `EQ-51` reduces identically to the legacy `SPEC-004` resistive term $G_{\text{xtalk}} V_{\text{dac}}[k]$; when $C_{\text{xtalk}} > 0$, total capacitive spike charge is conserved identically: $\sum_k i_{\text{cap}}[k]\,\Delta t_{\text{TDF}} = C_{\text{xtalk}}\Delta V_{\text{dac}}$.

### 2.5 Coherent Rayleigh/Facet Backscattering & BI Stitch Integrity (`EQ-52`)

$$
L_c = \frac{c}{\Delta\nu_{\text{eff}}}, \qquad
\sigma_{\phi,\text{back}} = 2\sqrt{R_{\text{facet}} + \frac{1}{2}\alpha_R\,S_{\text{capture}}\,L_c}, \qquad
\Delta\phi_{\text{back}}[k] = \sigma_{\phi,\text{back}}\sin\!\big(\theta_{\text{env}}[k]\big)
$$

where $\theta_{\text{env}}[k]$ evolves as a zero-mean Ornstein–Uhlenbeck process with correlation time $\tau_{\text{env}}$. To prevent double-counting Bias Instability across the Tier 2 / Tier 3 boundary ($\tau = 1\text{ s}$), `DualRegimeStitcher` computes the residual Tier 3 mechanical BI in quadrature:

$$
B_{\text{T3,mech}} = \sqrt{\max\!\big(0,\; B_{\text{total}}^2 - B_{\text{T2,meas}}^2\big)}
$$

### 2.6 Inverse Parameter Identification Objective (`EQ-53`)

For parameter vector $\boldsymbol{\theta} = [C_{\text{xtalk}}, G_{\text{xtalk}}, c_{1/f}, R_{\text{facet}}, \alpha_{\text{th,pot}}, \delta z_{\text{quad}}, \alpha_{V_\pi}, \alpha_{\text{bobbin}}]^T$ (plus optical conversion $\eta_{\text{PD}}$ and DAC asymmetry $\delta_{\text{DAC}}$):

$$
\min_{\boldsymbol{\theta} \in \mathcal{B}}\;
w_{\text{avar}}\left\|\log_{10}\frac{\sigma_{\text{sim}}(\tau; \boldsymbol{\theta})}{\sigma_{\text{meas}}(\tau)}\right\|_2^2
+ w_{\text{db}}\left\|\frac{\Omega_{\text{out,sim}}(\Omega_{\text{in}}; \boldsymbol{\theta}) - \Omega_{\text{out,meas}}(\Omega_{\text{in}})}{\Omega_{\text{norm}}}\right\|_2^2
+ w_{\text{th}}\left\|\frac{\Omega_{\text{bias,sim}}(T(t); \boldsymbol{\theta}) - \Omega_{\text{bias,meas}}(T(t))}{\Omega_{\text{th,norm}}}\right\|_2^2
$$

Parameter covariance and 95% confidence intervals are computed via Gauss–Newton Jacobian inversion:

$$
\mathbf{\Sigma}_{\hat{\theta}} = s^2 \big(\mathbf{J}^T \mathbf{J} + \lambda \mathbf{I}\big)^{-1}, \qquad
\text{CI}_{95,j} = \pm 1.96\sqrt{(\mathbf{\Sigma}_{\hat{\theta}})_{jj}}
$$

---

## 3. FMI 3.0 Tunable Parameter Contract (`VR 0` .. `VR 21`)

All 15 `SPEC-006` variables (`VR 0..14`) remain bit-exact; `SPEC-007` appends 7 tunable calibration variables (`VR 15..21`):

| VR | Name | Type | Causality | Variability | Unit | Start | Description |
| :---: | :--- | :---: | :---: | :---: | :---: | ---: | :--- |
| `15` | `C_xtalk_F` | `Float64` | `parameter` | `tunable` | `F` | `2.0e-12` | Capacitive PCB/package DAC-to-TIA crosstalk $C_{\text{xtalk}}$ (`EQ-51`) |
| `16` | `G_xtalk_S` | `Float64` | `parameter` | `tunable` | `S` | `1.0e-8` | Resistive DAC-to-TIA leakage conductance $G_{\text{xtalk}}$ (`EQ-51`) |
| `17` | `c_pink_coeff` | `Float64` | `parameter` | `tunable` | `1` | `1.0` | Tunable $1/f$ flicker amplitude multiplier (`EQ-53`) |
| `18` | `R_facet_dB` | `Float64` | `parameter` | `tunable` | `dB` | `-200.0` | Residual MIOC pigtail facet reflectivity $R_{\text{facet}}$ (`EQ-52`) |
| `19` | `alpha_vpi_ppm_K` | `Float64` | `parameter` | `tunable` | `ppm/K` | `0.0` | MIOC $V_\pi$ thermal coefficient $\alpha_{V_\pi}$ (`EQ-48`) |
| `20` | `alpha_bobbin_ppm_K` | `Float64` | `parameter` | `tunable` | `ppm/K` | `0.0` | Bobbin thermal expansion coefficient $\alpha_{\text{bobbin}}$ (`EQ-47`) |
| `21` | `delta_z_quad_m` | `Float64` | `parameter` | `tunable` | `m` | `0.002` | Winding asymmetry residual $\delta z_{\text{quad}}$ (`EQ-45`) |

---

## 4. Verification & Acceptance Criteria (`PHY-01` & `CAL-01`)

1. **Formula Matrix (Rule 3):** All **53 / 53** formulas (`EQ-01`..`EQ-53`) verified independently in CI (`scripts/verify_formulas_ci.py`).
2. **Dual-Domain 100% Coverage (Rules 2 & 14):** C++ `gcovr` = **100.0%** across `tier2_sysc_ams/` + `fmi_wrapper/src/`; Python `pytest-cov` = **100.00%** across `tier1_offline/`, `tier3_analysis/`, and `viz/`.
3. **PHY-01 Predictive Physics Gate:** LUT v2 roundtrip `< 1e-15 rad`, Octupole drift strictly lower than Quadrupole (`~47.7%` reduction), measurable capacitive + MIOC acoustic transient on $V_{\text{TIA}}(t)$, and exact quadrature BI conservation.
4. **CAL-01 Inverse Calibration Gate:** Reduces Static AVAR, Slow-Rate Deadband/Bunny Ears, and Thermal Chamber Bias prediction error from uncalibrated baseline (`> 40%` error) to **`< 5%` error**, recovers all 10 hidden parameters within **`< 5%` error**, and achieves **`< 5%`** error on live Tier 2 SystemC-AMS closed-loop validation.
