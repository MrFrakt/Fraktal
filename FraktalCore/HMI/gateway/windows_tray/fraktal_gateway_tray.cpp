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
constexpr UINT kMenuStart = 1002;
constexpr UINT kMenuStop = 1003;
constexpr UINT kMenuRestart = 1004;
constexpr UINT kMenuConfig = 1005;
constexpr UINT kMenuLogs = 1006;
constexpr UINT kMenuHealth = 1007;
constexpr UINT kMenuGuide = 1008;
constexpr UINT kMenuExit = 1009;
constexpr UINT kMenuWebHmi = 1010;

HWND g_window = nullptr;
NOTIFYICONDATAW g_tray{};
PROCESS_INFORMATION g_child{};
std::filesystem::path g_install_dir;
std::filesystem::path g_data_dir;
std::filesystem::path g_config_path;
std::filesystem::path g_log_path;
DWORD g_health_port = 8080;
bool g_user_stopped = false;
bool g_exiting = false;
unsigned g_restart_failures = 0;
ULONGLONG g_restart_after = 0;
std::wstring g_status = L"Starting";
HICON g_icon = nullptr;
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

std::vector<std::wstring> LoadArguments() {
  std::vector<std::wstring> arguments;
  std::ifstream stream(g_config_path, std::ios::binary);
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
  g_health_port = 8080;
  for (size_t index = 0; index + 1 < arguments.size(); ++index) {
    if (arguments[index] == L"--port") {
      try {
        g_health_port = std::stoul(arguments[index + 1]);
      } catch (...) {
        g_health_port = 8080;
      }
    }
  }
  return arguments;
}

void SetStatus(const std::wstring& status, HICON icon) {
  g_status = status;
  g_icon = icon;
  g_tray.hIcon = icon;
  const std::wstring tooltip = L"Fraktal Gateway - " + status;
  wcsncpy_s(g_tray.szTip, tooltip.c_str(), _TRUNCATE);
  Shell_NotifyIconW(NIM_MODIFY, &g_tray);
}

void CloseChildHandles() {
  if (g_child.hThread != nullptr) CloseHandle(g_child.hThread);
  if (g_child.hProcess != nullptr) CloseHandle(g_child.hProcess);
  g_child = {};
}

bool StartGateway() {
  if (g_child.hProcess != nullptr) return true;
  const auto executable = g_install_dir / L"fraktal_gateway.exe";
  if (!std::filesystem::exists(executable)) {
    SetStatus(L"Executable missing", LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  if (!std::filesystem::exists(g_config_path)) {
    SetStatus(L"Configuration missing", LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  std::filesystem::create_directories(g_log_path.parent_path());
  SECURITY_ATTRIBUTES security{};
  security.nLength = sizeof(security);
  security.bInheritHandle = TRUE;
  HANDLE log = CreateFileW(g_log_path.c_str(), FILE_APPEND_DATA,
                           FILE_SHARE_READ | FILE_SHARE_WRITE, &security,
                           OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
  if (log == INVALID_HANDLE_VALUE) {
    SetStatus(L"Cannot open log", LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  SetFilePointer(log, 0, nullptr, FILE_END);
  HANDLE null_input = CreateFileW(L"NUL", GENERIC_READ,
                                  FILE_SHARE_READ | FILE_SHARE_WRITE,
                                  &security, OPEN_EXISTING,
                                  FILE_ATTRIBUTE_NORMAL, nullptr);
  if (null_input == INVALID_HANDLE_VALUE) {
    CloseHandle(log);
    SetStatus(L"Cannot open process input", LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  std::wstring command = Quote(executable.wstring());
  for (const auto& argument : LoadArguments()) {
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
    SetStatus(L"Start failed", LoadIconW(nullptr, IDI_ERROR));
    return false;
  }
  g_child = process;
  g_user_stopped = false;
  SetStatus(L"Connecting", LoadIconW(nullptr, IDI_WARNING));
  return true;
}

void StopGateway(bool user_stopped) {
  g_user_stopped = user_stopped;
  g_restart_after = 0;
  if (g_child.hProcess != nullptr) {
    // The gateway owns no durable command queue. Forced local shutdown cannot
    // replay an HMI write and the PLC remains the final command authority.
    TerminateProcess(g_child.hProcess, 0);
    WaitForSingleObject(g_child.hProcess, 2000);
    CloseChildHandles();
  }
  if (!g_exiting) {
    SetStatus(user_stopped ? L"Stopped" : L"Restarting",
              LoadIconW(nullptr, user_stopped ? IDI_APPLICATION : IDI_WARNING));
  }
}

bool ProbeReady() {
  HINTERNET session = WinHttpOpen(
      L"FraktalGatewayTray/1.0", WINHTTP_ACCESS_TYPE_NO_PROXY,
      WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
  if (session == nullptr) return false;
  WinHttpSetTimeouts(session, 400, 400, 400, 400);
  HINTERNET connection = WinHttpConnect(
      session, L"127.0.0.1", static_cast<INTERNET_PORT>(g_health_port), 0);
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

void MonitorGateway() {
  if (g_child.hProcess == nullptr) {
    if (!g_user_stopped && g_restart_after != 0 &&
        GetTickCount64() >= g_restart_after) {
      StartGateway();
    }
    return;
  }
  DWORD exit_code = STILL_ACTIVE;
  if (!GetExitCodeProcess(g_child.hProcess, &exit_code) ||
      exit_code != STILL_ACTIVE) {
    CloseChildHandles();
    if (g_user_stopped || g_exiting || exit_code == 0) {
      SetStatus(L"Stopped", LoadIconW(nullptr, IDI_APPLICATION));
      return;
    }
    ++g_restart_failures;
    const ULONGLONG delay =
        std::min<ULONGLONG>(30000, 1000ULL << std::min(g_restart_failures, 5U));
    g_restart_after = GetTickCount64() + delay;
    SetStatus(L"Failed - retrying", LoadIconW(nullptr, IDI_ERROR));
    return;
  }
  if (ProbeReady()) {
    g_restart_failures = 0;
    SetStatus(L"Ready", LoadIconW(nullptr, IDI_INFORMATION));
  } else {
    SetStatus(L"Running - PLC unavailable", LoadIconW(nullptr, IDI_WARNING));
  }
}

void OpenPath(const std::filesystem::path& path) {
  ShellExecuteW(g_window, L"open", path.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
}

void ShowMenu() {
  POINT point{};
  GetCursorPos(&point);
  HMENU menu = CreatePopupMenu();
  AppendMenuW(menu, MF_STRING | MF_DISABLED, kMenuStatus,
              (L"Status: " + g_status).c_str());
  AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(menu, g_child.hProcess == nullptr ? MF_STRING : MF_GRAYED,
              kMenuStart, L"Start");
  AppendMenuW(menu, g_child.hProcess != nullptr ? MF_STRING : MF_GRAYED,
              kMenuStop, L"Stop");
  AppendMenuW(menu, MF_STRING, kMenuRestart, L"Restart");
  AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(menu, MF_STRING, kMenuConfig, L"Edit configuration...");
  AppendMenuW(menu, MF_STRING, kMenuLogs, L"Open logs");
  AppendMenuW(menu, MF_STRING, kMenuWebHmi, L"Open Web HMI");
  AppendMenuW(menu, MF_STRING, kMenuHealth, L"Open health page");
  AppendMenuW(menu, MF_STRING, kMenuGuide, L"Deployment guide");
  AppendMenuW(menu, MF_SEPARATOR, 0, nullptr);
  AppendMenuW(menu, MF_STRING, kMenuExit, L"Exit tray and gateway");
  SetForegroundWindow(g_window);
  TrackPopupMenu(menu, TPM_RIGHTBUTTON | TPM_BOTTOMALIGN,
                 point.x, point.y, 0, g_window, nullptr);
  DestroyMenu(menu);
}

LRESULT CALLBACK WindowProc(HWND window, UINT message, WPARAM wparam,
                            LPARAM lparam) {
  if (message == g_taskbar_created) {
    Shell_NotifyIconW(NIM_ADD, &g_tray);
    return 0;
  }
  switch (message) {
    case WM_COMMAND:
      switch (LOWORD(wparam)) {
        case kMenuStart:
          g_restart_failures = 0;
          StartGateway();
          break;
        case kMenuStop:
          StopGateway(true);
          break;
        case kMenuRestart:
          StopGateway(false);
          g_restart_failures = 0;
          StartGateway();
          break;
        case kMenuConfig:
          ShellExecuteW(window, L"open", L"notepad.exe",
                        Quote(g_config_path.wstring()).c_str(), nullptr,
                        SW_SHOWNORMAL);
          break;
        case kMenuLogs:
          OpenPath(g_log_path.parent_path());
          break;
        case kMenuWebHmi: {
          const std::wstring url = L"http://127.0.0.1:" +
                                   std::to_wstring(g_health_port) + L"/";
          ShellExecuteW(window, L"open", url.c_str(), nullptr, nullptr,
                        SW_SHOWNORMAL);
          break;
        }
        case kMenuHealth: {
          const std::wstring url = L"http://127.0.0.1:" +
                                   std::to_wstring(g_health_port) + L"/healthz";
          ShellExecuteW(window, L"open", url.c_str(), nullptr, nullptr,
                        SW_SHOWNORMAL);
          break;
        }
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
          MonitorGateway();
        }
      }
      return 0;
    case WM_DESTROY:
      g_exiting = true;
      StopGateway(true);
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
        OpenPath(g_log_path.parent_path());
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
  g_config_path = g_data_dir / L"gateway.args";
  g_log_path = g_data_dir / L"logs" / L"gateway.log";
  std::filesystem::create_directories(g_data_dir);

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
  StartGateway();

  MSG message{};
  while (GetMessageW(&message, nullptr, 0, 0) > 0) {
    TranslateMessage(&message);
    DispatchMessageW(&message);
  }
  if (g_stop_event != nullptr) CloseHandle(g_stop_event);
  CloseHandle(mutex);
  return static_cast<int>(message.wParam);
}
