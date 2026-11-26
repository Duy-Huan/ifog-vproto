---
name: ifog-fmi3-cosim-fmu
description: Industrial FMI 3.0 Co-Simulation FMU packaging skill for Accellera SystemC + SystemC-AMS cores (IFOG-SIM-SPEC-006), covering -fPIC shared libs, sc_main dlopen stub, all 75 FMI 3.0 C-API symbols, singleton sc_simcontext subprocess isolation, anti-aliased macro-step averaging, and 100% dual C++/Python coverage.
---

# FMI 3.0 Co-Simulation FMU Packaging for SystemC/SystemC-AMS (`fmi_wrapper/`)

## 1. Proven Engineering Invariants & Pitfalls (`IFOG-SIM-SPEC-006`)

1. **TRAP #1 — `libsystemc.so` Unresolved `sc_main` Inside `dlopen()`'d Shared Libraries:**
   - Distro & source-built Accellera `libsystemc.so` defines `main()` referencing `sc_main(int, char**)`. When Python/FMPy loads `binaries/x86_64-linux/ifog_core.so` via `dlopen()`, a missing `sc_main` fails linking/loading.
   - **FIX:** Export `extern "C" int sc_main(int, char**) { return 0; }` guarded by `-DIFOG_FMI_DEFINE_SC_MAIN_STUB` strictly on the shared library target (`ifog_core_fmu`), NOT on C++ test executables that define their own `sc_main()`.

2. **TRAP #2 — FMPy `FMU3Slave.__init__` Eagerly Loads ALL 75 FMI 3.0 C Symbols:**
   - Even for a Co-Simulation-only FMU (`hasEventMode="false"`), FMPy's `FMU3Slave._loadFunctions()` iterates all 75 C functions declared in `fmi3Functions.h` and raises `AttributeError: undefined symbol: fmi3ActivateModelPartition` if any symbol is omitted.
   - **FIX:** Export all 75 official FMI 3.0 C symbols in `fmi_wrapper/src/fmi3_bridge.cpp` (returning `nullptr` / `fmi3Error` for unsupported ME/SE/Clock/FMUState/unused scalar APIs) and call every single symbol inside `tier2_sysc_ams/src/fmi_unit_tests.cpp` to preserve **100.0% C++ line & function coverage**.

3. **TRAP #3 — SystemC `sc_simcontext` Singleton Lifecycle & Parameter Initialization Order:**
   - Accellera SystemC 2.3.4 cannot reset or re-elaborate `sc_simcontext` twice in one OS process. Furthermore, FMPy applies `start_values` (`dsp_mode`, `eps_vpi`, `k_xtalk`, `enable_dither`, `seed`) AFTER `fmi3InstantiateCoSimulation` and DURING Initialization Mode before `fmi3ExitInitializationMode`.
   - **FIX:**
     - Declare `canBeInstantiatedOnlyOncePerProcess="true"` on `<CoSimulation>` in `modelDescription.xml.in` and enforce an atomic process singleton flag in `fmi3_bridge.cpp`.
     - Load `resources/{phys_params.json, baseline_cfg.json, shupe_lut.bin}` in `fmi3InstantiateCoSimulation`, but construct `IfogTopModule` and execute `sc_start(SC_ZERO_TIME)` in `fmi3ExitInitializationMode` after all fixed parameters are configured.
     - In `tier3_analysis/fmi_master_runner.py`, run every `fmpy.simulate_fmu()` invocation inside a fresh isolated worker subprocess (`--worker-job` / `--worker-out`) with lazy `scipy` imports so multi-run sweeps & parallel AVAR ensembles stay fast and crash-free.

4. **TRAP #4 — FMPy `step_size` vs `output_interval` for FMI 3.0 Co-Simulation:**
   - In `fmpy.simulate_fmu()`, `step_size` controls ME solvers while `output_interval` controls the Co-Simulation macro communication step size passed to `fmi3DoStep`.
   - **FIX:** Always pass both `step_size=H` and `output_interval=H` to `fmpy.simulate_fmu(..., fmi_type="CoSimulation")`, and set `<DefaultExperiment stepSize="1.0e-3"/>` in `modelDescription.xml.in`.

5. **TRAP #5 — Macro-Step Aliasing vs Bit-Exact Equivalence (`EQ-42` & `EQ-44`):**
   - Instantaneous `omega_out` (`vr=3`) matches standalone `build/ifog_sim` bit-for-bit (**`0.00e+00 rad/s < 1e-12`** on both 4-state & 6-state modes with identical seeds!).
   - Sampling instantaneous `omega_out` at $H = 1\text{ ms}$ ($1\text{ kHz} < 2 f_{-3\text{dB,CL}}$) aliases wideband white noise; therefore `IfogTopModule` ALSO exports anti-aliased macro-step interval-averaged `omega_out_avg` (`vr=14`, boxcar mean over all $N_{\tau,k}$ clusters in $[t_k, t_k+H)$), preserving exact true ARW (`0.53%` WLS error, `3.83% < 5%` Dual-Regime overlap continuity!).

6. **TRAP #6 — FMI 3.0 XSD Strictness (`fmpy.validation.validate_fmu`):**
   - FMI 3.0 binary path MUST use `<arch>-<os>` (`binaries/x86_64-linux/ifog_core.so`), NOT FMI 2.0's `linux64`.
   - Non-float variables (`UInt32 bit_status`, `Int32 dsp_mode`, `Boolean enable_dither`) MUST NOT have `variability="continuous"`.
   - Every `output` with `initial="calculated"` MUST appear in BOTH `<Output valueReference="..."/>` AND `<InitialUnknown valueReference="..."/>` inside `<ModelStructure>`.
   - Set `BUILD_RPATH` / `INSTALL_RPATH` to `$ORIGIN;${SYSTEMC_AMS_LIB_DIR};${SYSTEMC_LIB_DIR}` on `ifog_core_fmu` so `dlopen()` locates `libsystemc-ams.so` and `libsystemc.so` automatically in any temp unzip directory.

## 2. Build & Verification Commands
```bash
cmake -S tier2_sysc_ams -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
cmake --build build --target package_fmu
python3 -c "from fmpy.validation import validate_fmu; assert not validate_fmu('build/ifog_core.fmu')"
bash scripts/run_cpp_coverage.sh
./scripts/run_sim.sh --mode fmi_gate --run-id gate6_fmi3_fmu
```
