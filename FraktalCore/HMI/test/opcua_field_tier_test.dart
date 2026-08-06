import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/opcua_field_tier.dart';

void main() {
  group('CONFIG — manifest-served, DA=0', () {
    const paths = [
      'PLC1/MAIN/PneumaticPress/Nameplate/SerialNumber',
      'PLC1/MAIN/PneumaticPress/Catalog/Catalog[2]/Label',
      'PLC1/MAIN/PneumaticPress/CatalogCount',
      'PLC1/MAIN/PneumaticPress/AvailableModels/AvailableModels[1]/ModelCode',
      'PLC1/MAIN/PneumaticPress/ModePolicy/ModePolicy[0]/Style',
      'PLC1/MAIN/PneumaticPress/StallTime',
      'PLC1/MAIN/PneumaticPress/AlarmLog/Meta/Meta[3]/OperatorAction',
      'PLC1/MAIN/PneumaticPress/ParCfg/DwellMs',
      // Note: fieldbus static identity (Name/Address/ParentIdx under Topology)
      // is OPC.UA.DA=0 and manifest-served, so those paths are never discovered
      // and the classifier never sees them — they are covered by the manifest
      // synthesizer tests, not here.
    ];
    for (final path in paths) {
      test(path, () => expect(OpcUaFieldTier.classify(path), FieldTier.config));
    }
  });

  group('LIVE — every snapshot (always-visible)', () {
    const paths = [
      // Status is discovery identity + live state: MUST be cyclic, or the mapper
      // (which keys modules on Status/Name + Status/ModuleType) drops the module.
      'PLC1/MAIN/PneumaticPress/Status/Name',
      'PLC1/MAIN/PneumaticPress/Status/ModuleType',
      'PLC1/MAIN/PneumaticPress/Status/State',
      // The Unit's mode/run-style capability feeds the mode dropdown — cyclic,
      // never obscured; excluding it left the dropdown showing only the current mode.
      'PLC1/MAIN/PneumaticPress/SupportedModesPublished/SupportedModesPublished[0]',
      'PLC1/MAIN/PneumaticPress/SupportedRunStylesPublished/SupportedRunStylesPublished[1]',
      'PLC1/MAIN/PneumaticPress/Busy',
      'PLC1/MAIN/PneumaticPress/GoodCount',
      'PLC1/MAIN/PneumaticPress/MachineState',
      'PLC1/MAIN/PneumaticPress/ModeActivePublished',
      'PLC1/MAIN/PneumaticPress/Status/Diagnostic/Description',
      'PLC1/MAIN/PneumaticPress/CurrentStep/StepName',
      'PLC1/MAIN/PneumaticPress/Oee/Availability',
      'PLC1/MAIN/PneumaticPress/Model/ModelCode',
      // Active alarms feed the global banner — stays live
      'PLC1/MAIN/PneumaticPress/AlarmLog/Active/Active[1]/State',
      'PLC1/MAIN/PneumaticPress/AlarmLog/Blocking',
      'PLC1/MAIN/PneumaticPress/Access/CurrentLevel',
    ];
    for (final path in paths) {
      test(path, () => expect(OpcUaFieldTier.classify(path), FieldTier.live));
    }
  });

  group('SLOW — heartbeat (per-module safety/power facets)', () {
    const paths = [
      'PLC1/MAIN/PneumaticPress/Safety/EStopActive',
      'PLC1/MAIN/PneumaticPress/ControlPower/PowerOn',
      'PLC1/MAIN/PneumaticPress/PressRam/Safety/GuardClosed',
      'PLC1/MAIN/PneumaticPress/PressRam/ControlPower/Groups/Groups[1]/On',
      // safety/power nested under the domain status are demoted too
      'PLC1/MAIN/PneumaticPress/Domain/Safety/EStopActive',
      'PLC1/MAIN/PneumaticPress/Domain/ControlPower/PowerOn',
    ];
    for (final path in paths) {
      test(path, () => expect(OpcUaFieldTier.classify(path), FieldTier.slow));
    }
  });

  group('ON-DEMAND — view-gated drill-down (module rings/trends + fieldbus)',
      () {
    const roots = ['PLC1/MAIN/PneumaticPress'];
    // Module drill-down data scopes to its owning root Unit.
    const moduleScoped = [
      'PLC1/MAIN/PneumaticPress/AlarmLog/Ring/Ring[5]/Description',
      'PLC1/MAIN/PneumaticPress/HostEvents/Ring/Ring[5]/Kind',
      'PLC1/MAIN/PneumaticPress/Profiler/History/History[2]/Total',
      'PLC1/MAIN/PneumaticPress/Profiler/StepStats/StepStats[1]/Avg',
      'PLC1/MAIN/PneumaticPress/OeeTrend/OeeTrend[10]/Oee',
      'PLC1/MAIN/PneumaticPress/Part/Result/Records/Records[1]/Value',
      'PLC1/MAIN/PneumaticPress/Profiler/History/History[4]/WorkTime',
    ];
    for (final path in moduleScoped) {
      test(path, () {
        expect(OpcUaFieldTier.classify(path), FieldTier.onDemand);
        expect(OpcUaFieldTier.onDemandScopeOf(path, roots),
            'PLC1/MAIN/PneumaticPress');
      });
    }
    // Fieldbus drill-down shares the reserved fieldbus scope. The channel VALUE
    // is deliberately NOT in this list: it is promoted to live (see below), so a
    // sensor that never comes on is visible without opening the bus page.
    const fieldbus = [
      'PLC1/GVL_PressFieldbus/Topology/NodeCount',
      'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[3]/State',
      'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[3]/Channels/Channels[5]/Forced',
      'PLC1/GVL_PressFieldbus/Topology/Nodes/Nodes[3]/Channels/Channels[5]/Address',
    ];
    for (final path in fieldbus) {
      test(path, () {
        expect(OpcUaFieldTier.classify(path), FieldTier.onDemand);
        expect(OpcUaFieldTier.onDemandScopeOf(path, roots),
            OpcUaFieldTier.fieldbusScope);
      });
    }
  });

  test('unknown leaf defaults to LIVE (never wrongly stale)', () {
    expect(
        OpcUaFieldTier.classify('PLC1/MAIN/X/SomeFutureField'), FieldTier.live);
    expect(
        OpcUaFieldTier.onDemandScopeOf('PLC1/MAIN/X/SomeFutureField', const []),
        isNull);
  });

  test('array index forms are stripped (bracket, double-segment)', () {
    expect(
        OpcUaFieldTier.classify('A/Ring[9]/Description'), FieldTier.onDemand);
    expect(OpcUaFieldTier.classify('A/Ring/Ring[9]/Description'),
        FieldTier.onDemand);
    expect(OpcUaFieldTier.classify('A/Meta/Meta[9]/OperatorAction'),
        FieldTier.config);
  });
}
