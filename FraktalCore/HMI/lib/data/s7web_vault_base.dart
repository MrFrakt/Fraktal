library;

/// A remembered CPU web login.
typedef S7WebLogin = ({String user, String password});

/// Where a CPU web login the operator chose to remember is kept between HMI
/// starts. Entries are keyed by target (host, port AND certificate pin) and
/// protected by the platform for the current OS user: Windows DPAPI, the
/// Linux desktop keyring (Secret Service), the Android Keystore or the iOS
/// Keychain. Asynchronous because the mobile stores are reached through a
/// platform channel.
abstract class S7WebVault {
  /// The remembered logins by target key, or null when this platform (or
  /// this session: no keyring, no platform store) cannot remember any; the
  /// HMI then offers no "remember" box. A corrupt or foreign entry is simply
  /// absent, so the HMI asks again instead of failing.
  Future<Map<String, S7WebLogin>?> load();

  /// Replaces every remembered login; an empty map removes the store entry.
  Future<void> save(Map<String, S7WebLogin> logins);
}

/// No persistence: Web builds (a browser reaches a TIA station through the
/// gateway, which holds the CPU login) and platforms without a user store.
class UnavailableS7WebVault implements S7WebVault {
  const UnavailableS7WebVault();

  @override
  Future<Map<String, S7WebLogin>?> load() async => null;

  @override
  Future<void> save(Map<String, S7WebLogin> logins) async {}
}
