library;

/// Dart FFI bridge to libplctag (vendored as
/// `native/cip/third_party/libplctag-2.7.2/plctag.dll`, checksums alongside).
///
/// The bridge is the thin layer the direct-CIP transport needs: create a tag
/// from a libplctag attribute string, read it into the in-process buffer,
/// access members by byte offset, write it back. libplctag owns the connected
/// EtherNet/IP messaging (ForwardOpen, sequence numbers, timeouts) that the
/// controller requires for tag access — the reason the pure-Dart attempt in
/// `eip_cip_client.dart` was stopped.
///
/// The DLL is loaded from the executable's directory (the packaged layout) or
/// from the vendored path (development runs).
import 'dart:ffi';
import 'dart:io';
import 'dart:typed_data';

import 'package:ffi/ffi.dart';

typedef _CreateNative = Int32 Function(Pointer<Utf8>, Int32);
typedef _ReadNative = Int32 Function(Int32, Int32);
typedef _WriteNative = Int32 Function(Int32, Int32);
typedef _DestroyNative = Void Function(Int32);
typedef _GetSizeNative = Int32 Function(Int32);
typedef _GetInt32Native = Int32 Function(Int32, Int32);
typedef _SetInt32Native = Int32 Function(Int32, Int32, Int32);
typedef _GetRawNative = Int32 Function(Int32, Int32, Pointer<Uint8>, Int32);
typedef _SetRawNative = Int32 Function(Int32, Int32, Pointer<Uint8>, Int32);
typedef _SetSizeNative = Int32 Function(Int32, Int32);
typedef _SetDebugNative = Void Function(Int32);

class PlcTagException implements Exception {
  final String message;
  final int status;
  const PlcTagException(this.message, this.status);

  @override
  String toString() => 'libplctag error $status: $message';
}

class LibPlctag {
  static LibPlctag? _instance;

  final DynamicLibrary lib;
  late final int Function(Pointer<Utf8>, int) _create;
  late final int Function(int, int) _read;
  late final int Function(int, int) _write;
  late final void Function(int) _destroy;
  late final int Function(int) _getSize;
  late final int Function(int, int) _getInt32;
  late final int Function(int, int, int) _setInt32;
  late final int Function(int, int, Pointer<Uint8>, int) _getRawBytes;
  late final int Function(int, int, Pointer<Uint8>, int) _setRawBytes;
  late final int Function(int, int) _setSize;
  late final void Function(int) _setDebugLevel;

  LibPlctag._(this.lib) {
    _create = lib
        .lookup<NativeFunction<_CreateNative>>('plc_tag_create')
        .asFunction<int Function(Pointer<Utf8>, int)>();
    _read =
        lib.lookup<NativeFunction<_ReadNative>>('plc_tag_read').asFunction<int Function(int, int)>();
    _write =
        lib.lookup<NativeFunction<_WriteNative>>('plc_tag_write').asFunction<int Function(int, int)>();
    _destroy = lib
        .lookup<NativeFunction<_DestroyNative>>('plc_tag_destroy')
        .asFunction<void Function(int)>();
    _getSize = lib
        .lookup<NativeFunction<_GetSizeNative>>('plc_tag_get_size')
        .asFunction<int Function(int)>();
    _getInt32 = lib
        .lookup<NativeFunction<_GetInt32Native>>('plc_tag_get_int32')
        .asFunction<int Function(int, int)>();
    _setInt32 = lib
        .lookup<NativeFunction<_SetInt32Native>>('plc_tag_set_int32')
        .asFunction<int Function(int, int, int)>();
    _getRawBytes = lib
        .lookup<NativeFunction<_GetRawNative>>('plc_tag_get_raw_bytes')
        .asFunction<int Function(int, int, Pointer<Uint8>, int)>();
    _setRawBytes = lib
        .lookup<NativeFunction<_SetRawNative>>('plc_tag_set_raw_bytes')
        .asFunction<int Function(int, int, Pointer<Uint8>, int)>();
    _setSize = lib
        .lookup<NativeFunction<_SetSizeNative>>('plc_tag_set_size')
        .asFunction<int Function(int, int)>();
    _setDebugLevel = lib
        .lookup<NativeFunction<_SetDebugNative>>('plc_tag_set_debug_level')
        .asFunction<void Function(int)>();
    _setDebugLevel(1); // PLCTAG_DEBUG_ERROR: internal errors on stderr.
  }

  /// Loads `plctag.dll` from [dllPath], or from the executable directory plus
  /// the vendored development location when no path is given.
  static LibPlctag open([String? dllPath]) {
    final existing = _instance;
    if (existing != null) {
      return existing;
    }
    final candidates = <String>[
      if (dllPath != null) dllPath,
      'plctag.dll',
      if (Platform.isWindows)
        'C:\\Users\\SoftIndVM\\Fraktal\\FraktalCore\\HMI\\native\\cip'
            '\\third_party\\libplctag-2.7.2\\plctag.dll',
    ];
    final failures = <String>[];
    for (final candidate in candidates) {
      try {
        _instance = LibPlctag._(DynamicLibrary.open(candidate));
        return _instance!;
      } on Object catch (error) {
        failures.add('$candidate: $error');
      }
    }
    throw PlcTagException(
        'could not load plctag.dll (looked in: '
        '${failures.join("; ")}); copy it next to the executable',
        -1);
  }

  int create(String attrib, {int timeoutMs = 5000}) {
    final pointer = attrib.toNativeUtf8();
    try {
      final handle = _create(pointer, timeoutMs);
      if (handle < 0) {
        throw PlcTagException('create failed: $attrib', handle);
      }
      return handle;
    } finally {
      calloc.free(pointer);
    }
  }

  int read(int tag, {int timeoutMs = 1000}) {
    final status = _read(tag, timeoutMs);
    if (status != 0) {
      throw PlcTagException('read failed', status);
    }
    return status;
  }

  int write(int tag, {int timeoutMs = 1000}) {
    final status = _write(tag, timeoutMs);
    if (status != 0) {
      throw PlcTagException('write failed', status);
    }
    return status;
  }

  int size(int tag) => _getSize(tag);

  int int32(int tag, int offset) => _getInt32(tag, offset);

  void setInt32(int tag, int offset, int value) =>
      _setInt32(tag, offset, value);

  Uint8List rawBytes(int tag) {
    final size = _getSize(tag);
    if (size <= 0) {
      return Uint8List(0);
    }
    final buffer = calloc<Uint8>(size);
    try {
      final status = _getRawBytes(tag, 0, buffer, size);
      if (status != 0) {
        throw PlcTagException('get raw bytes failed', status);
      }
      return Uint8List.fromList(buffer.asTypedList(size));
    } finally {
      calloc.free(buffer);
    }
  }

  void setRawBytes(int tag, Uint8List bytes) {
    // A raw (@raw) tag carries no size until one is set; libplctag returns
    // PLCTAG_ERR_NO_DATA from set_raw_bytes against a zero-size buffer.
    _setSize(tag, bytes.length);
    final buffer = calloc<Uint8>(bytes.length);
    try {
      buffer.asTypedList(bytes.length).setAll(0, bytes);
      final status = _setRawBytes(tag, 0, buffer, bytes.length);
      if (status != 0) {
        throw PlcTagException('set raw bytes failed', status);
      }
    } finally {
      calloc.free(buffer);
    }
  }

  void destroy(int tag) => _destroy(tag);

  /// libplctag debug level (1=error..6=spew); DETAIL (5) dumps full
  /// request/response packets to stderr — the diff tool when the Echo
  /// answers this client differently from libplctag.
  void setDebugLevel(int level) => _setDebugLevel(level);
}

/// Encodes ASCII text the way the generated key strings carry it.
Uint8List asciiBytes(String text, int width) {
  final out = Uint8List(width);
  for (var i = 0; i < width && i < text.length; i++) {
    out[i] = text.codeUnitAt(i) & 0xFF;
  }
  return out;
}

/// Decodes one Logix key string (LEN DINT + DATA[width]) out of a buffer.
String decodeKeyString(Uint8List payload, int offset, int width) {
  final data = ByteData.sublistView(payload);
  final length =
      data.getInt32(offset, Endian.little).clamp(0, width).toInt();
  return String.fromCharCodes(payload.sublist(offset + 4, offset + 4 + length));
}
