import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('default access policy covers every PLC gated-action ordinal', () {
    const session = AccessSession();

    expect(session.required, hasLength(GatedAction.values.length));
    for (final action in GatedAction.values) {
      expect(session.permits(action), isTrue,
          reason: '${action.name} must be open by default');
    }
  });

  test('short stale policy fails closed instead of throwing', () {
    const session = AccessSession(required: [AccessLevel.none]);

    expect(session.permits(GatedAction.dataRead), isTrue);
    expect(session.permits(GatedAction.alarmShelve), isFalse);
  });

  test('PLC policy edits are self-gated and preserve the timeout', () async {
    final repo = SimRepository();
    addTearDown(repo.dispose);

    expect(
        await repo.setAccessLevel(
            'StationA', GatedAction.dataWrite, AccessLevel.technician),
        isTrue,
        reason: 'other thresholds may be commissioned while policy is open');
    expect(
        await repo.setAccessLevel(
            'StationA', GatedAction.accessPolicy, AccessLevel.admin),
        isFalse,
        reason: 'an anonymous session must not lock out retained policy edits');

    expect(await repo.login('StationA', 'admin1', '2468'), isTrue);
    expect(
        await repo.setAccessLevel(
            'StationA', GatedAction.accessPolicy, AccessLevel.admin),
        isTrue);
    expect(
        await repo.setSessionTimeout('StationA', const Duration(minutes: 15)),
        isTrue);

    final root = await repo
        .forest()
        .map((roots) => roots.firstWhere((root) => root.path == 'StationA'))
        .first;
    expect(root.access!.required[GatedAction.dataWrite.index],
        AccessLevel.technician);
    expect(root.access!.sessionTimeout, const Duration(minutes: 15));

    await repo.logout('StationA');
    expect(
        await repo.setAccessLevel(
            'StationA', GatedAction.dataRead, AccessLevel.operator),
        isFalse,
        reason: 'policy edits are self-gated after commissioning');
  });
}
