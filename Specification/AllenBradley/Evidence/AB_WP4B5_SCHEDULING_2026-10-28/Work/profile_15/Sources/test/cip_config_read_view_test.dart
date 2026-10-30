import 'dart:convert';
import 'dart:io';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/src/cip_manifest.dart';
import 'package:fraktal_opcua_client/src/cip_config_read_view.dart';
import 'package:fraktal_hmi/data/opcua_repository.dart';
import 'package:fraktal_hmi/data/opcua_session_client.dart';
import 'package:fraktal_hmi/data/scoped_plc_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/state/app_state.dart';

Map<String, Object?> view() {
  const root = 'FixtureConfig/View';
  return {
    for (final e in <String, Object?>{
      'SchemaVersion': 1,
      'RootIdentity': 'Fixture',
      'Revision': 19,
      'DefinitionCount': 2,
      'DefinitionCapacity': 2,
      'ValueCount': 3,
      'ValueCapacity': 6,
      for (var i = 0; i < 2; i++) ...{
        for (final e in cipConfigDefinitionLayout.entries)
          'Definitions[$i]/${e.key}': e.value.$2 > 0
              ? ''
              : e.value.$1 == 0xc1
                  ? false
                  : e.value.$1 == 0xcb
                      ? 0.0
                      : 0,
        'Definitions[$i]/DefinitionIndex': i,
        'Definitions[$i]/Scope': 'Fixture',
        'Definitions[$i]/Item': i == 0 ? 'Dwell' : 'Station',
        'Definitions[$i]/WriteKey': i == 0 ? 'model.dwell' : 'station.id',
        'Definitions[$i]/ModelScoped': i == 0,
        'Definitions[$i]/WriteRevision': 9,
        'Definitions[$i]/ValueType': 1,
        'Definitions[$i]/ConfigKind': i == 0 ? 0 : 1,
        'Definitions[$i]/Writable': true
      },
      for (var i = 0; i < 3; i++) ...{
        'Values[$i]/DefinitionIndex': i == 2 ? 0 : i,
        'Values[$i]/ModelOrdinal': i == 2 ? 1 : 0,
        'Values[$i]/ModelCode': i == 2 ? 'MODEL_A' : '',
        'Values[$i]/ValueText': i == 0
            ? '12'
            : i == 1
                ? '9'
                : '27',
        'Values[$i]/Readable': true,
        'Values[$i]/Revision': 19
      },
    }.entries)
      '$root/${e.key}': e.value
  };
}

Map<String, Object?> page(Map<String, Object?> values, {int model = 0}) =>
    cipConfigurationPage(
        values: values,
        canonicalRoot: 'FixtureConfig/View',
        rootSymbol: 'Fixture',
        modelOrdinal: model);

class ReadOnlyClient
    implements
        OpcUaSessionClient,
        OpcUaWritePolicyClient,
        OpcUaReadOnlyConfigurationClient {
  int writes = 0, queries = 0;
  @override
  bool get readOnly => true;
  @override
  Future<Map<String, Object?>> snapshot() async => {
        'values': {
          'Fixture/Status/Name': 'Fixture',
          'Fixture/Status/ModuleType': 1,
          'Fixture/Status/State': 0,
          'Fixture/Status/ConfigRev': 19,
          'Fixture/ModeActive': 1
        },
        'readServices': [
          {
            'Kind': 1,
            'Version': 1,
            'RootSymbol': 'Fixture',
            'CanonicalRoot': 'FixtureConfig/View'
          }
        ]
      };
  @override
  Future<Map<String, Object?>?> readConfigurationPage(
      String root, int model) async {
    queries++;
    return page(view(), model: model);
  }

  @override
  Future<bool> write(String path, OpcUaWriteType type, Object value) async {
    writes++;
    return true;
  }

  @override
  Future<void> close() async {}
}

class _VersionedView {
  static const prefix = 'FixtureConfig/View';
  final data = view();
  final reads = <List<String>>[];
  Set<String> unavailable = {};
  int headers = 0, assembled = 0;
  void Function(int)? afterHeader;
  Map<String, Object?>? lastAssembly;
  Future<Map<String, Object?>> fetch(List<String> paths) async {
    reads.add(List.of(paths));
    final result = {
      for (final e in data.entries)
        if (!unavailable.contains(e.key) &&
            paths.any((p) => e.key == p || e.key.startsWith('$p/')))
          e.key: e.value
    };
    if (paths.contains('$prefix/SchemaVersion')) {
      headers++;
      afterHeader?.call(headers);
    }
    return result;
  }

  Future<Map<String, Object?>> query(CipConfigurationCache cache,
          {int model = 0}) =>
      cipAcquireConfiguration(
          root: 'Fixture',
          modelOrdinal: model,
          descriptor: {
            'CanonicalRoot': prefix,
            'DefinitionCapacity': 2,
            'ValueCapacity': 6
          },
          cache: cache,
          fetch: fetch,
          assemble: (values) async {
            assembled++;
            lastAssembly = Map.of(values);
            return page(values, model: model);
          });
  void mask(int revision) {
    data['$prefix/Revision'] = revision;
    for (var i = 0; i < 3; i++) {
      data['$prefix/Values[$i]/Revision'] = revision;
      data['$prefix/Values[$i]/Readable'] = false;
      data['$prefix/Values[$i]/ValueText'] = '';
    }
    for (var i = 0; i < 2; i++) {
      data['$prefix/Definitions[$i]/ReadLevel'] = 4;
    }
  }
}

void main() {
  CipConfigurationCache cache({int Function()? clock}) => CipConfigurationCache(
      maxSilence: const Duration(seconds: 5), clockUs: clock);
  test('an unchanged configuration is revalidated using fresh headers only',
      () async {
    final source = _VersionedView(), retained = cache();
    final first = await source.query(retained);
    source.reads.clear();
    expect(await source.query(retained), first);
    expect(source.reads.length, 2);
    expect(
        source.reads
            .every((p) => p.contains('${_VersionedView.prefix}/SchemaVersion')),
        true);
  });
  test(
      'incomplete configuration stays unavailable while coherent rows survive for revalidation',
      () async {
    final source = _VersionedView(), retained = cache();
    source.unavailable = {'${_VersionedView.prefix}/Definitions[0]/Scope'};
    await expectLater(source.query(retained), throwsFormatException);
    source.unavailable = {};
    source.reads.clear();
    expect(await source.query(retained), page(source.data));
    expect(source.reads.expand((p) => p),
        contains('${_VersionedView.prefix}/Definitions[0]'));
    expect(source.reads.expand((p) => p),
        isNot(contains('${_VersionedView.prefix}/Definitions[1]')));
  });
  test('a permission revision discards every cached plaintext and policy field',
      () async {
    final source = _VersionedView(), retained = cache();
    await source.query(retained);
    source.mask(20);
    source.reads.clear();
    final masked = await source.query(retained);
    expect(masked, page(source.data));
    expect(source.reads.length, greaterThan(2));
    expect(masked['Entries[1]/ValueText'], '');
    expect(masked['Entries[1]/Readable'], false);
    expect(masked['Entries[1]/ReadLevel'], 4);
  });
  test('a changed final version refuses a cached page before assembly',
      () async {
    final source = _VersionedView(), retained = cache();
    await source.query(retained);
    source.afterHeader = (n) {
      if (n == 3) source.mask(20);
    };
    await expectLater(source.query(retained), throwsFormatException);
    expect(source.assembled, 1);
    expect(await source.query(retained), page(source.data));
  });
  test(
      'an expired cache lease requires native rows even when the token matches',
      () async {
    var now = 0;
    final source = _VersionedView(), retained = cache(clock: () => now);
    await source.query(retained);
    now = 5000000;
    source.reads.clear();
    expect(await source.query(retained), page(source.data));
    expect(source.reads.length, greaterThan(2));
  });
  test('a bank query never supplies cached payloads from a different bank',
      () async {
    final source = _VersionedView(), retained = cache();
    await source.query(retained);
    expect(await source.query(retained, model: 1), page(source.data, model: 1));
    for (final i in [0, 1]) {
      expect(
          source.lastAssembly!
              .containsKey('${_VersionedView.prefix}/Values[$i]/ValueText'),
          false);
      expect(
          source.lastAssembly!
              .containsKey('${_VersionedView.prefix}/Values[$i]/Readable'),
          false);
    }
  });
  test(
      'configuration batches yield between bounded reads and fetch only the selected bank values',
      () async {
    final fixture = jsonDecode(utf8.decode(gzip.decode(
        File('test/fixtures/cip_read_view_goldens.json.gz')
            .readAsBytesSync()))) as Map;
    final all = Map<String, Object?>.from(fixture['values'] as Map),
        prefix = fixture['canonicalRoot'] as String;
    final batches = <List<String>>[];
    final result = await cipAcquireConfiguration(
        root: fixture['rootSymbol'] as String,
        modelOrdinal: 1,
        descriptor: {
          'CanonicalRoot': prefix,
          'DefinitionCapacity': all['$prefix/DefinitionCapacity'],
          'ValueCapacity': all['$prefix/ValueCapacity']
        },
        fetch: (paths) async {
          batches.add(paths);
          return {
            for (final e in all.entries)
              if (paths.any((p) => e.key == p || e.key.startsWith('$p/')))
                e.key: e.value
          };
        },
        assemble: (values) async => cipConfigurationPage(
            values: values,
            canonicalRoot: prefix,
            rootSymbol: fixture['rootSymbol'] as String,
            modelOrdinal: 1));
    expect(result['EntryCount'], (fixture['expectedPages'] as List)[1].length);
    expect(batches.length, greaterThan(4));
    expect(batches.every((b) => b.length <= 7), true);
    expect(
        batches
            .where((b) => b.any((p) => p.contains('/Definitions[')))
            .every((b) => b.length == 1),
        true);
    expect(
        batches
            .where((b) => b.any((p) => p.contains('/Values[')))
            .every((b) => b.length == 1 || b.length == 4),
        true);
    final requested = batches.expand((b) => b).toSet();
    for (var i = 0; i < (all['$prefix/ValueCount'] as int); i++) {
      expect(requested.contains('$prefix/Values[$i]'),
          all['$prefix/Values[$i]/ModelOrdinal'] == 1);
    }
  });
  test(
      'generated V6.8 hash and all 979 view paths produce the independent four configuration pages',
      () {
    final fixture = jsonDecode(utf8.decode(gzip.decode(
        File('test/fixtures/cip_read_view_goldens.json.gz')
            .readAsBytesSync()))) as Map;
    final manifest = CipManifest.fromNormalized(
        Map<String, Object?>.from(fixture['manifest'] as Map));
    expect(manifest.minor, 8);
    expect(manifest.rows('readServices'), hasLength(1));
    final values = Map<String, Object?>.from(fixture['values'] as Map);
    expect(values, hasLength(979));
    for (var bank = 0;
        bank < (fixture['expectedPages'] as List).length;
        bank++) {
      final page = cipConfigurationPage(
          values: values,
          canonicalRoot: fixture['canonicalRoot'] as String,
          rootSymbol: fixture['rootSymbol'] as String,
          modelOrdinal: bank);
      final rows = [
        for (var i = 1; i <= (page['EntryCount'] as int); i++)
          {
            for (final e in page.entries)
              if (e.key.startsWith('Entries[$i]/'))
                e.key.substring('Entries[$i]/'.length): e.value
          }
      ];
      expect(rows, (fixture['expectedPages'] as List)[bank]);
    }
  });
  test(
      'read view joins live and selected-bank entries without another bank value',
      () {
    expect(page(view())['EntryCount'], 2);
    final bank = view()
      ..remove('FixtureConfig/View/Values[0]/ValueText')
      ..remove('FixtureConfig/View/Values[1]/ValueText');
    expect(page(bank, model: 1)['Entries[1]/ValueText'], '27');
    expect(page(bank, model: 1)['EntryCount'], 1);
  });
  test(
      'incomplete, mixed-revision, duplicate, wrong-bank or unmasked rows refuse',
      () {
    for (final change in [
      'missing',
      'revision',
      'duplicate',
      'bank',
      'mask',
      'identity',
      'count'
    ]) {
      final v = view();
      switch (change) {
        case 'missing':
          v.remove('FixtureConfig/View/Definitions[0]/Item');
        case 'revision':
          v['FixtureConfig/View/Values[2]/Revision'] = 20;
        case 'duplicate':
          v['FixtureConfig/View/Values[2]/ModelOrdinal'] = 0;
          v['FixtureConfig/View/Values[2]/ModelCode'] = '';
        case 'bank':
          v['FixtureConfig/View/Values[2]/DefinitionIndex'] = 1;
        case 'mask':
          v['FixtureConfig/View/Values[0]/Readable'] = false;
        case 'identity':
          v['FixtureConfig/View/RootIdentity'] = 'Other';
        case 'count':
          v['FixtureConfig/View/ValueCount'] = 5;
      }
      expect(() => page(v), throwsFormatException, reason: change);
    }
  });
  test(
      'repository and root scope preserve read-only policy and never query through a mailbox',
      () async {
    final client = ReadOnlyClient(),
        repo = await OpcUaRepository.connectWithClient(client,
            refreshInterval: const Duration(days: 1));
    final scoped =
        ScopedPlcRepository(repo, allowedRoots: ['Fixture'], configured: true);
    addTearDown(scoped.dispose);
    expect(repo.readOnly, true);
    expect(scoped.readOnly, true);
    final app = AppState(scoped);
    addTearDown(app.dispose);
    for (final action in GatedAction.values) {
      expect(
          app.permitsLocal(action,
              forSession: const AccessSession(level: AccessLevel.admin)),
          action == GatedAction.dataRead || action == GatedAction.alarmHistory,
          reason: action.name);
    }
    expect(await repo.login('Fixture', 'user', 'secret'), false);
    expect(await repo.start('Fixture'), false);
    expect(await repo.setMode('Fixture', UnitMode.manual), false);
    expect(await repo.queryModelConfig('Fixture', 1), isNotNull);
    expect(client.queries, greaterThan(0));
    expect(client.writes, 0);
  });
}
