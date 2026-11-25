#include "pink_noise_tdf.hpp"
#include <cmath>

namespace ifog {

FivePolePinkFilter::FivePolePinkFilter(
    double f_min_Hz,
    double f_max_Hz,
    double dt_s,
    double sigma
)
    : a_{}, b_{}, state_{}, scale_(sigma / std::sqrt(static_cast<double>(NUM_POLES))) {
    const double ratio = f_max_Hz / f_min_Hz;
    for (int p = 0; p < NUM_POLES; ++p) {
        const double frac = static_cast<double>(p) / static_cast<double>(NUM_POLES - 1);
        const double fp = f_min_Hz * std::pow(ratio, frac);
        const double ap = std::exp(-TWO_PI * fp * dt_s);
        a_[static_cast<size_t>(p)] = ap;
        b_[static_cast<size_t>(p)] = std::sqrt(std::max(0.0, 1.0 - ap * ap));
        state_[static_cast<size_t>(p)] = 0.0;
    }
}

double FivePolePinkFilter::step(FastRng& rng) {
    double sum = 0.0;
    for (int p = 0; p < NUM_POLES; ++p) {
        const size_t idx = static_cast<size_t>(p);
        state_[idx] = a_[idx] * state_[idx] + b_[idx] * rng.normal01();
        sum += state_[idx];
    }
    return scale_ * sum;
}

PinkNoise_TDF::PinkNoise_TDF(sc_core::sc_module_name name, const IfogConfig& cfg)
    : sca_tdf::sca_module(name),
      pink_tia_out("pink_tia_out"),
      pink_dac_out("pink_dac_out"),
      pink_xtalk_out("pink_xtalk_out"),
      cfg_(cfg),
      rng_(cfg.seed ^ 0x517CC1B727220A95ULL),
      filter_tia_(cfg.pink_f_min_Hz, cfg.pink_f_max_Hz, cfg.tau_s, cfg.sigma_pink_tia_V),
      filter_dac_(cfg.pink_f_min_Hz, cfg.pink_f_max_Hz, cfg.tau_s, cfg.sigma_pink_dac_rel),
      filter_xtalk_(cfg.pink_f_min_Hz, cfg.pink_f_max_Hz, cfg.tau_s, cfg.sigma_pink_xtalk_rel),
      step_idx_(0) {}

void PinkNoise_TDF::set_attributes() {
    pink_tia_out.set_rate(1);
    pink_dac_out.set_rate(1);
    pink_xtalk_out.set_rate(1);
    set_timestep(sca_core::sca_time(cfg_.tau_s, sc_core::SC_SEC));
}

void PinkNoise_TDF::processing() {
    double n_tia = 0.0;
    double n_dac = 0.0;
    double n_xtalk = 0.0;

    if (cfg_.en_pink_noise) {
        n_tia = filter_tia_.step(rng_);
        n_dac = filter_dac_.step(rng_);
        n_xtalk = filter_xtalk_.step(rng_);
    }

    if (cfg_.sine_inject_target != SineInjectTarget::None && cfg_.sine_inject_amp != 0.0) {
        const double t = static_cast<double>(step_idx_) * cfg_.tau_s;
        const double tone = cfg_.sine_inject_amp * std::sin(TWO_PI * cfg_.sine_inject_freq_Hz * t);
        if (cfg_.sine_inject_target == SineInjectTarget::Tia) {
            n_tia += tone;
        } else if (cfg_.sine_inject_target == SineInjectTarget::Dac) {
            n_dac += tone;
        } else {
            n_xtalk += tone;
        }
    }

    pink_tia_out.write(n_tia);
    pink_dac_out.write(n_dac);
    pink_xtalk_out.write(n_xtalk);
    ++step_idx_;
}

}  // namespace ifog
