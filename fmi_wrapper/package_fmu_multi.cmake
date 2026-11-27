# Cross-platform CMake packager for FMI 3.0.2 Multi-Instance + Source-Code FMU (build/ifog_core_multi.fmu)
foreach(req_var
    FMU_STAGING_DIR
    FMU_OUTPUT_PATH
    FMU_XML_PATH
    FMU_BUILD_DESC_XML
    FMU_BINARY_PATH
    FMU_PLATFORM_DIR
    FMU_SOURCE_CPP
    FMU_INCLUDE_FMI3_DIR)
    if(NOT DEFINED ${req_var} OR "${${req_var}}" STREQUAL "")
        message(FATAL_ERROR "package_fmu_multi.cmake missing required variable: ${req_var}")
    endif()
endforeach()

file(REMOVE_RECURSE "${FMU_STAGING_DIR}")
file(MAKE_DIRECTORY
    "${FMU_STAGING_DIR}/binaries/${FMU_PLATFORM_DIR}"
    "${FMU_STAGING_DIR}/sources/fmi3"
)

get_filename_component(FMU_BIN_NAME "${FMU_BINARY_PATH}" NAME)
file(COPY_FILE "${FMU_XML_PATH}" "${FMU_STAGING_DIR}/modelDescription.xml")
file(COPY_FILE "${FMU_BINARY_PATH}" "${FMU_STAGING_DIR}/binaries/${FMU_PLATFORM_DIR}/${FMU_BIN_NAME}")
file(COPY_FILE "${FMU_BUILD_DESC_XML}" "${FMU_STAGING_DIR}/sources/buildDescription.xml")
file(COPY_FILE "${FMU_SOURCE_CPP}" "${FMU_STAGING_DIR}/sources/fmi3_multi_bridge.cpp")
file(COPY "${FMU_INCLUDE_FMI3_DIR}/" DESTINATION "${FMU_STAGING_DIR}/sources/fmi3/")

get_filename_component(FMU_OUT_DIR "${FMU_OUTPUT_PATH}" DIRECTORY)
file(MAKE_DIRECTORY "${FMU_OUT_DIR}")
file(REMOVE "${FMU_OUTPUT_PATH}")

execute_process(
    COMMAND "${CMAKE_COMMAND}" -E tar cf "${FMU_OUTPUT_PATH}" --format=zip
            modelDescription.xml binaries sources
    WORKING_DIRECTORY "${FMU_STAGING_DIR}"
    RESULT_VARIABLE zip_rc
)
if(NOT zip_rc EQUAL 0)
    message(FATAL_ERROR "Failed to create Multi-Instance FMU ZIP at ${FMU_OUTPUT_PATH} (rc=${zip_rc})")
endif()

message(STATUS "[package_fmu_multi] Packaged FMI 3.0 Multi-Instance Source-Code FMU -> ${FMU_OUTPUT_PATH}")
