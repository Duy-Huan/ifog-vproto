#include "analog_frontend_tdf.hpp"
#include <cmath>

namespace ifog {

AnalogFrontEnd_TDF::AnalogFrontEnd_TDF(
    sc_core::sc_module_name name,
    const IfogConfig& cfg,
    MicroTraceCollector* micro_trace,
    const ExternalDriveState* ext_drive
)
    : sca_tdf::sca_module(name),
      p_det_in("p_det_in"),
      v_drv_in("v_drv_in"),
      dv_drv_dt_in("dv_drv_dt_in"),
      pink_tia_in("pink_tia_in"),
      pink_xtalk_in("pink_xtalk_in"),
      rail_droop_in("rail_droop_in"),
      v_adc_out("v_adc_out"),
      cfg_(cfg),
      dt_fast_(cfg.tau_s / static_cast<double>(cfg.K_oversample)),
      B_fast_Hz_(1.0 / (2.0 * dt_fast_)),
      c_xtalk_eff_(
          cfg.ablation.en_xtalk
              ? (cfg.spec007.en_spec007_physics ? cfg.spec007.C_xtalk_F : cfg.C_xtalk_F)
              : 0.0
      ),
      k_xtalk_eff_(
          cfg.ablation.en_xtalk
              ? (cfg.spec007.en_spec007_physics ? cfg.spec007.G_xtalk_S : cfg.k_xtalk_A_per_V)
              : 0.0
      ),
      omega0_(compute_tia_omega0(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F, cfg.C_f_F)),
      zeta_(compute_tia_zeta(cfg.f_gbw_Hz, cfg.R_f_ohm, cfg.C_tot_F, cfg.C_f_F)),
      use_sca_ltf_((omega0_ * dt_fast_) <= 0.2),
      var_fixed_A2_(0.0),
      shot_coeff_(2.0 * Q_ELECTRON * cfg.responsivity_A_per_W * B_fast_Hz_),
      rin_coeff_((cfg.responsivity_A_per_W * cfg.responsivity_A_per_W / cfg.delta_nu_eff_Hz) * B_fast_Hz_),
      ltf_tia_("ltf_tia"),
      num_tia_(1),
      den_tia_(3),
      state_tia_(2),
      exact_ltf_tia_(),
      rng_(cfg.seed ^ 0xA24BAED4963EE407ULL),
      cluster_idx_(0),
      clip_count_(0),
      v_drv_prev_(0.0),
      has_v_drv_prev_(false),
      micro_trace_(micro_trace),
      ext_drive_(ext_drive) {
    // Precompute P_det-independent terms of EQ-15 (dark + thermal + op-amp white + capacitive gain)
    var_fixed_A2_ = compute_tia_noise_variance(
        0.0,
        cfg.responsivity_A_per_W,
        cfg.I_dark_A,
        cfg.T_tia_K,
        cfg.R_f_ohm,
        cfg.delta_nu_eff_Hz,
        cfg.i_n_op_A_per_rtHz,
        cfg.e_n_op_V_per_rtHz,
        cfg.C_tot_F,
        cfg.C_f_F,
        B_fast_Hz_
    );
}

void AnalogFrontEnd_TDF::set_attributes() {
    p_det_in.set_rate(cfg_.K_oversample);
    v_drv_in.set_rate(cfg_.K_oversample);
    dv_drv_dt_in.set_rate(cfg_.K_oversample);
    pink_tia_in.set_rate(1);
    pink_xtalk_in.set_rate(1);
    rail_droop_in.set_rate(cfg_.K_oversample);
    v_adc_out.set_rate(cfg_.K_oversample);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void AnalogFrontEnd_TDF::initialize() {
    // EQ-16: H_TIA(s) = (R_f * omega_0^2) / (omega_0^2 + 2*zeta*omega_0*s + s^2)
    const double w0_sq = omega0_ * omega0_;
    num_tia_(0) = cfg_.R_f_ohm * w0_sq;
    den_tia_(0) = w0_sq;
    den_tia_(1) = 2.0 * zeta_ * omega0_;
    den_tia_(2) = 1.0;
    state_tia_(0) = 0.0;
    state_tia_(1) = 0.0;

    // Pre-initialize steady state to nominal dark-fringe operating photocurrent
    const double p_init = 0.5 * cfg_.P_peak_W * (1.0 - cfg_.visibility_V * std::cos(cfg_.alpha_rad));
    const double v_init = cfg_.R_f_ohm * cfg_.responsivity_A_per_W * p_init;
    exact_ltf_tia_.configure(cfg_.R_f_ohm, omega0_, zeta_, dt_fast_, v_init);
}

void AnalogFrontEnd_TDF::processing() {
    const int K = cfg_.K_oversample;
    const double t_cluster = static_cast<double>(cluster_idx_) * cfg_.tau_s;
    const bool log_micro = (micro_trace_ != nullptr) && micro_trace_->active_at(t_cluster);

    const bool live_spec007 = (ext_drive_ != nullptr && ext_drive_->use_spec007_live);
    const double pink_scale = live_spec007 ? ext_drive_->c_pink_coeff_live : 1.0;
    const double n_pink_tia = pink_tia_in.read() * pink_scale;
    const double n_pink_xtalk = pink_xtalk_in.read();

    double k_xtalk_base = k_xtalk_eff_;
    double c_xtalk_base = c_xtalk_eff_;
    if (ext_drive_ != nullptr && ext_drive_->use_live_params && cfg_.ablation.en_xtalk) {
        k_xtalk_base = live_spec007 ? ext_drive_->G_xtalk_S_live : ext_drive_->k_xtalk_live_A_per_V;
        if (live_spec007) {
            c_xtalk_base = ext_drive_->C_xtalk_F_live;
        }
    }
    const double k_xtalk_mod = k_xtalk_base * (1.0 + n_pink_xtalk);
    const bool use_eq51_diff = cfg_.spec007.en_spec007_physics || live_spec007;
    const bool adc_sat_fault =
        (cfg_.fault_type == FaultType::AdcSaturation) &&
        is_fault_active(t_cluster, cfg_.fault_inject_time_s, cfg_.fault_duration_s);

    for (int k = 0; k < K; ++k) {
        const double p_det = p_det_in.read(k);
        const double v_drv = v_drv_in.read(k);
        const double dv_dt = dv_drv_dt_in.read(k);
        const double rail_droop = rail_droop_in.read(k);

        // EQ-15: Exact 6-component input current noise variance integrated over [0, B_fast]
        double i_white = 0.0;
        if (cfg_.en_white_noise) {
            const double var_i = var_fixed_A2_ + shot_coeff_ * p_det + rin_coeff_ * p_det * p_det;
            i_white = std::sqrt(var_i) * rng_.normal01();
        }

        // EQ-14 & EQ-51: Total inverting-node TIA input current with capacitive + resistive crosstalk
        const double v_prev = has_v_drv_prev_ ? v_drv_prev_ : v_drv;
        const double i_xtalk = use_eq51_diff
            ? compute_capacitive_crosstalk_A(v_drv, v_prev, dt_fast_, k_xtalk_mod, c_xtalk_base)
            : (c_xtalk_base * dv_dt + k_xtalk_mod * v_drv);
        v_drv_prev_ = v_drv;
        has_v_drv_prev_ = true;

        const double i_in = cfg_.responsivity_A_per_W * p_det + i_xtalk + i_white;

        // EQ-16: Second-order TIA transient response
        double v_tia = cfg_.R_f_ohm * i_in;
        if (cfg_.ablation.en_ltf_transient) {
            if (use_sca_ltf_) {
                v_tia = ltf_tia_(num_tia_, den_tia_, state_tia_, i_in, 1.0);
            } else {
                v_tia = exact_ltf_tia_.step(i_in);
            }
        }

        // EQ-18 & EQ-36: TIA 1/f offset + shared power-rail PSRR (-40 dB) + cubic nonlinearity + clipping
        const double v_lin = v_tia + cfg_.V_off_0_V + n_pink_tia + 0.01 * rail_droop;
        double v_adc = cfg_.G1 * v_lin;
        if (adc_sat_fault) {
            v_adc = cfg_.V_max_V;
            ++clip_count_;
        } else if (cfg_.ablation.en_tia_poly_nl) {
            const double v_poly =
                cfg_.G1 * v_lin
                + cfg_.G2_per_V * v_lin * v_lin
                + cfg_.G3_per_V2 * v_lin * v_lin * v_lin;
            if (v_poly < cfg_.V_min_V) {
                v_adc = cfg_.V_min_V;
                ++clip_count_;
            } else if (v_poly > cfg_.V_max_V) {
                v_adc = cfg_.V_max_V;
                ++clip_count_;
            } else {
                v_adc = v_poly;
            }
        }

        v_adc_out.write(v_adc, k);
        if (log_micro) {
            micro_trace_->set_analog(k, v_tia, v_adc);
        }
    }

    ++cluster_idx_;
}

}  // namespace ifog
