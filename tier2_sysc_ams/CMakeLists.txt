cmake_minimum_required(VERSION 3.16)
project(ifog_vproto_tier2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(IFOG_ENABLE_COVERAGE "Enable GCC gcov instrumentation for 100% coverage verification" OFF)

# Locate SystemC 2.3.4 (SYSTEMC_HOME, portable ifog-env prefix, or distro libsystemc-dev)
set(SYSTEMC_HINTS "")
if(DEFINED ENV{SYSTEMC_HOME} AND EXISTS "$ENV{SYSTEMC_HOME}/include/systemc.h")
    list(APPEND SYSTEMC_HINTS "$ENV{SYSTEMC_HOME}")
endif()
if(DEFINED ENV{IFOG_ENV_PREFIX} AND EXISTS "$ENV{IFOG_ENV_PREFIX}/systemc/include/systemc.h")
    list(APPEND SYSTEMC_HINTS "$ENV{IFOG_ENV_PREFIX}/systemc")
endif()
list(APPEND SYSTEMC_HINTS
    "$ENV{HOME}/.local/ifog-env/systemc"
    "$ENV{HOME}/.local/systemc"
    "/opt/ifog-env/systemc"
    "/usr/local/systemc"
    "/usr"
)

find_path(SYSTEMC_INCLUDE_DIR
    NAMES systemc.h
    HINTS ${SYSTEMC_HINTS}
    PATH_SUFFIXES include
    REQUIRED
)
find_library(SYSTEMC_LIBRARY
    NAMES systemc
    HINTS ${SYSTEMC_HINTS}
    PATH_SUFFIXES lib lib64 lib-linux64 lib/x86_64-linux-gnu lib/aarch64-linux-gnu
    REQUIRED
)

# Locate SystemC-AMS PoC 2.3.4 (SYSTEMC_AMS_HOME, portable ifog-env prefix, or standard paths)
set(SYSTEMC_AMS_HINTS "")
if(DEFINED ENV{SYSTEMC_AMS_HOME})
    list(APPEND SYSTEMC_AMS_HINTS "$ENV{SYSTEMC_AMS_HOME}")
endif()
if(DEFINED ENV{IFOG_ENV_PREFIX})
    list(APPEND SYSTEMC_AMS_HINTS "$ENV{IFOG_ENV_PREFIX}/systemc-ams")
endif()
list(APPEND SYSTEMC_AMS_HINTS
    "$ENV{HOME}/.local/ifog-env/systemc-ams"
    "$ENV{HOME}/.local/systemc-ams"
    "/opt/ifog-env/systemc-ams"
    "/usr/local/systemc-ams"
    "/usr"
)

find_path(SYSTEMC_AMS_INCLUDE_DIR
    NAMES systemc-ams.h
    HINTS ${SYSTEMC_AMS_HINTS}
    PATH_SUFFIXES include
    REQUIRED
)
find_library(SYSTEMC_AMS_LIBRARY
    NAMES systemc-ams
    HINTS ${SYSTEMC_AMS_HINTS}
    PATH_SUFFIXES lib lib64 lib-linux64 lib/x86_64-linux-gnu lib/aarch64-linux-gnu
    REQUIRED
)

# Locate nlohmann_json (supports portable source install under ifog-env or distro package)
list(APPEND CMAKE_PREFIX_PATH
    "$ENV{IFOG_ENV_PREFIX}/nlohmann_json"
    "$ENV{HOME}/.local/ifog-env/nlohmann_json"
    "/opt/ifog-env/nlohmann_json"
)
find_package(nlohmann_json 3.2.0 REQUIRED)

message(STATUS "SystemC include:     ${SYSTEMC_INCLUDE_DIR}")
message(STATUS "SystemC library:     ${SYSTEMC_LIBRARY}")
message(STATUS "SystemC-AMS include: ${SYSTEMC_AMS_INCLUDE_DIR}")
message(STATUS "SystemC-AMS library: ${SYSTEMC_AMS_LIBRARY}")

set(IFOG_CORE_SOURCES
    src/ifog_config.cpp
    src/optical_envelope_tdf.cpp
    src/pink_noise_tdf.cpp
    src/analog_frontend_tdf.cpp
    src/adc_dac_bridge.cpp
    src/digital_dsp_sc.cpp
    src/sim_runner.cpp
)

add_library(ifog_core STATIC ${IFOG_CORE_SOURCES})
target_include_directories(ifog_core
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
        ${SYSTEMC_INCLUDE_DIR}
        ${SYSTEMC_AMS_INCLUDE_DIR}
)
target_compile_definitions(ifog_core PUBLIC SC_CPLUSPLUS=201703L)
target_compile_options(ifog_core PRIVATE -Wall -Wextra -Wpedantic)
if(IFOG_ENABLE_COVERAGE)
    target_compile_options(ifog_core PUBLIC --coverage -O0 -g)
    target_link_options(ifog_core PUBLIC --coverage)
endif()
target_link_libraries(ifog_core
    PUBLIC
        ${SYSTEMC_AMS_LIBRARY}
        ${SYSTEMC_LIBRARY}
        nlohmann_json::nlohmann_json
        pthread
        m
)

add_executable(ifog_sim src/main.cpp)
target_compile_options(ifog_sim PRIVATE -Wall -Wextra -Wpedantic)
if(IFOG_ENABLE_COVERAGE)
    target_compile_options(ifog_sim PRIVATE --coverage -O0 -g)
    target_link_options(ifog_sim PRIVATE --coverage)
endif()
target_link_libraries(ifog_sim PRIVATE ifog_core)

# C++ unit test executable (fast deterministic module & formula tests for 100% C++ coverage)
add_executable(ifog_cpp_tests src/cpp_unit_tests.cpp)
target_compile_options(ifog_cpp_tests PRIVATE -Wall -Wextra -Wpedantic)
if(IFOG_ENABLE_COVERAGE)
    target_compile_options(ifog_cpp_tests PRIVATE --coverage -O0 -g)
    target_link_options(ifog_cpp_tests PRIVATE --coverage)
endif()
target_link_libraries(ifog_cpp_tests PRIVATE ifog_core)

enable_testing()
add_test(NAME ifog_cpp_unit_tests COMMAND ifog_cpp_tests)
