// A target-local observer: does not set time, change peers, or start W32Time.
#include <windows.h>
#include <rpc.h>
#include <cstdint>
#include <cstdio>
#include <cwchar>
#include <limits>
#include <cstddef>
#include <cstring>
#include "w32time.h"
extern "C" unsigned long QueryStatusSafely(handle_t, FraktalW32Status**);
extern "C" void __RPC_USER midl_user_free(void*);

#pragma pack(push, 1)
struct Sample {
 uint16_t version = 1;
 uint16_t length = sizeof(Sample);
 uint32_t magic = 0x434B5246; // FRKC, little endian
 uint32_t sequence = 0;
 uint32_t observed = 0;
 uint32_t lastSync = 0;
 int32_t offsetUs = 0;
 uint32_t syncAgeSeconds = 0;
 uint32_t error = 0;
 uint32_t flags = 0; // bit 0: available, bit 1: service synchronized
 char source[33] = {};
 uint8_t reserved[3] = {};
 uint32_t crc = 0;
};
#pragma pack(pop)
static_assert(sizeof(Sample) == 76, "PLC/observer wire size");

uint32_t Crc(const Sample& sample) {
 uint32_t value = 0xffffffff;
 auto bytes = reinterpret_cast<const uint8_t*>(&sample);
 for (size_t i = 0; i < offsetof(Sample, crc); ++i) {
  value ^= bytes[i];
  for (unsigned bit = 0; bit < 8; ++bit)
   value = (value >> 1) ^ ((value & 1) ? 0xedb88320 : 0);
 }
 return ~value;
}
uint32_t UnixTime(uint64_t fileTime) {
 constexpr uint64_t epoch = 116444736000000000ULL;
 if (fileTime < epoch) return 0;
 auto seconds = (fileTime - epoch) / 10000000;
 return seconds > UINT32_MAX ? 0 : static_cast<uint32_t>(seconds);
}
DWORD ServiceState() {
 auto manager = OpenSCManagerW(nullptr, nullptr, SC_MANAGER_CONNECT);
 if (!manager) return GetLastError();
 auto service = OpenServiceW(manager, L"W32Time", SERVICE_QUERY_STATUS);
 DWORD result = service ? 0 : GetLastError();
 if (service) {
  SERVICE_STATUS status{};
  if (!QueryServiceStatus(service, &status)) result = GetLastError();
  else if (status.dwCurrentState != SERVICE_RUNNING) result = ERROR_SERVICE_NOT_ACTIVE;
  CloseServiceHandle(service);
 }
 CloseServiceHandle(manager);
 return result;
}
Sample Observe(uint32_t sequence) {
 Sample sample;
 FILETIME fileTime;
 GetSystemTimeAsFileTime(&fileTime);
 ULARGE_INTEGER stamp;
 stamp.LowPart = fileTime.dwLowDateTime; stamp.HighPart = fileTime.dwHighDateTime;
 sample.observed = UnixTime(stamp.QuadPart);
 sample.sequence = sequence;
 memcpy(sample.source, "WINDOWS/W32TIME", 15);
 sample.error = ServiceState();
 if (sample.error) { sample.crc = Crc(sample); return sample; }
 RPC_WSTR bindingString = nullptr;
 RPC_BINDING_HANDLE binding = nullptr;
 // Local named pipe only; no remote computer or network destination accepted.
 auto result = RpcStringBindingComposeW(nullptr, reinterpret_cast<RPC_WSTR>(const_cast<wchar_t*>(L"ncacn_np")),
   nullptr, reinterpret_cast<RPC_WSTR>(const_cast<wchar_t*>(L"\\pipe\\W32TIME_ALT")), nullptr, &bindingString);
 if (!result) result = RpcBindingFromStringBindingW(bindingString, &binding);
 if (bindingString) RpcStringFreeW(&bindingString);
 if (!result) result = RpcBindingSetAuthInfoW(binding, nullptr,
   RPC_C_AUTHN_LEVEL_PKT_PRIVACY, RPC_C_AUTHN_WINNT, nullptr, RPC_C_AUTHZ_NONE);
 if (!result) result = RpcBindingSetOption(binding, RPC_C_OPT_CALL_TIMEOUT, 3000);
 FraktalW32Status* status = nullptr;
 if (!result) result = QueryStatusSafely(binding, &status);
 if (!result && status && status->count == 0 && status->entries == nullptr) {
  sample.flags = 1;
  sample.lastSync = UnixTime(status->lastSync);
  const auto offset = status->offset / 10; // 100 ns -> microseconds
  if (offset < INT32_MIN || offset > INT32_MAX) result = ERROR_ARITHMETIC_OVERFLOW;
  else sample.offsetUs = static_cast<int32_t>(offset);
  const auto age = status->syncAge / 10000000;
  sample.syncAgeSeconds = age > UINT32_MAX ? UINT32_MAX : static_cast<uint32_t>(age);
  // Reject local free-running reference clocks even when labeled synchronized.
  const bool localReference = status->reference == 0x4c4f434c || status->reference == 0x4c434f4c;
  if (!localReference && status->leap < 3 && status->stratum > 0 && status->stratum < 16
      && status->lastResult == 0 && sample.lastSync > 0 && status->source && status->source[0])
   sample.flags |= 2;
  if (status->source) wprintf(L"source=%ls ", status->source);
 } else if (!result) result = ERROR_INVALID_DATA;
 // RPC allocates the returned graph with midl_user_allocate.
 if (status) { midl_user_free(status->source); midl_user_free(status->entries); midl_user_free(status); }
 if (binding) RpcBindingFree(&binding);
 sample.error = result;
 if (result) sample.flags = 0;
 sample.crc = Crc(sample);
 return sample;
}
bool WriteSample(const wchar_t* path, const Sample& sample) {
 wchar_t pending[32768];
 if (swprintf_s(pending, L"%ls.partial", path) < 0) return false;
 auto file = CreateFileW(pending, GENERIC_WRITE, 0, nullptr, CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
 if (file == INVALID_HANDLE_VALUE) return false;
 DWORD written = 0;
 bool ok = WriteFile(file, &sample, sizeof(sample), &written, nullptr) && written == sizeof(sample);
 if (ok) ok = FlushFileBuffers(file) != 0;
 CloseHandle(file);
 if (ok) {
  // A PLC file read may briefly hold the old file without delete-sharing.
  ok = false;
  for (unsigned retry = 0; retry < 100; ++retry) {
   if (MoveFileExW(pending, path, MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) { ok = true; break; }
   const auto error = GetLastError();
   if (error != ERROR_SHARING_VIOLATION && error != ERROR_ACCESS_DENIED) break;
   Sleep(50);
  }
 }
 if (!ok) DeleteFileW(pending);
 return ok;
}
int wmain(int count, wchar_t** args) {
 if (count < 2 || count > 3) {
  puts("Usage: FraktalWindowsClock.exe <target-local-sample-file> [--once]"); return 64;
 }
 bool once = count == 3 && wcscmp(args[2], L"--once") == 0;
 if (count == 3 && !once) return 64;
 uint32_t sequence = GetTickCount();
 do {
  auto sample = Observe(++sequence);
  printf("available=%u synchronized=%u offsetUs=%ld syncAgeSeconds=%lu error=%lu\n",
   sample.flags & 1, (sample.flags >> 1) & 1, static_cast<long>(sample.offsetUs),
   static_cast<unsigned long>(sample.syncAgeSeconds), static_cast<unsigned long>(sample.error));
  if (!WriteSample(args[1], sample)) { fprintf(stderr, "Sample write failed: %lu\n", GetLastError()); return 1; }
  if (!once) Sleep(30000);
 } while (!once);
 return 0;
}
