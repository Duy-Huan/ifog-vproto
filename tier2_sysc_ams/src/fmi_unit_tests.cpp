#include <cmath>
#include <cstring>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <systemc-ams.h>
#include <systemc.h>
#include <vector>

#include "fmi3/fmi3Functions.h"
#include "ifog_config.hpp"
#include "ifog_top_module.hpp"
#include "ifog_types.hpp"

namespace {

#define FMI_CHECK(cond, msg)                                                           \
    do {                                                                               \
        if (!(cond)) {                                                                 \
            throw std::runtime_error(std::string("FMI_TEST_FAIL: ") + (msg));          \
        }                                                                              \
    } while (false)

constexpr const char* kToken = "{6e9c4b1a-7f20-4f06-9a5c-000000000006}";

int g_log_count = 0;

void test_log_callback(
    fmi3InstanceEnvironment,
    fmi3Status,
    fmi3String,
    fmi3String
) {
    ++g_log_count;
}

void test_pre_instantiation_guards(const std::string& res_dir) {
    FMI_CHECK(std::strcmp(fmi3GetVersion(), "3.0") == 0, "fmi3GetVersion == 3.0");

    // Null instance guards across every exported FMI 3.0 function
    fmi3ValueReference vr = 1u;
    fmi3Float64 fv = 0.0;
    fmi3Boolean bv = fmi3False;
    fmi3Int32 iv = 0;
    fmi3UInt32 uv = 0u;
    fmi3Boolean ev = fmi3False;
    fmi3Boolean term = fmi3False;
    fmi3Boolean early = fmi3False;
    fmi3Float64 last_t = 0.0;

    FMI_CHECK(fmi3SetDebugLogging(nullptr, fmi3True, 0, nullptr) == fmi3Error, "null SetDebugLogging");
    FMI_CHECK(fmi3EnterInitializationMode(nullptr, fmi3False, 0.0, 0.0, fmi3False, 0.0) == fmi3Error, "null EnterInit");
    FMI_CHECK(fmi3ExitInitializationMode(nullptr) == fmi3Error, "null ExitInit");
    FMI_CHECK(fmi3DoStep(nullptr, 0.0, 1e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3Error, "null DoStep");
    FMI_CHECK(fmi3SetFloat64(nullptr, &vr, 1, &fv, 1) == fmi3Error, "null SetFloat64");
    FMI_CHECK(fmi3GetFloat64(nullptr, &vr, 1, &fv, 1) == fmi3Error, "null GetFloat64");
    FMI_CHECK(fmi3SetBoolean(nullptr, &vr, 1, &bv, 1) == fmi3Error, "null SetBoolean");
    FMI_CHECK(fmi3GetBoolean(nullptr, &vr, 1, &bv, 1) == fmi3Error, "null GetBoolean");
    FMI_CHECK(fmi3SetInt32(nullptr, &vr, 1, &iv, 1) == fmi3Error, "null SetInt32");
    FMI_CHECK(fmi3GetInt32(nullptr, &vr, 1, &iv, 1) == fmi3Error, "null GetInt32");
    FMI_CHECK(fmi3GetUInt32(nullptr, &vr, 1, &uv, 1) == fmi3Error, "null GetUInt32");
    FMI_CHECK(fmi3Terminate(nullptr) == fmi3Error, "null Terminate");
    FMI_CHECK(fmi3Reset(nullptr) == fmi3Error, "null Reset");
    fmi3FreeInstance(nullptr);  // Must be safe no-op

    // Invalid instantiation tokens & resourcePath URI forms (exercises all normalize_resource_path branches)
    FMI_CHECK(
        fmi3InstantiateCoSimulation("bad", nullptr, res_dir.c_str(), fmi3False, fmi3True,
                                    fmi3False, fmi3False, nullptr, 0, nullptr, test_log_callback, nullptr) == nullptr,
        "null token rejected"
    );
    FMI_CHECK(
        fmi3InstantiateCoSimulation("bad", "wrong-token", res_dir.c_str(), fmi3False, fmi3True,
                                    fmi3False, fmi3False, nullptr, 0, nullptr, nullptr, nullptr) == nullptr,
        "wrong token rejected"
    );
    FMI_CHECK(
        fmi3InstantiateCoSimulation("bad", kToken, nullptr, fmi3False, fmi3True,
                                    fmi3False, fmi3False, nullptr, 0, nullptr, test_log_callback, nullptr) == nullptr,
        "null resourcePath rejected"
    );

    const std::vector<std::string> bad_uris = {
        "file://localhost/nonexistent_%20_%2f_%2F_%aB_%ZZ",
        "file:///C:/nonexistent_windows_path",
        "file:///nonexistent_triple_slash",
        "file://nonexistent_double_slash",
        "file:/nonexistent_single_slash",
    };
    for (const auto& uri : bad_uris) {
        FMI_CHECK(
            fmi3InstantiateCoSimulation("bad_uri", kToken, uri.c_str(), fmi3False, fmi3True,
                                        fmi3False, fmi3False, nullptr, 0, nullptr, test_log_callback, nullptr) == nullptr,
            "nonexistent URI rejected: " + uri
        );
    }
    FMI_CHECK(g_log_count > 0, "error log callback invoked");

    // Verify all remaining 59 FMI 3.0 binary-ABI symbols return nullptr / fmi3Error cleanly
    FMI_CHECK(fmi3InstantiateModelExchange(nullptr, nullptr, nullptr, fmi3False, fmi3False, nullptr, nullptr) == nullptr, "ME stub");
    FMI_CHECK(fmi3InstantiateScheduledExecution(nullptr, nullptr, nullptr, fmi3False, fmi3False, nullptr, nullptr, nullptr, nullptr, nullptr) == nullptr, "SE stub");
    FMI_CHECK(fmi3EnterEventMode(nullptr) == fmi3Error, "EnterEventMode stub");
    FMI_CHECK(fmi3EnterStepMode(nullptr) == fmi3Error, "EnterStepMode stub");
    FMI_CHECK(fmi3EnterConfigurationMode(nullptr) == fmi3Error, "EnterConfigMode stub");
    FMI_CHECK(fmi3ExitConfigurationMode(nullptr) == fmi3Error, "ExitConfigMode stub");
    FMI_CHECK(fmi3EnterContinuousTimeMode(nullptr) == fmi3Error, "EnterCTMode stub");
    FMI_CHECK(fmi3GetFloat32(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetFloat32 stub");
    FMI_CHECK(fmi3SetFloat32(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetFloat32 stub");
    FMI_CHECK(fmi3GetInt8(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetInt8 stub");
    FMI_CHECK(fmi3SetInt8(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetInt8 stub");
    FMI_CHECK(fmi3GetUInt8(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetUInt8 stub");
    FMI_CHECK(fmi3SetUInt8(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetUInt8 stub");
    FMI_CHECK(fmi3GetInt16(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetInt16 stub");
    FMI_CHECK(fmi3SetInt16(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetInt16 stub");
    FMI_CHECK(fmi3GetUInt16(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetUInt16 stub");
    FMI_CHECK(fmi3SetUInt16(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetUInt16 stub");
    FMI_CHECK(fmi3SetUInt32(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetUInt32 stub");
    FMI_CHECK(fmi3GetInt64(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetInt64 stub");
    FMI_CHECK(fmi3SetInt64(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetInt64 stub");
    FMI_CHECK(fmi3GetUInt64(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetUInt64 stub");
    FMI_CHECK(fmi3SetUInt64(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetUInt64 stub");
    FMI_CHECK(fmi3GetString(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "GetString stub");
    FMI_CHECK(fmi3SetString(nullptr, nullptr, 0, nullptr, 0) == fmi3Error, "SetString stub");
    FMI_CHECK(fmi3GetBinary(nullptr, nullptr, 0, nullptr, nullptr, 0) == fmi3Error, "GetBinary stub");
    FMI_CHECK(fmi3SetBinary(nullptr, nullptr, 0, nullptr, nullptr, 0) == fmi3Error, "SetBinary stub");
    FMI_CHECK(fmi3GetClock(nullptr, nullptr, 0, nullptr) == fmi3Error, "GetClock stub");
    FMI_CHECK(fmi3SetClock(nullptr, nullptr, 0, nullptr) == fmi3Error, "SetClock stub");
    FMI_CHECK(fmi3GetNumberOfVariableDependencies(nullptr, 0, nullptr) == fmi3Error, "NumVarDeps stub");
    FMI_CHECK(fmi3GetVariableDependencies(nullptr, 0, nullptr, nullptr, nullptr, nullptr, 0) == fmi3Error, "VarDeps stub");
    FMI_CHECK(fmi3GetFMUState(nullptr, nullptr) == fmi3Error, "GetFMUState stub");
    FMI_CHECK(fmi3SetFMUState(nullptr, nullptr) == fmi3Error, "SetFMUState stub");
    FMI_CHECK(fmi3FreeFMUState(nullptr, nullptr) == fmi3Error, "FreeFMUState stub");
    FMI_CHECK(fmi3SerializedFMUStateSize(nullptr, nullptr, nullptr) == fmi3Error, "SerSize stub");
    FMI_CHECK(fmi3SerializeFMUState(nullptr, nullptr, nullptr, 0) == fmi3Error, "SerState stub");
    FMI_CHECK(fmi3DeserializeFMUState(nullptr, nullptr, 0, nullptr) == fmi3Error, "DeserState stub");
    FMI_CHECK(fmi3GetDirectionalDerivative(nullptr, nullptr, 0, nullptr, 0, nullptr, 0, nullptr, 0) == fmi3Error, "DirDeriv stub");
    FMI_CHECK(fmi3GetAdjointDerivative(nullptr, nullptr, 0, nullptr, 0, nullptr, 0, nullptr, 0) == fmi3Error, "AdjDeriv stub");
    FMI_CHECK(fmi3GetIntervalDecimal(nullptr, nullptr, 0, nullptr, nullptr) == fmi3Error, "GetIntDec stub");
    FMI_CHECK(fmi3GetIntervalFraction(nullptr, nullptr, 0, nullptr, nullptr, nullptr) == fmi3Error, "GetIntFrac stub");
    FMI_CHECK(fmi3GetShiftDecimal(nullptr, nullptr, 0, nullptr) == fmi3Error, "GetShiftDec stub");
    FMI_CHECK(fmi3GetShiftFraction(nullptr, nullptr, 0, nullptr, nullptr) == fmi3Error, "GetShiftFrac stub");
    FMI_CHECK(fmi3SetIntervalDecimal(nullptr, nullptr, 0, nullptr) == fmi3Error, "SetIntDec stub");
    FMI_CHECK(fmi3SetIntervalFraction(nullptr, nullptr, 0, nullptr, nullptr) == fmi3Error, "SetIntFrac stub");
    FMI_CHECK(fmi3SetShiftDecimal(nullptr, nullptr, 0, nullptr) == fmi3Error, "SetShiftDec stub");
    FMI_CHECK(fmi3SetShiftFraction(nullptr, nullptr, 0, nullptr, nullptr) == fmi3Error, "SetShiftFrac stub");
    FMI_CHECK(fmi3EvaluateDiscreteStates(nullptr) == fmi3Error, "EvalDisc stub");
    FMI_CHECK(fmi3UpdateDiscreteStates(nullptr, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr) == fmi3Error, "UpdDisc stub");
    FMI_CHECK(fmi3CompletedIntegratorStep(nullptr, fmi3False, nullptr, nullptr) == fmi3Error, "CompIntStep stub");
    FMI_CHECK(fmi3SetTime(nullptr, 0.0) == fmi3Error, "SetTime stub");
    FMI_CHECK(fmi3SetContinuousStates(nullptr, nullptr, 0) == fmi3Error, "SetCS stub");
    FMI_CHECK(fmi3GetContinuousStateDerivatives(nullptr, nullptr, 0) == fmi3Error, "GetCSD stub");
    FMI_CHECK(fmi3GetEventIndicators(nullptr, nullptr, 0) == fmi3Error, "GetEI stub");
    FMI_CHECK(fmi3GetContinuousStates(nullptr, nullptr, 0) == fmi3Error, "GetCS stub");
    FMI_CHECK(fmi3GetNominalsOfContinuousStates(nullptr, nullptr, 0) == fmi3Error, "GetNomCS stub");
    FMI_CHECK(fmi3GetNumberOfEventIndicators(nullptr, nullptr) == fmi3Error, "GetNumEI stub");
    FMI_CHECK(fmi3GetNumberOfContinuousStates(nullptr, nullptr) == fmi3Error, "GetNumCS stub");
    FMI_CHECK(fmi3GetOutputDerivatives(nullptr, nullptr, 0, nullptr, nullptr, 0) == fmi3Error, "GetOutDeriv stub");
    FMI_CHECK(fmi3ActivateModelPartition(nullptr, 0, 0.0) == fmi3Error, "ActModPart stub");
}

void run_fmi_mode_test(const std::string& res_dir, int32_t dsp_mode, bool explicit_terminate) {
    test_pre_instantiation_guards(res_dir);

    const std::string uri = "file://" + res_dir;
    fmi3Instance inst = fmi3InstantiateCoSimulation(
        nullptr,
        kToken,
        uri.c_str(),
        fmi3False,
        fmi3True,
        fmi3False,
        fmi3False,
        nullptr,
        0,
        nullptr,
        test_log_callback,
        nullptr
    );
    FMI_CHECK(inst != nullptr, "valid instantiation succeeded");

    // Process singleton enforcement: second concurrent instantiation MUST fail
    FMI_CHECK(
        fmi3InstantiateCoSimulation("dup", kToken, res_dir.c_str(), fmi3False, fmi3True,
                                    fmi3False, fmi3False, nullptr, 0, nullptr, test_log_callback, nullptr) == nullptr,
        "second instantiation rejected per canBeInstantiatedOnlyOncePerProcess"
    );

    FMI_CHECK(fmi3SetDebugLogging(inst, fmi3False, 0, nullptr) == fmi3OK, "disable debug logging");
    FMI_CHECK(fmi3SetDebugLogging(inst, fmi3True, 0, nullptr) == fmi3OK, "enable debug logging");
    FMI_CHECK(fmi3EnterInitializationMode(inst, fmi3False, 0.0, 0.0, fmi3True, 0.01) == fmi3OK, "enter init");

    // Exercise Set/Get Float64, Boolean, Int32, UInt32 including error paths
    const fmi3ValueReference vr_f_set[4] = {1u, 2u, 6u, 7u};
    const fmi3Float64 val_f_set[4] = {0.02, 1.0e-5, 0.015, 2.0e-8};
    FMI_CHECK(fmi3SetFloat64(inst, vr_f_set, 4, val_f_set, 4) == fmi3OK, "set all float64");
    FMI_CHECK(fmi3SetFloat64(inst, vr_f_set, 4, val_f_set, 3) == fmi3Error, "mismatched SetFloat64 len");
    const fmi3ValueReference bad_vr = 999u;
    FMI_CHECK(fmi3SetFloat64(inst, &bad_vr, 1, val_f_set, 1) == fmi3Error, "bad VR SetFloat64");

    const fmi3ValueReference vr_f_get[8] = {0u, 1u, 2u, 3u, 4u, 6u, 7u, 14u};
    fmi3Float64 val_f_get[8] = {};
    FMI_CHECK(fmi3GetFloat64(inst, vr_f_get, 8, val_f_get, 8) == fmi3OK, "get all float64");
    FMI_CHECK(std::fabs(val_f_get[1] - 0.02) < 1e-15, "omega_in readback");
    FMI_CHECK(std::fabs(val_f_get[2] - 1.0e-5) < 1e-15, "shupe_phase_in readback");
    FMI_CHECK(std::fabs(val_f_get[5] - 0.015) < 1e-15, "eps_vpi readback");
    FMI_CHECK(std::fabs(val_f_get[6] - 2.0e-8) < 1e-15, "k_xtalk readback");
    FMI_CHECK(fmi3GetFloat64(inst, &bad_vr, 1, val_f_get, 1) == fmi3Error, "bad VR GetFloat64");

    // Exercise SPEC-007 FMI 3.0 tunable parameters (VR 15..21) in 6-state mode
    if (dsp_mode == 6) {
        const fmi3ValueReference vr_sp7[7] = {15u, 16u, 17u, 18u, 19u, 20u, 21u};
        const fmi3Float64 val_sp7_set[7] = {3.5e-12, 2.0e-8, 1.5, -62.0, 380.0, 12.0, 0.0025};
        fmi3Float64 val_sp7_get[7] = {};
        FMI_CHECK(fmi3SetFloat64(inst, vr_sp7, 7, val_sp7_set, 7) == fmi3OK, "set SPEC-007 float64");
        FMI_CHECK(fmi3GetFloat64(inst, vr_sp7, 7, val_sp7_get, 7) == fmi3OK, "get SPEC-007 float64");
        for (int idx = 0; idx < 7; ++idx) {
            FMI_CHECK(std::fabs(val_sp7_get[idx] - val_sp7_set[idx]) < 1e-15, "SPEC-007 VR readback");
        }
    }

    const fmi3ValueReference vr_b[4] = {8u, 10u, 11u, 12u};
    const fmi3Boolean val_b_set[4] = {fmi3True, fmi3False, fmi3False, fmi3True};
    fmi3Boolean val_b_get[4] = {};
    FMI_CHECK(fmi3SetBoolean(inst, vr_b, 4, val_b_set, 4) == fmi3OK, "set all boolean");
    FMI_CHECK(fmi3GetBoolean(inst, vr_b, 4, val_b_get, 4) == fmi3OK, "get all boolean");
    FMI_CHECK(val_b_get[0] == fmi3True && val_b_get[1] == fmi3False, "boolean readback");
    FMI_CHECK(fmi3SetBoolean(inst, &bad_vr, 1, val_b_set, 1) == fmi3Error, "bad VR SetBoolean");
    FMI_CHECK(fmi3GetBoolean(inst, &bad_vr, 1, val_b_get, 1) == fmi3Error, "bad VR GetBoolean");

    const fmi3ValueReference vr_i[2] = {9u, 13u};
    const fmi3Int32 val_i_set[2] = {dsp_mode, 42004};
    fmi3Int32 val_i_get[2] = {};
    FMI_CHECK(fmi3SetInt32(inst, vr_i, 2, val_i_set, 2) == fmi3OK, "set int32");
    FMI_CHECK(fmi3GetInt32(inst, vr_i, 2, val_i_get, 2) == fmi3OK, "get int32");
    FMI_CHECK(val_i_get[0] == dsp_mode && val_i_get[1] == 42004, "int32 readback");
    const fmi3Int32 bad_mode = 8;
    FMI_CHECK(fmi3SetInt32(inst, &vr_i[0], 1, &bad_mode, 1) == fmi3Error, "bad dsp_mode rejected");
    FMI_CHECK(fmi3SetInt32(inst, &bad_vr, 1, &bad_mode, 1) == fmi3Error, "bad VR SetInt32");
    FMI_CHECK(fmi3GetInt32(inst, &bad_vr, 1, val_i_get, 1) == fmi3Error, "bad VR GetInt32");

    const fmi3ValueReference vr_u = 5u;
    fmi3UInt32 val_u = 99u;
    FMI_CHECK(fmi3GetUInt32(inst, &vr_u, 1, &val_u, 1) == fmi3OK, "get uint32");
    FMI_CHECK(val_u == 0u, "initial bit_status == 0");
    FMI_CHECK(fmi3GetUInt32(inst, &bad_vr, 1, &val_u, 1) == fmi3Error, "bad VR GetUInt32");

    // DoStep before ExitInitializationMode must fail
    fmi3Boolean ev = fmi3False, term = fmi3False, early = fmi3False;
    fmi3Float64 last_t = 0.0;
    FMI_CHECK(fmi3DoStep(inst, 0.0, 1e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3Error, "DoStep before init");

    // Elaborate via fmi3ExitInitializationMode (calls sc_start(SC_ZERO_TIME))
    FMI_CHECK(fmi3ExitInitializationMode(inst) == fmi3OK, "exit init");
    FMI_CHECK(fmi3ExitInitializationMode(inst) == fmi3Error, "double exit init rejected");

    // Negative step size rejected
    FMI_CHECK(fmi3DoStep(inst, 0.0, -1e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3Error, "negative step rejected");

    // Advance 3 macro steps (3 ms) and exercise live tunable parameter updates
    for (int s = 0; s < 3; ++s) {
        if (s == 1) {
            const fmi3Boolean dither_off = fmi3False;
            FMI_CHECK(fmi3SetBoolean(inst, &vr_b[0], 1, &dither_off, 1) == fmi3OK, "toggle dither off mid-sim");
        }
        FMI_CHECK(
            fmi3DoStep(inst, s * 1e-3, 1e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3OK,
            "DoStep succeeded"
        );
        FMI_CHECK(!ev && !term && !early, "DoStep flags clean");
        FMI_CHECK(std::fabs(last_t - (s + 1) * 1e-3) < 1e-12, "lastSuccessfulTime exact");
    }

    FMI_CHECK(fmi3GetFloat64(inst, vr_f_get, 8, val_f_get, 8) == fmi3OK, "post-step get float64");
    FMI_CHECK(std::fabs(val_f_get[0] - 3e-3) < 1e-12, "time == 3 ms");
    FMI_CHECK(std::fabs(val_f_get[3] - 0.02) < 5e-3, "omega_out tracks omega_in");
    FMI_CHECK(std::fabs(val_f_get[7] - 0.02) < 5e-3, "omega_out_avg tracks omega_in");
    FMI_CHECK(fmi3GetUInt32(inst, &vr_u, 1, &val_u, 1) == fmi3OK && val_u == 0u, "bit_status healthy");

    FMI_CHECK(fmi3Reset(inst) == fmi3Error, "fmi3Reset returns fmi3Error for singleton SystemC");
    if (explicit_terminate) {
        FMI_CHECK(fmi3Terminate(inst) == fmi3OK, "terminate ok");
        FMI_CHECK(fmi3DoStep(inst, 3e-3, 1e-3, fmi3True, nullptr, nullptr, nullptr, nullptr) == fmi3Error, "DoStep after terminate");
    }
    fmi3FreeInstance(inst);
}

void run_top_module_fault_mask_test(const std::string& res_dir) {
    namespace fs = std::filesystem;
    ifog::IfogConfig cfg = ifog::load_ifog_config(
        (fs::path(res_dir) / "baseline_cfg.json").string(),
        (fs::path(res_dir) / "phys_params.json").string(),
        ""
    );
    cfg.dsp_mode = ifog::DspMode::SixState;
    cfg.alpha_rad = ifog::PI / 3.0;
    cfg.en_white_noise = false;
    cfg.en_pink_noise = false;
    cfg.en_prbs_dither = false;
    cfg.ablation.en_mioc_vpi_err = false;
    cfg.V_off_0_V = 0.0;
    cfg.V_min_V = -5.0;
    cfg.V_max_V = 5.0;
    cfg.max_delta_phi_step_rad = 0.05;
    cfg.fault_type = ifog::FaultType::AdcSaturation;
    cfg.fault_inject_time_s = 0.0015;
    cfg.fault_duration_s = 0.0005;
    cfg.en_bit = true;

    sc_core::sc_signal<double> sig_omega("sig_omega");
    sc_core::sc_signal<double> sig_shupe("sig_shupe");
    sc_core::sc_signal<double> sig_eps("sig_eps");
    sc_core::sc_signal<double> sig_kxt("sig_kxt");
    sc_core::sc_signal<bool> sig_dith("sig_dith");
    sc_core::sc_signal<double> sig_out("sig_out");
    sc_core::sc_signal<double> sig_avg("sig_avg");
    sc_core::sc_signal<double> sig_vpi("sig_vpi");
    sc_core::sc_signal<uint32_t> sig_bit("sig_bit");

    ifog::IfogTopModule top("IfogTopFault", cfg);
    top.omega_in(sig_omega);
    top.shupe_phase_in(sig_shupe);
    top.eps_vpi_in(sig_eps);
    top.k_xtalk_in(sig_kxt);
    top.enable_dither_in(sig_dith);
    top.omega_out(sig_out);
    top.omega_out_avg(sig_avg);
    top.e_vpi_res_out(sig_vpi);
    top.bit_status_out(sig_bit);

    sig_omega.write(0.5);
    sig_shupe.write(0.0);
    sig_eps.write(0.0);
    sig_kxt.write(0.0);
    sig_dith.write(false);
    sc_core::sc_start(sc_core::SC_ZERO_TIME);
    top.prepare_macro_step(0.5, 0.0, 0.0, 0.0, false);
    sc_core::sc_start(sc_core::sc_time(2e-3, sc_core::SC_SEC));
    const auto snap = top.sample_outputs();
    FMI_CHECK(top.total_tau_steps() > 0u, "top executed tau steps");
    FMI_CHECK(snap.e_vpi_res_rad == 0.0, "e_vpi_res == 0 when en_mioc_vpi_err is false");
    FMI_CHECK((snap.bit_status & ifog::BIT_MASK_ADC_SAT) != 0u, "ADC sat bit set");
    FMI_CHECK((snap.bit_status & ifog::BIT_MASK_ANTI_WINDUP) != 0u, "anti-windup bit set");
    sc_core::sc_stop();
}

}  // namespace

int sc_main(int argc, char* argv[]) {
    try {
        if (argc < 3) {
            throw std::invalid_argument("Usage: ifog_fmi_tests <resources_dir> <mode: 2|4|6|4noterm|fault|bitfault>");
        }
        const std::string res_dir(argv[1]);
        const std::string mode(argv[2]);
        if (mode == "4") {
            run_fmi_mode_test(res_dir, 4, true);
        } else if (mode == "6") {
            run_fmi_mode_test(res_dir, 6, true);
        } else if (mode == "2") {
            run_fmi_mode_test(res_dir, 2, true);
        } else if (mode == "4noterm") {
            run_fmi_mode_test(res_dir, 4, false);
        } else if (mode == "fault") {
            run_top_module_fault_mask_test(res_dir);
        } else {
            // bitfault: trigger BIT_SLD_DROP cleanly without clipping
            namespace fs = std::filesystem;
            ifog::IfogConfig cfg = ifog::load_ifog_config(
                (fs::path(res_dir) / "baseline_cfg.json").string(),
                (fs::path(res_dir) / "phys_params.json").string(),
                ""
            );
            cfg.dsp_mode = ifog::DspMode::FourState;
            cfg.alpha_rad = ifog::PI / 4.0;
            cfg.en_white_noise = false;
            cfg.en_pink_noise = false;
            cfg.en_prbs_dither = false;
            cfg.fault_type = ifog::FaultType::SldDrop50Pct;
            cfg.fault_inject_time_s = 0.0005;
            cfg.en_bit = true;

            sc_core::sc_signal<double> sig_omega("sig_omega");
            sc_core::sc_signal<double> sig_shupe("sig_shupe");
            sc_core::sc_signal<double> sig_eps("sig_eps");
            sc_core::sc_signal<double> sig_kxt("sig_kxt");
            sc_core::sc_signal<bool> sig_dith("sig_dith");
            sc_core::sc_signal<double> sig_out("sig_out");
            sc_core::sc_signal<double> sig_avg("sig_avg");
            sc_core::sc_signal<double> sig_vpi("sig_vpi");
            sc_core::sc_signal<uint32_t> sig_bit("sig_bit");

            ifog::IfogTopModule top("IfogTopBit", cfg);
            top.omega_in(sig_omega);
            top.shupe_phase_in(sig_shupe);
            top.eps_vpi_in(sig_eps);
            top.k_xtalk_in(sig_kxt);
            top.enable_dither_in(sig_dith);
            top.omega_out(sig_out);
            top.omega_out_avg(sig_avg);
            top.e_vpi_res_out(sig_vpi);
            top.bit_status_out(sig_bit);

            sig_omega.write(0.0);
            sig_shupe.write(0.0);
            sig_eps.write(cfg.eps_vpi);
            sig_kxt.write(cfg.k_xtalk_A_per_V);
            sig_dith.write(false);
            sc_core::sc_start(sc_core::SC_ZERO_TIME);
            // Trigger on_inputs_changed() via sc_signal update before stepping
            sig_omega.write(0.001);
            sc_core::sc_start(sc_core::sc_time(2e-3, sc_core::SC_SEC));
            const auto snap = top.sample_outputs();
            FMI_CHECK((snap.bit_status & ifog::BIT_MASK_SLD_DROP) != 0u, "BIT_MASK_SLD_DROP set");
            sc_core::sc_stop();
        }
        std::cout << "[ifog_fmi_tests] mode=" << mode << " PASSED!\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "[ifog_fmi_tests] ERROR: " << ex.what() << "\n";
        return 1;
    }
}
