library;

import 'package:fraktal_opcua_client/certificate_pin.dart';

/// A direct Siemens S7 Web API endpoint for the native HMI, the TIA analogue
/// of `ads://` (OPCUA_TRANSPORT "Siemens S7 Web API transport"):
///
/// `s7web://<host>[:443]?pin=<sha256 fingerprint>[&roots=A,B][&batch=N]`
///
/// The pin is mandatory: the HMI trusts exactly the CPU web server certificate
/// whose fingerprint commissioning recorded, never a CA or "accept any". The
/// CPU user and password are not part of the endpoint (it is persisted in
/// plain settings); they come from `FRAKTAL_TIA_WEB_USER` and
/// `FRAKTAL_TIA_WEB_PASSWORD`, the same names the gateway reads.
class S7WebEndpoint {
  static const String scheme = 's7web';
  static const int defaultPort = 443;
  static const int defaultBatch = 64;

  final String host;
  final int port;
  final String pinSha256;
  final List<String> roots;
  final int batchSize;

  const S7WebEndpoint._({
    required this.host,
    required this.port,
    required this.pinSha256,
    required this.roots,
    required this.batchSize,
  });

  /// Parses and validates [uri]; a FormatException names the first defect.
  static S7WebEndpoint parse(Uri uri) {
    if (uri.scheme != scheme) {
      throw FormatException('Not an $scheme:// endpoint.', uri.toString());
    }
    if (uri.host.isEmpty) {
      throw const FormatException('An s7web:// endpoint needs the CPU address.');
    }
    if (uri.userInfo.isNotEmpty) {
      throw const FormatException('Credentials never belong in the endpoint; '
          'set FRAKTAL_TIA_WEB_USER and FRAKTAL_TIA_WEB_PASSWORD.');
    }
    final query = uri.queryParameters;
    final unknown = query.keys.toSet().difference(const {'pin', 'roots', 'batch'});
    if (unknown.isNotEmpty) {
      throw FormatException('Unknown s7web:// option: ${unknown.join(', ')}.');
    }
    final pin = query['pin'] ?? '';
    if (pin.isEmpty) {
      throw const FormatException('An s7web:// endpoint needs '
          '?pin=<SHA-256 fingerprint of the CPU web server certificate>.');
    }
    final roots = [
      for (final root in (query['roots'] ?? '').split(','))
        if (root.trim().isNotEmpty) root.trim(),
    ];
    final batchText = query['batch'];
    final batch = batchText == null ? defaultBatch : int.tryParse(batchText);
    if (batch == null || batch < 1 || batch > 200) {
      throw const FormatException('s7web:// batch must be between 1 and 200.');
    }
    return S7WebEndpoint._(
      host: uri.host,
      port: uri.hasPort ? uri.port : defaultPort,
      pinSha256: normalizeSha256Fingerprint(pin),
      roots: List.unmodifiable(roots),
      batchSize: batch,
    );
  }

  /// The wizard's check: null when [uri] is a usable endpoint.
  static String? defect(Uri uri) {
    try {
      parse(uri);
      return null;
    } on FormatException catch (error) {
      return error.message;
    }
  }
}
