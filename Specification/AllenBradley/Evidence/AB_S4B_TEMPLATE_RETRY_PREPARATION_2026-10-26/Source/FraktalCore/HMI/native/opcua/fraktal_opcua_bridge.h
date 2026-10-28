#pragma once

#include <stdint.h>

#if defined(_WIN32)
#define FRK_EXPORT __declspec(dllexport)
#else
#define FRK_EXPORT __attribute__((visibility("default")))
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef void* FrkOpcUaHandle;

enum FrkOpcUaSecurityProfile {
  FRK_OPCUA_SECURITY_NONE = 0,
  FRK_OPCUA_SECURITY_SIGN_ENCRYPT_USER = 1,
  FRK_OPCUA_SECURITY_SIGN_ENCRYPT_ANONYMOUS = 2
};

FRK_EXPORT FrkOpcUaHandle frk_opcua_create(void);
FRK_EXPORT void frk_opcua_destroy(FrkOpcUaHandle handle);
FRK_EXPORT int32_t frk_opcua_connect(FrkOpcUaHandle handle,
                                     const char* endpoint,
                                     const char* username,
                                     const char* password,
                                     uint32_t timeout_ms);
FRK_EXPORT int32_t frk_opcua_connect_secure(
    FrkOpcUaHandle handle,
    const char* endpoint,
    const char* username,
    const char* password,
    uint32_t timeout_ms,
    int32_t security_profile,
    const char* security_policy_uri,
    const char* application_uri,
    const char* client_certificate_path,
    const char* client_private_key_path,
    const char* client_private_key_password,
    const char* trust_list_path,
    const char* revocation_list_path);
FRK_EXPORT void frk_opcua_disconnect(FrkOpcUaHandle handle);
FRK_EXPORT int32_t frk_opcua_is_connected(FrkOpcUaHandle handle);
FRK_EXPORT const char* frk_opcua_last_error(FrkOpcUaHandle handle);

// Returns an owned UTF-8 JSON document. Release it with frk_opcua_free_string.
FRK_EXPORT char* frk_opcua_snapshot_json(FrkOpcUaHandle handle);
FRK_EXPORT void frk_opcua_free_string(char* value);

// Marks browse paths (newline-separated) as low-frequency "config" reads: the
// snapshot reads them once at discovery and on a slow heartbeat, not on every
// call; the fast remainder is read every snapshot. The merged output is
// unchanged. The set persists across reconnects; call again to replace it.
FRK_EXPORT int32_t frk_opcua_set_slow_paths(FrkOpcUaHandle handle,
                                            const char* newline_separated_paths);
// Marks browse paths (newline-separated) as on-demand: never read in the
// cyclic snapshot, served only by an explicit frk_opcua_read_values_json call
// (e.g. fieldbus I/O, read only while its view is visible). Replaces the set.
FRK_EXPORT int32_t frk_opcua_set_excluded_paths(FrkOpcUaHandle handle,
                                                const char* newline_separated_paths);
// Forces the next snapshot to re-read the slow paths (e.g. after a config write).
FRK_EXPORT void frk_opcua_refresh_slow(FrkOpcUaHandle handle);

// Reads only the given browse paths (newline-separated) in one service call and
// returns {"values":{...}} — used for mailbox acknowledgement polling and other
// targeted reads that must not pay for a full snapshot. Paths must have been
// discovered. Release the result with frk_opcua_free_string.
FRK_EXPORT char* frk_opcua_read_values_json(FrkOpcUaHandle handle,
                                            const char* newline_separated_paths);

FRK_EXPORT int32_t frk_opcua_write_bool(FrkOpcUaHandle handle,
                                        const char* browse_path,
                                        int32_t value);
FRK_EXPORT int32_t frk_opcua_write_int64(FrkOpcUaHandle handle,
                                         const char* browse_path,
                                         int64_t value);
FRK_EXPORT int32_t frk_opcua_write_int32(FrkOpcUaHandle handle,
                                         const char* browse_path,
                                         int32_t value);
FRK_EXPORT int32_t frk_opcua_write_uint32(FrkOpcUaHandle handle,
                                          const char* browse_path,
                                          uint32_t value);
FRK_EXPORT int32_t frk_opcua_write_double(FrkOpcUaHandle handle,
                                          const char* browse_path,
                                          double value);
FRK_EXPORT int32_t frk_opcua_write_string(FrkOpcUaHandle handle,
                                          const char* browse_path,
                                          const char* value);

#ifdef __cplusplus
}
#endif
