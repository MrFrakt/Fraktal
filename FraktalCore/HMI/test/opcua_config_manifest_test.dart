import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_config_manifest.dart';
import 'package:fraktal_hmi/domain/types.dart';

void main() {
  const bases = {
    'PneumaticPress': 'PLC1/MAIN/PneumaticPress',
    'PneumaticPress.PressCylinder': 'PLC1/MAIN/PneumaticPress/PressCylinder',
  };
  const topologyBase = 'PLC1/GVL_PressFieldbus/Topology';

  test('module entries rebuild the exact browse-path keys, typed by item', () {
    final values = synthesizeManifestValues(
      const [
        ConfigManifestEntry('PneumaticPress', 'CatalogCount', '2'),
        ConfigManifestEntry('PneumaticPress', 'Catalog/Catalog[1]/Value', '11'),
        ConfigManifestEntry(
            'PneumaticPress', 'Catalog/Catalog[1]/Label', 'std.cmd.open'),
        ConfigManifestEntry('PneumaticPress',
            'AvailableModels/AvailableModels[1]/ModelCode', 'ALUMINUM'),
        ConfigManifestEntry(
            'PneumaticPress', 'ModePolicy/ModePolicy[0]/Shield', '2'),
        ConfigManifestEntry('PneumaticPress', 'AlarmLog/MetaCount', '1'),
        ConfigManifestEntry(
            'PneumaticPress', 'AlarmLog/Meta/Meta[1]/ReasonCode', '2003'),
        ConfigManifestEntry(
            'PneumaticPress', 'AlarmLog/Meta/Meta[1]/Shelvable', 'TRUE'),
        ConfigManifestEntry('PneumaticPress.PressCylinder',
            'Catalog/Catalog[1]/Label', 'std.cmd.extend'),
      ],
      browseBaseByModulePath: bases,
      topologyBase: topologyBase,
    );

    expect(values['PLC1/MAIN/PneumaticPress/CatalogCount'], 2);
    expect(values['PLC1/MAIN/PneumaticPress/Catalog/Catalog[1]/Value'], 11);
    expect(values['PLC1/MAIN/PneumaticPress/Catalog/Catalog[1]/Label'],
        'std.cmd.open');
    expect(
        values[
            'PLC1/MAIN/PneumaticPress/AvailableModels/AvailableModels[1]/ModelCode'],
        'ALUMINUM');
    expect(
        values['PLC1/MAIN/PneumaticPress/ModePolicy/ModePolicy[0]/Shield'], 2);
    expect(values['PLC1/MAIN/PneumaticPress/AlarmLog/MetaCount'], 1);
    expect(values['PLC1/MAIN/PneumaticPress/AlarmLog/Meta/Meta[1]/ReasonCode'],
        2003);
    expect(values['PLC1/MAIN/PneumaticPress/AlarmLog/Meta/Meta[1]/Shelvable'],
        isTrue);
    expect(
        values[
            'PLC1/MAIN/PneumaticPress/PressCylinder/Catalog/Catalog[1]/Label'],
        'std.cmd.extend');
  });

  test('fieldbus scope resolves against the topology base', () {
    final values = synthesizeManifestValues(
      const [
        ConfigManifestEntry(
            kManifestFieldbusScope, 'Nodes/Nodes[3]/Name', '=000+S-K010B1'),
        ConfigManifestEntry(
            kManifestFieldbusScope, 'Nodes/Nodes[3]/ParentIdx', '1'),
        ConfigManifestEntry(kManifestFieldbusScope,
            'Nodes/Nodes[3]/Channels/Channels[5]/Kind', '0'),
        ConfigManifestEntry(kManifestFieldbusScope,
            'Nodes/Nodes[3]/Channels/Channels[5]/Name', '-B12.5'),
        ConfigManifestEntry(kManifestFieldbusScope,
            'Nodes/Nodes[3]/Channels/Channels[5]/Forceable', 'TRUE'),
      ],
      browseBaseByModulePath: bases,
      topologyBase: topologyBase,
    );

    expect(values['$topologyBase/Nodes/Nodes[3]/Name'], '=000+S-K010B1');
    expect(values['$topologyBase/Nodes/Nodes[3]/ParentIdx'], 1);
    expect(values['$topologyBase/Nodes/Nodes[3]/Channels/Channels[5]/Kind'], 0);
    expect(values['$topologyBase/Nodes/Nodes[3]/Channels/Channels[5]/Name'],
        '-B12.5');
    expect(
        values['$topologyBase/Nodes/Nodes[3]/Channels/Channels[5]/Forceable'],
        isTrue);
  });

  test('unresolvable scopes and empty items are skipped, not mis-keyed', () {
    final values = synthesizeManifestValues(
      const [
        ConfigManifestEntry('UnknownStation', 'CatalogCount', '1'),
        ConfigManifestEntry(kManifestFieldbusScope, 'Nodes/Nodes[1]/Name', 'X'),
        ConfigManifestEntry('PneumaticPress', '', 'orphan'),
      ],
      browseBaseByModulePath: bases,
      topologyBase: null, // no topology discovered yet
    );
    expect(values, isEmpty);
  });

  test('malformed integer text degrades to 0, never a crash or a string', () {
    final values = synthesizeManifestValues(
      const [ConfigManifestEntry('PneumaticPress', 'CatalogCount', 'garbage')],
      browseBaseByModulePath: bases,
      topologyBase: null,
    );
    expect(values['PLC1/MAIN/PneumaticPress/CatalogCount'], 0);
  });

  test('typed write capabilities produce the only editable fields', () {
    final fields = configFieldsFromManifest(const [
      ConfigManifestEntry(
        'PneumaticPress',
        'ModePolicy/ModePolicy[0]/Shield',
        '1',
        writeKey: 'unit.modePolicy.0.shield',
        writeRevision: 1,
        configKind: 1,
        valueType: 0,
        writable: true,
        requiresReady: true,
        hasMinimum: true,
        hasMaximum: true,
        minimum: 0,
        maximum: 2,
        enumDomain: '0|1|2',
      ),
      ConfigManifestEntry('PneumaticPress', 'CatalogCount', '2'),
    ]);

    final field = fields['PneumaticPress']!.single;
    expect(field.kind, CfgKind.stationCfg);
    expect(field.type, CfgType.number);
    expect(field.writeKey, 'unit.modePolicy.0.shield');
    expect(field.writeRevision, 1);
    expect(field.requiresReady, isTrue);
    expect(field.accepts('2'), isTrue);
    expect(field.accepts('3'), isFalse);
  });

  test('missing authority and duplicate keys fail closed', () {
    final fields = configFieldsFromManifest(const [
      ConfigManifestEntry('PneumaticPress', 'ParCfg/Speed', '10',
          writable: true),
      ConfigManifestEntry('PneumaticPress', 'StationCfg/Port', '4840',
          writeKey: 'station.port',
          writeRevision: 1,
          configKind: 1,
          valueType: 0,
          writable: true),
      ConfigManifestEntry('PneumaticPress', 'StationCfg/OtherPort', '4841',
          writeKey: 'station.port',
          writeRevision: 1,
          configKind: 1,
          valueType: 0,
          writable: true),
    ]);

    expect(fields, isEmpty);
  });

  group('§3.8d data classes and per-value levels', () {
    const operatorSession = AccessSession(level: AccessLevel.operator);
    const engineerSession = AccessSession(level: AccessLevel.engineer);

    test('the published class and effective levels decide, not DATA_WRITE', () {
      final fields = configFieldsFromManifest(const [
        ConfigManifestEntry('Press', 'StationCfg/Preset', '5',
            writeKey: 'press.preset',
            writeRevision: 1,
            configKind: 1,
            valueType: 0,
            writable: true,
            classId: 'public',
            readLevel: 0,
            writeLevel: 1),
        ConfigManifestEntry('Press', 'StationCfg/Calibration', '1.5',
            writeKey: 'press.calibration',
            writeRevision: 1,
            configKind: 1,
            valueType: 0,
            writable: true,
            classId: 'public',
            readLevel: 0,
            writeLevel: 3),
      ]);
      final preset =
          fields['Press']!.firstWhere((f) => f.writeKey == 'press.preset');
      final calibration =
          fields['Press']!.firstWhere((f) => f.writeKey == 'press.calibration');
      expect(preset.classId, 'public');
      // The station-wide DATA_WRITE gate of this session is irrelevant here.
      expect(preset.canWriteIn(operatorSession), isTrue);
      expect(calibration.canWriteIn(operatorSession), isFalse,
          reason: 'a raised value refuses its class level');
      expect(calibration.canWriteIn(engineerSession), isTrue);
    });

    test('an older PLC without levels falls back to the gates', () {
      final field = configFieldsFromManifest(const [
        ConfigManifestEntry('Press', 'StationCfg/Port', '4840',
            writeKey: 'station.port',
            writeRevision: 1,
            configKind: 1,
            valueType: 0,
            writable: true),
      ])['Press']!.single;
      expect(field.writeLevel, isNull,
          reason: 'absent must be unknown, never NONE');
      const locked = AccessSession(
          level: AccessLevel.operator,
          required: [
            AccessLevel.none, AccessLevel.engineer, AccessLevel.none,
            AccessLevel.none, AccessLevel.none, AccessLevel.none,
            AccessLevel.none, AccessLevel.none, AccessLevel.none,
            AccessLevel.none, AccessLevel.none, AccessLevel.none,
          ]);
      expect(field.canWriteIn(locked), isFalse);
    });

    test('an unreadable value is listed without its value', () {
      final field = configFieldsFromManifest(const [
        ConfigManifestEntry('Press', 'StationCfg/Secret', '',
            writeKey: 'press.secret',
            writeRevision: 1,
            configKind: 1,
            valueType: 0,
            writable: true,
            readLevel: 4,
            writeLevel: 4,
            readable: false),
      ])['Press']!.single;
      expect(field.readable, isFalse);
      expect(field.value, isEmpty);
      expect(field.canReadIn(engineerSession), isFalse);
    });

    test('a mirrored line value is kept, read-only', () {
      final field = configFieldsFromManifest(const [
        ConfigManifestEntry('Press.Line', 'Calendar/StartMin[1]', '360',
            writeKey: 'shift.1.startMin',
            writeRevision: 1,
            configKind: 2,
            valueType: 0,
            writable: false,
            readLevel: 0,
            writeLevel: 3),
      ])['Press.Line']!.single;
      expect(field.kind, CfgKind.lineCfg);
      expect(field.value, '360');
      expect(field.hasWriteCapability, isFalse);
    });
  });

  group('§3.13 flow-chart rows arrive as NUMBERS, not strings', () {
    // Regression: the whole sequence flow chart rendered "N0" on every row with
    // an empty drill-down. The static half of each row is served through the
    // manifest, and the typing rule was a hand-maintained list of leaf NAMES
    // that never included StepNo — so "100" arrived as a String, the mapper's
    // _integer() fell back to 0, and every step became N0. The PLC now declares
    // NUMBER on the entries M_AppendNumber writes, and the declared type wins.
    const base = 'PLC1/MAIN/PneumaticPress';
    const bases = {'PneumaticPress': base};

    test('a declared NUMBER is parsed even for an unlisted leaf name', () {
      final values = synthesizeManifestValues(
        const [
          // valueType 0 = E_ConfigValueType.NUMBER
          ConfigManifestEntry('PneumaticPress', 'Anything/Unlisted', '4711',
              valueType: 0),
        ],
        browseBaseByModulePath: bases,
        topologyBase: null,
      );
      expect(values['$base/Anything/Unlisted'], 4711,
          reason: 'the sender declared the type; the receiver must not guess');
    });

    test('every sequence row leaf the PLC sends as a number is numeric', () {
      final values = synthesizeManifestValues(
        const [
          ConfigManifestEntry(
              'PneumaticPress', 'SequenceSteps/SequenceSteps[1]/StepNo', '100',
              valueType: 0),
          ConfigManifestEntry(
              'PneumaticPress', 'SequenceSteps/SequenceSteps[1]/Branch', '0',
              valueType: 0),
          ConfigManifestEntry('PneumaticPress',
              'SequenceSteps/SequenceSteps[1]/TimeClass', '3',
              valueType: 0),
          ConfigManifestEntry('PneumaticPress',
              'SequenceSteps/SequenceSteps[1]/ExpectedTime', '2500',
              valueType: 0),
          ConfigManifestEntry('PneumaticPress',
              'SequenceSteps/SequenceSteps[1]/StepName',
              'project.step.pressAwaitTwoHand'),
        ],
        browseBaseByModulePath: bases,
        topologyBase: null,
      );
      const row = '$base/SequenceSteps/SequenceSteps[1]';
      expect(values['$row/StepNo'], 100, reason: 'this is the N0 defect');
      expect(values['$row/Branch'], 0);
      expect(values['$row/TimeClass'], 3);
      expect(values['$row/ExpectedTime'], 2500);
      expect(values['$row/StepName'], 'project.step.pressAwaitTwoHand',
          reason: 'text must stay text');
    });

    test('an older PLC that declares nothing still works by leaf name', () {
      // Every entry TEXT (valueType 1) — a build predating the NUMBER stamp.
      final values = synthesizeManifestValues(
        const [
          ConfigManifestEntry(
              'PneumaticPress', 'SequenceSteps/SequenceSteps[2]/StepNo', '200'),
        ],
        browseBaseByModulePath: bases,
        topologyBase: null,
      );
      expect(values['$base/SequenceSteps/SequenceSteps[2]/StepNo'], 200,
          reason: 'the name-based fallback must still cover an old PLC');
    });

    test('a declared BOOLEAN is parsed without being in the name list', () {
      final values = synthesizeManifestValues(
        const [
          // valueType 2 = BOOLEAN
          ConfigManifestEntry('PneumaticPress', 'Some/Flag', 'TRUE',
              valueType: 2),
        ],
        browseBaseByModulePath: bases,
        topologyBase: null,
      );
      expect(values['$base/Some/Flag'], isTrue);
    });
  });
}
