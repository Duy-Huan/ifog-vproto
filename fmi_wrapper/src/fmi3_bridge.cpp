#include "fmi3/fmi3Functions.h"

#include <atomic>
#include <cctype>
#include <cstring>
#include <filesystem>
#include <memory>
#include <string>
#include <systemc-ams.h>
#include <systemc.h>

#include "ifog_config.hpp"
#include "ifog_top_module.hpp"
#include "ifog_types.hpp"

#ifdef IFOG_FMI_DEFINE_SC_MAIN_STUB
// Satisfy libsystemc.so unresolved sc_main symbol when loaded via dlopen() in Python/FMPy
extern "C" int sc_main(int, char**) {
    return 0;
}
#endif

namespace {

constexpr const char* kInstantiationToken = "{6e9c4b1a-7f20-4f06-9a5c-000000000006}";

// Value references strictly matching fmi_wrapper/modelDescription.xml.in
constexpr fmi3ValueReference VR_TIME = 0u;
constexpr fmi3ValueReference VR_OMEGA_IN = 1u;
constexpr fmi3ValueReference VR_SHUPE_PHASE_IN = 2u;
constexpr fmi3ValueReference VR_OMEGA_OUT = 3u;
constexpr fmi3ValueReference VR_E_VPI_RES = 4u;
constexpr fmi3ValueReference VR_BIT_STATUS = 5u;
constexpr fmi3ValueReference VR_EPS_VPI = 6u;
constexpr fmi3ValueReference VR_K_XTALK = 7u;
constexpr fmi3ValueReference VR_ENABLE_DITHER = 8u;
constexpr fmi3ValueReference VR_DSP_MODE = 9u;
constexpr fmi3ValueReference VR_EN_WHITE_NOISE = 10u;
constexpr fmi3ValueReference VR_EN_PINK_NOISE = 11u;
constexpr fmi3ValueReference VR_EN_VPI_LOOP = 12u;
constexpr fmi3ValueReference VR_SEED = 13u;
constexpr fmi3ValueReference VR_OMEGA_OUT_AVG = 14u;
constexpr fmi3ValueReference VR_C_XTALK_F = 15u;
constexpr fmi3ValueReference VR_G_XTALK_S = 16u;
constexpr fmi3ValueReference VR_C_PINK_COEFF = 17u;
constexpr fmi3ValueReference VR_R_FACET_DB = 18u;
constexpr fmi3ValueReference VR_ALPHA_VPI_PPM_K = 19u;
constexpr fmi3ValueReference VR_ALPHA_BOBBIN_PPM_K = 20u;
constexpr fmi3ValueReference VR_DELTA_Z_QUAD_M = 21u;

// Accellera SystemC 2.3.4 uses a process-global sc_simcontext singleton
// (canBeInstantiatedOnlyOncePerProcess="true" in modelDescription.xml).
std::atomic<bool> g_instance_created{false};

int hex_nibble(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'f') {
        return 10 + (c - 'a');
    }
    if (c >= 'A' && c <= 'F') {
        return 10 + (c - 'A');
    }
    return -1;
}

void percent_decode_in_place(std::string& s) {
    size_t write_idx = 0;
    for (size_t i = 0; i < s.size(); ++i) {
        if (s[i] == '%' && i + 2 < s.size()) {
            const int hi = hex_nibble(s[i + 1]);
            const int lo = hex_nibble(s[i + 2]);
            if (hi >= 0 && lo >= 0) {
                s[write_idx++] = static_cast<char>((hi << 4) | lo);
                i += 2;
                continue;
            }
        }
        s[write_idx++] = s[i];
    }
    s.resize(write_idx);
}

// Parse FMI 3.0 resourcePath, handling both native paths and file:// URIs on Linux & Windows.
std::string normalize_resource_path(const char* raw_path) {
    if (raw_path == nullptr) {
        return "";
    }
    std::string s(raw_path);
    const std::string prefix_localhost = "file://localhost/";
    const std::string prefix_triple = "file:///";
    const std::string prefix_double = "file://";
    const std::string prefix_single = "file:/";

    if (s.rfind(prefix_localhost, 0) == 0) {
        s = "/" + s.substr(prefix_localhost.size());
    } else if (s.rfind(prefix_triple, 0) == 0) {
        s = "/" + s.substr(prefix_triple.size());
    } else if (s.rfind(prefix_double, 0) == 0) {
        s = s.substr(prefix_double.size());
    } else if (s.rfind(prefix_single, 0) == 0) {
        s = "/" + s.substr(prefix_single.size());
    }

    percent_decode_in_place(s);

    // Strip leading '/' on Windows drive URI forms such as "/C:/path/to/resources"
    if (s.size() >= 3 && s[0] == '/' &&
        std::isalpha(static_cast<unsigned char>(s[1])) != 0 && s[2] == ':') {
        s.erase(0, 1);
    }
    return s;
}

struct FmuInstance {
    std::string name;
    bool logging_on = false;
    fmi3InstanceEnvironment env = nullptr;
    fmi3LogMessageCallback log_cb = nullptr;

    ifog::IfogConfig cfg;
    double current_time = 0.0;

    // Live FMI 3.0 variable shadow state
    double omega_in = 0.0;
    double shupe_phase_in = 0.0;
    double eps_vpi = 0.02;
    double k_xtalk = 1.0e-8;
    bool enable_dither = true;
    int32_t dsp_mode = 4;
    bool en_white_noise = true;
    bool en_pink_noise = false;
    bool en_vpi_loop = true;
    int32_t seed = 42004;

    // SPEC-007 tunable calibration parameter shadow state (VR 15..21)
    bool spec007_tuned = false;
    double C_xtalk_F = 2.0e-12;
    double G_xtalk_S = 1.0e-8;
    double c_pink_coeff = 1.0;
    double R_facet_dB = -200.0;
    double alpha_vpi_ppm_K = 0.0;
    double alpha_bobbin_ppm_K = 0.0;
    double delta_z_quad_m = 0.002;

    ifog::FmiOutputSnapshot outputs{};

    // Bound SystemC channels connecting FMI 3.0 bridge to IfogTopModule ports
    std::unique_ptr<sc_core::sc_signal<double>> sig_omega_in;
    std::unique_ptr<sc_core::sc_signal<double>> sig_shupe_in;
    std::unique_ptr<sc_core::sc_signal<double>> sig_eps_vpi;
    std::unique_ptr<sc_core::sc_signal<double>> sig_k_xtalk;
    std::unique_ptr<sc_core::sc_signal<bool>> sig_en_dither;
    std::unique_ptr<sc_core::sc_signal<double>> sig_omega_out;
    std::unique_ptr<sc_core::sc_signal<double>> sig_omega_out_avg;
    std::unique_ptr<sc_core::sc_signal<double>> sig_e_vpi_res;
    std::unique_ptr<sc_core::sc_signal<uint32_t>> sig_bit_status;

    std::unique_ptr<ifog::IfogTopModule> top;
    bool initialized = false;
    bool terminated = false;

    void log(fmi3Status status, const char* category, const std::string& msg) const {
        if (log_cb != nullptr && (logging_on || status >= fmi3Error)) {
            log_cb(env, status, category, msg.c_str());
        }
    }
};

void write_bound_input_signals(FmuInstance* inst) {
    inst->sig_omega_in->write(inst->omega_in);
    inst->sig_shupe_in->write(inst->shupe_phase_in);
    inst->sig_eps_vpi->write(inst->eps_vpi);
    inst->sig_k_xtalk->write(inst->k_xtalk);
    inst->sig_en_dither->write(inst->enable_dither);
}

void log_error_no_inst(
    fmi3InstanceEnvironment env,
    fmi3LogMessageCallback cb,
    const std::string& msg
) {
    if (cb != nullptr) {
        cb(env, fmi3Error, "logStatusError", msg.c_str());
    }
}

}  // namespace

extern "C" {

FMI3_Export const char* fmi3GetVersion(void) {
    return fmi3Version;
}

FMI3_Export fmi3Status fmi3SetDebugLogging(
    fmi3Instance instance,
    fmi3Boolean loggingOn,
    size_t,
    const fmi3String[]
) {
    if (instance == nullptr) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    inst->logging_on = loggingOn;
    inst->log(fmi3OK, "logEvents", loggingOn ? "Debug logging enabled" : "Debug logging disabled");
    return fmi3OK;
}

FMI3_Export fmi3Instance fmi3InstantiateCoSimulation(
    fmi3String instanceName,
    fmi3String instantiationToken,
    fmi3String resourcePath,
    fmi3Boolean,
    fmi3Boolean loggingOn,
    fmi3Boolean,
    fmi3Boolean,
    const fmi3ValueReference[],
    size_t,
    fmi3InstanceEnvironment instanceEnvironment,
    fmi3LogMessageCallback logMessage,
    fmi3IntermediateUpdateCallback
) {
    if (instantiationToken == nullptr || std::strcmp(instantiationToken, kInstantiationToken) != 0) {
        log_error_no_inst(instanceEnvironment, logMessage, "Invalid instantiationToken for ifog_core FMU");
        return nullptr;
    }

    const std::string res_dir_str = normalize_resource_path(resourcePath);
    if (res_dir_str.empty()) {
        log_error_no_inst(instanceEnvironment, logMessage, "Empty resourcePath provided to ifog_core FMU");
        return nullptr;
    }

    namespace fs = std::filesystem;
    const fs::path res_dir(res_dir_str);
    const fs::path phys_path = res_dir / "phys_params.json";
    const fs::path cfg_path = res_dir / "baseline_cfg.json";
    const fs::path shupe_path = res_dir / "shupe_lut.bin";

    if (!fs::exists(phys_path) || !fs::exists(cfg_path)) {
        log_error_no_inst(
            instanceEnvironment,
            logMessage,
            "Missing phys_params.json or baseline_cfg.json in resourcePath: " + res_dir_str
        );
        return nullptr;
    }

    bool expected = false;
    if (!g_instance_created.compare_exchange_strong(expected, true)) {
        log_error_no_inst(
            instanceEnvironment,
            logMessage,
            "ifog_core FMU violates canBeInstantiatedOnlyOncePerProcess (SystemC singleton kernel)"
        );
        return nullptr;
    }

    auto inst = std::make_unique<FmuInstance>();
    inst->name = (instanceName != nullptr) ? std::string(instanceName) : std::string("ifog_core");
    inst->logging_on = loggingOn;
    inst->env = instanceEnvironment;
    inst->log_cb = logMessage;

    const std::string shupe_arg = fs::exists(shupe_path) ? shupe_path.string() : std::string();
    inst->cfg = ifog::load_ifog_config(cfg_path.string(), phys_path.string(), shupe_arg);
    inst->eps_vpi = inst->cfg.eps_vpi;
    inst->k_xtalk = inst->cfg.k_xtalk_A_per_V;
    inst->enable_dither = inst->cfg.en_prbs_dither;
    inst->dsp_mode = 4;
    inst->en_white_noise = inst->cfg.en_white_noise;
    inst->en_pink_noise = inst->cfg.en_pink_noise;
    inst->en_vpi_loop = inst->cfg.en_vpi_loop;
    inst->seed = static_cast<int32_t>(inst->cfg.seed);
    inst->C_xtalk_F = inst->cfg.spec007.en_spec007_physics ? inst->cfg.spec007.C_xtalk_F : inst->cfg.C_xtalk_F;
    inst->G_xtalk_S = inst->cfg.spec007.en_spec007_physics ? inst->cfg.spec007.G_xtalk_S : inst->cfg.k_xtalk_A_per_V;
    inst->c_pink_coeff = 1.0;
    inst->R_facet_dB = inst->cfg.spec007.R_facet_dB;
    inst->alpha_vpi_ppm_K = inst->cfg.spec007.alpha_vpi_ppm_K;
    inst->alpha_bobbin_ppm_K = inst->cfg.spec007.alpha_bobbin_ppm_K;
    inst->delta_z_quad_m = 0.002;

    inst->log(fmi3OK, "logEvents", "Instantiated ifog_core FMI 3.0 Co-Simulation FMU from " + res_dir_str);
    return inst.release();
}

FMI3_Export fmi3Status fmi3EnterInitializationMode(
    fmi3Instance instance,
    fmi3Boolean,
    fmi3Float64,
    fmi3Float64 startTime,
    fmi3Boolean,
    fmi3Float64
) {
    if (instance == nullptr) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    inst->current_time = startTime;
    inst->log(fmi3OK, "logEvents", "Entered FMI 3.0 Initialization Mode");
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3ExitInitializationMode(fmi3Instance instance) {
    if (instance == nullptr) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    if (inst->initialized) {
        return fmi3Error;
    }

    // Apply fixed & initial tunable parameters to IfogConfig prior to SystemC elaboration
    inst->cfg.eps_vpi = inst->eps_vpi;
    inst->cfg.k_xtalk_A_per_V = inst->k_xtalk;
    inst->cfg.en_prbs_dither = inst->enable_dither;
    inst->cfg.en_white_noise = inst->en_white_noise;
    inst->cfg.en_pink_noise = inst->en_pink_noise;
    inst->cfg.en_vpi_loop = inst->en_vpi_loop;
    inst->cfg.seed = static_cast<uint64_t>(static_cast<uint32_t>(inst->seed));
    inst->cfg.omega_const_rad_per_s = inst->omega_in;

    if (inst->dsp_mode == 6) {
        inst->cfg.dsp_mode = ifog::DspMode::SixState;
        inst->cfg.alpha_rad = ifog::PI / 3.0;
    } else if (inst->dsp_mode == 2) {
        inst->cfg.dsp_mode = ifog::DspMode::TwoState;
        inst->cfg.alpha_rad = ifog::PI / 4.0;
    } else {
        inst->cfg.dsp_mode = ifog::DspMode::FourState;
        inst->cfg.alpha_rad = ifog::PI / 4.0;
    }

    // Instantiate SystemC signals & IfogTopModule, then elaborate via sc_start(SC_ZERO_TIME)
    inst->sig_omega_in = std::make_unique<sc_core::sc_signal<double>>("fmi_omega_in");
    inst->sig_shupe_in = std::make_unique<sc_core::sc_signal<double>>("fmi_shupe_phase_in");
    inst->sig_eps_vpi = std::make_unique<sc_core::sc_signal<double>>("fmi_eps_vpi");
    inst->sig_k_xtalk = std::make_unique<sc_core::sc_signal<double>>("fmi_k_xtalk");
    inst->sig_en_dither = std::make_unique<sc_core::sc_signal<bool>>("fmi_enable_dither");
    inst->sig_omega_out = std::make_unique<sc_core::sc_signal<double>>("fmi_omega_out");
    inst->sig_omega_out_avg = std::make_unique<sc_core::sc_signal<double>>("fmi_omega_out_avg");
    inst->sig_e_vpi_res = std::make_unique<sc_core::sc_signal<double>>("fmi_e_vpi_res");
    inst->sig_bit_status = std::make_unique<sc_core::sc_signal<uint32_t>>("fmi_bit_status");

    inst->top = std::make_unique<ifog::IfogTopModule>("IfogTopModule", inst->cfg);
    inst->top->omega_in(*inst->sig_omega_in);
    inst->top->shupe_phase_in(*inst->sig_shupe_in);
    inst->top->eps_vpi_in(*inst->sig_eps_vpi);
    inst->top->k_xtalk_in(*inst->sig_k_xtalk);
    inst->top->enable_dither_in(*inst->sig_en_dither);
    inst->top->omega_out(*inst->sig_omega_out);
    inst->top->omega_out_avg(*inst->sig_omega_out_avg);
    inst->top->e_vpi_res_out(*inst->sig_e_vpi_res);
    inst->top->bit_status_out(*inst->sig_bit_status);

    write_bound_input_signals(inst);
    inst->top->prepare_macro_step(
        inst->omega_in, inst->shupe_phase_in, inst->eps_vpi, inst->k_xtalk, inst->enable_dither
    );
    inst->top->set_spec007_tunable_params(
        inst->spec007_tuned,
        inst->C_xtalk_F,
        inst->G_xtalk_S,
        inst->c_pink_coeff,
        inst->R_facet_dB,
        inst->alpha_vpi_ppm_K,
        inst->alpha_bobbin_ppm_K,
        inst->delta_z_quad_m
    );

    // Complete SystemC elaboration and static SystemC-AMS TDF cluster scheduling
    sc_core::sc_start(sc_core::SC_ZERO_TIME);
    inst->outputs = inst->top->sample_outputs();
    inst->initialized = true;
    inst->log(fmi3OK, "logEvents", "Exited Initialization Mode; SystemC-AMS elaborated via sc_start(SC_ZERO_TIME)");
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3DoStep(
    fmi3Instance instance,
    fmi3Float64 currentCommunicationPoint,
    fmi3Float64 communicationStepSize,
    fmi3Boolean,
    fmi3Boolean* eventHandlingNeeded,
    fmi3Boolean* terminateSimulation,
    fmi3Boolean* earlyReturn,
    fmi3Float64* lastSuccessfulTime
) {
    if (instance == nullptr || communicationStepSize <= 0.0) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    if (!inst->initialized || inst->terminated) {
        return fmi3Error;
    }

    // Apply Zero-Order Hold (ZOH) inputs & tunable parameters across the macro step
    write_bound_input_signals(inst);
    inst->top->prepare_macro_step(
        inst->omega_in, inst->shupe_phase_in, inst->eps_vpi, inst->k_xtalk, inst->enable_dither
    );
    inst->top->set_spec007_tunable_params(
        inst->spec007_tuned,
        inst->C_xtalk_F,
        inst->G_xtalk_S,
        inst->c_pink_coeff,
        inst->R_facet_dB,
        inst->alpha_vpi_ppm_K,
        inst->alpha_bobbin_ppm_K,
        inst->delta_z_quad_m
    );

    // Advance IEEE 1666.1 SystemC-AMS kernel by exact communicationStepSize
    sc_core::sc_start(sc_core::sc_time(communicationStepSize, sc_core::SC_SEC));

    inst->current_time = currentCommunicationPoint + communicationStepSize;
    inst->outputs = inst->top->sample_outputs();

    if (eventHandlingNeeded != nullptr) {
        *eventHandlingNeeded = fmi3False;
    }
    if (terminateSimulation != nullptr) {
        *terminateSimulation = fmi3False;
    }
    if (earlyReturn != nullptr) {
        *earlyReturn = fmi3False;
    }
    if (lastSuccessfulTime != nullptr) {
        *lastSuccessfulTime = inst->current_time;
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3SetFloat64(
    fmi3Instance instance,
    const fmi3ValueReference valueReferences[],
    size_t nValueReferences,
    const fmi3Float64 values[],
    size_t nValues
) {
    if (instance == nullptr || nValueReferences != nValues) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    for (size_t i = 0; i < nValueReferences; ++i) {
        switch (valueReferences[i]) {
            case VR_OMEGA_IN:
                inst->omega_in = values[i];
                break;
            case VR_SHUPE_PHASE_IN:
                inst->shupe_phase_in = values[i];
                break;
            case VR_EPS_VPI:
                inst->eps_vpi = values[i];
                break;
            case VR_K_XTALK:
                inst->k_xtalk = values[i];
                inst->G_xtalk_S = values[i];
                break;
            case VR_C_XTALK_F:
                inst->C_xtalk_F = values[i];
                inst->spec007_tuned = true;
                break;
            case VR_G_XTALK_S:
                inst->G_xtalk_S = values[i];
                inst->k_xtalk = values[i];
                inst->spec007_tuned = true;
                break;
            case VR_C_PINK_COEFF:
                inst->c_pink_coeff = values[i];
                inst->spec007_tuned = true;
                break;
            case VR_R_FACET_DB:
                inst->R_facet_dB = values[i];
                inst->spec007_tuned = true;
                break;
            case VR_ALPHA_VPI_PPM_K:
                inst->alpha_vpi_ppm_K = values[i];
                inst->spec007_tuned = true;
                break;
            case VR_ALPHA_BOBBIN_PPM_K:
                inst->alpha_bobbin_ppm_K = values[i];
                inst->spec007_tuned = true;
                break;
            case VR_DELTA_Z_QUAD_M:
                inst->delta_z_quad_m = values[i];
                inst->spec007_tuned = true;
                break;
            default:
                inst->log(fmi3Error, "logStatusError", "Invalid Float64 valueReference in fmi3SetFloat64");
                return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetFloat64(
    fmi3Instance instance,
    const fmi3ValueReference valueReferences[],
    size_t nValueReferences,
    fmi3Float64 values[],
    size_t nValues
) {
    if (instance == nullptr || nValueReferences != nValues) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    for (size_t i = 0; i < nValueReferences; ++i) {
        switch (valueReferences[i]) {
            case VR_TIME:
                values[i] = inst->current_time;
                break;
            case VR_OMEGA_IN:
                values[i] = inst->omega_in;
                break;
            case VR_SHUPE_PHASE_IN:
                values[i] = inst->shupe_phase_in;
                break;
            case VR_OMEGA_OUT:
                values[i] = inst->outputs.omega_out_rad_per_s;
                break;
            case VR_E_VPI_RES:
                values[i] = inst->outputs.e_vpi_res_rad;
                break;
            case VR_EPS_VPI:
                values[i] = inst->eps_vpi;
                break;
            case VR_K_XTALK:
                values[i] = inst->k_xtalk;
                break;
            case VR_OMEGA_OUT_AVG:
                values[i] = inst->outputs.omega_out_avg_rad_per_s;
                break;
            case VR_C_XTALK_F:
                values[i] = inst->C_xtalk_F;
                break;
            case VR_G_XTALK_S:
                values[i] = inst->G_xtalk_S;
                break;
            case VR_C_PINK_COEFF:
                values[i] = inst->c_pink_coeff;
                break;
            case VR_R_FACET_DB:
                values[i] = inst->R_facet_dB;
                break;
            case VR_ALPHA_VPI_PPM_K:
                values[i] = inst->alpha_vpi_ppm_K;
                break;
            case VR_ALPHA_BOBBIN_PPM_K:
                values[i] = inst->alpha_bobbin_ppm_K;
                break;
            case VR_DELTA_Z_QUAD_M:
                values[i] = inst->delta_z_quad_m;
                break;
            default:
                inst->log(fmi3Error, "logStatusError", "Invalid Float64 valueReference in fmi3GetFloat64");
                return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3SetBoolean(
    fmi3Instance instance,
    const fmi3ValueReference valueReferences[],
    size_t nValueReferences,
    const fmi3Boolean values[],
    size_t nValues
) {
    if (instance == nullptr || nValueReferences != nValues) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    for (size_t i = 0; i < nValueReferences; ++i) {
        switch (valueReferences[i]) {
            case VR_ENABLE_DITHER:
                inst->enable_dither = values[i];
                break;
            case VR_EN_WHITE_NOISE:
                inst->en_white_noise = values[i];
                break;
            case VR_EN_PINK_NOISE:
                inst->en_pink_noise = values[i];
                break;
            case VR_EN_VPI_LOOP:
                inst->en_vpi_loop = values[i];
                break;
            default:
                inst->log(fmi3Error, "logStatusError", "Invalid Boolean valueReference in fmi3SetBoolean");
                return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetBoolean(
    fmi3Instance instance,
    const fmi3ValueReference valueReferences[],
    size_t nValueReferences,
    fmi3Boolean values[],
    size_t nValues
) {
    if (instance == nullptr || nValueReferences != nValues) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    for (size_t i = 0; i < nValueReferences; ++i) {
        switch (valueReferences[i]) {
            case VR_ENABLE_DITHER:
                values[i] = inst->enable_dither;
                break;
            case VR_EN_WHITE_NOISE:
                values[i] = inst->en_white_noise;
                break;
            case VR_EN_PINK_NOISE:
                values[i] = inst->en_pink_noise;
                break;
            case VR_EN_VPI_LOOP:
                values[i] = inst->en_vpi_loop;
                break;
            default:
                inst->log(fmi3Error, "logStatusError", "Invalid Boolean valueReference in fmi3GetBoolean");
                return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3SetInt32(
    fmi3Instance instance,
    const fmi3ValueReference valueReferences[],
    size_t nValueReferences,
    const fmi3Int32 values[],
    size_t nValues
) {
    if (instance == nullptr || nValueReferences != nValues) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    for (size_t i = 0; i < nValueReferences; ++i) {
        if (valueReferences[i] == VR_DSP_MODE) {
            if (values[i] != 2 && values[i] != 4 && values[i] != 6) {
                inst->log(fmi3Error, "logStatusError", "Unsupported dsp_mode: must be 2, 4, or 6");
                return fmi3Error;
            }
            inst->dsp_mode = values[i];
        } else if (valueReferences[i] == VR_SEED) {
            inst->seed = values[i];
        } else {
            inst->log(fmi3Error, "logStatusError", "Invalid Int32 valueReference in fmi3SetInt32");
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetInt32(
    fmi3Instance instance,
    const fmi3ValueReference valueReferences[],
    size_t nValueReferences,
    fmi3Int32 values[],
    size_t nValues
) {
    if (instance == nullptr || nValueReferences != nValues) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    for (size_t i = 0; i < nValueReferences; ++i) {
        if (valueReferences[i] == VR_DSP_MODE) {
            values[i] = inst->dsp_mode;
        } else if (valueReferences[i] == VR_SEED) {
            values[i] = inst->seed;
        } else {
            inst->log(fmi3Error, "logStatusError", "Invalid Int32 valueReference in fmi3GetInt32");
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetUInt32(
    fmi3Instance instance,
    const fmi3ValueReference valueReferences[],
    size_t nValueReferences,
    fmi3UInt32 values[],
    size_t nValues
) {
    if (instance == nullptr || nValueReferences != nValues) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    for (size_t i = 0; i < nValueReferences; ++i) {
        if (valueReferences[i] == VR_BIT_STATUS) {
            values[i] = inst->outputs.bit_status;
        } else {
            inst->log(fmi3Error, "logStatusError", "Invalid UInt32 valueReference in fmi3GetUInt32");
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3Terminate(fmi3Instance instance) {
    if (instance == nullptr) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    if (!inst->terminated) {
        if (inst->initialized && sc_core::sc_get_status() != sc_core::SC_STOPPED) {
            sc_core::sc_stop();
        }
        inst->terminated = true;
        inst->log(fmi3OK, "logEvents", "Terminated ifog_core SystemC-AMS simulation");
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3Reset(fmi3Instance instance) {
    if (instance == nullptr) {
        return fmi3Error;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    inst->log(
        fmi3Error,
        "logStatusError",
        "fmi3Reset is unsupported: Accellera SystemC sc_simcontext cannot restart in-process"
    );
    return fmi3Error;
}

FMI3_Export void fmi3FreeInstance(fmi3Instance instance) {
    if (instance == nullptr) {
        return;
    }
    auto* inst = static_cast<FmuInstance*>(instance);
    if (!inst->terminated) {
        fmi3Terminate(instance);
    }
    inst->top.reset();
    inst->sig_bit_status.reset();
    inst->sig_e_vpi_res.reset();
    inst->sig_omega_out_avg.reset();
    inst->sig_omega_out.reset();
    inst->sig_en_dither.reset();
    inst->sig_k_xtalk.reset();
    inst->sig_eps_vpi.reset();
    inst->sig_shupe_in.reset();
    inst->sig_omega_in.reset();
    delete inst;
}

// =============================================================================
// Remaining FMI 3.0 Standard C-API Entry Points (Required by FMI 3.0 Binary ABI)
// Unsupported interface types (ME/SE), clocks, FMU state, derivatives, and unused
// scalar types return nullptr / fmi3Error cleanly per FMI 3.0 specification.
// =============================================================================

FMI3_Export fmi3Instance fmi3InstantiateModelExchange(
    fmi3String, fmi3String, fmi3String, fmi3Boolean, fmi3Boolean,
    fmi3InstanceEnvironment, fmi3LogMessageCallback) { return nullptr; }

FMI3_Export fmi3Instance fmi3InstantiateScheduledExecution(
    fmi3String, fmi3String, fmi3String, fmi3Boolean, fmi3Boolean,
    fmi3InstanceEnvironment, fmi3LogMessageCallback, fmi3ClockUpdateCallback,
    fmi3LockPreemptionCallback, fmi3UnlockPreemptionCallback) { return nullptr; }

FMI3_Export fmi3Status fmi3EnterEventMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EnterStepMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EnterConfigurationMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3ExitConfigurationMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EnterContinuousTimeMode(fmi3Instance) { return fmi3Error; }

FMI3_Export fmi3Status fmi3GetFloat32(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Float32[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetFloat32(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Float32[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetInt8(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Int8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetInt8(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetUInt8(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt8(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetInt16(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Int16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetInt16(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetUInt16(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt16(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt32(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt32[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetInt64(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Int64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetInt64(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetUInt64(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt64(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetString(fmi3Instance, const fmi3ValueReference[], size_t, fmi3String[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetString(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3String[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetBinary(fmi3Instance, const fmi3ValueReference[], size_t, size_t[], fmi3Binary[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetBinary(fmi3Instance, const fmi3ValueReference[], size_t, const size_t[], const fmi3Binary[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetClock(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Clock[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetClock(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Clock[]) { return fmi3Error; }

FMI3_Export fmi3Status fmi3GetNumberOfVariableDependencies(fmi3Instance, fmi3ValueReference, size_t*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetVariableDependencies(fmi3Instance, fmi3ValueReference, size_t[], fmi3ValueReference[], size_t[], fmi3DependencyKind[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetFMUState(fmi3Instance, fmi3FMUState*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetFMUState(fmi3Instance, fmi3FMUState) { return fmi3Error; }
FMI3_Export fmi3Status fmi3FreeFMUState(fmi3Instance, fmi3FMUState*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SerializedFMUStateSize(fmi3Instance, fmi3FMUState, size_t*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SerializeFMUState(fmi3Instance, fmi3FMUState, fmi3Byte[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3DeserializeFMUState(fmi3Instance, const fmi3Byte[], size_t, fmi3FMUState*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetDirectionalDerivative(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3ValueReference[], size_t, const fmi3Float64[], size_t, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetAdjointDerivative(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3ValueReference[], size_t, const fmi3Float64[], size_t, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetIntervalDecimal(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Float64[], fmi3IntervalQualifier[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetIntervalFraction(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt64[], fmi3UInt64[], fmi3IntervalQualifier[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetShiftDecimal(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Float64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetShiftFraction(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt64[], fmi3UInt64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetIntervalDecimal(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Float64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetIntervalFraction(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt64[], const fmi3UInt64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetShiftDecimal(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Float64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetShiftFraction(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt64[], const fmi3UInt64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EvaluateDiscreteStates(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3UpdateDiscreteStates(fmi3Instance, fmi3Boolean*, fmi3Boolean*, fmi3Boolean*, fmi3Boolean*, fmi3Boolean*, fmi3Float64*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3CompletedIntegratorStep(fmi3Instance, fmi3Boolean, fmi3Boolean*, fmi3Boolean*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetTime(fmi3Instance, fmi3Float64) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetContinuousStates(fmi3Instance, const fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetContinuousStateDerivatives(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetEventIndicators(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetContinuousStates(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetNominalsOfContinuousStates(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetNumberOfEventIndicators(fmi3Instance, size_t*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetNumberOfContinuousStates(fmi3Instance, size_t*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetOutputDerivatives(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int32[], fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3ActivateModelPartition(fmi3Instance, fmi3ValueReference, fmi3Float64) { return fmi3Error; }

}  // extern "C"
