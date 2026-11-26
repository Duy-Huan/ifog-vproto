---
name: ifog-spec007-physics-calibration
description: Engineering invariants, physical identifiability rules, binary LUT v2 contract, FMI 3.0 tunability (VR 15..21), and 3-stage bounded Inverse Calibration workflow for IFOG-SIM-SPEC-007 (EQ-45..EQ-53, PHY-01, CAL-01).
---

# Skill: `IFOG-SIM-SPEC-007` High-Fidelity Predictive Physics & Inverse Calibration

## Scope & Files
- **Normative Spec:** `spec/IFOG-SIM-SPEC-007.{md,tex,pdf,sha256}` (`EQ-45`..`EQ-53`, mapping draft `EQ-40`..`EQ-48` without colliding with locked `SPEC-005` `EQ-31`..`EQ-41` and `SPEC-006` `EQ-42`..`EQ-44`).
- **Config & Schema:** `configs/schema_v6.json` (backward-compatible with `"4.0"`, `"5.0"`, `"6.0"`), `configs/baseline_1km_spec007.json`, `tier1_offline/config_loader.py`.
- **Tier 1 Solvers:** `tier1_offline/shupe_thermal.py` (`build_winding_map`, `elasto_optic_stress_integral`, `compute_dynamic_k_opt_rel`, `compute_dynamic_optical_params`, `write_shupe_lut_v2`, `read_shupe_lut_v2`, `solve_tier1_shupe_v2`), `tier1_offline/jones_spectral.py` (`L_coherence_m`, `sigma_phi_back_rad`).
- **Tier 2 Core & FMI 3.0:** `tier2_sysc_ams/{include,src}/ifog_types.hpp`, `ifog_math.hpp`, `ifog_config.{hpp,cpp}`, `optical_envelope_tdf.{hpp,cpp}`, `analog_frontend_tdf.{hpp,cpp}`, `ifog_top_module.{hpp,cpp}`, `fmi_wrapper/{modelDescription.xml.in,src/fmi3_bridge.cpp}`.
- **Tier 3 Calibration & Viz:** `tier3_analysis/dual_regime_avar.py` (`compute_residual_tier3_bi`, `DualRegimeStitcher`), `tier3_analysis/inverse_calibration.py` (`InverseCalibrator`), `tier3_analysis/scenarios_spec007.py` (`PHY-01`, `CAL-01`), `viz/plot_spec007_calibration.py`.

## Key Invariants & Lessons Learned

1. **Equation Numbering Collision Guard (Rule 7):**
   - `SPEC-004` locks `EQ-01..EQ-30`; `SPEC-005` locks `EQ-31..EQ-41`; `SPEC-006` locks `EQ-42..EQ-44`.
   - All 9 `SPEC-007` equations are canonically numbered **`EQ-45..EQ-53`** with an explicit cross-reference table to draft `EQ-40..EQ-48`.

2. **Binary `shupe_lut.bin` v2 & Backward-Compatible v1 Fallback (`EQ-49`):**
   - Header is `24 B` (`<4sIQd`: `magic="SHUP"`, `version=2`, `n_samples`, `dt_s`).
   - Each v2 record is `56 B` (`<7d`, `static_assert(sizeof(ShupeLutRecordV2) == 56)`): `(t_s, phi_shupe_rad, phi_stress_rad, dK_opt_rel, V_eff, phi_pol_rad, V_pi_V)`.
   - Both Python (`read_shupe_lut_v2`) and C++ (`load_shupe_lut_v2`) auto-detect `version == 1` (`16 B <2d`) and seamlessly promote records to v2 layout using baseline nominal values (`phi_stress=0`, `dK_opt_rel=0`, nominal `V`, `phi_pol`, `V_pi`).

3. **Exact Reduction to `SPEC-004` & Gate 6 Bit-Exactness (`EQ-50`, `EQ-51`):**
   - `MiocDynamicsFilter` runs BEFORE the $\tau$-delay ring buffer ($K_{\text{delay}}$ samples); when `en_mioc_dynamics = false`, `V_eff_mioc = V_drv` identically.
   - `compute_capacitive_crosstalk_A`: $i_{\text{xtalk}}[k] = G_{\text{xtalk}} V_{\text{drv}}[k] + C_{\text{xtalk}} (V_{\text{drv}}[k] - V_{\text{drv}}[k-1]) / \Delta t_{\text{fast}}$ reduces to $G_{\text{xtalk}} V_{\text{drv}}[k]$ when $C_{\text{xtalk}} = 0$.
   - In `fmi3_bridge.cpp`, maintain `bool spec007_tuned = false` until a master explicitly invokes `fmi3SetFloat64` on ANY of `VR 15..21`; this preserves `0.00e+00 rad/s` bit-exact Gate 6 equivalence while enabling live FMI 3.0 parameter sweeps (`C_xtalk_F`, `G_xtalk_S`, `c_pink_coeff`, `R_facet_dB`, `alpha_vpi_ppm_K`, `alpha_bobbin_ppm_K`, `delta_z_quad_m`).

4. **Anti-Double-Counting BI Stitching (`EQ-52`):**
   - `DualRegimeStitcher` / `compute_residual_tier3_bi` ALWAYS enforces $B_{\text{T3,mech}} = \sqrt{\max(0, B_{\text{total}}^2 - B_{\text{T2,meas}}^2)}$ so Tier 2 electronic $1/f$ + back-reflection BI is never double-counted in Tier 3 slow-scale AVAR synthesis.

5. **Physical Identifiability in 3-Stage `InverseCalibrator` (`EQ-53`):**
   - **Stage A (Static AVAR):** Separates broadband electronic $1/f$ (`c_pink_coeff`, flat plateau across all $\tau$) from coherent Rayleigh/facet cavity back-reflection (`R_facet_dB`, band-limited Ornstein–Uhlenbeck Lorentzian with corner `f_corner_back_Hz = 0.015 Hz`) plus white ARW (`RIN_dB_Hz`) and long-term RRW (`K_rrw_deg_h32`). Use decade-balanced relative RMS error in log-AVAR space.
   - **Stage B (Slow Rate Ramp):** Separates resistive crosstalk (`G_xtalk_S`, drives Deadband half-width across blanking window) from capacitive spike crosstalk (`C_xtalk_F`, drives Bunny Ears overshoot amplitude).
   - **Stage C (Thermal Chamber):** Maps 1D radial heat diffusion symmetrically around the coil midpoint $L/2$ (`r_sym = |2z/L - 1|`), cancelling the symmetric `(L - 2z)` integral so `delta_z_quad_m` and `diffusivity_m2_per_s` are independently identifiable alongside `alpha_vpi_ppm_K` and `alpha_bobbin_ppm_K`.
   - **Verified `CAL-01` Performance:** Reduces uncalibrated baseline error (`40–103%`) to `< 1%` across all 4 validation domains (AVAR `0.81%`, Deadband `0.91%`, Thermal Bias `0.29%`, Scale Factor `0.04%`), recovers all 10 hidden parameters within `<= 2.18%`, and exports `calibrated_params.json` with Gauss–Newton 95% confidence intervals.

## Verification Checklist
1. `python3 scripts/verify_formulas_ci.py` -> **53 / 53 PASS** (`EQ-01..EQ-53`).
2. `bash scripts/run_cpp_coverage.sh` -> **100.0%** line & function coverage across `tier2_sysc_ams/` + `fmi_wrapper/src/`.
3. `pytest tests/unit tests/formula_verification --cov` -> **100.00%** Python line coverage.
4. `pytest tests/system/test_spec007_system.py -v` -> `PHY-01`, `CAL-01`, and live FMI 3.0 `VR 15..21` tunability PASS.
5. `./scripts/run_sim.sh --mode spec007_all --run-id spec007_demo` -> generates `fig_spec007_physics_winding_mioc.png`, `fig_spec007_calibration_validation.png`, `calibrated_params.json`, `report.md`, and `report.html`.
