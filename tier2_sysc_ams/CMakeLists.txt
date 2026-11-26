cmake_minimum_required(VERSION 3.16)
project(ifog_vproto_tier2 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

option(IFOG_ENABLE_COVERAGE "Enable GCC gcov instrumentation for 100% coverage verification" OFF)

get_filename_component(IFOG_REPO_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.." ABSOLUTE)
set(IFOG_PROJECT_VERSION "3.0.0")
set(IFOG_FMI_INSTANTIATION_TOKEN "{6e9c4b1a-7f20-4f06-9a5c-000000000006}")

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
find_package(Python3 COMPONENTS Interpreter REQUIRED)

get_filename_component(SYSTEMC_LIB_DIR "${SYSTEMC_LIBRARY}" DIRECTORY)
get_filename_component(SYSTEMC_AMS_LIB_DIR "${SYSTEMC_AMS_LIBRARY}" DIRECTORY)

# Determine FMI 3.0 platform tuple (e.g., x86_64-linux, aarch64-linux, x86_64-windows)
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(x86_64|AMD64|amd64)$")
    set(FMI3_ARCH "x86_64")
elseif(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64|ARM64)$")
    set(FMI3_ARCH "aarch64")
else()
    set(FMI3_ARCH "${CMAKE_SYSTEM_PROCESSOR}")
endif()
if(WIN32)
    set(FMI3_OS "windows")
elseif(APPLE)
    set(FMI3_OS "darwin")
else()
    set(FMI3_OS "linux")
endif()
set(FMI3_PLATFORM_TUPLE "${FMI3_ARCH}-${FMI3_OS}")

message(STATUS "SystemC include:     ${SYSTEMC_INCLUDE_DIR}")
message(STATUS "SystemC library:     ${SYSTEMC_LIBRARY}")
message(STATUS "SystemC-AMS include: ${SYSTEMC_AMS_INCLUDE_DIR}")
message(STATUS "SystemC-AMS library: ${SYSTEMC_AMS_LIBRARY}")
message(STATUS "FMI 3.0 platform:    ${FMI3_PLATFORM_TUPLE}")

set(IFOG_CORE_SOURCES
    src/ifog_config.cpp
    src/optical_envelope_tdf.cpp
    src/pink_noise_tdf.cpp
    src/analog_frontend_tdf.cpp
    src/adc_dac_bridge.cpp
    src/digital_dsp_sc.cpp
    src/imu_3axis.cpp
    src/ifog_top_module.cpp
    src/sim_runner.cpp
)

add_library(ifog_core STATIC ${IFOG_CORE_SOURCES})
set_target_properties(ifog_core PROPERTIES POSITION_INDEPENDENT_CODE ON)
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

# ==============================================================================
# IFOG-SIM-SPEC-006: FMI 3.0 Co-Simulation Shared Library & FMU Packager
# ==============================================================================
add_library(ifog_core_fmu SHARED
    ${IFOG_REPO_ROOT}/fmi_wrapper/src/fmi3_bridge.cpp
)
target_include_directories(ifog_core_fmu
    PRIVATE
        ${IFOG_REPO_ROOT}/fmi_wrapper/include
)
target_compile_definitions(ifog_core_fmu PRIVATE IFOG_FMI_DEFINE_SC_MAIN_STUB)
target_compile_options(ifog_core_fmu PRIVATE -Wall -Wextra -Wpedantic)
if(IFOG_ENABLE_COVERAGE)
    target_compile_options(ifog_core_fmu PRIVATE --coverage -O0 -g)
    target_link_options(ifog_core_fmu PRIVATE --coverage)
endif()
target_link_libraries(ifog_core_fmu PRIVATE ifog_core)
set_target_properties(ifog_core_fmu PROPERTIES
    PREFIX ""
    OUTPUT_NAME "ifog_core"
    LIBRARY_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/binaries/${FMI3_PLATFORM_TUPLE}"
    RUNTIME_OUTPUT_DIRECTORY "${CMAKE_BINARY_DIR}/binaries/${FMI3_PLATFORM_TUPLE}"
    BUILD_RPATH "$ORIGIN;${SYSTEMC_AMS_LIB_DIR};${SYSTEMC_LIB_DIR}"
    INSTALL_RPATH "$ORIGIN;${SYSTEMC_AMS_LIB_DIR};${SYSTEMC_LIB_DIR}"
    BUILD_WITH_INSTALL_RPATH ON
)

# C++ FMI 3.0 bridge unit test executable (verifies 100% line coverage of fmi3_bridge.cpp & IfogTopModule)
add_executable(ifog_fmi_tests
    src/fmi_unit_tests.cpp
    ${IFOG_REPO_ROOT}/fmi_wrapper/src/fmi3_bridge.cpp
)
target_include_directories(ifog_fmi_tests
    PRIVATE
        ${IFOG_REPO_ROOT}/fmi_wrapper/include
)
target_compile_options(ifog_fmi_tests PRIVATE -Wall -Wextra -Wpedantic)
if(IFOG_ENABLE_COVERAGE)
    target_compile_options(ifog_fmi_tests PRIVATE --coverage -O0 -g)
    target_link_options(ifog_fmi_tests PRIVATE --coverage)
endif()
target_link_libraries(ifog_fmi_tests PRIVATE ifog_core)

# Generate FMI 3.0 modelDescription.xml with build timestamp & matching instantiationToken
string(TIMESTAMP IFOG_FMU_BUILD_TIMESTAMP "%Y-%m-%dT%H:%M:%SZ" UTC)
set(IFOG_MODEL_DESC_XML "${CMAKE_BINARY_DIR}/fmu_generated/modelDescription.xml")
configure_file(
    "${IFOG_REPO_ROOT}/fmi_wrapper/modelDescription.xml.in"
    "${IFOG_MODEL_DESC_XML}"
    @ONLY
)

set(IFOG_FMU_RESOURCES_DIR "${CMAKE_BINARY_DIR}/fmu_resources")
set(IFOG_FMU_OUTPUT "${CMAKE_BINARY_DIR}/ifog_core.fmu")

# Package standalone FMI 3.0 Co-Simulation FMU archive (build/ifog_core.fmu)
add_custom_target(package_fmu
    DEPENDS ifog_core_fmu
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${IFOG_FMU_RESOURCES_DIR}"
    COMMAND "${Python3_EXECUTABLE}" "${IFOG_REPO_ROOT}/tier1_offline/jones_spectral.py"
            --cfg "${IFOG_REPO_ROOT}/configs/baseline_1km.json"
            --out "${IFOG_FMU_RESOURCES_DIR}"
    COMMAND "${Python3_EXECUTABLE}" "${IFOG_REPO_ROOT}/tier1_offline/shupe_thermal.py"
            --cfg "${IFOG_REPO_ROOT}/configs/baseline_1km.json"
            --out "${IFOG_FMU_RESOURCES_DIR}"
    COMMAND "${CMAKE_COMMAND}"
            "-DFMU_STAGING_DIR=${CMAKE_BINARY_DIR}/fmu_staging"
            "-DFMU_OUTPUT_PATH=${IFOG_FMU_OUTPUT}"
            "-DFMU_XML_PATH=${IFOG_MODEL_DESC_XML}"
            "-DFMU_BINARY_PATH=$<TARGET_FILE:ifog_core_fmu>"
            "-DFMU_PLATFORM_DIR=${FMI3_PLATFORM_TUPLE}"
            "-DFMU_RES_PHYS=${IFOG_FMU_RESOURCES_DIR}/phys_params.json"
            "-DFMU_RES_SHUPE=${IFOG_FMU_RESOURCES_DIR}/shupe_lut.bin"
            "-DFMU_RES_CFG=${IFOG_REPO_ROOT}/configs/baseline_1km.json"
            -P "${IFOG_REPO_ROOT}/fmi_wrapper/package_fmu.cmake"
    WORKING_DIRECTORY "${IFOG_REPO_ROOT}"
    COMMENT "Packaging standalone FMI 3.0 Co-Simulation FMU -> ${IFOG_FMU_OUTPUT}"
)

enable_testing()
add_test(NAME ifog_cpp_unit_tests COMMAND ifog_cpp_tests)
