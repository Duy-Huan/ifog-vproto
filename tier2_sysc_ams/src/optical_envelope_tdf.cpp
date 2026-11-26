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
      micro_trace_(micro_trace),
      ext_drive_(ext_drive) {}

void OpticalEnvelope_TDF::set_attributes() {
    v_drv_in.set_rate(cfg_.K_oversample);
    p_scale_in.set_rate(cfg_.K_oversample);
    p_det_out.set_rate(cfg_.K_oversample);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void OpticalEnvelope_TDF::initialize() {
    const double phi_init = compute_mioc_phase(init_v_drv_, cfg_.V_pi_0_V, eps_vpi_eff_, gamma_nl_eff_);
    std::fill(phi_mioc_ring_.begin(), phi_mioc_ring_.end(), phi_init);
}

void OpticalEnvelope_TDF::processing() {
    const int K = cfg_.K_oversample;
    const double t_cluster = static_cast<double>(sample_idx_) * dt_fast_;
    const bool log_micro = (micro_trace_ != nullptr) && micro_trace_->active_at(t_cluster);

    for (int k = 0; k < K; ++k) {
        const double t = static_cast<double>(sample_idx_) * dt_fast_;
        const double v_drv = v_drv_in.read(k);
        double p_scale = p_scale_in.read(k);

        // EQ-06..EQ-10: Total non-reciprocal phase Delta_phi_NR[m]
        const double omega_in =
            (ext_drive_ != nullptr && ext_drive_->use_external_omega)
                ? ext_drive_->omega_in_rad_per_s
                : eval_stimulus(cfg_, t);
        double delta_phi_nr = cfg_.K_opt * omega_in + phi_kerr_eff_ + phi_faraday_dc_;
        if (cfg_.ablation.en_faraday && cfg_.B_ac_T > 0.0) {
            // EQ-38: Dynamic external AC magnetic field Faraday phase
            const double b_ac = cfg_.B_ac_T * std::sin(TWO_PI * cfg_.B_freq_Hz * t);
            delta_phi_nr += compute_faraday_phase(cfg_.verdet_rad_per_Tm, b_ac, cfg_.effective_loop_m);
        }
        if (cfg_.ablation.en_pol_error) {
            delta_phi_nr += cfg_.phi_pol_rad + cfg_.phi_pol_drift_rad_per_s * t;
        }
        if (cfg_.ablation.en_shupe) {
            delta_phi_nr += interpolate_shupe(cfg_.shupe_lut, t);
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

        // EQ-11 & EQ-12: MIOC phase & modulo-2pi differential modulation phase across delay K
        const double phi_now = compute_mioc_phase(v_drv, cfg_.V_pi_0_V, eps_now, gamma_nl_eff_);
        const double phi_delayed = phi_mioc_ring_[static_cast<size_t>(ring_pos_)];
        phi_mioc_ring_[static_cast<size_t>(ring_pos_)] = phi_now;
        ring_pos_ = (ring_pos_ + 1) % K;

        const double delta_phi_mod = wrap_2pi(phi_now - phi_delayed);

        // EQ-13 & EQ-36: Detected optical power with RAM & shared SLD bus scaling
        const double p_det = compute_pd_power(
            cfg_.P_peak_W * p_scale, alpha_ram_eff_, v_drv, cfg_.visibility_V, delta_phi_nr, delta_phi_mod
        );

        p_det_out.write(p_det, k);
        if (log_micro) {
            micro_trace_->set_optical(k, t, v_drv, p_det);
        }
        ++sample_idx_;
    }
}

}  // namespace ifog
