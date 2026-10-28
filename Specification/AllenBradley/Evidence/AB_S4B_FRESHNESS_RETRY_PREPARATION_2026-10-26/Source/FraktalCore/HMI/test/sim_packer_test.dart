import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/localization/localization_controller.dart';

void main() {
  test('simulation publishes Packer C and its packing cell and nested Unit',
      () async {
    final repository = SimRepository();
    addTearDown(repository.dispose);
    final forest = await repository.forest().first;
    expect(forest.map((node) => node.path),
        ['StationA', 'ConveyorB', 'PackerC']);

    final packer = forest.singleWhere((node) => node.path == 'PackerC');
    expect(packer.type, ModuleType.unit);
    expect(packer.controlDomainId, 'Cell2');
    expect(packer.controlDomainName, 'Cell 2 (packing)');
    expect(packer.controlDomainMembers, ['PackerC']);
    final labeler =
        packer.children.singleWhere((node) => node.path == 'PackerC.Labeler');
    expect(labeler.type, ModuleType.unit);
    expect(labeler.children.map((node) => node.path),
        containsAll(['PackerC.Labeler.Printer', 'PackerC.Labeler.Applicator']));

    final localization = LocalizationController(
        enabledLanguages: {'en'}, activeLanguage: 'en');
    addTearDown(localization.dispose);
    expect(localization.resolve(packer.displayNameKey), 'Packer C');
  });
}
