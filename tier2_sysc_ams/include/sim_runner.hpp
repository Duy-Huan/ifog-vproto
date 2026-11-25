#ifndef SIM_RUNNER_HPP
#define SIM_RUNNER_HPP

#include <string>
#include "ifog_types.hpp"

namespace ifog {

// Assemble full SystemC-AMS + SystemC DE closed-loop IFOG topology and run for cfg.duration_s
SimSummary run_ifog_simulation(const IfogConfig& cfg, const std::string& out_dir);

// Parse CLI arguments (--phys, --cfg, --out, optional --shupe, --dump-micro-ms, --duration-s)
struct CliArgs {
    std::string phys_path;
    std::string cfg_path;
    std::string out_dir;
    std::string shupe_path;
    double override_duration_s = -1.0;
    double override_dump_micro_ms = -1.0;
};

CliArgs parse_cli_args(int argc, char* argv[]);

}  // namespace ifog

#endif  // SIM_RUNNER_HPP
