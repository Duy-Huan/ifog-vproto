#include "adc_dac_bridge.hpp"
#include <algorithm>
#include <cmath>
#include <systemc.h>
#include "ifog_math.hpp"

namespace ifog {

ADC_Bridge_TDF::ADC_Bridge_TDF(
    sc_core::sc_module_name name,
    const IfogConfig& cfg,
    MicroTraceCollector* micro_trace
)
    : sca_tdf::sca_module(name),
      v_adc_in("v_adc_in"),
      adc_code_out("adc_code_out"),
      cfg_(cfg),
      win_start_(cfg.en_adc_blanking ? cfg.k_start : 0),
      win_end_(cfg.en_adc_blanking ? cfg.k_end : (cfg.K_oversample - 1)),
      win_len_(win_end_ - win_start_ + 1),
      eta_blanking_(static_cast<double>(win_len_) / static_cast<double>(cfg.K_oversample)),
      delta_adc_(compute_adc_lsb(cfg.V_fs_adc_V, cfg.N_adc_bits)),
      inv_dt_fast_(static_cast<double>(cfg.K_oversample) / cfg.tau_s),
      prev_v_adc_(0.0),
      code_min_(-(1LL << (cfg.N_adc_bits - 1))),
      code_max_((1LL << (cfg.N_adc_bits - 1)) - 1LL),
      rng_(cfg.seed ^ 0x517CC1B727220A95ULL),
      cluster_idx_(0),
      micro_trace_(micro_trace) {}

void ADC_Bridge_TDF::set_attributes() {
    v_adc_in.set_rate(cfg_.K_oversample);
    adc_code_out.set_rate(1);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void ADC_Bridge_TDF::processing() {
    // EQ-19 & EQ-35: Average over blanking window [win_start_, win_end_] with optional aperture jitter
    const int K = cfg_.K_oversample;
    double sum_v = 0.0;
    double max_edge_slew = 0.0;
    double prev = (cluster_idx_ == 0u) ? v_adc_in.read(0) : prev_v_adc_;
    for (int k = 0; k < K; ++k) {
        const double v_k = v_adc_in.read(k);
        const double slew_k = (v_k - prev) * inv_dt_fast_;
        max_edge_slew = std::max(max_edge_slew, std::fabs(slew_k));
        if (k >= win_start_ && k <= win_end_) {
            double v_sample = v_k;
            if (cfg_.aperture_jitter_s > 0.0) {
                // EQ-35: dV_j = (dV_adc/dt) * delta_t_j combining local & switching-edge slew
                const double eff_slew = std::hypot(slew_k, 0.25 * max_edge_slew);
                v_sample += eff_slew * cfg_.aperture_jitter_s * rng_.normal01();
            }
            sum_v += v_sample;
        }
        prev = v_k;
    }
    prev_v_adc_ = prev;
    const double raw_counts = sum_v / (delta_adc_ * static_cast<double>(win_len_));

    double out_val = raw_counts;
    int32_t int_code = static_cast<int32_t>(std::llround(raw_counts));
    if (cfg_.ablation.en_quantization) {
        const int64_t rounded = static_cast<int64_t>(std::llround(raw_counts));
        const int64_t clamped = std::clamp<int64_t>(rounded, code_min_, code_max_);
        // Bit-true SystemC sc_int<32> representation
        const sc_dt::sc_int<32> q_code = static_cast<int32_t>(clamped);
        int_code = q_code.to_int();
        out_val = static_cast<double>(int_code);
    }

    adc_code_out.write(out_val);

    const double t_cluster = static_cast<double>(cluster_idx_) * cfg_.tau_s;
    if ((micro_trace_ != nullptr) && micro_trace_->active_at(t_cluster)) {
        micro_trace_->flush_cluster(int_code, win_start_, win_end_);
    }
    ++cluster_idx_;
}

DAC_Driver_TDF::DAC_Driver_TDF(
    sc_core::sc_module_name name,
    const IfogConfig& cfg,
    double init_dac_code,
    double init_v_drv
)
    : sca_tdf::sca_module(name),
      dac_code_in("dac_code_in"),
      pink_dac_in("pink_dac_in"),
      rail_droop_in("rail_droop_in"),
      v_drv_out("v_drv_out"),
      dv_drv_dt_out("dv_drv_dt_out"),
      cfg_(cfg),
      dt_fast_(cfg.tau_s / static_cast<double>(cfg.K_oversample)),
      inv_dt_fast_(1.0 / dt_fast_),
      dac_lsb_scale_(cfg.V_ref_dac_V / static_cast<double>(1ULL << cfg.N_dac_bits)),
      init_dac_code_(init_dac_code),
      init_v_drv_(init_v_drv),
      v_drv_prev_(init_v_drv),
      use_sca_ltf_((cfg.drv_omega0_rad_per_s * dt_fast_) <= 0.2),
      ltf_drv_("ltf_drv"),
      num_drv_(1),
      den_drv_(3),
      state_drv_(2),
      exact_ltf_drv_() {}

void DAC_Driver_TDF::set_attributes() {
    dac_code_in.set_rate(1);
    // Rule 10 (Spec Fig. 2): Mandatory set_delay(1) breaking closed-loop algebraic dependency
    dac_code_in.set_delay(1);
    pink_dac_in.set_rate(1);
    rail_droop_in.set_rate(1);
    rail_droop_in.set_delay(1);
    v_drv_out.set_rate(cfg_.K_oversample);
    dv_drv_dt_out.set_rate(cfg_.K_oversample);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void DAC_Driver_TDF::initialize() {
    dac_code_in.initialize(init_dac_code_, 0);
    rail_droop_in.initialize(0.0, 0);
    const double w0_sq = cfg_.drv_omega0_rad_per_s * cfg_.drv_omega0_rad_per_s;
    num_drv_(0) = w0_sq;
    den_drv_(0) = w0_sq;
    den_drv_(1) = 2.0 * cfg_.drv_zeta * cfg_.drv_omega0_rad_per_s;
    den_drv_(2) = 1.0;
    state_drv_(0) = init_v_drv_;
    state_drv_(1) = 0.0;
    exact_ltf_drv_.configure(1.0, cfg_.drv_omega0_rad_per_s, cfg_.drv_zeta, dt_fast_, init_v_drv_);
    v_drv_prev_ = init_v_drv_;
}

void DAC_Driver_TDF::processing() {
    const int K = cfg_.K_oversample;
    const double code = dac_code_in.read();
    const double n_pink_dac = pink_dac_in.read();
    const double rail_droop = rail_droop_in.read();
    const double v_target = code * dac_lsb_scale_ * (1.0 + n_pink_dac + (rail_droop / cfg_.V_ref_dac_V));

    for (int k = 0; k < K; ++k) {
        double v_now = v_target;
        if (cfg_.ablation.en_ltf_transient) {
            if (use_sca_ltf_) {
                v_now = ltf_drv_(num_drv_, den_drv_, state_drv_, v_target, 1.0);
            } else {
                v_now = exact_ltf_drv_.step(v_target);
            }
        }
        const double dv_dt = (v_now - v_drv_prev_) * inv_dt_fast_;
        v_drv_out.write(v_now, k);
        dv_drv_dt_out.write(dv_dt, k);
        v_drv_prev_ = v_now;
    }
}

}  // namespace ifog
