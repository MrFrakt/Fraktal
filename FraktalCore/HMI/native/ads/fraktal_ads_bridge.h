#pragma once

#include <stdint.h>

#if defined(_WIN32)
#define FRK_ADS_EXPORT __declspec(dllexport)
#else
#define FRK_ADS_EXPORT __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

// Direct-ADS transport for the native TwinCAT path. Wraps TcAdsDll and emits the
// SAME fraktal.opcua.snapshot.v1 browse-path document the OPC UA bridge does, so
// the Dart repository, snapshot mapper, and every HMI view are unchanged.
//
// Wire identity is the ADS symbol name; the document uses '/'-separated paths
// under a synthetic "PLC1/" prefix so the mapper cannot tell which transport
// produced it (symbol MAIN.X.Y <-> path PLC1/MAIN/X/Y).

typedef void* FrkAdsHandle;

FRK_ADS_EXPORT FrkAdsHandle frk_ads_create(void);
FRK_ADS_EXPORT void frk_ads_destroy(FrkAdsHandle handle);

// Opens an ADS port and targets amsNetId ("a.b.c.d.e.f") : amsPort (e.g. 851).
// Returns 1 on success, 0 on failure (see frk_ads_last_error).
FRK_ADS_EXPORT int32_t frk_ads_connect(FrkAdsHandle handle,
                                       const char* ams_net_id,
                                       uint16_t ams_port);
FRK_ADS_EXPORT void frk_ads_disconnect(FrkAdsHandle handle);
FRK_ADS_EXPORT int32_t frk_ads_is_connected(FrkAdsHandle handle);
FRK_ADS_EXPORT const char* frk_ads_last_error(FrkAdsHandle handle);

// Returns an owned UTF-8 JSON snapshot document. Release with frk_ads_free_string.
// On the first call after connect it discovers the contract (symbol upload +
// datatype-table walk), caches value handles, then reads. Discovery is cached;
// a session/router loss re-discovers on the next call.
FRK_ADS_EXPORT char* frk_ads_snapshot_json(FrkAdsHandle handle);
FRK_ADS_EXPORT void frk_ads_free_string(char* value);

// Reads only the given browse paths (newline-separated) and returns
// {"values":{...}} — the targeted-read path for mailbox ack polling and
// on-demand scopes. Release with frk_ads_free_string.
FRK_ADS_EXPORT char* frk_ads_read_values_json(FrkAdsHandle handle,
                                              const char* newline_separated_paths);

// Marks browse paths (newline-separated) as on-demand: excluded from the cyclic
// snapshot, served only by frk_ads_read_values_json. Replaces the set.
FRK_ADS_EXPORT int32_t frk_ads_set_excluded_paths(
    FrkAdsHandle handle, const char* newline_separated_paths);

// Typed writes by browse path (mapped back to the ADS symbol handle).
FRK_ADS_EXPORT int32_t frk_ads_write_bool(FrkAdsHandle handle,
                                          const char* browse_path, int32_t value);
FRK_ADS_EXPORT int32_t frk_ads_write_int32(FrkAdsHandle handle,
                                           const char* browse_path, int32_t value);
FRK_ADS_EXPORT int32_t frk_ads_write_uint32(FrkAdsHandle handle,
                                            const char* browse_path, uint32_t value);
FRK_ADS_EXPORT int32_t frk_ads_write_int64(FrkAdsHandle handle,
                                           const char* browse_path, int64_t value);
FRK_ADS_EXPORT int32_t frk_ads_write_double(FrkAdsHandle handle,
                                            const char* browse_path, double value);
FRK_ADS_EXPORT int32_t frk_ads_write_string(FrkAdsHandle handle,
                                            const char* browse_path, const char* value);

#ifdef __cplusplus
}
#endif
