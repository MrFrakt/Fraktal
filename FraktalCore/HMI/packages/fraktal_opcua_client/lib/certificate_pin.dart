library;

/// Platform-neutral certificate-pin helpers (no dart:io), so a Web build can
/// validate a pin it will hand to a native transport elsewhere.
export 'src/sha256.dart';
