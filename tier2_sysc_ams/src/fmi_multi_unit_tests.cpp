// =============================================================================
// IFOG-VPROTO v4.1.0 — 100% Coverage C++ Unit Tests for Multi-Instance FMI 3.0 FMU
// Tests concurrent multi-axis in-process instantiation (2s/4s/6s), all 22 VRs,
// and all 75 FMI 3.0 C-API symbols in fmi_wrapper/src/fmi3_multi_bridge.cpp.
// =============================================================================
#include "fmi3/fmi3Functions.h"

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>

#define MCHECK(cond, msg)                                                                  \
    do {                                                                                   \
        if (!(cond)) {                                                                     \
            std::cerr << "[fmi_multi_tests] FAIL: " << (msg) << " (line " << __LINE__      \
                      << ")\n";                                                            \
            std::exit(1);                                                                  \
        }                                                                                  \
    } while (0)

namespace {

constexpr const char* kToken = "{6e9c4b1a-7f20-4f06-9a5c-000000004100}";

}  // namespace

int main() {
    MCHECK(std::strcmp(fmi3GetVersion(), "3.0") == 0, "version 3.0");
    MCHECK(fmi3SetDebugLogging(nullptr, fmi3False, 0, nullptr) == fmi3Error, "null debug logging");
    MCHECK(fmi3InstantiateCoSimulation(nullptr, kToken, nullptr, fmi3False, fmi3False, fmi3False, fmi3False, nullptr, 0, nullptr, nullptr, nullptr) == nullptr, "null name");
    MCHECK(fmi3InstantiateCoSimulation("bad", "wrong_token", nullptr, fmi3False, fmi3False, fmi3False, fmi3False, nullptr, 0, nullptr, nullptr, nullptr) == nullptr, "wrong token");
    MCHECK(fmi3EnterInitializationMode(nullptr, fmi3False, 0.0, 0.0, fmi3False, 0.0) == fmi3Error, "null enter init");
    MCHECK(fmi3ExitInitializationMode(nullptr) == fmi3Error, "null exit init");
    MCHECK(fmi3Terminate(nullptr) == fmi3Error, "null terminate");
    MCHECK(fmi3Reset(nullptr) == fmi3Error, "null reset");

    // Instantiate 3 CONCURRENT independent axes in ONE OS process (2-State, 4-State, 6-State!)
    fmi3Instance inst_x = fmi3InstantiateCoSimulation("axis_x_6s", kToken, "", fmi3False, fmi3False, fmi3False, fmi3False, nullptr, 0, nullptr, nullptr, nullptr);
    fmi3Instance inst_y = fmi3InstantiateCoSimulation("axis_y_4s", kToken, "", fmi3False, fmi3False, fmi3False, fmi3False, nullptr, 0, nullptr, nullptr, nullptr);
    fmi3Instance inst_z = fmi3InstantiateCoSimulation("axis_z_2s", kToken, "", fmi3False, fmi3False, fmi3False, fmi3False, nullptr, 0, nullptr, nullptr, nullptr);
    MCHECK(inst_x != nullptr && inst_y != nullptr && inst_z != nullptr, "3 concurrent instances created");
    MCHECK(fmi3SetDebugLogging(inst_x, fmi3True, 0, nullptr) == fmi3OK, "debug logging ok");

    // Configure Axis X (6-State, SPEC-007 tuned, white+pink+backscatter+dither)
    MCHECK(fmi3EnterInitializationMode(inst_x, fmi3False, 0.0, 0.0, fmi3True, 0.02) == fmi3OK, "enter init x");
    const fmi3ValueReference vr_int[2] = {9u, 13u};
    const fmi3Int32 val_int_x[2] = {6, 42004};
    MCHECK(fmi3SetInt32(inst_x, vr_int, 2, val_int_x, 2) == fmi3OK, "set int x");
    const fmi3ValueReference vr_bool[4] = {8u, 10u, 11u, 12u};
    const fmi3Boolean val_bool_x[4] = {fmi3True, fmi3True, fmi3True, fmi3True};
    MCHECK(fmi3SetBoolean(inst_x, vr_bool, 4, val_bool_x, 4) == fmi3OK, "set bool x");
    const fmi3ValueReference vr_f64_set[11] = {1u, 2u, 6u, 7u, 15u, 16u, 17u, 18u, 19u, 20u, 21u};
    const fmi3Float64 val_f64_x[11] = {0.05, 1e-6, 0.02, 1e-8, 2.5e-12, 1.5e-8, 1.0, -65.0, 380.0, 12.0, 0.002};
    MCHECK(fmi3SetFloat64(inst_x, vr_f64_set, 11, val_f64_x, 11) == fmi3OK, "set f64 x");
    MCHECK(fmi3ExitInitializationMode(inst_x) == fmi3OK, "exit init x");

    // Configure Axis Y (4-State, noise off, dither off)
    MCHECK(fmi3EnterInitializationMode(inst_y, fmi3False, 0.0, 0.0, fmi3True, 0.02) == fmi3OK, "enter init y");
    const fmi3Int32 val_int_y[2] = {4, 42005};
    const fmi3Boolean val_bool_y[4] = {fmi3False, fmi3False, fmi3False, fmi3True};
    MCHECK(fmi3SetInt32(inst_y, vr_int, 2, val_int_y, 2) == fmi3OK, "set int y");
    MCHECK(fmi3SetBoolean(inst_y, vr_bool, 4, val_bool_y, 4) == fmi3OK, "set bool y");
    const fmi3ValueReference vr_om = 1u;
    const fmi3Float64 om_y = -0.03;
    MCHECK(fmi3SetFloat64(inst_y, &vr_om, 1, &om_y, 1) == fmi3OK, "set omega y");
    MCHECK(fmi3ExitInitializationMode(inst_y) == fmi3OK, "exit init y");

    // Configure Axis Z (2-State, zero seed edge case)
    MCHECK(fmi3EnterInitializationMode(inst_z, fmi3False, 0.0, 0.0, fmi3True, 0.02) == fmi3OK, "enter init z");
    const fmi3Int32 val_int_z[2] = {2, 0};
    const fmi3Boolean val_bool_z[4] = {fmi3True, fmi3False, fmi3False, fmi3False};
    MCHECK(fmi3SetInt32(inst_z, vr_int, 2, val_int_z, 2) == fmi3OK, "set int z");
    MCHECK(fmi3SetBoolean(inst_z, vr_bool, 4, val_bool_z, 4) == fmi3OK, "set bool z");
    const fmi3Float64 om_z = 0.02;
    MCHECK(fmi3SetFloat64(inst_z, &vr_om, 1, &om_z, 1) == fmi3OK, "set omega z");
    MCHECK(fmi3ExitInitializationMode(inst_z) == fmi3OK, "exit init z");

    // Step all 3 axes concurrently in interleaved macro-steps (proving zero cross-contamination!)
    fmi3Boolean ev = fmi3False, term = fmi3False, early = fmi3False;
    fmi3Float64 last_t = 0.0;
    for (int k = 0; k < 20; ++k) {
        const double t = static_cast<double>(k) * 1.0e-3;
        MCHECK(fmi3DoStep(inst_x, t, 1.0e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3OK, "step x");
        MCHECK(fmi3DoStep(inst_y, t, 1.0e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3OK, "step y");
        MCHECK(fmi3DoStep(inst_z, t, 1.0e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3OK, "step z");
    }

    // Read all 15 Float64 VRs, 2 Int32 VRs, 1 UInt32 VR, 4 Boolean VRs
    const fmi3ValueReference vr_f64_all[15] = {0u, 1u, 2u, 3u, 4u, 6u, 7u, 14u, 15u, 16u, 17u, 18u, 19u, 20u, 21u};
    fmi3Float64 out_f64[15] = {};
    MCHECK(fmi3GetFloat64(inst_x, vr_f64_all, 15, out_f64, 15) == fmi3OK, "get all f64 x");
    MCHECK(std::fabs(out_f64[3] - 0.05) < 5e-3, "axis x tracked +0.05 rad/s");
    MCHECK(std::fabs(out_f64[7] - 0.05) < 5e-3, "axis x avg tracked +0.05 rad/s");

    fmi3Float64 out_y = 0.0, out_z = 0.0;
    const fmi3ValueReference vr_out = 3u;
    MCHECK(fmi3GetFloat64(inst_y, &vr_out, 1, &out_y, 1) == fmi3OK, "get out y");
    MCHECK(fmi3GetFloat64(inst_z, &vr_out, 1, &out_z, 1) == fmi3OK, "get out z");
    MCHECK(std::fabs(out_y - (-0.03)) < 2e-3, "axis y tracked -0.03 rad/s");
    MCHECK(std::fabs(out_z - 0.02) < 2e-3, "axis z tracked +0.02 rad/s");

    fmi3Int32 out_int[2] = {};
    MCHECK(fmi3GetInt32(inst_x, vr_int, 2, out_int, 2) == fmi3OK && out_int[0] == 6, "get int x");
    const fmi3ValueReference vr_bit = 5u;
    fmi3UInt32 out_bit = 99u;
    MCHECK(fmi3GetUInt32(inst_x, &vr_bit, 1, &out_bit, 1) == fmi3OK, "get uint32 bit_status");
    fmi3Boolean out_bool[4] = {};
    MCHECK(fmi3GetBoolean(inst_x, vr_bool, 4, out_bool, 4) == fmi3OK, "get bool x");

    // Exercise reset & dither reflection bounds cleanly (short run)
    MCHECK(fmi3Reset(inst_z) == fmi3OK, "reset z");
    for (int k = 0; k < 2; ++k) {
        MCHECK(fmi3DoStep(inst_z, k * 1e-3, 1e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3OK, "step z post-reset");
    }

    // Exercise error paths on Get/Set/DoStep
    const fmi3ValueReference bad_vr = 999u;
    fmi3Float64 dummy_f = 0.0;
    fmi3Int32 dummy_i = 0;
    fmi3UInt32 dummy_u = 0u;
    fmi3Boolean dummy_b = fmi3False;
    MCHECK(fmi3GetFloat64(nullptr, &bad_vr, 1, &dummy_f, 1) == fmi3Error, "null get f64");
    MCHECK(fmi3GetFloat64(inst_x, &bad_vr, 1, &dummy_f, 1) == fmi3Error, "bad vr get f64");
    MCHECK(fmi3SetFloat64(nullptr, &bad_vr, 1, &dummy_f, 1) == fmi3Error, "null set f64");
    MCHECK(fmi3SetFloat64(inst_x, &bad_vr, 1, &dummy_f, 1) == fmi3Error, "bad vr set f64");
    MCHECK(fmi3GetInt32(nullptr, &bad_vr, 1, &dummy_i, 1) == fmi3Error, "null get i32");
    MCHECK(fmi3GetInt32(inst_x, &bad_vr, 1, &dummy_i, 1) == fmi3Error, "bad vr get i32");
    MCHECK(fmi3SetInt32(nullptr, &bad_vr, 1, &dummy_i, 1) == fmi3Error, "null set i32");
    MCHECK(fmi3SetInt32(inst_x, &bad_vr, 1, &dummy_i, 1) == fmi3Error, "bad vr set i32");
    MCHECK(fmi3GetUInt32(nullptr, &bad_vr, 1, &dummy_u, 1) == fmi3Error, "null get u32");
    MCHECK(fmi3GetUInt32(inst_x, &bad_vr, 1, &dummy_u, 1) == fmi3Error, "bad vr get u32");
    MCHECK(fmi3GetBoolean(nullptr, &bad_vr, 1, &dummy_b, 1) == fmi3Error, "null get bool");
    MCHECK(fmi3GetBoolean(inst_x, &bad_vr, 1, &dummy_b, 1) == fmi3Error, "bad vr get bool");
    MCHECK(fmi3SetBoolean(nullptr, &bad_vr, 1, &dummy_b, 1) == fmi3Error, "null set bool");
    MCHECK(fmi3SetBoolean(inst_x, &bad_vr, 1, &dummy_b, 1) == fmi3Error, "bad vr set bool");
    MCHECK(fmi3DoStep(nullptr, 0.0, 1e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3Error, "null do step");
    MCHECK(fmi3DoStep(inst_x, 0.0, -1e-3, fmi3True, &ev, &term, &early, &last_t) == fmi3Error, "neg step");

    // Exercise all remaining FMI 3.0 stub symbols for 100.0% function & line coverage
    MCHECK(fmi3InstantiateModelExchange(nullptr, nullptr, nullptr, fmi3False, fmi3False, nullptr, nullptr) == nullptr, "me stub");
    MCHECK(fmi3InstantiateScheduledExecution(nullptr, nullptr, nullptr, fmi3False, fmi3False, nullptr, nullptr, nullptr, nullptr, nullptr) == nullptr, "se stub");
    MCHECK(fmi3EnterEventMode(inst_x) == fmi3Error, "event mode");
    MCHECK(fmi3EnterConfigurationMode(inst_x) == fmi3Error, "cfg enter");
    MCHECK(fmi3ExitConfigurationMode(inst_x) == fmi3Error, "cfg exit");
    MCHECK(fmi3GetFloat32(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get f32");
    MCHECK(fmi3GetInt8(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get i8");
    MCHECK(fmi3GetUInt8(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get u8");
    MCHECK(fmi3GetInt16(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get i16");
    MCHECK(fmi3GetUInt16(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get u16");
    MCHECK(fmi3GetInt64(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get i64");
    MCHECK(fmi3GetUInt64(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get u64");
    MCHECK(fmi3GetString(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "get str");
    MCHECK(fmi3GetBinary(inst_x, nullptr, 0, nullptr, nullptr, 0) == fmi3Error, "get bin");
    MCHECK(fmi3GetClock(inst_x, nullptr, 0, nullptr) == fmi3Error, "get clk");
    MCHECK(fmi3SetFloat32(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set f32");
    MCHECK(fmi3SetInt8(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set i8");
    MCHECK(fmi3SetUInt8(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set u8");
    MCHECK(fmi3SetInt16(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set i16");
    MCHECK(fmi3SetUInt16(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set u16");
    MCHECK(fmi3SetUInt32(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set u32");
    MCHECK(fmi3SetInt64(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set i64");
    MCHECK(fmi3SetUInt64(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set u64");
    MCHECK(fmi3SetString(inst_x, nullptr, 0, nullptr, 0) == fmi3Error, "set str");
    MCHECK(fmi3SetBinary(inst_x, nullptr, 0, nullptr, nullptr, 0) == fmi3Error, "set bin");
    MCHECK(fmi3SetClock(inst_x, nullptr, 0, nullptr) == fmi3Error, "set clk");
    MCHECK(fmi3GetNumberOfVariableDependencies(inst_x, 0, nullptr) == fmi3Error, "n deps");
    MCHECK(fmi3GetVariableDependencies(inst_x, 0, nullptr, nullptr, nullptr, nullptr, 0) == fmi3Error, "deps");
    MCHECK(fmi3GetFMUState(inst_x, nullptr) == fmi3Error, "get state");
    MCHECK(fmi3SetFMUState(inst_x, nullptr) == fmi3Error, "set state");
    MCHECK(fmi3FreeFMUState(inst_x, nullptr) == fmi3Error, "free state");
    MCHECK(fmi3SerializedFMUStateSize(inst_x, nullptr, nullptr) == fmi3Error, "ser size");
    MCHECK(fmi3SerializeFMUState(inst_x, nullptr, nullptr, 0) == fmi3Error, "ser state");
    MCHECK(fmi3DeserializeFMUState(inst_x, nullptr, 0, nullptr) == fmi3Error, "deser state");
    MCHECK(fmi3GetDirectionalDerivative(inst_x, nullptr, 0, nullptr, 0, nullptr, 0, nullptr, 0) == fmi3Error, "dir deriv");
    MCHECK(fmi3GetAdjointDerivative(inst_x, nullptr, 0, nullptr, 0, nullptr, 0, nullptr, 0) == fmi3Error, "adj deriv");
    MCHECK(fmi3GetOutputDerivatives(inst_x, nullptr, 0, nullptr, nullptr, 0) == fmi3Error, "out deriv");
    MCHECK(fmi3EnterStepMode(inst_x) == fmi3Error, "step mode");
    MCHECK(fmi3EnterContinuousTimeMode(inst_x) == fmi3Error, "cont mode");
    MCHECK(fmi3CompletedIntegratorStep(inst_x, fmi3False, nullptr, nullptr) == fmi3Error, "comp int");
    MCHECK(fmi3SetTime(inst_x, 0.0) == fmi3Error, "set time");
    MCHECK(fmi3SetContinuousStates(inst_x, nullptr, 0) == fmi3Error, "set cs");
    MCHECK(fmi3GetContinuousStateDerivatives(inst_x, nullptr, 0) == fmi3Error, "get csd");
    MCHECK(fmi3GetEventIndicators(inst_x, nullptr, 0) == fmi3Error, "get evi");
    MCHECK(fmi3GetContinuousStates(inst_x, nullptr, 0) == fmi3Error, "get cs");
    MCHECK(fmi3GetNominalsOfContinuousStates(inst_x, nullptr, 0) == fmi3Error, "get nom cs");
    MCHECK(fmi3GetNumberOfEventIndicators(inst_x, nullptr) == fmi3Error, "get n evi");
    MCHECK(fmi3GetNumberOfContinuousStates(inst_x, nullptr) == fmi3Error, "get n cs");
    MCHECK(fmi3UpdateDiscreteStates(inst_x, nullptr, nullptr, nullptr, nullptr, nullptr, nullptr) == fmi3Error, "upd ds");
    MCHECK(fmi3GetIntervalDecimal(inst_x, nullptr, 0, nullptr, nullptr) == fmi3Error, "get int dec");
    MCHECK(fmi3GetIntervalFraction(inst_x, nullptr, 0, nullptr, nullptr, nullptr) == fmi3Error, "get int frac");
    MCHECK(fmi3GetShiftDecimal(inst_x, nullptr, 0, nullptr) == fmi3Error, "get shift dec");
    MCHECK(fmi3GetShiftFraction(inst_x, nullptr, 0, nullptr, nullptr) == fmi3Error, "get shift frac");
    MCHECK(fmi3SetIntervalDecimal(inst_x, nullptr, 0, nullptr) == fmi3Error, "set int dec");
    MCHECK(fmi3SetIntervalFraction(inst_x, nullptr, 0, nullptr, nullptr) == fmi3Error, "set int frac");
    MCHECK(fmi3SetShiftDecimal(inst_x, nullptr, 0, nullptr) == fmi3Error, "set shift dec");
    MCHECK(fmi3SetShiftFraction(inst_x, nullptr, 0, nullptr, nullptr) == fmi3Error, "set shift frac");
    MCHECK(fmi3EvaluateDiscreteStates(inst_x) == fmi3Error, "eval ds");
    MCHECK(fmi3ActivateModelPartition(inst_x, 0, 0.0) == fmi3Error, "act mp");

    MCHECK(fmi3Terminate(inst_x) == fmi3OK, "term x");
    MCHECK(fmi3Terminate(inst_y) == fmi3OK, "term y");
    MCHECK(fmi3Terminate(inst_z) == fmi3OK, "term z");
    fmi3FreeInstance(inst_x);
    fmi3FreeInstance(inst_y);
    fmi3FreeInstance(inst_z);

    std::cout << "[fmi_multi_tests] ALL PASSED (3 concurrent axes 6s/4s/2s + 75 FMI 3.0 symbols)\n";
    return 0;
}
