#include "optical_envelope_tdf.hpp"
#include <cmath>
#include "ifog_math.hpp"

namespace ifog {

OpticalEnvelope_TDF::OpticalEnvelope_TDF(
    sc_core::sc_module_name name,
    const IfogConfig& cfg,
    double init_v_drv,
    MicroTraceCollector* micro_trace,
    const ExternalDriveState* ext_drive
)
    : sca_tdf::sca_module(name),
      v_drv_in("v_drv_in"),
      p_scale_in("p_scale_in"),
      p_det_out("p_det_out"),
      cfg_(cfg),
      dt_fast_(cfg.tau_s / static_cast<double>(cfg.K_oversample)),
      init_v_drv_(init_v_drv),
      eps_vpi_eff_(cfg.ablation.en_mioc_vpi_err ? cfg.eps_vpi : 0.0),
      gamma_nl_eff_(cfg.ablation.en_mioc_vpi_err ? cfg.gamma_nl_rad_per_V2 : 0.0),
      alpha_ram_eff_(cfg.ablation.en_ram ? cfg.alpha_ram_per_V : 0.0),
      phi_kerr_eff_(cfg.ablation.en_kerr ? cfg.delta_phi_kerr_rad : 0.0),
      phi_faraday_dc_(
          cfg.ablation.en_faraday
              ? compute_faraday_phase(cfg.verdet_rad_per_Tm, cfg.B_ext_T, cfg.effective_loop_m)
              : 0.0
      ),
      sample_idx_(0),
      ring_pos_(0),
      phi_mioc_ring_(static_cast<size_t>(cfg.K_oversample), 0.0),
      mioc_dyn_(),
      back_rng_(cfg.seed ^ 0x9E3779B97F4A7C15ULL),
      ou_phi_(std::exp(-cfg.tau_s / std::max(cfg.spec007.tau_env_s, 1.0e-6))),
      ou_sigma_step_(
          cfg.spec007.sigma_theta_env_rad * std::sqrt(std::max(0.0, 1.0 - ou_phi_ * ou_phi_))
      ),
      theta_env_(0.0),
      micro_trace_(micro_trace),
      ext_drive_(ext_drive) {}

void OpticalEnvelope_TDF::set_attributes() {
    v_drv_in.set_rate(cfg_.K_oversample);
    p_scale_in.set_rate(cfg_.K_oversample);
    p_det_out.set_rate(cfg_.K_oversample);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void OpticalEnvelope_TDF::initialize() {
    if (cfg_.spec007.en_spec007_physics) {
        mioc_dyn_.configure(
            cfg_.spec007.mioc_f_elec_Hz,
            cfg_.spec007.mioc_f_acoustic_Hz,
            cfg_.spec007.mioc_zeta_acoustic,
            cfg_.spec007.mioc_g_acoustic,
            dt_fast_,
            init_v_drv_
        );
    }
    const double phi_init = compute_mioc_phase(init_v_drv_, cfg_.V_pi_0_V, eps_vpi_eff_, gamma_nl_eff_);
    std::fill(phi_mioc_ring_.begin(), phi_mioc_ring_.end(), phi_init);
}

void OpticalEnvelope_TDF::processing() {
    const int K = cfg_.K_oversample;
    const double t_cluster = static_cast<double>(sample_idx_) * dt_fast_;
    const bool log_micro = (micro_trace_ != nullptr) && micro_trace_->active_at(t_cluster);

    // EQ-52 (SPEC-007 §2.5): Coherent back-reflection environmental phase OU step per tau
    double delta_phi_back = 0.0;
    const bool live_spec007 = (ext_drive_ != nullptr && ext_drive_->use_spec007_live);
    if (cfg_.spec007.en_spec007_physics || live_spec007) {
        const double r_facet_db = live_spec007 ? ext_drive_->R_facet_dB_live : cfg_.spec007.R_facet_dB;
        const double sigma_back = compute_backscatter_sigma_rad(
            r_facet_db, cfg_.spec007.alpha_R_per_m, cfg_.spec007.S_capture, cfg_.delta_nu_eff_Hz
        );
        if (sigma_back > 0.0) {
            theta_env_ = ou_phi_ * theta_env_ + ou_sigma_step_ * back_rng_.normal01();
            delta_phi_back = sigma_back * std::sin(theta_env_);
        }
    }

    const bool has_v2_lut = (cfg_.shupe_lut_version == 2u) && !cfg_.shupe_lut_v2.empty();

    for (int k = 0; k < K; ++k) {
        const double t = static_cast<double>(sample_idx_) * dt_fast_;
        const double v_drv = v_drv_in.read(k);
        double p_scale = p_scale_in.read(k);

        // EQ-47..EQ-49: Interpolate 6-channel v2 LUT (or v1 fallback) at each TDF step t_k
        double k_opt_now = cfg_.K_opt;
        double vis_now = cfg_.visibility_V;
        double phi_pol_now = cfg_.phi_pol_rad + cfg_.phi_pol_drift_rad_per_s * t;
        double v_pi_now = cfg_.V_pi_0_V;
        double delta_phi_therm = 0.0;

        if (cfg_.ablation.en_shupe) {
            if (has_v2_lut) {
                const ShupeLutRecordV2 rec = interpolate_shupe_v2(cfg_.shupe_lut_v2, t);
                delta_phi_therm = rec.delta_phi_shupe_rad + rec.delta_phi_stress_rad;
                vis_now = rec.visibility_V_t;
                phi_pol_now = rec.phi_pol_rad_t + cfg_.phi_pol_drift_rad_per_s * t;
                if (rec.v_pi_V_t > 0.0) {
                    v_pi_now = rec.v_pi_V_t;
                }
                k_opt_now = cfg_.K_opt * rec.k_opt_scale_rel_t;
            } else {
                delta_phi_therm = interpolate_shupe(cfg_.shupe_lut, t);
            }
        }

        // EQ-06..EQ-10, EQ-46, EQ-52: Total non-reciprocal phase Delta_phi_NR[m]
        const double omega_in =
            (ext_drive_ != nullptr && ext_drive_->use_external_omega)
                ? ext_drive_->omega_in_rad_per_s
                : eval_stimulus(cfg_, t);
        double delta_phi_nr = k_opt_now * omega_in + phi_kerr_eff_ + phi_faraday_dc_ + delta_phi_back;
        if (cfg_.ablation.en_faraday && cfg_.B_ac_T > 0.0) {
            // EQ-38: Dynamic external AC magnetic field Faraday phase
            const double b_ac = cfg_.B_ac_T * std::sin(TWO_PI * cfg_.B_freq_Hz * t);
            delta_phi_nr += compute_faraday_phase(cfg_.verdet_rad_per_Tm, b_ac, cfg_.effective_loop_m);
        }
        if (cfg_.ablation.en_pol_error) {
            delta_phi_nr += phi_pol_now;
        }
        if (cfg_.ablation.en_shupe) {
            delta_phi_nr += delta_phi_therm;
        }
        if (ext_drive_ != nullptr && ext_drive_->use_external_shupe) {
            delta_phi_nr += ext_drive_->shupe_phase_rad;
        }

        // EQ-37: Mechanical vibration optical loss & microphonic phase modulation (ENG-03)
        if (cfg_.en_vibration && cfg_.vib_g_rms > 0.0) {
            const double a_g = std::sqrt(2.0) * cfg_.vib_g_rms * std::sin(TWO_PI * cfg_.vib_freq_Hz * t);
            delta_phi_nr += cfg_.vib_phase_mod_rad_per_g * a_g;
            p_scale *= (1.0 + cfg_.vib_loss_mod_per_g * a_g);
        }

        // TD-03 & SPEC-006 tunable eps_vpi: Thermal shock step jump or live FMI parameter
        double eps_now =
            (ext_drive_ != nullptr && ext_drive_->use_live_params && cfg_.ablation.en_mioc_vpi_err)
                ? ext_drive_->eps_vpi_live
                : eps_vpi_eff_;
        if (cfg_.ablation.en_mioc_vpi_err && cfg_.eps_vpi_step_time_s >= 0.0 && t >= cfg_.eps_vpi_step_time_s) {
            eps_now += cfg_.eps_vpi_step_delta;
        }

        // EQ-39: Optical / MIOC Fault Injection (ENG-04)
        if (cfg_.fault_type != FaultType::None &&
            is_fault_active(t, cfg_.fault_inject_time_s, cfg_.fault_duration_s)) {
            if (cfg_.fault_type == FaultType::SldDrop50Pct) {
                p_scale *= 0.5;
            } else if (cfg_.fault_type == FaultType::FiberBreak) {
                p_scale = 0.0;
            } else if (cfg_.fault_type == FaultType::MiocElectrodeOpen) {
                // Losing one push-pull MIOC electrode doubles effective V_pi (halves phase gain)
                eps_now = -0.5;
            }
        }

        // EQ-11, EQ-12 & EQ-50: MIOC electro-acoustic dynamics + modulo-2pi differential phase across K_delay
        const double v_mioc_eff = mioc_dyn_.active() ? step_mioc_dynamics(mioc_dyn_, v_drv) : v_drv;
        const double phi_now = compute_mioc_phase(v_mioc_eff, v_pi_now, eps_now, gamma_nl_eff_);
        const double phi_delayed = phi_mioc_ring_[static_cast<size_t>(ring_pos_)];
        phi_mioc_ring_[static_cast<size_t>(ring_pos_)] = phi_now;
        ring_pos_ = (ring_pos_ + 1) % K;

        const double delta_phi_mod = wrap_2pi(phi_now - phi_delayed);

        // EQ-13 & EQ-36: Detected optical power with RAM & shared SLD bus scaling
        const double p_det = compute_pd_power(
            cfg_.P_peak_W * p_scale, alpha_ram_eff_, v_drv, vis_now, delta_phi_nr, delta_phi_mod
        );

        p_det_out.write(p_det, k);
        if (log_micro) {
            micro_trace_->set_optical(k, t, v_drv, p_det);
        }
        ++sample_idx_;
    }
}

}  // namespace ifog
