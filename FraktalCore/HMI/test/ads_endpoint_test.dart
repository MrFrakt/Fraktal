import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/repository_factory.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';

// Offline coverage for the ads:// transport branch of the native factory: URI
// shape validation, without needing a live PLC or TcAdsDll. (The live end-to-end
// path is exercised by the `live`-tagged test.)
void main() {
  test('createRepository skips the TCP preflight for ads:// endpoints', () async {
    // 127.0.0.1 is a resolvable IP, so the TCP/host-lookup preflight would have
    // thrown a `tcp-preflight` ConnectionStartupException. With the preflight
    // skipped for ADS, the native factory instead validates the AmsNetId (four
    // octets, not six) and throws UnsupportedError — proving no preflight ran.
    await expectLater(
      createRepository(const ConnectionSettings(endpoint: 'ads://127.0.0.1:851')),
      throwsA(isA<UnsupportedError>()),
    );
  });

  test('ads endpoint with a non-6-octet AmsNetId is rejected clearly', () async {
    await expectLater(
      createExternalRepository(const ConnectionSettings(
        endpoint: 'ads://127.0.0.1:851', // only 4 octets — not an AmsNetId
      )),
      throwsA(isA<UnsupportedError>().having(
        (e) => e.message, 'message', contains('AmsNetId'))),
    );
  });

  test('a non-ads/opc.tcp/ws native scheme is rejected', () async {
    await expectLater(
      createExternalRepository(const ConnectionSettings(endpoint: 'ftp://x')),
      throwsA(isA<UnsupportedError>()),
    );
  });
}
