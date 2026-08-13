#define NOMINMAX

#include <windows.h>
#include <shellapi.h>
#include <winhttp.h>

#include <algorithm>
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <sstream>
#include <string>
#include <vector>

#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "winhttp.lib")

namespace {
constexpr UINT kTrayMessage = WM_APP + 1;
constexpr UINT_PTR kMonitorTimer = 1;
constexpr UINT kMenuStatus = 1001;
constexpr UINT kMenuStartAll = 1002;
constexpr UINT kMenuStopAll = 1003;
constexpr UINT kMenuRestartAll = 1004;
constexpr UINT kMenuLogsRoot = 1006;
constexpr UINT kMenuGuide = 1008;
constexpr UINT kMenuExit = 1009;
constexpr UINT kMenuProxyConfig = 1011;
constexpr UINT kMenuReload = 1012;

// One gateway process serves one PLC, so a host with several controllers runs
// several instances. Each is a folder under
// %LOCALAPPDATA%\Fraktal\Gateway\instances holding one gateway.args; the folder
// name is the instance name. deploy/windows/fraktal_instances.ps1 states the
// same rule for the wizard and the installer — keep the two in step.
constexpr UINT kMaxInstances = 16;
// Per-instance menu commands are allocated in fixed-width blocks so a click can
// be decoded back into (instance, command) arithmetically.
constexpr UINT kInstanceMenuBase = 2000;
constexpr UINT kInstanceMenuStride = 16;
constexpr UINT kInstanceStart = 0;
constexpr UINT kInstanceStop = 1;
constexpr UINT kInstanceRestart = 2;
constexpr UINT kInstanceConfig = 3;
constexpr UINT kInstanceLogs = 4;
constexpr UINT kInstanceWebHmi = 5;
constexpr UINT kInstanceHealth = 6;

enum class InstanceState { kStopped, kStarting, kDegraded, kReady, kFailed };

struct Instance {
  std::wstring name;
  std::filesystem::path config_path;
  std::filesystem::path log_path;
  // The browser origin this instance's Web HMI is published on, taken from its
  // own --allow-origin. Empty when the instance is loopback-only.
  std::wstring web_origin;
  DWORD health_port = 8080;
  PROCESS_INFORMATION child{};
  bool user_stopped = false;
  unsigned restart_failures = 0;
  ULONGLONG restart_after = 0;
  InstanceState state = InstanceState::kStopped;
  std::wstring status = L"Stopped";
};

HWND g_window = nullptr;
NOTIFYICONDATAW g_tray{};
PROCESS_INFORMATION g_proxy{};
std::filesystem::path g_install_dir;
std::filesystem::path g_data_dir;
std::filesystem::path g_instance_dir;
std::filesystem::path g_logs_dir;
std::filesystem::path g_proxy_config_path;
std::filesystem::path g_proxy_log_path;
std::vector<Instance> g_instances;
bool g_exiting = false;
unsigned g_proxy_restart_failures = 0;
ULONGLONG g_proxy_restart_after = 0;
std::wstring g_status = L"Starting";
UINT g_taskbar_created = 0;
HANDLE g_stop_event = nullptr;

std::wstring Quote(const std::wstring& value) {
  if (value.find_first_of(L" \t\"") == std::wstring::npos) return value;
  std::wstring result = L"\"";
  unsigned slashes = 0;
  for (const wchar_t character : value) {
    if (character == L'\\') {
      ++slashes;
    } else if (character == L'\"') {
      result.append(slashes * 2 + 1, L'\\');
      result.push_back(L'\"');
      slashes = 0;
    } else {
      result.append(slashes, L'\\');
      slashes = 0;
      result.push_back(character);
    }
  }
  result.append(slashes * 2, L'\\');
  result.push_back(L'\"');
  return result;
}

std::wstring Utf8ToWide(const std::string& value) {
  if (value.empty()) return {};
  const int length = MultiByteToWideChar(
      CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
      static_cast<int>(value.size()), nullptr, 0);
  if (length <= 0) return {};
  std::wstring result(static_cast<size_t>(length), L'\0');
  MultiByteToWideChar(CP_UTF8, MB_ERR_INVALID_CHARS, value.data(),
                      static_cast<int>(value.size()), result.data(), length);
  return result;
}

std::wstring ExpandEnvironment(const std::wstring& value) {
  const DWORD required = ExpandEnvironmentStringsW(value.c_str(), nullptr, 0);
  if (required == 0) return value;
  std::wstring result(required, L'\0');
  ExpandEnvironmentStringsW(value.c_str(), result.data(), required);
  if (!result.empty() && result.back() == L'\0') result.pop_back();
  return result;
}

std::vector<std::wstring> LoadArguments(const std::filesystem::path& path) {
  std::vector<std::wstring> arguments;
  std::ifstream stream(path, std::ios::binary);
  std::string line;
  bool first = true;
  while (std::getline(stream, line)) {
    if (!line.empty() && line.back() == '\r') line.pop_back();
    if (first && line.size() >= 3 &&
        static_cast<unsigned char>(line[0]) == 0xEF &&
        static_cast<unsigned char>(line[1]) == 0xBB &&
        static_cast<unsigned char>(line[2]) == 0xBF) {
      line.erase(0, 3);
    }
    first = false;
    const auto start = line.find_first_not_of(" \t");
    if (start == std::string::npos || line[start] == '#') continue;
    const auto end = line.find_last_not_of(" \t");
    arguments.push_back(ExpandEnvironment(
        Utf8ToWide(line.substr(start, end - start + 1))));
  }
  return arguments;
}

// The arguments file is the only source for an instance's port and published
// origin, so both are read back from it rather than cached anywhere else.
void RefreshInstanceSettings(Instance& instance) {
  instance.health_port = 8080;
  instance.web_origin.clear();
  const auto arguments = LoadArguments(instance.config_path);
  for (size_t index = 0; index + 1 < arguments.size(); ++index) {
    if (arguments[index] == L"--port") {
      try {
        instance.health_port = std::stoul(arguments[index + 1]);
      } catch (...) {
        instance.health_port = 8080;
      }
    } else if (arguments[index] == L"--allow-origin" &&
               instance.web_origin.empty()) {
      instance.web_origin = arguments[index + 1];
    }
  }
}

bool ValidInstanceName(const std::wstring& name) {
  if (name.empty() || name.size() > 32) return false;
  if (name == L"." || name == L"..") return false;
  for (const wchar_t character : name) {
    const bool allowed = (character >= L'A' && character <= L'Z') ||
                         (character >= L'a' && character <= L'z') ||
                         (character >= L'0' && character <= L'9') ||
                         character == L'.' || character == L'_' ||
                         character == L'-';
    if (!allowed) return false;
  }
  return true;
}

void DiscoverInstances() {
  g_instances.clear();
  std::error_code error;
  if (std::filesystem::is_directory(g_instance_dir, error)) {
    std::vector<std::wstring> names;
    for (const auto& entry :
         std::filesystem::directory_iterator(g_instance_dir, error)) {
      if (!entry.is_directory(error)) continue;
      const std::wstring name = entry.path().filename().wstring();
      if (!ValidInstanceName(name)) continue;
      if (!std::filesystem::exists(entry.path() / L"gateway.args", error)) {
        continue;
      }
      names.push_back(name);
    }
    std::sort(names.begin(), names.end());
    if (names.size() > kMaxInstances) names.resize(kMaxInstances);

    for (const auto& name : names) {
      Instance instance;
      instance.name = name;
      instance.config_path = g_instance_dir / name / L"gateway.args";
      instance.log_path = g_logs_dir / name / L"gateway.log";
      g_instances.push_back(std::move(instance));
    }
  }
  if (g_instances.empty()) {
    // Pre-instances layout: a single gateway.args in the data root. Left in
    // place and used as-is, so an installation that has not been upgraded yet
    // keeps running instead of reporting a missing configuration.
    const auto legacy = g_data_dir / L"gateway.args";
    if (std::filesystem::exists(legacy, error)) {
      Instance instance;
      instance.name = L"default";
      instance.config_path = legacy;
      instance.log_path = g_logs_dir / L"gateway.log";
      g_instances.push_back(std::move(instance));
    }
  }
  for (auto& instance : g_instances) RefreshInstanceSettings(instance);
}

void SetTrayStatus(const std::wstring& status, HICON icon) {
  g_status = status;
  g_tray.hIcon = icon;
  const std::wstring tooltip = L"Fraktal Gateway - " + status;
  wcsncpy_s(g_tray.szTip, tooltip.c_str(), _TRUNCATE);
  Shell_NotifyIconW(NIM_MODIFY, &g_tray);
}

bool ProxyConfigured() {
  return std::filesystem::exists(g_proxy_config_path);
}

HICON IconForState(InstanceState state) {
  switch (state) {
    case InstanceState::kReady:
      return LoadIconW(nullptr, IDI_INFORMATION);
    case InstanceState::kFailed:
      return LoadIconW(nullptr, IDI_ERROR);
    case InstanceState::kStopped:
      return LoadIconW(nullptr, IDI_APPLICATION);
    default:
      return LoadIconW(nullptr, IDI_WARNING);
  }
}

// One icon and one tooltip have to describe every instance at once. Failure is
// the headline: an operator must not read "Ready" while one of three PLCs is
// unreachable.
void UpdateAggregateStatus() {
  if (g_exiting) return;
  if (g_instances.empty()) {
    SetTrayStatus(L"No instance configured", LoadIconW(nullptr, IDI_ERROR));
    return;
  }
  size_t ready = 0;
  size_t failed = 0;
  size_t stopped = 0;
  for (const auto& instance : g_instances) {
    if (instance.state == InstanceState::kReady) ++ready;
    if (instance.state == InstanceState::kFailed) ++failed;
    if (instance.state == InstanceState::kStopped) ++stopped;
  }
  const size_t total = g_instances.size();
  const std::wstring counted = std::to_wstring(ready) + L" of " +
                               std::to_wstring(total) + L" ready";
  if (total == 1) {
    SetTrayStatus(g_instances.front().status,
                  IconForState(g_instances.front().state));
  } else if (failed > 0) {
    SetTrayStatus(std::to_wstring(failed) + L" of " + std::to_wstring(total) +
                      L" failed",
                  LoadIconW(nullptr, IDI_ERROR));
  } else if (ready == total) {
    SetTrayStatus(std::to_wstring(total) + L" instances ready",
                  LoadIconW(nullptr, IDI_INFORMATION));
  } else if (stopped == total) {
    SetTrayStatus(L"Stopped", LoadIconW(nullptr, IDI_APPLICATION));
  } else {
    SetTrayStatus(counted, LoadIconW(nullptr, IDI_WARNING));
  }
  if (ProxyConfigured() && g_proxy.hProcess == nullptr && !g_exiting) {
    SetTrayStatus(L"HTTPS proxy failed - retrying",
                  LoadIconW(nullptr, IDI_ERROR));
  }
}

void SetInstanceStatus(Instance& instance, InstanceState state,
                       const std::wstring& status) {
  instance.state = state;
  instance.status = status;
  UpdateAggregateStatus();
}

void CloseChildHandles(Instance& instance) {
  if (instance.child.hThread != nullptr) CloseHandle(instance.child.hThread);
  if (instance.child.hProcess != nullptr) CloseHandle(instance.child.hProcess);
  instance.child = {};
}

void CloseProxyHandles() {
  if (g_proxy.hThread != nullptr) CloseHandle(g_proxy.hThread);
  if (g_proxy.hProcess != nullptr) CloseHandle(g_proxy.hProcess);
  g_proxy = {};
}

bool StartInstance(Instance& instance) {
  if (instance.child.hProcess != nullptr) return true;
  const auto executable = g_install_dir / L"fraktal_gateway.exe";
  if (!std::filesystem::exists(executable)) {
    SetInstanceStatus(instance, InstanceState::kFailed, L"Executable missing");
    return false;
  }
  if (!std::filesystem::exists(instance.config_path)) {
    SetInstanceStatus(instance, InstanceState::kFailed,
                      L"Configuration missing");
    return false;
  }
  RefreshInstanceSettings(instance);
  std::filesystem::create_directories(instance.log_path.parent_path());
  SECURITY_ATTRIBUTES security{};
  security.nLength = sizeof(security);
  security.bInheritHandle = TRUE;
  HANDLE log = CreateFileW(instance.log_path.c_str(), FILE_APPEND_DATA,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, &security,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (log == INVALID_HANDLE_VALUE) {
    SetInstanceStatus(instance, InstanceState::kFailed, L"Cannot open log");
    return false;
  }
  SetFilePointer(log, 0, nullptr, FILE_END);
  HANDLE null_input = CreateFileW(L"NUL", GENERIC_READ,
                                  FILE_SHARE_READ | FILE_SHARE_WRITE,
                                  &security, OPEN_EXISTING,
                                  FILE_ATTRIBUTE_NORMAL, nullptr);
  if (null_input == INVALID_HANDLE_VALUE) {
    CloseHandle(log);
    SetInstanceStatus(instance, InstanceState::kFailed,
                      L"Cannot open process input");
    return false;
  }
  std::wstring command = Quote(executable.wstring());
  for (const auto& argument : LoadArguments(instance.config_path)) {
    command += L" " + Quote(argument);
  }
  std::vector<wchar_t> mutable_command(command.begin(), command.end());
  mutable_command.push_back(L'\0');
  STARTUPINFOW startup{};
  startup.cb = sizeof(startup);
  startup.dwFlags = STARTF_USESHOWWINDOW | STARTF_USESTDHANDLES;
  startup.wShowWindow = SW_HIDE;
  startup.hStdInput = null_input;
  startup.hStdOutput = log;
  startup.hStdError = log;
  PROCESS_INFORMATION process{};
  const BOOL created = CreateProcessW(
      executable.c_str(), mutable_command.data(), nullptr, nullptr, TRUE,
      CREATE_NO_WINDOW, nullptr, g_install_dir.c_str(), &startup, &process);
  CloseHandle(null_input);
  CloseHandle(log);
  if (!created) {
    SetInstanceStatus(instance, InstanceState::kFailed, L"Start failed");
    return false;
  }
  instance.child = process;
  instance.user_stopped = false;
  SetInstanceStatus(instance, InstanceState::kStarting, L"Connecting");
  return true;
}

void StopInstance(Instance& instance, bool user_stopped) {
  instance.user_stopped = user_stopped;
  instance.restart_after = 0;
  if (instance.child.hProcess != nullptr) {
    // The gateway owns no durable command queue. Forced local shutdown cannot
    // replay an HMI write and the PLC remains the final command authority.
    TerminateProcess(instance.child.hProcess, 0);
    WaitForSingleObject(instance.child.hProcess, 2000);
    CloseChildHandles(instance);
  }
  if (!g_exiting) {
    SetInstanceStatus(instance,
                      user_stopped ? InstanceState::kStopped
                                   : InstanceState::kStarting,
                      user_stopped ? L"Stopped" : L"Restarting");
  }
}

bool StartProxy() {
  if (!ProxyConfigured() || g_proxy.hProcess != nullptr) return true;
  const auto executable = g_install_dir / L"caddy.exe";
  if (!std::filesystem::exists(executable)) {
    SetTrayStatus(L"HTTPS proxy executable missing",
                  LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  std::filesystem::create_directories(g_proxy_log_path.parent_path());
  SECURITY_ATTRIBUTES security{};
  security.nLength = sizeof(security);
  security.bInheritHandle = TRUE;
  HANDLE log = CreateFileW(g_proxy_log_path.c_str(), FILE_APPEND_DATA,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, &security,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (log == INVALID_HANDLE_VALUE) {
    SetTrayStatus(L"Cannot open HTTPS proxy log",
                  LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  SetFilePointer(log, 0, nullptr, FILE_END);
  HANDLE null_input = CreateFileW(L"NUL", GENERIC_READ,
                                  FILE_SHARE_READ | FILE_SHARE_WRITE,
                                  &security, OPEN_EXISTING,
                                  FILE_ATTRIBUTE_NORMAL, nullptr);
  if (null_input == INVALID_HANDLE_VALUE) {
    CloseHandle(log);
    SetTrayStatus(L"Cannot open HTTPS proxy input",
                  LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  std::wstring command = Quote(executable.wstring()) +
      L" run --config " + Quote(g_proxy_config_path.wstring()) +
      L" --adapter caddyfile";
  std::vector<wchar_t> mutable_command(command.begin(), command.end());
  mutable_command.push_back(L'\0');
  STARTUPINFOW startup{};
  startup.cb = sizeof(startup);
  startup.dwFlags = STARTF_USESHOWWINDOW | STARTF_USESTDHANDLES;
  startup.wShowWindow = SW_HIDE;
  startup.hStdInput = null_input;
  startup.hStdOutput = log;
  startup.hStdError = log;
  PROCESS_INFORMATION process{};
  const BOOL created = CreateProcessW(
      executable.c_str(), mutable_command.data(), nullptr, nullptr, TRUE,
      CREATE_NO_WINDOW, nullptr, g_install_dir.c_str(), &startup, &process);
  CloseHandle(null_input);
  CloseHandle(log);
  if (!created) {
    SetTrayStatus(L"HTTPS proxy start failed", LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  g_proxy = process;
  return true;
}

void StopProxy() {
  g_proxy_restart_after = 0;
  if (g_proxy.hProcess == nullptr) return;
  TerminateProcess(g_proxy.hProcess, 0);
  WaitForSingleObject(g_proxy.hProcess, 2000);
  CloseProxyHandles();
}

void StartAll() {
  g_proxy_restart_failures = 0;
  for (auto& instance : g_instances) {
    instance.restart_failures = 0;
    if (!StartInstance(instance)) {
      instance.restart_after = GetTickCount64() + 1000;
    }
  }
  if (!StartProxy()) {
    g_proxy_restart_after = GetTickCount64() + 1000;
  }
  UpdateAggregateStatus();
}

void StopAll(bool user_stopped) {
  StopProxy();
  for (auto& instance : g_instances) StopInstance(instance, user_stopped);
  UpdateAggregateStatus();
}

bool ProbeReady(DWORD port) {
  HINTERNET session = WinHttpOpen(
      L"FraktalGatewayTray/1.0", WINHTTP_ACCESS_TYPE_NO_PROXY,
      WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
  if (session == nullptr) return false;
  WinHttpSetTimeouts(session, 400, 400, 400, 400);
  HINTERNET connection = WinHttpConnect(
      session, L"127.0.0.1", static_cast<INTERNET_PORT>(port), 0);
  HINTERNET request = connection == nullptr
      ? nullptr
      : WinHttpOpenRequest(connection, L"GET", L"/readyz", nullptr,
                           WINHTTP_NO_REFERER, WINHTTP_DEFAULT_ACCEPT_TYPES, 0);
  bool ready = false;
  if (request != nullptr &&
      WinHttpSendRequest(request, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                         WINHTTP_NO_REQUEST_DATA, 0, 0, 0) &&
      WinHttpReceiveResponse(request, nullptr)) {
    DWORD status = 0;
    DWORD size = sizeof(status);
    if (WinHttpQueryHeaders(
            request, WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
            WINHTTP_HEADER_NAME_BY_INDEX, &status, &size,
            WINHTTP_NO_HEADER_INDEX)) {
      ready = status == 200;
    }
  }
  if (request != nullptr) WinHttpCloseHandle(request);
  if (connection != nullptr) WinHttpCloseHandle(connection);
  WinHttpCloseHandle(session);
  return ready;
}

void MonitorProxy() {
  if (!ProxyConfigured()) return;
  if (g_proxy.hProcess == nullptr) {
    if (g_proxy_restart_after != 0 &&
        GetTickCount64() >= g_proxy_restart_after) {
      if (StartProxy()) {
        g_proxy_restart_after = 0;
      }
    }
    return;
  }
  DWORD exit_code = STILL_ACTIVE;
  if (!GetExitCodeProcess(g_proxy.hProcess, &exit_code) ||
      exit_code != STILL_ACTIVE) {
    CloseProxyHandles();
    if (g_exiting) return;
    ++g_proxy_restart_failures;
    const ULONGLONG delay = std::min<ULONGLONG>(
        30000, 1000ULL << std::min(g_proxy_restart_failures, 5U));
    g_proxy_restart_after = GetTickCount64() + delay;
  }
}

void MonitorInstance(Instance& instance) {
  if (instance.child.hProcess == nullptr) {
    if (!instance.user_stopped && instance.restart_after != 0 &&
        GetTickCount64() >= instance.restart_after) {
      StartInstance(instance);
    }
    return;
  }
  DWORD exit_code = STILL_ACTIVE;
  if (!GetExitCodeProcess(instance.child.hProcess, &exit_code) ||
      exit_code != STILL_ACTIVE) {
    CloseChildHandles(instance);
    if (instance.user_stopped || g_exiting) {
      instance.state = InstanceState::kStopped;
      instance.status = L"Stopped";
      return;
    }
    ++instance.restart_failures;
    const ULONGLONG delay = std::min<ULONGLONG>(
        30000, 1000ULL << std::min(instance.restart_failures, 5U));
    instance.restart_after = GetTickCount64() + delay;
    instance.state = InstanceState::kFailed;
    instance.status = L"Failed - retrying";
    return;
  }
  if (ProbeReady(instance.health_port)) {
    instance.restart_failures = 0;
    instance.state = InstanceState::kReady;
    instance.status = ProxyConfigured() && !instance.web_origin.empty()
                          ? L"Ready - secure remote access"
                          : L"Ready";
  } else {
    instance.state = InstanceState::kDegraded;
    instance.status = L"Running - PLC unavailable";
  }
}

void MonitorAll() {
  MonitorProxy();
  bool anyReady = false;
  for (auto& instance : g_instances) {
    MonitorInstance(instance);
    anyReady = anyReady || instance.state == InstanceState::kReady;
  }
  // Clear the proxy backoff only from an observed healthy state, never merely
  // because a start call returned — a crash loop must keep backing off.
  if (anyReady && g_proxy.hProcess != nullptr) g_proxy_restart_failures = 0;
  UpdateAggregateStatus();
}

void OpenPath(const std::filesystem::path& path) {
  ShellExecuteW(g_window, L"open", path.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

void OpenUrl(const std::wstring& url) {
  ShellExecuteW(g_window, L"open", url.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

UINT InstanceCommandId(size_t index, UINT command) {
  return kInstanceMenuBase +
         static_cast<UINT>(index) * kInstanceMenuStride + command;
}

void AppendInstanceCommands(HMENU menu, size_t index) {
  const Instance& instance = g_instances[index];
  AppendMenuW(menu, MF_STRING | MF_DISABLED, kMenuStatus,
              (L"Status: " + instance.status).c_str());
  AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(menu, instance.child.hProcess == nullptr ? MF_STRING : MF_GRAYED,
              InstanceCommandId(index, kInstanceStart), L"Start");
  AppendMenuW(menu, instance.child.hProcess != nullptr ? MF_STRING : MF_GRAYED,
              InstanceCommandId(index, kInstanceStop), L"Stop");
  AppendMenuW(menu, MF_STRING, InstanceCommandId(index, kInstanceRestart),
              L"Restart");
  AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(menu, MF_STRING, InstanceCommandId(index, kInstanceConfig),
              L"Edit configuration...");
  AppendMenuW(menu, MF_STRING, InstanceCommandId(index, kInstanceLogs),
              L"Open logs");
  AppendMenuW(menu, MF_STRING, InstanceCommandId(index, kInstanceWebHmi),
              L"Open Web HMI");
  AppendMenuW(menu, MF_STRING, InstanceCommandId(index, kInstanceHealth),
              L"Open health page");
}

void ShowMenu() {
  POINT point{};
  GetCursorPos(&point);
  HMENU menu = CreatePopupMenu();
  std::vector<HMENU> submenus;
  if (g_instances.size() == 1) {
    // The common single-PLC install keeps the flat menu it always had.
    AppendInstanceCommands(menu, 0);
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  } else {
    AppendMenuW(menu, MF_STRING | MF_DISABLED, kMenuStatus,
                (L"Status: " + g_status).c_str());
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
    for (size_t index = 0; index < g_instances.size(); ++index) {
      HMENU submenu = CreatePopupMenu();
      AppendInstanceCommands(submenu, index);
      submenus.push_back(submenu);
      const Instance& instance = g_instances[index];
      AppendMenuW(menu, MF_POPUP, reinterpret_cast<UINT_PTR>(submenu),
                  (instance.name + L"  (" + instance.status + L")").c_str());
    }
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
    AppendMenuW(menu, MF_STRING, kMenuStartAll, L"Start all");
    AppendMenuW(menu, MF_STRING, kMenuStopAll, L"Stop all");
    AppendMenuW(menu, MF_STRING, kMenuRestartAll, L"Restart all");
    AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  }
  AppendMenuW(menu, MF_STRING, kMenuReload, L"Reload instances");
  if (ProxyConfigured()) {
    AppendMenuW(menu, MF_STRING, kMenuProxyConfig,
                L"Edit HTTPS proxy configuration...");
  }
  AppendMenuW(menu, MF_STRING, kMenuLogsRoot, L"Open logs folder");
  AppendMenuW(menu, MF_STRING, kMenuGuide, L"Deployment guide");
  AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(menu, MF_STRING, kMenuExit, L"Exit tray and all gateways");
  SetForegroundWindow(g_window);
  TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_BOTTOMALIGN,
                 point.x, point.y, 0, g_window, nullptr);
  for (HMENU submenu : submenus) DestroyMenu(submenu);
  DestroyMenu(menu);
}

bool HandleInstanceCommand(UINT id) {
  if (id < kInstanceMenuBase ||
      id >= kInstanceMenuBase + kInstanceMenuStride * kMaxInstances) {
    return false;
  }
  const size_t index = (id - kInstanceMenuBase) / kInstanceMenuStride;
  const UINT command = (id - kInstanceMenuBase) % kInstanceMenuStride;
  if (index >= g_instances.size()) return true;
  Instance& instance = g_instances[index];
  switch (command) {
    case kInstanceStart:
    case kInstanceRestart:
      if (command == kInstanceRestart) StopInstance(instance, false);
      instance.restart_failures = 0;
      if (!StartInstance(instance)) {
        instance.restart_after = GetTickCount64() + 1000;
      }
      // The proxy is host-wide: bringing one instance back up after a "Stop
      // all" must restore remote access with it.
      if (!StartProxy()) {
        g_proxy_restart_after = GetTickCount64() + 1000;
      }
      break;
    case kInstanceStop:
      StopInstance(instance, true);
      break;
    case kInstanceConfig:
      ShellExecuteW(g_window, L"open", L"notepad.exe",
                    Quote(instance.config_path.wstring()).c_str(), nullptr,
                    SW_SHOWNORMAL);
      break;
    case kInstanceLogs:
      OpenPath(instance.log_path.parent_path());
      break;
    case kInstanceWebHmi:
      OpenUrl(instance.web_origin.empty()
                  ? L"http://127.0.0.1:" +
                        std::to_wstring(instance.health_port) + L"/"
                  : instance.web_origin);
      break;
    case kInstanceHealth:
      OpenUrl(L"http://127.0.0.1:" + std::to_wstring(instance.health_port) +
              L"/healthz");
      break;
    default:
      break;
  }
  UpdateAggregateStatus();
  return true;
}

LRESULT CALLBACK WindowProc(HWND window, UINT message, WPARAM wparam,
                            LPARAM lparam) {
  if (message == g_taskbar_created) {
    Shell_NotifyIconW(NIM_ADD, &g_tray);
    return 0;
  }
  switch (message) {
    case WM_COMMAND:
      if (HandleInstanceCommand(LOWORD(wparam))) return 0;
      switch (LOWORD(wparam)) {
        case kMenuStartAll:
          StartAll();
          break;
        case kMenuStopAll:
          StopAll(true);
          break;
        case kMenuRestartAll:
          StopAll(false);
          StartAll();
          break;
        case kMenuReload:
          // Picks up an instance the installer added, renamed, or retired
          // without making the operator sign out and back in.
          StopAll(false);
          DiscoverInstances();
          StartAll();
          break;
        case kMenuProxyConfig:
          ShellExecuteW(window, L"open", L"notepad.exe",
                        Quote(g_proxy_config_path.wstring()).c_str(), nullptr,
                        SW_SHOWNORMAL);
          break;
        case kMenuLogsRoot:
          OpenPath(g_logs_dir);
          break;
        case kMenuGuide: {
          const auto walkthrough =
              g_install_dir / L"WEB_HMI_GATEWAY_DEPLOYMENT.md";
          OpenPath(std::filesystem::exists(walkthrough)
                       ? walkthrough
                       : g_install_dir / L"DEPLOYMENT.md");
          break;
        }
        case kMenuExit:
          DestroyWindow(window);
          break;
      }
      return 0;
    case WM_TIMER:
      if (wparam == kMonitorTimer) {
        if (g_stop_event != nullptr &&
            WaitForSingleObject(g_stop_event, 0) == WAIT_OBJECT_0) {
          DestroyWindow(window);
        } else {
          MonitorAll();
        }
      }
      return 0;
    case WM_DESTROY:
      g_exiting = true;
      StopAll(true);
      Shell_NotifyIconW(NIM_DELETE, &g_tray);
      PostQuitMessage(0);
      return 0;
    default:
      if (message == kTrayMessage &&
          (lparam == WM_RBUTTONUP || lparam == WM_CONTEXTMENU)) {
        ShowMenu();
        return 0;
      }
      if (message == kTrayMessage && lparam == WM_LBUTTONDBLCLK) {
        OpenPath(g_logs_dir);
        return 0;
      }
      return DefWindowProcW(window, message, wparam, lparam);
  }
}
}  // namespace

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE, PWSTR, int) {
  int argument_count = 0;
  LPWSTR* arguments = CommandLineToArgvW(GetCommandLineW(), &argument_count);
  const bool stop_requested = arguments != nullptr && argument_count == 2 &&
                              wcscmp(arguments[1], L"--stop") == 0;
  if (arguments != nullptr) LocalFree(arguments);
  if (stop_requested) {
    HANDLE stop_event = OpenEventW(
        EVENT_MODIFY_STATE, FALSE, L"Local\\FraktalGatewayTrayStop");
    if (stop_event != nullptr) {
      SetEvent(stop_event);
      CloseHandle(stop_event);
    }
    HANDLE existing = OpenMutexW(
        SYNCHRONIZE, FALSE, L"Local\\FraktalGatewayTray");
    if (existing != nullptr) {
      WaitForSingleObject(existing, 5000);
      CloseHandle(existing);
    }
    return 0;
  }
  HANDLE mutex = CreateMutexW(nullptr, TRUE, L"Local\\FraktalGatewayTray");
  if (mutex == nullptr || GetLastError() == ERROR_ALREADY_EXISTS) {
    if (mutex != nullptr) CloseHandle(mutex);
    return 0;
  }
  g_stop_event = CreateEventW(
      nullptr, TRUE, FALSE, L"Local\\FraktalGatewayTrayStop");
  wchar_t module_path[MAX_PATH]{};
  GetModuleFileNameW(nullptr, module_path, MAX_PATH);
  g_install_dir = std::filesystem::path(module_path).parent_path();
  wchar_t local_app_data[32768]{};
  ExpandEnvironmentStringsW(L"%LOCALAPPDATA%", local_app_data,
                            static_cast<DWORD>(std::size(local_app_data)));
  g_data_dir = std::filesystem::path(local_app_data) / L"Fraktal" / L"Gateway";
  g_instance_dir = g_data_dir / L"instances";
  g_logs_dir = g_data_dir / L"logs";
  g_proxy_config_path = g_data_dir / L"proxy" / L"Caddyfile";
  g_proxy_log_path = g_logs_dir / L"proxy.log";
  std::filesystem::create_directories(g_logs_dir);
  DiscoverInstances();

  g_taskbar_created = RegisterWindowMessageW(L"TaskbarCreated");
  WNDCLASSW window_class{};
  window_class.lpfnWndProc = WindowProc;
  window_class.hInstance = instance;
  window_class.lpszClassName = L"FraktalGatewayTrayWindow";
  RegisterClassW(&window_class);
  g_window = CreateWindowExW(0, window_class.lpszClassName,
                             L"Fraktal Gateway", 0, 0, 0, 0, 0,
                             nullptr, nullptr, instance, nullptr);
  if (g_window == nullptr) {
    CloseHandle(mutex);
    return 1;
  }
  g_tray.cbSize = sizeof(g_tray);
  g_tray.hWnd = g_window;
  g_tray.uID = 1;
  g_tray.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP;
  g_tray.uCallbackMessage = kTrayMessage;
  g_tray.hIcon = LoadIconW(nullptr, IDI_WARNING);
  wcscpy_s(g_tray.szTip, L"Fraktal Gateway - Starting");
  Shell_NotifyIconW(NIM_ADD, &g_tray);
  SetTimer(g_window, kMonitorTimer, 2000, nullptr);
  StartAll();

  MSG message{};
  while (GetMessageW(&message, nullptr, 0, 0) > 0) {
    TranslateMessage(&message);
    DispatchMessageW(&message);
  }
  if (g_stop_event != nullptr) CloseHandle(g_stop_event);
  CloseHandle(mutex);
  return static_cast<int>(message.wParam);
}
