import Flutter
import Security
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    if let registrar = engineBridge.pluginRegistry.registrar(forPlugin: "FraktalSecureStore") {
      SecureStore.register(messenger: registrar.messenger())
    }
  }
}

/// The HMI's `fraktal/secure_store` channel (lib/data/s7web_vault_io.dart):
/// small secrets such as remembered CPU web logins, kept as generic-password
/// items in this app's Keychain. Readable after the first unlock so a panel
/// that restarts unattended can log in, and never migrated to another device
/// or into a backup (`ThisDeviceOnly`).
enum SecureStore {
  private static let channel = "fraktal/secure_store"
  private static let service = "org.fraktal.hmi.secure_store"

  static func register(messenger: FlutterBinaryMessenger) {
    FlutterMethodChannel(name: channel, binaryMessenger: messenger)
      .setMethodCallHandler { call, result in
        guard let arguments = call.arguments as? [String: Any],
              let key = arguments["key"] as? String,
              key.range(of: "^[a-z0-9_]{1,64}$", options: .regularExpression) != nil
        else {
          result(FlutterError(code: "bad-key", message: "Unknown secure store entry", details: nil))
          return
        }
        do {
          switch call.method {
          case "read":
            result(try read(key))
          case "write":
            guard let value = arguments["value"] as? String else {
              result(FlutterError(code: "bad-value", message: "No value", details: nil))
              return
            }
            try write(key, value)
            result(nil)
          case "delete":
            try delete(key)
            result(nil)
          default:
            result(FlutterMethodNotImplemented)
          }
        } catch let error as NSError {
          // The status code only: never the stored value.
          result(FlutterError(code: "store-failed", message: "OSStatus \(error.code)", details: nil))
        }
      }
  }

  private static func query(_ key: String) -> [String: Any] {
    [
      kSecClass as String: kSecClassGenericPassword,
      kSecAttrService as String: service,
      kSecAttrAccount as String: key,
    ]
  }

  private static func failure(_ status: OSStatus) -> NSError {
    NSError(domain: NSOSStatusErrorDomain, code: Int(status))
  }

  static func read(_ key: String) throws -> String? {
    var request = query(key)
    request[kSecReturnData as String] = true
    request[kSecMatchLimit as String] = kSecMatchLimitOne
    var item: CFTypeRef?
    let status = SecItemCopyMatching(request as CFDictionary, &item)
    if status == errSecItemNotFound { return nil }
    guard status == errSecSuccess, let data = item as? Data else { throw failure(status) }
    return String(data: data, encoding: .utf8)
  }

  static func write(_ key: String, _ value: String) throws {
    let attributes: [String: Any] = [
      kSecValueData as String: Data(value.utf8),
      kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
    ]
    var status = SecItemUpdate(query(key) as CFDictionary, attributes as CFDictionary)
    if status == errSecItemNotFound {
      let item = query(key).merging(attributes) { _, new in new }
      status = SecItemAdd(item as CFDictionary, nil)
    }
    guard status == errSecSuccess else { throw failure(status) }
  }

  static func delete(_ key: String) throws {
    let status = SecItemDelete(query(key) as CFDictionary)
    guard status == errSecSuccess || status == errSecItemNotFound else { throw failure(status) }
  }
}
