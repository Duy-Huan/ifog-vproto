#include "sim_runner.hpp"

#include <filesystem>
#include <stdexcept>
#include <systemc-ams.h>
#include <systemc.h>
#include "adc_dac_bridge.hpp"
#include "analog_frontend_tdf.hpp"
#include "digital_dsp_sc.hpp"
#include "ifog_config.hpp"
#include "ifog_math.hpp"
#include "imu_3axis.hpp"
#include "micro_trace.hpp"
#include "optical_envelope_tdf.hpp"
#include "pink_noise_tdf.hpp"

namespace ifog {

CliArgs parse_cli_args(int argc, char* argv[]) {
    CliArgs args;
    for (int i = 1; i < argc; ++i) {
        const std::string opt(argv[i]);
        auto require_val = [&](const std::string& flag) -> std::string {
            if (i + 1 >= argc) {
                throw std::invalid_argument("Missing value for argument: " + flag);
            }
            return std::string(argv[++i]);
        };
        if (opt == "--phys") {
            args.phys_path = require_val(opt);
        } else if (opt == "--cfg") {
            args.cfg_path = require_val(opt);
        } else if (opt == "--out") {
            args.out_dir = require_val(opt);
        } else if (opt == "--shupe") {
            args.shupe_path = require_val(opt);
        } else if (opt == "--duration-s") {
            args.override_duration_s = std::stod(require_val(opt));
        } else if (opt == "--dump-micro-ms") {
            args.override_dump_micro_ms = std::stod(require_val(opt));
        } else if (opt == "--imu3axis") {
            args.imu_3axis = true;
        } else {
            throw std::invalid_argument("Unknown CLI argument: " + opt);
        }
    }
    if (args.phys_path.empty() || args.cfg_path.empty() || args.out_dir.empty()) {
        throw std::invalid_argument(
            "Usage: ifog_sim --phys <phys_params.json> --cfg <config.json> --out <out_dir> "
            "[--shupe <shupe_lut.bin>] [--duration-s <sec>] [--dump-micro-ms <ms>] [--imu3axis]"
        );
    }
    return args;
}

SimSummary run_ifog_simulation(const IfogConfig& cfg, const std::string& out_dir) {
    validate_ifog_config(cfg);
    namespace fs = std::filesystem;
    fs::create_directories(out_dir);

    const std::string bin_out = (fs::path(out_dir) / "sim_out.bin").string();
    const std::string micro_out = (fs::path(out_dir) / "micro_waveforms.bin").string();
    const std::string dsp_trace_out = (fs::path(out_dir) / "dsp_trace.bin").string();
    const std::string summary_out = (fs::path(out_dir) / "sim_summary.json").string();

    MicroTraceCollector micro_trace(micro_out, cfg.dump_micro_ms * 1.0e-3, cfg.K_oversample);
    DspTraceCollector dsp_trace(dsp_trace_out, cfg.dump_dsp_trace);

    // TDF signals
    sca_tdf::sca_signal<double> sig_p_det("sig_p_det");
    sca_tdf::sca_signal<double> sig_v_adc("sig_v_adc");
    sca_tdf::sca_signal<double> sig_v_drv("sig_v_drv");
    sca_tdf::sca_signal<double> sig_dv_drv_dt("sig_dv_drv_dt");
    sca_tdf::sca_signal<double> sig_pink_tia("sig_pink_tia");
    sca_tdf::sca_signal<double> sig_pink_dac("sig_pink_dac");
    sca_tdf::sca_signal<double> sig_pink_xtalk("sig_pink_xtalk");
    sca_tdf::sca_signal<double> sig_p_scale("sig_p_scale");
    sca_tdf::sca_signal<double> sig_rail_fast("sig_rail_fast");
    sca_tdf::sca_signal<double> sig_rail_tau("sig_rail_tau");

    // DE boundary channels (sc_buffer guarantees notification on every tau write even if value repeats)
    sc_core::sc_buffer<double> sig_adc_code("sig_adc_code");
    sc_core::sc_buffer<double> sig_dac_code("sig_dac_code");

    // Instantiate modules per IFOG-SIM-SPEC-004/005 Figure 2
    DigitalDSP_SC dsp("DigitalDSP_SC", cfg, bin_out, &micro_trace, &dsp_trace);
    const double init_dac = dsp.init_dac_code();
    const double init_v = dsp.init_v_drv();
    sig_dac_code.write(init_dac);

    NominalBus_TDF bus("NominalBus_TDF", cfg);
    PinkNoise_TDF pink("PinkNoise_TDF", cfg);
    OpticalEnvelope_TDF opt("OpticalEnvelope_TDF", cfg, init_v, &micro_trace);
    AnalogFrontEnd_TDF afe("AnalogFrontEnd_TDF", cfg, &micro_trace);
    ADC_Bridge_TDF adc("ADC_Bridge_TDF", cfg, &micro_trace);
    DAC_Driver_TDF dac("DAC_Driver_TDF", cfg, init_dac, init_v);

    // Wire topology
    bus.p_scale_out(sig_p_scale);
    bus.rail_droop_fast_out(sig_rail_fast);
    bus.rail_droop_tau_out(sig_rail_tau);

    pink.pink_tia_out(sig_pink_tia);
    pink.pink_dac_out(sig_pink_dac);
    pink.pink_xtalk_out(sig_pink_xtalk);

    dac.dac_code_in(sig_dac_code);
    dac.pink_dac_in(sig_pink_dac);
    dac.rail_droop_in(sig_rail_tau);
    dac.v_drv_out(sig_v_drv);
    dac.dv_drv_dt_out(sig_dv_drv_dt);

    opt.v_drv_in(sig_v_drv);
    opt.p_scale_in(sig_p_scale);
    opt.p_det_out(sig_p_det);

    afe.p_det_in(sig_p_det);
    afe.v_drv_in(sig_v_drv);
    afe.dv_drv_dt_in(sig_dv_drv_dt);
    afe.pink_tia_in(sig_pink_tia);
    afe.pink_xtalk_in(sig_pink_xtalk);
    afe.rail_droop_in(sig_rail_fast);
    afe.v_adc_out(sig_v_adc);

    adc.v_adc_in(sig_v_adc);
    adc.adc_code_out(sig_adc_code);

    dsp.adc_code_in(sig_adc_code);
    dsp.dac_code_out(sig_dac_code);

    // Run IEEE 1666.1 SystemC-AMS simulation
    sc_core::sc_start(cfg.duration_s, sc_core::SC_SEC);
    dsp.flush_records();

    const double omega0 = compute_tia_omega0(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F, cfg.C_f_F);
    const double zeta = compute_tia_zeta(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F, cfg.C_f_F);
    const double cf_opt = compute_tia_cf_opt(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F);
    const double ts = compute_tia_ts_0p1pct(zeta, omega0);
    const double eps_eff = cfg.ablation.en_mioc_vpi_err
        ? ((1.0 + cfg.eps_vpi) * (dsp.final_g_dac() * (cfg.V_ref_dac_V / (2.0 * cfg.V_pi_0_V))) - 1.0)
        : 0.0;

    SimSummary summary{};
    summary.total_tau_steps = dsp.total_tau_steps();
    summary.total_records_written = dsp.total_records_written();
    summary.total_micro_records = micro_trace.records_written();
    summary.total_dsp_trace_records = dsp_trace.records_written();
    summary.flyback_count = dsp.flyback_count();
    summary.adc_clip_count = afe.clip_count();
    summary.anti_windup_count = dsp.anti_windup_count();
    summary.final_omega_out_rad_per_s = dsp.final_omega_out();
    summary.final_delta_phi_step_rad = dsp.final_delta_phi_step();
    summary.final_g_dac = dsp.final_g_dac();
    summary.final_eps_vpi_eff = eps_eff;
    summary.mean_omega_out_second_half_rad_per_s = dsp.mean_omega_second_half();
    summary.tia_omega0_rad_per_s = omega0;
    summary.tia_zeta = zeta;
    summary.tia_cf_opt_F = cf_opt;
    summary.tia_ts_0p1pct_s = ts;
    summary.eta_blanking = adc.eta_blanking();
    summary.S_alpha_counts_per_rad = dsp.S_alpha();
    summary.bit_first_fault_code = dsp.bit_first_fault_code();
    summary.bit_alert_time_s = dsp.bit_alert_time_s();
    summary.bit_time_to_alert_s = dsp.bit_time_to_alert_s();
    summary.fdir_recovered = dsp.fdir_recovered();
    summary.e_asym_rms = dsp.e_asym_rms();

    write_sim_summary_json(summary_out, summary);
    return summary;
}

}  // namespace ifog
