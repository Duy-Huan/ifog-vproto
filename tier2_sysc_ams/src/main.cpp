#include <exception>
#include <iostream>
#include <systemc.h>
#include "ifog_config.hpp"
#include "sim_runner.hpp"

int sc_main(int argc, char* argv[]) {
    try {
        const ifog::CliArgs args = ifog::parse_cli_args(argc, argv);
        ifog::IfogConfig cfg = ifog::load_ifog_config(args.cfg_path, args.phys_path, args.shupe_path);
        if (args.override_duration_s > 0.0) {
            cfg.duration_s = args.override_duration_s;
        }
        if (args.override_dump_micro_ms >= 0.0) {
            cfg.dump_micro_ms = args.override_dump_micro_ms;
        }
        const ifog::SimSummary summary = ifog::run_ifog_simulation(cfg, args.out_dir);
        std::cout << "[ifog_sim] Completed " << summary.total_tau_steps
                  << " tau steps, wrote " << summary.total_records_written
                  << " records, final_omega_out=" << summary.final_omega_out_rad_per_s
                  << " rad/s, final_eps_vpi_eff=" << summary.final_eps_vpi_eff << "\n";
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "[ifog_sim] ERROR: " << ex.what() << "\n";
        return 1;
    }
}
