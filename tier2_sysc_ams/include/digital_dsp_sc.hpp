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

// DigitalDSP_SC: SystemC Discrete-Event (DE) bit-true closed-loop demodulator & ramp controller
// Implements 2-state and 4-state Lefevre demodulation (EQ-01, EQ-03, EQ-20..EQ-23),
// Loop-1 Sagnac integrator + 2*pi flyback ramp, Loop-2 V_pi tracking, PRBS LFSR dither,
// and buffered 32-byte binary SimRecord logging.
SC_MODULE(DigitalDSP_SC) {
public:
    sc_core::sc_in<double> adc_code_in;
    sc_core::sc_out<double> dac_code_out;

    SC_HAS_PROCESS(DigitalDSP_SC);

    DigitalDSP_SC(
        sc_core::sc_module_name name,
        const IfogConfig& cfg,
        const std::string& bin_out_path,
        MicroTraceCollector* micro_trace = nullptr
    );

    ~DigitalDSP_SC() override;

    void on_adc_sample();
    void flush_records();

    double init_dac_code() const { return init_dac_code_; }
    double init_v_drv() const { return init_v_drv_; }

    uint64_t total_tau_steps() const { return step_idx_; }
    uint64_t total_records_written() const { return records_written_; }
    uint64_t flyback_count() const { return flyback_count_; }
    double final_omega_out() const { return omega_out_; }
    double final_delta_phi_step() const { return delta_phi_step_; }
    double final_g_dac() const { return g_dac_; }
    double mean_omega_second_half() const;
    double S_alpha() const { return s_alpha_; }

private:
    struct PipeTag {
        bool valid;
        int state_idx;
        double dither_step;
    };

    double bias_phase_for_state(int state_idx) const;
    double encode_dac_phase(double phi_total) const;

    IfogConfig cfg_;
    double s_alpha_;
    double k_i1_;
    double k_p1_;
    double k_i2_;
    double g_dac_nom_;
    double g_dac_;
    double init_dac_code_;
    double init_v_drv_;

    // Loop-1 & Loop-2 state
    double delta_phi_step_;
    double prev_e_omega_;
    double phi_ramp_;
    double phi_dither_;
    double active_dither_step_;
    double omega_out_;
    int32_t last_e_vpi_raw_;

    // 4-state / 2-state buffers & 2-slot pipeline alignment FIFO (matches set_delay(1) + DE boundary)
    static constexpr int PIPE_DEPTH = 2;
    std::array<PipeTag, PIPE_DEPTH> pipe_;
    int pipe_head_;
    int emit_state_;
    std::array<double, 4> y_frame_;
    double prev_y_2state_;
    bool has_prev_y_2state_;
    int two_state_rx_count_;

    PrbsLfsr32 lfsr_;

    // Binary logger (buffered 4096 x 32-byte SimRecord)
    std::ofstream bin_ofs_;
    std::vector<SimRecord> record_buf_;
    uint64_t step_idx_;
    uint64_t total_expected_steps_;
    uint64_t records_written_;
    uint64_t flyback_count_;
    double second_half_sum_;
    uint64_t second_half_count_;
    MicroTraceCollector* micro_trace_;
};

}  // namespace ifog

#endif  // DIGITAL_DSP_SC_HPP
