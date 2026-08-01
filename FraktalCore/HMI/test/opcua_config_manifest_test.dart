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
}
