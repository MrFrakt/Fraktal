library;

import 'package:flutter/foundation.dart' show debugPrint, visibleForTesting;

import 's7web_endpoint.dart';
import 's7web_vault.dart';

/// The CPU web (UMAC) login for one direct `s7web://` target.
class S7WebCredentials {
  final String user;
  final String password;

  const S7WebCredentials(this.user, this.password);

  @override
  String toString() => 'S7WebCredentials(user: $user, password: <hidden>)';
}

/// The CPU web login is held in process memory by default and entered again
/// after the HMI restarts. Only when the operator ticks "remember" is it also
/// kept in the platform [S7WebVault] for the OS user (Windows DPAPI, the Linux
/// keyring, the Android Keystore or the iOS Keychain), so a saved endpoint
/// logs in by itself on the next start. It never goes to the connection
/// settings, the customization bundle or a log. A target is host, port AND
/// certificate pin, so a login can never follow an endpoint to a different
/// CPU.
class S7WebCredentialStore {
  S7WebCredentialStore({S7WebVault? vault})
      : _vault = vault ?? const UnavailableS7WebVault();

  S7WebVault _vault;
  final Map<String, S7WebCredentials> _byTarget = {};
  Map<String, S7WebLogin>? _saved;
  bool _ready = false;
  Future<Map<String, S7WebLogin>?>? _loading;
  Future<void>? _writes;

  /// Replaces the vault and starts over as a fresh HMI process would: no
  /// login in memory, the remembered ones read again by [ready].
  @visibleForTesting
  set vault(S7WebVault vault) {
    _vault = vault;
    _saved = null;
    _ready = false;
    _loading = null;
    _writes = null;
    _byTarget.clear();
  }

  /// Reads the remembered logins once. The connection screen and the s7web
  /// repository await it before asking or connecting. Only the result is
  /// kept, never a completed future, so no caller waits on a finished one.
  Future<void> ready() async {
    if (_ready) return;
    try {
      _saved = await (_loading ??= _vault.load());
    } on Object catch (error) {
      debugPrint('[Fraktal/Connection] stage=s7web-vault-unavailable '
          'detail=$error');
    }
    _ready = true;
    _loading = null;
  }

  /// Whether a login can be remembered across HMI starts here (after
  /// [ready]; false before, and where the platform keeps no user store).
  bool get canRemember => _saved != null;

  /// The vault writes still in flight, in order; tests await it.
  @visibleForTesting
  Future<void> get pendingWrites => _writes ?? Future.value();

  static String _key(S7WebEndpoint target) =>
      '${target.host}:${target.port}#${target.pinSha256}';

  S7WebCredentials? lookup(S7WebEndpoint target) {
    final key = _key(target);
    final entered = _byTarget[key];
    if (entered != null) return entered;
    final saved = _saved?[key];
    return saved == null ? null : S7WebCredentials(saved.user, saved.password);
  }

  /// True when [target]'s login is remembered across HMI starts.
  bool isRemembered(S7WebEndpoint target) =>
      _saved?.containsKey(_key(target)) ?? false;

  /// Holds the login for this process and, with [persist], remembers it;
  /// without it any remembered login for the target is removed, so unticking
  /// the box is how an operator makes the HMI forget.
  void remember(S7WebEndpoint target, String user, String password,
      {bool persist = false}) {
    final key = _key(target);
    _byTarget[key] = S7WebCredentials(user, password);
    final saved = _saved;
    if (saved == null) return;
    final current = saved[key];
    if (persist) {
      if (current?.user == user && current?.password == password) return;
      saved[key] = (user: user, password: password);
    } else {
      if (current == null) return;
      saved.remove(key);
    }
    _persist(saved);
  }

  /// Drops the login everywhere, used when the CPU refuses it.
  void forget(S7WebEndpoint target) {
    final key = _key(target);
    _byTarget.remove(key);
    final saved = _saved;
    if (saved != null && saved.remove(key) != null) _persist(saved);
  }

  /// Queues one write of the whole set behind any still in flight, so the
  /// vault always ends with the latest state.
  void _persist(Map<String, S7WebLogin> saved) {
    final snapshot = Map.of(saved);
    final vault = _vault;
    final previous = _writes;
    late final Future<void> current;
    current = () async {
      if (previous != null) await previous;
      try {
        await vault.save(snapshot);
      } on Object catch (error) {
        debugPrint(
            '[Fraktal/Connection] stage=s7web-vault-write-failed detail=$error');
      }
      if (identical(_writes, current)) _writes = null;
    }();
    _writes = current;
  }

  /// The user name last entered for [target], to prefill the prompt; the
  /// password is never offered back.
  String userFor(S7WebEndpoint target) => lookup(target)?.user ?? '';
}

/// The one store of this HMI process.
final s7WebCredentials = S7WebCredentialStore(vault: createS7WebVault());

/// The direct link cannot log in: no CPU web login is known for the target,
/// or the CPU refused the one that was offered. Not retried automatically;
/// the connection screen asks the operator instead.
class S7WebLoginRequired implements Exception {
  final bool rejected;

  const S7WebLoginRequired({required this.rejected});

  @override
  String toString() => rejected
      ? 'The CPU refused the web login for this s7web:// endpoint.'
      : 'A CPU web login is required for this s7web:// endpoint.';
}
