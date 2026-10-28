library;

import 'dart:async';
import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:isolate';

import 'package:ffi/ffi.dart';

import 'opcua_session_client.dart';

/// Direct-ADS implementation of the transport-neutral session contract, for the
/// native TwinCAT path (ADS_TRANSPORT_MIGRATION.md). It drives the `fraktal_ads`
/// C bridge (which wraps `TcAdsDll`) and emits the SAME
/// `fraktal.opcua.snapshot.v1` browse-path document the OPC UA client does, so
/// the repository, snapshot mapper, and every view are unchanged.
///
/// Like [NativeOpcUaClient], every potentially-blocking native call runs in a
/// dedicated isolate; the UI isolate never blocks on ADS.
class AdsSessionClient
    implements OpcUaBulkReadClient, OpcUaTieredReadClient, OpcUaBatchSessionClient {
  final Isolate _isolate;
  final SendPort _worker;
  final ReceivePort _responses;
  final StreamSubscription<Object?> _subscription;
  final Map<int, Completer<Object?>> _pending = {};
  int _nextId = 1;
  bool _closed = false;
  String _amsNetId = '';
  int _amsPort = 0;

  AdsSessionClient._(
      this._isolate, this._worker, this._responses, this._subscription);

  /// Re-runs the ADS connect on the SAME worker/context, releasing the previous
  /// session's server handles first (the bridge does this in frk_ads_connect).
  /// The session-recovery path uses this so a router restart / online change does
  /// not orphan the PLC symbol-server handle pool.
  Future<void> reconnect() async {
    await _call('connect', {'amsNetId': _amsNetId, 'amsPort': _amsPort});
  }

  /// Connects to [amsNetId] (`a.b.c.d.e.f`) : [amsPort] (e.g. 851). The AMS
  /// router must be running; a local runtime needs no explicit route. [timeout]
  /// bounds isolate-spawn readiness (must be generous: in debug mode the spawned
  /// isolate registers with the VM service before running, which can take many
  /// seconds); the ADS connect call itself has its own bound.
  static Future<AdsSessionClient> connect({
    required String amsNetId,
    required int amsPort,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final responses = ReceivePort();
    final ready = Completer<SendPort>();
    AdsSessionClient? client;
    final subscription = responses.listen((message) {
      if (message is SendPort) {
        if (!ready.isCompleted) ready.complete(message);
        return;
      }
      client?._onResponse(message);
    });
    Isolate? isolate;
    try {
      isolate = await Isolate.spawn(_adsWorkerMain, responses.sendPort,
          debugName: 'fraktal-ads');
      final worker = await ready.future.timeout(timeout);
      client = AdsSessionClient._(isolate, worker, responses, subscription);
      client._amsNetId = amsNetId;
      client._amsPort = amsPort;
      // Bound the connect: a native ADS call to an unreachable/black-holed
      // AmsNetId can block the worker indefinitely (TcAdsDll's port timeout is
      // not always honored). _callBounded kills the isolate on timeout so the
      // caller gets a clear failure instead of a silent hang.
      await client._callBounded('connect', {
        'amsNetId': amsNetId,
        'amsPort': amsPort,
      });
      return client;
    } on Object {
      await subscription.cancel();
      responses.close();
      isolate?.kill(priority: Isolate.immediate);
      rethrow;
    }
  }

  /// Bounds a native round trip. A hung ADS call (unreachable/black-holed
  /// target) would otherwise wedge the worker isolate and the whole app forever.
  /// On timeout the client is marked closed and the isolate killed, so the
  /// caller gets a clear failure and the app can retry or return to the wizard.
  static const Duration _callTimeout = Duration(seconds: 10);

  Future<Object?> _callBounded(String operation,
      [Map<String, Object?>? args]) {
    return _call(operation, args).timeout(_callTimeout, onTimeout: () {
      // The isolate is stuck in a synchronous FFI call and cannot be reused.
      _closed = true;
      _isolate.kill(priority: Isolate.immediate);
      for (final c in _pending.values) {
        if (!c.isCompleted) {
          c.completeError(const OpcUaTransportException('ADS client aborted.'));
        }
      }
      _pending.clear();
      throw OpcUaTransportException(
          'ADS $operation timed out after ${_callTimeout.inSeconds}s '
          '(target unreachable or unresponsive). Check the AMS route and PLC.');
    });
  }

  @override
  Future<Map<String, Object?>> snapshot() async {
    final value = await _callBounded('snapshot');
    if (value is! Map) throw const OpcUaTransportException('ADS snapshot invalid.');
    return Map<String, Object?>.from(value);
  }

  @override
  Future<Map<String, Object?>> readValues(List<String> browsePaths) async {
    final value =
        await _callBounded('readValues', {'paths': browsePaths.join('\n')});
    if (value is! Map) return const {};
    final raw = value['values'];
    if (raw is! Map) return const {};
    return {for (final e in raw.entries) '${e.key}': e.value};
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
  Future<bool> writeBatch(List<OpcUaWrite> writes) async {
    // ADS has no cross-symbol atomic write in this bridge cut; the commit-last
    // mailbox contract is preserved by writing in order (Sequence written last).
    for (final w in writes) {
      if (!await write(w.path, w.type, w.value)) return false;
    }
    return true;
  }

  @override
  Future<void> setExcludedPaths(Iterable<String> browsePaths) async {
    await _call('setExcluded', {'paths': browsePaths.join('\n')});
  }

  // The ADS bridge has no separate slow tier: excluded (on-demand) paths are the
  // only ones held off the snapshot. Slow-path bookkeeping is a no-op here; the
  // repository still classifies and the on-demand path does the work.
  @override
  Future<void> setSlowPaths(Iterable<String> browsePaths) async {}

  @override
  Future<void> refreshSlowPaths() async {}

  Future<Object?> _call(String operation, [Map<String, Object?>? args]) {
    if (_closed) return Future.error(const OpcUaTransportException('ADS client closed.'));
    final id = _nextId++;
    final completer = Completer<Object?>();
    _pending[id] = completer;
    _worker.send({'id': id, 'operation': operation, ...?args});
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
      completer.completeError(OpcUaTransportException('${message['error']}'));
    }
  }

  @override
  Future<void> close() async {
    if (_closed) return;
    try {
      await _call('close').timeout(const Duration(seconds: 2));
    } on Object {
      // isolate is killed below regardless.
    }
    _closed = true;
    for (final c in _pending.values) {
      if (!c.isCompleted) {
        c.completeError(const OpcUaTransportException('ADS client closed.'));
      }
    }
    _pending.clear();
    await _subscription.cancel();
    _responses.close();
    _isolate.kill(priority: Isolate.immediate);
  }
}

void _adsWorkerMain(SendPort host) async {
  final inbox = ReceivePort();
  host.send(inbox.sendPort);
  _AdsBindings? b;
  Pointer<Void> handle = nullptr;

  await for (final message in inbox) {
    if (message is! Map) continue;
    final id = message['id'];
    final op = message['operation'];
    if (id is! int || op is! String) continue;
    try {
      b ??= _AdsBindings.open();
      if (handle == nullptr) handle = b.create();
      switch (op) {
        case 'connect':
          final netId = '${message['amsNetId']}'.toNativeUtf8();
          try {
            final ok = b.connect(handle, netId,
                    (message['amsPort'] as num).toInt()) == 1;
            if (!ok) throw StateError(b.error(handle));
          } finally {
            malloc.free(netId);
          }
          host.send({'id': id, 'ok': true, 'value': true});
        case 'snapshot':
          final ptr = b.snapshot(handle);
          if (ptr == nullptr) throw StateError(b.error(handle));
          try {
            host.send({'id': id, 'ok': true, 'value': jsonDecode(ptr.toDartString())});
          } finally {
            b.freeString(ptr);
          }
        case 'readValues':
          final blob = '${message['paths'] ?? ''}'.toNativeUtf8();
          try {
            final ptr = b.readValues(handle, blob);
            if (ptr == nullptr) throw StateError(b.error(handle));
            try {
              host.send({'id': id, 'ok': true, 'value': jsonDecode(ptr.toDartString())});
            } finally {
              b.freeString(ptr);
            }
          } finally {
            malloc.free(blob);
          }
        case 'setExcluded':
          final blob = '${message['paths'] ?? ''}'.toNativeUtf8();
          try {
            b.setExcluded(handle, blob);
            host.send({'id': id, 'ok': true, 'value': true});
          } finally {
            malloc.free(blob);
          }
        case 'write':
          final path = '${message['path']}'.toNativeUtf8();
          try {
            final type = OpcUaWriteType.values.byName('${message['valueType']}');
            final v = message['value'];
            final accepted = switch (type) {
              OpcUaWriteType.boolean => b.writeBool(handle, path, v == true ? 1 : 0),
              OpcUaWriteType.int32 => b.writeInt32(handle, path, (v as num).toInt()),
              OpcUaWriteType.uint32 => b.writeUint32(handle, path, (v as num).toInt()),
              OpcUaWriteType.int64 => b.writeInt64(handle, path, (v as num).toInt()),
              OpcUaWriteType.doubleValue => b.writeDouble(handle, path, (v as num).toDouble()),
              OpcUaWriteType.string => _writeStr(b, handle, path, '$v'),
            };
            if (accepted != 1) throw StateError(b.error(handle));
            host.send({'id': id, 'ok': true, 'value': true});
          } finally {
            malloc.free(path);
          }
        case 'close':
          b.disconnect(handle);
          b.destroy(handle);
          handle = nullptr;
          host.send({'id': id, 'ok': true, 'value': true});
          inbox.close();
        default:
          throw UnsupportedError('Unknown ADS op: $op');
      }
    } on Object catch (error, stack) {
      host.send({'id': id, 'ok': false, 'error': '$error', 'stack': '$stack'});
    }
  }
  if (handle != nullptr && b != null) {
    b.disconnect(handle);
    b.destroy(handle);
  }
}

int _writeStr(_AdsBindings b, Pointer<Void> h, Pointer<Utf8> path, String v) {
  final nv = v.toNativeUtf8();
  try {
    return b.writeString(h, path, nv);
  } finally {
    malloc.free(nv);
  }
}

// --- fraktal_ads FFI bindings ---
typedef _CreateN = Pointer<Void> Function();
typedef _DestroyN = Void Function(Pointer<Void>);
typedef _ConnectN = Int32 Function(Pointer<Void>, Pointer<Utf8>, Uint16);
typedef _DisconnectN = Void Function(Pointer<Void>);
typedef _ErrorN = Pointer<Utf8> Function(Pointer<Void>);
typedef _SnapshotN = Pointer<Utf8> Function(Pointer<Void>);
typedef _FreeN = Void Function(Pointer<Utf8>);
typedef _ReadValuesN = Pointer<Utf8> Function(Pointer<Void>, Pointer<Utf8>);
typedef _SetExcludedN = Int32 Function(Pointer<Void>, Pointer<Utf8>);
typedef _WBoolN = Int32 Function(Pointer<Void>, Pointer<Utf8>, Int32);
typedef _WI32N = Int32 Function(Pointer<Void>, Pointer<Utf8>, Int32);
typedef _WU32N = Int32 Function(Pointer<Void>, Pointer<Utf8>, Uint32);
typedef _WI64N = Int32 Function(Pointer<Void>, Pointer<Utf8>, Int64);
typedef _WDblN = Int32 Function(Pointer<Void>, Pointer<Utf8>, Double);
typedef _WStrN = Int32 Function(Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>);

class _AdsBindings {
  final Pointer<Void> Function() create;
  final void Function(Pointer<Void>) destroy;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) connect;
  final void Function(Pointer<Void>) disconnect;
  final Pointer<Utf8> Function(Pointer<Void>) _error;
  final Pointer<Utf8> Function(Pointer<Void>) snapshot;
  final void Function(Pointer<Utf8>) freeString;
  final Pointer<Utf8> Function(Pointer<Void>, Pointer<Utf8>) readValues;
  final int Function(Pointer<Void>, Pointer<Utf8>) setExcluded;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeBool;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeInt32;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeUint32;
  final int Function(Pointer<Void>, Pointer<Utf8>, int) writeInt64;
  final int Function(Pointer<Void>, Pointer<Utf8>, double) writeDouble;
  final int Function(Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>) writeString;

  _AdsBindings(DynamicLibrary lib)
      : create = lib.lookupFunction<_CreateN, _CreateN>('frk_ads_create'),
        destroy = lib.lookupFunction<_DestroyN, void Function(Pointer<Void>)>(
            'frk_ads_destroy'),
        connect = lib.lookupFunction<_ConnectN,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>('frk_ads_connect'),
        disconnect = lib.lookupFunction<_DisconnectN,
            void Function(Pointer<Void>)>('frk_ads_disconnect'),
        _error = lib.lookupFunction<_ErrorN, Pointer<Utf8> Function(Pointer<Void>)>(
            'frk_ads_last_error'),
        snapshot = lib.lookupFunction<_SnapshotN,
            Pointer<Utf8> Function(Pointer<Void>)>('frk_ads_snapshot_json'),
        freeString = lib.lookupFunction<_FreeN, void Function(Pointer<Utf8>)>(
            'frk_ads_free_string'),
        readValues = lib.lookupFunction<_ReadValuesN,
            Pointer<Utf8> Function(Pointer<Void>, Pointer<Utf8>)>(
            'frk_ads_read_values_json'),
        setExcluded = lib.lookupFunction<_SetExcludedN,
            int Function(Pointer<Void>, Pointer<Utf8>)>('frk_ads_set_excluded_paths'),
        writeBool = lib.lookupFunction<_WBoolN,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>('frk_ads_write_bool'),
        writeInt32 = lib.lookupFunction<_WI32N,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>('frk_ads_write_int32'),
        writeUint32 = lib.lookupFunction<_WU32N,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>('frk_ads_write_uint32'),
        writeInt64 = lib.lookupFunction<_WI64N,
            int Function(Pointer<Void>, Pointer<Utf8>, int)>('frk_ads_write_int64'),
        writeDouble = lib.lookupFunction<_WDblN,
            int Function(Pointer<Void>, Pointer<Utf8>, double)>('frk_ads_write_double'),
        writeString = lib.lookupFunction<_WStrN,
            int Function(Pointer<Void>, Pointer<Utf8>, Pointer<Utf8>)>(
            'frk_ads_write_string');

  static const _libraryName = 'fraktal_ads.dll';

  static _AdsBindings open() {
    final override = Platform.environment['FRAKTAL_ADS_LIBRARY'];
    if (override != null && override.isNotEmpty) {
      return _AdsBindings(DynamicLibrary.open(override));
    }
    const name = _libraryName;
    final exeDir = File(Platform.resolvedExecutable).parent.path;
    final sep = Platform.pathSeparator;
    for (final c in ['$exeDir$sep$name', '${Directory.current.path}$sep$name']) {
      if (File(c).existsSync()) return _AdsBindings(_load(c, found: true));
    }
    return _AdsBindings(_load(name, found: false));
  }

  /// Opens the ADS bridge, translating Windows' famously ambiguous LoadLibrary
  /// error 126 into something actionable. When the file IS on disk, error 126
  /// means one of its *dependencies* is missing — not the DLL named in the
  /// message — which is otherwise a dead end to diagnose in the field.
  static DynamicLibrary _load(String path, {required bool found}) {
    try {
      return DynamicLibrary.open(path);
    } on ArgumentError catch (error) {
      final detail = error.message?.toString() ?? '$error';
      if (!found) {
        throw ArgumentError(
          'ADS transport unavailable: $_libraryName was not found next to the '
          'executable or in the working directory. This build may have been '
          'produced without the TwinCAT ADS SDK. Original error: $detail',
        );
      }
      throw ArgumentError(
        'ADS transport unavailable: $path exists but could not be loaded, '
        'which means a DEPENDENCY is missing (Windows reports this as the '
        'library itself). $_libraryName requires TcAdsDll.dll (install TwinCAT, or '
        'the TwinCAT ADS runtime, on this machine). Original error: $detail',
      );
    }
  }

  String error(Pointer<Void> handle) {
    final p = _error(handle);
    return p == nullptr ? 'Unknown ADS error.' : p.toDartString();
  }
}
