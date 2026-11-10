# Native HMI on Linux, Android and iOS: build and acceptance checklist

Non-normative. The HMI contract is unchanged on every platform; this guide is the
work list for the first build and test of the Linux, Android and iOS targets,
and for the remembered CPU web login they carry. The normative description of
the login stores is `OPCUA_TRANSPORT.md`, "Direct native HMI".

## 1. Status (2026-10-17)

The `linux/`, `android/` and `ios/` targets were generated with
`flutter create` on Flutter 3.47.6 and extended by hand. **None of them has
been built yet**: the development PC has no Linux distribution, no Android SDK
and no Mac. Their Dart code passes `flutter analyze` and the shared HMI suite;
the Kotlin, Swift and CMake changes have been reviewed only.

| Area | State |
|---|---|
| Windows native HMI, remember login (DPAPI) | built, unit-tested, used against the simulated CPU |
| Gateway sealed login (`--plc-login-file`, `?pin=`) | built, connected to the simulated CPU 1516 |
| Windows installer wizard, `s7web://` instance | sealing helper tested; full wizard run **not yet done** |
| Linux gateway, systemd credentials | written; **not run** |
| Linux native HMI, keyring store, `libfraktal_opcua.so` | written; **not built** |
| Android native HMI, Keystore store | written; **not built** |
| iOS native HMI, Keychain store | written; **not built** |

On Android and iOS only the `s7web://` direct link and the gateway (`ws://`,
`wss://`) work. The native OPC UA and ADS libraries are not built for mobile.

## 2. Before the first install on a real device

### 2.1 Replace the application identifier

The generated targets use the placeholder `org.fraktal.fraktal_hmi`; Windows
still shows the template's `com.example`. Choose the plant or company identifier
**before** any device installs the app: on Android and iOS the remembered logins
belong to the app identity, so a later change installs as a new app and every
operator enters the CPU login once more. Lowercase letters, digits and dots
only (iOS refuses underscores), e.g. `com.yourcompany.fraktalhmi`.

| Platform | Where | What |
|---|---|---|
| Android | `FraktalCore/HMI/android/app/build.gradle.kts` | `applicationId` (line 19) and `namespace` (line 8) |
| Android | `android/app/src/main/kotlin/org/fraktal/fraktal_hmi/` | when `namespace` changes: move `MainActivity.kt` and `SecureStore.kt` to the matching folder and change their `package` line |
| iOS | `ios/Runner.xcodeproj/project.pbxproj` | all six `PRODUCT_BUNDLE_IDENTIFIER` lines; keep the `.RunnerTests` suffix (or Xcode: Runner → Signing & Capabilities → Bundle Identifier) |
| Linux | `linux/CMakeLists.txt` | `APPLICATION_ID` (line 10) |
| Windows | `windows/runner/Runner.rc` | `CompanyName` and `LegalCopyright` (file properties only) |

Nothing else in Fraktal reads the identifier. The internal store names
(`org.fraktal.hmi.secure_store`, keyring schema `org.fraktal.hmi.S7WebLogins`)
are independent labels and may stay.

### 2.2 Other one-time decisions

- **iOS signing team**: select it in Xcode; a device build needs one.
- **Display name**: Android `android:label` in `AndroidManifest.xml` is still
  `fraktal_hmi`; iOS shows `Fraktal HMI`.
- **Lockfile**: `flutter create` and a plain `flutter pub get` re-resolve
  `pubspec.lock`. Always use `flutter pub get --enforce-lockfile`; if the lock
  changed, restore it from git before building.

## 3. Build prerequisites

| Platform | Needs |
|---|---|
| Linux | Flutter's Linux desktop toolchain (clang, CMake, ninja, GTK 3 headers); `libsecret-1-0` at run time for the remember option; a desktop keyring (GNOME Keyring, KWallet's Secret Service, KeePassXC) unlocked by the session |
| Android | Android SDK and an emulator or device; `minSdk` is Flutter's default, at least API 23 (Keystore AES-GCM) |
| iOS | a Mac with Xcode and CocoaPods; a device or simulator on the plant network |

## 4. Acceptance checklist

Use a CPU you are authorized to connect to, and record the CPU identity, the
endpoint and pin, the app build and the device in the result. These steps log
in and read; they command nothing unless a step says so.

### 4.1 Every platform

1. `flutter build <linux|apk|ios>` succeeds; record warnings.
2. The wizard accepts `s7web://<CPU>?pin=<SHA-256>` and shows the CPU web user,
   password and **Remember on this device**.
3. Connect with the box **unticked**. Restart the app: the login screen asks
   again.
4. Connect with the box **ticked**. Restart the app: it reaches LIVE without
   the login screen, and the connection log shows `login=remembered`.
5. Enter the login again with the box **unticked**. Restart: the login screen
   asks again (the remembered login was removed).
6. Change the CPU web password in TIA Portal and download, or enter a wrong
   password with the box ticked. The CPU refuses it: the screen shows the
   refusal, and after a restart the app asks again instead of retrying the
   stale login.
7. The connection settings and the exported customization bundle contain no
   password, and neither does the HMI log.

### 4.2 Linux

1. On a desktop with a keyring: after step 4.1.4 the keyring holds one item
   labelled *Fraktal HMI CPU web logins*; its secret is never in a file of the
   app.
2. On a session **without** a keyring (no D-Bus session bus, or `libsecret`
   absent): the box is not offered, the log shows
   `stage=s7web-vault-unavailable`, and the memory-only login still works.
3. An `opc.tcp://` endpoint connects: the bundle contains
   `libfraktal_opcua.so` beside the executable.

### 4.3 Android

1. A release build (`flutter build apk --release`) connects; the main manifest
   carries the `INTERNET` permission.
2. After step 4.1.4, uninstalling and reinstalling the app asks for the login
   again.
3. Restore an app backup onto a new device: the restored entry does not open
   (the Keystore key is not in the backup) and the app simply asks for the
   login.

### 4.4 iOS

1. The first connection shows the local-network permission prompt with the
   `NSLocalNetworkUsageDescription` text; after **Allow** the CPU is reachable.
2. Restart the device and open the app **before** the first unlock: the login
   is not readable yet, so the app asks; after the first unlock it logs in by
   itself.
3. An encrypted device backup restored to another device carries no remembered
   login (`ThisDeviceOnly`).

### 4.5 Gateway + Web HMI

1. **Windows wizard, full run**: add an `s7web://` instance with the CPU web
   login, install, and confirm `instances\<name>\plc_login.json` exists, the
   instance's `gateway.args` carries `--plc-login-file` and no password, the
   install log names no password, and the tray's instance reaches
   `stage=connected`.
2. Upgrade with blank login fields: the stored login is kept.
3. Remove the instance: its `plc_login.json` is deleted, `gateway.args` is kept
   as `gateway.args.removed`.
4. Install as one Windows user and run the tray as another: the gateway refuses
   with "cannot be opened by this Windows user" (expected; set up as the tray's
   user).
5. **Linux systemd**: install `fraktal-gateway-s7web-login.conf.example` as the
   instance drop-in, seal both credentials with `systemd-creds encrypt`, and
   confirm the gateway logs `login=systemd-credentials` and `stage=connected`.
6. From a browser, the Web HMI renders the station; the browser never receives
   the CPU login.

## 5. Where the code is

| Piece | Path |
|---|---|
| Login store and vault contract | `FraktalCore/HMI/lib/data/s7web_credentials.dart`, `s7web_vault*.dart` |
| Linux keyring (libsecret FFI) | `FraktalCore/HMI/lib/data/s7web_vault_libsecret.dart` |
| Android Keystore | `FraktalCore/HMI/android/app/src/main/kotlin/.../SecureStore.kt`, `MainActivity.kt` |
| iOS Keychain | `FraktalCore/HMI/ios/Runner/AppDelegate.swift` |
| DPAPI seal shared by HMI and gateway | `FraktalCore/HMI/packages/fraktal_opcua_client/lib/user_seal.dart` |
| Gateway login sources, `--seal-plc-login` | `FraktalCore/HMI/gateway/bin/fraktal_gateway.dart` |
| Windows installer | `FraktalCore/HMI/gateway/deploy/windows/fraktal_instances.ps1`, `fraktal_wizard.ps1`, `install_gateway.ps1` |
| Linux systemd drop-in | `FraktalCore/HMI/gateway/deploy/linux/fraktal-gateway-s7web-login.conf.example` |
| Unit tests | `FraktalCore/HMI/test/s7web_direct_test.dart`, `connection_bootstrap_test.dart` |

## 6. Recording results

Record each completed run as a dated evidence note: build command and output,
Flutter/Xcode/SDK versions, device, CPU identity and the outcome of every
checklist line, with failures kept as failures. For a Siemens TIA station that
is `Specification/Siemens/Evidence/`. Then update the table in section 1.
