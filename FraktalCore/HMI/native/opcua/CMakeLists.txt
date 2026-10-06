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

if(NOT TARGET mbedtls)
  add_subdirectory(
    "${CMAKE_CURRENT_SOURCE_DIR}/third_party/mbedtls-3.6.6"
    "${CMAKE_CURRENT_BINARY_DIR}/mbedtls"
    EXCLUDE_FROM_ALL)
endif()

add_library(fraktal_opcua SHARED
  "${CMAKE_CURRENT_SOURCE_DIR}/fraktal_opcua_bridge.cpp"
  "${CMAKE_CURRENT_SOURCE_DIR}/third_party/open62541/open62541.c")
target_include_directories(fraktal_opcua PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}"
  "${CMAKE_CURRENT_SOURCE_DIR}/third_party/open62541"
  "${CMAKE_CURRENT_SOURCE_DIR}/third_party/mbedtls-3.6.6/include")
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
