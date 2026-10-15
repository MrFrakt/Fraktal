// Core §3.8b parameter sets through the repository seam. The simulator stands
// in for the PLC; the OPC UA adapter's tiering is proven separately, because
// the listing and the export lines only exist as answers read right after a
// request - they must never ride in the cyclic snapshot.
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import 'package:fraktal_hmi/data/plc_repository.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  group('parameter sets through the repository', () {
    late SimRepository repo;
    setUp(() => repo = SimRepository());
    tearDown(() => repo.dispose());

    test('save, list, export, delete, import round trip', () async {
      expect(await repo.saveConfigSet('StationA', 'commissioned', CfgKind.stationCfg),
          isTrue);
      final sets = await repo.listConfigSets('StationA');
      expect(sets, isNotNull);
      expect(sets!.single.name, 'commissioned');
      expect(sets.single.kind, CfgKind.stationCfg);
      expect(sets.single.recordCount, greaterThan(0));

      final document = await repo.exportConfigSet('StationA', 'commissioned');
      expect(document, isNotNull);
      expect(document!.split('\n').first, contains('"set":"commissioned"'));

      expect(await repo.deleteConfigSet('StationA', 'commissioned'), isTrue);
      expect(await repo.listConfigSets('StationA'), isEmpty);
      expect(await repo.deleteConfigSet('StationA', 'commissioned'), isFalse,
          reason: 'deleting what is not there is refused');

      expect(await repo.importConfigSet('StationA', document), isTrue);
      expect((await repo.listConfigSets('StationA'))!.single.name, 'commissioned');
      expect(await repo.loadConfigSet('StationA', 'commissioned'), isTrue);
    });

    test('an empty set and a fifth name are refused', () async {
      // The simulator has no line data, so a line set would carry nothing.
      expect(await repo.saveConfigSet('StationA', 'nothing', CfgKind.lineCfg),
          isFalse);
      for (final name in ['a', 'b', 'c', 'd']) {
        expect(await repo.saveConfigSet('StationA', name, CfgKind.stationCfg),
            isTrue);
      }
      expect(await repo.saveConfigSet('StationA', 'e', CfgKind.stationCfg),
          isFalse,
          reason: 'the store never evicts somebody\'s set');
      expect(await repo.deleteConfigSet('StationA', 'a'), isTrue);
      expect(await repo.saveConfigSet('StationA', 'e', CfgKind.stationCfg),
          isTrue,
          reason: 'a deleted slot takes a new name');
    });

    test('a refused load names what it refused', () async {
      expect(await repo.loadConfigSet('StationA', 'missing'), isFalse);
      expect(await repo.configSetRejection('StationA'), contains('missing'));
    });

    test('a line longer than one request travels in pieces', () {
      expect(kConfigSetRequestTextMax, 255, reason: 'ST_HmiRequest.TextValue');
      expect(kConfigSetImportLineMax, 480, reason: 'the PLC document line');
      final line = List.filled(400, 'x').join();
      final pieces = configSetLinePieces(line);
      expect(pieces.map((p) => p.length), [255, 145]);
      expect(pieces.join(), line, reason: 'joined, the pieces are the line');
      expect(configSetLinePieces('{"a":1}'), ['{"a":1}']);
      expect(configSetLinePieces(List.filled(510, 'y').join()).map((p) => p.length),
          [255, 255]);
    });
  });

  group('the set answers are on-demand, never cyclic', () {
    for (final path in [
      'PLC1/MAIN/Press/ConfigSetCount',
      'PLC1/MAIN/Press/ConfigSets/ConfigSets[1]/SetName',
      'PLC1/MAIN/Press/ConfigSetDocument',
      'PLC1/MAIN/Press/ConfigSetDocumentLines',
    ]) {
      test(path,
          () => expect(OpcUaFieldTier.classify(path), FieldTier.onDemand));
    }
  });
}
