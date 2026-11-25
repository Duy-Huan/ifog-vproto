#include "ifog_config.hpp"

#include <cstring>
#include <fstream>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include "ifog_math.hpp"

namespace ifog {

using json = nlohmann::json;

std::vector<ShupeSample> load_shupe_lut(const std::string& lut_path) {
    std::ifstream ifs(lut_path, std::ios::binary);
    if (!ifs.is_open()) {
        throw std::runtime_error("Cannot open shupe_lut.bin: " + lut_path);
    }
    char magic[4] = {};
    uint32_t version = 0;
    uint64_t n_samples = 0;
    double dt_s = 0.0;
    ifs.read(magic, 4);
    ifs.read(reinterpret_cast<char*>(&version), sizeof(version));
    ifs.read(reinterpret_cast<char*>(&n_samples), sizeof(n_samples));
    ifs.read(reinterpret_cast<char*>(&dt_s), sizeof(dt_s));

    if (!ifs || std::memcmp(magic, "SHUP", 4) != 0 || version != 1u) {
        throw std::runtime_error("Invalid shupe_lut.bin header in: " + lut_path);
    }

    std::vector<ShupeSample> samples(static_cast<size_t>(n_samples));
    for (size_t i = 0; i < samples.size(); ++i) {
        ifs.read(reinterpret_cast<char*>(&samples[i].t_s), sizeof(double));
        ifs.read(reinterpret_cast<char*>(&samples[i].delta_phi_rad), sizeof(double));
    }
    if (!ifs) {
        throw std::runtime_error("Truncated shupe_lut.bin data in: " + lut_path);
    }
    return samples;
}

void validate_ifog_config(const IfogConfig& cfg) {
    if (cfg.K_oversample != 16 && cfg.K_oversample != 32) {
        throw std::invalid_argument("K_oversample must be 16 or 32 per IFOG-SIM-SPEC-004");
    }
    if (cfg.k_start < 0 || cfg.k_end < cfg.k_start || cfg.k_end >= cfg.K_oversample) {
        throw std::invalid_argument("Invalid ADC blanking window [k_start, k_end]");
    }
    if (!check_jury_stability(cfg.K_tot_1)) {
        throw std::invalid_argument("Jury stability violated (EQ-22): K_tot_1 must be in (0, 1)");
    }
    if (cfg.dsp_mode == DspMode::FourState && cfg.en_vpi_loop) {
        if (!check_dual_loop_separation(cfg.K_tot_1, cfg.K_tot_2)) {
            throw std::invalid_argument("Loop-2 bandwidth separation violated (EQ-22): K_tot_2 > 0.1 * K_tot_1");
        }
    }
    if (cfg.duration_s <= 0.0 || cfg.decimation_tau == 0u) {
        throw std::invalid_argument("duration_s and decimation_tau must be positive");
    }
    if (cfg.V_min_V >= cfg.V_max_V) {
        throw std::invalid_argument("ADC rails V_min_V must be strictly less than V_max_V");
    }
}

IfogConfig load_ifog_config(
    const std::string& cfg_path,
    const std::string& phys_path,
    const std::string& shupe_lut_path
) {
    std::ifstream cfg_ifs(cfg_path);
    if (!cfg_ifs.is_open()) {
        throw std::runtime_error("Cannot open config JSON: " + cfg_path);
    }
    json jcfg;
    cfg_ifs >> jcfg;

    std::ifstream phys_ifs(phys_path);
    if (!phys_ifs.is_open()) {
        throw std::runtime_error("Cannot open phys_params JSON: " + phys_path);
    }
    json jphys;
    phys_ifs >> jphys;

    IfogConfig cfg;
    const auto& meta = jcfg.at("meta");
    cfg.name = meta.at("name").get<std::string>();
    cfg.seed = meta.at("seed").get<uint64_t>();

    // Optics from config + Tier-1 phys_params.json
    const auto& opt = jcfg.at("optics");
    cfg.L_m = opt.at("L_m").get<double>();
    cfg.D_m = opt.at("D_m").get<double>();
    cfg.lambda_bar_m = opt.at("lambda_bar_m").get<double>();
    cfg.n_eff = opt.at("n_eff").get<double>();
    cfg.P_peak_W = opt.at("P_peak_W").get<double>();
    cfg.P_coil_W = opt.at("P_coil_W").get<double>();
    cfg.phi_pol_drift_rad_per_s = opt.value("phi_pol_drift_rad_per_s", 0.0);

    cfg.visibility_V = jphys.at("visibility_V").get<double>();
    cfg.phi_pol_rad = jphys.at("phi_pol_rad").get<double>();
    cfg.K_opt = jphys.at("K_opt_rad_per_rad_s").get<double>();
    cfg.tau_s = jphys.at("tau_s").get<double>();
    cfg.delta_nu_eff_Hz = jphys.at("delta_nu_eff_Hz").get<double>();
    cfg.delta_phi_kerr_rad = jphys.at("delta_phi_kerr_rad").get<double>();

    // Magneto-optic
    const auto& mag = jcfg.at("magneto_optic");
    cfg.verdet_rad_per_Tm = mag.at("verdet_rad_per_Tm").get<double>();
    cfg.B_ext_T = mag.at("B_ext_T").get<double>();
    cfg.effective_loop_m = mag.at("effective_loop_m").get<double>();

    // MIOC
    const auto& mioc = jcfg.at("mioc");
    cfg.V_pi_0_V = mioc.at("V_pi_0_V").get<double>();
    cfg.eps_vpi = mioc.at("eps_vpi").get<double>();
    cfg.gamma_nl_rad_per_V2 = mioc.at("gamma_nl_rad_per_V2").get<double>();
    cfg.alpha_ram_per_V = mioc.at("alpha_ram_per_V").get<double>();

    // Analog Front-End
    const auto& afe = jcfg.at("analog_frontend");
    cfg.responsivity_A_per_W = afe.at("responsivity_A_per_W").get<double>();
    cfg.I_dark_A = afe.at("I_dark_A").get<double>();
    cfg.R_f_ohm = afe.at("R_f_ohm").get<double>();
    cfg.C_tot_F = afe.at("C_tot_F").get<double>();
    cfg.C_f_F = afe.at("C_f_F").get<double>();
    cfg.f_gbw_Hz = afe.at("f_gbw_Hz").get<double>();
    cfg.T_tia_K = afe.at("T_tia_K").get<double>();
    cfg.e_n_op_V_per_rtHz = afe.at("e_n_op_V_per_rtHz").get<double>();
    cfg.i_n_op_A_per_rtHz = afe.at("i_n_op_A_per_rtHz").get<double>();
    cfg.V_off_0_V = afe.at("V_off_0_V").get<double>();
    cfg.G1 = afe.at("G1").get<double>();
    cfg.G2_per_V = afe.at("G2_per_V").get<double>();
    cfg.G3_per_V2 = afe.at("G3_per_V2").get<double>();
    cfg.V_min_V = afe.at("V_min_V").get<double>();
    cfg.V_max_V = afe.at("V_max_V").get<double>();
    cfg.C_xtalk_F = afe.at("C_xtalk_F").get<double>();
    cfg.k_xtalk_A_per_V = afe.at("k_xtalk_A_per_V").get<double>();

    // ADC / DAC
    const auto& adc = jcfg.at("adc_dac");
    cfg.K_oversample = adc.at("K_oversample").get<int>();
    cfg.N_adc_bits = adc.at("N_adc_bits").get<int>();
    cfg.V_fs_adc_V = adc.at("V_fs_adc_V").get<double>();
    cfg.k_start = adc.at("k_start").get<int>();
    cfg.k_end = adc.at("k_end").get<int>();
    cfg.N_dac_bits = adc.at("N_dac_bits").get<int>();
    cfg.V_ref_dac_V = adc.at("V_ref_dac_V").get<double>();
    cfg.drv_omega0_rad_per_s = adc.at("drv_omega0_rad_per_s").get<double>();
    cfg.drv_zeta = adc.at("drv_zeta").get<double>();

    // DSP
    const auto& dsp = jcfg.at("dsp");
    const std::string mode_str = dsp.at("mode").get<std::string>();
    if (mode_str == "4state") {
        cfg.dsp_mode = DspMode::FourState;
    } else if (mode_str == "2state") {
        cfg.dsp_mode = DspMode::TwoState;
    } else {
        throw std::invalid_argument("Unsupported dsp.mode: " + mode_str);
    }
    cfg.alpha_rad = dsp.at("alpha_rad").get<double>();
    cfg.K_tot_1 = dsp.at("K_tot_1").get<double>();
    cfg.K_P_1 = dsp.at("K_P_1").get<double>();
    cfg.K_tot_2 = dsp.at("K_tot_2").get<double>();
    cfg.en_adc_blanking = dsp.at("en_adc_blanking").get<bool>();
    cfg.en_vpi_loop = dsp.at("en_vpi_loop").get<bool>();
    cfg.en_prbs_dither = dsp.at("en_prbs_dither").get<bool>();
    cfg.prbs_amplitude_rad = dsp.at("prbs_amplitude_rad").get<double>();

    // Noise
    const auto& ns = jcfg.at("noise");
    cfg.en_white_noise = ns.at("en_white_noise").get<bool>();
    cfg.en_pink_noise = ns.at("en_pink_noise").get<bool>();
    cfg.pink_f_min_Hz = ns.at("pink_f_min_Hz").get<double>();
    cfg.pink_f_max_Hz = ns.at("pink_f_max_Hz").get<double>();
    cfg.sigma_pink_tia_V = ns.at("sigma_pink_tia_V").get<double>();
    cfg.sigma_pink_dac_rel = ns.at("sigma_pink_dac_rel").get<double>();
    cfg.sigma_pink_xtalk_rel = ns.at("sigma_pink_xtalk_rel").get<double>();

    const std::string inj_str = ns.value("sine_inject_target", std::string("none"));
    if (inj_str == "none") {
        cfg.sine_inject_target = SineInjectTarget::None;
    } else if (inj_str == "tia") {
        cfg.sine_inject_target = SineInjectTarget::Tia;
    } else if (inj_str == "dac") {
        cfg.sine_inject_target = SineInjectTarget::Dac;
    } else if (inj_str == "xtalk") {
        cfg.sine_inject_target = SineInjectTarget::Xtalk;
    } else {
        throw std::invalid_argument("Unsupported sine_inject_target: " + inj_str);
    }
    cfg.sine_inject_freq_Hz = ns.value("sine_inject_freq_Hz", 100.0);
    cfg.sine_inject_amp = ns.value("sine_inject_amp", 0.0);

    // Ablation flags (10 flags)
    const auto& ab = jcfg.at("ablation_flags");
    cfg.ablation.en_pol_error = ab.at("en_pol_error").get<bool>();
    cfg.ablation.en_kerr = ab.at("en_kerr").get<bool>();
    cfg.ablation.en_shupe = ab.at("en_shupe").get<bool>();
    cfg.ablation.en_faraday = ab.at("en_faraday").get<bool>();
    cfg.ablation.en_mioc_vpi_err = ab.at("en_mioc_vpi_err").get<bool>();
    cfg.ablation.en_ram = ab.at("en_ram").get<bool>();
    cfg.ablation.en_xtalk = ab.at("en_xtalk").get<bool>();
    cfg.ablation.en_ltf_transient = ab.at("en_ltf_transient").get<bool>();
    cfg.ablation.en_tia_poly_nl = ab.at("en_tia_poly_nl").get<bool>();
    cfg.ablation.en_quantization = ab.at("en_quantization").get<bool>();

    // Simulation
    const auto& sim = jcfg.at("simulation");
    cfg.duration_s = sim.at("duration_s").get<double>();
    cfg.decimation_tau = sim.at("decimation_tau").get<uint32_t>();
    cfg.dump_micro_ms = sim.value("dump_micro_ms", 0.0);

    const auto& stim = sim.at("stimulus");
    const std::string stype = stim.at("type").get<std::string>();
    if (stype == "constant") {
        cfg.stimulus_type = StimulusType::Constant;
        cfg.omega_const_rad_per_s = stim.value("omega_rad_per_s", 0.0);
    } else if (stype == "step") {
        cfg.stimulus_type = StimulusType::Step;
        cfg.omega_start_rad_per_s = stim.value("omega_start_rad_per_s", 0.0);
        cfg.omega_end_rad_per_s = stim.value("omega_end_rad_per_s", 0.0);
        cfg.step_time_s = stim.value("step_time_s", 0.0);
    } else if (stype == "ramp") {
        cfg.stimulus_type = StimulusType::Ramp;
        cfg.omega_start_rad_per_s = stim.value("omega_start_rad_per_s", 0.0);
        cfg.omega_end_rad_per_s = stim.value("omega_end_rad_per_s", 0.0);
    } else if (stype == "sine") {
        cfg.stimulus_type = StimulusType::Sine;
        cfg.omega_const_rad_per_s = stim.value("omega_rad_per_s", 0.0);
        cfg.sine_freq_Hz = stim.value("freq_Hz", 10.0);
        cfg.sine_amp_rad_per_s = stim.value("amp_rad_per_s", 0.0);
    } else {
        throw std::invalid_argument("Unsupported stimulus.type: " + stype);
    }

    if (!shupe_lut_path.empty()) {
        cfg.shupe_lut = load_shupe_lut(shupe_lut_path);
    }

    validate_ifog_config(cfg);
    return cfg;
}

void write_sim_summary_json(const std::string& out_path, const SimSummary& s) {
    json j = {
        {"spec_id", "IFOG-SIM-SPEC-004"},
        {"total_tau_steps", s.total_tau_steps},
        {"total_records_written", s.total_records_written},
        {"total_micro_records", s.total_micro_records},
        {"flyback_count", s.flyback_count},
        {"adc_clip_count", s.adc_clip_count},
        {"final_omega_out_rad_per_s", s.final_omega_out_rad_per_s},
        {"final_delta_phi_step_rad", s.final_delta_phi_step_rad},
        {"final_g_dac", s.final_g_dac},
        {"final_eps_vpi_eff", s.final_eps_vpi_eff},
        {"mean_omega_out_second_half_rad_per_s", s.mean_omega_out_second_half_rad_per_s},
        {"tia_omega0_rad_per_s", s.tia_omega0_rad_per_s},
        {"tia_zeta", s.tia_zeta},
        {"tia_cf_opt_F", s.tia_cf_opt_F},
        {"tia_ts_0p1pct_s", s.tia_ts_0p1pct_s},
        {"eta_blanking", s.eta_blanking},
        {"S_alpha_counts_per_rad", s.S_alpha_counts_per_rad},
        {"omega_out_lsb_rad_per_s", OMEGA_OUT_LSB},
    };
    std::ofstream ofs(out_path);
    if (!ofs.is_open()) {
        throw std::runtime_error("Cannot write sim_summary.json: " + out_path);
    }
    ofs << j.dump(2) << "\n";
}

}  // namespace ifog
