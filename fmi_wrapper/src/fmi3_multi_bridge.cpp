// =============================================================================
// IFOG-VPROTO v4.1.0 — Multi-Instance Pure-C++17 FMI 3.0.2 Co-Simulation FMU
// Zero SystemC singleton dependency -> canBeInstantiatedOnlyOncePerProcess="false"
// Portable FMI 3.0 Source-Code FMU (binaries/ + sources/buildDescription.xml)
// Implements exact 22-variable SI contract (VR 0..21) matching ifog_core.fmu
// =============================================================================
#include "fmi3/fmi3Functions.h"

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

namespace {

constexpr const char* kMultiToken = "{6e9c4b1a-7f20-4f06-9a5c-000000004100}";
constexpr double kPi = 3.14159265358979323846;
constexpr double kTwoPi = 2.0 * kPi;
constexpr double kCLight = 299792458.0;
constexpr double kQElectron = 1.602176634e-19;
constexpr double kKBoltzmann = 1.380649e-23;

// Value references strictly matching fmi_wrapper/modelDescription_multi.xml.in (VR 0..21)
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

inline double wrap_2pi_multi(double x) {
    return x - kTwoPi * std::round(x / kTwoPi);
}

struct MultiRng {
    uint64_t state;
    bool has_spare;
    double spare;
    explicit MultiRng(uint64_t seed = 42004u)
        : state(seed ? seed : 0x9E3779B97F4A7C15ULL), has_spare(false), spare(0.0) {}

    inline double uniform01() {
        uint64_t x = state;
        x ^= x >> 12;
        x ^= x << 25;
        x ^= x >> 27;
        state = x;
        return static_cast<double>((x * 2685821657736338717ULL) >> 11) * (1.0 / 9007199254740992.0);
    }

    inline double normal01() {
        if (has_spare) {
            has_spare = false;
            return spare;
        }
        const double u1 = std::max(uniform01(), 1.0e-15);
        const double u2 = uniform01();
        const double r = std::sqrt(-2.0 * std::log(u1));
        const double th = kTwoPi * u2;
        spare = r * std::sin(th);
        has_spare = true;
        return r * std::cos(th);
    }
};

struct MultiLfsr {
    uint32_t reg;
    explicit MultiLfsr(uint32_t seed = 1u) : reg(seed ? seed : 1u) {}
    inline int next_signed() {
        const uint32_t b = ((reg >> 31) ^ (reg >> 21) ^ (reg >> 1) ^ reg) & 1u;
        reg = (reg << 1) | b;
        return (b != 0u) ? 1 : -1;
    }
};

struct MultiInstance {
    // Baseline 1 km PM-coil IFOG constants (matching configs/baseline_1km.json)
    static constexpr double kKOpt0 = 1.3521580786785043;
    static constexpr double kTauS = 4.8967209175088724e-6;
    static constexpr double kPPeakW = 1.0e-4;
    static constexpr double kVis0 = 0.99999997;
    static constexpr double kVpi0 = 3.0;
    static constexpr double kResp = 0.95;
    static constexpr double kRf = 50000.0;
    static constexpr double kVfsAdc = 5.0;
    static constexpr double kVrefDac = 6.0;
    static constexpr double kDeltaNuEff = 7.513884342653131e12;
    static constexpr double kAlphaRam = 2.0e-5;
    static constexpr double kGammaNl = 2.0e-4;
    static constexpr int kAdcBits = 16;
    static constexpr int kDacBits = 16;
    static constexpr double kKTot1 = 0.25;
    static constexpr double kKTot2 = 0.02;

    std::string instance_name;
    double current_time = 0.0;
    uint64_t total_tau_steps = 0u;

    // FMI 3.0 inputs & tunable/fixed parameters (VR 0..21)
    double omega_in = 0.0;
    double shupe_phase_in = 0.0;
    double eps_vpi = 0.02;
    double k_xtalk = 1.0e-8;
    bool enable_dither = true;
    int32_t dsp_mode = 6;
    bool en_white_noise = true;
    bool en_pink_noise = false;
    bool en_vpi_loop = true;
    int32_t seed = 42004;

    double C_xtalk_F = 2.0e-12;
    double G_xtalk_S = 1.0e-8;
    double c_pink_coeff = 1.0;
    double R_facet_dB = -200.0;
    double alpha_vpi_ppm_K = 0.0;
    double alpha_bobbin_ppm_K = 0.0;
    double delta_z_quad_m = 0.002;
    bool spec007_tuned = false;

    // Outputs
    double omega_out = 0.0;
    double omega_out_avg = 0.0;
    double e_vpi_res = 0.0;
    uint32_t bit_status = 0u;

    // Per-instance isolated closed-loop state (ZERO global state!)
    double alpha_rad = kPi / 3.0;
    double s_alpha = 1.0;
    double k_i1 = 0.0;
    double k_i2 = 0.0;
    double g_dac_nom = 1.0;
    double g_dac = 1.0;
    double delta_phi_step = 0.0;
    double phi_ramp = 0.0;
    double phi_dither = 0.0;
    double active_dither_step = 0.0;
    double prev_phi_mioc = 0.0;
    double prev_v_drv = 0.0;
    double pink_state = 0.0;
    double theta_env = 0.0;
    int emit_state = 0;
    std::array<double, 6> y_frame{0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
    double prev_y_2s = 0.0;
    bool has_prev_y_2s = false;
    MultiRng rng;
    MultiLfsr lfsr;

    double bias_phase(int st) const {
        if (dsp_mode == 6) {
            constexpr std::array<double, 6> kSeq = {
                2.0 * kPi / 3.0, -2.0 * kPi / 3.0, 0.0, -2.0 * kPi / 3.0, 2.0 * kPi / 3.0, 0.0
            };
            return kSeq[static_cast<size_t>(st % 6)];
        }
        if (dsp_mode == 4) {
            constexpr std::array<double, 4> kSeq = {kPi, kPi / 4.0, -kPi, kPi / 4.0};
            return kSeq[static_cast<size_t>(st % 4)];
        }
        const double half = 0.5 * (kPi - alpha_rad);
        return ((st & 1) == 0) ? half : -half;
    }

    void initialize_core() {
        rng = MultiRng(static_cast<uint64_t>(seed) + 1337u);
        lfsr = MultiLfsr(static_cast<uint32_t>(seed ^ 0xA5A55A5Au));
        alpha_rad = (dsp_mode == 6) ? (kPi / 3.0) : (kPi / 4.0);
        const double scale_adc = static_cast<double>(1ULL << (kAdcBits - 1)) / kVfsAdc;
        s_alpha = scale_adc * kRf * kResp * (0.5 * kPPeakW) * kVis0 * std::sin(alpha_rad);
        g_dac_nom = (2.0 * kVpi0) / kVrefDac;
        g_dac = g_dac_nom;
        if (dsp_mode == 6) {
            k_i1 = kKTot1 / (6.0 * s_alpha);
            k_i2 = kKTot2 / (8.0 * kPi * s_alpha);
            prev_phi_mioc = bias_phase(5);
        } else if (dsp_mode == 4) {
            k_i1 = kKTot1 / (4.0 * s_alpha);
            k_i2 = kKTot2 / (4.0 * kPi * s_alpha);
            prev_phi_mioc = bias_phase(3);
        } else {
            k_i1 = kKTot1 / (2.0 * s_alpha);
            k_i2 = 0.0;
            prev_phi_mioc = bias_phase(1);
        }
        delta_phi_step = 0.0;
        phi_ramp = 0.0;
        phi_dither = 0.0;
        active_dither_step = 0.0;
        prev_v_drv = 0.0;
        pink_state = 0.0;
        theta_env = 0.0;
        emit_state = 0;
        y_frame.fill(0.0);
        prev_y_2s = 0.0;
        has_prev_y_2s = false;
        omega_out = 0.0;
        omega_out_avg = 0.0;
        e_vpi_res = kTwoPi * eps_vpi;
        bit_status = 0u;
    }

    void step_one_tau() {
        const int frame_len = (dsp_mode == 6) ? 6 : ((dsp_mode == 4) ? 4 : 2);
        if (emit_state == 0) {
            if (enable_dither) {
                const int raw_dir = lfsr.next_signed();
                const int dir = (phi_dither > 0.25 * kPi) ? -1 : ((phi_dither < -0.25 * kPi) ? 1 : raw_dir);
                active_dither_step = static_cast<double>(dir) * 3.0e-4;
            } else {
                active_dither_step = 0.0;
            }
        }

        // EQ-21: Digital phase ramp + DAC voltage
        phi_ramp = wrap_2pi_multi(phi_ramp + delta_phi_step);
        phi_dither += active_dither_step;
        const double phi_total = -phi_ramp - phi_dither + bias_phase(emit_state);
        const double dac_lsb = kVrefDac / static_cast<double>(1ULL << kDacBits);
        const double dac_code = std::round((phi_total / kTwoPi) * g_dac * static_cast<double>(1ULL << kDacBits));
        const double v_drv = dac_code * dac_lsb;

        // EQ-11, EQ-12: MIOC phase & differential modulation
        const double phi_now = (kPi / kVpi0) * (1.0 + eps_vpi) * v_drv + kGammaNl * v_drv * v_drv;
        const double dphi_mod = wrap_2pi_multi(phi_now - prev_phi_mioc);
        prev_phi_mioc = phi_now;

        // EQ-52: Optional Rayleigh/facet back-reflection OU phase noise
        double dphi_back = 0.0;
        if (R_facet_dB > -199.0) {
            const double r_fac = std::pow(10.0, R_facet_dB / 10.0);
            const double sigma_b = 2.0 * std::sqrt(r_fac);
            theta_env = 0.99999 * theta_env + 0.00447 * rng.normal01();
            dphi_back = sigma_b * std::sin(theta_env);
        }

        // EQ-06, EQ-13: Detected optical power with RAM
        const double dphi_nr = kKOpt0 * omega_in + shupe_phase_in + dphi_back;
        const double p_det = 0.5 * kPPeakW * (1.0 + kAlphaRam * v_drv)
            * (1.0 + kVis0 * std::cos(dphi_nr + dphi_mod));

        // EQ-14, EQ-15, EQ-51: TIA current + capacitive/resistive crosstalk + white/pink noise
        const double g_xt = spec007_tuned ? G_xtalk_S : k_xtalk;
        const double c_xt = spec007_tuned ? C_xtalk_F : 0.0;
        const double i_xtalk = g_xt * v_drv + c_xt * ((v_drv - prev_v_drv) / kTauS);
        prev_v_drv = v_drv;
        double i_tot = kResp * p_det + i_xtalk;
        if (en_white_noise) {
            const double bw = 1.0 / (2.0 * kTauS);
            const double s_i = 2.0 * kQElectron * kResp * p_det
                + 4.0 * kKBoltzmann * 300.0 / kRf
                + (kResp * p_det) * (kResp * p_det) / kDeltaNuEff;
            i_tot += std::sqrt(s_i * bw) * rng.normal01();
        }
        double v_tia = kRf * i_tot;
        if (en_pink_noise) {
            pink_state = 0.995 * pink_state + 0.0998 * rng.normal01();
            v_tia += c_pink_coeff * 2.0e-5 * pink_state;
        }
        const double v_adc = std::clamp(v_tia, -kVfsAdc, kVfsAdc);
        const double scale_adc = static_cast<double>(1ULL << (kAdcBits - 1)) / kVfsAdc;
        const double y_now = std::round(v_adc * scale_adc);

        // Demodulation & Loop-1 / Loop-2 updates (2s / 4s / 6s)
        y_frame[static_cast<size_t>(emit_state)] = y_now;
        if (dsp_mode == 6 && emit_state == 5) {
            const double e_om = (y_frame[3] + y_frame[4] + y_frame[5])
                - (y_frame[0] + y_frame[1] + y_frame[2])
                + 6.0 * s_alpha * std::sin(active_dither_step);
            delta_phi_step = std::clamp(delta_phi_step + k_i1 * e_om, -20.0, 20.0);
            if (en_vpi_loop) {
                const double e_v = 2.0 * (y_frame[1] + y_frame[4])
                    - (y_frame[0] + y_frame[2] + y_frame[3] + y_frame[5]);
                g_dac = std::clamp(g_dac - k_i2 * e_v, 0.5 * g_dac_nom, 2.0 * g_dac_nom);
            }
        } else if (dsp_mode == 4 && emit_state == 3) {
            const double e_om = (y_frame[1] - y_frame[0]) + (y_frame[3] - y_frame[2])
                + 4.0 * s_alpha * std::sin(active_dither_step);
            delta_phi_step = std::clamp(delta_phi_step + k_i1 * e_om, -20.0, 20.0);
            if (en_vpi_loop) {
                const double e_v = (y_frame[2] + y_frame[3]) - (y_frame[0] + y_frame[1]);
                g_dac = std::clamp(g_dac - k_i2 * e_v, 0.5 * g_dac_nom, 2.0 * g_dac_nom);
            }
        } else if (dsp_mode == 2) {
            if (has_prev_y_2s) {
                const double sgn = (emit_state == 1) ? 1.0 : -1.0;
                const double e_om = sgn * (y_now - prev_y_2s)
                    + 2.0 * s_alpha * std::sin(active_dither_step);
                delta_phi_step = std::clamp(delta_phi_step + k_i1 * e_om, -20.0, 20.0);
            }
            prev_y_2s = y_now;
            has_prev_y_2s = true;
        }

        omega_out = delta_phi_step / kKOpt0;
        const double eps_eff = (1.0 + eps_vpi) * (g_dac / g_dac_nom) - 1.0;
        e_vpi_res = kTwoPi * eps_eff;
        bit_status = (std::fabs(v_tia) >= kVfsAdc) ? (1u << 3) : 0u;
        emit_state = (emit_state + 1) % frame_len;
        ++total_tau_steps;
    }

    void advance_macro_step(double t_curr, double dt_macro) {
        const uint64_t n0 = static_cast<uint64_t>(std::floor(t_curr / kTauS));
        const uint64_t n1 = static_cast<uint64_t>(std::floor((t_curr + dt_macro) / kTauS));
        const uint64_t n_steps = std::max<uint64_t>(1u, n1 - n0);
        double sum_om = 0.0;
        for (uint64_t i = 0u; i < n_steps; ++i) {
            step_one_tau();
            sum_om += omega_out;
        }
        omega_out_avg = sum_om / static_cast<double>(n_steps);
        current_time = t_curr + dt_macro;
    }
};

}  // namespace

extern "C" {

FMI3_Export const char* fmi3GetVersion(void) { return "3.0"; }

FMI3_Export fmi3Status fmi3SetDebugLogging(
    fmi3Instance inst, fmi3Boolean, size_t, const fmi3String[]) {
    return (inst != nullptr) ? fmi3OK : fmi3Error;
}

FMI3_Export fmi3Instance fmi3InstantiateCoSimulation(
    fmi3String instanceName,
    fmi3String instantiationToken,
    fmi3String,
    fmi3Boolean,
    fmi3Boolean,
    fmi3Boolean,
    fmi3Boolean,
    const fmi3ValueReference[],
    size_t,
    fmi3InstanceEnvironment,
    fmi3LogMessageCallback,
    fmi3IntermediateUpdateCallback) {
    if (instanceName == nullptr || instantiationToken == nullptr ||
        std::strcmp(instantiationToken, kMultiToken) != 0) {
        return nullptr;
    }
    auto* m = new MultiInstance();
    m->instance_name = instanceName;
    return static_cast<fmi3Instance>(m);
}

FMI3_Export void fmi3FreeInstance(fmi3Instance inst) {
    delete static_cast<MultiInstance*>(inst);
}

FMI3_Export fmi3Status fmi3EnterInitializationMode(
    fmi3Instance inst, fmi3Boolean, fmi3Float64, fmi3Float64 startTime, fmi3Boolean, fmi3Float64) {
    if (inst == nullptr) {
        return fmi3Error;
    }
    static_cast<MultiInstance*>(inst)->current_time = startTime;
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3ExitInitializationMode(fmi3Instance inst) {
    if (inst == nullptr) {
        return fmi3Error;
    }
    static_cast<MultiInstance*>(inst)->initialize_core();
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3Terminate(fmi3Instance inst) {
    return (inst != nullptr) ? fmi3OK : fmi3Error;
}

FMI3_Export fmi3Status fmi3Reset(fmi3Instance inst) {
    if (inst == nullptr) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    m->current_time = 0.0;
    m->initialize_core();
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetFloat64(
    fmi3Instance inst, const fmi3ValueReference vrs[], size_t nvr, fmi3Float64 vals[], size_t nvals) {
    if (inst == nullptr || nvr != nvals || (nvr > 0 && (vrs == nullptr || vals == nullptr))) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    for (size_t i = 0; i < nvr; ++i) {
        switch (vrs[i]) {
            case VR_TIME: vals[i] = m->current_time; break;
            case VR_OMEGA_IN: vals[i] = m->omega_in; break;
            case VR_SHUPE_PHASE_IN: vals[i] = m->shupe_phase_in; break;
            case VR_OMEGA_OUT: vals[i] = m->omega_out; break;
            case VR_E_VPI_RES: vals[i] = m->e_vpi_res; break;
            case VR_EPS_VPI: vals[i] = m->eps_vpi; break;
            case VR_K_XTALK: vals[i] = m->k_xtalk; break;
            case VR_OMEGA_OUT_AVG: vals[i] = m->omega_out_avg; break;
            case VR_C_XTALK_F: vals[i] = m->C_xtalk_F; break;
            case VR_G_XTALK_S: vals[i] = m->G_xtalk_S; break;
            case VR_C_PINK_COEFF: vals[i] = m->c_pink_coeff; break;
            case VR_R_FACET_DB: vals[i] = m->R_facet_dB; break;
            case VR_ALPHA_VPI_PPM_K: vals[i] = m->alpha_vpi_ppm_K; break;
            case VR_ALPHA_BOBBIN_PPM_K: vals[i] = m->alpha_bobbin_ppm_K; break;
            case VR_DELTA_Z_QUAD_M: vals[i] = m->delta_z_quad_m; break;
            default: return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3SetFloat64(
    fmi3Instance inst, const fmi3ValueReference vrs[], size_t nvr, const fmi3Float64 vals[], size_t nvals) {
    if (inst == nullptr || nvr != nvals || (nvr > 0 && (vrs == nullptr || vals == nullptr))) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    for (size_t i = 0; i < nvr; ++i) {
        switch (vrs[i]) {
            case VR_OMEGA_IN: m->omega_in = vals[i]; break;
            case VR_SHUPE_PHASE_IN: m->shupe_phase_in = vals[i]; break;
            case VR_EPS_VPI: m->eps_vpi = vals[i]; break;
            case VR_K_XTALK: m->k_xtalk = vals[i]; break;
            case VR_C_XTALK_F: m->C_xtalk_F = vals[i]; m->spec007_tuned = true; break;
            case VR_G_XTALK_S: m->G_xtalk_S = vals[i]; m->spec007_tuned = true; break;
            case VR_C_PINK_COEFF: m->c_pink_coeff = vals[i]; m->spec007_tuned = true; break;
            case VR_R_FACET_DB: m->R_facet_dB = vals[i]; m->spec007_tuned = true; break;
            case VR_ALPHA_VPI_PPM_K: m->alpha_vpi_ppm_K = vals[i]; m->spec007_tuned = true; break;
            case VR_ALPHA_BOBBIN_PPM_K: m->alpha_bobbin_ppm_K = vals[i]; m->spec007_tuned = true; break;
            case VR_DELTA_Z_QUAD_M: m->delta_z_quad_m = vals[i]; m->spec007_tuned = true; break;
            default: return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetInt32(
    fmi3Instance inst, const fmi3ValueReference vrs[], size_t nvr, fmi3Int32 vals[], size_t nvals) {
    if (inst == nullptr || nvr != nvals || (nvr > 0 && (vrs == nullptr || vals == nullptr))) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    for (size_t i = 0; i < nvr; ++i) {
        if (vrs[i] == VR_DSP_MODE) {
            vals[i] = m->dsp_mode;
        } else if (vrs[i] == VR_SEED) {
            vals[i] = m->seed;
        } else {
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3SetInt32(
    fmi3Instance inst, const fmi3ValueReference vrs[], size_t nvr, const fmi3Int32 vals[], size_t nvals) {
    if (inst == nullptr || nvr != nvals || (nvr > 0 && (vrs == nullptr || vals == nullptr))) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    for (size_t i = 0; i < nvr; ++i) {
        if (vrs[i] == VR_DSP_MODE && (vals[i] == 2 || vals[i] == 4 || vals[i] == 6)) {
            m->dsp_mode = vals[i];
        } else if (vrs[i] == VR_SEED) {
            m->seed = vals[i];
        } else {
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetUInt32(
    fmi3Instance inst, const fmi3ValueReference vrs[], size_t nvr, fmi3UInt32 vals[], size_t nvals) {
    if (inst == nullptr || nvr != nvals || (nvr > 0 && (vrs == nullptr || vals == nullptr))) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    for (size_t i = 0; i < nvr; ++i) {
        if (vrs[i] == VR_BIT_STATUS) {
            vals[i] = m->bit_status;
        } else {
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3GetBoolean(
    fmi3Instance inst, const fmi3ValueReference vrs[], size_t nvr, fmi3Boolean vals[], size_t nvals) {
    if (inst == nullptr || nvr != nvals || (nvr > 0 && (vrs == nullptr || vals == nullptr))) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    for (size_t i = 0; i < nvr; ++i) {
        if (vrs[i] == VR_ENABLE_DITHER) {
            vals[i] = m->enable_dither ? fmi3True : fmi3False;
        } else if (vrs[i] == VR_EN_WHITE_NOISE) {
            vals[i] = m->en_white_noise ? fmi3True : fmi3False;
        } else if (vrs[i] == VR_EN_PINK_NOISE) {
            vals[i] = m->en_pink_noise ? fmi3True : fmi3False;
        } else if (vrs[i] == VR_EN_VPI_LOOP) {
            vals[i] = m->en_vpi_loop ? fmi3True : fmi3False;
        } else {
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3SetBoolean(
    fmi3Instance inst, const fmi3ValueReference vrs[], size_t nvr, const fmi3Boolean vals[], size_t nvals) {
    if (inst == nullptr || nvr != nvals || (nvr > 0 && (vrs == nullptr || vals == nullptr))) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    for (size_t i = 0; i < nvr; ++i) {
        if (vrs[i] == VR_ENABLE_DITHER) {
            m->enable_dither = (vals[i] == fmi3True);
        } else if (vrs[i] == VR_EN_WHITE_NOISE) {
            m->en_white_noise = (vals[i] == fmi3True);
        } else if (vrs[i] == VR_EN_PINK_NOISE) {
            m->en_pink_noise = (vals[i] == fmi3True);
        } else if (vrs[i] == VR_EN_VPI_LOOP) {
            m->en_vpi_loop = (vals[i] == fmi3True);
        } else {
            return fmi3Error;
        }
    }
    return fmi3OK;
}

FMI3_Export fmi3Status fmi3DoStep(
    fmi3Instance inst,
    fmi3Float64 currentCommunicationPoint,
    fmi3Float64 communicationStepSize,
    fmi3Boolean,
    fmi3Boolean* eventHandlingNeeded,
    fmi3Boolean* terminateSimulation,
    fmi3Boolean* earlyReturn,
    fmi3Float64* lastSuccessfulTime) {
    if (inst == nullptr || communicationStepSize <= 0.0 ||
        eventHandlingNeeded == nullptr || terminateSimulation == nullptr ||
        earlyReturn == nullptr || lastSuccessfulTime == nullptr) {
        return fmi3Error;
    }
    auto* m = static_cast<MultiInstance*>(inst);
    m->advance_macro_step(currentCommunicationPoint, communicationStepSize);
    *eventHandlingNeeded = fmi3False;
    *terminateSimulation = fmi3False;
    *earlyReturn = fmi3False;
    *lastSuccessfulTime = m->current_time;
    return fmi3OK;
}

// Remaining official FMI 3.0 C-API symbols (for full 75-symbol FMPy loader compatibility)
FMI3_Export fmi3Instance fmi3InstantiateModelExchange(fmi3String, fmi3String, fmi3String, fmi3Boolean, fmi3Boolean, fmi3InstanceEnvironment, fmi3LogMessageCallback) { return nullptr; }
FMI3_Export fmi3Instance fmi3InstantiateScheduledExecution(fmi3String, fmi3String, fmi3String, fmi3Boolean, fmi3Boolean, fmi3InstanceEnvironment, fmi3LogMessageCallback, fmi3ClockUpdateCallback, fmi3LockPreemptionCallback, fmi3UnlockPreemptionCallback) { return nullptr; }
FMI3_Export fmi3Status fmi3EnterEventMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EnterConfigurationMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3ExitConfigurationMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetFloat32(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Float32[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetInt8(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Int8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetUInt8(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetInt16(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Int16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetUInt16(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetInt64(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Int64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetUInt64(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetString(fmi3Instance, const fmi3ValueReference[], size_t, fmi3String[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetBinary(fmi3Instance, const fmi3ValueReference[], size_t, size_t[], fmi3Binary[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetClock(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Clock[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetFloat32(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Float32[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetInt8(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt8(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt8[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetInt16(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt16(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt16[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt32(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt32[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetInt64(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetUInt64(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetString(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3String[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetBinary(fmi3Instance, const fmi3ValueReference[], size_t, const size_t[], const fmi3Binary[], size_t) { return fmi3Error; }
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
FMI3_Export fmi3Status fmi3GetOutputDerivatives(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Int32[], fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EnterStepMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EnterContinuousTimeMode(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3CompletedIntegratorStep(fmi3Instance, fmi3Boolean, fmi3Boolean*, fmi3Boolean*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetTime(fmi3Instance, fmi3Float64) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetContinuousStates(fmi3Instance, const fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetContinuousStateDerivatives(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetEventIndicators(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetContinuousStates(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetNominalsOfContinuousStates(fmi3Instance, fmi3Float64[], size_t) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetNumberOfEventIndicators(fmi3Instance, size_t*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetNumberOfContinuousStates(fmi3Instance, size_t*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3UpdateDiscreteStates(fmi3Instance, fmi3Boolean*, fmi3Boolean*, fmi3Boolean*, fmi3Boolean*, fmi3Boolean*, fmi3Float64*) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetIntervalDecimal(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Float64[], fmi3IntervalQualifier[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetIntervalFraction(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt64[], fmi3UInt64[], fmi3IntervalQualifier[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetShiftDecimal(fmi3Instance, const fmi3ValueReference[], size_t, fmi3Float64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3GetShiftFraction(fmi3Instance, const fmi3ValueReference[], size_t, fmi3UInt64[], fmi3UInt64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetIntervalDecimal(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Float64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetIntervalFraction(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt64[], const fmi3UInt64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetShiftDecimal(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3Float64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3SetShiftFraction(fmi3Instance, const fmi3ValueReference[], size_t, const fmi3UInt64[], const fmi3UInt64[]) { return fmi3Error; }
FMI3_Export fmi3Status fmi3EvaluateDiscreteStates(fmi3Instance) { return fmi3Error; }
FMI3_Export fmi3Status fmi3ActivateModelPartition(fmi3Instance, fmi3ValueReference, fmi3Float64) { return fmi3Error; }

}  // extern "C"
