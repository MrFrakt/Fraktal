// Core §8.5.2 - a Unit on a line publishes its shift in force and the shifts it
// closed; the mapper turns them into a facet, and a Unit on no line gets none.
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';

Map<String, Object?> _unit(Map<String, Object?> extra) => {
      'protocol': 'fraktal.opcua.snapshot.v1',
      'values': {
        'PLC1/MAIN/Press/Status/Name': 'Press',
        'PLC1/MAIN/Press/Status/ModuleType': 1,
        'PLC1/MAIN/Press/Status/State': 0,
        'PLC1/MAIN/Press/Status/TileEnable': true,
        'PLC1/MAIN/Press/ModeActivePublished': 0,
        ...extra,
      },
    };

void main() {
  test('unscheduled intervals retain a facet, history and next boundary', () {
    final ends = DateTime.utc(2026, 10, 10, 8);
    final projection = OpcUaSnapshotMapper().map(_unit({
      'PLC1/MAIN/Press/CurrentShift': 0,
      'PLC1/MAIN/Press/ShiftEndsAt': ends.toIso8601String(),
      'PLC1/MAIN/Press/ShiftTimeSynchronized': false,
      'PLC1/MAIN/Press/ShiftCalendarPending': true,
      'PLC1/MAIN/Press/ShiftHistoryCount': 1,
      'PLC1/MAIN/Press/ShiftHistory[1]/ShiftIndex': 0,
      'PLC1/MAIN/Press/ShiftHistory[1]/GoodCount': 3,
    }));
    final facet = projection.forest.single.shift!;
    expect(facet.currentShift, 0);
    expect(facet.endsAt, ends);
    expect(facet.calendarPending, isTrue);
    expect(facet.timeSynchronized, isFalse);
    expect(facet.history.single.good, 3);
  });
  test('a Unit on a line maps its current shift and closed shifts', () {
    final started = DateTime.utc(2026, 9, 27, 14);
    // As ADS delivers a TwinCAT DT: Unix seconds.
    int dt(DateTime t) => t.millisecondsSinceEpoch ~/ 1000;
    final projection = OpcUaSnapshotMapper().map(_unit({
      'PLC1/MAIN/Press/CurrentShift': 2,
      'PLC1/MAIN/Press/ShiftStartedAt': dt(started),
      'PLC1/MAIN/Press/ShiftHistoryCount': 1,
      'PLC1/MAIN/Press/ShiftHistoryTruncated': false,
      'PLC1/MAIN/Press/ShiftHistory/1/ShiftIndex': 1,
      'PLC1/MAIN/Press/ShiftHistory/1/StartAt': dt(DateTime.utc(2026, 9, 27, 6)),
      'PLC1/MAIN/Press/ShiftHistory/1/EndAt': dt(started),
      'PLC1/MAIN/Press/ShiftHistory/1/TimeSynchronized': false,
      'PLC1/MAIN/Press/ShiftHistory/1/ManualReset': true,
      'PLC1/MAIN/Press/ShiftHistory/1/GoodCount': 412,
      'PLC1/MAIN/Press/ShiftHistory/1/NokCount': 3,
      'PLC1/MAIN/Press/ShiftHistory/1/ReworkCount': 1,
      'PLC1/MAIN/Press/ShiftHistory/1/Oee': 0.81,
      'PLC1/MAIN/Press/ShiftHistory/1/OeeValid': true,
      'PLC1/MAIN/Press/ShiftHistory/1/Availability': 0.9,
      'PLC1/MAIN/Press/ShiftHistory/1/Performance': 0.91,
      'PLC1/MAIN/Press/ShiftHistory/1/Quality': 0.99,
      'PLC1/MAIN/Press/ShiftHistory/1/AvailValid': true,
      'PLC1/MAIN/Press/ShiftHistory/1/PerfValid': false,
      'PLC1/MAIN/Press/ShiftHistory/1/QualValid': true,
      'PLC1/MAIN/Press/ShiftHistory/1/RunMs': 120456,
      'PLC1/MAIN/Press/ShiftHistory/1/DownMs': 8000,
      'PLC1/MAIN/Press/ShiftHistory/1/IdleMs': 1000,
    }));
    final shift = projection.forest.single.shift;
    expect(shift, isNotNull);
    expect(shift!.currentShift, 2);
    expect(shift.startedAt, started);
    final closed = shift.history.single;
    expect(closed.shiftIndex, 1);
    expect(closed.good, 412);
    expect(closed.nok, 3);
    expect(closed.oeeValid, isTrue);
    expect(closed.timeSynchronized, isFalse,
        reason: 'an unsynchronized boundary is carried, never hidden');
    expect(closed.manualReset, isTrue);
    expect(closed.availability, 0.9);
    expect(closed.performance, 0.91);
    expect(closed.quality, 0.99);
    expect(closed.availValid, isTrue);
    expect(closed.perfValid, isFalse);
    expect(closed.qualValid, isTrue);
    expect(closed.runTime.inMilliseconds, 120456);
    expect(closed.downTime.inSeconds, 8);
    expect(closed.idleTime.inSeconds, 1);
  });

  test('a Unit on no line has no shift facet', () {
    final projection = OpcUaSnapshotMapper().map(_unit({}));
    expect(projection.forest.single.shift, isNull);
  });

  test('closed shifts ride the slow heartbeat; the current shift stays live', () {
    expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/ShiftHistory/ShiftHistory[1]/GoodCount'),
        FieldTier.slow);
    expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/ShiftHistoryCount'),
        FieldTier.slow);
    expect(OpcUaFieldTier.classify('PLC1/MAIN/Press/CurrentShift'),
        FieldTier.live);
  });
}
