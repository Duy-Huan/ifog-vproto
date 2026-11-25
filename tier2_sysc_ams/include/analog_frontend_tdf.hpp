#ifndef ANALOG_FRONTEND_TDF_HPP
#define ANALOG_FRONTEND_TDF_HPP

#include <systemc-ams.h>
#include "ifog_math.hpp"
#include "ifog_types.hpp"
#include "micro_trace.hpp"

namespace ifog {

// AnalogFrontEnd_TDF: 6-component noise, capacitive/resistive crosstalk, 2nd-order TIA LTF
// (SystemC-AMS sca_ltf_nd in non-stiff regime & exact ZOH matrix-exponential in stiff regime),
// 1/f offset, and cubic polynomial nonlinearity + clipping (EQ-14..EQ-18).
SCA_TDF_MODULE(AnalogFrontEnd_TDF) {
public:
    sca_tdf::sca_in<double> p_det_in;
    sca_tdf::sca_in<double> v_drv_in;
    sca_tdf::sca_in<double> dv_drv_dt_in;
    sca_tdf::sca_in<double> pink_tia_in;
    sca_tdf::sca_in<double> pink_xtalk_in;
    sca_tdf::sca_out<double> v_adc_out;

    AnalogFrontEnd_TDF(
        sc_core::sc_module_name name,
        const IfogConfig& cfg,
        MicroTraceCollector* micro_trace = nullptr
    );

    void set_attributes() override;
    void initialize() override;
    void processing() override;

    uint64_t clip_count() const { return clip_count_; }

private:
    IfogConfig cfg_;
    double dt_fast_;
    double B_fast_Hz_;
    double c_xtalk_eff_;
    double k_xtalk_eff_;
    double omega0_;
    double zeta_;
    bool use_sca_ltf_;
    // Hoisted noise variance constants (P_det-independent terms of EQ-15)
    double var_fixed_A2_;
    double shot_coeff_;
    double rin_coeff_;
    sca_tdf::sca_ltf_nd ltf_tia_;
    sca_util::sca_vector<double> num_tia_;
    sca_util::sca_vector<double> den_tia_;
    sca_util::sca_vector<double> state_tia_;
    ExactSecondOrderLtf exact_ltf_tia_;
    FastRng rng_;
    uint64_t cluster_idx_;
    uint64_t clip_count_;
    MicroTraceCollector* micro_trace_;
};

}  // namespace ifog

#endif  // ANALOG_FRONTEND_TDF_HPP
