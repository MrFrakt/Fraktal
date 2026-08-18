import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_snapshot_mapper.dart';
import 'package:fraktal_hmi/domain/module_node.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  test('discovers a generic Unit and nested CM from Status contract members',
      () {
    final projection = OpcUaSnapshotMapper().map({
      'protocol': 'fraktal.opcua.snapshot.v1',
      'values': {
        'PLC1/MAIN/PneumaticPress/Status/Name': 'PneumaticPress',
        'PLC1/MAIN/PneumaticPress/Status/ModuleType': 1,
        'PLC1/MAIN/PneumaticPress/Status/State': 1,
        'PLC1/MAIN/PneumaticPress/Status/FaultActive': false,
        'PLC1/MAIN/PneumaticPress/Status/TileEnable': true,
        'PLC1/MAIN/PneumaticPress/ModeActivePublished': 0,
        'PLC1/MAIN/PneumaticPress/RunningPublished': true,
        'PLC1/MAIN/PneumaticPress/SupportedModesPublished': [
          true,
          true,
          true,
          true,
          false,
          false,
          false
        ],
        'PLC1/MAIN/PneumaticPress/AvailableModelCount': 3,
        'PLC1/MAIN/PneumaticPress/AvailableModels/1/ModelCode': 'ALUMINUM',
        'PLC1/MAIN/PneumaticPress/AvailableModels/2/ModelCode': 'PLASTIC',
        'PLC1/MAIN/PneumaticPress/AvailableModels/3/ModelCode': 'STEEL',
        'PLC1/MAIN/PneumaticPress/CurrentStep/StepNo': 880,
        'PLC1/MAIN/PneumaticPress/CurrentStep/StepName':
            'project.step.pressChangeoverAwaitConfirmation',
        'PLC1/MAIN/PneumaticPress/CurrentStep/TimeClass': 3,
        'PLC1/MAIN/PneumaticPress/CurrentStep/ExpectedTime': 0,
        'PLC1/MAIN/PneumaticPress/CurrentStep/Conds/1/Label':
            'project.condition.pressChangeoverConfirmation',
        'PLC1/MAIN/PneumaticPress/CurrentStep/Conds/1/Ok': false,
        'PLC1/MAIN/PneumaticPress/Decision/Prompt':
            'project.decision.pressChangeoverConfirm',
        'PLC1/MAIN/PneumaticPress/Decision/Options': [
          'project.decision.confirmChangeover',
          'project.decision.repeatChangeoverPosition',
          '',
          '',
          '',
          ''
        ],
        'PLC1/MAIN/PneumaticPress/Decision/Default': 0,
        'PLC1/MAIN/PneumaticPress/SupportedRunStylesPublished': [
          true,
          true,
          false
        ],
        'PLC1/MAIN/PneumaticPress/Access/CurrentLevel': 3,
        'PLC1/MAIN/PneumaticPress/Access/CurrentUser': 'engineer',
        'PLC1/MAIN/PneumaticPress/Access/Policy/Required':
            List<int>.filled(11, 0),
        'PLC1/MAIN/PneumaticPress/OutImm/Temperature': 42.5,
        'PLC1/MAIN/PneumaticPress/HmiRequest/Secret': 'must-not-bind',
        'PLC1/MAIN/PneumaticPress/PressRam/Status/Name':
            'PneumaticPress.PressRam',
        'PLC1/MAIN/PneumaticPress/PressRam/Status/ModuleType': 3,
        'PLC1/MAIN/PneumaticPress/PressRam/Status/State': 0,
        'PLC1/MAIN/PneumaticPress/PressRam/Status/TileEnable': true,
        'PLC1/MAIN/PneumaticPress/PressRam/OutImm/Closed': true,
      },
    });

    expect(projection.forest, hasLength(1));
    final root = projection.forest.single;
    expect(root.path, 'PneumaticPress');
    expect(root.type, ModuleType.unit);
    expect(root.modeActive, UnitMode.auto);
    expect(root.running, isTrue);
    expect(root.supportedModes,
        [UnitMode.auto, UnitMode.manual, UnitMode.home, UnitMode.changeover]);
    expect(root.availableModels, ['ALUMINUM', 'PLASTIC', 'STEEL']);
    expect(root.step?.stepNo, 880);
    expect(root.step?.timeClass, TimeClass.waitOperator);
    expect(root.step?.conds.single.ok, isFalse);
    expect(root.decision?.prompt, 'project.decision.pressChangeoverConfirm');
    expect(root.decision?.options, hasLength(2));
    expect(root.supportedRunStyles, [RunStyle.continuous, RunStyle.singleStep]);
    expect(root.access?.level, AccessLevel.engineer);
    expect(root.valueAt('OutImm/Temperature'), 42.5);
    expect(root.publishedValues, isNot(contains('PressRam/OutImm/Closed')));
    expect(root.publishedValues, isNot(contains('HmiRequest/Secret')));
    expect(root.children.single.path, 'PneumaticPress.PressRam');
    expect(root.children.single.valueAt('OutImm/Closed'), isTrue);
    expect(projection.browsePathByModulePath['PneumaticPress.PressRam'],
        'PLC1/MAIN/PneumaticPress/PressRam');
  });

  test('rejects arbitrary OPC UA trees without the Fraktal Status contract',
      () {
    final projection = OpcUaSnapshotMapper().map({
      'values': {'Objects/Server/ServerStatus/State': 0},
    });
    expect(projection.forest, isEmpty);
  });

  test('maps system health, time quality, and signal tower generically', () {
    final projection = OpcUaSnapshotMapper().map({
      'values': {
        'PLC1/MAIN/Unit/Status/Name': 'Unit',
        'PLC1/MAIN/Unit/Status/ModuleType': ModuleType.unit.index,
        'PLC1/MAIN/Unit/SystemHealth/Present': true,
        'PLC1/MAIN/Unit/SystemHealth/Healthy': false,
        'PLC1/MAIN/Unit/SystemHealth/TaskAvailable': true,
        'PLC1/MAIN/Unit/SystemHealth/TaskCycleUs': 1100,
        'PLC1/MAIN/Unit/SystemHealth/TaskJitterUs': 100,
        'PLC1/MAIN/Unit/SystemHealth/ControllerAvailable': true,
        'PLC1/MAIN/Unit/SystemHealth/CpuLoadPct': 32.5,
        'PLC1/MAIN/Unit/SystemHealth/MemoryAvailableMb': 1024,
        'PLC1/MAIN/Unit/SystemHealth/FieldbusAvailable': true,
        'PLC1/MAIN/Unit/SystemHealth/FieldbusMasterHealthy': true,
        'PLC1/MAIN/Unit/SystemHealth/TimeQuality/Available': true,
        'PLC1/MAIN/Unit/SystemHealth/TimeQuality/Synchronized': false,
        'PLC1/MAIN/Unit/SystemHealth/TimeQuality/Source': 'PTP',
        'PLC1/MAIN/Unit/SystemHealth/TimeQuality/OffsetUs': 2500,
        'PLC1/MAIN/Unit/SignalTower/Red': false,
        'PLC1/MAIN/Unit/SignalTower/Amber': true,
        'PLC1/MAIN/Unit/SignalTower/Green': false,
        'PLC1/MAIN/Unit/SignalTower/Blue': true,
        'PLC1/MAIN/Unit/SignalTower/White': false,
        'PLC1/MAIN/Unit/SignalTower/Horn': false,
        'PLC1/MAIN/Unit/SignalTower/TestActive': false,
      }
    });

    final unit = projection.forest.single;
    expect(unit.systemHealth?.healthy, isFalse);
    expect(unit.systemHealth?.taskCycleUs, 1100);
    expect(unit.systemHealth?.cpuLoadPct, 32.5);
    expect(unit.systemHealth?.time.source, 'PTP');
    expect(unit.systemHealth?.time.synchronized, isFalse);
    expect(unit.signalTower?.amber, isTrue);
    expect(unit.signalTower?.blue, isTrue);
  });

  test('hydrates live alarms, time quality, OEE, nameplate and safety facets',
      () {
    const base = 'PLC1/MAIN/Unit';
    final projection = OpcUaSnapshotMapper().map({
      'values': {
        '$base/Status/Name': 'Unit',
        '$base/Status/ModuleType': ModuleType.unit.index,
        '$base/Status/Diagnostic/Description': 'std.error.test',
        '$base/Status/Diagnostic/Since': 1784613600,
        '$base/Status/Diagnostic/TimeSynchronized': false,
        '$base/AlarmLog/Blocking': true,
        '$base/AlarmLog/Active/Active[1]/ReasonCode': 17,
        '$base/AlarmLog/Active/Active[1]/Description':
            'std.system.timeSyncLost',
        '$base/AlarmLog/Active/Active[1]/SourcePath': 'Unit.SystemHealth',
        '$base/AlarmLog/Active/Active[1]/Severity': Severity.low.index,
        '$base/AlarmLog/Active/Active[1]/ResetClass':
            ResetClass.autoReset.index,
        '$base/AlarmLog/Active/Active[1]/State': AlarmState.active.index,
        '$base/AlarmLog/Active/Active[1]/ComeAt': 1784613600,
        '$base/AlarmLog/Active/Active[1]/ComeTimeSynchronized': false,
        '$base/AlarmLog/RingHead': 1,
        '$base/AlarmLog/Ring/Ring[1]/ReasonCode': 2003,
        '$base/AlarmLog/Ring/Ring[1]/Description': 'std.error.interlock',
        '$base/AlarmLog/Ring/Ring[1]/SourcePath': 'Unit.Clamp',
        '$base/AlarmLog/Ring/Ring[1]/Severity': Severity.medium.index,
        '$base/AlarmLog/Ring/Ring[1]/ResetClass': ResetClass.autoReset.index,
        '$base/AlarmLog/Ring/Ring[1]/State': AlarmState.closed.index,
        // OPC UA DateTime: 100-ns ticks from 1601 (the ADS case above is DT
        // seconds from 1970). Both transports normalize to UTC DateTime.
        '$base/AlarmLog/Ring/Ring[1]/ComeAt': 134290871000000000,
        '$base/AlarmLog/Ring/Ring[1]/GoneAt': 134290871100000000,
        '$base/AlarmLog/Ring/Ring[1]/Duration': 10000,
        '$base/AlarmLog/Ring/Ring[1]/ComeTimeSynchronized': true,
        '$base/AlarmLog/Ring/Ring[1]/GoneTimeSynchronized': true,
        '$base/AlarmLog/MetaCount': 1,
        '$base/AlarmLog/Meta/Meta[1]/ReasonCode': 2003,
        '$base/AlarmLog/Meta/Meta[1]/OperatorAction': 'std.action.inspect',
        '$base/AlarmLog/Meta/Meta[1]/Consequence': 'std.consequence.stop',
        '$base/AlarmLog/Meta/Meta[1]/Priority': Severity.medium.index,
        '$base/AlarmLog/Meta/Meta[1]/Category': AlarmCategory.process.index,
        '$base/AlarmLog/Meta/Meta[1]/Shelvable': true,
        '$base/HostEvents/RingHead': 1,
        '$base/HostEvents/Count': 1,
        '$base/HostEvents/Capacity': 32,
        '$base/HostEvents/Ring/Ring[1]/Sequence': 7,
        '$base/HostEvents/Ring/Ring[1]/Kind': HostEventKind.nok.index,
        '$base/HostEvents/Ring/Ring[1]/StationPath': 'Unit',
        '$base/HostEvents/Ring/Ring[1]/PartUid': 'PART-42',
        '$base/HostEvents/Ring/Ring[1]/Stamp': 1784613610,
        '$base/HostEvents/Ring/Ring[1]/TimeSynchronized': true,
        '$base/HostEvents/Ring/Ring[1]/Verdict': Verdict.nok.index,
        '$base/HostEvents/Ring/Ring[1]/ReasonCode': 2003,
        '$base/Oee/Availability': .9,
        '$base/Oee/Performance': .8,
        '$base/Oee/Quality': .99,
        '$base/Oee/Oee': .7128,
        '$base/Oee/AvailValid': true,
        '$base/Oee/PerfValid': true,
        '$base/Oee/QualValid': true,
        '$base/Oee/OeeValid': true,
        '$base/Nameplate/ManufacturerName': 'Fraktal',
        '$base/Nameplate/ProductDesignation': 'Test Cell',
        '$base/Nameplate/SerialNumber': 'SN-1',
        '$base/Safety/Present': true,
        '$base/Safety/AllSafe': true,
        '$base/Safety/DeviceCount': 1,
        '$base/Safety/Devices/Devices[1]/Present': true,
        '$base/Safety/Devices/Devices[1]/Name': 'EStop',
        '$base/Safety/Devices/Devices[1]/Kind': SafetyDeviceKind.estop.index,
        '$base/Safety/Devices/Devices[1]/State': SafetyState.ready.index,
        '$base/Safety/Devices/Devices[1]/Ready': true,
        '$base/Safety/Devices/Devices[1]/FieldbusHealthy': true,
      }
    });

    final unit = projection.forest.single;
    expect(unit.diagnosticSince?.isUtc, isTrue);
    expect(unit.diagnosticTimeSynchronized, isFalse);
    expect(unit.activeEvents.single.reasonCode, 17);
    expect(unit.activeEvents.single.timestampsSynchronized, isFalse);
    expect(unit.ringEvents.single.duration, const Duration(seconds: 10));
    expect(unit.ringEvents.single.timestampsSynchronized, isTrue);
    final interlockMeta =
        unit.alarmMeta.singleWhere((meta) => meta.reasonCode == 2003);
    expect(unit.alarmMeta, hasLength(61));
    expect(interlockMeta.shelvable, isTrue);
    expect(interlockMeta.priority, Severity.medium);
    expect(interlockMeta.category, AlarmCategory.process);
    expect(unit.hostEvents.single.kind, HostEventKind.nok);
    expect(unit.hostEvents.single.partUid, 'PART-42');
    expect(unit.hostEvents.single.reasonCode, 2003);
    expect(unit.hostEvents.single.timeSynchronized, isTrue);
    expect(unit.oee?.oee, closeTo(.7128, .00001));
    expect(unit.nameplate?.serial, 'SN-1');
    expect(unit.safety?.devices.single.kind, SafetyDeviceKind.estop);
  });

  test('retains DataValue quality and timestamps for custom controls', () {
    final projection = OpcUaSnapshotMapper().map({
      'protocol': 'fraktal.opcua.snapshot.v1',
      'values': {
        'PLC1/MAIN/Unit/Status/Name': 'Unit',
        'PLC1/MAIN/Unit/Status/ModuleType': ModuleType.unit.index,
        'PLC1/MAIN/Unit/OutImm/GoodPressure': 4.2,
      },
      'dataValues': {
        'PLC1/MAIN/Unit/OutImm/GoodPressure': {
          'status': 0,
          'type': 'Double',
          'value': 4.2,
          'sourceTimestampUs': '1784613600123456',
        },
        'PLC1/MAIN/Unit/OutImm/BadPressure': {
          'status': 0x80000000,
          'type': 'Double',
          'value': 9.9,
          'sourceTimestampUs': '1784613600223456',
        },
      },
    });

    final unit = projection.forest.single;
    final good = unit.tagAt('OutImm/GoodPressure');
    final bad = unit.tagAt('OutImm/BadPressure');
    expect(good?.quality, PublishedTagQuality.good);
    expect(good?.value, 4.2);
    expect(good?.sourceTimestamp?.isUtc, isTrue);
    expect(bad?.quality, PublishedTagQuality.bad);
    expect(bad?.value, 9.9);
    expect(bad?.usable, isFalse);
    expect(unit.valueAt('OutImm/BadPressure'), isNull,
        reason: 'Bad values must not leak into the legacy scalar surface.');
  });

  test('keeps the direct root and discards TF6100 reference aliases', () {
    final projection = OpcUaSnapshotMapper().map({
      'values': {
        'PLC1/MAIN/PneumaticPress/Status/Name': 'PneumaticPress',
        'PLC1/MAIN/PneumaticPress/Status/ModuleType': ModuleType.unit.index,
        'PLC1/MAIN/PneumaticPress/ModeActivePublished': UnitMode.auto.index,
        'PLC1/MAIN/PneumaticPress/PressRam/Status/Name':
            'PneumaticPress.PressRam',
        'PLC1/MAIN/PneumaticPress/PressRam/Status/ModuleType':
            ModuleType.controlModule.index,
        // REFERENCE TO alias: browse name and Fraktal identity disagree.
        'PLC1/MAIN/RecipeCatalog/UnitRef/Status/Name': 'PneumaticPress',
        'PLC1/MAIN/RecipeCatalog/UnitRef/Status/ModuleType':
            ModuleType.unit.index,
        // A same-named owner alias still loses to the shallower direct root.
        'PLC1/MAIN/IoDriver/PneumaticPress/Status/Name': 'PneumaticPress',
        'PLC1/MAIN/IoDriver/PneumaticPress/Status/ModuleType':
            ModuleType.unit.index,
      },
    });

    expect(projection.forest, hasLength(1));
    expect(projection.forest.single.path, 'PneumaticPress');
    expect(projection.forest.single.children.single.path,
        'PneumaticPress.PressRam');
    expect(projection.browsePathByModulePath['PneumaticPress'],
        'PLC1/MAIN/PneumaticPress');
    expect(projection.discardedAliases, hasLength(2));
  });

  test('maps TF6100 named containers for fieldbus arrays', () {
    final projection = OpcUaSnapshotMapper().map({
      'protocol': 'fraktal.opcua.snapshot.v1',
      'values': {
        'PLC1/GVL_PressFieldbus/Topology/NodeCount': 2,
        'PLC1/GVL_PressFieldbus/Topology/MappingValid': true,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/ParentIdx': 0,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Name': 'EtherCAT',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/TypeId': 'MASTER',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Address': '0',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/State': 4,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/LinkOk': true,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/ChannelCount': 1,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Channels/Channels[1]/Name':
            '_101B202A',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Channels/Channels[1]/Address':
            'EL1809 Ch5',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Channels/Channels[1]/Path':
            'PneumaticPress.IO._101B202A',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Channels/Channels[1]/ModulePath':
            'PneumaticPress.PressRam',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Channels/Channels[1]/Dir':
            0,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[1]/Channels/Channels[1]/Kind':
            0,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[2]/ParentIdx': 1,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[2]/Name': 'EL1809',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[2]/TypeId': 'EL1809',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[2]/Address': '1001',
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[2]/State': 4,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[2]/LinkOk': true,
        'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[2]/ChannelCount': 0,
      },
    });

    expect(projection.fieldbus, hasLength(1));
    final master = projection.fieldbus.single;
    expect(master.name, 'EtherCAT');
    expect(master.channels.single.name, '_101B202A');
    expect(master.channels.single.address, 'EL1809 Ch5');
    expect(master.children.single.name, 'EL1809');
  });
}
