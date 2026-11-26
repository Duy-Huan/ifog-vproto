#ifndef OPTICAL_ENVELOPE_TDF_HPP
#define OPTICAL_ENVELOPE_TDF_HPP

#include <systemc-ams.h>
#include <vector>
#include "ifog_math.hpp"
#include "ifog_types.hpp"
#include "micro_trace.hpp"

namespace ifog {

// OpticalEnvelope_TDF: 64-bit optical interferometer envelope model (EQ-06..EQ-13, EQ-36..EQ-39, EQ-47..EQ-52)
// Rate = K micro-samples per transit time tau; internal K-sample ring buffer models coil delay tau.
SCA_TDF_MODULE(OpticalEnvelope_TDF) {
public:
    sca_tdf::sca_in<double> v_drv_in;
    sca_tdf::sca_in<double> p_scale_in;
    sca_tdf::sca_out<double> p_det_out;

    OpticalEnvelope_TDF(
        sc_core::sc_module_name name,
        const IfogConfig& cfg,
        double init_v_drv,
        MicroTraceCollector* micro_trace = nullptr,
        const ExternalDriveState* ext_drive = nullptr
    );

    void set_attributes() override;
    void initialize() override;
    void processing() override;

private:
    IfogConfig cfg_;
    double dt_fast_;
    double init_v_drv_;
    double eps_vpi_eff_;
    double gamma_nl_eff_;
    double alpha_ram_eff_;
    double phi_kerr_eff_;
    double phi_faraday_dc_;
    uint64_t sample_idx_;
    int ring_pos_;
    std::vector<double> phi_mioc_ring_;
    MiocDynamicsFilter mioc_dyn_;
    FastRng back_rng_;
    double ou_phi_;
    double ou_sigma_step_;
    double theta_env_;
    MicroTraceCollector* micro_trace_;
    const ExternalDriveState* ext_drive_;
};

}  // namespace ifog

#endif  // OPTICAL_ENVELOPE_TDF_HPP
