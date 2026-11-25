#include "imu_3axis.hpp"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <memory>
#include <nlohmann/json.hpp>
#include <stdexcept>
#include <systemc.h>
#include "adc_dac_bridge.hpp"
#include "analog_frontend_tdf.hpp"
#include "digital_dsp_sc.hpp"
#include "ifog_config.hpp"
#include "ifog_math.hpp"
#include "optical_envelope_tdf.hpp"
#include "pink_noise_tdf.hpp"

namespace ifog {

NominalBus_TDF::NominalBus_TDF(sc_core::sc_module_name name, const IfogConfig& cfg)
    : sca_tdf::sca_module(name),
      p_scale_out("p_scale_out"),
      rail_droop_fast_out("rail_droop_fast_out"),
      rail_droop_tau_out("rail_droop_tau_out"),
      cfg_(cfg) {}

void NominalBus_TDF::set_attributes() {
    p_scale_out.set_rate(cfg_.K_oversample);
    rail_droop_fast_out.set_rate(cfg_.K_oversample);
    rail_droop_tau_out.set_rate(1);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void NominalBus_TDF::processing() {
    for (int k = 0; k < cfg_.K_oversample; ++k) {
        p_scale_out.write(1.0, k);
        rail_droop_fast_out.write(0.0, k);
    }
    rail_droop_tau_out.write(0.0);
}

SharedPowerBus_TDF::SharedPowerBus_TDF(sc_core::sc_module_name name, const IfogConfig& cfg)
    : sca_tdf::sca_module(name),
      v_drv_x_in("v_drv_x_in"),
      dv_dt_x_in("dv_dt_x_in"),
      v_drv_y_in("v_drv_y_in"),
      dv_dt_y_in("dv_dt_y_in"),
      v_drv_z_in("v_drv_z_in"),
      dv_dt_z_in("dv_dt_z_in"),
      p_scale_x_out("p_scale_x_out"),
      p_scale_y_out("p_scale_y_out"),
      p_scale_z_out("p_scale_z_out"),
      rail_droop_fast_out("rail_droop_fast_out"),
      rail_droop_tau_out("rail_droop_tau_out"),
      cfg_(cfg),
      inv_v_pi_(1.0 / cfg.V_pi_0_V),
      inv_r_load_(1.0 / cfg.imu_r_load_ohm),
      peak_rail_droop_V_(0.0) {}

void SharedPowerBus_TDF::set_attributes() {
    const int K = cfg_.K_oversample;
    v_drv_x_in.set_rate(K);
    dv_dt_x_in.set_rate(K);
    v_drv_y_in.set_rate(K);
    dv_dt_y_in.set_rate(K);
    v_drv_z_in.set_rate(K);
    dv_dt_z_in.set_rate(K);
    p_scale_x_out.set_rate(K);
    p_scale_y_out.set_rate(K);
    p_scale_z_out.set_rate(K);
    rail_droop_fast_out.set_rate(K);
    rail_droop_tau_out.set_rate(1);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void SharedPowerBus_TDF::processing() {
    const int K = cfg_.K_oversample;
    const double rho = cfg_.imu_rho_opt_coupling;
    const double z_rail = cfg_.imu_z_rail_ohm;
    const double c_load = cfg_.imu_c_load_F;
    double droop_sum = 0.0;

    for (int k = 0; k < K; ++k) {
        const double vx = v_drv_x_in.read(k);
        const double vy = v_drv_y_in.read(k);
        const double vz = v_drv_z_in.read(k);
        const double dvx = dv_dt_x_in.read(k);
        const double dvy = dv_dt_y_in.read(k);
        const double dvz = dv_dt_z_in.read(k);

        // EQ-36: Shared SLD optical splitter back-reflection coupling
        const double px = std::max(0.1, 1.0 + rho * (vy + vz) * inv_v_pi_);
        const double py = std::max(0.1, 1.0 + rho * (vx + vz) * inv_v_pi_);
        const double pz = std::max(0.1, 1.0 + rho * (vx + vy) * inv_v_pi_);
        p_scale_x_out.write(px, k);
        p_scale_y_out.write(py, k);
        p_scale_z_out.write(pz, k);

        // EQ-36: Shared FPGA/DAC analog rail droop from 3-axis simultaneous driver currents
        const double i_bus = (std::fabs(vx) + std::fabs(vy) + std::fabs(vz)) * inv_r_load_
            + c_load * (std::fabs(dvx) + std::fabs(dvy) + std::fabs(dvz));
        const double droop = -z_rail * i_bus;
        peak_rail_droop_V_ = std::max(peak_rail_droop_V_, std::fabs(droop));
        droop_sum += droop;
        rail_droop_fast_out.write(droop, k);
    }
    rail_droop_tau_out.write(droop_sum / static_cast<double>(K));
}

namespace {

struct AxisRig {
    IfogConfig cfg;
    sca_tdf::sca_signal<double> sig_p_det;
    sca_tdf::sca_signal<double> sig_v_adc;
    sca_tdf::sca_signal<double> sig_v_drv;
    sca_tdf::sca_signal<double> sig_dv_drv_dt;
    sca_tdf::sca_signal<double> sig_pink_tia;
    sca_tdf::sca_signal<double> sig_pink_dac;
    sca_tdf::sca_signal<double> sig_pink_xtalk;
    sca_tdf::sca_signal<double> sig_p_scale;
    sc_core::sc_buffer<double> sig_adc_code;
    sc_core::sc_buffer<double> sig_dac_code;

    std::unique_ptr<DigitalDSP_SC> dsp;
    std::unique_ptr<PinkNoise_TDF> pink;
    std::unique_ptr<OpticalEnvelope_TDF> opt;
    std::unique_ptr<AnalogFrontEnd_TDF> afe;
    std::unique_ptr<ADC_Bridge_TDF> adc;
    std::unique_ptr<DAC_Driver_TDF> dac;

    AxisRig(
        const std::string& tag,
        const IfogConfig& axis_cfg,
        const std::string& bin_path,
        sca_tdf::sca_signal<double>& shared_rail_fast,
        sca_tdf::sca_signal<double>& shared_rail_tau
    )
        : cfg(axis_cfg),
          sig_p_det((tag + "_p_det").c_str()),
          sig_v_adc((tag + "_v_adc").c_str()),
          sig_v_drv((tag + "_v_drv").c_str()),
          sig_dv_drv_dt((tag + "_dv_dt").c_str()),
          sig_pink_tia((tag + "_pink_tia").c_str()),
          sig_pink_dac((tag + "_pink_dac").c_str()),
          sig_pink_xtalk((tag + "_pink_xtalk").c_str()),
          sig_p_scale((tag + "_p_scale").c_str()),
          sig_adc_code((tag + "_adc_code").c_str()),
          sig_dac_code((tag + "_dac_code").c_str()) {
        dsp = std::make_unique<DigitalDSP_SC>((tag + "_dsp").c_str(), cfg, bin_path, nullptr, nullptr);
        const double init_dac = dsp->init_dac_code();
        const double init_v = dsp->init_v_drv();
        sig_dac_code.write(init_dac);

        pink = std::make_unique<PinkNoise_TDF>((tag + "_pink").c_str(), cfg);
        opt = std::make_unique<OpticalEnvelope_TDF>((tag + "_opt").c_str(), cfg, init_v, nullptr);
        afe = std::make_unique<AnalogFrontEnd_TDF>((tag + "_afe").c_str(), cfg, nullptr);
        adc = std::make_unique<ADC_Bridge_TDF>((tag + "_adc").c_str(), cfg, nullptr);
        dac = std::make_unique<DAC_Driver_TDF>((tag + "_dac").c_str(), cfg, init_dac, init_v);

        pink->pink_tia_out(sig_pink_tia);
        pink->pink_dac_out(sig_pink_dac);
        pink->pink_xtalk_out(sig_pink_xtalk);

        dac->dac_code_in(sig_dac_code);
        dac->pink_dac_in(sig_pink_dac);
        dac->rail_droop_in(shared_rail_tau);
        dac->v_drv_out(sig_v_drv);
        dac->dv_drv_dt_out(sig_dv_drv_dt);

        opt->v_drv_in(sig_v_drv);
        opt->p_scale_in(sig_p_scale);
        opt->p_det_out(sig_p_det);

        afe->p_det_in(sig_p_det);
        afe->v_drv_in(sig_v_drv);
        afe->dv_drv_dt_in(sig_dv_drv_dt);
        afe->pink_tia_in(sig_pink_tia);
        afe->pink_xtalk_in(sig_pink_xtalk);
        afe->rail_droop_in(shared_rail_fast);
        afe->v_adc_out(sig_v_adc);

        adc->v_adc_in(sig_v_adc);
        adc->adc_code_out(sig_adc_code);

        dsp->adc_code_in(sig_adc_code);
        dsp->dac_code_out(sig_dac_code);
    }

    SimSummary build_summary() const {
        const double omega0 = compute_tia_omega0(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F, cfg.C_f_F);
        const double zeta = compute_tia_zeta(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F, cfg.C_f_F);
        const double cf_opt = compute_tia_cf_opt(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F);
        const double ts = compute_tia_ts_0p1pct(zeta, omega0);
        const double eps_eff = cfg.ablation.en_mioc_vpi_err
            ? ((1.0 + cfg.eps_vpi) * (dsp->final_g_dac() * (cfg.V_ref_dac_V / (2.0 * cfg.V_pi_0_V))) - 1.0)
            : 0.0;

        SimSummary s{};
        s.total_tau_steps = dsp->total_tau_steps();
        s.total_records_written = dsp->total_records_written();
        s.flyback_count = dsp->flyback_count();
        s.adc_clip_count = afe->clip_count();
        s.anti_windup_count = dsp->anti_windup_count();
        s.final_omega_out_rad_per_s = dsp->final_omega_out();
        s.final_delta_phi_step_rad = dsp->final_delta_phi_step();
        s.final_g_dac = dsp->final_g_dac();
        s.final_eps_vpi_eff = eps_eff;
        s.mean_omega_out_second_half_rad_per_s = dsp->mean_omega_second_half();
        s.tia_omega0_rad_per_s = omega0;
        s.tia_zeta = zeta;
        s.tia_cf_opt_F = cf_opt;
        s.tia_ts_0p1pct_s = ts;
        s.eta_blanking = adc->eta_blanking();
        s.S_alpha_counts_per_rad = dsp->S_alpha();
        s.e_asym_rms = dsp->e_asym_rms();
        return s;
    }
};

}  // namespace

Imu3AxisSummary run_ifog_imu3axis_simulation(const IfogConfig& base_cfg, const std::string& out_dir) {
    validate_ifog_config(base_cfg);
    namespace fs = std::filesystem;
    fs::create_directories(out_dir);
    fs::create_directories(fs::path(out_dir) / "axis_x");
    fs::create_directories(fs::path(out_dir) / "axis_y");
    fs::create_directories(fs::path(out_dir) / "axis_z");

    // Configure Axis X (smooth ramp-hold to imu_omega_x so loop locks without fringe slip), Y, Z
    IfogConfig cfg_x = base_cfg;
    cfg_x.stimulus_type = StimulusType::Ramp;
    cfg_x.omega_start_rad_per_s = 0.0;
    cfg_x.omega_end_rad_per_s = base_cfg.imu_omega_x_rad_per_s;
    cfg_x.step_time_s = std::min(0.015, 0.3 * base_cfg.duration_s);

    IfogConfig cfg_y = base_cfg;
    cfg_y.seed = base_cfg.seed + 101ULL;
    cfg_y.stimulus_type = StimulusType::Constant;
    cfg_y.omega_const_rad_per_s = base_cfg.imu_omega_y_rad_per_s;

    IfogConfig cfg_z = base_cfg;
    cfg_z.seed = base_cfg.seed + 202ULL;
    cfg_z.stimulus_type = StimulusType::Constant;
    cfg_z.omega_const_rad_per_s = base_cfg.imu_omega_z_rad_per_s;

    sca_tdf::sca_signal<double> sig_rail_fast("imu_rail_fast");
    sca_tdf::sca_signal<double> sig_rail_tau("imu_rail_tau");

    AxisRig rig_x("axis_x", cfg_x, (fs::path(out_dir) / "axis_x" / "sim_out.bin").string(), sig_rail_fast, sig_rail_tau);
    AxisRig rig_y("axis_y", cfg_y, (fs::path(out_dir) / "axis_y" / "sim_out.bin").string(), sig_rail_fast, sig_rail_tau);
    AxisRig rig_z("axis_z", cfg_z, (fs::path(out_dir) / "axis_z" / "sim_out.bin").string(), sig_rail_fast, sig_rail_tau);

    SharedPowerBus_TDF bus("SharedPowerBus_TDF", base_cfg);
    bus.v_drv_x_in(rig_x.sig_v_drv);
    bus.dv_dt_x_in(rig_x.sig_dv_drv_dt);
    bus.v_drv_y_in(rig_y.sig_v_drv);
    bus.dv_dt_y_in(rig_y.sig_dv_drv_dt);
    bus.v_drv_z_in(rig_z.sig_v_drv);
    bus.dv_dt_z_in(rig_z.sig_dv_drv_dt);
    bus.p_scale_x_out(rig_x.sig_p_scale);
    bus.p_scale_y_out(rig_y.sig_p_scale);
    bus.p_scale_z_out(rig_z.sig_p_scale);
    bus.rail_droop_fast_out(sig_rail_fast);
    bus.rail_droop_tau_out(sig_rail_tau);

    // Concurrent IEEE 1666.1 3-axis SystemC-AMS simulation
    sc_core::sc_start(base_cfg.duration_s, sc_core::SC_SEC);
    rig_x.dsp->flush_records();
    rig_y.dsp->flush_records();
    rig_z.dsp->flush_records();

    Imu3AxisSummary summary{};
    summary.axis_x = rig_x.build_summary();
    summary.axis_y = rig_y.build_summary();
    summary.axis_z = rig_z.build_summary();
    summary.peak_rail_droop_V = bus.peak_rail_droop_V();
    summary.y_bias_err_deg_per_h =
        (summary.axis_y.mean_omega_out_second_half_rad_per_s - base_cfg.imu_omega_y_rad_per_s) * RAD_S_TO_DEG_H;
    summary.z_bias_err_deg_per_h =
        (summary.axis_z.mean_omega_out_second_half_rad_per_s - base_cfg.imu_omega_z_rad_per_s) * RAD_S_TO_DEG_H;

    write_sim_summary_json((fs::path(out_dir) / "axis_x" / "sim_summary.json").string(), summary.axis_x);
    write_sim_summary_json((fs::path(out_dir) / "axis_y" / "sim_summary.json").string(), summary.axis_y);
    write_sim_summary_json((fs::path(out_dir) / "axis_z" / "sim_summary.json").string(), summary.axis_z);
    write_imu_3axis_summary_json((fs::path(out_dir) / "imu_3axis_summary.json").string(), summary);
    return summary;
}

void write_imu_3axis_summary_json(const std::string& out_path, const Imu3AxisSummary& s) {
    nlohmann::json j = nlohmann::json::object();
    j["spec_id"] = "IFOG-SIM-SPEC-005";
    j["formula_id"] = "EQ-36";
    j["peak_rail_droop_V"] = s.peak_rail_droop_V;
    j["y_bias_err_deg_per_h"] = s.y_bias_err_deg_per_h;
    j["z_bias_err_deg_per_h"] = s.z_bias_err_deg_per_h;
    j["axis_x_flyback_count"] = s.axis_x.flyback_count;
    j["axis_x_mean_rate_deg_per_s"] = s.axis_x.mean_omega_out_second_half_rad_per_s * (180.0 / PI);
    j["axis_y_mean_rate_deg_per_h"] = s.axis_y.mean_omega_out_second_half_rad_per_s * RAD_S_TO_DEG_H;
    j["axis_z_mean_rate_deg_per_h"] = s.axis_z.mean_omega_out_second_half_rad_per_s * RAD_S_TO_DEG_H;
    std::ofstream ofs(out_path);
    if (!ofs.is_open()) {
        throw std::runtime_error("Cannot write imu_3axis_summary.json: " + out_path);
    }
    ofs << j.dump(2) << "\n";
}

}  // namespace ifog
