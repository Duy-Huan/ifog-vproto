#ifndef IFOG_CONFIG_HPP
#define IFOG_CONFIG_HPP

#include <string>
#include "ifog_types.hpp"

namespace ifog {

// Load and validate IfogConfig from JSON config file + Tier-1 phys_params.json (+ optional shupe_lut.bin)
IfogConfig load_ifog_config(
    const std::string& cfg_path,
    const std::string& phys_path,
    const std::string& shupe_lut_path = ""
);

// Load binary shupe_lut.bin written by tier1_offline/shupe_thermal.py
std::vector<ShupeSample> load_shupe_lut(const std::string& lut_path);

// Validate stability & physical bounds (Rule 11 fail-closed)
void validate_ifog_config(const IfogConfig& cfg);

// Write run_summary.json after simulation
void write_sim_summary_json(const std::string& out_path, const SimSummary& summary);

}  // namespace ifog

#endif  // IFOG_CONFIG_HPP
