#include "digital_dsp_sc.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace ifog {

DigitalDSP_SC::DigitalDSP_SC(
    sc_core::sc_module_name name,
    const IfogConfig& cfg,
    const std::string& bin_out_path,
    MicroTraceCollector* micro_trace
)
    : sc_core::sc_module(name),
      adc_code_in("adc_code_in"),
      dac_code_out("dac_code_out"),
      cfg_(cfg),
      s_alpha_(compute_channel_sensitivity(cfg)),
      k_i1_(0.0),
      k_p1_(cfg.K_P_1),
      k_i2_(0.0),
      g_dac_nom_((2.0 * cfg.V_pi_0_V) / cfg.V_ref_dac_V),
      g_dac_(g_dac_nom_),
      init_dac_code_(0.0),
      init_v_drv_(0.0),
      delta_phi_step_(0.0),
      prev_e_omega_(0.0),
      phi_ramp_(0.0),
      phi_dither_(0.0),
      active_dither_step_(0.0),
      omega_out_(0.0),
      last_e_vpi_raw_(0),
      pipe_{},
      pipe_head_(0),
      emit_state_(0),
      y_frame_{0.0, 0.0, 0.0, 0.0},
      prev_y_2state_(0.0),
      has_prev_y_2state_(false),
      two_state_rx_count_(0),
      lfsr_(static_cast<uint32_t>(cfg.seed ^ 0xA5A55A5Au)),
      record_buf_(),
      step_idx_(0),
      total_expected_steps_(static_cast<uint64_t>(std::llround(cfg.duration_s / cfg.tau_s))),
      records_written_(0),
      flyback_count_(0),
      second_half_sum_(0.0),
      second_half_count_(0),
      micro_trace_(micro_trace) {
    // EQ-22: Loop-1 & Loop-2 gains calibrated directly from K_tot_1 and K_tot_2
    if (cfg_.dsp_mode == DspMode::FourState) {
        k_i1_ = cfg_.K_tot_1 / (4.0 * s_alpha_);
        k_i2_ = cfg_.K_tot_2 / (4.0 * PI * s_alpha_);
    } else {
        k_i1_ = cfg_.K_tot_1 / (2.0 * s_alpha_);
        k_i2_ = 0.0;
    }

    // Pre-State-0 bias phase so first differential transition yields exact +(pi - alpha)
    const double init_bias = (cfg_.dsp_mode == DspMode::FourState)
        ? cfg_.alpha_rad
        : (-0.5 * (PI - cfg_.alpha_rad));
    init_dac_code_ = encode_dac_phase(init_bias);
    init_v_drv_ = init_dac_code_ * (cfg_.V_ref_dac_V / static_cast<double>(1ULL << cfg_.N_dac_bits));

    for (auto& tag : pipe_) {
        tag = {false, 0, 0.0};
    }

    record_buf_.reserve(4096);
    bin_ofs_.open(bin_out_path, std::ios::binary | std::ios::trunc);
    if (!bin_ofs_.is_open()) {
        throw std::runtime_error("Cannot open sim_out.bin for writing: " + bin_out_path);
    }

    SC_METHOD(on_adc_sample);
    sensitive << adc_code_in;
    dont_initialize();
}

DigitalDSP_SC::~DigitalDSP_SC() {
    flush_records();
}

double DigitalDSP_SC::bias_phase_for_state(int state_idx) const {
    if (cfg_.dsp_mode == DspMode::FourState) {
        // Bounded instantaneous phases in [-pi, +pi] producing exact EQ-01 differential sequence:
        //   state 0: +pi    - (+alpha) = +(pi - alpha)
        //   state 1: +alpha - (+pi)    = -(pi - alpha)
        //   state 2: -pi    - (+alpha) = -(pi + alpha)
        //   state 3: +alpha - (-pi)    = +(pi + alpha)
        switch (state_idx) {
            case 0:
                return PI;
            case 1:
                return cfg_.alpha_rad;
            case 2:
                return -PI;
            default:
                return cfg_.alpha_rad;
        }
    }
    // 2-state instantaneous bias phases yielding exact +/-(pi - alpha) transitions
    const double half_mod = 0.5 * (PI - cfg_.alpha_rad);
    return (state_idx == 0) ? half_mod : -half_mod;
}

double DigitalDSP_SC::encode_dac_phase(double phi_total) const {
    // EQ-21: DAC_code = round((phi_total / (2*pi)) * G_DAC * 2^{N_DAC})
    const double raw_code = (phi_total / TWO_PI) * g_dac_ * static_cast<double>(1ULL << cfg_.N_dac_bits);
    if (!cfg_.ablation.en_quantization) {
        return raw_code;
    }
    const int64_t limit = static_cast<int64_t>(2ULL << cfg_.N_dac_bits);
    const int64_t rounded = std::clamp<int64_t>(
        static_cast<int64_t>(std::llround(raw_code)), -limit, limit - 1
    );
    // Bit-true SystemC signed fixed-width representation
    const sc_dt::sc_int<32> q_dac = static_cast<int32_t>(rounded);
    return static_cast<double>(q_dac.to_int());
}

void DigitalDSP_SC::on_adc_sample() {
    const double y_now = adc_code_in.read();

    // Pop the tag that generated y_now (exact PIPE_DEPTH = 2 cluster delay)
    const PipeTag rx_tag = pipe_[static_cast<size_t>(pipe_head_)];

    if (rx_tag.valid) {
        if (cfg_.dsp_mode == DspMode::FourState) {
            y_frame_[static_cast<size_t>(rx_tag.state_idx)] = y_now;
            if (rx_tag.state_idx == 3) {
                // EQ-03 & EQ-20: Corrected orthogonal 4-state demodulation (Lefevre Ch. 8)
                const double e_omega_raw =
                    (y_frame_[1] - y_frame_[0]) + (y_frame_[3] - y_frame_[2]);
                // Exact PRBS dither cancellation before Loop-1 integrator (EQ-21)
                const double e_omega = e_omega_raw + 4.0 * s_alpha_ * std::sin(rx_tag.dither_step);

                delta_phi_step_ += k_i1_ * e_omega + k_p1_ * (e_omega - prev_e_omega_);
                prev_e_omega_ = e_omega;

                // Loop-2 V_pi error channel (orthogonal to Delta_phi_NR)
                const double e_vpi =
                    (y_frame_[2] + y_frame_[3]) - (y_frame_[0] + y_frame_[1]);
                last_e_vpi_raw_ = static_cast<int32_t>(std::llround(e_vpi));
                if (cfg_.en_vpi_loop) {
                    g_dac_ -= k_i2_ * e_vpi;
                    g_dac_ = std::clamp(g_dac_, 0.5 * g_dac_nom_, 2.0 * g_dac_nom_);
                }
            }
        } else {
            // EQ-20: 2-state demodulation with alternating sign s[n] = (-1)^n
            if (has_prev_y_2state_) {
                const double sign = (rx_tag.state_idx == 1) ? 1.0 : -1.0;
                const double e_omega_raw = sign * (y_now - prev_y_2state_);
                const double e_omega = e_omega_raw + 2.0 * s_alpha_ * std::sin(rx_tag.dither_step);
                delta_phi_step_ += k_i1_ * e_omega + k_p1_ * (e_omega - prev_e_omega_);
                prev_e_omega_ = e_omega;
            }
            prev_y_2state_ = y_now;
            has_prev_y_2state_ = true;
            ++two_state_rx_count_;
        }
    }

    // EQ-23: Closed-loop angular rate output Omega_out = Delta_phi_step / SF_CL (SF_CL = K_opt)
    omega_out_ = delta_phi_step_ / cfg_.K_opt;

    // Update frame-constant PRBS dither at start of each modulation frame so Loop-2 cancels identically.
    // Reflect direction when |phi_dither_| approaches pi/4 to prevent spurious 2*pi flybacks at zero rate.
    if (emit_state_ == 0) {
        if (cfg_.en_prbs_dither && cfg_.prbs_amplitude_rad > 0.0) {
            int dir = lfsr_.next_bit_signed();
            if (phi_dither_ > 0.25 * PI) {
                dir = -1;
            } else if (phi_dither_ < -0.25 * PI) {
                dir = 1;
            }
            active_dither_step_ = static_cast<double>(dir) * cfg_.prbs_amplitude_rad;
        } else {
            active_dither_step_ = 0.0;
        }
    }

    // EQ-21: Digital phase ramp with modulo-2pi flyback reset
    const double raw_ramp = phi_ramp_ + delta_phi_step_;
    phi_ramp_ = wrap_2pi(raw_ramp);
    const bool flyback = (std::fabs(phi_ramp_ - raw_ramp) > 1.0);
    if (flyback) {
        ++flyback_count_;
    }

    phi_dither_ += active_dither_step_;

    // Negative feedback polarity: feedback ramp (-phi_ramp - phi_dither) nulls +Delta_phi_NR
    const double phi_bias = bias_phase_for_state(emit_state_);
    const double phi_total = -phi_ramp_ - phi_dither_ + phi_bias;
    const double next_dac_code = encode_dac_phase(phi_total);
    dac_code_out.write(next_dac_code);

    if (micro_trace_ != nullptr) {
        micro_trace_->set_phi_ramp(phi_ramp_);
    }

    // Push tag for the DAC code just emitted into the 2-slot pipeline FIFO
    pipe_[static_cast<size_t>(pipe_head_)] = {true, emit_state_, active_dither_step_};
    pipe_head_ = (pipe_head_ + 1) % PIPE_DEPTH;

    const int n_states = (cfg_.dsp_mode == DspMode::FourState) ? 4 : 2;
    emit_state_ = (emit_state_ + 1) % n_states;

    // Accumulate second-half steady-state mean rate for summary diagnostics
    if (step_idx_ >= (total_expected_steps_ / 2)) {
        second_half_sum_ += omega_out_;
        ++second_half_count_;
    }

    // Buffered binary logging at decimation_tau
    if ((step_idx_ % cfg_.decimation_tau) == 0u) {
        const double t_now = static_cast<double>(step_idx_) * cfg_.tau_s;
        uint32_t flags = 0u;
        if (flyback) {
            flags |= FLAG_FLYBACK_RESET;
        }
        if (cfg_.dsp_mode == DspMode::FourState) {
            flags |= FLAG_DSP_4STATE;
        }
        if (cfg_.en_vpi_loop) {
            flags |= FLAG_VPI_LOOP_EN;
        }
        if (cfg_.en_prbs_dither) {
            flags |= FLAG_PRBS_DITHER_EN;
        }

        SimRecord rec{};
        rec.t = t_now;
        rec.omega_in = eval_stimulus(cfg_, t_now);
        rec.omega_out_raw = std::llround(omega_out_ / OMEGA_OUT_LSB);
        rec.vpi_err_raw = last_e_vpi_raw_;
        rec.flags = flags;
        record_buf_.push_back(rec);
        if (record_buf_.size() >= 4096u) {
            flush_records();
        }
    }

    ++step_idx_;
}

void DigitalDSP_SC::flush_records() {
    if (!record_buf_.empty() && bin_ofs_.is_open()) {
        bin_ofs_.write(
            reinterpret_cast<const char*>(record_buf_.data()),
            static_cast<std::streamsize>(record_buf_.size() * sizeof(SimRecord))
        );
        records_written_ += record_buf_.size();
        record_buf_.clear();
    }
}

double DigitalDSP_SC::mean_omega_second_half() const {
    return (second_half_count_ > 0u) ? (second_half_sum_ / static_cast<double>(second_half_count_)) : 0.0;
}

}  // namespace ifog
