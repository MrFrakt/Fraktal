cmake_minimum_required(VERSION 3.14)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  project(fraktal_ads LANGUAGES CXX)
endif()

# The ADS bridge is Beckhoff/TwinCAT-specific and Windows-only: it wraps
# TcAdsDll, which ships with a TwinCAT installation. On non-Windows or where
# TcAdsDll is absent, the target is simply not built and the HMI falls back to
# the OPC UA transport (the portable, multi-brand path).
if(NOT WIN32)
  message(STATUS "fraktal_ads: skipped (ADS transport is Windows/TwinCAT only)")
  return()
endif()

# Locate the TwinCAT ADS SDK (headers + import lib). Overridable via -D.
set(TCADS_ROOT "C:/Program Files (x86)/Beckhoff/TwinCAT/AdsApi/TcAdsDll"
    CACHE PATH "TwinCAT ADS SDK root (TcAdsDll)")
find_path(TCADS_INCLUDE_DIR NAMES TcAdsAPI.h
    HINTS "${TCADS_ROOT}/Include")
find_library(TCADS_LIBRARY NAMES TcAdsDll
    HINTS "${TCADS_ROOT}/Lib/x64" "${TCADS_ROOT}/Lib")

if(NOT TCADS_INCLUDE_DIR OR NOT TCADS_LIBRARY)
  message(STATUS
    "fraktal_ads: TcAdsDll SDK not found (set -DTCADS_ROOT=...). "
    "Skipping the ADS transport; the HMI uses OPC UA.")
  return()
endif()

# Statically link the MSVC runtime (/MT) so the DLL has no dependency on the
# Visual C++ Redistributable. A bare CX-series PLC / IPC typically has TwinCAT
# (so TcAdsDll.dll is present) but NOT the VC++ redist, and a missing
# msvcp140.dll/vcruntime140.dll surfaces only as LoadLibrary error 126
# ("module could not be found") naming fraktal_ads.dll itself — a dead end to
# diagnose in the field. Replacing /MD in the flag variables works regardless of
# CMake policy CMP0091 (which needs CMake >= 3.15).
foreach(flagVar
    CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_DEBUG CMAKE_CXX_FLAGS_RELEASE
    CMAKE_CXX_FLAGS_MINSIZEREL CMAKE_CXX_FLAGS_RELWITHDEBINFO)
  string(REGEX REPLACE "/MD" "/MT" ${flagVar} "${${flagVar}}")
endforeach()

add_library(fraktal_ads SHARED
  "${CMAKE_CURRENT_SOURCE_DIR}/fraktal_ads_bridge.cpp")
target_include_directories(fraktal_ads PRIVATE
  "${CMAKE_CURRENT_SOURCE_DIR}" "${TCADS_INCLUDE_DIR}")
target_compile_features(fraktal_ads PRIVATE cxx_std_17)
target_compile_definitions(fraktal_ads PRIVATE _CRT_SECURE_NO_WARNINGS)
target_compile_options(fraktal_ads PRIVATE /W3 /wd4244 /wd4267 /EHsc)
target_link_libraries(fraktal_ads PRIVATE "${TCADS_LIBRARY}")

# Signal to the parent (runner) CMake that the target exists, so it can install
# the DLL next to the executable.
set(FRAKTAL_ADS_AVAILABLE ON CACHE INTERNAL "fraktal_ads target was built")
