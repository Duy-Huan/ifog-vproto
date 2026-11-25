#ifndef ADC_DAC_BRIDGE_HPP
#define ADC_DAC_BRIDGE_HPP

#include <systemc-ams.h>
#include "ifog_math.hpp"
#include "ifog_types.hpp"
#include "micro_trace.hpp"

namespace ifog {

// ADC_Bridge_TDF: rate=K -> rate=1 DE, ADC blanking window [k_start, k_end] & N_ADC-bit quantizer (EQ-19)
SCA_TDF_MODULE(ADC_Bridge_TDF) {
public:
    sca_tdf::sca_in<double> v_adc_in;
    sca_tdf::sca_de::sca_out<double> adc_code_out;

    ADC_Bridge_TDF(
        sc_core::sc_module_name name,
        const IfogConfig& cfg,
        MicroTraceCollector* micro_trace = nullptr
    );

    void set_attributes() override;
    void processing() override;

    double eta_blanking() const { return eta_blanking_; }

private:
    IfogConfig cfg_;
    int win_start_;
    int win_end_;
    int win_len_;
    double eta_blanking_;
    double delta_adc_;
    int64_t code_min_;
    int64_t code_max_;
    uint64_t cluster_idx_;
    MicroTraceCollector* micro_trace_;
};

// DAC_Driver_TDF: rate=1 DE (with set_delay(1) breaking algebraic loop) -> rate=K TDF
// Models DAC reference 1/f drift, 2nd-order driver LTF, and dV_drv/dt crosstalk source.
SCA_TDF_MODULE(DAC_Driver_TDF) {
public:
    sca_tdf::sca_de::sca_in<double> dac_code_in;
    sca_tdf::sca_in<double> pink_dac_in;
    sca_tdf::sca_out<double> v_drv_out;
    sca_tdf::sca_out<double> dv_drv_dt_out;

    DAC_Driver_TDF(
        sc_core::sc_module_name name,
        const IfogConfig& cfg,
        double init_dac_code,
        double init_v_drv
    );

    void set_attributes() override;
    void initialize() override;
    void processing() override;

private:
    IfogConfig cfg_;
    double dt_fast_;
    double inv_dt_fast_;
    double dac_lsb_scale_;
    double init_dac_code_;
    double init_v_drv_;
    double v_drv_prev_;
    bool use_sca_ltf_;
    sca_tdf::sca_ltf_nd ltf_drv_;
    sca_util::sca_vector<double> num_drv_;
    sca_util::sca_vector<double> den_drv_;
    sca_util::sca_vector<double> state_drv_;
    ExactSecondOrderLtf exact_ltf_drv_;
};

}  // namespace ifog

#endif  // ADC_DAC_BRIDGE_HPP
