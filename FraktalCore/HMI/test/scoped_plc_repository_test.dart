import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/scoped_plc_repository.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/fieldbus.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('configured root scope filters reads and rejects writes outside it',
      () async {
    final scoped = ScopedPlcRepository(
      SimRepository(),
      allowedRoots: const ['StationA'],
      configured: true,
    );
    addTearDown(scoped.dispose);

    final roots = await scoped.forest().firstWhere((items) => items.isNotEmpty);
    expect(roots.map((root) => root.path), ['StationA']);

    final bus = await scoped.fieldbus().firstWhere((items) => items.isNotEmpty);
    final channelPaths = <String>[];
    void walk(List<BusNode> nodes) {
      for (final node in nodes) {
        channelPaths.addAll(node.channels.map((channel) => channel.path));
        walk(node.children);
      }
    }

    walk(bus);
    expect(channelPaths, isNotEmpty);
    expect(channelPaths.every((path) => path.startsWith('StationA.')), isTrue);
    expect(await scoped.start('ConveyorB'), isFalse);
    expect((await scoped.releaseReportStart('ConveyorB')).released, isFalse);
    expect(await scoped.login('ConveyorB', 'admin1', '2468'), isFalse);
  });

  test('forcing uses the channel ModulePath owner and manual-mode gate',
      () async {
    final scoped = ScopedPlcRepository(
      SimRepository(),
      allowedRoots: const ['StationA'],
      configured: true,
    );
    addTearDown(scoped.dispose);

    final bus = await scoped.fieldbus().firstWhere((items) => items.isNotEmpty);
    IoChannel? output;
    IoChannel? readOnlyOutput;
    void walk(List<BusNode> nodes) {
      for (final node in nodes) {
        for (final channel in node.channels) {
          if (output == null &&
              channel.dir == ChannelDir.output &&
              channel.forceable) {
            output = channel;
          }
          if (readOnlyOutput == null &&
              channel.dir == ChannelDir.output &&
              !channel.forceable) {
            readOnlyOutput = channel;
          }
        }
        walk(node.children);
      }
    }

    walk(bus);
    expect(output, isNotNull);
    expect(readOnlyOutput, isNotNull);
    expect(output!.modulePath, startsWith('StationA'));
    expect(await scoped.login('StationA', 'tech1', '4711'), isTrue);
    expect(await scoped.forceChannel('StationA', output!.path, force: true),
        isFalse,
        reason: 'AUTO mode must not permit channel forcing');
    expect(await scoped.setMode('StationA', UnitMode.manual), isTrue);
    expect(await scoped.forceChannel('StationA', output!.path, force: true),
        isTrue);
    expect(
        await scoped.forceChannel('StationA', readOnlyOutput!.path,
            force: true),
        isFalse,
        reason: 'output direction alone must not grant force capability');
    expect(
        await scoped.forceChannel('StationA', 'StationA.Unknown.Output',
            force: true),
        isFalse);
  });
}
