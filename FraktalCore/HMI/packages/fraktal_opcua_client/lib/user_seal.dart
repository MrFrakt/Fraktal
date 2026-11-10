/// Seals a small secret (a CPU web login) for the current operating-system
/// user, shared by the native HMI's remembered logins and the gateway's
/// per-instance PLC login file so there is one implementation of the
/// protection.
///
/// Windows: DPAPI (`CryptProtectData`) in the current-user scope, never
/// showing UI. The [purpose] entropy binds each sealed value to what it is
/// for, so a blob copied to another entry or another program does not open.
/// Plaintext copies in native memory are wiped before release.
library;

import 'dart:convert';
import 'dart:ffi';
import 'dart:io';
import 'dart:typed_data';

import 'package:ffi/ffi.dart';

abstract final class UserSeal {
  /// Whether this platform seals for the OS user here (Windows only).
  static bool get available => Platform.isWindows;

  static Uint8List? protect(List<int> plain, String purpose) => available
      ? _Dpapi.run(plain, utf8.encode(purpose), protect: true)
      : null;

  static Uint8List? unprotect(List<int> sealed, String purpose) => available
      ? _Dpapi.run(sealed, utf8.encode(purpose), protect: false)
      : null;
}

/// The gateway's CPU web login for ONE instance, sealed for the Windows user
/// the tray runs as. Written by `fraktal_gateway --seal-plc-login PATH` (the
/// installer pipes user and password on standard input), read at start by
/// `--plc-login-file PATH`. Never on a command line, in gateway.args or a log.
abstract final class PlcLoginFile {
  static const _version = 1;
  static const _purpose = 'Fraktal.Gateway.plc-login.v1';

  static void write(File file, String user, String password) {
    final sealed = UserSeal.protect(
        utf8.encode(jsonEncode({'user': user, 'password': password})),
        _purpose);
    if (sealed == null) {
      throw UnsupportedError(
          'A sealed PLC login file needs Windows DPAPI; on Linux use systemd '
          'credentials (tia-web-user, tia-web-password).');
    }
    file.parent.createSync(recursive: true);
    final temp = File('${file.path}.tmp');
    temp.writeAsStringSync(
        jsonEncode({'version': _version, 'login': base64Encode(sealed)}),
        flush: true);
    if (file.existsSync()) file.deleteSync();
    temp.renameSync(file.path);
  }

  /// The login, or a [FormatException] naming why it cannot be used (most
  /// often: sealed by a different Windows user than the one running now).
  static ({String user, String password}) read(File file) {
    if (!file.existsSync()) {
      throw FormatException('PLC login file not found: ${file.path}');
    }
    final Object? document;
    try {
      document = jsonDecode(file.readAsStringSync());
    } on FormatException {
      throw FormatException('PLC login file is not valid: ${file.path}');
    }
    if (document is! Map ||
        document['version'] != _version ||
        document['login'] is! String) {
      throw FormatException('PLC login file is not valid: ${file.path}');
    }
    final plain = UserSeal.unprotect(
        base64Decode(document['login'] as String), _purpose);
    if (plain == null) {
      throw FormatException(
          'PLC login file ${file.path} cannot be opened by this Windows user; '
          'store the login again with the installer as the user that runs '
          'the gateway.');
    }
    final login = jsonDecode(utf8.decode(plain));
    if (login is! Map ||
        login['user'] is! String ||
        login['password'] is! String ||
        (login['user'] as String).isEmpty ||
        (login['password'] as String).isEmpty) {
      throw FormatException('PLC login file is not valid: ${file.path}');
    }
    return (user: login['user'] as String, password: login['password'] as String);
  }
}

final class _DataBlob extends Struct {
  @Uint32()
  external int cbData;
  external Pointer<Uint8> pbData;
}

typedef _CryptNative = Int32 Function(
    Pointer<_DataBlob> dataIn,
    Pointer<Void> description,
    Pointer<_DataBlob> entropy,
    Pointer<Void> reserved,
    Pointer<Void> prompt,
    Uint32 flags,
    Pointer<_DataBlob> dataOut);
typedef _Crypt = int Function(Pointer<_DataBlob>, Pointer<Void>,
    Pointer<_DataBlob>, Pointer<Void>, Pointer<Void>, int, Pointer<_DataBlob>);
typedef _LocalFreeNative = Pointer<Void> Function(Pointer<Void>);

abstract final class _Dpapi {
  static const _uiForbidden = 0x1;
  static final _crypt32 = DynamicLibrary.open('crypt32.dll');
  static final _protect =
      _crypt32.lookupFunction<_CryptNative, _Crypt>('CryptProtectData');
  // CryptUnprotectData's description is an OUT pointer; null is permitted
  // and the signature is otherwise identical.
  static final _unprotect =
      _crypt32.lookupFunction<_CryptNative, _Crypt>('CryptUnprotectData');
  static final _localFree = DynamicLibrary.open('kernel32.dll')
      .lookupFunction<_LocalFreeNative, _LocalFreeNative>('LocalFree');

  static Uint8List? run(List<int> data, List<int> entropy,
      {required bool protect}) {
    final input = calloc<_DataBlob>();
    final salt = calloc<_DataBlob>();
    final output = calloc<_DataBlob>();
    final inputBytes = calloc<Uint8>(data.isEmpty ? 1 : data.length);
    final saltBytes = calloc<Uint8>(entropy.isEmpty ? 1 : entropy.length);
    try {
      inputBytes.asTypedList(data.length).setAll(0, data);
      saltBytes.asTypedList(entropy.length).setAll(0, entropy);
      input.ref
        ..cbData = data.length
        ..pbData = inputBytes;
      salt.ref
        ..cbData = entropy.length
        ..pbData = saltBytes;
      final ok = (protect ? _protect : _unprotect)(
          input, nullptr, salt, nullptr, nullptr, _uiForbidden, output);
      if (ok == 0) return null;
      final out = output.ref;
      final bytes = out.pbData.asTypedList(out.cbData);
      final result = Uint8List.fromList(bytes);
      bytes.fillRange(0, out.cbData, 0);
      _localFree(out.pbData.cast());
      return result;
    } finally {
      inputBytes.asTypedList(data.length).fillRange(0, data.length, 0);
      calloc
        ..free(inputBytes)
        ..free(saltBytes)
        ..free(input)
        ..free(salt)
        ..free(output);
    }
  }
}
