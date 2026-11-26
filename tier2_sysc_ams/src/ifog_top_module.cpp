#include "ifog_top_module.hpp"

#include "ifog_config.hpp"

namespace ifog {

namespace {

ExternalDriveState make_initial_drive(const IfogConfig& cfg) {
    ExternalDriveState st{};
    st.use_external_omega = true;
    st.omega_in_rad_per_s = cfg.omega_const_rad_per_s;
    st.use_external_shupe = true;
    st.shupe_phase_rad = 0.0;
    st.use_live_params = true;
    st.eps_vpi_live = cfg.eps_vpi;
    st.k_xtalk_live_A_per_V = cfg.k_xtalk_A_per_V;
    st.enable_dither_live = cfg.en_prbs_dither;
    return st;
}

}  // namespace

IfogTopModule::IfogTopModule(sc_core::sc_module_name name, const IfogConfig& cfg)
    : sc_core::sc_module(name),
      omega_in("omega_in"),
      shupe_phase_in("shupe_phase_in"),
      eps_vpi_in("eps_vpi_in"),
      k_xtalk_in("k_xtalk_in"),
      enable_dither_in("enable_dither_in"),
      omega_out("omega_out"),
      omega_out_avg("omega_out_avg"),
      e_vpi_res_out("e_vpi_res_out"),
      bit_status_out("bit_status_out"),
      cfg_(cfg),
      ext_drive_(make_initial_drive(cfg)),
      sig_p_det_("sig_p_det"),
      sig_v_adc_("sig_v_adc"),
      sig_v_drv_("sig_v_drv"),
      sig_dv_drv_dt_("sig_dv_drv_dt"),
      sig_pink_tia_("sig_pink_tia"),
      sig_pink_dac_("sig_pink_dac"),
      sig_pink_xtalk_("sig_pink_xtalk"),
      sig_p_scale_("sig_p_scale"),
      sig_rail_fast_("sig_rail_fast"),
      sig_rail_tau_("sig_rail_tau"),
      sig_adc_code_("sig_adc_code"),
      sig_dac_code_("sig_dac_code"),
      dsp_("DigitalDSP_SC", cfg_, "", nullptr, nullptr, &ext_drive_),
      bus_("NominalBus_TDF", cfg_),
      pink_("PinkNoise_TDF", cfg_),
      opt_("OpticalEnvelope_TDF", cfg_, dsp_.init_v_drv(), nullptr, &ext_drive_),
      afe_("AnalogFrontEnd_TDF", cfg_, nullptr, &ext_drive_),
      adc_("ADC_Bridge_TDF", cfg_, nullptr),
      dac_("DAC_Driver_TDF", cfg_, dsp_.init_dac_code(), dsp_.init_v_drv()) {
    validate_ifog_config(cfg_);
    sig_dac_code_.write(dsp_.init_dac_code());

    bus_.p_scale_out(sig_p_scale_);
    bus_.rail_droop_fast_out(sig_rail_fast_);
    bus_.rail_droop_tau_out(sig_rail_tau_);

    pink_.pink_tia_out(sig_pink_tia_);
    pink_.pink_dac_out(sig_pink_dac_);
    pink_.pink_xtalk_out(sig_pink_xtalk_);

    dac_.dac_code_in(sig_dac_code_);
    dac_.pink_dac_in(sig_pink_dac_);
    dac_.rail_droop_in(sig_rail_tau_);
    dac_.v_drv_out(sig_v_drv_);
    dac_.dv_drv_dt_out(sig_dv_drv_dt_);

    opt_.v_drv_in(sig_v_drv_);
    opt_.p_scale_in(sig_p_scale_);
    opt_.p_det_out(sig_p_det_);

    afe_.p_det_in(sig_p_det_);
    afe_.v_drv_in(sig_v_drv_);
    afe_.dv_drv_dt_in(sig_dv_drv_dt_);
    afe_.pink_tia_in(sig_pink_tia_);
    afe_.pink_xtalk_in(sig_pink_xtalk_);
    afe_.rail_droop_in(sig_rail_fast_);
    afe_.v_adc_out(sig_v_adc_);

    adc_.v_adc_in(sig_v_adc_);
    adc_.adc_code_out(sig_adc_code_);

    dsp_.adc_code_in(sig_adc_code_);
    dsp_.dac_code_out(sig_dac_code_);

    SC_METHOD(on_inputs_changed);
    sensitive << omega_in << shupe_phase_in << eps_vpi_in << k_xtalk_in << enable_dither_in;
    dont_initialize();
}

void IfogTopModule::on_inputs_changed() {
    ext_drive_.omega_in_rad_per_s = omega_in.read();
    ext_drive_.shupe_phase_rad = shupe_phase_in.read();
    ext_drive_.eps_vpi_live = eps_vpi_in.read();
    ext_drive_.k_xtalk_live_A_per_V = k_xtalk_in.read();
    ext_drive_.enable_dither_live = enable_dither_in.read();
}

void IfogTopModule::prepare_macro_step(
    double omega_rad_s,
    double shupe_rad,
    double eps_vpi,
    double k_xtalk_A_V,
    bool enable_dither
) {
    ext_drive_.omega_in_rad_per_s = omega_rad_s;
    ext_drive_.shupe_phase_rad = shupe_rad;
    ext_drive_.eps_vpi_live = eps_vpi;
    ext_drive_.k_xtalk_live_A_per_V = k_xtalk_A_V;
    ext_drive_.enable_dither_live = enable_dither;
    dsp_.reset_step_accumulator();
}

FmiOutputSnapshot IfogTopModule::sample_outputs() {
    FmiOutputSnapshot snap{};
    snap.omega_out_rad_per_s = dsp_.final_omega_out();
    snap.omega_out_avg_rad_per_s = dsp_.step_mean_omega_out();

    // EQ-43: Residual 2*pi flyback V_pi phase error [rad]
    const double g_ratio = dsp_.final_g_dac() * (cfg_.V_ref_dac_V / (2.0 * cfg_.V_pi_0_V));
    const double eps_eff = cfg_.ablation.en_mioc_vpi_err
        ? ((1.0 + ext_drive_.eps_vpi_live) * g_ratio - 1.0)
        : 0.0;
    snap.e_vpi_res_rad = TWO_PI * eps_eff;

    // EQ-43: Real-time FPGA BIT/FDIR & saturation bitmask (post-blanking BIT faults + anti-windup)
    uint32_t mask = 0u;
    const uint16_t fc = (dsp_.current_bit_fault_code() != BIT_OK)
        ? dsp_.current_bit_fault_code()
        : dsp_.bit_first_fault_code();
    if (fc >= BIT_SLD_DROP && fc <= BIT_DSP_SEU) {
        mask |= (1u << (fc - 1u));
    }
    if (dsp_.anti_windup_count() > 0u) {
        mask |= BIT_MASK_ANTI_WINDUP;
    }
    snap.bit_status = mask;

    omega_out.write(snap.omega_out_rad_per_s);
    omega_out_avg.write(snap.omega_out_avg_rad_per_s);
    e_vpi_res_out.write(snap.e_vpi_res_rad);
    bit_status_out.write(snap.bit_status);
    return snap;
}

}  // namespace ifog
