#include "flutter_window.h"

#include <flutter/method_channel.h>
#include <flutter/standard_method_codec.h>

#include <memory>
#include <optional>

#include "flutter/generated_plugin_registrant.h"

namespace {

// Borderless-fullscreen state for the panel window. Saved so leaving fullscreen
// restores exactly the window the operator had.
struct FullscreenState {
  bool active = false;
  LONG style = 0;
  LONG ex_style = 0;
  RECT rect = {};
};

FullscreenState g_fullscreen;

bool SetFullscreen(HWND hwnd, bool enable) {
  if (enable == g_fullscreen.active) return g_fullscreen.active;
  if (enable) {
    g_fullscreen.style = GetWindowLong(hwnd, GWL_STYLE);
    g_fullscreen.ex_style = GetWindowLong(hwnd, GWL_EXSTYLE);
    GetWindowRect(hwnd, &g_fullscreen.rect);
    MONITORINFO mi = {sizeof(mi)};
    if (!GetMonitorInfo(MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST),
                        &mi)) {
      return false;
    }
    SetWindowLong(hwnd, GWL_STYLE,
                  g_fullscreen.style & ~(WS_CAPTION | WS_THICKFRAME));
    SetWindowLong(hwnd, GWL_EXSTYLE,
                  g_fullscreen.ex_style & ~(WS_EX_DLGMODALFRAME |
                                            WS_EX_WINDOWEDGE |
                                            WS_EX_CLIENTEDGE | WS_EX_STATICEDGE));
    SetWindowPos(hwnd, HWND_TOP, mi.rcMonitor.left, mi.rcMonitor.top,
                 mi.rcMonitor.right - mi.rcMonitor.left,
                 mi.rcMonitor.bottom - mi.rcMonitor.top,
                 SWP_NOOWNERZORDER | SWP_FRAMECHANGED);
  } else {
    SetWindowLong(hwnd, GWL_STYLE, g_fullscreen.style);
    SetWindowLong(hwnd, GWL_EXSTYLE, g_fullscreen.ex_style);
    SetWindowPos(hwnd, nullptr, g_fullscreen.rect.left, g_fullscreen.rect.top,
                 g_fullscreen.rect.right - g_fullscreen.rect.left,
                 g_fullscreen.rect.bottom - g_fullscreen.rect.top,
                 SWP_NOZORDER | SWP_NOOWNERZORDER | SWP_FRAMECHANGED);
  }
  g_fullscreen.active = enable;
  return g_fullscreen.active;
}

// Keeps display and system awake for an unattended machine panel. ES_CONTINUOUS
// holds until cleared, so the screen never blanks mid-shift.
void SetKeepAwake(bool enable) {
  SetThreadExecutionState(enable ? (ES_CONTINUOUS | ES_DISPLAY_REQUIRED |
                                    ES_SYSTEM_REQUIRED)
                                 : ES_CONTINUOUS);
}

}  // namespace

FlutterWindow::FlutterWindow(const flutter::DartProject& project)
    : project_(project) {}

FlutterWindow::~FlutterWindow() {}

bool FlutterWindow::OnCreate() {
  if (!Win32Window::OnCreate()) {
    return false;
  }

  RECT frame = GetClientArea();

  // The size here must match the window dimensions to avoid unnecessary surface
  // creation / destruction in the startup path.
  flutter_controller_ = std::make_unique<flutter::FlutterViewController>(
      frame.right - frame.left, frame.bottom - frame.top, project_);
  // Ensure that basic setup of the controller was successful.
  if (!flutter_controller_->engine() || !flutter_controller_->view()) {
    return false;
  }
  RegisterPlugins(flutter_controller_->engine());
  SetChildContent(flutter_controller_->view()->GetNativeWindow());

  // 'fraktal/panel' — panel-host services the Dart side calls (see
  // lib/data/panel_platform_io.dart): quit, fullscreen, and the wake lock that
  // stops an unattended panel blanking mid-shift.
  panel_channel_ = std::make_unique<
      flutter::MethodChannel<flutter::EncodableValue>>(
      flutter_controller_->engine()->messenger(), "fraktal/panel",
      &flutter::StandardMethodCodec::GetInstance());
  panel_channel_->SetMethodCallHandler(
      [this](const flutter::MethodCall<flutter::EncodableValue>& call,
             std::unique_ptr<flutter::MethodResult<flutter::EncodableValue>>
                 result) {
        HWND hwnd = GetHandle();
        const auto* args =
            std::get_if<flutter::EncodableMap>(call.arguments());
        auto bool_arg = [&](const char* name, bool fallback) {
          if (!args) return fallback;
          auto it = args->find(flutter::EncodableValue(name));
          if (it == args->end()) return fallback;
          const auto* value = std::get_if<bool>(&it->second);
          return value ? *value : fallback;
        };

        if (call.method_name() == "closeApp") {
          SetKeepAwake(false);
          PostMessage(hwnd, WM_CLOSE, 0, 0);
          result->Success();
        } else if (call.method_name() == "isFullscreen") {
          result->Success(flutter::EncodableValue(g_fullscreen.active));
        } else if (call.method_name() == "setFullscreen") {
          const bool reached = SetFullscreen(hwnd, bool_arg("value", false));
          result->Success(flutter::EncodableValue(reached));
        } else if (call.method_name() == "setKeepAwake") {
          SetKeepAwake(bool_arg("value", false));
          result->Success();
        } else {
          result->NotImplemented();
        }
      });

  flutter_controller_->engine()->SetNextFrameCallback([&]() {
    this->Show();
  });

  // Flutter can complete the first frame before the "show window" callback is
  // registered. The following call ensures a frame is pending to ensure the
  // window is shown. It is a no-op if the first frame hasn't completed yet.
  flutter_controller_->ForceRedraw();

  return true;
}

void FlutterWindow::OnDestroy() {
  if (flutter_controller_) {
    flutter_controller_ = nullptr;
  }

  Win32Window::OnDestroy();
}

LRESULT
FlutterWindow::MessageHandler(HWND hwnd, UINT const message,
                              WPARAM const wparam,
                              LPARAM const lparam) noexcept {
  // Give Flutter, including plugins, an opportunity to handle window messages.
  if (flutter_controller_) {
    std::optional<LRESULT> result =
        flutter_controller_->HandleTopLevelWindowProc(hwnd, message, wparam,
                                                      lparam);
    if (result) {
      return *result;
    }
  }

  switch (message) {
    case WM_FONTCHANGE:
      flutter_controller_->engine()->ReloadSystemFonts();
      break;
  }

  return Win32Window::MessageHandler(hwnd, message, wparam, lparam);
}
