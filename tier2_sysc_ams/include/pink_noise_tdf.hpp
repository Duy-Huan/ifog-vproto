#ifndef PINK_NOISE_TDF_HPP
#define PINK_NOISE_TDF_HPP

#include <array>
#include <systemc-ams.h>
#include "ifog_math.hpp"
#include "ifog_types.hpp"

namespace ifog {

// 5-pole IIR Lorentzian superposition 1/f flicker generator (exact -10 dB/dec on [f_min, f_max])
class FivePolePinkFilter {
public:
    FivePolePinkFilter(double f_min_Hz, double f_max_Hz, double dt_s, double sigma);

    double step(FastRng& rng);

private:
    static constexpr int NUM_POLES = 5;
    std::array<double, NUM_POLES> a_;
    std::array<double, NUM_POLES> b_;
    std::array<double, NUM_POLES> state_;
    double scale_;
};

// PinkNoise_TDF: rate=1 per tau (internal ZOH) generating n_1f_TIA, n_1f_DAC, n_1f_xtalk
// plus optional deterministic sinusoidal test tone injection for EQ-27 K-matrix extraction.
SCA_TDF_MODULE(PinkNoise_TDF) {
public:
    sca_tdf::sca_out<double> pink_tia_out;
    sca_tdf::sca_out<double> pink_dac_out;
    sca_tdf::sca_out<double> pink_xtalk_out;

    PinkNoise_TDF(sc_core::sc_module_name name, const IfogConfig& cfg);

    void set_attributes() override;
    void processing() override;

private:
    IfogConfig cfg_;
    FastRng rng_;
    FivePolePinkFilter filter_tia_;
    FivePolePinkFilter filter_dac_;
    FivePolePinkFilter filter_xtalk_;
    uint64_t step_idx_;
};

}  // namespace ifog

#endif  // PINK_NOISE_TDF_HPP
