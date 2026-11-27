---
name: ifog-industrial-trl7-do254
description: Operate, verify, and extend the v4.1.0 Group E TRL 7-8 / DO-254 Industrial Qualification Suite (IND-01..IND-06): physical lab CSV CAS-4 ingestion, Q16.32 fixed-point FPGA DSP + SystemVerilog RTL (2/4/6-State), 3D ANSYS/COMSOL FEM to shupe_lut.bin v2, MIL-STD-810H / DO-160G broadband random vibration PSD, multi-instance Source-Code FMI 3.0.2 FMU, and 12-corner PVT / 10-yr 50 krad(Si) aging analysis.
---

# IFOG Industrial TRL 7-8 / DO-254 Qualification Skill (`v4.1.0`)

## Scope
Covers all 6 industrial qualification scenarios (`IND-01`..`IND-06`) introduced in `v4.1.0` plus full **2-State / 4-State / 6-State DSP** coverage across Tier 2 C++, SystemVerilog RTL, FMI 3.0.2 Multi-Instance FMU, and Tier 3 analysis.

## Key Modules & Artifacts
- **IND-01 Physical Lab CAS-4 Validation:** `tier3_analysis/lab_validation.py`, `configs/lab_datasets/reference_ifog_lab/{static_avar_10h,rate_table_deadband,thermal_chamber_ramp}.csv`
- **IND-02 Bit-True Fixed-Point FPGA DSP & SV RTL:** `tier2_sysc_ams/include/ifog_math.hpp` (`quantize_fixed_signed`), `tier2_sysc_ams/src/digital_dsp_sc.cpp`, `rtl/ifog_dsp_6state.sv` (2/4/6-State selectable, Q16.32 48-bit)
- **IND-03 3D Cylindrical FEM Importer:** `tier1_offline/shupe_thermal.py` (`load_fem_3d_csv`, `generate_asymmetric_3d_fem_csv`, `solve_tier1_shupe_3d_fem` -> native 56-byte `shupe_lut.bin` v2)
- **IND-04 Broadband Random Vibration PSD:** `tier3_analysis/scenarios_industrial.py` (`mil_std_810h_cat24_psd`, `mechanical_transmissibility_2dof`, `run_ind04_random_vib_psd`)
- **IND-05 Multi-Instance Source-Code FMI 3.0.2 FMU:** `fmi_wrapper/src/fmi3_multi_bridge.cpp`, `fmi_wrapper/modelDescription_multi.xml.in` (`canBeInstantiatedOnlyOncePerProcess="false"`), `fmi_wrapper/buildDescription.xml`, `build/ifog_core_multi.fmu`
- **IND-06 12-Corner PVT & Space Aging/TID:** `tier3_analysis/scenarios_industrial.py` (`compute_aging_and_tid_factors`, `run_ind06_pvt_aging_corners`)
- **Visualization:** `viz/plot_industrial.py` (`fig_ind01_lab_validation.png`..`fig_ind06_pvt_aging_corners.png`)

## Standard Commands
```bash
# Build Tier 2 + both FMI 3.0.2 FMUs (SystemC-AMS + Pure-C++17 Multi-Instance Source-Code)
cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
cmake --build build --target package_fmu package_fmu_multi
./build/ifog_cpp_tests && ./build/ifog_fmi_multi_tests

# Run all 6 Group E industrial scenarios (or supply custom physical lab CSV directory)
./scripts/run_sim.sh --mode ind_all --lab-dir configs/lab_datasets/reference_ifog_lab --run-id ind_v41

# Verify 100.0% C++ & 100.00% Python coverage
bash scripts/run_cpp_coverage.sh
pytest tests/unit tests/formula_verification --cov --cov-report=term-missing --cov-fail-under=100
```
