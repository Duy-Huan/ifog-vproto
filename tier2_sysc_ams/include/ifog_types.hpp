#ifndef IFOG_TYPES_HPP
#define IFOG_TYPES_HPP

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ifog {

// Exact SI / CODATA physical constants matching tier1_offline/config_loader.py
constexpr double C_LIGHT = 299792458.0;            // m/s
constexpr double Q_ELECTRON = 1.602176634e-19;     // C
constexpr double K_BOLTZMANN = 1.380649e-23;       // J/K
constexpr double PI = 3.14159265358979323846;
constexpr double TWO_PI = 2.0 * PI;
constexpr double RAD_S_TO_DEG_H = (180.0 / PI) * 3600.0;
constexpr double OMEGA_OUT_LSB = 1.0e-12;          // rad/s per raw LSB in SimRecord

// Normative 32-byte binary output record (IFOG-SIM-SPEC-004 Section 2, I/O Contract)
#pragma pack(push, 1)
struct SimRecord {
    double t;
    double omega_in;
    int64_t omega_out_raw;
    int32_t vpi_err_raw;
    uint32_t flags;
};
#pragma pack(pop)

static_assert(sizeof(SimRecord) == 32, "SimRecord must be exactly 32 bytes per IFOG-SIM-SPEC-004");

// Flag bit definitions for SimRecord::flags
constexpr uint32_t FLAG_FLYBACK_RESET = 1u << 0;
constexpr uint32_t FLAG_ADC_CLIPPED = 1u << 1;
constexpr uint32_t FLAG_DSP_4STATE = 1u << 2;
constexpr uint32_t FLAG_VPI_LOOP_EN = 1u << 3;
constexpr uint32_t FLAG_PRBS_DITHER_EN = 1u << 4;

// Optional micro-sample waveform diagnostic record (64 bytes, local window dump for plot_waveforms.py)
#pragma pack(push, 1)
struct MicroRecord {
    double t;
    double v_drv;
    double p_det;
    double v_tia;
    double v_adc;
    double phi_ramp;
    int32_t adc_code;
    uint32_t k_idx;
    uint32_t in_blanking;
    uint32_t reserved;
};
#pragma pack(pop)

static_assert(sizeof(MicroRecord) == 64, "MicroRecord must be exactly 64 bytes");

// 10 normative physical/analog impairment isolation flags (IFOG-SIM-SPEC-004)
struct AblationConfig {
    bool en_pol_error = true;
    bool en_kerr = true;
    bool en_shupe = false;
    bool en_faraday = false;
    bool en_mioc_vpi_err = true;
    bool en_ram = true;
    bool en_xtalk = true;
    bool en_ltf_transient = true;
    bool en_tia_poly_nl = true;
    bool en_quantization = true;
};

enum class DspMode {
    TwoState,
    FourState
};

enum class StimulusType {
    Constant,
    Step,
    Ramp,
    Sine
};

enum class SineInjectTarget {
    None,
    Tia,
    Dac,
    Xtalk
};

struct ShupeSample {
    double t_s;
    double delta_phi_rad;
};

struct IfogConfig {
    // Meta
    std::string name;
    uint64_t seed = 42004;

    // Optics (merged from config + phys_params.json)
    double L_m = 1000.0;
    double D_m = 0.10;
    double lambda_bar_m = 1.55e-6;
    double n_eff = 1.468;
    double P_peak_W = 1.0e-4;
    double P_coil_W = 1.0e-3;
    double delta_nu_eff_Hz = 7.51e12;
    double visibility_V = 1.0;
    double phi_pol_rad = 0.0;
    double phi_pol_drift_rad_per_s = 0.0;
    double K_opt = 1.3521584;
    double tau_s = 4.8967209e-6;
    double delta_phi_kerr_rad = 0.0;

    // Magneto-optic Faraday (EQ-10)
    double verdet_rad_per_Tm = 0.6;
    double B_ext_T = 0.0;
    double effective_loop_m = 0.0;

    // MIOC (EQ-11, EQ-13)
    double V_pi_0_V = 3.0;
    double eps_vpi = 0.02;
    double gamma_nl_rad_per_V2 = 1.0e-3;
    double alpha_ram_per_V = 2.0e-3;

    // Analog Front-End (EQ-14..EQ-18)
    double responsivity_A_per_W = 0.95;
    double I_dark_A = 5.0e-9;
    double R_f_ohm = 50000.0;
    double C_tot_F = 3.0e-12;
    double C_f_F = 2.52313252202016e-13;
    double f_gbw_Hz = 150.0e6;
    double T_tia_K = 300.0;
    double e_n_op_V_per_rtHz = 4.0e-9;
    double i_n_op_A_per_rtHz = 2.0e-12;
    double V_off_0_V = 0.0;
    double G1 = 1.0;
    double G2_per_V = 2.0e-3;
    double G3_per_V2 = 5.0e-4;
    double V_min_V = -5.0;
    double V_max_V = 5.0;
    double C_xtalk_F = 0.5e-12;
    double k_xtalk_A_per_V = 1.0e-7;

    // ADC / DAC (EQ-19, EQ-21)
    int K_oversample = 16;
    int N_adc_bits = 16;
    double V_fs_adc_V = 5.0;
    int k_start = 4;
    int k_end = 15;
    int N_dac_bits = 16;
    double V_ref_dac_V = 6.0;
    double drv_omega0_rad_per_s = 1.0e8;
    double drv_zeta = 0.7071067811865476;

    // Digital DSP (EQ-01, EQ-03, EQ-20..EQ-23)
    DspMode dsp_mode = DspMode::FourState;
    double alpha_rad = PI / 4.0;
    double K_tot_1 = 0.25;
    double K_P_1 = 0.0;
    double K_tot_2 = 0.02;
    bool en_adc_blanking = true;
    bool en_vpi_loop = true;
    bool en_prbs_dither = true;
    double prbs_amplitude_rad = 0.02;

    // Noise (EQ-15 & PinkNoise_TDF)
    bool en_white_noise = true;
    bool en_pink_noise = true;
    double pink_f_min_Hz = 1.0;
    double pink_f_max_Hz = 5000.0;
    double sigma_pink_tia_V = 2.0e-4;
    double sigma_pink_dac_rel = 5.0e-5;
    double sigma_pink_xtalk_rel = 1.0e-3;
    SineInjectTarget sine_inject_target = SineInjectTarget::None;
    double sine_inject_freq_Hz = 100.0;
    double sine_inject_amp = 0.0;

    // Ablation
    AblationConfig ablation;

    // Simulation runtime parameters
    double duration_s = 1.0;
    uint32_t decimation_tau = 4;
    double dump_micro_ms = 0.0;

    // Stimulus
    StimulusType stimulus_type = StimulusType::Constant;
    double omega_const_rad_per_s = 0.0;
    double omega_start_rad_per_s = 0.0;
    double omega_end_rad_per_s = 0.0;
    double step_time_s = 0.0;
    double sine_freq_Hz = 0.0;
    double sine_amp_rad_per_s = 0.0;

    // Optional Shupe LUT loaded from shupe_lut.bin
    std::vector<ShupeSample> shupe_lut;
};

struct SimSummary {
    uint64_t total_tau_steps = 0;
    uint64_t total_records_written = 0;
    uint64_t total_micro_records = 0;
    uint64_t flyback_count = 0;
    uint64_t adc_clip_count = 0;
    double final_omega_out_rad_per_s = 0.0;
    double final_delta_phi_step_rad = 0.0;
    double final_g_dac = 1.0;
    double final_eps_vpi_eff = 0.0;
    double mean_omega_out_second_half_rad_per_s = 0.0;
    double tia_omega0_rad_per_s = 0.0;
    double tia_zeta = 0.0;
    double tia_cf_opt_F = 0.0;
    double tia_ts_0p1pct_s = 0.0;
    double eta_blanking = 1.0;
    double S_alpha_counts_per_rad = 0.0;
};

}  // namespace ifog

#endif  // IFOG_TYPES_HPP
