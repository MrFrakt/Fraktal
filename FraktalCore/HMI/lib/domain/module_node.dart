/// The discovered module tree — mirror of the exposed namespace (Core 3.10/3.13):
/// a node exists iff the PLC symbol carries `Status : ST_ModuleStatus`.
library;

import 'types.dart';

enum PublishedTagQuality { good, uncertain, bad }

/// Transport-neutral OPC UA DataValue metadata retained for custom HMI
/// controls. A value is usable only when OPC UA reports Good quality.
class PublishedTagValue {
  final Object? value;
  final String typeName;
  final int statusCode;
  final DateTime? sourceTimestamp;
  final DateTime? serverTimestamp;
  final String engineeringUnit;
  final num? minimum;
  final num? maximum;
  final bool writable;

  const PublishedTagValue({
    required this.value,
    this.typeName = 'Unknown',
    this.statusCode = 0,
    this.sourceTimestamp,
    this.serverTimestamp,
    this.engineeringUnit = '',
    this.minimum,
    this.maximum,
    this.writable = false,
  });

  factory PublishedTagValue.good(Object? value) => PublishedTagValue(
        value: value,
        typeName: switch (value) {
          bool _ => 'Boolean',
          int _ => 'Integer',
          double _ => 'Double',
          String _ => 'String',
          _ => 'Unknown',
        },
      );

  PublishedTagQuality get quality {
    final severity = statusCode & 0xC0000000;
    if (severity == 0x00000000) return PublishedTagQuality.good;
    if (severity == 0x40000000) return PublishedTagQuality.uncertain;
    return PublishedTagQuality.bad;
  }

  bool get usable => quality == PublishedTagQuality.good;
}

class ModuleNode {
  final String path; // OPC UA browse path = identity (Core 4.8)
  final String name;
  final String displayNameKey;
  final String descriptionKey;
  final ModuleType type;
  final ExecState state;
  final bool faultActive;
  final String
      message; // Status.Diagnostic.Description (Unit: Pending overlays)
  final String diagnosticIoTag;
  final String diagnosticIoAddress;
  final DateTime? diagnosticSince;
  final bool diagnosticTimeSynchronized;
  final bool tileEnable;
  final List<ModuleNode> children;
  final String controlDomainId; // §9.8; empty means no assigned arrangement
  final String controlDomainName;
  final List<String> controlDomainMembers;

  // Unit-only extras (empty/zero elsewhere)
  final String modelCode;
  final List<String>
      availableModels; // §3.8 optional PLC-published recipe catalog
  final UnitMode? modeActive;
  final int goodCount;
  final int nokCount;
  final bool blocking; // AlarmLog.Blocking -> banner + Start disabled
  final List<AlarmEvent> activeEvents; // AlarmLog.Active (this node's log)
  final List<AlarmEvent> ringEvents; // AlarmLog.Ring newest-first
  final List<HostEvent> hostEvents; // §11.6 bounded ring, newest-first
  final AccessSession? access; // root Units only (per-root manager, 7.7)

  // optional typed facets (annex data) — null when the module doesn't publish them
  final LinkFacet? link; // Annex D
  final PartFacet? part; // Annex E
  final PackMLState? packML; // Annex F
  final MotionFacet? motion; // Annex G / I
  final SafetyFacet? safety; // §9.8 read-only certified-safety mirror
  final ControlPowerFacet? controlPower; // §9.8 Control On + power groups
  final CycleProfile? cycle; // §8.11.4 (Units)
  final List<CycleSummary>
      cycleHistory; // §8.11.4 trend ring, oldest..newest (Units)
  final Duration lastCycleTime; // §8.11.1 (Units)
  final Duration minCycleTime; // §8.11.1 rolling best since reset (Units)
  final List<CommandTiming>
      commandTimings; // §8.11.4(a) module Timing.Rows (CM/EM)
  final MachineState? machineState; // §8.11.3 (Units)
  final int reworkCount; // §8.11.2 (Units)
  final DecisionRequest? decision; // §6.11 (Units)
  final SystemHealthFacet? systemHealth; // §2.7/§8.12 (Units)
  final SignalTowerFacet? signalTower; // §8.13 (Units)
  final List<CfgField> config; // §3.8a editable persistent data
  final StepInfo? step; // §6.5/§6.9 current step (Units)
  final List<StepStat> stepStats; // §8.11.4 Pareto (Units)
  // §3.13 sequence flow chart. The PLC decides whether this module has a chain
  // worth drawing; the HMI never guesses from the module type.
  /// §3.12 derived state this module publishes, in index order.
  final List<StateFlag> stateFlags;
  final bool sequenceViewEnabled;
  final List<SequenceStep> sequenceSteps;

  /// §3.13 rows the PLC says it has. Published live at the module root while
  /// [sequenceSteps] is an on-demand subtree, so this is what tells the UI the
  /// chart exists before any row has been read.
  final int sequenceStepCount;
  final Duration currentStepElapsed;
  final bool currentStepTimedOut;
  final List<CommandInfo>
      commands; // §7.6.1 published manual-command catalog (CM/EM)
  final Nameplate? nameplate; // §3.10.1 asset identity (null = none published)
  final bool running; // §3.4 — a mode sequence is executing (BUSY)
  final bool
      stopPending; // §3.4 — stop requested, sequence still finishing (blink)
  final RunStyle runStyle; // §3.4.2 active run style (Units)
  final List<UnitMode> supportedModes; // §3.7 _M_Supports (Units)
  final List<RunStyle>
      supportedRunStyles; // §3.4.2 which run styles this mode allows
  final Map<UnitMode, ModePolicy> modePolicy; // §3.4.1 per-mode switch policy
  final OeeSnapshot? oee; // §8.5.1 (Units)
  final List<AlarmMeta> alarmMeta; // §8.9 rationalization catalog (Units)
  /// Scalar OPC UA values below this module's canonical browse node, keyed by
  /// relative browse path. Built-in screens keep using the typed contract;
  /// admin-authored controls use this map so custom published module data stays
  /// generic and can still be hidden at the PLC publication edge.
  final Map<String, Object?> publishedValues;
  final Map<String, PublishedTagValue> publishedTags;

  const ModuleNode({
    required this.path,
    required this.name,
    this.displayNameKey = '',
    this.descriptionKey = '',
    required this.type,
    this.state = ExecState.ready,
    this.faultActive = false,
    this.message = '',
    this.diagnosticIoTag = '',
    this.diagnosticIoAddress = '',
    this.diagnosticSince,
    this.diagnosticTimeSynchronized = true,
    this.tileEnable = true,
    this.children = const [],
    this.controlDomainId = '',
    this.controlDomainName = '',
    this.controlDomainMembers = const [],
    this.modelCode = '',
    this.availableModels = const [],
    this.modeActive,
    this.goodCount = 0,
    this.nokCount = 0,
    this.blocking = false,
    this.activeEvents = const [],
    this.ringEvents = const [],
    this.hostEvents = const [],
    this.access,
    this.link,
    this.part,
    this.packML,
    this.motion,
    this.safety,
    this.controlPower,
    this.cycle,
    this.cycleHistory = const [],
    this.lastCycleTime = Duration.zero,
    this.minCycleTime = Duration.zero,
    this.commandTimings = const [],
    this.machineState,
    this.reworkCount = 0,
    this.decision,
    this.systemHealth,
    this.signalTower,
    this.config = const [],
    this.step,
    this.stepStats = const [],
    this.stateFlags = const [],
    this.sequenceViewEnabled = false,
    this.sequenceSteps = const [],
    this.sequenceStepCount = 0,
    this.currentStepElapsed = Duration.zero,
    this.currentStepTimedOut = false,
    this.commands = const [],
    this.nameplate,
    this.running = false,
    this.stopPending = false,
    this.runStyle = RunStyle.continuous,
    this.supportedModes = const [],
    this.supportedRunStyles = const [RunStyle.continuous],
    this.modePolicy = const {},
    this.oee,
    this.alarmMeta = const [],
    this.publishedValues = const {},
    this.publishedTags = const {},
  });

  bool get isUnit => type == ModuleType.unit;

  Map<String, Object?> get hmiValues => {
        ...publishedValues,
        'Status/Name': path,
        'Status/State': state.index,
        'Status/FaultActive': faultActive,
        'Status/Diagnostic/Description': message,
        if (diagnosticSince != null)
          'Status/Diagnostic/Since': diagnosticSince!.toUtc().toIso8601String(),
        'Status/Diagnostic/TimeSynchronized': diagnosticTimeSynchronized,
        'Busy': state == ExecState.busy,
        'Done': state == ExecState.done,
        'Error': state == ExecState.error,
        'Aborted': state == ExecState.aborted,
        if (link != null) ...{
          'Link/Linked': link!.linked,
          'Link/Reason': link!.linkReason,
        },
        if (motion != null) ...{
          'Motion/ActualPosition': motion!.actualPosition,
          'Motion/ActualVelocity': motion!.actualVelocity,
          'Motion/TargetPosition': motion!.targetPosition,
          'Motion/Moving': motion!.moving,
          'Motion/Homed': motion!.homed,
        },
        if (part != null) ...{
          'Part/Uid': part!.uid,
          'Part/Present': part!.present,
          'Part/Verdict': part!.verdict.index,
        },
        if (step != null) ...{
          'CurrentStep/StepNo': step!.stepNo,
          'CurrentStep/StepName': step!.stepName,
          'CurrentStep/AwaitingLabel': step!.awaitingLabel,
        },
        if (systemHealth != null) ...{
          'SystemHealth/Healthy': systemHealth!.healthy,
          'SystemHealth/TaskCycleUs': systemHealth!.taskCycleUs,
          'SystemHealth/TaskJitterUs': systemHealth!.taskJitterUs,
          'SystemHealth/CpuLoadPct': systemHealth!.cpuLoadPct,
          'SystemHealth/MemoryAvailableMb': systemHealth!.memoryAvailableMb,
          'SystemHealth/TimeQuality/Synchronized':
              systemHealth!.time.synchronized,
        },
        if (modeActive != null) 'ModeActivePublished': modeActive!.index,
        'GoodCount': goodCount,
        'NokCount': nokCount,
        'ReworkCount': reworkCount,
      };

  Map<String, PublishedTagValue> get hmiTags {
    final values = hmiValues;
    return {
      for (final entry in values.entries)
        entry.key:
            publishedTags[entry.key] ?? PublishedTagValue.good(entry.value),
      // Preserve Bad/Uncertain tags even when the compatibility `values`
      // object correctly omitted their unusable value.
      ...publishedTags,
    };
  }

  Object? valueAt(String relativePath) {
    var normalized = relativePath.trim();
    while (normalized.startsWith('/')) {
      normalized = normalized.substring(1);
    }
    return hmiValues[normalized];
  }

  PublishedTagValue? tagAt(String relativePath) {
    var normalized = relativePath.trim();
    while (normalized.startsWith('/')) {
      normalized = normalized.substring(1);
    }
    return hmiTags[normalized];
  }

  /// Highest ACTIVE severity on THIS node (null = none).
  Severity? get ownSeverity {
    Severity? top;
    for (final e in activeEvents) {
      if (e.state == AlarmState.closed) continue;
      if (top == null || e.severity.index > top.index) top = e.severity;
    }
    // a module fault without an own log entry still shows as error via Status
    if (faultActive && (top == null || top.index < Severity.high.index)) {
      top = Severity.high;
    }
    return top;
  }

  /// Core 3.13 event-path highlight: max severity in this node's subtree.
  /// Every ancestor of an event source therefore tints (high > medium > low).
  Severity? get effectiveSeverity {
    Severity? top = ownSeverity;
    for (final c in children) {
      final cs = c.effectiveSeverity;
      if (cs != null && (top == null || cs.index > top.index)) top = cs;
    }
    return top;
  }

  ModuleNode? find(String p) {
    if (p == path) return this;
    for (final c in children) {
      final hit = c.find(p);
      if (hit != null) return hit;
    }
    return null;
  }
}
