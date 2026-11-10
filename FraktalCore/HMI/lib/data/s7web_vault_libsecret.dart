library;

import 'dart:ffi';

import 'package:ffi/ffi.dart';
import 'package:flutter/foundation.dart' show debugPrint;

import 's7web_vault_base.dart';
import 's7web_vault_io.dart' show decodeS7WebLogins, encodeS7WebLogins;

/// Linux: one item in the desktop keyring (Secret Service: GNOME Keyring,
/// KWallet's secret service, KeePassXC…) through libsecret, which the session
/// unlocks with the user's login. A panel with no keyring session (no D-Bus
/// session bus, libsecret not installed) returns null from [load], so the
/// HMI offers no "remember" box there and keeps the login in memory only.
///
/// Only the non-variadic libsecret entry points are used, so the binding is
/// plain FFI: `secret_schema_newv`, `secret_password_{lookup,store,clear}v_sync`.
class LibsecretS7WebVault implements S7WebVault {
  static const _schemaName = 'org.fraktal.hmi.S7WebLogins';
  static const _label = 'Fraktal HMI CPU web logins';

  _Libsecret? _lib;
  bool _opened = false;

  _Libsecret? get _secret {
    if (!_opened) {
      _opened = true;
      try {
        _lib = _Libsecret.open();
      } on Object catch (error) {
        debugPrint('[Fraktal/Connection] stage=s7web-vault-unavailable '
            'platform=linux detail=$error');
      }
    }
    return _lib;
  }

  @override
  Future<Map<String, S7WebLogin>?> load() async {
    final secret = _secret;
    if (secret == null) return null;
    try {
      return decodeS7WebLogins(secret.lookup());
    } on _SecretError catch (error) {
      debugPrint('[Fraktal/Connection] stage=s7web-vault-unavailable '
          'platform=linux detail=${error.message}');
      return null;
    }
  }

  @override
  Future<void> save(Map<String, S7WebLogin> logins) async {
    final secret = _secret;
    if (secret == null) return;
    if (logins.isEmpty) {
      secret.clear();
    } else {
      secret.store(_label, encodeS7WebLogins(logins));
    }
  }

  static String get schemaName => _schemaName;
}

class _SecretError implements Exception {
  final String message;
  _SecretError(this.message);
}

typedef _HashTableNewNative = Pointer<Void> Function(
    Pointer<NativeFunction<Uint32 Function(Pointer<Void>)>>,
    Pointer<NativeFunction<Int32 Function(Pointer<Void>, Pointer<Void>)>>);
typedef _HashTableInsertNative = Int32 Function(
    Pointer<Void>, Pointer<Void>, Pointer<Void>);
typedef _HashTableInsert = int Function(
    Pointer<Void>, Pointer<Void>, Pointer<Void>);
typedef _UnrefNative = Void Function(Pointer<Void>);
typedef _Unref = void Function(Pointer<Void>);
typedef _SchemaNewvNative = Pointer<Void> Function(
    Pointer<Utf8>, Int32, Pointer<Void>);
typedef _SchemaNewv = Pointer<Void> Function(Pointer<Utf8>, int, Pointer<Void>);
typedef _LookupNative = Pointer<Utf8> Function(Pointer<Void> schema,
    Pointer<Void> attributes, Pointer<Void> cancellable, Pointer<Pointer<_GError>> error);
typedef _StoreNative = Int32 Function(
    Pointer<Void> schema,
    Pointer<Void> attributes,
    Pointer<Utf8> collection,
    Pointer<Utf8> label,
    Pointer<Utf8> password,
    Pointer<Void> cancellable,
    Pointer<Pointer<_GError>> error);
typedef _Store = int Function(Pointer<Void>, Pointer<Void>, Pointer<Utf8>,
    Pointer<Utf8>, Pointer<Utf8>, Pointer<Void>, Pointer<Pointer<_GError>>);
typedef _ClearNative = Int32 Function(Pointer<Void> schema,
    Pointer<Void> attributes, Pointer<Void> cancellable, Pointer<Pointer<_GError>> error);
typedef _Clear = int Function(
    Pointer<Void>, Pointer<Void>, Pointer<Void>, Pointer<Pointer<_GError>>);
typedef _FreeStringNative = Void Function(Pointer<Utf8>);
typedef _FreeString = void Function(Pointer<Utf8>);
typedef _ErrorFreeNative = Void Function(Pointer<_GError>);
typedef _ErrorFree = void Function(Pointer<_GError>);

final class _GError extends Struct {
  @Uint32()
  external int domain;
  @Int32()
  external int code;
  external Pointer<Utf8> message;
}

/// The libsecret/GLib calls, the schema and the one attribute set naming the
/// item. Native strings handed to GLib live as long as the process.
class _Libsecret {
  final Pointer<Void> _schema;
  final Pointer<Void> Function() _attributes;
  final _Unref _hashUnref;
  final Pointer<Utf8> Function(Pointer<Void>, Pointer<Void>, Pointer<Void>,
      Pointer<Pointer<_GError>>) _lookup;
  final _Store _store;
  final _Clear _clear;
  final _FreeString _passwordFree;
  final _ErrorFree _errorFree;

  _Libsecret._(this._schema, this._attributes, this._hashUnref, this._lookup,
      this._store, this._clear, this._passwordFree, this._errorFree);

  factory _Libsecret.open() {
    final glib = DynamicLibrary.open('libglib-2.0.so.0');
    final secret = DynamicLibrary.open('libsecret-1.so.0');
    final hashNew = glib
        .lookupFunction<_HashTableNewNative, _HashTableNewNative>(
            'g_hash_table_new');
    final insert = glib.lookupFunction<_HashTableInsertNative, _HashTableInsert>(
        'g_hash_table_insert');
    final unref = glib.lookupFunction<_UnrefNative, _Unref>('g_hash_table_unref');
    final strHash = glib
        .lookup<NativeFunction<Uint32 Function(Pointer<Void>)>>('g_str_hash');
    final strEqual = glib.lookup<
        NativeFunction<Int32 Function(Pointer<Void>, Pointer<Void>)>>('g_str_equal');

    final application = 'application'.toNativeUtf8();
    final kind = 'kind'.toNativeUtf8();
    final applicationValue = 'fraktal-hmi'.toNativeUtf8();
    final kindValue = 's7web-logins'.toNativeUtf8();

    // Attribute types: SECRET_SCHEMA_ATTRIBUTE_STRING is 0 (GINT_TO_POINTER).
    final types = hashNew(strHash, strEqual);
    insert(types, application.cast(), nullptr);
    insert(types, kind.cast(), nullptr);
    final schema = secret.lookupFunction<_SchemaNewvNative, _SchemaNewv>(
        'secret_schema_newv')(
        LibsecretS7WebVault.schemaName.toNativeUtf8(), 0, types);
    unref(types);
    if (schema == nullptr) throw StateError('secret_schema_newv failed');

    Pointer<Void> attributes() {
      final table = hashNew(strHash, strEqual);
      insert(table, application.cast(), applicationValue.cast());
      insert(table, kind.cast(), kindValue.cast());
      return table;
    }

    return _Libsecret._(
      schema,
      attributes,
      unref,
      secret.lookupFunction<_LookupNative, _LookupNative>(
          'secret_password_lookupv_sync'),
      secret.lookupFunction<_StoreNative, _Store>('secret_password_storev_sync'),
      secret.lookupFunction<_ClearNative, _Clear>('secret_password_clearv_sync'),
      // Wipes the returned password before freeing it.
      secret.lookupFunction<_FreeStringNative, _FreeString>(
          'secret_password_free'),
      glib.lookupFunction<_ErrorFreeNative, _ErrorFree>('g_error_free'),
    );
  }

  T _call<T>(T Function(Pointer<Void>, Pointer<Pointer<_GError>>) body) {
    final attributes = _attributes();
    final error = calloc<Pointer<_GError>>();
    try {
      final result = body(attributes, error);
      if (error.value != nullptr) {
        final message = error.value.ref.message.toDartString();
        _errorFree(error.value);
        throw _SecretError(message);
      }
      return result;
    } finally {
      _hashUnref(attributes);
      calloc.free(error);
    }
  }

  String? lookup() => _call((attributes, error) {
        final value = _lookup(_schema, attributes, nullptr, error);
        if (value == nullptr) return null;
        final text = value.toDartString();
        _passwordFree(value);
        return text;
      });

  void store(String label, String value) {
    final nativeLabel = label.toNativeUtf8(allocator: calloc);
    final nativeValue = value.toNativeUtf8(allocator: calloc);
    try {
      _call((attributes, error) => _store(
          _schema, attributes, nullptr, nativeLabel, nativeValue, nullptr, error));
    } finally {
      final length = nativeValue.length;
      nativeValue.cast<Uint8>().asTypedList(length).fillRange(0, length, 0);
      calloc
        ..free(nativeLabel)
        ..free(nativeValue);
    }
  }

  void clear() =>
      _call((attributes, error) => _clear(_schema, attributes, nullptr, error));
}
