/// The Dart host adapter against the emitted Fraktal/AB V6.11 controller code.
///
/// `fraktal_ab_host_bench_server.py` runs the generated typed-ingress, mailbox
/// and configuration-restore routines over the generated tag initializers, and
/// serves them over stdio. `RootService` answers the jobs those routines open,
/// with a real store and medium in temporary folders. What it renders from
/// published facts must equal what the engineering code renders.
///
/// The configuration-set scenarios run twice: once through a port that hands
/// the bench plain values, and once through the real `CipHostIngress`. That
/// port reads and writes CIP tag bytes; the bench answers them in synthetic
/// Template layouts (not a measured Logix layout) and decodes the writes back
/// into the emitted request and commit tags.
@Timeout(Duration(minutes: 20))
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:fraktal_gateway/host_adapter.dart';
import 'package:fraktal_opcua_client/cip_host_service.dart';
import 'package:test/test.dart';

final _tools = Directory('../../PLC/Allen-Bradley/tools');
final _python = Platform.environment['FRAKTAL_PYTHON'] ?? 'python';

/// One bench controller process; requests are answered one line at a time.
final class Bench {
  final Process process;
  final StreamIterator<String> _lines;
  Bench._(this.process)
      : _lines = StreamIterator(process.stdout
            .transform(utf8.decoder)
            .transform(const LineSplitter()));

  static Future<Bench> start(String variant) async {
    final process = await Process.start(
        _python, ['fraktal_ab_host_bench_server.py', variant],
        workingDirectory: _tools.path);
    process.stderr.transform(utf8.decoder).listen(stderr.write);
    final bench = Bench._(process);
    final ready = await bench._next();
    if (ready['ready'] != true) throw StateError('bench did not start: $ready');
    return bench;
  }

  Future<Map<String, Object?>> _next() async {
    if (!await _lines.moveNext()) throw StateError('bench process ended');
    return Map<String, Object?>.from(jsonDecode(_lines.current) as Map);
  }

  Future<Map<String, Object?>> call(String op, [Map<String, Object?> fields = const {}]) async {
    process.stdin.writeln(jsonEncode({'op': op, ...fields}));
    final answer = await _next();
    if (answer.containsKey('error')) throw StateError('bench: ${answer['error']}');
    return answer;
  }

  Future<void> stop() async {
    await process.stdin.close();
    await process.exitCode;
  }
}

/// The adapter's port over the bench: published reply in, request and commit out.
final class BenchPort implements CipHostPort {
  final Bench bench;
  @override
  final String root;
  BenchPort(this.bench, this.root);

  @override
  Future<Map<String, Object?>> reply() => bench.call('reply');

  @override
  Future<Map<String, Object?>> submit(
      Map<String, Object?> envelope, Map<String, Object?> body) async {
    final answer = await bench.call('submit', {'envelope': envelope, 'body': body});
    final reply = answer['reply'];
    if (reply == null) throw const CipHostUnanswered('no acknowledgement');
    return Map<String, Object?>.from(reply as Map);
  }

  @override
  Future<CipHostFacts> facts() async {
    final f = await bench.call('facts');
    return CipHostFacts(
        f['root'] as String,
        f['revision'] as int,
        [
          for (final c in f['capabilities'] as List)
            CipHostCapability(c[0] as int, c[1] as String, c[2] as int, c[3] as int)
        ],
        [for (final code in f['codes'] as List) code as String],
        f['capacity'] as int);
  }

  @override
  Future<String> keyText(int numeric) async =>
      (await bench.call('key', {'numeric': numeric}))['text'] as String;

  @override
  Future<void> wait() => bench.call('scan');
}

String _hex(List<int> bytes) =>
    bytes.map((b) => b.toRadixString(16).padLeft(2, '0')).join();

Uint8List _bytes(String hex) => Uint8List.fromList(
    [for (var i = 0; i < hex.length; i += 2) int.parse(hex.substring(i, i + 2), radix: 16)]);

/// A symbolic request path as (name, element index or null) segments.
List<List<Object?>> _segments(Uint8List bytes) {
  final out = <List<Object?>>[];
  final view = ByteData.sublistView(bytes);
  for (var at = 0; at < bytes.length;) {
    final kind = bytes[at++];
    if (kind == 0x91) {
      final n = bytes[at++];
      out.add([String.fromCharCodes(bytes.sublist(at, at + n)), null]);
      at += n + n % 2;
    } else if (kind == 0x28) {
      out.last[1] = bytes[at++];
    } else if (kind == 0x29) {
      out.last[1] = view.getUint16(at + 1, Endian.little);
      at += 3;
    } else if (kind == 0x2a) {
      out.last[1] = view.getUint32(at + 1, Endian.little);
      at += 5;
    } else {
      throw FormatException('unexpected path segment $kind');
    }
  }
  return out;
}

/// The controller's read connection: Read Tag answered from the bench.
final class BenchWire implements CipReadTransport {
  final Bench bench;
  bool closed = false;
  BenchWire(this.bench);

  @override
  Future<CipReply> request(int service, Uint8List path, [Uint8List? data]) async {
    if (service != 0x52) throw UnsupportedError('the port only reads tags');
    final answer = await bench.call('read_tag', {'path': _segments(path)});
    return CipReply(0, const [], _bytes(answer['data'] as String));
  }

  @override
  Future<void> close() async => closed = true;
  @override
  void abort() => closed = true;
}

/// The controller's command connection. A write reaches the bench unless the
/// test drops it (no acknowledgement follows) or refuses it (a CIP error).
final class BenchCommand implements CipCommandTransport {
  final Bench bench;
  final List<String> writes;
  final bool drop, refuse;
  bool aborted = false;
  BenchCommand(this.bench, this.writes, {required this.drop, required this.refuse});

  @override
  int get connectionBytes => 4000;

  @override
  Future<CipReply> writeTag(String symbol, Uint8List data) async {
    writes.add(symbol);
    if (refuse) return CipReply(0x05, const [], Uint8List(0));
    if (!drop) await bench.call('write_tag', {'symbol': symbol, 'data': _hex(data)});
    return CipReply(0, const [], Uint8List(0));
  }

  @override
  Future<void> close() async {}
  @override
  void abort() => aborted = true;
}

/// The real port over the bench's wire, as discovery builds it.
final class WirePort {
  final CipHostIngress port;
  final List<String> writes;
  final List<BenchCommand> opened;
  WirePort._(this.port, this.writes, this.opened);

  static Future<WirePort> create(Bench bench, {bool drop = false, bool refuse = false}) async {
    final capture = await bench.call('capture');
    final namespace = CipNamespace.fromCapture(
        {'symbols': capture['symbols'], 'templates': capture['templates']});
    final manifest =
        CipManifest.fromNormalized(Map<String, Object?>.from(capture['manifest'] as Map));
    final writes = <String>[], opened = <BenchCommand>[];
    final ports = cipHostIngresses(BenchWire(bench), namespace, manifest, (bytes) async {
      expect(bytes, 4000);
      final command = BenchCommand(bench, writes, drop: drop, refuse: refuse);
      opened.add(command);
      return command;
    });
    return WirePort._(ports.single, writes, opened);
  }
}

/// A fresh station, its adapter, and the folders the adapter keeps.
final class Rig {
  final Bench bench;
  final Directory folder;
  final RootService service;
  final FileStore store;
  final FileMedium medium;
  Rig._(this.bench, this.folder, this.service, this.store, this.medium);

  /// [wire] answers through the real `CipHostIngress` instead of plain values.
  static Future<Rig> create(Bench bench, {required bool live, bool wire = false}) async {
    await bench.call('station');
    final facts = await BenchPort(bench, '').facts();
    final folder = await Directory.systemTemp.createTemp('fraktal_host_adapter_');
    final store = FileStore(Directory('${folder.path}/sets'));
    final medium = FileMedium(Directory('${folder.path}/live'));
    final CipHostPort port =
        wire ? (await WirePort.create(bench)).port : BenchPort(bench, facts.root);
    final service = RootService(port, store, live ? medium : null,
        clock: () => 100.0, wall: () => 1790899200, keepInterval: 0, retry: 0);
    return Rig._(bench, folder, service, store, medium);
  }

  Future<void> dispose() => folder.delete(recursive: true);

  /// An operator command, answered with whatever the adapter serves.
  Future<Map<String, Object?>> command(int kind, [Map<String, Object?> arguments = const {}]) async {
    final sequence = (await bench.call('command', {'kind': kind, 'arguments': arguments}))['sequence'];
    for (var i = 0; i < 40; i++) {
      final answer = await bench.call('answered', {'sequence': sequence});
      if (answer['answered'] == true) return answer;
      await bench.call('scan');
      await service.step();
    }
    throw StateError('the command was never answered');
  }

  Future<void> settle([int steps = 10]) async {
    for (var i = 0; i < steps; i++) {
      await bench.call('scan');
      await service.step();
    }
  }

  Future<Map<String, Object?>> read() => bench.call('read');

  /// [predecessor] renders as the same declaration without host services saved it.
  Future<Document> engineering(String name, int kind, String source,
          {String model = '', int created = 0, int clock = 0, bool predecessor = false}) async =>
      [
        for (final line in (await bench.call('document', {
          'name': name,
          'kind': kind,
          'source': source,
          'model': model,
          'created': created,
          'clock': clock,
          'predecessor': predecessor
        }))['document'] as List)
          Map<String, Object?>.from(line as Map)
      ];
}

bool get _available {
  try {
    return _tools.existsSync() &&
        Process.runSync(_python, ['--version']).exitCode == 0;
  } on ProcessException {
    return false;
  }
}

void main() {
  final skip = _available ? false : 'needs Python and the Fraktal/AB tools beside the HMI';

  for (final wire in [false, true]) {
  group(wire ? 'configuration sets through the CIP port' : 'configuration sets', () {
    late Bench bench;
    setUpAll(() async => bench = await Bench.start('sets'));
    tearDownAll(() => bench.stop());

    late Rig r;
    setUp(() async => r = await Rig.create(bench, live: false, wire: wire));
    tearDown(() => r.dispose());

    test('save, list, load, export and delete go through the adapter\'s store', () async {
      expect((await r.command(save, {'TextValue': 'alpha', 'IntValue': 1}))['accepted'], 1);
      await r.settle();
      expect(((await r.read())['persist'] as Map)['Pending'], 0);
      final saved = r.store.read('alpha');
      // Rendered from published facts, equal to the declaration's rendering.
      expect(saved,
          await r.engineering('alpha', 1, 'station',
              created: saved.first['created'] as int, clock: saved.first['clock'] as int));
      expect((await r.command(list))['accepted'], 1);
      expect(((await r.read())['catalog'] as List)[0], 1);
      final before = (await r.read())['station'];
      final number = saved[1];
      final members = (await bench.call('members'))['members'] as Map;
      await bench.call('set', {'key': number['key'], 'value': (members[number['key']] as List)[1]});
      expect((await r.command(load, {'TextValue': 'alpha'}))['accepted'], 1);
      expect((await r.read())['station'], before);
      expect((await r.command(export, {'TextValue': 'alpha', 'IntValue': 2}))['accepted'], 1);
      expect((await r.read())['document'], renderLine(saved[2]));
      expect((await r.command(delete, {'TextValue': 'alpha'}))['accepted'], 1);
      await r.settle();
      expect(r.store.list(), isEmpty);
    }, skip: skip);

    test('a current export is rendered, then served line by line', () async {
      expect((await r.command(exportCurrent, {'TextValue': 'now', 'IntValue': 1}))['accepted'], 1);
      final read = await r.read();
      final header = jsonDecode(read['document'] as String) as Map;
      expect([header['set'], header['kind']], ['now', 1]);
      final lines = (read['lines'] as List)[1] as int;
      expect((await r.command(export, {'TextValue': 'now', 'IntValue': lines}))['accepted'], 1);
      expect(((await r.read())['lines'] as List)[0], lines);
    }, skip: skip);

    test('an import in pieces is stored on commit', () async {
      final document = await r.engineering('imported', 1, 'initial');
      final lines = document.map(renderLine).toList();
      for (var index = 0; index < lines.length; index++) {
        final text = lines[index];
        final pieces = [for (var i = 0; i < text.length; i += 200) text.substring(i, i + 200 > text.length ? text.length : i + 200)];
        for (var p = 0; p < pieces.length; p++) {
          final last = index == lines.length - 1 && p == pieces.length - 1;
          final answer = await r.command(import, {
            'TextValue': pieces[p],
            'IntValue': p < pieces.length - 1 ? 1 : 0,
            'BoolValue': last ? 1 : 0
          });
          expect(answer['accepted'], 1, reason: 'line $index piece $p');
        }
      }
      await r.settle();
      expect(r.store.read('imported'), document);
    }, skip: skip);

    test('a stored value the controller cannot parse is sent as invalid, never coerced', () async {
      final document = await r.engineering('bad', 1, 'initial');
      final members = (await bench.call('members'))['members'] as Map;
      final target = document.skip(1).firstWhere((x) {
        final m = members[x['key']] as List;
        return x['type'] != 2 && (m[0] as int) <= 0 && (m[1] as int) >= 0;
      });
      target['value'] = '3.5';
      r.store.save(document);
      final before = (await r.read())['station'];
      expect((await r.command(load, {'TextValue': 'bad'}))['accepted'], 0);
      expect((await r.read())['station'], before);
      expect((await r.read())['rejectKey'], target['key']);
    }, skip: skip);

    test('a missing set and a full store refuse', () async {
      final missing = await r.command(load, {'TextValue': 'nothing'});
      expect(missing['accepted'], 0);
      // Refused by the transaction, which audits it: the host answered.
      expect(missing['diagnostic'], 'std.error.configSetRejected');
      expect((await r.read())['audits'], 1);
      for (final name in ['a', 'b', 'c', 'd']) {
        expect((await r.command(save, {'TextValue': name, 'IntValue': 1}))['accepted'], 1);
        await r.settle();
      }
      expect((await r.command(save, {'TextValue': 'e', 'IntValue': 1}))['accepted'], 0);
      expect((await r.command(save, {'TextValue': 'a', 'IntValue': 1}))['accepted'], 1);
    }, skip: skip);
  });
  }

  group('the CIP port', () {
    late Bench bench;
    setUpAll(() async => bench = await Bench.start('sets'));
    tearDownAll(() => bench.stop());
    setUp(() => bench.call('station'));

    final envelope = {
      'Service': CipHost.configSets,
      'JobSequence': 1,
      'Operation': load,
      'Argument': 0,
      'Chunk': 0,
      'Final': 1,
      'Status': CipHost.ok
    };

    test('reads the reply and the facts exactly as the controller holds them', () async {
      final w = await WirePort.create(bench);
      final plain = BenchPort(bench, w.port.root);
      expect(await w.port.reply(), await plain.reply());
      final mine = await w.port.facts(), theirs = await plain.facts();
      List<Object?> flat(CipHostFacts f) => [
            f.root,
            f.revision,
            [for (final c in f.capabilities) [c.ordinal, c.key, c.kind, c.valueType]],
            f.codes,
            f.capacity
          ];
      expect(flat(mine), flat(theirs));
      expect(mine.capabilities, hasLength(30));
      expect(w.writes, isEmpty);
    }, skip: skip);

    test('writes the payload, then its commit, and returns the acknowledgement', () async {
      final w = await WirePort.create(bench);
      final before = (await w.port.reply())['Serial'] as int;
      // No job is open, so the controller acknowledges and refuses it.
      final answer = await w.port.submit(envelope, {'Kind': CipHost.none});
      expect(answer['AckSequence'], before + 1);
      expect(answer['Accepted'], 0);
      expect(w.writes, ['FRK_Press_HostRequest', 'FRK_Press_HostCommit']);
      expect(w.opened, hasLength(1));
    }, skip: skip);

    test('an unacknowledged request is never resent', () async {
      final w = await WirePort.create(bench, drop: true);
      final before = await w.port.reply();
      await expectLater(w.port.submit(envelope, {'Kind': CipHost.none}),
          throwsA(isA<CipHostUnanswered>()));
      expect(w.writes, ['FRK_Press_HostRequest', 'FRK_Press_HostCommit']);
      expect(await w.port.reply(), before);
    }, skip: skip);

    test('a refused write is never resent, and the next request reopens the connection', () async {
      final w = await WirePort.create(bench, refuse: true);
      for (var attempt = 1; attempt <= 2; attempt++) {
        await expectLater(w.port.submit(envelope, {'Kind': CipHost.none}),
            throwsA(isA<CipHostUnanswered>()));
        expect(w.writes, List.filled(attempt, 'FRK_Press_HostRequest'));
        expect(w.opened, hasLength(attempt));
        expect(w.opened.last.aborted, isTrue);
      }
    }, skip: skip);
  });

  group('parity with the engineering code', () {
    late Bench bench;
    setUpAll(() async => bench = await Bench.start('sets'));
    tearDownAll(() => bench.stop());

    test('a chunk encodes to the engineering encoder\'s bytes', () async {
      final envelope = {
        'Service': CipHost.configSets,
        'JobSequence': 12,
        'Operation': load,
        'Argument': -3,
        'Chunk': 1,
        'Final': 0,
        'Status': CipHost.ok
      };
      final body = {
        'Kind': CipHost.records,
        'Count': 2,
        'Total': 2,
        'Scope': 'Press',
        'Keys': ['press.stroke', 'press.dwellMs'],
        'Revisions': [5480224, 5480224],
        'RecordKinds': [1, 1],
        'ValueTypes': [0, 3],
        'Values': [-12, 2500]
      };
      for (final sequence in [7, 0x7fffffff, 0xfffffffe]) {
        final python = await bench.call('encode', {
          'service': CipHost.configSets,
          'revision': 4242,
          'envelope': envelope,
          'body': body,
          'sequence': sequence
        });
        final row = Map<String, Object?>.from(python['row'] as Map);
        final namespace = CipNamespace.fromCapture(
            {'symbols': python['symbols'], 'templates': python['templates']});
        final (payload, commit) = CipHostLayout.negotiate(namespace, row).encode(
            manifestRevision: 4242,
            envelope: envelope,
            body: body,
            sequence: sequence,
            connectionBytes: 4000);
        String request(String symbol, List<int> data) {
          final path = cipSymbolPath(symbol);
          return [0x4d, path.length ~/ 2, ...path, ...data]
              .map((b) => b.toRadixString(16).padLeft(2, '0'))
              .join();
        }

        expect(request(row['RequestSymbol'] as String, payload), python['payload']);
        expect(request(row['CommitSymbol'] as String, commit), python['commit']);
      }
    }, skip: skip);

    test('the store and the medium write the engineering code\'s bytes, both ways', () async {
      final r = await Rig.create(bench, live: false);
      addTearDown(r.dispose);
      final document = await r.engineering('parity', 1, 'initial', created: 4294967295, clock: 1);
      // Every escape class the frozen ASCII transport admits.
      document[1]['value'] = 'q"b\\s\tc\u0001d~\u007f';
      final dart = Directory('${r.folder.path}/dart'), python = Directory('${r.folder.path}/python');
      FileStore(Directory('${dart.path}/sets')).save(document);
      FileMedium(Directory('${dart.path}/live')).write('Press.station', document);
      final written = await bench.call('python_store',
          {'directory': python.path, 'document': document, 'key': 'Press.station'});
      final files = <String, String>{
        for (final f in dart.listSync(recursive: true).whereType<File>())
          f.path.substring(dart.path.length + 1).replaceAll('\\', '/'): f.readAsStringSync()
      };
      expect(files, written['files']);
      // Python reads what Dart wrote, and Dart reads what Python wrote.
      expect(((await bench.call('python_store', {'directory': dart.path}))['listed'] as List).length, 1);
      expect(FileStore(Directory('${python.path}/sets')).read('parity'), document);
      expect(FileMedium(Directory('${python.path}/live')).read('Press.station'), document);
    }, skip: skip);

    test('lines the format refuses are refused, and Python\'s splitting is kept', () {
      for (final line in [
        '{"set":"a","set":"b"}',
        '{"scope":"P","key":"k","rev":1,"kind":1,"type":0,"value":NaN}',
        '{"scope":"P","key":"k","rev":1.0,"kind":1,"type":0,"value":"1"}',
        '{"scope":"P","key":"k","rev":true,"kind":1,"type":0,"value":"1"}',
        '{"scope":"P","key":"k","rev":1,"kind":1,"type":0,"value":"\u0009"}',
        '[]'
      ]) {
        expect(() => parseLine(line), throwsA(isA<SetRejected>()), reason: line);
      }
      expect(splitLines('a\r\nb\rc\nd\u000be\u001cf'), ['a', 'b', 'c', 'd', 'e', 'f']);
      expect(splitLines('a\n'), ['a']);
    });
  });

  group('live documents', () {
    late Bench bench;
    setUpAll(() async => bench = await Bench.start('live'));
    tearDownAll(() => bench.stop());

    late Rig r;
    setUp(() async => r = await Rig.create(bench, live: true));
    tearDown(() => r.dispose());

    test('a download is restored from the medium and then kept', () async {
      final facts = await r.service.port.facts();
      final root = facts.root, code = facts.codes.first;
      final station = await r.engineering(liveName, 1, 'changed', model: code, created: 1790899200);
      final model = await r.engineering(liveName, 0, 'changed', model: code, created: 1790899200);
      r.medium.write('$root.station', station);
      r.medium.write('$root.model1', model);
      expect((await r.read())['restoring'], 1);
      await r.settle(4);
      expect(r.service.health.restoredAt, isNotEmpty, reason: '${r.service.health.toJson()}');
      expect(r.service.health.losses, isEmpty);
      final read = await r.read();
      expect(read['stamped'], true);
      expect(read['station'], {
        for (final x in station.skip(1))
          x['key']: x['value'] == 'TRUE' ? 1 : x['value'] == 'FALSE' ? 0 : int.parse(x['value'] as String)
      });
      // Now kept: every document rewritten from the controller, as the keeper renders it.
      await r.settle(12);
      final kept = (await bench.call('kept', {'created': 1790899200}))['documents'] as Map;
      for (final entry in kept.entries) {
        final expected = [for (final l in entry.value as List) Map<String, Object?>.from(l as Map)];
        expect(content(r.medium.read(entry.key as String)!), content(expected), reason: '${entry.key}');
      }
    }, skip: skip);

    test('documents saved by the build without host services are restored', () async {
      // The first V6.11 download restores what V6.10 kept: same values, its revision.
      final facts = await r.service.port.facts();
      final root = facts.root, code = facts.codes.first;
      final station = await r.engineering(liveName, 1, 'changed',
          model: code, created: 1790899200, predecessor: true);
      final model = await r.engineering(liveName, 0, 'changed',
          model: code, created: 1790899200, predecessor: true);
      expect(station.first['configRev'], isNot(facts.revision));
      r.medium.write('$root.station', station);
      r.medium.write('$root.model1', model);
      await r.settle(4);
      expect(r.service.health.restoredAt, isNotEmpty, reason: '${r.service.health.toJson()}');
      expect(r.service.health.losses, isEmpty);
      final read = await r.read();
      expect(read['stamped'], true);
      expect(read['station'], {
        for (final x in station.skip(1))
          x['key']: x['value'] == 'TRUE' ? 1 : x['value'] == 'FALSE' ? 0 : int.parse(x['value'] as String)
      });
    }, skip: skip);

    test('a lost document is restored as a loss', () async {
      final facts = await r.service.port.facts();
      final root = facts.root, code = facts.codes.first;
      r.medium.write('$root.station', await r.engineering(liveName, 1, 'initial', model: code));
      r.medium.write('$root.model1', await r.engineering(liveName, 0, 'initial', model: code));
      r.medium.pathOf('$root.model1').deleteSync();
      await r.settle(4);
      expect(r.service.health.restoredAt, isNotEmpty);
      expect([for (final (key, _) in r.service.health.losses) key], ['$root.model1']);
      expect(((await r.read())['persist'] as Map)['RestoreLost'], 1);
    }, skip: skip);

    test('an unreadable medium restores nothing', () async {
      Directory('${r.folder.path}/live').createSync(recursive: true);
      File('${r.folder.path}/live/$indexName').writeAsStringSync('not json');
      await r.settle(4);
      expect(r.service.health.state, 'unreadable');
      expect((await r.read())['restoring'], 1);
    }, skip: skip);
  });
}
