library;

import '../domain/fieldbus.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/reason_catalog.g.dart';

class OpcUaProjection {
  final List<ModuleNode> forest;
  final List<BusNode> fieldbus;
  final Map<String, String> browsePathByModulePath;
  final List<String> discardedAliases;

  const OpcUaProjection({
    required this.forest,
    required this.fieldbus,
    required this.browsePathByModulePath,
    this.discardedAliases = const [],
  });
}

/// Maps a transport-neutral flat OPC UA browse snapshot into the domain model.
/// The mapper keys off the normative Status member, never a concrete FB type.
class OpcUaSnapshotMapper {
  OpcUaProjection map(Map<String, Object?> document,
      {Map<String, List<CfgField>> configByModulePath = const {}}) {
    final rawValues = document['values'];
    if (rawValues is! Map) {
      throw const FormatException('OPC UA snapshot has no values object.');
    }
    final values = <String, Object?>{
      for (final entry in rawValues.entries) '${entry.key}': entry.value,
    };
    final rawDataValues = document['dataValues'];
    final dataValues = rawDataValues is Map
        ? <String, Object?>{
            for (final entry in rawDataValues.entries)
              '${entry.key}': entry.value,
          }
        : const <String, Object?>{};
    final candidatesByIdentity = <String, _ModuleCandidate>{};
    final discardedAliases = <String>[];
    for (final entry in values.entries) {
      if (!entry.key.endsWith('/Status/Name') || entry.value is! String) {
        continue;
      }
      final base =
          entry.key.substring(0, entry.key.length - '/Status/Name'.length);
      final type = _integer(values['$base/Status/ModuleType']);
      if (type <= ModuleType.none.index || type >= ModuleType.values.length) {
        continue;
      }
      final identity = entry.value as String;
      final browseName = base.substring(base.lastIndexOf('/') + 1);
      final localName = identity.substring(identity.lastIndexOf('.') + 1);
      // TF6100 can expose REFERENCE TO aliases whose Status still describes
      // the referenced module. Nested Status.Name is the full Fraktal path, so
      // compare its final segment with the local OPC UA browse name.
      if (browseName != localName) {
        discardedAliases.add('$base -> $identity');
        continue;
      }
      final candidate =
          _ModuleCandidate(base, identity, localName, ModuleType.values[type]);
      final existing = candidatesByIdentity[identity];
      if (existing == null) {
        candidatesByIdentity[identity] = candidate;
      } else {
        final preferred = _preferCanonical(existing, candidate);
        final alias = identical(preferred, existing) ? candidate : existing;
        candidatesByIdentity[identity] = preferred;
        discardedAliases.add('${alias.browsePath} -> $identity');
      }
    }

    for (final candidate in candidatesByIdentity.values) {
      final separator = candidate.identity.lastIndexOf('.');
      if (separator < 0) continue;
      final parentIdentity = candidate.identity.substring(0, separator);
      candidate.parent = candidatesByIdentity[parentIdentity];
      candidate.parent?.children.add(candidate);
    }

    // Loop-invariant: the candidate path set does not depend on the module being
    // projected, so it is built ONCE per snapshot instead of once per module.
    // Rebuilding it inside project() made mapping O(modules x symbols) with a
    // fresh ~15k-entry Set allocated per module — the dominant cost of a refresh
    // (~1.1s on a 15k-symbol tree), which blocked the UI isolate and with it
    // every command's ack poll. Still a Set: it must stay deduplicated across
    // values/dataValues so a path present in both is projected once.
    final candidatePaths = <String>{...values.keys, ...dataValues.keys};
    // O(1) "has children" index for the indexed-array probes (see
    // _buildParentPaths): built once per snapshot, reused by every module.
    final parentPaths = _buildParentPaths(values.keys);

    final browseByModule = <String, String>{};
    ModuleNode project(_ModuleCandidate candidate) {
      final path = candidate.identity;
      browseByModule[path] = candidate.browsePath;
      final base = candidate.browsePath;
      final state = _enumAt(ExecState.values,
          _integer(values['$base/Status/State']), ExecState.ready);
      final isUnit = candidate.type == ModuleType.unit;
      final modeValue =
          _integer(values['$base/ModeActivePublished'], fallback: -1);
      final runStyleValue = _integer(values['$base/RunStyle'], fallback: 0);
      final currentMode = modeValue >= 0 && modeValue < UnitMode.values.length
          ? UnitMode.values[modeValue]
          : null;
      final accessLevel = _enumAt(AccessLevel.values,
          _integer(values['$base/Access/CurrentLevel']), AccessLevel.none);
      final required = <AccessLevel>[];
      for (var i = 0; i < GatedAction.values.length; i++) {
        final raw = _arrayElement(values, '$base/Access/Policy/Required', i,
            parentPaths: parentPaths);
        required
            .add(_enumAt(AccessLevel.values, _integer(raw), AccessLevel.admin));
      }
      final commandCount = _integer(values['$base/CatalogCount']);
      final commands = <CommandInfo>[];
      for (var i = 1; i <= commandCount; i++) {
        final prefix = _indexedPrefix(values, '$base/Catalog', i,
            parentPaths: parentPaths);
        if (prefix == null) continue;
        commands.add(CommandInfo(
          _integer(values['$prefix/Value']),
          _string(values['$prefix/Label']),
        ));
      }
      final children = candidate.children.map(project).toList()
        ..sort((a, b) => a.name.compareTo(b.name));
      final childBrowsePrefixes = [
        for (final child in candidate.children) '${child.browsePath}/',
      ];
      final publishedValues = <String, Object?>{};
      final publishedTags = <String, PublishedTagValue>{};
      final browsePrefix = '$base/';
      for (final fullPath in candidatePaths) {
        if (!fullPath.startsWith(browsePrefix)) continue;
        if (childBrowsePrefixes
            .any((childPrefix) => fullPath.startsWith(childPrefix))) {
          continue;
        }
        final tag = _publishedTag(dataValues[fullPath], values[fullPath]);
        final value = tag.value;
        if (value != null &&
            value is! bool &&
            value is! num &&
            value is! String) {
          continue;
        }
        final relative = fullPath.substring(browsePrefix.length);
        if (!_customBindable(relative)) continue;
        if (tag.usable && value != null) publishedValues[relative] = value;
        publishedTags[relative] = tag;
      }
      final supportedModes = isUnit
          ? [
              for (var i = 0; i < UnitMode.values.length; i++)
                if (_arrayElement(values, '$base/SupportedModesPublished', i,
                        parentPaths: parentPaths) ==
                    true)
                  UnitMode.values[i],
            ]
          : const <UnitMode>[];
      final supportedRunStyles = isUnit
          ? [
              for (var i = 0; i < RunStyle.values.length; i++)
                if (_arrayElement(
                        values, '$base/SupportedRunStylesPublished', i,
                        parentPaths: parentPaths) ==
                    true)
                  RunStyle.values[i],
            ]
          : const <RunStyle>[];
      final modePolicy = <UnitMode, ModePolicy>{};
      if (isUnit) {
        for (var i = 0; i < UnitMode.values.length; i++) {
          final prefix = _indexedPrefix(values, '$base/ModePolicy', i + 1,
              parentPaths: parentPaths);
          if (prefix == null) continue;
          modePolicy[UnitMode.values[i]] = ModePolicy(
            _enumAt(ModeSwitchShield.values, _integer(values['$prefix/Shield']),
                ModeSwitchShield.confirm),
            _enumAt(ModeSwitchStyle.values, _integer(values['$prefix/Style']),
                ModeSwitchStyle.graceful),
          );
        }
      }

      final availableModels = <String>[];
      final availableModelCount = _integer(values['$base/AvailableModelCount']);
      for (var i = 1; i <= availableModelCount; i++) {
        final prefix = _indexedPrefix(values, '$base/AvailableModels', i,
            parentPaths: parentPaths);
        if (prefix == null) continue;
        final code = _string(values['$prefix/ModelCode']);
        if (code.isNotEmpty) availableModels.add(code);
      }

      final stepNo = _integer(values['$base/CurrentStep/StepNo']);
      StepInfo? step;
      if (isUnit && stepNo != 0) {
        final conds = <CondInfo>[];
        for (var i = 1; i <= 8; i++) {
          final prefix = _indexedPrefix(values, '$base/CurrentStep/Conds', i,
              parentPaths: parentPaths);
          if (prefix == null) continue;
          final label = _string(values['$prefix/Label']);
          if (label.isNotEmpty) {
            conds.add(CondInfo(label, _boolean(values['$prefix/Ok'])));
          }
        }
        step = StepInfo(
          stepNo: stepNo,
          stepName: _string(values['$base/CurrentStep/StepName']),
          awaitingLabel: _string(values['$base/CurrentStep/AwaitingLabel']),
          timeClass: _enumAt(TimeClass.values,
              _integer(values['$base/CurrentStep/TimeClass'] ??
                  values['$base/CurrentStep/Class']), TimeClass.work),
          expected: _duration(values['$base/CurrentStep/ExpectedTime']),
          conds: conds,
          starved: _boolean(values['$base/Starved']),
          blocked: _boolean(values['$base/Blocked']),
        );
      }

      // §8.11.4 — cycle profile, trend ring, throughput markers (Units)
      CycleProfile? cycle;
      final cycleHistory = <CycleSummary>[];
      var lastCycleTime = Duration.zero;
      var minCycleTime = Duration.zero;
      MachineState? machineState;
      if (isUnit) {
        final profileBase = '$base/Profiler/LastCycle';
        final cycleNo = _integer(values['$profileBase/CycleNo']);
        if (cycleNo > 0) {
          final steps = <StepTiming>[];
          final nSteps = _integer(values['$profileBase/NSteps']);
          for (var i = 1; i <= nSteps; i++) {
            final prefix = _indexedPrefix(values, '$profileBase/Steps', i,
                parentPaths: parentPaths);
            if (prefix == null) continue;
            steps.add(StepTiming(
              _integer(values['$prefix/StepNo']),
              _string(values['$prefix/StepName']),
              _enumAt(
                  TimeClass.values,
                  _integer(values['$prefix/TimeClass'] ??
                      values['$prefix/Class']),
                  TimeClass.work),
              _duration(values['$prefix/Duration']),
              _duration(values['$prefix/Expected']),
            ));
          }
          cycle = CycleProfile(
            cycleNo: cycleNo,
            total: _duration(values['$profileBase/Total']),
            workTime: _duration(values['$profileBase/WorkTime']),
            waitTime: _duration(values['$profileBase/WaitTime']),
            steps: steps,
          );
        }
        lastCycleTime = _duration(values['$base/Profiler/LastCycleTime']);
        minCycleTime = _duration(values['$base/Profiler/MinCycleTime']);
        final head = _integer(values['$base/Profiler/HistoryHead']);
        if (head > 0) {
          // ring -> chronological list, oldest..newest, skipping empty slots
          const ringSize = 60; // PL_Fraktal.MAX_CYCLE_HISTORY
          for (var offset = 1; offset <= ringSize; offset++) {
            final index = ((head - 1 + offset) % ringSize) + 1;
            final prefix = _indexedPrefix(
                values, '$base/Profiler/History', index,
                parentPaths: parentPaths);
            if (prefix == null) continue;
            if (_integer(values['$prefix/CycleNo']) == 0) continue;
            cycleHistory.add(CycleSummary(
              cycleNo: _integer(values['$prefix/CycleNo']),
              total: _duration(values['$prefix/Total']),
              workTime: _duration(values['$prefix/WorkTime']),
              waitTime: _duration(values['$prefix/WaitTime']),
              byClass: [
                for (var c = 0; c < TimeClass.values.length; c++)
                  _duration(_arrayElement(values, '$prefix/ByClass', c,
                      parentPaths: parentPaths)),
              ],
            ));
          }
        }
        final machineStateValue =
            _integer(values['$base/MachineState'], fallback: -1);
        machineState = machineStateValue >= 0 &&
                machineStateValue < MachineState.values.length
            ? MachineState.values[machineStateValue]
            : null;
      }
      final stepStats = <StepStat>[];
      if (isUnit) {
        for (var i = 1; i <= 32; i++) {
          final prefix = _indexedPrefix(values, '$base/Profiler/StepStats', i,
              parentPaths: parentPaths);
          if (prefix == null) continue;
          if (_integer(values['$prefix/Count']) == 0) continue;
          stepStats.add(StepStat(
            _integer(values['$prefix/Id']),
            _string(values['$prefix/Label']),
            _enumAt(
                TimeClass.values,
                _integer(values['$prefix/TimeClass'] ??
                    values['$prefix/Class']),
                TimeClass.work),
            _duration(values['$prefix/Avg']),
            _duration(values['$prefix/Maximum']),
          ));
        }
      }
      // §8.11.4(a) — module command timing (any tier that ran commands)
      final commandTimings = <CommandTiming>[];
      for (var i = 1; i <= 8; i++) {
        final prefix = _indexedPrefix(values, '$base/Timing/Rows', i,
            parentPaths: parentPaths);
        if (prefix == null) continue;
        if (_integer(values['$prefix/Count']) == 0) continue;
        commandTimings.add(CommandTiming(
          _integer(values['$prefix/Id']),
          _string(values['$prefix/Label']),
          _integer(values['$prefix/Count']),
          _duration(values['$prefix/Last']),
          _duration(values['$prefix/Minimum']),
          _duration(values['$prefix/Maximum']),
          _duration(values['$prefix/Avg']),
        ));
      }

      DecisionRequest? decision;
      final prompt = _string(values['$base/Decision/Prompt']);
      if (isUnit && prompt.isNotEmpty) {
        final options = <String>[];
        for (var i = 0; i < 6; i++) {
          final option = _string(_arrayElement(
              values, '$base/Decision/Options', i,
              parentPaths: parentPaths));
          if (option.isNotEmpty) options.add(option);
        }
        final plcDefault = _integer(values['$base/Decision/Default']);
        decision = DecisionRequest(
          prompt: prompt,
          options: options,
          defaultOption: plcDefault > 0 ? plcDefault - 1 : -1,
        );
      }

      // §8.3/§8.9 — hydrate the real PLC alarm surface. Active slots are
      // sparse, so scan the fixed bound instead of trusting NActive as an index.
      final activeEvents = <AlarmEvent>[];
      final ringEvents = <AlarmEvent>[];
      final hostEvents = <HostEvent>[];
      final alarmMeta = <AlarmMeta>[
        // §8.9 generated standard catalog. The manifest carries the same data so
        // non-HMI clients can discover it; this local projection also gives a
        // deterministic fallback during an older/partial server rollout.
        for (final reasonCode in generatedReasonSymbolByCode.keys)
          AlarmMeta(
            reasonCode,
            reasonActionKey(reasonCode),
            reasonConsequenceKey(reasonCode),
            priority: _enumAt(
              Severity.values,
              generatedReasonPriorityByCode[reasonCode] ?? 0,
              Severity.low,
            ),
            category: _enumAt(
              AlarmCategory.values,
              generatedReasonCategoryByCode[reasonCode] ?? 0,
              AlarmCategory.process,
            ),
            shelvable: generatedReasonShelvableByCode[reasonCode] ?? false,
          ),
      ];
      if (isUnit) {
        for (var i = 1; i <= 16; i++) {
          final prefix = _indexedPrefix(values, '$base/AlarmLog/Active', i,
              parentPaths: parentPaths);
          if (prefix == null) continue;
          final event = _alarmEvent(values, prefix, active: true);
          if (event != null) activeEvents.add(event);
        }
        final ringHead = _integer(values['$base/AlarmLog/RingHead']);
        if (ringHead > 0) {
          for (var offset = 0; offset < 64; offset++) {
            final index = ((ringHead - 1 - offset + 64) % 64) + 1;
            final prefix = _indexedPrefix(values, '$base/AlarmLog/Ring', index,
                parentPaths: parentPaths);
            if (prefix == null) continue;
            final event = _alarmEvent(values, prefix, active: false);
            if (event != null) ringEvents.add(event);
          }
        }
        final hostRingHead = _integer(values['$base/HostEvents/RingHead']);
        final hostCapacity =
            _integer(values['$base/HostEvents/Capacity']).clamp(0, 1024);
        final hostCount =
            _integer(values['$base/HostEvents/Count']).clamp(0, hostCapacity);
        if (hostRingHead > 0 && hostCapacity > 0) {
          for (var offset = 0; offset < hostCount; offset++) {
            final index =
                ((hostRingHead - 1 - offset + hostCapacity) % hostCapacity) + 1;
            final prefix = _indexedPrefix(
              values,
              '$base/HostEvents/Ring',
              index,
              parentPaths: parentPaths,
            );
            if (prefix == null) continue;
            final sequence = _integer(values['$prefix/Sequence']);
            final kind = _enumAt(
              HostEventKind.values,
              _integer(values['$prefix/Kind']),
              HostEventKind.none,
            );
            if (sequence == 0 || kind == HostEventKind.none) continue;
            hostEvents.add(HostEvent(
              sequence: sequence,
              kind: kind,
              stationPath: _string(values['$prefix/StationPath']),
              partUid: _string(values['$prefix/PartUid']),
              subject: _string(values['$prefix/Subject']),
              value: _string(values['$prefix/Value']),
              stamp: _nonPlaceholderDateTime(values['$prefix/Stamp']),
              timeSynchronized: _boolean(values['$prefix/TimeSynchronized']),
              verdict: _enumAt(
                Verdict.values,
                _integer(values['$prefix/Verdict']),
                Verdict.none,
              ),
              reasonCode: _integer(values['$prefix/ReasonCode']),
            ));
          }
        }
        final metaCount = _integer(values['$base/AlarmLog/MetaCount']);
        for (var i = 1; i <= metaCount; i++) {
          final prefix = _indexedPrefix(values, '$base/AlarmLog/Meta', i,
              parentPaths: parentPaths);
          if (prefix == null) continue;
          final reasonCode = _integer(values['$prefix/ReasonCode']);
          if (reasonCode == 0) continue;
          alarmMeta.removeWhere((meta) => meta.reasonCode == reasonCode);
          alarmMeta.add(AlarmMeta(
            reasonCode,
            _string(values['$prefix/OperatorAction']),
            _string(values['$prefix/Consequence']),
            priority: _enumAt(
              Severity.values,
              _integer(
                values['$prefix/Priority'],
                fallback: generatedReasonPriorityByCode[reasonCode] ?? 0,
              ),
              _enumAt(
                Severity.values,
                generatedReasonPriorityByCode[reasonCode] ?? 0,
                Severity.low,
              ),
            ),
            category: _enumAt(
              AlarmCategory.values,
              _integer(
                values['$prefix/Category'],
                fallback: generatedReasonCategoryByCode[reasonCode] ?? 0,
              ),
              _enumAt(
                AlarmCategory.values,
                generatedReasonCategoryByCode[reasonCode] ?? 0,
                AlarmCategory.process,
              ),
            ),
            shelvable: _boolean(values['$prefix/Shelvable']),
          ));
        }
      }

      PartFacet? part;
      if (isUnit) {
        final records = <MeasRecord>[];
        for (var i = 1; i <= 32; i++) {
          final prefix = _indexedPrefix(values, '$base/Part/Result/Records', i,
              parentPaths: parentPaths);
          if (prefix == null) continue;
          final recordName = _string(values['$prefix/Name']);
          if (recordName.isEmpty) continue;
          records.add(MeasRecord(
            recordName,
            _number(values['$prefix/Value']),
            _number(values['$prefix/Minimum']),
            _number(values['$prefix/Maximum']),
            _number(values['$prefix/Target']),
            _string(values['$prefix/Unit']),
            _boolean(values['$prefix/InTol']),
          ));
        }
        final uid = _string(values['$base/Part/Uid']);
        final present = _boolean(values['$base/Part/Present']);
        if (present || uid.isNotEmpty || records.isNotEmpty) {
          final reasonCode = _integer(values['$base/Part/Result/ReasonCode']);
          part = PartFacet(
            uid: uid,
            present: present,
            verdict: _enumAt(Verdict.values,
                _integer(values['$base/Part/Result/Verdict']), Verdict.none),
            reason: reasonDescriptionKey(reasonCode, ''),
            records: records,
          );
        }
      }

      SafetyFacet? safety;
      if (_boolean(values['$base/Safety/Present'])) {
        final devices = <SafetyDeviceStatus>[];
        final count = _integer(values['$base/Safety/DeviceCount']);
        for (var i = 1; i <= count && i <= 16; i++) {
          final prefix = _indexedPrefix(values, '$base/Safety/Devices', i,
              parentPaths: parentPaths);
          if (prefix == null || !_boolean(values['$prefix/Present'])) continue;
          devices.add(SafetyDeviceStatus(
            name: _string(values['$prefix/Name']),
            description: _string(values['$prefix/Description']),
            kind: _enumAt(SafetyDeviceKind.values,
                _integer(values['$prefix/Kind']), SafetyDeviceKind.other),
            state: _enumAt(SafetyState.values,
                _integer(values['$prefix/State']), SafetyState.unavailable),
            ready: _boolean(values['$prefix/Ready']),
            demandActive: _boolean(values['$prefix/DemandActive']),
            safeStateActive: _boolean(values['$prefix/SafeStateActive']),
            resetRequired: _boolean(values['$prefix/ResetRequired']),
            faultActive: _boolean(values['$prefix/FaultActive']),
            mutingActive: _boolean(values['$prefix/MutingActive']),
            bridgeActive: _boolean(values['$prefix/BridgeActive']),
            fieldbusHealthy: _boolean(values['$prefix/FieldbusHealthy']),
            affectedPowerMask: _integer(values['$prefix/AffectedPowerMask']),
          ));
        }
        safety = SafetyFacet(
          allSafe: _boolean(values['$base/Safety/AllSafe']),
          demandActive: _boolean(values['$base/Safety/DemandActive']),
          resetRequired: _boolean(values['$base/Safety/ResetRequired']),
          faultActive: _boolean(values['$base/Safety/FaultActive']),
          mutingActive: _boolean(values['$base/Safety/MutingActive']),
          bridgeActive: _boolean(values['$base/Safety/BridgeActive']),
          stopRequested: _boolean(values['$base/Safety/StopRequested']),
          devices: devices,
        );
      }

      ControlPowerFacet? controlPower;
      if (_boolean(values['$base/ControlPower/Present'])) {
        final groups = <PowerGroupStatus>[];
        final count = _integer(values['$base/ControlPower/GroupCount']);
        for (var i = 1; i <= count && i <= 8; i++) {
          final prefix = _indexedPrefix(values, '$base/ControlPower/Groups', i,
              parentPaths: parentPaths);
          if (prefix == null || !_boolean(values['$prefix/Present'])) continue;
          groups.add(PowerGroupStatus(
            name: _string(values['$prefix/Name']),
            diagnostic: reasonDescriptionKey(
              _integer(values['$prefix/Diagnostic/ReasonCode']),
              _string(values['$prefix/Diagnostic/Description']),
            ),
            kind: _enumAt(PowerGroupKind.values,
                _integer(values['$prefix/Kind']), PowerGroupKind.control),
            state: _enumAt(PowerState.values, _integer(values['$prefix/State']),
                PowerState.off),
            requiredForControl: _boolean(values['$prefix/RequiredForControl']),
            requestedOn: _boolean(values['$prefix/RequestedOn']),
            powerOn: _boolean(values['$prefix/PowerOn']),
            safetyPermit: _boolean(values['$prefix/SafetyPermit']),
            fieldbusHealthy: _boolean(values['$prefix/FieldbusHealthy']),
            rearmRequired: _boolean(values['$prefix/RearmRequired']),
            fieldbusLossReaction: _enumAt(
                FieldbusLossReaction.values,
                _integer(values['$prefix/FieldbusLossReaction']),
                FieldbusLossReaction.controlOff),
          ));
        }
        controlPower = ControlPowerFacet(
          requestedOn: _boolean(values['$base/ControlPower/RequestedOn']),
          controlOn: _boolean(values['$base/ControlPower/ControlOn']),
          transitioning: _boolean(values['$base/ControlPower/Transitioning']),
          rearmRequired: _boolean(values['$base/ControlPower/RearmRequired']),
          diagnostic: reasonDescriptionKey(
            _integer(values['$base/ControlPower/Diagnostic/ReasonCode']),
            _string(values['$base/ControlPower/Diagnostic/Description']),
          ),
          groups: groups,
        );
      }

      Nameplate? nameplate;
      final manufacturer = _string(values['$base/Nameplate/ManufacturerName']);
      final designation = _string(values['$base/Nameplate/ProductDesignation']);
      final serial = _string(values['$base/Nameplate/SerialNumber']);
      if (manufacturer.isNotEmpty ||
          designation.isNotEmpty ||
          serial.isNotEmpty) {
        nameplate = Nameplate(
          productUri: _string(values['$base/Nameplate/ProductUri']),
          manufacturer: manufacturer,
          designation: designation,
          serial: serial,
          year: _string(values['$base/Nameplate/YearOfConstruction']),
          hwVersion: _string(values['$base/Nameplate/HardwareVersion']),
          fwVersion: _string(values['$base/Nameplate/FirmwareVersion']),
          swVersion: _string(values['$base/Nameplate/SoftwareVersion']),
          orderCode: _string(values['$base/Nameplate/OrderCode']),
          docUrl: _string(values['$base/Nameplate/DocumentationUrl']),
        );
      }

      OeeSnapshot? oee;
      if (isUnit && candidatePaths.contains('$base/Oee/OeeValid')) {
        final trend = <double>[];
        final head = _integer(values['$base/OeeTrendHead']);
        if (head > 0) {
          for (var offset = 1; offset <= 60; offset++) {
            final index = ((head - 1 + offset) % 60) + 1;
            final prefix = _indexedPrefix(values, '$base/OeeTrend', index,
                parentPaths: parentPaths);
            if (prefix == null || !_boolean(values['$prefix/OeeValid']))
              continue;
            trend.add(_number(values['$prefix/Oee']));
          }
        }
        oee = OeeSnapshot(
          availability: _number(values['$base/Oee/Availability']),
          performance: _number(values['$base/Oee/Performance']),
          quality: _number(values['$base/Oee/Quality']),
          oee: _number(values['$base/Oee/Oee']),
          availValid: _boolean(values['$base/Oee/AvailValid']),
          perfValid: _boolean(values['$base/Oee/PerfValid']),
          qualValid: _boolean(values['$base/Oee/QualValid']),
          oeeValid: _boolean(values['$base/Oee/OeeValid']),
          trend: trend,
        );
      }

      SystemHealthFacet? systemHealth;
      if (isUnit && _boolean(values['$base/SystemHealth/Present'])) {
        systemHealth = SystemHealthFacet(
          healthy: _boolean(values['$base/SystemHealth/Healthy']),
          taskAvailable: _boolean(values['$base/SystemHealth/TaskAvailable']),
          taskCycleUs: _integer(values['$base/SystemHealth/TaskCycleUs']),
          taskJitterUs: _integer(values['$base/SystemHealth/TaskJitterUs']),
          taskOverrun: _boolean(values['$base/SystemHealth/TaskOverrun']),
          controllerAvailable:
              _boolean(values['$base/SystemHealth/ControllerAvailable']),
          cpuLoadPct: _number(values['$base/SystemHealth/CpuLoadPct']),
          memoryAvailableMb:
              _integer(values['$base/SystemHealth/MemoryAvailableMb']),
          ipcAvailable: _boolean(values['$base/SystemHealth/IpcAvailable']),
          ipcTemperatureC:
              _number(values['$base/SystemHealth/IpcTemperatureC']),
          fanHealthy: _boolean(values['$base/SystemHealth/FanHealthy']),
          storageHealthPct:
              _number(values['$base/SystemHealth/StorageHealthPct']),
          fieldbusAvailable:
              _boolean(values['$base/SystemHealth/FieldbusAvailable']),
          fieldbusMasterHealthy:
              _boolean(values['$base/SystemHealth/FieldbusMasterHealthy']),
          lostFrameCount: _integer(values['$base/SystemHealth/LostFrameCount']),
          slaveErrorCount:
              _integer(values['$base/SystemHealth/SlaveErrorCount']),
          dcAvailable: _boolean(values['$base/SystemHealth/DcAvailable']),
          dcSynchronized: _boolean(values['$base/SystemHealth/DcSynchronized']),
          time: TimeQualityFacet(
            available:
                _boolean(values['$base/SystemHealth/TimeQuality/Available']),
            synchronized:
                _boolean(values['$base/SystemHealth/TimeQuality/Synchronized']),
            source: _string(values['$base/SystemHealth/TimeQuality/Source']),
            offsetUs:
                _integer(values['$base/SystemHealth/TimeQuality/OffsetUs']),
          ),
        );
      }
      SignalTowerFacet? signalTower;
      if (isUnit && candidatePaths.contains('$base/SignalTower/Red')) {
        signalTower = SignalTowerFacet(
          red: _boolean(values['$base/SignalTower/Red']),
          amber: _boolean(values['$base/SignalTower/Amber']),
          green: _boolean(values['$base/SignalTower/Green']),
          blue: _boolean(values['$base/SignalTower/Blue']),
          white: _boolean(values['$base/SignalTower/White']),
          horn: _boolean(values['$base/SignalTower/Horn']),
          testActive: _boolean(values['$base/SignalTower/TestActive']),
        );
      }

      return ModuleNode(
        path: path,
        name: candidate.name,
        displayNameKey: _string(values['$base/Status/DisplayNameKey']),
        descriptionKey: _string(values['$base/Status/DescriptionKey']),
        type: candidate.type,
        state: state,
        faultActive: _boolean(values['$base/Status/FaultActive']),
        message: reasonDescriptionKey(
          _integer(values['$base/Status/Diagnostic/ReasonCode']),
          _string(values['$base/Status/Diagnostic/Description']),
        ),
        diagnosticIoTag: _string(values['$base/Status/Diagnostic/IoTag']),
        diagnosticIoAddress:
            _string(values['$base/Status/Diagnostic/IoAddress']),
        diagnosticSince: _dateTime(values['$base/Status/Diagnostic/Since']),
        diagnosticTimeSynchronized: _boolean(
            values['$base/Status/Diagnostic/TimeSynchronized'],
            fallback: false),
        tileEnable: _boolean(values['$base/Status/TileEnable'], fallback: true),
        controlDomainId: _string(values['$base/Status/ControlDomainId']),
        children: children,
        modelCode: _string(values['$base/Model/ModelCode']),
        availableModels: availableModels,
        modeActive: isUnit ? currentMode : null,
        activeEvents: activeEvents,
        ringEvents: ringEvents,
        hostEvents: hostEvents,
        goodCount: _integer(values['$base/GoodCount']),
        nokCount: _integer(values['$base/NokCount']),
        reworkCount: _integer(values['$base/ReworkCount']),
        cycle: cycle,
        cycleHistory: cycleHistory,
        lastCycleTime: lastCycleTime,
        minCycleTime: minCycleTime,
        stepStats: stepStats,
        commandTimings: commandTimings,
        machineState: machineState,
        blocking: _boolean(values['$base/AlarmLog/Blocking']),
        access: isUnit
            ? AccessSession(
                level: accessLevel,
                user: _string(values['$base/Access/CurrentUser']),
                loginFailed: _boolean(values['$base/Access/LoginFailed']),
                required: required,
                sessionTimeout:
                    _duration(values['$base/Access/Policy/SessionTimeout']),
              )
            : null,
        commands: commands,
        decision: decision,
        part: part,
        safety: safety,
        controlPower: controlPower,
        systemHealth: systemHealth,
        signalTower: signalTower,
        config: configByModulePath[path] ?? const [],
        nameplate: nameplate,
        oee: oee,
        alarmMeta: alarmMeta,
        step: step,
        running: _boolean(values['$base/RunningPublished'],
            fallback: state == ExecState.busy),
        stopPending: _boolean(values['$base/StopPendingPublished']),
        runStyle: _enumAt(RunStyle.values, runStyleValue, RunStyle.continuous),
        supportedModes: supportedModes.isEmpty && currentMode != null
            ? [currentMode]
            : supportedModes,
        supportedRunStyles: supportedRunStyles.isEmpty
            ? const [RunStyle.continuous]
            : supportedRunStyles,
        modePolicy: modePolicy,
        publishedValues: publishedValues,
        publishedTags: publishedTags,
      );
    }

    final roots = candidatesByIdentity.values
        .where((candidate) =>
            candidate.parent == null &&
            !candidate.identity.contains('.') &&
            candidate.type == ModuleType.unit)
        .map((candidate) => project(candidate))
        .toList()
      ..sort((a, b) => a.name.compareTo(b.name));

    return OpcUaProjection(
      forest: roots,
      fieldbus: _mapFieldbus(values, parentPaths),
      browsePathByModulePath: browseByModule,
      discardedAliases: discardedAliases,
    );
  }

  List<BusNode> _mapFieldbus(
      Map<String, Object?> values, Set<String> parentPaths) {
    String? topology;
    for (final key in values.keys) {
      if (key.endsWith('/Topology/NodeCount')) {
        topology = key.substring(0, key.length - '/NodeCount'.length);
        break;
      }
    }
    if (topology == null) return const [];
    final count = _integer(values['$topology/NodeCount']);
    final nodes = <int, _BusCandidate>{};
    for (var index = 1; index <= count; index++) {
      final prefix = _indexedPrefix(values, '$topology/Nodes', index,
          parentPaths: parentPaths);
      if (prefix == null) continue;
      final channels = <IoChannel>[];
      final channelCount = _integer(values['$prefix/ChannelCount']);
      for (var channelIndex = 1; channelIndex <= channelCount; channelIndex++) {
        final channelPrefix = _indexedPrefix(
            values, '$prefix/Channels', channelIndex,
            parentPaths: parentPaths);
        if (channelPrefix == null) continue;
        channels.add(IoChannel(
          name: _string(values['$channelPrefix/Name']),
          descriptionKey: _string(values['$channelPrefix/DescriptionKey']),
          address: _string(values['$channelPrefix/Address']),
          path: _string(values['$channelPrefix/Path']),
          modulePath: _string(values['$channelPrefix/ModulePath']),
          dir: _enumAt(ChannelDir.values,
              _integer(values['$channelPrefix/Dir']), ChannelDir.input),
          kind: _enumAt(ChannelKind.values,
              _integer(values['$channelPrefix/Kind']), ChannelKind.digital),
          boolValue: _boolean(values['$channelPrefix/BoolValue']),
          analogValue: _number(values['$channelPrefix/AnalogValue']),
          unit: _string(values['$channelPrefix/Unit']),
          forced: _boolean(values['$channelPrefix/Forced']),
          quality: _boolean(values['$channelPrefix/Quality'], fallback: true),
          faultActive: _boolean(values['$channelPrefix/FaultActive']),
          diagnosticKey: _string(values['$channelPrefix/Diagnostic']),
          forceable: _boolean(values['$channelPrefix/Forceable']),
        ));
      }
      nodes[index] = _BusCandidate(
        parent: _integer(values['$prefix/ParentIdx']),
        node: BusNode(
          name: _string(values['$prefix/Name']),
          descriptionKey: _string(values['$prefix/DescriptionKey']),
          typeId: _string(values['$prefix/TypeId']),
          address: _string(values['$prefix/Address']),
          state: _enumAt(NodeState.values, _integer(values['$prefix/State']),
              NodeState.offline),
          linkOk: _boolean(values['$prefix/LinkOk']),
          mappingValid:
              _boolean(values['$topology/MappingValid'], fallback: true),
          mappingDiagnosticKey: _string(values['$topology/MappingDiagnostic']),
          channels: channels,
        ),
      );
    }

    BusNode build(int index) {
      final candidate = nodes[index]!;
      final childNodes = nodes.entries
          .where((entry) => entry.value.parent == index)
          .map((entry) => build(entry.key))
          .toList();
      final source = candidate.node;
      return BusNode(
        name: source.name,
        descriptionKey: source.descriptionKey,
        typeId: source.typeId,
        address: source.address,
        state: source.state,
        linkOk: source.linkOk,
        mappingValid: source.mappingValid,
        mappingDiagnosticKey: source.mappingDiagnosticKey,
        channels: source.channels,
        children: childNodes,
      );
    }

    return nodes.entries
        .where((entry) => entry.value.parent == 0)
        .map((entry) => build(entry.key))
        .toList();
  }
}

bool _customBindable(String relativePath) {
  final lower = relativePath.toLowerCase();
  if (lower.startsWith('hmirequest/') || lower.startsWith('access/req')) {
    return false;
  }
  final segments = lower.split('/');
  return !segments.any((segment) => const {
        'secret',
        'password',
        'pin',
        'credential',
        'token',
      }.contains(segment));
}

AlarmEvent? _alarmEvent(Map<String, Object?> values, String prefix,
    {required bool active}) {
  final state = _enumAt(
      AlarmState.values, _integer(values['$prefix/State']), AlarmState.closed);
  if (active && state == AlarmState.closed) return null;
  final reasonCode = _integer(values['$prefix/ReasonCode']);
  final description = reasonDescriptionKey(
    reasonCode,
    _string(values['$prefix/Description']),
  );
  final sourcePath = _string(values['$prefix/SourcePath']);
  if (!active && description.isEmpty && sourcePath.isEmpty) return null;
  final comeAt = _dateTime(values['$prefix/ComeAt']);
  if (comeAt == null) return null;
  final goneAt = _nonPlaceholderDateTime(values['$prefix/GoneAt']);
  final duration = _duration(values['$prefix/Duration']);
  return AlarmEvent(
    severity: _enumAt(
        Severity.values, _integer(values['$prefix/Severity']), Severity.low),
    description: description,
    sourcePath: sourcePath,
    resetClass: _enumAt(ResetClass.values,
        _integer(values['$prefix/ResetClass']), ResetClass.autoReset),
    state: state,
    comeAt: comeAt,
    goneAt: goneAt,
    duration: goneAt == null ? null : duration,
    reasonCode: reasonCode,
    shelved: _boolean(values['$prefix/Shelved']),
    ioTag: _string(values['$prefix/IoTag']),
    ioAddress: _string(values['$prefix/IoAddress']),
    comeTimeSynchronized:
        _boolean(values['$prefix/ComeTimeSynchronized'], fallback: false),
    goneTimeSynchronized:
        _boolean(values['$prefix/GoneTimeSynchronized'], fallback: false),
    resetTimeSynchronized:
        _boolean(values['$prefix/ResetTimeSynchronized'], fallback: false),
    shelfTimeSynchronized:
        _boolean(values['$prefix/ShelfTimeSynchronized'], fallback: false),
  );
}

DateTime? _nonPlaceholderDateTime(Object? value) {
  final parsed = _dateTime(value);
  return parsed == null || parsed.year <= 1970 ? null : parsed;
}

/// Normalizes the two deployed transport encodings: OPC UA DateTime is a
/// 100-ns count from 1601, while ADS exposes TwinCAT DT as Unix seconds.
DateTime? _dateTime(Object? value) {
  if (value is String && value.contains(RegExp(r'[^0-9-]'))) {
    return DateTime.tryParse(value)?.toUtc();
  }
  final raw = value is num
      ? value.toInt()
      : value is String
          ? int.tryParse(value)
          : null;
  if (raw == null || raw == 0) return null;
  try {
    if (raw.abs() >= 10000000000000000) {
      const uaUnixOffset100ns = 116444736000000000;
      return DateTime.fromMicrosecondsSinceEpoch(
          (raw - uaUnixOffset100ns) ~/ 10,
          isUtc: true);
    }
    if (raw.abs() >= 100000000000000) {
      return DateTime.fromMicrosecondsSinceEpoch(raw, isUtc: true);
    }
    if (raw.abs() >= 100000000000) {
      return DateTime.fromMillisecondsSinceEpoch(raw, isUtc: true);
    }
    return DateTime.fromMillisecondsSinceEpoch(raw * 1000, isUtc: true);
  } on Object {
    return null;
  }
}

PublishedTagValue _publishedTag(Object? source, Object? fallbackValue) {
  if (source is! Map) return PublishedTagValue.good(fallbackValue);
  DateTime? timestamp(String name) {
    final raw = source[name];
    final microseconds = raw is int
        ? raw
        : raw is String
            ? int.tryParse(raw)
            : null;
    if (microseconds == null) return null;
    try {
      return DateTime.fromMicrosecondsSinceEpoch(microseconds, isUtc: true);
    } on Object {
      return null;
    }
  }

  final status = source['status'];
  final type = source['type'];
  return PublishedTagValue(
    value: source.containsKey('value') ? source['value'] : fallbackValue,
    typeName: type is String ? type : 'Unknown',
    statusCode: status is num ? status.toInt() : 0,
    sourceTimestamp: timestamp('sourceTimestampUs'),
    serverTimestamp: timestamp('serverTimestampUs'),
  );
}

class _ModuleCandidate {
  final String browsePath;
  final String identity;
  final String name;
  final ModuleType type;
  _ModuleCandidate? parent;
  final List<_ModuleCandidate> children = [];

  _ModuleCandidate(this.browsePath, this.identity, this.name, this.type);
}

_ModuleCandidate _preferCanonical(
    _ModuleCandidate left, _ModuleCandidate right) {
  final leftDepth = '/'.allMatches(left.browsePath).length;
  final rightDepth = '/'.allMatches(right.browsePath).length;
  if (leftDepth != rightDepth) return leftDepth < rightDepth ? left : right;
  return left.browsePath.compareTo(right.browsePath) <= 0 ? left : right;
}

class _BusCandidate {
  final int parent;
  final BusNode node;
  const _BusCandidate({required this.parent, required this.node});
}

String _string(Object? value) => value is String ? value : '';
bool _boolean(Object? value, {bool fallback = false}) =>
    value is bool ? value : fallback;
int _integer(Object? value, {int fallback = 0}) =>
    value is num ? value.toInt() : fallback;
double _number(Object? value) => value is num ? value.toDouble() : 0;
Duration _duration(Object? value) =>
    Duration(milliseconds: _number(value).round());

T _enumAt<T>(List<T> values, int index, T fallback) =>
    index >= 0 && index < values.length ? values[index] : fallback;

/// Set of every ancestor path that has at least one child, so
/// "does any key start with `<p>/`?" becomes an O(1) lookup instead of a full
/// scan of the value map.
///
/// This is the single biggest cost in mapping a large tree: [_arrayElement] and
/// [_indexedPrefix] each probed 4 candidate prefixes with
/// `values.keys.any(startsWith)`, and they are called once per enum value per
/// module. On a 15k-symbol tree that was ~12M string comparisons per refresh
/// (~1.1s), which blocked the UI isolate and every command's ack poll behind it.
Set<String> _buildParentPaths(Iterable<String> keys) {
  final parents = <String>{};
  for (final key in keys) {
    var cut = key.lastIndexOf('/');
    // Register every ancestor, stopping early once a branch is already known
    // (its ancestors were added when it was first seen).
    while (cut > 0) {
      final parent = key.substring(0, cut);
      if (!parents.add(parent)) break;
      cut = parent.lastIndexOf('/');
    }
  }
  return parents;
}

Object? _arrayElement(
    Map<String, Object?> values, String base, int zeroBasedIndex,
    {Set<String>? parentPaths}) {
  final direct = values[base];
  if (direct is List && zeroBasedIndex < direct.length) {
    return direct[zeroBasedIndex];
  }
  final zeroBased = _indexedAlternatives(base, 0).any((alternative) =>
      values.containsKey(alternative) ||
      _hasChildren(values, alternative, parentPaths));
  final index = zeroBased ? zeroBasedIndex : zeroBasedIndex + 1;
  for (final alternative in _indexedAlternatives(base, index)) {
    if (values.containsKey(alternative)) return values[alternative];
  }
  return null;
}

String? _indexedPrefix(
    Map<String, Object?> values, String base, int oneBasedIndex,
    {Set<String>? parentPaths}) {
  final zeroBased = _indexedAlternatives(base, 0)
      .any((alternative) => _hasChildren(values, alternative, parentPaths));
  final index = zeroBased ? oneBasedIndex - 1 : oneBasedIndex;
  for (final alternative in _indexedAlternatives(base, index)) {
    if (_hasChildren(values, alternative, parentPaths)) {
      return alternative;
    }
  }
  return null;
}

/// True when some key is a descendant of [path]. Uses the precomputed
/// [parentPaths] index when available and falls back to the original scan so
/// direct callers/tests keep working without threading the index through.
bool _hasChildren(
    Map<String, Object?> values, String path, Set<String>? parentPaths) {
  if (parentPaths != null) return parentPaths.contains(path);
  final prefix = '$path/';
  return values.keys.any((key) => key.startsWith(prefix));
}

List<String> _indexedAlternatives(String base, int index) {
  final separator = base.lastIndexOf('/');
  final member = separator < 0 ? base : base.substring(separator + 1);
  return [
    '$base/$index',
    '$base[$index]',
    // TF6100 inserts an ARRAY container before repeating the member browse
    // name on each element: Nodes/Nodes[1], Channels/Channels[1], and so on.
    '$base/$member/$index',
    '$base/$member[$index]',
  ];
}
