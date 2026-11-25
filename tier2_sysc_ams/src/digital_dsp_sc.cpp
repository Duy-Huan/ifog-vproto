#include "digital_dsp_sc.hpp"
#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace ifog {

DigitalDSP_SC::DigitalDSP_SC(
    sc_core::sc_module_name name,
    const IfogConfig& cfg,
    const std::string& bin_out_path,
    MicroTraceCollector* micro_trace,
    DspTraceCollector* dsp_trace
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
      y_nom_(
          (cfg.G1 * cfg.responsivity_A_per_W * cfg.R_f_ohm / compute_adc_lsb(cfg.V_fs_adc_V, cfg.N_adc_bits))
          * (0.5 * cfg.P_peak_W * (1.0 - cfg.visibility_V * std::cos(cfg.alpha_rad)))
      ),
      adc_code_max_(static_cast<double>((1LL << (cfg.N_adc_bits - 1)) - 1LL)),
      delta_phi_step_(0.0),
      filtered_dphi_step_(0.0),
      prev_e_omega_(0.0),
      phi_ramp_(0.0),
      phi_dither_(0.0),
      active_dither_step_(0.0),
      active_prbs_bit_(0),
      omega_out_(0.0),
      last_e_omega_(0.0),
      last_e_asym_(0.0),
      last_e_vpi_raw_(0),
      pipe_{},
      pipe_head_(0),
      emit_state_(0),
      y_frame_{0.0, 0.0, 0.0, 0.0, 0.0, 0.0},
      prev_y_2state_(0.0),
      has_prev_y_2state_(false),
      two_state_rx_count_(0),
      lfsr_(static_cast<uint32_t>(cfg.seed ^ 0xA5A55A5Au)),
      seu_injected_(false),
      last_bit_fault_code_(BIT_OK),
      bit_first_fault_code_(BIT_OK),
      bit_alert_time_s_(-1.0),
      bit_time_to_alert_s_(-1.0),
      fdir_recovery_active_(false),
      fdir_calm_frames_(0),
      fdir_recovered_(false),
      record_buf_(),
      step_idx_(0),
      total_expected_steps_(static_cast<uint64_t>(std::llround(cfg.duration_s / cfg.tau_s))),
      records_written_(0),
      flyback_count_(0),
      anti_windup_count_(0),
      second_half_sum_(0.0),
      second_half_count_(0),
      e_asym_sq_sum_(0.0),
      e_asym_count_(0),
      micro_trace_(micro_trace),
      dsp_trace_(dsp_trace) {
    // EQ-22 & EQ-34: Loop-1 & Loop-2 gains calibrated directly from K_tot_1 and K_tot_2
    double init_bias = 0.0;
    if (cfg_.dsp_mode == DspMode::SixState) {
        k_i1_ = cfg_.K_tot_1 / (6.0 * s_alpha_);
        k_i2_ = cfg_.K_tot_2 / (8.0 * PI * s_alpha_);
        // Pre-State-0 bias phase = psi_5 so State 0 yields psi_0 - psi_5 = +(pi - alpha)
        init_bias = compute_6state_bias_phase(5, cfg_.alpha_rad);
    } else if (cfg_.dsp_mode == DspMode::FourState) {
        k_i1_ = cfg_.K_tot_1 / (4.0 * s_alpha_);
        k_i2_ = cfg_.K_tot_2 / (4.0 * PI * s_alpha_);
        init_bias = cfg_.alpha_rad;
    } else {
        k_i1_ = cfg_.K_tot_1 / (2.0 * s_alpha_);
        k_i2_ = 0.0;
        init_bias = -0.5 * (PI - cfg_.alpha_rad);
    }

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
    if (cfg_.dsp_mode == DspMode::SixState) {
        // EQ-31: Anti-periodic 6-state sequence with zero DC drive mean & zero RAM/xtalk at alpha=pi/3
        return compute_6state_bias_phase(state_idx, cfg_.alpha_rad);
    }
    if (cfg_.dsp_mode == DspMode::FourState) {
        // Bounded instantaneous phases in [-pi, +pi] producing exact EQ-01 differential sequence
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

bool DigitalDSP_SC::apply_loop1_update(double e_omega) {
    // EQ-20 & EQ-34: Loop-1 PI integrator with anti-windup clamping
    const double raw_dphi = delta_phi_step_ + k_i1_ * e_omega + k_p1_ * (e_omega - prev_e_omega_);
    prev_e_omega_ = e_omega;
    last_e_omega_ = e_omega;
    if (raw_dphi > cfg_.max_delta_phi_step_rad) {
        delta_phi_step_ = cfg_.max_delta_phi_step_rad;
        ++anti_windup_count_;
        return true;
    }
    if (raw_dphi < -cfg_.max_delta_phi_step_rad) {
        delta_phi_step_ = -cfg_.max_delta_phi_step_rad;
        ++anti_windup_count_;
        return true;
    }
    delta_phi_step_ = raw_dphi;
    return false;
}

void DigitalDSP_SC::record_bit_fault(uint16_t code, double t_now) {
    last_bit_fault_code_ = code;
    if (bit_first_fault_code_ == BIT_OK) {
        bit_first_fault_code_ = code;
        bit_alert_time_s_ = t_now;
        bit_time_to_alert_s_ = std::max(0.0, t_now - cfg_.fault_inject_time_s);
    }
}

void DigitalDSP_SC::evaluate_frame_bit(
    double t_now,
    double y_mean,
    double y_min,
    double y_max,
    double e_omega,
    double e_vpi
) {
    if (!cfg_.en_bit || step_idx_ < 12u) {
        return;
    }
    if (y_mean < cfg_.bit_fiber_break_ratio * y_nom_ || y_min < cfg_.bit_fiber_break_ratio * y_nom_) {
        record_bit_fault(BIT_FIBER_BREAK, t_now);
    } else if (y_mean < cfg_.bit_sld_drop_ratio * y_nom_ ||
               (y_min < cfg_.bit_sld_drop_ratio * y_nom_ && y_max <= 1.05 * y_nom_)) {
        record_bit_fault(BIT_SLD_DROP, t_now);
    } else if (std::fabs(e_vpi) > cfg_.bit_vpi_err_threshold ||
               g_dac_ <= 0.501 * g_dac_nom_ ||
               g_dac_ >= 1.999 * g_dac_nom_) {
        record_bit_fault(BIT_MIOC_OPEN, t_now);
    } else if (std::fabs(e_omega) > cfg_.bit_seu_err_threshold) {
        record_bit_fault(BIT_DSP_SEU, t_now);
        if (cfg_.en_fdir_recovery) {
            // FDIR soft-recovery: restore Loop-1 integrator to pre-fault smoothed estimate
            delta_phi_step_ = filtered_dphi_step_;
            prev_e_omega_ = 0.0;
            fdir_recovery_active_ = true;
            fdir_calm_frames_ = 0;
        }
    } else {
        filtered_dphi_step_ = 0.85 * filtered_dphi_step_ + 0.15 * delta_phi_step_;
        if (fdir_recovery_active_ && std::fabs(e_omega) < 0.05 * cfg_.bit_seu_err_threshold) {
            ++fdir_calm_frames_;
            if (fdir_calm_frames_ >= 4) {
                fdir_recovered_ = true;
                fdir_recovery_active_ = false;
            }
        }
    }
}

void DigitalDSP_SC::on_adc_sample() {
    const double t_now = static_cast<double>(step_idx_) * cfg_.tau_s;
    const double y_now = adc_code_in.read();

    // EQ-39: Per-tau ADC rail saturation check (when BIT enabled)
    last_bit_fault_code_ = BIT_OK;
    if (cfg_.en_bit && step_idx_ >= 12u && std::fabs(y_now) >= 0.98 * adc_code_max_) {
        record_bit_fault(BIT_ADC_SAT, t_now);
    }

    // Pop the tag that generated y_now (exact PIPE_DEPTH = 2 cluster delay)
    const PipeTag rx_tag = pipe_[static_cast<size_t>(pipe_head_)];
    bool anti_windup_hit = false;

    if (rx_tag.valid) {
        if (cfg_.dsp_mode == DspMode::SixState) {
            y_frame_[static_cast<size_t>(rx_tag.state_idx)] = y_now;
            if (rx_tag.state_idx == 5) {
                // EQ-33: Official 6-state 3-channel orthogonal demodulation
                const double e_omega_raw =
                    (y_frame_[3] + y_frame_[4] + y_frame_[5])
                    - (y_frame_[0] + y_frame_[1] + y_frame_[2]);
                const double e_omega = e_omega_raw + 6.0 * s_alpha_ * std::sin(rx_tag.dither_step);
                anti_windup_hit = apply_loop1_update(e_omega);

                const double e_vpi =
                    2.0 * (y_frame_[1] + y_frame_[4])
                    - (y_frame_[0] + y_frame_[2] + y_frame_[3] + y_frame_[5]);
                last_e_vpi_raw_ = static_cast<int32_t>(std::llround(e_vpi));
                if (cfg_.en_vpi_loop) {
                    g_dac_ -= k_i2_ * e_vpi;
                    g_dac_ = std::clamp(g_dac_, 0.5 * g_dac_nom_, 2.0 * g_dac_nom_);
                }

                last_e_asym_ = (y_frame_[0] - y_frame_[2]) + (y_frame_[5] - y_frame_[3]);
                e_asym_sq_sum_ += last_e_asym_ * last_e_asym_;
                ++e_asym_count_;

                const double y_mean =
                    (y_frame_[0] + y_frame_[1] + y_frame_[2] + y_frame_[3] + y_frame_[4] + y_frame_[5])
                    / 6.0;
                const auto [it_min, it_max] = std::minmax_element(y_frame_.begin(), y_frame_.end());
                evaluate_frame_bit(t_now, y_mean, *it_min, *it_max, e_omega, e_vpi);
            }
        } else if (cfg_.dsp_mode == DspMode::FourState) {
            y_frame_[static_cast<size_t>(rx_tag.state_idx)] = y_now;
            if (rx_tag.state_idx == 3) {
                // EQ-03 & EQ-20: Corrected orthogonal 4-state demodulation (Lefevre Ch. 8)
                const double e_omega_raw =
                    (y_frame_[1] - y_frame_[0]) + (y_frame_[3] - y_frame_[2]);
                const double e_omega = e_omega_raw + 4.0 * s_alpha_ * std::sin(rx_tag.dither_step);
                anti_windup_hit = apply_loop1_update(e_omega);

                const double e_vpi =
                    (y_frame_[2] + y_frame_[3]) - (y_frame_[0] + y_frame_[1]);
                last_e_vpi_raw_ = static_cast<int32_t>(std::llround(e_vpi));
                if (cfg_.en_vpi_loop) {
                    g_dac_ -= k_i2_ * e_vpi;
                    g_dac_ = std::clamp(g_dac_, 0.5 * g_dac_nom_, 2.0 * g_dac_nom_);
                }

                const double y_mean = 0.25 * (y_frame_[0] + y_frame_[1] + y_frame_[2] + y_frame_[3]);
                const auto [it_min, it_max] = std::minmax_element(y_frame_.begin(), y_frame_.begin() + 4);
                evaluate_frame_bit(t_now, y_mean, *it_min, *it_max, e_omega, e_vpi);
            }
        } else {
            // EQ-20: 2-state demodulation with alternating sign s[n] = (-1)^n
            if (has_prev_y_2state_) {
                const double sign = (rx_tag.state_idx == 1) ? 1.0 : -1.0;
                const double e_omega_raw = sign * (y_now - prev_y_2state_);
                const double e_omega = e_omega_raw + 2.0 * s_alpha_ * std::sin(rx_tag.dither_step);
                anti_windup_hit = apply_loop1_update(e_omega);
            }
            prev_y_2state_ = y_now;
            has_prev_y_2state_ = true;
            ++two_state_rx_count_;
        }
    }

    // EQ-39: Single-Event Upset (SEU) one-shot register bit-flip fault injection
    if (cfg_.fault_type == FaultType::DspSeuBitflip &&
        !seu_injected_ &&
        t_now >= cfg_.fault_inject_time_s) {
        delta_phi_step_ += cfg_.fault_seu_delta_phi_rad;
        seu_injected_ = true;
    }

    // EQ-23: Closed-loop angular rate output Omega_out = Delta_phi_step / SF_CL (SF_CL = K_opt)
    omega_out_ = delta_phi_step_ / cfg_.K_opt;

    // Update frame-constant PRBS dither at start of each modulation frame so Loop-2 cancels identically.
    if (emit_state_ == 0) {
        if (cfg_.en_prbs_dither && cfg_.prbs_amplitude_rad > 0.0) {
            int dir = lfsr_.next_bit_signed();
            if (phi_dither_ > 0.25 * PI) {
                dir = -1;
            } else if (phi_dither_ < -0.25 * PI) {
                dir = 1;
            }
            active_prbs_bit_ = static_cast<int16_t>(dir);
            active_dither_step_ = static_cast<double>(dir) * cfg_.prbs_amplitude_rad;
        } else {
            active_prbs_bit_ = 0;
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
        micro_trace_->set_dsp_state(phi_ramp_, static_cast<int32_t>(std::llround(next_dac_code)));
    }
    if (dsp_trace_ != nullptr && dsp_trace_->enabled()) {
        DspTraceRecord tr{};
        tr.t = t_now;
        tr.phi_ramp = phi_ramp_;
        tr.delta_phi_step = delta_phi_step_;
        tr.g_dac = g_dac_;
        tr.e_omega = last_e_omega_;
        tr.e_asym = last_e_asym_;
        tr.adc_code = static_cast<int32_t>(std::llround(y_now));
        tr.dac_code = static_cast<int32_t>(std::llround(next_dac_code));
        tr.e_vpi = last_e_vpi_raw_;
        tr.prbs_bit = active_prbs_bit_;
        tr.bit_fault_code = last_bit_fault_code_;
        dsp_trace_->push(tr);
    }

    // Push tag for the DAC code just emitted into the 2-slot pipeline FIFO
    pipe_[static_cast<size_t>(pipe_head_)] = {true, emit_state_, active_dither_step_};
    pipe_head_ = (pipe_head_ + 1) % PIPE_DEPTH;

    const int n_states =
        (cfg_.dsp_mode == DspMode::SixState) ? 6 : ((cfg_.dsp_mode == DspMode::FourState) ? 4 : 2);
    emit_state_ = (emit_state_ + 1) % n_states;

    // Accumulate second-half steady-state mean rate for summary diagnostics
    if (step_idx_ >= (total_expected_steps_ / 2)) {
        second_half_sum_ += omega_out_;
        ++second_half_count_;
    }

    // Buffered binary logging at decimation_tau
    if ((step_idx_ % cfg_.decimation_tau) == 0u) {
        uint32_t flags = 0u;
        if (flyback) {
            flags |= FLAG_FLYBACK_RESET;
        }
        if (cfg_.dsp_mode == DspMode::FourState) {
            flags |= FLAG_DSP_4STATE;
        } else if (cfg_.dsp_mode == DspMode::SixState) {
            flags |= FLAG_DSP_6STATE;
        }
        if (cfg_.en_vpi_loop) {
            flags |= FLAG_VPI_LOOP_EN;
        }
        if (cfg_.en_prbs_dither) {
            flags |= FLAG_PRBS_DITHER_EN;
        }
        if (last_bit_fault_code_ != BIT_OK) {
            flags |= FLAG_BIT_FAULT;
        }
        if (anti_windup_hit) {
            flags |= FLAG_ANTI_WINDUP;
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
    if (dsp_trace_ != nullptr) {
        dsp_trace_->flush();
    }
}

double DigitalDSP_SC::mean_omega_second_half() const {
    return (second_half_count_ > 0u) ? (second_half_sum_ / static_cast<double>(second_half_count_)) : 0.0;
}

double DigitalDSP_SC::e_asym_rms() const {
    return (e_asym_count_ > 0u) ? std::sqrt(e_asym_sq_sum_ / static_cast<double>(e_asym_count_)) : 0.0;
}

}  // namespace ifog
