// Report what certificate a Dart client actually receives from the gateway.
//
// A TLS-intercepting endpoint security product re-signs the server certificate
// with its own root, so the client verifies against a chain the deployment
// never configured and fails with CERTIFICATE_VERIFY_FAILED. That looks exactly
// like a misconfigured trust store, so this probe separates the two: it prints
// the issuer the client is really offered.
//
//   dart run tool/probe_gateway_tls.dart <host> <port> [trustedCaPath]
//
// Read-only: it opens a socket and reports, and speaks no Fraktal protocol.

import 'dart:io';

Future<void> main(List<String> args) async {
  if (args.length < 2) {
    stderr.writeln('usage: probe_gateway_tls.dart <host> <port> [trustedCa]');
    exitCode = 2;
    return;
  }
  final host = args[0];
  final port = int.parse(args[1]);
  final trustedCa = args.length > 2 ? args[2] : '';

  SecurityContext? context;
  if (trustedCa.isNotEmpty) {
    context = SecurityContext(withTrustedRoots: true);
    try {
      context.setTrustedCertificates(trustedCa);
      stdout.writeln('trusted CA loaded: $trustedCa');
    } on Object catch (error) {
      stdout.writeln('trusted CA FAILED to load: $error');
    }
  } else {
    stdout.writeln('no trusted CA supplied (system roots only)');
  }

  // Accept any certificate so the probe can *report* it rather than abort. This
  // is a diagnostic, never a client: nothing is sent over this socket.
  try {
    final socket = await SecureSocket.connect(
      host,
      port,
      context: context,
      onBadCertificate: (certificate) {
        stdout.writeln('certificate did NOT verify; reporting it anyway:');
        stdout.writeln('  subject: ${certificate.subject}');
        stdout.writeln('  issuer : ${certificate.issuer}');
        return true;
      },
    );
    final peer = socket.peerCertificate;
    stdout.writeln('connected.');
    if (peer != null) {
      stdout.writeln('  subject: ${peer.subject}');
      stdout.writeln('  issuer : ${peer.issuer}');
    }
    await socket.close();
    socket.destroy();
  } on Object catch (error) {
    stdout.writeln('connect failed: $error');
    exitCode = 1;
  }
}
