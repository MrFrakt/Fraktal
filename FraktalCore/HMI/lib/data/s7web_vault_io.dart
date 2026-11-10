library;

import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart' show debugPrint;
import 'package:flutter/services.dart';
import 'package:fraktal_opcua_client/user_seal.dart';

import 's7web_vault_base.dart';
import 's7web_vault_libsecret.dart';

/// The platform's user-bound store. Tests never touch the operator's real
/// store (the HMI log follows the same rule).
S7WebVault createS7WebVault() {
  if (Platform.environment.containsKey('FLUTTER_TEST')) {
    return const UnavailableS7WebVault();
  }
  if (Platform.isWindows) {
    final env = Platform.environment;
    final base =
        env['APPDATA'] ?? env['LOCALAPPDATA'] ?? Directory.current.path;
    final sep = Platform.pathSeparator;
    return DpapiS7WebVault(
        File('$base${sep}Fraktal${sep}HMI${sep}s7web_logins.json'));
  }
  if (Platform.isLinux) return LibsecretS7WebVault();
  if (Platform.isAndroid || Platform.isIOS) return PlatformChannelS7WebVault();
  return const UnavailableS7WebVault();
}

/// The logins as one JSON document, the value every store below keeps.
String encodeS7WebLogins(Map<String, S7WebLogin> logins) => jsonEncode({
      'version': 1,
      'logins': {
        for (final entry in logins.entries)
          entry.key: {'user': entry.value.user, 'password': entry.value.password}
      },
    });

Map<String, S7WebLogin> decodeS7WebLogins(String? text) {
  final result = <String, S7WebLogin>{};
  if (text == null) return result;
  try {
    final document = jsonDecode(text);
    final logins = document is Map && document['version'] == 1
        ? document['logins']
        : null;
    if (logins is! Map) return result;
    for (final entry in logins.entries) {
      final login = entry.value;
      if (entry.key is String &&
          login is Map &&
          login['user'] is String &&
          login['password'] is String) {
        result[entry.key as String] =
            (user: login['user'] as String, password: login['password'] as String);
      }
    }
  } on FormatException {
    // Unreadable: ask the operator again.
  }
  return result;
}

/// Windows: each login sealed with DPAPI for the current Windows user (the
/// same protection as the `Start-TiaHmiDirect.ps1` secret file) in
/// `%APPDATA%\Fraktal\HMI\s7web_logins.json`.
class DpapiS7WebVault implements S7WebVault {
  final File file;
  DpapiS7WebVault(this.file);

  static const _version = 1;

  /// Binds each sealed login to its own target, so an entry copied under
  /// another key in the file does not open.
  static String _purpose(String key) => 'Fraktal.HMI.s7web.v1\n$key';

  @override
  Future<Map<String, S7WebLogin>?> load() async {
    final result = <String, S7WebLogin>{};
    try {
      if (!file.existsSync()) return result;
      final document = jsonDecode(file.readAsStringSync());
      if (document is! Map || document['version'] != _version) return result;
      final logins = document['logins'];
      if (logins is! Map) return result;
      for (final entry in logins.entries) {
        final key = entry.key;
        final sealed = entry.value;
        if (key is! String || sealed is! String) continue;
        final plain = UserSeal.unprotect(base64Decode(sealed), _purpose(key));
        if (plain == null) continue;
        final login = jsonDecode(utf8.decode(plain));
        if (login is Map &&
            login['user'] is String &&
            login['password'] is String) {
          result[key] = (user: login['user'], password: login['password']);
        }
      }
    } on Object {
      // Unreadable or tampered: ask the operator again.
    }
    return result;
  }

  @override
  Future<void> save(Map<String, S7WebLogin> logins) async {
    final sealed = <String, String>{};
    for (final entry in logins.entries) {
      final plain = utf8.encode(jsonEncode(
          {'user': entry.value.user, 'password': entry.value.password}));
      final blob = UserSeal.protect(plain, _purpose(entry.key));
      if (blob != null) sealed[entry.key] = base64Encode(blob);
    }
    if (sealed.isEmpty) {
      if (file.existsSync()) file.deleteSync();
      return;
    }
    file.parent.createSync(recursive: true);
    final temp = File('${file.path}.tmp');
    temp.writeAsStringSync(
        jsonEncode({'version': _version, 'logins': sealed}),
        flush: true);
    if (file.existsSync()) file.deleteSync();
    temp.renameSync(file.path);
  }
}

/// Android and iOS: the app's own `fraktal/secure_store` channel (no plugin
/// package). Android seals the value with an AES-GCM key held in the Android
/// Keystore; iOS keeps it in the Keychain, readable after first unlock and
/// never migrated to another device. See `MainActivity.kt` / `AppDelegate.swift`.
class PlatformChannelS7WebVault implements S7WebVault {
  static const channel = MethodChannel('fraktal/secure_store');
  static const _key = 's7web_logins';

  @override
  Future<Map<String, S7WebLogin>?> load() async {
    try {
      return decodeS7WebLogins(
          await channel.invokeMethod<String>('read', {'key': _key}));
    } on MissingPluginException {
      return null;
    } on PlatformException catch (error) {
      debugPrint('[Fraktal/Connection] stage=s7web-vault-unavailable '
          'platform=channel code=${error.code}');
      return null;
    }
  }

  @override
  Future<void> save(Map<String, S7WebLogin> logins) async {
    if (logins.isEmpty) {
      await channel.invokeMethod<void>('delete', {'key': _key});
    } else {
      await channel.invokeMethod<void>(
          'write', {'key': _key, 'value': encodeS7WebLogins(logins)});
    }
  }
}
