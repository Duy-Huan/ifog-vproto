#ifndef DIGITAL_DSP_SC_HPP
#define DIGITAL_DSP_SC_HPP

#include <array>
#include <cstdint>
#include <fstream>
#include <string>
#include <systemc.h>
#include <vector>
#include "ifog_math.hpp"
#include "ifog_types.hpp"
#include "micro_trace.hpp"

namespace ifog {

// DigitalDSP_SC: SystemC Discrete-Event (DE) bit-true closed-loop demodulator & ramp controller.
// Implements 2-state, 4-state (EQ-01..EQ-03, EQ-20..EQ-23), and official 6-state symmetric
// demodulation (EQ-31..EQ-34), Loop-1 Sagnac integrator with anti-windup + 2*pi flyback ramp,
// Loop-2 V_pi tracking, PRBS LFSR dither, real-time FPGA BIT/FDIR monitor (EQ-39),
// buffered 32-byte SimRecord logging, and optional 64-byte DspTraceRecord logging.
SC_MODULE(DigitalDSP_SC) {
public:
    sc_core::sc_in<double> adc_code_in;
    sc_core::sc_out<double> dac_code_out;

    SC_HAS_PROCESS(DigitalDSP_SC);

    DigitalDSP_SC(
        sc_core::sc_module_name name,
        const IfogConfig& cfg,
        const std::string& bin_out_path,
        MicroTraceCollector* micro_trace = nullptr,
        DspTraceCollector* dsp_trace = nullptr,
        const ExternalDriveState* ext_drive = nullptr
    );

    ~DigitalDSP_SC() override;

    void on_adc_sample();
    void flush_records();
    void reset_step_accumulator();

    double init_dac_code() const { return init_dac_code_; }
    double init_v_drv() const { return init_v_drv_; }

    uint64_t total_tau_steps() const { return step_idx_; }
    uint64_t total_records_written() const { return records_written_; }
    uint64_t flyback_count() const { return flyback_count_; }
    uint64_t anti_windup_count() const { return anti_windup_count_; }
    double final_omega_out() const { return omega_out_; }
    double step_mean_omega_out() const;
    double final_delta_phi_step() const { return delta_phi_step_; }
    double final_g_dac() const { return g_dac_; }
    double mean_omega_second_half() const;
    double S_alpha() const { return s_alpha_; }
    uint16_t current_bit_fault_code() const { return last_bit_fault_code_; }
    uint16_t bit_first_fault_code() const { return bit_first_fault_code_; }
    double bit_alert_time_s() const { return bit_alert_time_s_; }
    double bit_time_to_alert_s() const { return bit_time_to_alert_s_; }
    bool fdir_recovered() const { return fdir_recovered_; }
    double e_asym_rms() const;

private:
    struct PipeTag {
        bool valid;
        int state_idx;
        double dither_step;
    };

    double bias_phase_for_state(int state_idx) const;
    double encode_dac_phase(double phi_total) const;
    bool apply_loop1_update(double e_omega);
    void record_bit_fault(uint16_t code, double t_now);
    void evaluate_frame_bit(
        double t_now,
        double y_mean,
        double y_min,
        double y_max,
        double e_omega,
        double e_vpi
    );

    IfogConfig cfg_;
    double s_alpha_;
    double k_i1_;
    double k_p1_;
    double k_i2_;
    double g_dac_nom_;
    double g_dac_;
    double init_dac_code_;
    double init_v_drv_;
    double y_nom_;
    double adc_code_max_;

    // Loop-1 & Loop-2 state
    double delta_phi_step_;
    double filtered_dphi_step_;
    double prev_e_omega_;
    double phi_ramp_;
    double phi_dither_;
    double active_dither_step_;
    int16_t active_prbs_bit_;
    double omega_out_;
    double last_e_omega_;
    double last_e_asym_;
    int32_t last_e_vpi_raw_;

    // 2/4/6-state buffers & 2-slot pipeline alignment FIFO (matches set_delay(1) + DE boundary)
    static constexpr int PIPE_DEPTH = 2;
    std::array<PipeTag, PIPE_DEPTH> pipe_;
    int pipe_head_;
    int emit_state_;
    std::array<double, 6> y_frame_;
    double prev_y_2state_;
    bool has_prev_y_2state_;
    int two_state_rx_count_;

    PrbsLfsr32 lfsr_;

    // BIT/FDIR & SEU state (EQ-39)
    bool seu_injected_;
    uint16_t last_bit_fault_code_;
    uint16_t bit_first_fault_code_;
    double bit_alert_time_s_;
    double bit_time_to_alert_s_;
    bool fdir_recovery_active_;
    int fdir_calm_frames_;
    bool fdir_recovered_;

    // Telemetry & buffered binary logger (4096 x 32-byte SimRecord)
    std::ofstream bin_ofs_;
    std::vector<SimRecord> record_buf_;
    uint64_t step_idx_;
    uint64_t total_expected_steps_;
    uint64_t records_written_;
    uint64_t flyback_count_;
    uint64_t anti_windup_count_;
    double second_half_sum_;
    uint64_t second_half_count_;
    double e_asym_sq_sum_;
    uint64_t e_asym_count_;
    double step_omega_sum_;
    uint64_t step_omega_count_;
    MicroTraceCollector* micro_trace_;
    DspTraceCollector* dsp_trace_;
    const ExternalDriveState* ext_drive_;
};

}  // namespace ifog

#endif  // DIGITAL_DSP_SC_HPP
