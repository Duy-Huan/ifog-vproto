# Cross-platform CMake script to assemble a valid FMI 3.0 Co-Simulation FMU archive (ZIP -> .fmu)
# Expected -D variables:
#   FMU_STAGING_DIR   : Temporary staging folder
#   FMU_OUTPUT_PATH   : Destination .fmu path (e.g., build/ifog_core.fmu)
#   FMU_XML_PATH      : Configured modelDescription.xml path
#   FMU_BINARY_PATH   : Compiled shared library path (ifog_core.so / ifog_core.dll)
#   FMU_PLATFORM_DIR  : FMI 3.0 platform tuple (e.g., x86_64-linux, aarch64-linux, x86_64-windows)
#   FMU_RES_PHYS      : resources/phys_params.json path
#   FMU_RES_SHUPE     : resources/shupe_lut.bin path
#   FMU_RES_CFG       : resources/baseline_cfg.json path

foreach(req_var
    FMU_STAGING_DIR
    FMU_OUTPUT_PATH
    FMU_XML_PATH
    FMU_BINARY_PATH
    FMU_PLATFORM_DIR
    FMU_RES_PHYS
    FMU_RES_SHUPE
    FMU_RES_CFG)
    if(NOT DEFINED ${req_var} OR "${${req_var}}" STREQUAL "")
        message(FATAL_ERROR "package_fmu.cmake missing required variable: ${req_var}")
    endif()
endforeach()

file(REMOVE_RECURSE "${FMU_STAGING_DIR}")
file(MAKE_DIRECTORY
    "${FMU_STAGING_DIR}/binaries/${FMU_PLATFORM_DIR}"
    "${FMU_STAGING_DIR}/resources"
)

get_filename_component(FMU_BIN_NAME "${FMU_BINARY_PATH}" NAME)

file(COPY_FILE "${FMU_XML_PATH}" "${FMU_STAGING_DIR}/modelDescription.xml")
file(COPY_FILE "${FMU_BINARY_PATH}" "${FMU_STAGING_DIR}/binaries/${FMU_PLATFORM_DIR}/${FMU_BIN_NAME}")
file(COPY_FILE "${FMU_RES_PHYS}" "${FMU_STAGING_DIR}/resources/phys_params.json")
file(COPY_FILE "${FMU_RES_SHUPE}" "${FMU_STAGING_DIR}/resources/shupe_lut.bin")
file(COPY_FILE "${FMU_RES_CFG}" "${FMU_STAGING_DIR}/resources/baseline_cfg.json")

get_filename_component(FMU_OUT_DIR "${FMU_OUTPUT_PATH}" DIRECTORY)
file(MAKE_DIRECTORY "${FMU_OUT_DIR}")
file(REMOVE "${FMU_OUTPUT_PATH}")

execute_process(
    COMMAND "${CMAKE_COMMAND}" -E tar cf "${FMU_OUTPUT_PATH}" --format=zip
            modelDescription.xml binaries resources
    WORKING_DIRECTORY "${FMU_STAGING_DIR}"
    RESULT_VARIABLE zip_rc
)
if(NOT zip_rc EQUAL 0)
    message(FATAL_ERROR "Failed to create FMU ZIP archive at ${FMU_OUTPUT_PATH} (rc=${zip_rc})")
endif()

message(STATUS "[package_fmu] Packaged FMI 3.0 FMU -> ${FMU_OUTPUT_PATH}")
