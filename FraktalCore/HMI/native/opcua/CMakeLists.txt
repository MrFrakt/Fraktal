cmake_minimum_required(VERSION 3.14)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  project(fraktal_opcua LANGUAGES C CXX)
endif()

# The Linux gateway links the pinned static Mbed TLS archives into this shared
# bridge, so every contributing object must be position independent.
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

set(ENABLE_PROGRAMS OFF CACHE BOOL "" FORCE)
set(ENABLE_TESTING OFF CACHE BOOL "" FORCE)
set(MBEDTLS_FATAL_WARNINGS OFF CACHE BOOL "" FORCE)
set(USE_SHARED_MBEDTLS_LIBRARY OFF CACHE BOOL "" FORCE)
set(USE_STATIC_MBEDTLS_LIBRARY ON CACHE BOOL "" FORCE)

set(MBEDTLS_RELEASE "mbedtls-3.6.6")
set(MBEDTLS_ARCHIVE "${CMAKE_CURRENT_SOURCE_DIR}/third_party/${MBEDTLS_RELEASE}.tar.bz2")
set(MBEDTLS_SOURCE_DIR "${CMAKE_CURRENT_BINARY_DIR}/third_party/${MBEDTLS_RELEASE}")

# Keep the upstream archive as the only vendored representation. Fresh checkouts
# unpack it into the build tree, using CMake alone on both Windows and Linux.
file(STRINGS "${CMAKE_CURRENT_SOURCE_DIR}/third_party/${MBEDTLS_RELEASE}-sha256sum.txt"
  MBEDTLS_CHECKSUM_LINE LIMIT_COUNT 1)
string(REGEX MATCH "^[0-9a-f]+" MBEDTLS_EXPECTED_SHA256 "${MBEDTLS_CHECKSUM_LINE}")
file(SHA256 "${MBEDTLS_ARCHIVE}" MBEDTLS_ACTUAL_SHA256)
if(NOT MBEDTLS_ACTUAL_SHA256 STREQUAL MBEDTLS_EXPECTED_SHA256)
  message(FATAL_ERROR "${MBEDTLS_RELEASE}: bundled archive SHA256 mismatch")
endif()

if(NOT EXISTS "${MBEDTLS_SOURCE_DIR}/.fraktal-extracted")
  file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/third_party")
  message(STATUS "Extracting bundled ${MBEDTLS_RELEASE}")
  execute_process(
    COMMAND "${CMAKE_COMMAND}" -E tar xjf "${MBEDTLS_ARCHIVE}"
    WORKING_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/third_party"
    RESULT_VARIABLE MBEDTLS_EXTRACT_RESULT
    ERROR_VARIABLE MBEDTLS_EXTRACT_ERROR)
  if(NOT MBEDTLS_EXTRACT_RESULT EQUAL 0 OR
      NOT EXISTS "${MBEDTLS_SOURCE_DIR}/CMakeLists.txt")
    message(FATAL_ERROR "${MBEDTLS_RELEASE}: extraction failed: ${MBEDTLS_EXTRACT_ERROR}")
  endif()
  file(WRITE "${MBEDTLS_SOURCE_DIR}/.fraktal-extracted" "${MBEDTLS_ACTUAL_SHA256}\n")
endif()

if(NOT TARGET mbedtls)
  add_subdirectory(
    "${MBEDTLS_SOURCE_DIR}"
    "${CMAKE_CURRENT_BINARY_DIR}/mbedtls"
    EXCLUDE_FROM_ALL)
endif()

add_library(fraktal_opcua SHARED
  "${CMAKE_CURRENT_SOURCE_DIR}/fraktal_opcua_bridge.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/third_party/open62541/open62541.c")
target_include_directories(fraktal_opcua PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/third_party/open62541"
  "${MBEDTLS_SOURCE_DIR}/include")
target_compile_features(fraktal_opcua PRIVATE cxx_std_17)
target_link_libraries(fraktal_opcua PRIVATE mbedtls mbedx509 mbedcrypto)

if(MSVC)
  target_compile_definitions(fraktal_opcua PRIVATE _CRT_SECURE_NO_WARNINGS)
  target_compile_options(fraktal_opcua PRIVATE
    /W3 /wd4244 /wd4267 /wd4996 /UUNICODE /U_UNICODE)
  target_link_libraries(fraktal_opcua PRIVATE ws2_32 iphlpapi)

  add_executable(fraktal_gateway_tray WIN32
    "${CMAKE_CURRENT_SOURCE_DIR}/../../gateway/windows_tray/fraktal_gateway_tray.cpp")
  target_compile_features(fraktal_gateway_tray PRIVATE cxx_std_17)
  target_compile_definitions(fraktal_gateway_tray PRIVATE UNICODE _UNICODE)
  target_compile_options(fraktal_gateway_tray PRIVATE /W4 /EHsc)
  target_link_libraries(fraktal_gateway_tray PRIVATE shell32 user32 winhttp)
else()
  find_package(Threads REQUIRED)
  target_compile_options(fraktal_opcua PRIVATE -Wall -Wextra)
  target_link_libraries(fraktal_opcua PRIVATE Threads::Threads ${CMAKE_DL_LIBS} m)
endif()
