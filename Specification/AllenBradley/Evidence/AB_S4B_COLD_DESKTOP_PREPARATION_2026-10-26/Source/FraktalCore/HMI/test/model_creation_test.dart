import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/parameter_set_export.dart';

void main() {
  test('new model preserves active recipe and can be edited separately',
      () async {
    final repo = SimRepository();
    addTearDown(repo.dispose);
    final active = await repo.queryModelConfig('StationA', 0);
    expect(await repo.createModel('StationA', 'NEW', sourceModel: 2), isTrue);
    final fields = (await repo.queryModelConfig('StationA', 4))!;
    expect(fields.single.value, '180');
    expect(
        await repo.writeConfig('StationA', fields.single, '190', modelIndex: 4),
        isTrue);
    expect((await repo.queryModelConfig('StationA', 0))!.single.value,
        active!.single.value);
    expect(await repo.createModel('StationA', 'NEW'), isFalse);
    expect(await repo.createModel('StationA', 'BAD CODE'), isFalse);
    for (var i = 0; i < 4; i++) {
      expect(await repo.createModel('StationA', 'NEW$i'), isTrue);
    }
    expect(await repo.createModel('StationA', 'FULL'), isFalse);
  });
  test('current values export does not fill the saved-set store', () async {
    final repo = SimRepository();
    addTearDown(repo.dispose);
    expect(await repo.exportCurrentConfig('StationA', CfgKind.stationCfg),
        isNotNull);
    expect(await repo.listConfigSets('StationA'), isEmpty);
    expect(parameterSetFileName('../../name:*'), '______name__.jsonl');
  });
}
