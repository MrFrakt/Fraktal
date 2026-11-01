import 'dart:io';
import 'package:fraktal_opcua_client/cip_session_client.dart';
import 'package:test/test.dart';

void main() {
  test('Windows installer applies the CIP endpoint bounds', () async {
    if (!Platform.isWindows) return;
    final result=await Process.run('powershell.exe',[
      '-NoProfile','-ExecutionPolicy','Bypass','-File','test/installer_endpoints.ps1']);
    expect(result.exitCode,0,reason:'${result.stdout}\n${result.stderr}');
    expect(result.stdout,contains('17 installer endpoint cases passed.'));
  });
  test('gateway endpoint requires serial and bounds every transport parameter',
      () {
    final endpoint = CipEndpoint.parse(
        'cip://192.0.2.1?slot=255&serial=601FC87B',
        requireSerial: true);
    expect((endpoint.host, endpoint.port, endpoint.slot, endpoint.serial),
        ('192.0.2.1', 44818, 255, '601FC87B'));
    expect(
        CipEndpoint.parse('cip://localhost:44819?serial=abcdef01',
                requireSerial: true)
            .port,
        44819);
    for (final uri in [
      'cip://localhost',
      'cip://localhost?serial=bad',
      'cip://localhost?serial=601FC87B&slot=-1',
      'cip://localhost?serial=601FC87B&slot=256',
      'cip://localhost?serial=601FC87B&slot=0&slot=1',
      'cip://localhost?serial=601FC87B&other=1',
      'cip://localhost?serial=601FC87B&Serial=12345678',
      'cip://user@localhost?serial=601FC87B',
      'cip://localhost/path?serial=601FC87B',
      'cip://localhost?serial=601FC87B#fragment',
      'cip://localhost:0?serial=601FC87B',
    ]) {
      expect(() => CipEndpoint.parse(uri, requireSerial: true),
          throwsFormatException,
          reason: uri);
    }
  });
  test('CLI rejects invalid CIP before attempting a controller connection',
      () async {
    for (final endpoint in ['cip://localhost', 'cip://localhost?serial=bad', 'cip://localhost:0?serial=601FC87B']) {
      final result = await Process.run(Platform.resolvedExecutable,
          ['run', 'bin/fraktal_gateway.dart', '--plc-endpoint', endpoint]);
      expect(result.exitCode, 64);
      expect(result.stdout, isNot(contains('stage=cip-connect')));
    }
  });
  test('CIP cannot enable all-root write policy', () async {
    final result = await Process.run(Platform.resolvedExecutable, [
      'run',
      'bin/fraktal_gateway.dart',
      '--plc-endpoint',
      'cip://localhost?serial=601FC87B',
      '--allow-all-root-mailboxes'
    ]);
    expect(result.exitCode, 64);
    expect(result.stdout, isNot(contains('stage=cip-connect')));
  });
}
