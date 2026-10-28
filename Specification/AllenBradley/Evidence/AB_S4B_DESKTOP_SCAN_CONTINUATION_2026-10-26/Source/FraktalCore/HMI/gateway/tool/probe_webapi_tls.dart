// Dev probe: does the S7 web server keep a TLS connection open for a second
// HTTP request? Raw SecureSocket, two Api.Ping requests on ONE connection.
//   dart run tool/probe_webapi_tls.dart <host>
import 'dart:async';
import 'dart:convert';
import 'dart:io';

Future<void> main(List<String> args) async {
  final host = args[0];
  final w = Stopwatch()..start();
  final socket = await SecureSocket.connect(host, 443,
      context: SecurityContext(withTrustedRoots: false),
      onBadCertificate: (_) => true,
      timeout: const Duration(seconds: 10));
  stdout.writeln('connected+handshake ${w.elapsedMilliseconds}ms');
  final incoming = StreamController<String>();
  var closedAt = -1;
  socket.cast<List<int>>().transform(latin1.decoder).listen(incoming.add,
      onDone: () => closedAt = w.elapsedMilliseconds, onError: (_) {});
  final buffer = StringBuffer();
  incoming.stream.listen(buffer.write);
  const body = '{"jsonrpc":"2.0","method":"Api.Ping","id":1}';
  for (var i = 0; i < 2; i++) {
    final t0 = w.elapsedMilliseconds;
    buffer.clear();
    socket.add(latin1.encode('POST /api/jsonrpc HTTP/1.1\r\nHost: $host\r\n'
        'Content-Type: application/json\r\nContent-Length: ${body.length}\r\n\r\n$body'));
    await socket.flush();
    final deadline = DateTime.now().add(const Duration(seconds: 5));
    while (!buffer.toString().contains('\r\n0\r\n\r\n') && DateTime.now().isBefore(deadline) && closedAt < 0) {
      await Future<void>.delayed(const Duration(milliseconds: 5));
    }
    final text = buffer.toString();
    final status = text.split('\r\n').first;
    stdout.writeln('request #$i: ${w.elapsedMilliseconds - t0}ms status="$status" '
        'complete=${text.contains('\r\n0\r\n\r\n')} serverClosedAt=${closedAt < 0 ? "-" : "${closedAt}ms"}');
  }
  socket.destroy();
  exit(0);
}
