// The native HMI's direct Siemens S7 Web API link (s7web://): the endpoint
// grammar, the SHA-256 certificate pin and its fail-closed behaviour against a
// real loopback TLS server.
import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/external_repository_factory_native.dart';
import 'package:fraktal_hmi/data/s7web_credentials.dart';
import 'package:fraktal_hmi/data/s7web_endpoint.dart';
import 'package:fraktal_hmi/data/s7web_vault.dart';
import 'package:fraktal_hmi/data/s7web_vault_io.dart'
    show DpapiS7WebVault, decodeS7WebLogins, encodeS7WebLogins;
import 'package:fraktal_hmi/domain/connection_settings.dart';
import 'package:fraktal_opcua_client/certificate_pin.dart';
import 'package:fraktal_opcua_client/opcua_session_client.dart';
import 'package:fraktal_opcua_client/user_seal.dart';
import 'package:fraktal_opcua_client/webapi_session_client.dart';

import 'support/memory_s7web_vault.dart';

const _fixturePin =
    'DB:09:EC:F4:AD:75:60:04:03:97:06:31:E5:9C:C3:67:DE:9B:FA:5C:35:87:F3:27:FA:B4:15:A0:FA:B7:2D:57';
const _fixtureHex =
    'db09ecf4ad75600403970631e59cc367de9bfa5c3587f327fab415a0fab72d57';

void main() {
  group('SHA-256', () {
    test('matches the FIPS 180-4 known answers', () {
      expect(sha256Hex(const []),
          'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855');
      expect(sha256Hex(utf8.encode('abc')),
          'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad');
      expect(
          sha256Hex(utf8.encode(
              'abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq')),
          '248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1');
    });

    test('padding boundaries: 55, 56 and 64 bytes', () {
      expect(sha256Hex(List.filled(55, 0x61)),
          '9f4390f8d30c2dd92ec9f095b65e2b9ae9b0a925a5258e241c9f1e910f734318');
      expect(sha256Hex(List.filled(56, 0x61)),
          'b35439a4ac6f0948b6d6f9e3c6af0f5f590ce20f1bde7090ef7970686ec6738a');
      expect(sha256Hex(List.filled(64, 0x61)),
          'ffe054fe7ae0cb6dc65c3af9b61d5209f439851db43d0ba5997337df154668eb');
    });

    test('fingerprint forms normalise; anything else is refused', () {
      const hex = _fixtureHex;
      expect(normalizeSha256Fingerprint(_fixturePin), hex);
      expect(normalizeSha256Fingerprint('sha256:${hex.toUpperCase()}'), hex);
      expect(() => normalizeSha256Fingerprint(hex.substring(2)),
          throwsFormatException);
      expect(() => normalizeSha256Fingerprint('${hex.substring(1)}g'),
          throwsFormatException);
    });
  });

  group('s7web:// endpoint', () {
    S7WebEndpoint parse(String text) => S7WebEndpoint.parse(Uri.parse(text));

    test('defaults: HTTPS 443, every published root, batch 64', () {
      final endpoint = parse('s7web://169.254.212.49?pin=$_fixturePin');
      expect(endpoint.host, '169.254.212.49');
      expect(endpoint.port, 443);
      expect(endpoint.roots, isEmpty);
      expect(endpoint.batchSize, 64);
      expect(endpoint.pinSha256, _fixtureHex);
    });

    test('port, roots and batch are honoured', () {
      final endpoint = parse(
          's7web://cpu.local:8443?pin=$_fixturePin&roots=PressDemo,Line&batch=20');
      expect(endpoint.port, 8443);
      expect(endpoint.roots, ['PressDemo', 'Line']);
      expect(endpoint.batchSize, 20);
    });

    test('fails closed without a valid pin, with credentials or unknown options',
        () {
      for (final text in [
        's7web://10.0.0.1',
        's7web://10.0.0.1?pin=',
        's7web://10.0.0.1?pin=1234',
        's7web://fraktal:secret@10.0.0.1?pin=$_fixturePin',
        's7web://10.0.0.1?pin=$_fixturePin&insecure=1',
        's7web://10.0.0.1?pin=$_fixturePin&batch=0',
        's7web://10.0.0.1?pin=$_fixturePin&batch=201',
      ]) {
        expect(S7WebEndpoint.defect(Uri.parse(text)), isNotNull, reason: text);
      }
    });
  });

  group('pinned HTTPS against a loopback TLS server', () {
    late SecureServerSocket server;
    late StreamSubscription<SecureSocket> serving;

    setUp(() async {
      final context = SecurityContext()
        ..useCertificateChain('test/fixtures/tls/s7web_test_cert.pem')
        ..usePrivateKey('test/fixtures/tls/s7web_test_key.pem');
      server = await SecureServerSocket.bind(
          InternetAddress.loopbackIPv4, 0, context);
      serving = server.listen(_answerPing);
    });

    tearDown(() async {
      await serving.cancel();
      await server.close();
    });

    test('the pinned fingerprint is accepted', () async {
      final transport = HttpsWebApiTransport.fingerprint(
        host: '127.0.0.1',
        port: server.port,
        sha256Fingerprint: _fixturePin,
        keepAlive: null,
      );
      final reply = await transport
          .post({'jsonrpc': '2.0', 'method': 'Api.Ping', 'id': 1});
      expect((reply as Map)['result'], 'pong');
      await transport.close();
    });

    test('any other certificate is refused and named by its fingerprint',
        () async {
      final transport = HttpsWebApiTransport.fingerprint(
        host: '127.0.0.1',
        port: server.port,
        sha256Fingerprint: 'ab' * 32,
        keepAlive: null,
      );
      await expectLater(
        transport.post({'jsonrpc': '2.0', 'method': 'Api.Ping', 'id': 1}),
        throwsA(isA<OpcUaTransportException>().having(
            (error) => error.message,
            'message',
            contains(_fixtureHex))),
      );
      await transport.close();
    });
  });

  group('CPU web login for the direct link (memory only)', () {
    final fromEnvironment =
        (Platform.environment['FRAKTAL_TIA_WEB_USER'] ?? '').isNotEmpty;
    late SecureServerSocket server;
    late StreamSubscription<SecureSocket> serving;
    final logins = <Object?>[];

    setUp(() async {
      logins.clear();
      final context = SecurityContext()
        ..useCertificateChain('test/fixtures/tls/s7web_test_cert.pem')
        ..usePrivateKey('test/fixtures/tls/s7web_test_key.pem');
      server = await SecureServerSocket.bind(
          InternetAddress.loopbackIPv4, 0, context);
      serving = server.listen((socket) => _refuseLogin(socket, logins));
    });

    tearDown(() async {
      await serving.cancel();
      await server.close();
    });

    ConnectionSettings settings() => ConnectionSettings(
        endpoint: 's7web://127.0.0.1:${server.port}?pin=$_fixtureHex');

    test('the store keys a login by host, port and certificate pin', () {
      final store = S7WebCredentialStore();
      final a = S7WebEndpoint.parse(Uri.parse('s7web://10.0.0.1?pin=$_fixtureHex'));
      final b = S7WebEndpoint.parse(Uri.parse('s7web://10.0.0.1?pin=${'ab' * 32}'));
      store.remember(a, 'fraktal', 'secret');
      expect(store.lookup(a)!.password, 'secret');
      expect(store.lookup(b), isNull, reason: 'another certificate is another CPU');
      expect(store.userFor(a), 'fraktal');
      expect(store.lookup(a).toString(), isNot(contains('secret')));
      store.forget(a);
      expect(store.lookup(a), isNull);
    });

    test('no login known: asks, without touching the network', () async {
      await expectLater(
          createExternalRepository(settings()),
          throwsA(isA<S7WebLoginRequired>()
              .having((e) => e.rejected, 'rejected', isFalse)));
      expect(logins, isEmpty);
    }, skip: fromEnvironment ? 'environment login present' : false);

    test('a refused login is reported and forgotten', () async {
      final target = S7WebEndpoint.parse(Uri.parse(settings().endpoint));
      s7WebCredentials.remember(target, 'fraktal', 'wrong');
      addTearDown(() => s7WebCredentials.forget(target));
      await expectLater(
          createExternalRepository(settings()),
          throwsA(isA<S7WebLoginRequired>()
              .having((e) => e.rejected, 'rejected', isTrue)));
      expect(logins, [
        {'user': 'fraktal', 'password': 'wrong'}
      ]);
      expect(s7WebCredentials.lookup(target), isNull);
    }, skip: fromEnvironment ? 'environment login present' : false);

    test('a remembered login the CPU refuses is removed from the vault',
        () async {
      final vault = MemoryS7WebVault();
      s7WebCredentials.vault = vault;
      addTearDown(() => s7WebCredentials.vault = const UnavailableS7WebVault());
      await s7WebCredentials.ready();
      final target = S7WebEndpoint.parse(Uri.parse(settings().endpoint));
      s7WebCredentials.remember(target, 'fraktal', 'changed-on-cpu',
          persist: true);
      await s7WebCredentials.pendingWrites;
      expect(vault.logins, hasLength(1));
      await expectLater(createExternalRepository(settings()),
          throwsA(isA<S7WebLoginRequired>()));
      await s7WebCredentials.pendingWrites;
      expect(vault.logins, isEmpty);
      expect(s7WebCredentials.isRemembered(target), isFalse);
    }, skip: fromEnvironment ? 'environment login present' : false);
  });

  group('remembered CPU web login', () {
    final a = S7WebEndpoint.parse(Uri.parse('s7web://10.0.0.1?pin=$_fixtureHex'));
    final b = S7WebEndpoint.parse(Uri.parse('s7web://10.0.0.2?pin=$_fixtureHex'));

    test('memory only unless asked; a later start logs in by itself', () async {
      final vault = MemoryS7WebVault();
      final first = S7WebCredentialStore(vault: vault);
      expect(first.canRemember, isFalse, reason: 'not known before ready');
      await first.ready();
      expect(first.canRemember, isTrue);
      first.remember(a, 'fraktal', 'secret');
      await first.pendingWrites;
      expect(vault.saves, 0, reason: 'not ticked: nothing leaves memory');
      first.remember(b, 'fraktal', 'other', persist: true);
      await first.pendingWrites;
      expect(vault.logins.keys, hasLength(1));

      final restarted = S7WebCredentialStore(vault: vault);
      await restarted.ready();
      expect(restarted.lookup(a), isNull);
      expect(restarted.lookup(b)!.password, 'other');
      expect(restarted.isRemembered(b), isTrue);

      // Unticking on the next entry is how the operator makes it forget.
      restarted.remember(b, 'fraktal', 'other');
      await restarted.pendingWrites;
      expect(vault.logins, isEmpty);
      expect(restarted.lookup(b)!.password, 'other',
          reason: 'still held for this session');
    });

    test('an unchanged login is not rewritten; writes land in order',
        () async {
      final vault = MemoryS7WebVault();
      final store = S7WebCredentialStore(vault: vault);
      await store.ready();
      store
        ..remember(a, 'fraktal', 'secret', persist: true)
        ..remember(a, 'fraktal', 'secret', persist: true)
        ..remember(b, 'fraktal', 'one', persist: true)
        ..remember(b, 'fraktal', 'two', persist: true)
        ..forget(a);
      await store.pendingWrites;
      expect(vault.saves, 4);
      expect(vault.logins, {
        '10.0.0.2:443#$_fixtureHex': (user: 'fraktal', password: 'two'),
      });
    });

    test('platforms without a user-bound store keep memory only', () async {
      final store = S7WebCredentialStore();
      await store.ready();
      expect(store.canRemember, isFalse);
      store.remember(a, 'fraktal', 'secret', persist: true);
      expect(store.isRemembered(a), isFalse);
      expect(store.lookup(a)!.password, 'secret');
    });

    test('a vault the session cannot open offers no box', () async {
      final store = S7WebCredentialStore(vault: _FailingVault());
      await store.ready();
      expect(store.canRemember, isFalse);
    });

    test('the keyring and mobile stores round-trip one JSON document', () {
      final logins = {
        'h:443#p': (user: 'fraktal', password: 'pa"ss\nword'),
      };
      expect(decodeS7WebLogins(encodeS7WebLogins(logins)), logins);
      expect(decodeS7WebLogins('{"version":2,"logins":{}}'), isEmpty);
      expect(decodeS7WebLogins('garbage'), isEmpty);
      expect(decodeS7WebLogins(null), isEmpty);
    });

    test('Windows DPAPI seals each login to this user and its target',
        () async {
      final dir = Directory.systemTemp.createTempSync('fraktal_vault_');
      addTearDown(() => dir.deleteSync(recursive: true));
      final file = File('${dir.path}${Platform.pathSeparator}logins.json');
      final vault = DpapiS7WebVault(file);
      await vault.save({
        'a': (user: 'fraktal', password: 'Fraktal123456'),
        'b': (user: 'other', password: 'x'),
      });
      final text = file.readAsStringSync();
      expect(text, isNot(contains('Fraktal123456')));
      expect(text, isNot(contains('fraktal')));
      expect(await DpapiS7WebVault(file).load(), {
        'a': (user: 'fraktal', password: 'Fraktal123456'),
        'b': (user: 'other', password: 'x'),
      });

      // An entry moved under another target does not decrypt there.
      final document = jsonDecode(text) as Map<String, dynamic>;
      final logins = document['logins'] as Map<String, dynamic>;
      logins['b'] = logins['a'];
      file.writeAsStringSync(jsonEncode(document));
      expect((await DpapiS7WebVault(file).load())!.keys, ['a']);

      file.writeAsStringSync('not json');
      expect(await DpapiS7WebVault(file).load(), isEmpty);
      await vault.save({});
      expect(file.existsSync(), isFalse);
    }, skip: Platform.isWindows ? false : 'DPAPI is Windows only');

    test('the gateway login file opens only for its own purpose', () {
      final dir = Directory.systemTemp.createTempSync('fraktal_gateway_login_');
      addTearDown(() => dir.deleteSync(recursive: true));
      final file = File('${dir.path}${Platform.pathSeparator}plc_login.json');
      PlcLoginFile.write(file, 'fraktal', 'Fraktal123456');
      expect(file.readAsStringSync(), isNot(contains('Fraktal123456')));
      expect(PlcLoginFile.read(file),
          (user: 'fraktal', password: 'Fraktal123456'));

      // A blob sealed for the HMI's vault is not a gateway login.
      final hmiBlob = UserSeal.protect(
          utf8.encode('{"user":"u","password":"p"}'), 'Fraktal.HMI.s7web.v1\nx');
      file.writeAsStringSync(
          jsonEncode({'version': 1, 'login': base64Encode(hmiBlob!)}));
      expect(() => PlcLoginFile.read(file), throwsFormatException);
      expect(() => PlcLoginFile.read(File('${file.path}.missing')),
          throwsFormatException);
    }, skip: Platform.isWindows ? false : 'DPAPI is Windows only');
  });
}

class _FailingVault implements S7WebVault {
  @override
  Future<Map<String, S7WebLogin>?> load() async =>
      throw StateError('no keyring session');

  @override
  Future<void> save(Map<String, S7WebLogin> logins) async {}
}

/// Answers one HTTP/1.1 JSON-RPC request per connection with `pong`.
Future<void> _answerPing(SecureSocket socket) async {
  final received = <int>[];
  await for (final chunk in socket) {
    received.addAll(chunk);
    final text = latin1.decode(received);
    final headerEnd = text.indexOf('\r\n\r\n');
    if (headerEnd < 0) continue;
    final length = int.parse(RegExp(r'Content-Length: (\d+)')
        .firstMatch(text)!
        .group(1)!);
    if (received.length < headerEnd + 4 + length) continue;
    final body = utf8.encode(jsonEncode({'jsonrpc': '2.0', 'id': 1, 'result': 'pong'}));
    socket.add(latin1.encode('HTTP/1.1 200 OK\r\n'
        'Content-Type: application/json\r\n'
        'Content-Length: ${body.length}\r\n'
        'Connection: close\r\n\r\n'));
    socket.add(body);
    await socket.flush();
    await socket.close();
    return;
  }
}

/// Refuses every Api.Login the way the CPU does (JSON-RPC error 100) and
/// records the parameters it was offered.
Future<void> _refuseLogin(SecureSocket socket, List<Object?> logins) async {
  final received = <int>[];
  await for (final chunk in socket) {
    received.addAll(chunk);
    final text = latin1.decode(received);
    final headerEnd = text.indexOf('\r\n\r\n');
    if (headerEnd < 0) continue;
    final length = int.parse(RegExp(r'Content-Length: (\d+)')
        .firstMatch(text)!
        .group(1)!);
    if (received.length < headerEnd + 4 + length) continue;
    final body = jsonDecode(utf8.decode(received.sublist(headerEnd + 4)));
    final requests = (body is List ? body : [body]).cast<Map>();
    final replies = [
      for (final request in requests)
        request['method'] == 'Api.Login'
            ? {
                'jsonrpc': '2.0',
                'id': request['id'],
                'error': {'code': 100, 'message': 'Login failed'},
              }
            : {'jsonrpc': '2.0', 'id': request['id'], 'result': true},
    ];
    for (final request in requests) {
      if (request['method'] == 'Api.Login') logins.add(request['params']);
    }
    final reply =
        utf8.encode(jsonEncode(body is List ? replies : replies.single));
    socket.add(latin1.encode('HTTP/1.1 200 OK\r\n'
        'Content-Type: application/json\r\n'
        'Content-Length: ${reply.length}\r\n'
        'Connection: close\r\n\r\n'));
    socket.add(reply);
    await socket.flush();
    await socket.close();
    return;
  }
}
