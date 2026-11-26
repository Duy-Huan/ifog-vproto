cmake_minimum_required(VERSION 3.16)
project(ifog_vproto LANGUAGES CXX)

# Forward top-level CMake builds to Tier 2 SystemC-AMS Core & FMI 3.0 FMU packager
add_subdirectory(tier2_sysc_ams)
