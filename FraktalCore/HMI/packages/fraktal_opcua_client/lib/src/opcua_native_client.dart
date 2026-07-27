library;

import 'dart:async';
import 'dart:convert';
import 'dart:ffi';
import 'dart:isolate';
import 'dart:io';
import 'package:ffi/ffi.dart';
import 'opcua_session_client.dart';

const String kOpcUaBasic256Sha256 =
    'http://opcfoundation.org/UA/SecurityPolicy#Basic256Sha256';

enum OpcUaSecurityProfile {
  production,
  secureAnonymous,
  commissioningAnonymous,
  isolatedAnonymous,
}

class OpcUaSecurityOptions {
  final OpcUaSecurityProfile profile;
  final String securityPolicyUri;
  final String applicationUri;
  final String clientCertificatePath;
  final String clientPrivateKeyPath;
  final String clientPrivateKeyPassword;
  final String trustListPath;
  final String revocationListPath;

  const OpcUaSecurityOptions({
    required this.profile,
    this.securityPolicyUri = kOpcUaBasic256Sha256,
    this.applicationUri = '',
    this.clientCertificatePath = '',
    this.clientPrivateKeyPath = '',
    this.clientPrivateKeyPassword = '',
    this.trustListPath = '',
    this.revocationListPath = '',
  });

  const OpcUaSecurityOptions.commissioningAnonymous()
      : this(profile: OpcUaSecurityProfile.commissioningAnonymous);

  const OpcUaSecurityOptions.isolatedAnonymous()
      : this(profile: OpcUaSecurityProfile.isolatedAnonymous);

  bool get encrypted =>
      profile == OpcUaSecurityProfile.production ||
      profile == OpcUaSecurityProfile.secureAnonymous;

  int get nativeProfile => switch (profile) {
        OpcUaSecurityProfile.production => 1,
        OpcUaSecurityProfile.secureAnonymous => 2,
        OpcUaSecurityProfile.commissioningAnonymous ||
        OpcUaSecurityProfile.isolatedAnonymous =>
          0,
      };

  void validate({required String username}) {
    if (!encrypted) return;
    if (securityPolicyUri.isEmpty ||
        applicationUri.isEmpty ||
        clientCertificatePath.isEmpty ||
        clientPrivateKeyPath.isEmpty ||
        trustListPath.isEmpty) {
      throw ArgumentError(
        'Secure OPC UA requires a security policy, application URI, client '
        'certificate, private key, and trust-list paths.',
      );
    }
    if (profile == OpcUaSecurityProfile.production && username.isEmpty) {
      throw ArgumentError(
        'The production OPC UA profile requires an authenticated user.',
      );
    }
  }
}

/// Isolate-owned native OPC UA session. Every potentially blocking call stays
/// off Flutter's UI isolate; request/reply messages contain only Dart values.
class NativeOpcUaClient
    implements OpcUaTieredReadClient, OpcUaBulkReadClient {
  final Isolate _isolate;
  final SendPort _worker;
  final ReceivePort _responses;
  final StreamSubscription<Object?> _subscription;
  final Map<int, Completer<Object?>> _pending = {};
  int _nextId = 1;
  bool _closed = false;

  NativeOpcUaClient._(
      this._isolate, this._worker, this._responses, this._subscription);

  static Future<NativeOpcUaClient> connect(
    Uri endpoint, {
    String username = '',
    String password = '',
    Duration timeout = const Duration(seconds: 5),
    OpcUaSecurityOptions security =
        const OpcUaSecurityOptions.commissioningAnonymous(),
  }) async {
    security.validate(username: username);
    // A ReceivePort is single-subscription: the same listener must carry the
    // SendPort handshake and every later response for the client's lifetime.
    final responses = ReceivePort();
    final ready = Completer<SendPort>();
    NativeOpcUaClient? client;
    final subscription = responses.listen((message) {
      if (message is SendPort) {
        if (!ready.isCompleted) ready.complete(message);
        return;
      }
      client?._onResponse(message);
    });
    Isolate? isolate;
    try {
      isolate = await Isolate.spawn(_opcUaWorkerMain, responses.sendPort,
          debugName: 'fraktal-opcua');
      final worker = await ready.future.timeout(timeout);
      client = NativeOpcUaClient._(isolate, worker, responses, subscription);
      await client._call('connect', {
        'endpoint': endpoint.toString(),
        'username': username,
        'password': password,
        'timeoutMs': timeout.inMilliseconds,
        'securityProfile': security.nativeProfile,
        'securityPolicyUri': security.securityPolicyUri,
        'applicationUri': security.applicationUri,
        'clientCertificatePath': security.clientCertificatePath,
        'clientPrivateKeyPath': security.clientPrivateKeyPath,
        'clientPrivateKeyPassword': security.clientPrivateKeyPassword,
        'trustListPath': security.trustListPath,
        'revocationListPath': security.revocationListPath,
      });
      return client;
    } on Object {
      await subscription.cancel();
      responses.close();
      isolate?.kill(priority: Isolate.immediate);
      rethrow;
    }
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    final value = await _call('snapshot');
    if (value is! Map) throw StateError('Native OPC UA snapshot is not a map.');
    return Map<String, Object?>.from(value);
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async =>
      (await _call('write', {
        'path': path,
        'valueType': type.name,
        'value': value,
      })) ==
      true;

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    final value =
        await _call('readValues', {'paths': browsePaths.join('\n')});
    if (value is! Map) return const {};
    final raw = value['values'];
    if (raw is! Map) return const {};
    return {for (final entry in raw.entries) '${entry.key}': entry.value};
  }

  @override
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {
    await _call('setSlowPaths', {'paths': browsePaths.join('\n')});
  }

  @override
  Future<void> refreshSlowPaths() async {
    await _call('refreshSlow');
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    await _call('setExcludedPaths', {'paths': browsePaths.join('\n')});
  }

  Future<Object?> _call(String operation, [Map<String, Object?>? arguments]) {
    if (_closed) return Future.error(StateError('OPC UA client is closed.'));
    final id = _nextId++;
    final completer = Completer<Object?>();
    _pending[id] = completer;
    _worker.send({
      'id': id,
      'operation': operation,
      ...?arguments,
    });
    return completer.future;
  }

  void _onResponse(Object? message) {
    if (message is! Map) return;
    final id = message['id'];
    if (id is! int) return;
    final completer = _pending.remove(id);
    if (completer == null) return;
    if (message['ok'] == true) {
      completer.complete(message['value']);
    } else {
      completer.completeError(StateError('${message['error']}'));
    }
  }

  @override
  Future<void> close() async {
    if (_closed) return;
    try {
      await _call('close').timeout(const Duration(seconds: 2));
    } on Object {
      // The isolate is terminated below even if native disconnect failed.
    }
    _closed = true;
    for (final completer in _pending.values) {
      if (!completer.isCompleted) {
        completer.completeError(StateError('OPC UA client closed.'));
      }
    }
    _pending.clear();
    await _subscription.cancel();
    _responses.close();
    _isolate.kill(priority: Isolate.immediate);
  }
}

void _opcUaWorkerMain(SendPort host) async {
  final inbox = ReceivePort();
  host.send(inbox.sendPort);
  _NativeBindings? bindings;
  Pointer<Void> handle = nullptr;

  await for (final message in inbox) {
    if (message is! Map) continue;
    final id = message['id'];
    final operation = message['operation'];
    if (id is! int || operation is! String) continue;
    try {
      bindings ??= _NativeBindings.open();
      if (handle == nullptr) handle = bindings.create();
      switch (operation) {
        case 'connect':
          final endpoint = '${message['endpoint']}'.toNativeUtf8();
          final username = '${message['username'] ?? ''}'.toNativeUtf8();
          final password = '${message['password'] ?? ''}'.toNativeUtf8();
          final policy = '${message['securityPolicyUri'] ?? ''}'.toNativeUtf8();
          final applicationUri =
              '${message['applicationUri'] ?? ''}'.toNativeUtf8();
          final certificatePath =
              '${message['clientCertificatePath'] ?? ''}'.toNativeUtf8();
          final privateKeyPath =
              '${message['clientPrivateKeyPath'] ?? ''}'.toNativeUtf8();
          final privateKeyPassword =
              '${message['clientPrivateKeyPassword'] ?? ''}'.toNativeUtf8();
          final trustListPath =
              '${message['trustListPath'] ?? ''}'.toNativeUtf8();
          final revocationListPath =
              '${message['revocationListPath'] ?? ''}'.toNativeUtf8();
          try {
            final connected = bindings.connectSecure(
                  handle,
                  endpoint,
                  username,
                  password,
                  (message['timeoutMs'] as num).toInt(),
                  (message['securityProfile'] as num).toInt(),
                  policy,
                  applicationUri,
                  certificatePath,
                  privateKeyPath,
                  privateKeyPassword,
                  trustListPath,
                  revocationListPath,
                ) ==
                1;
            if (!connected) throw StateError(bindings.error(handle));
          } finally {
            malloc.free(endpoint);
            malloc.free(username);
            malloc.free(password);
            malloc.free(policy);
            malloc.free(applicationUri);
            malloc.free(certificatePath);
            malloc.free(privateKeyPath);
            malloc.free(privateKeyPassword);
            malloc.free(trustListPath);
            malloc.free(revocationListPath);
          }
          host.send({'id': id, 'ok': true, 'value': true});
        case 'snapshot':
          final pointer = bindings.snapshot(handle);
          if (pointer == nullptr) throw StateError(bindings.error(handle));
          try {
            final decoded = jsonDecode(pointer.toDartString());
            host.send({'id': id, 'ok': true, 'value': decoded});
          } finally {
            bindings.freeString(pointer);
          }
        case 'write':
          final path = '${message['path']}'.toNativeUtf8();
          try {
            final type =
                OpcUaWriteType.values.byName('${message['valueType']}');
            final value = message['value'];
            final accepted = switch (type) {
              OpcUaWriteType.boolean =>
                bindings.writeBool(handle, path, value == true ? 1 : 0),
              OpcUaWriteType.int32 =>
                bindings.writeInt32(handle, path, (value as num).toInt()),
              OpcUaWriteType.uint32 =>
                bindings.writeUint32(handle, path, (value as num).toInt()),
              OpcUaWriteType.int64 =>
                bindings.writeInt64(handle, path, (value as num).toInt()),
              OpcUaWriteType.doubleValue =>
                bindings.writeDouble(handle, path, (value as num).toDouble()),
              OpcUaWriteType.string =>
                _writeNativeString(bindings, handle, path, '$value'),
            };
            if (accepted != 1) throw StateError(bindings.error(handle));
            host.send({'id': id, 'ok': true, 'value': true});
          } finally {
            malloc.free(path);
          }
        case 'readValues':
          final pathsBlob = '${message['paths'] ?? ''}'.toNativeUtf8();
          try {
            final pointer = bindings.readValues(handle, pathsBlob);
            if (pointer == nullptr) throw StateError(bindings.error(handle));
            try {
              final decoded = jsonDecode(pointer.toDartString());
              host.send({'id': id, 'ok': true, 'value': decoded});
            } finally {
              bindings.freeString(pointer);
            }
          } finally {
            malloc.free(pathsBlob);
          }
        case 'setSlowPaths':
          final blob = '${message['paths'] ?? ''}'.toNativeUtf8();
          try {
            bindings.setSlowPaths(handle, blob);
            host.send({'id': id, 'ok': true, 'value': true});
          } finally {
            malloc.free(blob);
          }
        case 'refreshSlow':
          bindings.refreshSlow(handle);
          host.send({'id': id, 'ok': true, 'value': true});
        case 'setExcludedPaths':
          final blob = '${message['paths'] ?? ''}'.toNativeUtf8();
          try {
            bindings.setExcludedPaths(handle, blob);
            host.send({'id': id, 'ok': true, 'value': true});
          } finally {
            malloc.free(blob);
          }
        case 'close':
          bindings.disconnect(handle);
          bindings.destroy(handle);
          handle = nullptr;
          host.send({'id': id, 'ok': true, 'value': true});
          inbox.close();
        default:
          throw UnsupportedError('Unknown native OPC UA operation: $operation');
      }
    } on Object catch (error, stackTrace) {
      host.send({
        'id': id,
        'ok': false,
        'error': '$error',
        'stack': '$stackTrace',
      });
    }
  }
  if (handle != nullptr && bindings != null) {
    bindings.disconnect(handle);
    bindings.destroy(handle);
  }
}

int _writeNativeString(_NativeBindings bindings, Pointer<Void> handle,
    Pointer<Utf8> path, String value) {
  final nativeValue = value.toNativeUtf8();
  try {
    return bindings.writeString(handle, path, nativeValue);
  } finally {
    malloc.free(nativeValue);
  }
}

typedef _CreateNative = Pointer<Void> Function();
typedef _DestroyNative = Void Function(Pointer<Void>);
typedef _ConnectNative = Int32 Function(
    Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>, Pointer<Utf8>, Uint32);
typedef _ConnectSecureNative = Int32 Function(
    Pointer<Void>,
    Pointer<Utf8>,
    Pointer<Utf8>,
    Pointer<Utf8>,
    Uint32,
    Int32,
    Pointer<Utf8>,
    Pointer<Utf8>,
    Pointer<Utf8>,
    Pointer<Utf8>,
    Pointer<Utf8>,
    Pointer<Utf8>,
    Pointer<Utf8>);
typedef _DisconnectNative = Void Function(Pointer<Void>);
typedef _LastErrorNative = Pointer<Utf8> Function(Pointer<Void>);
typedef _SnapshotNative = Pointer<Utf8> Function(Pointer<Void>);
typedef _FreeStringNative = Void Function(Pointer<Utf8>);
typedef _WriteBoolNative = Int32 Function(Pointer<Void>, Pointer<Utf8>, Int32);
typedef _WriteInt32Native = Int32 Function(Pointer<Void>, Pointer<Utf8>, Int32);
typedef _WriteUint32Native = Int32 Function(
    Pointer<Void>, Pointer<Utf8>, Uint32);
typedef _WriteInt64Native = Int32 Function(Pointer<Void>, Pointer<Utf8>, Int64);
typedef _WriteDoubleNative = Int32 Function(
    Pointer<Void>, Pointer<Utf8>, Double);
typedef _WriteStringNative = Int32 Function(
    Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>);
typedef _SetSlowPathsNative = Int32 Function(Pointer<Void>, Pointer<Utf8>);
typedef _RefreshSlowNative = Void Function(Pointer<Void>);
typedef _SetExcludedPathsNative = Int32 Function(Pointer<Void>, Pointer<Utf8>);
typedef _ReadValuesNative = Pointer<Utf8> Function(Pointer<Void>, Pointer<Utf8>);

class _NativeBindings {
  final Pointer<Void> Function() create;
  final void Function(Pointer<Void>) destroy;
  final int Function(
      Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>, Pointer<Utf8>, int) connect;
  final int Function(
      Pointer<Void>,
      Pointer<Utf8>,
      Pointer<Utf8>,
      Pointer<Utf8>,
      int,
      int,
      Pointer<Utf8>,
      Pointer<Utf8>,
      Pointer<Utf8>,
      Pointer<Utf8>,
      Pointer<Utf8>,
      Pointer<Utf8>,
      Pointer<Utf8>) connectSecure;
  final void Function(Pointer<Void>) disconnect;
  final Pointer<Utf8> Function(Pointer<Void>) _lastError;
  final Pointer<Utf8> Function(Pointer<Void>) snapshot;
  final void Function(Pointer<Utf8>) freeString;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeBool;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeInt32;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeUint32;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeInt64;
  final int Function(Pointer<Void>, Pointer<Utf8>, double) writeDouble;
  final int Function(Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>) writeString;
  final int Function(Pointer<Void>, Pointer<Utf8>) setSlowPaths;
  final void Function(Pointer<Void>) refreshSlow;
  final int Function(Pointer<Void>, Pointer<Utf8>) setExcludedPaths;
  final Pointer<Utf8> Function(Pointer<Void>, Pointer<Utf8>) readValues;

  _NativeBindings(DynamicLibrary library)
      : create = library
            .lookupFunction<_CreateNative, _CreateNative>('frk_opcua_create'),
        destroy = library.lookupFunction<_DestroyNative,
            void Function(Pointer<Void>)>('frk_opcua_destroy'),
        connect = library.lookupFunction<
            _ConnectNative,
            int Function(Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>,
                Pointer<Utf8>, int)>('frk_opcua_connect'),
        connectSecure = library.lookupFunction<
            _ConnectSecureNative,
            int Function(
                Pointer<Void>,
                Pointer<Utf8>,
                Pointer<Utf8>,
                Pointer<Utf8>,
                int,
                int,
                Pointer<Utf8>,
                Pointer<Utf8>,
                Pointer<Utf8>,
                Pointer<Utf8>,
                Pointer<Utf8>,
                Pointer<Utf8>,
                Pointer<Utf8>)>('frk_opcua_connect_secure'),
        disconnect = library.lookupFunction<_DisconnectNative,
            void Function(Pointer<Void>)>('frk_opcua_disconnect'),
        _lastError = library.lookupFunction<_LastErrorNative,
            Pointer<Utf8> Function(Pointer<Void>)>('frk_opcua_last_error'),
        snapshot = library.lookupFunction<_SnapshotNative,
            Pointer<Utf8> Function(Pointer<Void>)>('frk_opcua_snapshot_json'),
        freeString = library.lookupFunction<_FreeStringNative,
            void Function(Pointer<Utf8>)>('frk_opcua_free_string'),
        writeBool = library.lookupFunction<_WriteBoolNative,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>(
          'frk_opcua_write_bool',
        ),
        writeInt32 = library.lookupFunction<_WriteInt32Native,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>(
          'frk_opcua_write_int32',
        ),
        writeUint32 = library.lookupFunction<_WriteUint32Native,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>(
          'frk_opcua_write_uint32',
        ),
        writeInt64 = library.lookupFunction<_WriteInt64Native,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>(
          'frk_opcua_write_int64',
        ),
        writeDouble = library.lookupFunction<_WriteDoubleNative,
            int Function(Pointer<Void>, Pointer<Utf8>, double)>(
          'frk_opcua_write_double',
        ),
        writeString = library.lookupFunction<_WriteStringNative,
            int Function(Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>)>(
          'frk_opcua_write_string',
        ),
        setSlowPaths = library.lookupFunction<_SetSlowPathsNative,
            int Function(Pointer<Void>, Pointer<Utf8>)>(
          'frk_opcua_set_slow_paths',
        ),
        refreshSlow = library.lookupFunction<_RefreshSlowNative,
            void Function(Pointer<Void>)>(
          'frk_opcua_refresh_slow',
        ),
        setExcludedPaths = library.lookupFunction<_SetExcludedPathsNative,
            int Function(Pointer<Void>, Pointer<Utf8>)>(
          'frk_opcua_set_excluded_paths',
        ),
        readValues = library.lookupFunction<_ReadValuesNative,
            Pointer<Utf8> Function(Pointer<Void>, Pointer<Utf8>)>(
          'frk_opcua_read_values_json',
        );

  static _NativeBindings open() {
    final name = Platform.isWindows
        ? 'fraktal_opcua.dll'
        : Platform.isMacOS
            ? 'libfraktal_opcua.dylib'
            : 'libfraktal_opcua.so';
    final override = Platform.environment['FRAKTAL_OPCUA_LIBRARY'];
    if (override != null && override.isNotEmpty) {
      return _NativeBindings(DynamicLibrary.open(override));
    }
    final executableDirectory = File(Platform.resolvedExecutable).parent.path;
    final separator = Platform.pathSeparator;
    final candidates = <String>[
      '$executableDirectory$separator$name',
      '${Directory.current.path}$separator$name',
    ];
    for (final candidate in candidates) {
      if (File(candidate).existsSync()) {
        return _NativeBindings(DynamicLibrary.open(candidate));
      }
    }
    return _NativeBindings(DynamicLibrary.open(name));
  }

  String error(Pointer<Void> handle) {
    final pointer = _lastError(handle);
    return pointer == nullptr
        ? 'Unknown native OPC UA error.'
        : pointer.toDartString();
  }
}
