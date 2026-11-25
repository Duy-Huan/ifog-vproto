#ifndef IMU_3AXIS_HPP
#define IMU_3AXIS_HPP

#include <string>
#include <systemc-ams.h>
#include "ifog_types.hpp"

namespace ifog {

// NominalBus_TDF: Ideal uncoupled power & optical bus for single-axis IFOG runs.
SCA_TDF_MODULE(NominalBus_TDF) {
public:
    sca_tdf::sca_out<double> p_scale_out;
    sca_tdf::sca_out<double> rail_droop_fast_out;
    sca_tdf::sca_out<double> rail_droop_tau_out;

    NominalBus_TDF(sc_core::sc_module_name name, const IfogConfig& cfg);

    void set_attributes() override;
    void processing() override;

private:
    IfogConfig cfg_;
};

// SharedPowerBus_TDF: Real 3-axis IMU shared SLD back-reflection & shared FPGA/DAC rail droop (EQ-36).
SCA_TDF_MODULE(SharedPowerBus_TDF) {
public:
    sca_tdf::sca_in<double> v_drv_x_in;
    sca_tdf::sca_in<double> dv_dt_x_in;
    sca_tdf::sca_in<double> v_drv_y_in;
    sca_tdf::sca_in<double> dv_dt_y_in;
    sca_tdf::sca_in<double> v_drv_z_in;
    sca_tdf::sca_in<double> dv_dt_z_in;

    sca_tdf::sca_out<double> p_scale_x_out;
    sca_tdf::sca_out<double> p_scale_y_out;
    sca_tdf::sca_out<double> p_scale_z_out;
    sca_tdf::sca_out<double> rail_droop_fast_out;
    sca_tdf::sca_out<double> rail_droop_tau_out;

    SharedPowerBus_TDF(sc_core::sc_module_name name, const IfogConfig& cfg);

    void set_attributes() override;
    void processing() override;

    double peak_rail_droop_V() const { return peak_rail_droop_V_; }

private:
    IfogConfig cfg_;
    double inv_v_pi_;
    double inv_r_load_;
    double peak_rail_droop_V_;
};

// Assemble and execute a concurrent 3-axis (X, Y, Z) SystemC-AMS IMU simulation sharing one SLD & power rail.
Imu3AxisSummary run_ifog_imu3axis_simulation(const IfogConfig& base_cfg, const std::string& out_dir);

// Write imu_3axis_summary.json
void write_imu_3axis_summary_json(const std::string& out_path, const Imu3AxisSummary& summary);

}  // namespace ifog

#endif  // IMU_3AXIS_HPP
