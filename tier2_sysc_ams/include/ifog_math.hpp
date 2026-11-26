#ifndef IFOG_MATH_HPP
#define IFOG_MATH_HPP

#include <algorithm>
#include <cmath>
#include <cstdint>
#include "ifog_types.hpp"

namespace ifog {

// EQ-12 / EQ-21: Exact modulo-2pi phase wrapping in [-pi, +pi] (64-bit IEEE-754 double)
inline double wrap_2pi(double x) {
    return x - TWO_PI * std::round(x / TWO_PI);
}

// EQ-06: Transit time tau = n_eff * L / c [s]
inline double compute_tau(double L_m, double n_eff) {
    return (n_eff * L_m) / C_LIGHT;
}

// EQ-07: Sagnac scale factor K_opt = 2*pi*L*D / (lambda_bar * c) [rad/(rad/s)]
inline double compute_k_opt(double L_m, double D_m, double lambda_bar_m) {
    return (TWO_PI * L_m * D_m) / (lambda_bar_m * C_LIGHT);
}

// EQ-08: Optical Kerr phase (Bergh et al. 1982)
inline double compute_kerr_phase(
    double n2_m2_per_W,
    double L_eff_m,
    double lambda_bar_m,
    double A_eff_m2,
    double kappa_split,
    double P_coil_W,
    double eta_coh
) {
    return ((TWO_PI * n2_m2_per_W * L_eff_m) / (lambda_bar_m * A_eff_m2))
        * (1.0 - 2.0 * kappa_split) * P_coil_W * eta_coh;
}

// EQ-10: Magneto-optic Faraday phase Delta_phi_Faraday = V_Verdet * B_ext * L_loop
inline double compute_faraday_phase(double verdet_rad_per_Tm, double B_ext_T, double eff_loop_m) {
    return verdet_rad_per_Tm * B_ext_T * eff_loop_m;
}

// EQ-11: Instantaneous MIOC phase
inline double compute_mioc_phase(double v_drv, double V_pi_0, double eps_vpi, double gamma_nl) {
    return PI * (1.0 + eps_vpi) * (v_drv / V_pi_0) + gamma_nl * v_drv * v_drv;
}

// EQ-13: Photodiode detected optical power with RAM
inline double compute_pd_power(
    double P_peak_W,
    double alpha_ram,
    double v_drv,
    double visibility_V,
    double delta_phi_nr,
    double delta_phi_mod
) {
    return 0.5 * P_peak_W * (1.0 + alpha_ram * v_drv)
        * (1.0 + visibility_V * std::cos(delta_phi_nr + delta_phi_mod));
}

// EQ-15: Integrated 6-component TIA input current noise variance over [0, B_fast]
inline double compute_tia_noise_variance(
    double P_det_W,
    double responsivity,
    double I_dark,
    double T_tia_K,
    double R_f,
    double delta_nu_eff_Hz,
    double i_n_op,
    double e_n_op,
    double C_tot,
    double C_f,
    double B_fast_Hz
) {
    const double i_pd = responsivity * P_det_W;
    const double s_shot = 2.0 * Q_ELECTRON * (i_pd + I_dark);
    const double s_therm = (4.0 * K_BOLTZMANN * T_tia_K) / R_f;
    const double s_rin = (i_pd * i_pd) / delta_nu_eff_Hz;
    const double s_op = (i_n_op * i_n_op) + (e_n_op * e_n_op) / (R_f * R_f);
    const double s_flat = s_shot + s_therm + s_rin + s_op;
    const double c_sum = C_tot + C_f;
    const double var_cap = (1.0 / 3.0) * (e_n_op * e_n_op)
        * (TWO_PI * TWO_PI) * (c_sum * c_sum) * (B_fast_Hz * B_fast_Hz * B_fast_Hz);
    return s_flat * B_fast_Hz + var_cap;
}

// EQ-16 & EQ-17: Second-order TIA natural frequency, damping ratio, Cf_opt, ts(0.1%)
inline double compute_tia_omega0(double f_gbw_Hz, double R_f, double C_tot, double C_f) {
    return std::sqrt((TWO_PI * f_gbw_Hz) / (R_f * (C_tot + C_f)));
}

inline double compute_tia_zeta(double f_gbw_Hz, double R_f, double C_tot, double C_f) {
    const double two_pi_gbw = TWO_PI * f_gbw_Hz;
    const double omega0 = std::sqrt(two_pi_gbw / (R_f * (C_tot + C_f)));
    return 0.5 * omega0 * (R_f * C_f + 1.0 / two_pi_gbw);
}

inline double compute_tia_cf_opt(double f_gbw_Hz, double R_f, double C_tot) {
    return std::sqrt(C_tot / (TWO_PI * R_f * f_gbw_Hz));
}

inline double compute_tia_ts_0p1pct(double zeta, double omega0) {
    return 6.9 / (zeta * omega0);
}

// EQ-19: ADC quantization step Delta_ADC = 2 * V_FS / 2^{N_ADC}
inline double compute_adc_lsb(double V_fs_adc_V, int N_adc_bits) {
    return (2.0 * V_fs_adc_V) / static_cast<double>(1ULL << N_adc_bits);
}

// EQ-03: Channel sensitivity S_alpha in ADC LSB counts per rad
inline double compute_channel_sensitivity(const IfogConfig& cfg) {
    const double delta_adc = compute_adc_lsb(cfg.V_fs_adc_V, cfg.N_adc_bits);
    const double g_chain = (cfg.G1 * cfg.responsivity_A_per_W * cfg.R_f_ohm) / delta_adc;
    return g_chain * (0.5 * cfg.P_peak_W) * cfg.visibility_V * std::sin(cfg.alpha_rad);
}

// EQ-22: Jury stability criterion (0 < K_tot < 1) & Loop-2 bandwidth separation
inline bool check_jury_stability(double K_tot_1) {
    return (K_tot_1 > 0.0) && (K_tot_1 < 1.0);
}

inline bool check_dual_loop_separation(double K_tot_1, double K_tot_2) {
    return (K_tot_2 >= 0.0) && (K_tot_2 <= 0.1 * K_tot_1 + 1e-15);
}

// EQ-31: Official 6-state anti-periodic instantaneous bias phases psi_0..psi_5
// Yielding exact differential phases [+(pi-a), -(pi+a), +(pi-a), -(pi-a), +(pi+a), -(pi-a)]
// with zero DC drive mean and exact RAM/crosstalk/MIOC-V^2 cancellation at alpha = pi/3.
inline double compute_6state_bias_phase(int state_idx, double alpha_rad) {
    const double a_hi = 0.5 * (PI + alpha_rad);
    const double a_lo = 0.5 * (PI - 3.0 * alpha_rad);
    switch (state_idx) {
        case 0:
            return a_hi;
        case 1:
            return -a_hi;
        case 2:
            return a_lo;
        case 3:
            return -a_hi;
        case 4:
            return a_hi;
        default:
            return -a_lo;
    }
}

// EQ-39: Determine whether a fault injection window is active at simulation time t_s
inline bool is_fault_active(double t_s, double inject_time_s, double duration_s) {
    if (t_s < inject_time_s) {
        return false;
    }
    return (duration_s <= 0.0) || (t_s < (inject_time_s + duration_s));
}

// Evaluate stimulus angular rate Omega_in(t) [rad/s]
inline double eval_stimulus(const IfogConfig& cfg, double t_s) {
    switch (cfg.stimulus_type) {
        case StimulusType::Constant:
            return cfg.omega_const_rad_per_s;
        case StimulusType::Step:
            return (t_s >= cfg.step_time_s) ? cfg.omega_end_rad_per_s : cfg.omega_start_rad_per_s;
        case StimulusType::Ramp: {
            const double ramp_t = (cfg.step_time_s > 0.0) ? cfg.step_time_s : cfg.duration_s;
            const double frac = std::clamp(t_s / ramp_t, 0.0, 1.0);
            return cfg.omega_start_rad_per_s
                + frac * (cfg.omega_end_rad_per_s - cfg.omega_start_rad_per_s);
        }
        case StimulusType::Sine:
            return cfg.omega_const_rad_per_s
                + cfg.sine_amp_rad_per_s * std::sin(TWO_PI * cfg.sine_freq_Hz * t_s);
    }
    return 0.0;  // LCOV_EXCL_LINE
}

// Interpolate Shupe thermal phase LUT at time t_s
inline double interpolate_shupe(const std::vector<ShupeSample>& lut, double t_s) {
    if (lut.empty()) {
        return 0.0;
    }
    if (t_s <= lut.front().t_s) {
        return lut.front().delta_phi_rad;
    }
    if (t_s >= lut.back().t_s) {
        return lut.back().delta_phi_rad;
    }
    const double dt = lut[1].t_s - lut[0].t_s;
    const size_t idx = static_cast<size_t>((t_s - lut.front().t_s) / dt);
    const size_t i0 = std::min(idx, lut.size() - 2);
    const double alpha = (t_s - lut[i0].t_s) / (lut[i0 + 1].t_s - lut[i0].t_s);
    return lut[i0].delta_phi_rad + alpha * (lut[i0 + 1].delta_phi_rad - lut[i0].delta_phi_rad);
}

// Deterministic, portable, fast xoshiro256** PRNG + paired Box-Muller Gaussian generator
class FastRng {
public:
    explicit FastRng(uint64_t seed) {
        // SplitMix64 seeding
        uint64_t z = seed + 0x9E3779B97F4A7C15ULL;
        for (int i = 0; i < 4; ++i) {
            z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL;
            z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL;
            s_[i] = z ^ (z >> 31);
            z += 0x9E3779B97F4A7C15ULL;
        }
        has_spare_ = false;
        spare_ = 0.0;
    }

    inline uint64_t next_u64() {
        const uint64_t result = rotl(s_[1] * 5ULL, 7) * 9ULL;
        const uint64_t t = s_[1] << 17;
        s_[2] ^= s_[0];
        s_[3] ^= s_[1];
        s_[1] ^= s_[2];
        s_[0] ^= s_[3];
        s_[2] ^= t;
        s_[3] = rotl(s_[3], 45);
        return result;
    }

    inline double uniform01() {
        // Strictly in (0, 1) to guarantee finite log() in Box-Muller
        return (static_cast<double>(next_u64() >> 11) + 0.5) * (1.0 / 9007199254740992.0);
    }

    inline double normal01() {
        if (has_spare_) {
            has_spare_ = false;
            return spare_;
        }
        const double u1 = uniform01();
        const double u2 = uniform01();
        const double r = std::sqrt(-2.0 * std::log(u1));
        const double theta = TWO_PI * u2;
        spare_ = r * std::sin(theta);
        has_spare_ = true;
        return r * std::cos(theta);
    }

private:
    static inline uint64_t rotl(uint64_t x, int k) {
        return (x << k) | (x >> (64 - k));
    }

    uint64_t s_[4];
    bool has_spare_;
    double spare_;
};

// 32-bit maximal-length Galois LFSR for deterministic PRBS deadband dither
class PrbsLfsr32 {
public:
    explicit PrbsLfsr32(uint32_t seed)
        : state_(seed == 0u ? 0xACE1u : seed) {}

    inline int next_bit_signed() {
        const uint32_t lsb = state_ & 1u;
        state_ >>= 1;
        if (lsb != 0u) {
            state_ ^= 0x80200003u;  // Primitive polynomial x^32 + x^22 + x^2 + x + 1
        }
        return (lsb != 0u) ? 1 : -1;
    }

private:
    uint32_t state_;
};

// Exact continuous-time ZOH matrix-exponential solver for H(s) = G*w0^2 / (s^2 + 2*z*w0*s + w0^2)
// Eliminates Tustin/Trapezoidal Nyquist oscillation in stiff regimes (w0 * dt > 0.2) while remaining
// analytically exact for underdamped (zeta < 1), critically damped (zeta == 1), and overdamped (zeta > 1).
class ExactSecondOrderLtf {
public:
    ExactSecondOrderLtf()
        : gain_(1.0), phi11_(0.0), phi12_(0.0), phi21_(0.0), phi22_(0.0), x1_(0.0), x2_(0.0) {}

    void configure(double dc_gain, double omega0, double zeta, double dt, double init_y = 0.0) {
        gain_ = dc_gain;
        x1_ = init_y;
        x2_ = 0.0;

        if (zeta < 1.0 - 1e-9) {
            const double sq = std::sqrt(1.0 - zeta * zeta);
            const double wd = omega0 * sq;
            const double e = std::exp(-zeta * omega0 * dt);
            const double c = std::cos(wd * dt);
            const double s = std::sin(wd * dt);
            phi11_ = e * (c + (zeta / sq) * s);
            phi12_ = e * (s / wd);
            phi21_ = -e * (omega0 * omega0 / wd) * s;
            phi22_ = e * (c - (zeta / sq) * s);
        } else if (zeta > 1.0 + 1e-9) {
            const double alpha = omega0 * std::sqrt(zeta * zeta - 1.0);
            const double r1 = -zeta * omega0 + alpha;
            const double r2 = -zeta * omega0 - alpha;
            const double e1 = std::exp(r1 * dt);
            const double e2 = std::exp(r2 * dt);
            const double inv_dr = 1.0 / (r1 - r2);
            phi11_ = (r1 * e2 - r2 * e1) * inv_dr;
            phi12_ = (e1 - e2) * inv_dr;
            phi21_ = r1 * r2 * (e2 - e1) * inv_dr;
            phi22_ = (r1 * e1 - r2 * e2) * inv_dr;
        } else {
            const double e = std::exp(-omega0 * dt);
            phi11_ = e * (1.0 + omega0 * dt);
            phi12_ = e * dt;
            phi21_ = -e * omega0 * omega0 * dt;
            phi22_ = e * (1.0 - omega0 * dt);
        }
    }

    inline double step(double u) {
        const double y_ss = gain_ * u;
        const double dx1 = x1_ - y_ss;
        const double nx1 = y_ss + phi11_ * dx1 + phi12_ * x2_;
        const double nx2 = phi21_ * dx1 + phi22_ * x2_;
        x1_ = nx1;
        x2_ = nx2;
        return x1_;
    }

private:
    double gain_;
    double phi11_;
    double phi12_;
    double phi21_;
    double phi22_;
    double x1_;
    double x2_;
};

// EQ-47 (SPEC-007 §2.2a): Dynamic Sagnac scale factor K_opt(t)
inline double compute_dynamic_k_opt(
    double K_opt_0,
    double dT_coil_K,
    double dT_sld_K,
    double alpha_bobbin_ppm_K,
    double alpha_lambda_pm_K,
    double lambda_bar_m,
    double kappa_back_m_per_W,
    double P_back_W,
    double n_eff_0,
    double dn_dT_per_K
) {
    const double term_bobbin = (alpha_bobbin_ppm_K * 1.0e-6) * dT_coil_K;
    const double term_lambda =
        ((alpha_lambda_pm_K * 1.0e-12) * dT_sld_K + kappa_back_m_per_W * P_back_W) / lambda_bar_m;
    const double term_neff = (dn_dT_per_K / n_eff_0) * dT_coil_K;
    return K_opt_0 * (1.0 + term_bobbin - term_lambda + term_neff);
}

// EQ-49 (SPEC-007 §2.3): O(1) linear interpolation across all 6 channels of shupe_lut.bin v2
inline ShupeLutRecordV2 interpolate_shupe_v2(const std::vector<ShupeLutRecordV2>& lut, double t_s) {
    if (lut.empty()) {
        return ShupeLutRecordV2{};
    }
    if (lut.size() == 1u || t_s <= lut.front().t_s) {
        return lut.front();
    }
    if (t_s >= lut.back().t_s) {
        return lut.back();
    }
    const double dt = lut[1].t_s - lut[0].t_s;
    const size_t idx = static_cast<size_t>((t_s - lut.front().t_s) / dt);
    const size_t i0 = std::min(idx, lut.size() - 2u);
    const double a = (t_s - lut[i0].t_s) / (lut[i0 + 1u].t_s - lut[i0].t_s);
    const ShupeLutRecordV2& r0 = lut[i0];
    const ShupeLutRecordV2& r1 = lut[i0 + 1u];
    ShupeLutRecordV2 out{};
    out.t_s = t_s;
    out.delta_phi_shupe_rad = r0.delta_phi_shupe_rad + a * (r1.delta_phi_shupe_rad - r0.delta_phi_shupe_rad);
    out.delta_phi_stress_rad = r0.delta_phi_stress_rad + a * (r1.delta_phi_stress_rad - r0.delta_phi_stress_rad);
    out.visibility_V_t = r0.visibility_V_t + a * (r1.visibility_V_t - r0.visibility_V_t);
    out.phi_pol_rad_t = r0.phi_pol_rad_t + a * (r1.phi_pol_rad_t - r0.phi_pol_rad_t);
    out.v_pi_V_t = r0.v_pi_V_t + a * (r1.v_pi_V_t - r0.v_pi_V_t);
    out.k_opt_scale_rel_t = r0.k_opt_scale_rel_t + a * (r1.k_opt_scale_rel_t - r0.k_opt_scale_rel_t);
    return out;
}

// EQ-51 (SPEC-007 §2.4b): Capacitive + resistive PCB/package crosstalk current at TIA summing node
inline double compute_capacitive_crosstalk_A(
    double v_dac_now,
    double v_dac_prev,
    double dt_tdf,
    double G_xtalk_S,
    double C_xtalk_F
) {
    return G_xtalk_S * v_dac_now + C_xtalk_F * ((v_dac_now - v_dac_prev) / dt_tdf);
}

// EQ-52 (SPEC-007 §2.5): Coherent cavity facet + Rayleigh backscattering phase RMS [rad]
inline double compute_backscatter_sigma_rad(
    double R_facet_dB,
    double alpha_R_per_m,
    double S_capture,
    double delta_nu_eff_Hz
) {
    const double r_facet = (R_facet_dB > -199.0) ? std::pow(10.0, R_facet_dB / 10.0) : 0.0;
    const double l_coh = C_LIGHT / delta_nu_eff_Hz;
    return 2.0 * std::sqrt(std::max(0.0, r_facet + 0.5 * alpha_R_per_m * S_capture * l_coh));
}

// EQ-50 (SPEC-007 §2.4a): LiNbO3 MIOC electrode cutoff + 2nd-order electro-acoustic step dynamics
class MiocDynamicsFilter {
public:
    MiocDynamicsFilter()
        : active_(false), a_elec_(0.0), v_elec_(0.0), g_ac_(0.0), has_ac_(false), ac_ltf_() {}

    void configure(
        double f_elec_Hz,
        double f_acoustic_Hz,
        double zeta_acoustic,
        double g_acoustic,
        double dt_s,
        double init_v = 0.0
    ) {
        active_ = (f_elec_Hz > 0.0) || (f_acoustic_Hz > 0.0 && g_acoustic > 0.0);
        v_elec_ = init_v;
        a_elec_ = (f_elec_Hz > 0.0) ? std::exp(-TWO_PI * f_elec_Hz * dt_s) : 0.0;
        has_ac_ = (f_acoustic_Hz > 0.0 && g_acoustic > 0.0);
        g_ac_ = has_ac_ ? g_acoustic : 0.0;
        if (has_ac_) {
            ac_ltf_.configure(1.0, TWO_PI * f_acoustic_Hz, zeta_acoustic, dt_s, init_v);
        }
    }

    inline bool active() const { return active_; }

    inline double step(double v_in) {
        if (!active_) {
            return v_in;
        }
        v_elec_ = (a_elec_ > 0.0) ? (a_elec_ * v_elec_ + (1.0 - a_elec_) * v_in) : v_in;
        if (has_ac_) {
            const double v_ac = ac_ltf_.step(v_elec_);
            return v_elec_ + g_ac_ * (v_ac - v_elec_);
        }
        return v_elec_;
    }

private:
    bool active_;
    double a_elec_;
    double v_elec_;
    double g_ac_;
    bool has_ac_;
    ExactSecondOrderLtf ac_ltf_;
};

// Stateless functional helper wrapping MiocDynamicsFilter::step (EQ-50)
inline double step_mioc_dynamics(MiocDynamicsFilter& filt, double v_in) {
    return filt.step(v_in);
}

}  // namespace ifog

#endif  // IFOG_MATH_HPP
