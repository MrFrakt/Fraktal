import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_config_manifest.dart';

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
        ConfigManifestEntry(
            'PneumaticPress', 'Catalog/Catalog[1]/Value', '11'),
        ConfigManifestEntry(
            'PneumaticPress', 'Catalog/Catalog[1]/Label', 'std.cmd.open'),
        ConfigManifestEntry('PneumaticPress',
            'AvailableModels/AvailableModels[1]/ModelCode', 'ALUMINUM'),
        ConfigManifestEntry(
            'PneumaticPress', 'ModePolicy/ModePolicy[0]/Shield', '2'),
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
      ],
      browseBaseByModulePath: bases,
      topologyBase: topologyBase,
    );

    expect(values['$topologyBase/Nodes/Nodes[3]/Name'], '=000+S-K010B1');
    expect(values['$topologyBase/Nodes/Nodes[3]/ParentIdx'], 1);
    expect(
        values['$topologyBase/Nodes/Nodes[3]/Channels/Channels[5]/Kind'], 0);
    expect(values['$topologyBase/Nodes/Nodes[3]/Channels/Channels[5]/Name'],
        '-B12.5');
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
}
