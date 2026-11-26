#ifndef IFOG_TOP_MODULE_HPP
#define IFOG_TOP_MODULE_HPP

#include <cstdint>
#include <systemc-ams.h>
#include <systemc.h>
#include "adc_dac_bridge.hpp"
#include "analog_frontend_tdf.hpp"
#include "digital_dsp_sc.hpp"
#include "ifog_types.hpp"
#include "imu_3axis.hpp"
#include "optical_envelope_tdf.hpp"
#include "pink_noise_tdf.hpp"

namespace ifog {

struct FmiOutputSnapshot {
    double omega_out_rad_per_s = 0.0;
    double omega_out_avg_rad_per_s = 0.0;
    double e_vpi_res_rad = 0.0;
    uint32_t bit_status = 0u;
};

// Top-level SystemC/SystemC-AMS closed-loop IFOG module for FMI 3.0 Co-Simulation (IFOG-SIM-SPEC-006).
// Wraps the exact Tier 2 TDF/DE physics topology without altering any physical or DSP equations.
SC_MODULE(IfogTopModule) {
public:
    // FMI 3.0 input & tunable parameter ports (bound to sc_signal channels by fmi3_bridge)
    sc_core::sc_in<double> omega_in;
    sc_core::sc_in<double> shupe_phase_in;
    sc_core::sc_in<double> eps_vpi_in;
    sc_core::sc_in<double> k_xtalk_in;
    sc_core::sc_in<bool> enable_dither_in;

    // FMI 3.0 output ports (bound to sc_signal channels by fmi3_bridge)
    sc_core::sc_out<double> omega_out;
    sc_core::sc_out<double> omega_out_avg;
    sc_core::sc_out<double> e_vpi_res_out;
    sc_core::sc_out<uint32_t> bit_status_out;

    SC_HAS_PROCESS(IfogTopModule);

    IfogTopModule(sc_core::sc_module_name name, const IfogConfig& cfg);

    // Synchronize external ZOH inputs & reset per-macro-step anti-aliased accumulator before sc_start()
    void prepare_macro_step(
        double omega_rad_s,
        double shupe_rad,
        double eps_vpi,
        double k_xtalk_A_V,
        bool enable_dither
    );

    // Apply SPEC-007 FMI 3.0 tunable physical & calibration parameters (VR 15..21)
    void set_spec007_tunable_params(
        bool enable_live,
        double C_xtalk_F,
        double G_xtalk_S,
        double c_pink_coeff,
        double R_facet_dB,
        double alpha_vpi_ppm_K,
        double alpha_bobbin_ppm_K,
        double delta_z_quad_m
    );

    // Sample & publish closed-loop outputs after sc_start() (EQ-42, EQ-43)
    FmiOutputSnapshot sample_outputs();

    uint64_t total_tau_steps() const { return dsp_.total_tau_steps(); }

private:
    void on_inputs_changed();

    IfogConfig cfg_;
    ExternalDriveState ext_drive_;

    // Internal TDF signals matching sim_runner.cpp topology identically
    sca_tdf::sca_signal<double> sig_p_det_;
    sca_tdf::sca_signal<double> sig_v_adc_;
    sca_tdf::sca_signal<double> sig_v_drv_;
    sca_tdf::sca_signal<double> sig_dv_drv_dt_;
    sca_tdf::sca_signal<double> sig_pink_tia_;
    sca_tdf::sca_signal<double> sig_pink_dac_;
    sca_tdf::sca_signal<double> sig_pink_xtalk_;
    sca_tdf::sca_signal<double> sig_p_scale_;
    sca_tdf::sca_signal<double> sig_rail_fast_;
    sca_tdf::sca_signal<double> sig_rail_tau_;

    // DE boundary channels (sc_buffer guarantees unconditional per-tau notification)
    sc_core::sc_buffer<double> sig_adc_code_;
    sc_core::sc_buffer<double> sig_dac_code_;

    // Exact Tier 2 closed-loop submodules
    DigitalDSP_SC dsp_;
    NominalBus_TDF bus_;
    PinkNoise_TDF pink_;
    OpticalEnvelope_TDF opt_;
    AnalogFrontEnd_TDF afe_;
    ADC_Bridge_TDF adc_;
    DAC_Driver_TDF dac_;
};

}  // namespace ifog

#endif  // IFOG_TOP_MODULE_HPP
