/// Demo/dev transport and the HMI's integrated demo (Core O6): a simulated
/// controller hosting a three-root forest (Core 3.1a) - a clamp-and-inspect
/// station, the transfer conveyor that feeds it, and a case packer with a
/// nested labeling Unit (§3.1 recursion) - that exercises every surface the
/// generic HMI renders, on any platform, with zero infrastructure.
///
/// Behaviour mirrors the PLC contracts rather than the screens:
///   * every chain runs on [SimChain], so the §3.13 chart, the cycle Gantt,
///     the trend and the step Pareto come from the same steps;
///   * a fault latches until an operator reset (§8.3(b)), clears the latch and
///     never the condition, and the station never resumes on its own - neither
///     after the reset nor after safety or control power return (§9.8);
///   * the write surface applies the §7.6/§7.7 gates the PLC re-checks, so the
///     demo cannot teach a habit a real station refuses.
///
/// What the plant does by itself follows [SimTour], so a viewer meets every
/// feature within one period and a screenshot tool can stop at a known moment.
library;

import 'dart:async';
import 'dart:math' as math;

import '../domain/fieldbus.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import 'plc_repository.dart';
import 'sim_sequence.dart';

/// When the demo's scripted plant does what, measured in plant time from the
/// first forest subscription. One tour repeats for as long as the demo runs.
abstract final class SimTour {
  /// The simulated scan the plant advances by. 4 Hz keeps a step timer live.
  static const tick = Duration(milliseconds: 250);
  static const period = Duration(seconds: 150);

  /// The infeed light curtain is muted while a pallet passes (§9.8, shown
  /// read-only - muting is never granted from the HMI).
  static const mutingFrom = Duration(seconds: 18);
  static const mutingUntil = Duration(seconds: 24);

  /// Conveyor air pressure dips: a MEDIUM auto-reset warning, and Station A
  /// starves at N10 because no pallet arrives (§8.11.4 wait class).
  static const airDipFrom = Duration(seconds: 36);
  static const airDipUntil = Duration(seconds: 50);

  /// A worn robot tool asks the operator what to do (§6.11).
  static const decisionFrom = Duration(seconds: 58);
  static const decisionUntil = Duration(seconds: 88);

  /// The conveyor loses its heartbeat to the line controller (Annex D); a
  /// derived flag it can no longer compute goes stale (§3.12).
  static const linkLossFrom = Duration(seconds: 66);
  static const linkLossUntil = Duration(seconds: 74);

  /// From here the next clamp stroke jams: cylinder B times out (§6.9), the
  /// operator opens the guard to free it, and the station waits for an
  /// operator reset, Control On and Start (§8.3(b), §9.8).
  static const jamFrom = Duration(seconds: 96);
  static const doorOpenAfter = Duration(seconds: 3);
  static const doorClosedAfter = Duration(seconds: 7);
  static const safetyResetAfter = Duration(seconds: 9);
  static const jamClearedAfter = Duration(seconds: 10);

  /// Cylinder B's own command timeout - longer than the step's 2.5 s guard,
  /// so the step first STALLS (a pending diagnostic) and only then faults.
  static const cylinderTimeout = Duration(seconds: 4);

  /// Disturbances that recur at production rate, by AUTO cycle number.
  static const readerRetryEvery = 4; // §6.9(e) handled warning on N55
  static const reworkEvery = 9; // a vision reject goes to rework
  static const nokEvery = 23; // an out-of-tolerance part
}

/// A simulated Unit: its mode, run style and one chain per supported mode.
class _Unit {
  final String path;
  final List<UnitMode> modes;
  final Map<UnitMode, SimChain> chains = {};
  UnitMode mode = UnitMode.auto;
  RunStyle runStyle = RunStyle.continuous;

  /// §3.4 - a mode sequence is executing.
  bool running = false;
  bool stopRequested = false;
  bool stepGranted = false;
  int holdUntil = -1;
  int good = 0, nok = 0, rework = 0;
  final List<double> oeeTrend = [];
  _Unit(this.path, this.modes);
  SimChain? get chain => chains[mode];
}

/// One §9.8 control domain: Control On is requested per domain, and it may
/// serve several peer roots without becoming a super-root.
class _Domain {
  final String id;
  final String name;
  final List<String> members;
  bool requested = true;
  bool on = true;
  bool rearm = false;
  int energizingUntil = -1;
  _Domain(this.id, this.name, this.members);
}

/// One active §8.3 event.
class _Event {
  final Severity severity;
  final String description;
  final String sourcePath;
  final ResetClass resetClass;
  final int reason;
  final String ioTag;
  final String ioAddress;
  final DateTime comeAt;
  final bool synchronized;
  AlarmState state = AlarmState.active;
  _Event(this.severity, this.description, this.sourcePath, this.resetClass,
      {required this.comeAt,
      this.reason = 0,
      this.ioTag = '',
      this.ioAddress = '',
      this.synchronized = true});
  String get id => '$sourcePath|$description';
}

/// A §8.11.4(a) command-timing aggregate (module `Timing.Rows[]`).
class _Timing {
  final int id;
  final String label;
  int count = 0;
  Duration last = Duration.zero;
  Duration min = Duration.zero;
  Duration max = Duration.zero;
  Duration total = Duration.zero;
  _Timing(this.id, this.label);

  void add(Duration d) {
    count++;
    last = d;
    total += d;
    if (count == 1 || d < min) min = d;
    if (d > max) max = d;
  }

  CommandTiming publish() => CommandTiming(id, label, count, last, min, max,
      count == 0 ? Duration.zero : total ~/ count);
}

class SimRepository implements PlcRepository {
  /// §3.8b startup state. A real station learns both of these exactly once, as
  /// it restores: the image was rejected, or the store is refusing writes. They
  /// are constructor parameters rather than setters for that reason - there is
  /// no runtime act that produces a restore loss, so a back door would prove
  /// the back door works rather than the path a station takes.
  ///
  /// The shipped demo defaults to a healthy store: a permanent warning banner
  /// in a demo teaches an operator to ignore the real one.
  final bool restoreLost;
  final String restoreLostPath;
  final bool persistFailed;

  /// The simulated controller is a commissioning build (Core §7.5): it runs a
  /// simulation driver, so it says so, and it offers §10.5.1 output forcing -
  /// which only exists while a gate is declared. False is a production-like
  /// build: no gate, and no channel is forceable.
  final bool commissioning;

  SimRepository({
    this.restoreLost = false,
    this.restoreLostPath = '',
    this.persistFailed = false,
    this.commissioning = true,
    DateTime? epoch,
  }) : _epoch = epoch ?? DateTime.now() {
    _build();
  }

  final _ctrl = StreamController<List<ModuleNode>>.broadcast();
  final _link = StreamController<LinkState>.broadcast();
  final _bus = StreamController<List<BusNode>>.broadcast();
  Timer? _timer;
  int _tick = 0;

  /// Plant time: the wall clock at construction, advanced by simulated scans
  /// rather than read from the host, so a recorded run is reproducible.
  final DateTime _epoch;
  DateTime get _now => _epoch.add(SimTour.tick * _tick);

  /// The plant's clock: what a panel recording this demo measures elapsed
  /// time against (`hmiNow`).
  DateTime get plantTime => _now;

  static final int _periodTicks =
      SimTour.period.inMilliseconds ~/ SimTour.tick.inMilliseconds;
  Duration get _tour => SimTour.tick * (_tick % _periodTicks);
  bool _within(Duration from, Duration until) => _tour >= from && _tour < until;
  static int _ticksOf(Duration d) =>
      d.inMilliseconds ~/ SimTour.tick.inMilliseconds;

  // ---- plant state ----

  final Map<String, _Unit> _units = {};
  final Map<String, _Domain> _domains = {
    'Cell1': _Domain('Cell1', 'Cell 1 (station + conveyor)',
        const ['StationA', 'ConveyorB']),
    'Cell2': _Domain('Cell2', 'Cell 2 (packing)', const ['PackerC']),
  };
  final Map<String, AccessSession> _access = {
    'StationA': const AccessSession(),
    'ConveyorB': const AccessSession(),
    'PackerC': const AccessSession(),
  };

  /// §3.8d(b) data classes declared on Station A, as its policy holds them.
  final Map<String, DataClassPolicy> _classes = {
    'quality': const DataClassPolicy(
        classId: 'quality',
        labelKey: 'project.dataClass.quality',
        readLevel: AccessLevel.operator,
        writeLevel: AccessLevel.technician),
    'integration': const DataClassPolicy(
        classId: 'integration',
        labelKey: 'project.dataClass.integration',
        readLevel: AccessLevel.technician,
        writeLevel: AccessLevel.engineer),
  };

  final List<_Event> _active = [];
  final Map<String, List<AlarmEvent>> _rings = {
    'StationA': [],
    'ConveyorB': [],
    'PackerC': [],
  };
  static const _ringDepth = 60;
  final Set<String> _shelved = {}; // §8.10 'src|desc' keys
  final Map<String, ({bool b, double a})> _forced = {};
  final Map<String, IoChannel> _latestChannels = {};
  final Map<String, Map<int, _Timing>> _timings = {};
  final Map<String, (bool, DateTime)> _flags = {};
  final Map<String, int> _commandBusyUntil = {};
  bool _seeding = false;

  // Station A's process.
  bool _jamArmed = false;
  bool _cylBStuck = false;
  bool _jamFault = false;
  int _jamTick = -1;
  bool _doorOpen = false;
  bool _safetyResetRequired = false;
  bool _separatorOut = false;
  bool _partPresent = false;
  // Each cylinder travels toward the position it was last commanded to, by an
  // AUTO step or a manual command; the clamp is closed when both are there.
  double _cylAPos = 0, _cylBPos = 0;
  double _cylATarget = 0, _cylBTarget = 0;
  bool get _clamped => _cylAPos >= 49 && _cylBPos >= 49;
  double _robotPos = 245.7, _robotVel = 0;
  int _jogUntil = -1;
  double _jogDir = 0;
  bool _judgeOk = true;
  int _inspections = 0;
  String _inspectionResult = '';
  int _codeTriggers = 0, _codeGood = 0, _codeNoRead = 0;
  String _lastCode = '';
  bool _readerRetry = false;
  String _lastUid = '';
  bool _tagPresent = false;
  DecisionRequest? _decision;
  bool _toolWorn = false;
  bool _changeoverConfirm = false;
  String? _pendingModel;
  int _lampTestUntil = -1;
  Verdict _verdict = Verdict.ok;
  String _verdictReason = '';
  int _partSerial = 4100;

  // Conveyor B's process.
  bool _airDip = false;
  bool _linkLost = false;
  bool _palletAtStop = false;
  bool _liftUp = false;

  // Station A's model data, one record per model (the recipe-provider
  // analogue): any model's record can be read and edited without a changeover.
  String _modelA = 'A100';
  String _modelB = 'EURO-PAL';
  String _modelC = 'CASE-12';
  final _stationAModels = ['A100', 'A200', 'A300'];
  final Map<String, String> _settleByModel = {
    'A100': '150',
    'A200': '180',
    'A300': '220',
  };
  String _settle(String model) =>
      _settleByModel.putIfAbsent(model, () => '150');

  /// The Station A model a request names: 0 = the running one.
  String? _modelAt(int index) => index == 0
      ? _modelA
      : (index > 0 && index <= _stationAModels.length
          ? _stationAModels[index - 1]
          : null);

  /// Station and model values by write key (one store, every module).
  final Map<String, String> _cfg = {
    'sim.station.mes.endpointIp': '10.20.0.14',
    'sim.station.mes.port': '4840',
    'sim.station.requireTwoHandStart': 'TRUE',
    'sim.station.modeShield': '1',
    'sim.station.inspectionThreshold': '85',
    'sim.station.rejectBinCapacity': '40',
    'sim.station.mesHeartbeat': '5',
    'sim.clamp.pressureBar': '5.5',
    'sim.cylB.extendLimitMs': '4000',
    'sim.camera.program': '7',
    'sim.conveyor.beltSpeed': '18',
    'sim.packer.cartonsPerLayer': '12',
    'sim.packer.glueTemperature': '165',
    'sim.labeler.template': 'LBL-EU-04',
  };

  /// §3.8e line config, owned by Station A and mirrored by Conveyor B. The
  /// calendar is a §8.5.2 weekly calendar (V2): start, duration, weekdays and
  /// a target per shift. The offset is set from the plant clock's zone at
  /// construction, so the shift times the demo shows agree with its clock.
  static const _shiftRows = 4;
  final Map<String, String> _line = {
    'line.shift.utcOffsetMin': '0',
    'line.shift.1.startMin': '360',
    'line.shift.1.durationMin': '480',
    'line.shift.1.activeDays': '31',
    'line.shift.1.productionTarget': '1200',
    'line.shift.2.startMin': '840',
    'line.shift.2.durationMin': '480',
    'line.shift.2.activeDays': '31',
    'line.shift.2.productionTarget': '1100',
    'line.shift.3.startMin': '1320',
    'line.shift.3.durationMin': '480',
    'line.shift.3.activeDays': '15',
    'line.shift.3.productionTarget': '900',
    'line.shift.4.startMin': '480',
    'line.shift.4.durationMin': '720',
    'line.shift.4.activeDays': '96',
    'line.shift.4.productionTarget': '1300',
    'line.taktMs': '10500',
  };

  // demo users (FB_LocalAccessProvider analogue)
  static const _users = {
    'op1': ('1111', AccessLevel.operator),
    'tech1': ('4711', AccessLevel.technician),
    'eng1': ('9999', AccessLevel.engineer),
    'admin1': ('2468', AccessLevel.admin),
  };

  // ==== construction ====

  void _build() {
    _line['line.shift.utcOffsetMin'] = '${_epoch.timeZoneOffset.inMinutes}';
    final a = _units['StationA'] = _Unit('StationA', const [
      UnitMode.auto,
      UnitMode.manual,
      UnitMode.home,
      UnitMode.changeover
    ]);
    a.chains[UnitMode.auto] = SimChain(
      steps: _autoA,
      duration: _durationA,
      holds: (step) => step.stepNo == 40 && _cylBStuck,
      onEnter: _enterA,
      onComplete: _completeA,
      onCycle: _cycleA,
    );
    a.chains[UnitMode.manual] = _idleChain();
    a.chains[UnitMode.home] = SimChain(
      steps: _homeA,
      repeats: false,
      duration: _nominal,
      onComplete: (step, took, _) {
        if (step.stepNo == 20) {
          _cylATarget = 0;
          _cylBTarget = 0;
        }
        if (step.stepNo == 30) _robotPos = 0;
      },
    );
    a.chains[UnitMode.changeover] = SimChain(
      steps: _changeoverA,
      repeats: false,
      duration: _nominal,
      holds: (step) => step.stepNo == 30 && _changeoverConfirm,
      onEnter: (step, _) {
        if (step.stepNo == 30) {
          _changeoverConfirm = true;
          _decision = const DecisionRequest(
              prompt: 'project.decision.fingersSwapped',
              options: ['project.decision.confirmSwapped'],
              defaultOption: 1);
        }
        if (step.stepNo == 40 && _pendingModel != null) {
          _modelA = _pendingModel!;
          _pendingModel = null;
        }
      },
    );

    final b = _units['ConveyorB'] =
        _Unit('ConveyorB', const [UnitMode.auto, UnitMode.manual]);
    b.chains[UnitMode.auto] = SimChain(
      steps: _autoB,
      duration: (step, cycle) {
        var ms = step.nominal.inMilliseconds + _jitter(cycle, step.stepNo, 80);
        if (step.stepNo == 10 && _airDip) ms += 3000;
        return Duration(milliseconds: ms);
      },
      onEnter: (step, _) {
        if (step.stepNo == 20) _liftUp = true;
        if (step.stepNo == 40) _liftUp = false;
      },
      onComplete: (step, took, _) {
        if (step.stepNo == 10) _palletAtStop = true;
        if (step.stepNo == 30) _palletAtStop = false;
        _timing(
            'ConveyorB.Lift',
            step.stepNo == 20 ? 1 : 2,
            step.stepNo == 20
                ? 'project.command.raise'
                : 'project.command.lower',
            took,
            when: step.stepNo == 20 || step.stepNo == 40);
      },
      onCycle: (_) => b.good++,
    );
    b.chains[UnitMode.manual] = _idleChain();

    final c = _units['PackerC'] =
        _Unit('PackerC', const [UnitMode.auto, UnitMode.manual]);
    c.chains[UnitMode.auto] = SimChain(
      steps: _autoC,
      duration: (step, cycle) => Duration(
          milliseconds:
              step.nominal.inMilliseconds + _jitter(cycle, step.stepNo, 90)),
      onComplete: (step, took, _) {
        if (step.stepNo == 10) {
          _timing('PackerC.Erector', 1, 'project.command.erect', took);
        }
      },
      onCycle: (cycle) => cycle % 31 == 7 ? c.nok++ : c.good++,
    );
    c.chains[UnitMode.manual] = _idleChain();

    final l = _units['PackerC.Labeler'] =
        _Unit('PackerC.Labeler', const [UnitMode.auto, UnitMode.manual]);
    l.chains[UnitMode.auto] = SimChain(
      steps: _autoLabeler,
      duration: (step, cycle) => Duration(
          milliseconds:
              step.nominal.inMilliseconds + _jitter(cycle, step.stepNo, 60)),
      onCycle: (_) => l.good++,
    );
    l.chains[UnitMode.manual] = _idleChain();

    // "The station has been running": every AUTO chain is seeded with a full
    // profiler ring by the same engine that runs it live, so the trend, the
    // Gantt and the Pareto have something true to say from the first frame.
    _seeding = true;
    for (final unit in _units.values) {
      final chain = unit.chains[UnitMode.auto]!;
      chain.restart(clearChart: true);
      while (chain.cycleNo < SimChain.historyDepth) {
        chain.advance(SimTour.tick);
      }
      unit.running = true;
    }
    _seeding = false;
    // Counts are the current shift's (§8.5.2 closes them at each boundary).
    a.good = 912;
    a.nok = 9;
    a.rework = 14;
    b.good = 931;
    c.good = 377;
    c.nok = 2;
    l.good = 377;
    for (final unit in _units.values) {
      for (var i = 0; i < 24; i++) {
        unit.oeeTrend.add(0.78 + 0.1 * ((i * 7) % 10) / 10);
      }
    }
    _cylAPos = _cylBPos = _cylATarget = _cylBTarget = 0;
    _robotPos = 245.7;
    _seedHistory();
    if (commissioning) {
      for (final root in _rings.keys) {
        _raise(Severity.low, 'std.engineering.simulation', root,
            ResetClass.autoReset,
            reason: _commissioningGate);
        _raise(Severity.low, 'std.engineering.outputForcing', root,
            ResetClass.autoReset,
            reason: _commissioningGate);
      }
    }
  }

  /// `E_Reason.COMMISSIONING_GATE_ACTIVE` (Core §8.8).
  static const _commissioningGate = 2030;

  SimChain _idleChain() => SimChain(
        steps: const [
          SimStepDef(10, 'project.step.manualIdle',
              timeClass: TimeClass.waitOperator,
              nominal: Duration(days: 1),
              steppable: false),
        ],
        duration: _nominal,
      );

  static Duration _nominal(SimStepDef step, int cycle) => step.nominal;

  /// Deterministic scatter, so a recorded run repeats exactly.
  static int _jitter(int cycle, int step, int spread) => spread == 0
      ? 0
      : ((cycle * 7919 + step * 104729) % (2 * spread + 1)) - spread;

  /// A few closed events from before the demo connected, so the history has
  /// the shape it has on a station that has been running for a shift.
  void _seedHistory() {
    AlarmEvent closed(Severity sev, String desc, String src, ResetClass rc,
            Duration ago, Duration lasted,
            {int reason = 0, String ioTag = '', bool synced = true}) =>
        AlarmEvent(
            severity: sev,
            description: desc,
            sourcePath: src,
            resetClass: rc,
            state: AlarmState.closed,
            comeAt: _now.subtract(ago),
            goneAt: _now.subtract(ago - lasted),
            duration: lasted,
            reasonCode: reason,
            ioTag: ioTag,
            comeTimeSynchronized: synced,
            goneTimeSynchronized: synced);
    _rings['StationA']!.addAll([
      closed(
          Severity.high,
          'project.reason.cylinderTimeout',
          'StationA.ClampStation.CylB',
          ResetClass.manualReset,
          const Duration(hours: 3, minutes: 12),
          const Duration(minutes: 4),
          reason: 10112,
          ioTag: '=A1+S1-B41'),
      closed(
          Severity.low,
          'project.reason.readRetry',
          'StationA.CodeReader',
          ResetClass.autoReset,
          const Duration(hours: 2, minutes: 40),
          const Duration(seconds: 2),
          reason: 10205),
      closed(
          Severity.medium,
          'project.reason.guardOpened',
          'StationA.DoorNorth',
          ResetClass.autoReset,
          const Duration(hours: 1, minutes: 55),
          const Duration(minutes: 2),
          reason: 10401),
      closed(
          Severity.low,
          'project.reason.visionReject',
          'StationA.Camera',
          ResetClass.autoReset,
          const Duration(minutes: 47),
          const Duration(seconds: 1),
          reason: 10210),
      closed(
          Severity.low,
          'project.reason.toolChange',
          'StationA.Robot',
          ResetClass.autoReset,
          const Duration(minutes: 21),
          const Duration(seconds: 40),
          reason: 10220),
    ]);
    _rings['ConveyorB']!.addAll([
      closed(
          Severity.medium,
          'project.reason.airPressureLow',
          'ConveyorB.AirMonitor',
          ResetClass.autoReset,
          const Duration(hours: 2, minutes: 5),
          const Duration(seconds: 50),
          reason: 10301,
          ioTag: '=A2+S1-B30'),
      closed(
          Severity.medium,
          'project.status.heartbeatLost',
          'ConveyorB',
          ResetClass.autoReset,
          const Duration(minutes: 58),
          const Duration(seconds: 9),
          reason: 10302),
    ]);
    _rings['PackerC']!.addAll([
      closed(
          Severity.medium,
          'project.reason.cartonJam',
          'PackerC.Erector',
          ResetClass.manualReset,
          const Duration(hours: 1, minutes: 10),
          const Duration(minutes: 3),
          reason: 10501,
          synced: false),
    ]);
  }

  // ==== chain definitions ====

  static const _autoA = [
    SimStepDef(10, 'project.step.awaitPallet',
        awaitingLabel: 'ConveyorB',
        timeClass: TimeClass.waitUpstream,
        expected: Duration(seconds: 5),
        nominal: Duration(milliseconds: 1400)),
    SimStepDef(20, 'project.step.readPalletTag',
        awaitingLabel: 'RfidReader.READ',
        awaitsPath: 'StationA.RfidReader',
        expected: Duration(milliseconds: 1500),
        nominal: Duration(milliseconds: 700)),
    SimStepDef(30, 'project.step.separatePart',
        awaitingLabel: 'Separator1.EXTEND',
        awaitsPath: 'StationA.Separator1',
        expected: Duration(seconds: 2),
        nominal: Duration(milliseconds: 1500)),
    SimStepDef(40, 'project.step.clampPart',
        awaitingLabel: 'ClampStation.CLAMP',
        awaitsPath: 'StationA.ClampStation',
        expected: Duration(milliseconds: 2500),
        nominal: Duration(milliseconds: 1800)),
    SimStepDef(45, 'project.step.inspectAndRead',
        expected: Duration(seconds: 3),
        nominal: Duration.zero,
        legs: [
          SimStepDef(50, 'project.step.inspectPart',
              awaitingLabel: 'Camera.INSPECT',
              awaitsPath: 'StationA.Camera',
              expected: Duration(milliseconds: 2500),
              nominal: Duration(milliseconds: 1600)),
          SimStepDef(55, 'project.step.readPartCode',
              awaitingLabel: 'CodeReader.READ',
              awaitsPath: 'StationA.CodeReader',
              expected: Duration(milliseconds: 2500),
              nominal: Duration(milliseconds: 900)),
        ]),
    SimStepDef(60, 'project.step.robotPick',
        awaitingLabel: 'Robot.PICK',
        awaitsPath: 'StationA.Robot',
        expected: Duration(milliseconds: 2500),
        nominal: Duration(milliseconds: 1700)),
    SimStepDef(70, 'project.step.unclampPart',
        awaitingLabel: 'ClampStation.UNCLAMP',
        awaitsPath: 'StationA.ClampStation',
        expected: Duration(milliseconds: 1500),
        nominal: Duration(milliseconds: 900)),
    SimStepDef(80, 'project.step.awaitOutfeed',
        awaitingLabel: 'PackerC',
        timeClass: TimeClass.waitDownstream,
        expected: Duration(seconds: 3),
        nominal: Duration(milliseconds: 600)),
  ];

  static const _homeA = [
    SimStepDef(10, 'project.step.homeInitialize',
        nominal: Duration(milliseconds: 500)),
    SimStepDef(20, 'project.step.homeUnclamp',
        awaitingLabel: 'ClampStation.UNCLAMP',
        awaitsPath: 'StationA.ClampStation',
        expected: Duration(seconds: 2),
        nominal: Duration(milliseconds: 1200)),
    SimStepDef(30, 'project.step.homeRobot',
        awaitingLabel: 'Robot.HOME',
        awaitsPath: 'StationA.Robot',
        expected: Duration(seconds: 6),
        nominal: Duration(milliseconds: 3200)),
    SimStepDef(40, 'project.step.homeDone',
        nominal: Duration(milliseconds: 250)),
  ];

  static const _changeoverA = [
    SimStepDef(10, 'project.step.changeoverInitialize',
        nominal: Duration(milliseconds: 500)),
    SimStepDef(20, 'project.step.changeoverUnclamp',
        awaitingLabel: 'ClampStation.UNCLAMP',
        awaitsPath: 'StationA.ClampStation',
        expected: Duration(seconds: 2),
        nominal: Duration(milliseconds: 1200)),
    SimStepDef(30, 'project.step.changeoverSwapFingers',
        timeClass: TimeClass.waitOperator,
        nominal: Duration(milliseconds: 500)),
    SimStepDef(40, 'project.step.changeoverCommit',
        nominal: Duration(milliseconds: 800)),
    SimStepDef(50, 'project.step.changeoverDone',
        nominal: Duration(milliseconds: 250)),
  ];

  static const _autoB = [
    SimStepDef(10, 'project.step.conveyorInfeed',
        awaitingLabel: 'Infeed.TRANSPORT',
        awaitsPath: 'ConveyorB.Infeed',
        expected: Duration(seconds: 4),
        nominal: Duration(milliseconds: 2400)),
    SimStepDef(20, 'project.step.liftRaise',
        awaitingLabel: 'Lift.RAISE',
        awaitsPath: 'ConveyorB.Lift',
        expected: Duration(seconds: 2),
        nominal: Duration(milliseconds: 1300)),
    SimStepDef(30, 'project.step.handOver',
        awaitingLabel: 'StationA',
        timeClass: TimeClass.waitDownstream,
        expected: Duration(seconds: 8),
        nominal: Duration(milliseconds: 1800)),
    SimStepDef(40, 'project.step.liftLower',
        awaitingLabel: 'Lift.LOWER',
        awaitsPath: 'ConveyorB.Lift',
        expected: Duration(seconds: 2),
        nominal: Duration(milliseconds: 1100)),
  ];

  static const _autoC = [
    SimStepDef(10, 'project.step.erectCarton',
        awaitingLabel: 'Erector.ERECT',
        awaitsPath: 'PackerC.Erector',
        expected: Duration(seconds: 3),
        nominal: Duration(milliseconds: 2200)),
    SimStepDef(20, 'project.step.fillCarton',
        awaitingLabel: 'StationA',
        timeClass: TimeClass.waitUpstream,
        expected: Duration(seconds: 5),
        nominal: Duration(milliseconds: 3000)),
    SimStepDef(30, 'project.step.labelCarton',
        awaitingLabel: 'Labeler',
        awaitsPath: 'PackerC.Labeler',
        expected: Duration(seconds: 3),
        nominal: Duration(milliseconds: 1800)),
    SimStepDef(40, 'project.step.sealCarton',
        awaitingLabel: 'Sealer.SEAL',
        awaitsPath: 'PackerC.Sealer',
        expected: Duration(seconds: 2),
        nominal: Duration(milliseconds: 1600)),
  ];

  static const _autoLabeler = [
    SimStepDef(10, 'project.step.printLabel',
        awaitingLabel: 'Printer.PRINT',
        awaitsPath: 'PackerC.Labeler.Printer',
        expected: Duration(milliseconds: 1500),
        nominal: Duration(milliseconds: 1000)),
    SimStepDef(20, 'project.step.applyLabel',
        awaitingLabel: 'Applicator.APPLY',
        awaitsPath: 'PackerC.Labeler.Applicator',
        expected: Duration(milliseconds: 1200),
        nominal: Duration(milliseconds: 800)),
  ];

  /// Which module command a Station A AUTO step issues (§8.11.4(a)).
  static const _commandOfStep = {
    20: ('StationA.RfidReader', 1, 'project.command.readTag'),
    30: ('StationA.Separator1', 1, 'project.command.extend'),
    40: ('StationA.ClampStation', 1, 'project.command.clamp'),
    50: ('StationA.Camera', 1, 'project.command.triggerInspection'),
    55: ('StationA.CodeReader', 1, 'project.command.triggerRead'),
    60: ('StationA.Robot', 3, 'project.command.pick'),
    70: ('StationA.ClampStation', 2, 'project.command.unclamp'),
  };

  Duration _durationA(SimStepDef step, int cycle) {
    var ms = step.nominal.inMilliseconds +
        _jitter(cycle, step.stepNo, step.nominal.inMilliseconds ~/ 10);
    switch (step.stepNo) {
      case 10:
        // Starved: the conveyor brings no pallet while its air is low. One
        // seeded cycle carries the same excursion, so the trend shows it.
        if (_airDip || (_seeding && cycle == 12)) ms += 2600;
      case 40:
        ms += (cycle % 30) * 15; // the clamp slows as its seals wear
      case 55:
        if (cycle % SimTour.readerRetryEvery == 2) ms += 1400;
    }
    return Duration(milliseconds: ms);
  }

  void _enterA(SimStepDef step, int cycle) {
    switch (step.stepNo) {
      case 20:
        _tagPresent = true;
        _partPresent = true;
      case 40:
        _cylATarget = 50;
        _cylBTarget = 50;
        if (_jamArmed && !_seeding) {
          _jamArmed = false;
          _cylBStuck = true;
        }
      case 70:
        _cylATarget = 0;
        _cylBTarget = 0;
      case 55:
        _readerRetry = cycle % SimTour.readerRetryEvery == 2;
        _codeTriggers++;
        if (_readerRetry) {
          _codeNoRead++;
          if (!_seeding) {
            // §6.9(e): the step owns this - it reads again and carries on.
            _units['StationA']!.chains[UnitMode.auto]!.markWarning(
                55, 'project.reason.readRetry', 'StationA.CodeReader');
            _raise(Severity.low, 'project.reason.readRetry',
                'StationA.CodeReader', ResetClass.autoReset,
                reason: 10205);
          }
        }
      case 60:
        if (!_seeding && _toolWorn && _decision == null) {
          _decision = const DecisionRequest(
              prompt: 'project.decision.toolWorn',
              options: [
                'project.decision.replaceNow',
                'project.decision.finishBatch'
              ],
              defaultOption: 2);
        }
    }
  }

  void _completeA(SimStepDef step, Duration took, int cycle) {
    final command = _commandOfStep[step.stepNo];
    if (command != null) _timing(command.$1, command.$2, command.$3, took);
    switch (step.stepNo) {
      case 20:
        _lastUid =
            'E004 0150 ${(0x1A2B + cycle).toRadixString(16).toUpperCase()} '
            '${(0x3C4D + cycle * 7).toRadixString(16).toUpperCase().padLeft(4, '0')}';
      case 30:
        _separatorOut = true;
      case 40:
        _separatorOut = false;
      case 50:
        _inspections++;
        _judgeOk = cycle % SimTour.reworkEvery != 5;
        _inspectionResult = _judgeOk
            ? 'OK  score=0.${96 - cycle % 4}  x=12.4${cycle % 10} y=8.0${cycle % 7}  θ=0.${cycle % 5}°'
            : 'NG  score=0.61  scratch at x=4.2 y=11.8';
        if (!_judgeOk && !_seeding) {
          _raise(Severity.low, 'project.reason.visionReject', 'StationA.Camera',
              ResetClass.autoReset,
              reason: 10210);
          _clear('StationA.Camera', 'project.reason.visionReject');
        }
      case 55:
        _codeGood++;
        _lastCode =
            'FRK-$_modelA-${(_partSerial + 1).toString().padLeft(6, '0')}';
        if (_readerRetry && !_seeding) {
          _clear('StationA.CodeReader', 'project.reason.readRetry');
        }
      case 60:
        _partPresent = false;
      case 80:
        _tagPresent = false; // the pallet leaves the reader
    }
  }

  void _cycleA(int cycle) {
    final unit = _units['StationA']!;
    _partSerial++;
    if (!_judgeOk) {
      unit.rework++;
      _verdict = Verdict.rework;
      _verdictReason = 'project.reason.visionReject';
    } else if (cycle % SimTour.nokEvery == 11) {
      unit.nok++;
      _verdict = Verdict.nok;
      _verdictReason = 'project.reason.dimensionOutOfTolerance';
    } else {
      unit.good++;
      _verdict = Verdict.ok;
      _verdictReason = '';
    }
  }

  void _timing(String path, int id, String label, Duration took,
      {bool when = true}) {
    if (!when) return;
    (_timings[path] ??= {}).putIfAbsent(id, () => _Timing(id, label)).add(took);
  }

  // ==== streams ====

  @override
  Stream<LinkState> linkState() {
    scheduleMicrotask(() => _link.add(LinkState.live));
    return _link.stream;
  }

  @override
  Stream<List<ModuleNode>> forest() {
    _timer ??= Timer.periodic(SimTour.tick, (_) => _step());
    scheduleMicrotask(_publish);
    return _ctrl.stream;
  }

  @override
  Stream<List<BusNode>> fieldbus() {
    scheduleMicrotask(_publishBus);
    return _bus.stream;
  }

  // The simulation publishes its bus tree immediately, so an empty fieldbus
  // means none — no separate loading state.
  @override
  bool get fieldbusExpected => false;

  // ==== the plant's scan ====

  void _step() {
    _tick++;
    _tourEvents();
    _jamTimeline();
    for (final domain in _domains.values) {
      if (domain.energizingUntil >= 0 && _tick >= domain.energizingUntil) {
        domain.energizingUntil = -1;
        domain.on = true;
      }
    }
    for (final unit in _units.values) {
      _scanUnit(unit);
    }
    _animate();
    if (_tick % _ticksOf(const Duration(seconds: 10)) == 0) {
      for (final unit in _units.values) {
        unit.oeeTrend.add(_oee(unit).oee);
        if (unit.oeeTrend.length > 24) unit.oeeTrend.removeAt(0);
      }
    }
    // The plant scans at 4 Hz; it PUBLISHES at the 2 Hz a real station's
    // snapshot arrives at, so the panel is driven exactly as hard as it is in
    // the field. (A write still publishes at once, as an acknowledgement does.)
    if (_tick % _publishEvery == 0) {
      _publish();
      _publishBus();
    }
  }

  static final int _publishEvery = _ticksOf(const Duration(milliseconds: 500));

  /// The tour's windows open and close here, each on its edge.
  void _tourEvents() {
    final airDip = _within(SimTour.airDipFrom, SimTour.airDipUntil);
    if (airDip != _airDip) {
      _airDip = airDip;
      if (airDip) {
        _raise(Severity.medium, 'project.reason.airPressureLow',
            'ConveyorB.AirMonitor', ResetClass.autoReset,
            reason: 10301, ioTag: '=A2+S1-B30', ioAddress: 'EL3021 Ch1');
      } else {
        _clear('ConveyorB.AirMonitor', 'project.reason.airPressureLow');
      }
    }
    final linkLost = _within(SimTour.linkLossFrom, SimTour.linkLossUntil);
    if (linkLost != _linkLost) {
      _linkLost = linkLost;
      if (linkLost) {
        _raise(Severity.medium, 'project.status.heartbeatLost', 'ConveyorB',
            ResetClass.autoReset,
            reason: 10302);
      } else {
        _clear('ConveyorB', 'project.status.heartbeatLost');
      }
    }
    final wearWindow = _within(SimTour.decisionFrom, SimTour.decisionUntil);
    if (wearWindow && !_toolWorn) {
      _toolWorn = true;
      _raise(Severity.low, 'project.reason.toolChange', 'StationA.Robot',
          ResetClass.autoReset,
          reason: 10220);
    } else if (!wearWindow && _toolWorn) {
      // The batch ended without an answer: the default stands, as the PLC's
      // own decision default would.
      _toolWorn = false;
      if (_decision?.prompt == 'project.decision.toolWorn') _decision = null;
      _clear('StationA.Robot', 'project.reason.toolChange');
    }
    if (_tour == SimTour.jamFrom && !_jamFault) _jamArmed = true;
  }

  /// The jam's own story, from the moment cylinder B faulted: the operator
  /// opens the guard, frees the cylinder, closes the guard and resets the
  /// safety circuit - and then the station still waits for the HMI.
  void _jamTimeline() {
    final unit = _units['StationA']!;
    final chain = unit.chains[UnitMode.auto]!;
    if (_cylBStuck &&
        !_jamFault &&
        unit.mode == UnitMode.auto &&
        chain.currentStep?.stepNo == 40 &&
        chain.currentElapsed >= SimTour.cylinderTimeout) {
      _jamFault = true;
      _jamTick = _tick;
      unit.running = false;
      unit.stopRequested = false;
      chain.raiseError(40, 'StationA.ClampStation.CylB');
      _raise(Severity.high, 'project.reason.cylinderTimeout',
          'StationA.ClampStation.CylB', ResetClass.manualReset,
          reason: 10112, ioTag: '=A1+S1-B41', ioAddress: 'EL1008 Ch1');
    }
    if (_jamTick < 0) return;
    final since = SimTour.tick * (_tick - _jamTick);
    if (since == SimTour.doorOpenAfter) {
      _doorOpen = true;
      _raise(Severity.medium, 'project.reason.guardOpened',
          'StationA.DoorNorth', ResetClass.autoReset,
          reason: 10401, ioTag: '=A1+S1-S01', ioAddress: 'EL1904 Ch1');
      // §9.8: the safety circuit withdraws the valve zones; they do not come
      // back by themselves when it closes.
      final domain = _domains['Cell1']!;
      domain.on = false;
      domain.rearm = true;
    } else if (since == SimTour.doorClosedAfter) {
      _doorOpen = false;
      _safetyResetRequired = true;
      _clear('StationA.DoorNorth', 'project.reason.guardOpened');
    } else if (since == SimTour.safetyResetAfter) {
      _safetyResetRequired = false; // the physical reset button, not the HMI
    } else if (since == SimTour.jamClearedAfter) {
      _cylBStuck = false;
      _jamTick = -1;
      for (final e in _active) {
        if (e.sourcePath == 'StationA.ClampStation.CylB') {
          e.state = AlarmState.waitReset; // condition gone, latch stays
        }
      }
    }
  }

  bool _domainLive(String unitPath) {
    final domain = _domainOf(unitPath);
    return domain == null || (domain.on && !domain.rearm);
  }

  void _scanUnit(_Unit unit) {
    final chain = unit.chain;
    if (chain == null) return;
    if (unit.mode == UnitMode.manual) {
      if (!chain.running) chain.restart(clearChart: true);
      chain.advance(SimTour.tick);
      return;
    }
    if (!unit.running) return;
    // Outputs withdrawn by control power or the safety circuit: the chain
    // holds where it is (HELD, not a fault) and resumes only on Start.
    if (!_domainLive(unit.path) || (unit.path == 'StationA' && _doorOpen)) {
      unit.running = false;
      return;
    }
    if (unit.runStyle == RunStyle.holdToRun && _tick > unit.holdUntil) return;
    final single = unit.runStyle == RunStyle.singleStep;
    final before = chain.currentStep?.stepNo;
    final cycleEnded = chain.advance(SimTour.tick,
        mayComplete: !single || unit.stepGranted,
        stopAtCycleEnd: unit.stopRequested);
    if (single && chain.currentStep?.stepNo != before) unit.stepGranted = false;
    if (chain.finished ||
        (cycleEnded && unit.stopRequested) ||
        !chain.running) {
      unit.running = false;
      unit.stopRequested = false;
    }
  }

  void _animate() {
    final a = _units['StationA']!;
    final chain = a.chain;
    final step = chain?.currentStep?.stepNo;
    final elapsed = chain?.currentElapsed ?? Duration.zero;
    double frac(int ms) => (elapsed.inMilliseconds / ms).clamp(0.0, 1.0);
    if (a.mode == UnitMode.auto && a.running && step != null) {
      switch (step) {
        case 40:
          final f = frac(1600);
          _cylAPos = 50 * f;
          _cylBPos = _cylBStuck ? math.min(12.4, 50 * f) : 50 * f;
        case 70:
          final f = 1 - frac(800);
          _cylAPos = 50 * f;
          _cylBPos = 50 * f;
        case 60:
          final f = frac(1600);
          final previous = _robotPos;
          _robotPos = 245.7 - 165 * math.sin(math.pi * f);
          _robotVel = (_robotPos - previous) / 0.25;
        default:
          _cylAPos = _cylATarget;
          _cylBPos = _cylBStuck ? _cylBPos : _cylBTarget;
      }
    } else {
      // Outside a running AUTO cycle a cylinder moves at its own pace toward
      // where it was last sent: 50 mm in about a second.
      double approach(double pos, double target) => (target - pos).abs() <= 12.5
          ? target
          : pos + 12.5 * (target - pos).sign;
      _cylAPos = approach(_cylAPos, _cylATarget);
      if (!_cylBStuck) _cylBPos = approach(_cylBPos, _cylBTarget);
    }
    if (step != 60) _robotVel = 0;
    if (_tick <= _jogUntil) {
      _robotPos = (_robotPos + 2 * _jogDir).clamp(0.0, 400.0);
      _robotVel = 8 * _jogDir;
    }
  }

  // ==== events ====

  static String _rootOfPath(String path) {
    final dot = path.indexOf('.');
    return dot < 0 ? path : path.substring(0, dot);
  }

  void _raise(Severity severity, String description, String source,
      ResetClass resetClass,
      {int reason = 0, String ioTag = '', String ioAddress = ''}) {
    if (_seeding) return;
    if (_active
        .any((e) => e.sourcePath == source && e.description == description)) {
      return;
    }
    _active.add(_Event(severity, description, source, resetClass,
        comeAt: _now,
        reason: reason,
        ioTag: ioTag,
        ioAddress: ioAddress,
        synchronized: !source.startsWith('PackerC')));
  }

  /// The condition is gone: an AUTO_RESET event closes into the ring, a
  /// MANUAL_RESET one waits for the operator (§8.3(b)).
  void _clear(String source, String description) {
    for (final e in List.of(_active)) {
      if (e.sourcePath != source || e.description != description) continue;
      if (e.resetClass == ResetClass.manualReset) {
        e.state = AlarmState.waitReset;
      } else {
        _close(e);
      }
    }
  }

  void _close(_Event e) {
    _active.remove(e);
    _shelved.remove(e.id);
    final ring = _rings[_rootOfPath(e.sourcePath)]!;
    final now = _now;
    ring.add(AlarmEvent(
        severity: e.severity,
        description: e.description,
        sourcePath: e.sourcePath,
        resetClass: e.resetClass,
        state: AlarmState.closed,
        comeAt: e.comeAt,
        goneAt: now,
        duration: now.difference(e.comeAt),
        reasonCode: e.reason,
        ioTag: e.ioTag,
        ioAddress: e.ioAddress,
        comeTimeSynchronized: e.synchronized,
        goneTimeSynchronized: e.synchronized));
    if (ring.length > _ringDepth) ring.removeAt(0);
  }

  List<AlarmEvent> _alarms(String path, {bool subtree = false}) => [
        for (final e in _active)
          if (e.sourcePath == path ||
              (subtree && e.sourcePath.startsWith('$path.')))
            AlarmEvent(
                severity: e.severity,
                description: e.description,
                sourcePath: e.sourcePath,
                resetClass: e.resetClass,
                state: e.state,
                comeAt: e.comeAt,
                reasonCode: e.reason,
                ioTag: e.ioTag,
                ioAddress: e.ioAddress,
                shelved: _shelved.contains(e.id),
                comeTimeSynchronized: e.synchronized),
      ];

  bool _blocking(String root) => _active.any((e) =>
      _rootOfPath(e.sourcePath) == root &&
      e.resetClass == ResetClass.manualReset);

  void _audit(String what, String who) {
    // §8.3: operator actions are logged events (audit trail); come+gone ->
    // they land in the ring of the root they acted on.
    final ring = _rings[
        _rings.containsKey(_rootOfPath(who)) ? _rootOfPath(who) : 'StationA']!;
    ring.add(AlarmEvent(
        severity: Severity.low,
        description: '$what: $who',
        sourcePath: 'Access',
        resetClass: ResetClass.autoReset,
        state: AlarmState.closed,
        comeAt: _now,
        goneAt: _now,
        duration: Duration.zero));
    if (ring.length > _ringDepth) ring.removeAt(0);
    _publish();
  }

  // ==== derived state ====

  _Domain? _domainOf(String unitPath) {
    final root = _rootOfPath(unitPath);
    for (final d in _domains.values) {
      if (d.members.contains(root)) return d;
    }
    return null;
  }

  /// The Unit that owns [path]: the deepest Unit on the path (§3.4).
  _Unit? _owningUnit(String path) {
    var p = path;
    while (true) {
      final unit = _units[p];
      if (unit != null) return unit;
      final dot = p.lastIndexOf('.');
      if (dot < 0) return null;
      p = p.substring(0, dot);
    }
  }

  AccessSession _accessFor(String path) =>
      _access[_rootOfPath(path)] ?? const AccessSession();

  void _setAccess(String path, AccessSession value) {
    final root = _rootOfPath(path);
    if (!_access.containsKey(root)) return;
    _access[root] = value;
    _publish();
  }

  /// A §3.12 derived flag, with the moment it last CHANGED.
  StateFlag _flag(String key, bool value, {bool stale = false}) {
    final prior = _flags[key];
    if (prior == null || prior.$1 != value) {
      _flags[key] = (
        value,
        prior == null ? _now.subtract(const Duration(minutes: 47)) : _now
      );
    }
    return StateFlag(
        key: key,
        value: stale ? false : value,
        since: stale ? null : _flags[key]!.$2,
        stale: stale);
  }

  OeeSnapshot _oee(_Unit unit) {
    final total = unit.good + unit.nok + unit.rework;
    final quality = total == 0 ? 0.0 : unit.good / total;
    final availability =
        unit.path == 'StationA' && (_jamFault || _blocking('StationA'))
            ? 0.71
            : 0.93;
    const performance = 0.88;
    return OeeSnapshot(
      availability: availability,
      availValid: true,
      performance: performance,
      perfValid: true,
      quality: quality,
      qualValid: total > 0,
      oee: availability * performance * (total > 0 ? quality : 1),
      oeeValid: true,
      trend: List.of(unit.oeeTrend),
    );
  }

  ExecState _unitState(_Unit unit) {
    if (unit.path == 'StationA' && (_jamFault || _blocking('StationA'))) {
      return ExecState.error;
    }
    if (unit.running) return ExecState.busy;
    if ((unit.mode == UnitMode.home || unit.mode == UnitMode.changeover) &&
        (unit.chain?.finished ?? false)) {
      return ExecState.done;
    }
    return ExecState.ready;
  }

  // ==== §8.5.2 shifts ====

  int _lineInt(String key) => int.tryParse(_line[key] ?? '') ?? -1;

  /// The weekly-calendar interval [utc] falls in: (index, start, end) in UTC.
  /// Index 0 is an unscheduled interval between shifts.
  ({int index, DateTime start, DateTime end}) _shiftAt(DateTime utc) {
    final offset = Duration(minutes: _lineInt('line.shift.utcOffsetMin'));
    final local = utc.toUtc().add(offset); // line wall clock, kept UTC-flagged
    final midnight = DateTime.utc(local.year, local.month, local.day);
    ({int index, DateTime start, DateTime end})? current;
    DateTime? next, previousEnd;
    for (var day = -2; day <= 7; day++) {
      final dayStart = midnight.add(Duration(days: day));
      final weekdayBit = 1 << (dayStart.weekday - 1); // Monday bit 0
      for (var n = 1; n <= _shiftRows; n++) {
        final start = _lineInt('line.shift.$n.startMin');
        final minutes = _lineInt('line.shift.$n.durationMin');
        final days = _lineInt('line.shift.$n.activeDays');
        if (start < 0 || minutes <= 0 || days < 0 || days & weekdayBit == 0) {
          continue;
        }
        final s = dayStart.add(Duration(minutes: start));
        final e = s.add(Duration(minutes: minutes));
        if (!local.isBefore(s) && local.isBefore(e)) {
          current = (index: n, start: s, end: e);
        }
        if (s.isAfter(local) && (next == null || s.isBefore(next))) next = s;
        if (!e.isAfter(local) &&
            (previousEnd == null || e.isAfter(previousEnd))) {
          previousEnd = e;
        }
      }
    }
    final result = current ??
        (
          index: 0,
          start: previousEnd ?? local.subtract(const Duration(hours: 1)),
          end: next ?? local.add(const Duration(days: 1)),
        );
    return (
      index: result.index,
      start: result.start.subtract(offset),
      end: result.end.subtract(offset),
    );
  }

  ShiftFacet _shift(_Unit unit) {
    final now = _now.toUtc();
    final current = _shiftAt(now);
    int? target(int index) => index == 0
        ? null
        : int.tryParse(_line['line.shift.$index.productionTarget'] ?? '');
    final history = <ShiftRecord>[];
    var cursor = current.start.subtract(const Duration(minutes: 1));
    for (var i = 0; i < 3; i++) {
      final s = _shiftAt(cursor);
      final goal = target(s.index) ?? 0;
      final good = goal == 0 ? 120 + i * 13 : goal * (93 + (i * 5) % 9) ~/ 100;
      history.add(ShiftRecord(
        shiftIndex: s.index,
        productionTarget: s.index == 0 ? null : goal,
        startAt: s.start,
        endAt: s.end,
        good: good,
        nok: 6 + i * 3,
        rework: 4 + i,
        oee: 0.81 - i * 0.03,
        oeeValid: true,
        availability: 0.92 - i * 0.02,
        performance: 0.89,
        quality: 0.988,
        availValid: true,
        perfValid: true,
        qualValid: true,
        manualReset: i == 2,
        runTime: Duration(minutes: 412 - i * 9),
        downTime: Duration(minutes: 31 + i * 7),
        idleTime: Duration(minutes: 37 + i * 2),
      ));
      cursor = s.start.subtract(const Duration(minutes: 1));
    }
    return ShiftFacet(
      currentShift: current.index,
      productionTarget: target(current.index),
      startedAt: current.start,
      endsAt: current.end,
      history: history,
    );
  }

  // ==== configuration ====

  /// The data class a value belongs to and the levels the PLC would compute.
  CfgField _classed(CfgField f, String classId, AccessSession session) {
    final policy = _classes[classId]!;
    final readable = session.level.index >= policy.readLevel.index;
    return CfgField(f.name, f.kind, f.type, readable ? f.value : '',
        unit: f.unit,
        labelKey: f.labelKey,
        writeKey: f.writeKey,
        writeRevision: f.writeRevision,
        writable: f.writable,
        minimum: f.minimum,
        maximum: f.maximum,
        unitCode: f.unitCode,
        classId: classId,
        readLevel: policy.readLevel,
        writeLevel: policy.writeLevel,
        readable: readable);
  }

  /// §3.8e - the line's values as [root] presents them: writable on the
  /// owner, a read-only mirror everywhere else.
  List<CfgField> _lineFields({required bool owner}) {
    CfgField number(
            String key, String label, EngUnit unit, double min, double max) =>
        CfgField(key, CfgKind.lineCfg, CfgType.number, _line[key]!,
            labelKey: label,
            writeKey: key,
            writeRevision: 1,
            writable: owner,
            minimum: min,
            maximum: max,
            unitCode: unit,
            // As FB_LineDataV3 registers the calendar: everyone reads it, an
            // ENGINEER changes it.
            readLevel: AccessLevel.none,
            writeLevel: AccessLevel.engineer);
    return [
      number('line.shift.utcOffsetMin', 'std.config.shiftUtcOffset',
          EngUnit.minute, -840, 840),
      for (var n = 1; n <= _shiftRows; n++) ...[
        number('line.shift.$n.startMin', 'std.config.shift.$n.start',
            EngUnit.minute, -1, 1439),
        number('line.shift.$n.durationMin', 'std.config.shift.$n.duration',
            EngUnit.minute, 1, 1440),
        number('line.shift.$n.activeDays', 'std.config.shift.$n.days',
            EngUnit.none, 0, 127),
        number('line.shift.$n.productionTarget', 'std.config.shift.$n.target',
            EngUnit.piece, 0, 100000),
      ],
      number('line.taktMs', 'project.config.lineTakt', EngUnit.millisecond,
          1000, 60000),
    ];
  }

  CfgField _value(
          String key, String name, CfgKind kind, CfgType type, String label,
          {EngUnit unit = EngUnit.none,
          double? min,
          double? max,
          List<String> choices = const [],
          String choiceLabels = ''}) =>
      CfgField(name, kind, type, _cfg[key]!,
          labelKey: label,
          writeKey: key,
          writeRevision: 1,
          writable: true,
          minimum: min,
          maximum: max,
          unitCode: unit,
          enumDomain: choices,
          enumLabelKey: choiceLabels);

  /// The editable values [path] publishes (§3.8a), for this session.
  List<CfgField> _configFor(String path, {String? model}) {
    final session = _accessFor(path);
    switch (path) {
      case 'StationA':
        return [
          _value('sim.station.mes.endpointIp', 'MES endpoint IP',
              CfgKind.stationCfg, CfgType.text, 'project.config.mesEndpointIp'),
          _value('sim.station.mes.port', 'MES port', CfgKind.stationCfg,
              CfgType.number, 'project.config.mesPort',
              min: 1, max: 65535),
          CfgField('Clamp settle time', CfgKind.parCfg, CfgType.time,
              _settle(model ?? _modelA),
              modelScoped: true,
              unit: 'ms',
              unitCode: EngUnit.millisecond,
              labelKey: 'project.config.clampSettleTime',
              writeKey: 'sim.recipe.clamp.settleMs',
              writeRevision: 1,
              writable: true,
              minimum: 0,
              maximum: 60000),
          // A flag and a choice, edited as a checkbox and a translated dropdown
          // - the shapes Core 0.14 publishes (UnitCode NONE: no unit shown).
          _value(
              'sim.station.requireTwoHandStart',
              'Require two-hand start',
              CfgKind.stationCfg,
              CfgType.boolean,
              'project.config.pressRequireTwoHandStart',
              choices: const ['TRUE', 'FALSE']),
          _value('sim.station.modeShield', 'Mode-switch protection',
              CfgKind.stationCfg, CfgType.number, 'std.enum.modeSwitchShield',
              choices: const ['0', '1', '2'],
              choiceLabels: 'std.enum.modeSwitchShield'),
          // §3.8d - two declared data classes: quality values are visible to an
          // operator, the MES integration only from technician up.
          _classed(
              _value(
                  'sim.station.inspectionThreshold',
                  'Inspection score threshold',
                  CfgKind.stationCfg,
                  CfgType.number,
                  'project.config.inspectionThreshold',
                  unit: EngUnit.percent,
                  min: 50,
                  max: 100),
              'quality',
              session),
          _classed(
              _value(
                  'sim.station.rejectBinCapacity',
                  'Reject bin capacity',
                  CfgKind.stationCfg,
                  CfgType.number,
                  'project.config.rejectBinCapacity',
                  unit: EngUnit.piece,
                  min: 1,
                  max: 200),
              'quality',
              session),
          _classed(
              _value(
                  'sim.station.mesHeartbeat',
                  'MES heartbeat interval',
                  CfgKind.stationCfg,
                  CfgType.number,
                  'project.config.mesHeartbeat',
                  unit: EngUnit.second,
                  min: 1,
                  max: 60),
              'integration',
              session),
          ..._lineFields(owner: true),
        ];
      case 'StationA.ClampStation':
        return [
          _value('sim.clamp.pressureBar', 'Clamp pressure set point',
              CfgKind.parCfg, CfgType.number, 'project.config.clampPressure',
              unit: EngUnit.bar, min: 2, max: 8),
        ];
      case 'StationA.ClampStation.CylB':
        return [
          _value('sim.cylB.extendLimitMs', 'Extend time limit',
              CfgKind.stationCfg, CfgType.time, 'project.config.extendTimeout',
              unit: EngUnit.millisecond, min: 500, max: 10000),
        ];
      case 'StationA.Camera':
        return [
          _value('sim.camera.program', 'Inspection program', CfgKind.parCfg,
              CfgType.number, 'project.config.inspectionProgram',
              min: 1, max: 32),
        ];
      case 'ConveyorB':
        return [
          _value('sim.conveyor.beltSpeed', 'Belt speed', CfgKind.stationCfg,
              CfgType.number, 'project.config.beltSpeed',
              unit: EngUnit.meterPerMinute, min: 5, max: 40),
          ..._lineFields(owner: false),
        ];
      case 'PackerC':
        return [
          _value('sim.packer.cartonsPerLayer', 'Cartons per layer',
              CfgKind.parCfg, CfgType.number, 'project.config.cartonsPerLayer',
              unit: EngUnit.piece, min: 1, max: 48),
          _value(
              'sim.packer.glueTemperature',
              'Glue temperature',
              CfgKind.stationCfg,
              CfgType.number,
              'project.config.glueTemperature',
              unit: EngUnit.degreeCelsius,
              min: 120,
              max: 190),
        ];
      case 'PackerC.Labeler':
        return [
          _value('sim.labeler.template', 'Label template', CfgKind.parCfg,
              CfgType.text, 'project.config.labelTemplate'),
        ];
      default:
        return const [];
    }
  }

  // ==== publication ====

  void _publish() {
    if (_ctrl.isClosed) return;
    _ctrl.add([_stationA(), _conveyorB(), _packerC()]);
  }

  ConfigPersistStatus _persistStatus(String root,
      {ConfigStoreKind kind = ConfigStoreKind.localRetain, bool store = true}) {
    final since = _persistPendingSince;
    final settled =
        since != null && _now.toUtc().difference(since) >= _persistWindow;
    if (settled) _persistPendingSince = null;
    final lostHere = restoreLost &&
        (restoreLostPath.isEmpty
            ? root == 'StationA'
            : _rootOfPath(restoreLostPath) == root);
    return ConfigPersistStatus(
      pending: !settled && since != null,
      failed: persistFailed,
      window: _persistWindow,
      pendingSince: settled ? null : since,
      storePresent: store,
      storeKind: kind,
      restoreLost: lostHere,
      restoreAcknowledged: _restoreAcknowledged,
      lostPath: lostHere ? restoreLostPath : '',
      restorePolicy: ConfigRestorePolicy.defaultsAndAnnunciate,
    );
  }

  List<CommandTiming> _timingsOf(String path) => [
        for (final t in (_timings[path] ?? const <int, _Timing>{}).values)
          t.publish(),
      ];

  ExecState _cmdState(String path, ExecState otherwise) =>
      (_commandBusyUntil[path] ?? -1) >= _tick ? ExecState.busy : otherwise;

  ControlPowerFacet _power(String unitPath) {
    final domain = _domainOf(unitPath)!;
    final energizing = domain.energizingUntil >= 0;
    final safe = !(unitPath == 'StationA' || unitPath == 'ConveyorB') ||
        (!_doorOpen && !_safetyResetRequired);
    PowerGroupStatus group(
            String name, PowerGroupKind kind, FieldbusLossReaction reaction) =>
        PowerGroupStatus(
            name: name,
            kind: kind,
            state: energizing
                ? PowerState.energizing
                : domain.on && !domain.rearm
                    ? PowerState.on
                    : domain.rearm
                        ? PowerState.tripped
                        : PowerState.off,
            requestedOn: domain.requested,
            powerOn: domain.on && !domain.rearm,
            safetyPermit: safe,
            rearmRequired: domain.rearm,
            diagnostic: domain.rearm ? 'project.status.rearmRequired' : '',
            fieldbusLossReaction: reaction);
    return ControlPowerFacet(
      requestedOn: domain.requested,
      controlOn: domain.on && !domain.rearm,
      transitioning: energizing,
      rearmRequired: domain.rearm,
      diagnostic: domain.rearm ? 'project.status.rearmRequired' : '',
      groups: domain.id == 'Cell1'
          ? [
              group('ValveZoneA', PowerGroupKind.valveZone,
                  FieldbusLossReaction.controlOff),
              group('ValveZoneB', PowerGroupKind.valveZone,
                  FieldbusLossReaction.powerGroupOff),
              group('RobotDrives', PowerGroupKind.driveGroup,
                  FieldbusLossReaction.stopUnit),
            ]
          : [
              group('PackerDrives', PowerGroupKind.driveGroup,
                  FieldbusLossReaction.stopUnit),
              group('GlueHeater', PowerGroupKind.heater,
                  FieldbusLossReaction.alarmOnly),
            ],
    );
  }

  String _messageA(_Unit unit, SimChain chain) {
    if (_jamFault && _cylBStuck) return 'project.reason.cylinderTimeout';
    if (_blocking('StationA')) return 'project.status.awaitingReset';
    if (_doorOpen) return 'project.status.safetyDemand';
    if (_safetyResetRequired) return 'project.status.safetyResetRequired';
    if (!_domainLive('StationA')) return 'project.status.rearmRequired';
    if (_decision != null) return 'project.status.decisionPending';
    switch (unit.mode) {
      case UnitMode.manual:
        return 'project.status.manualReady';
      case UnitMode.home:
        return unit.running
            ? 'project.status.homing'
            : (chain.finished
                ? 'project.status.homed'
                : 'project.status.stopped');
      case UnitMode.changeover:
        return unit.running
            ? 'project.status.changeover'
            : (chain.finished
                ? 'project.status.changeoverDone'
                : 'project.status.stopped');
      default:
    }
    if (!unit.running) return 'project.status.stopped';
    if (unit.stopRequested) return 'project.status.stopping';
    if (chain.currentStep?.stepNo == 40 && chain.currentTimedOut) {
      return 'project.status.waitingClamp'; // a STALL: pending, not a fault
    }
    if (chain.currentStep?.stepNo == 10 && _airDip) {
      return 'project.status.starved';
    }
    return 'project.status.producing';
  }

  ModuleNode _stationA() {
    final unit = _units['StationA']!;
    final chain = unit.chain!;
    final auto = unit.chains[UnitMode.auto]!;
    final session = _access['StationA']!;
    final step = chain.currentStep?.stepNo;
    final blocking = _blocking('StationA');
    final faulted = _jamFault || blocking;
    final testing = _tick <= _lampTestUntil;
    final towerHorn = _jamTick >= 0 &&
        _tick - _jamTick < _ticksOf(const Duration(seconds: 5));
    final machineState = faulted
        ? MachineState.down
        : unit.mode == UnitMode.changeover
            ? MachineState.changeover
            : !unit.running
                ? (unit.mode == UnitMode.auto
                    ? MachineState.stopped
                    : MachineState.idle)
                : step == 10 && _airDip
                    ? MachineState.starved
                    : MachineState.producing;
    final packML = faulted
        ? PackMLState.held
        : unit.running
            ? (unit.stopRequested
                ? PackMLState.completing
                : PackMLState.execute)
            : chain.finished
                ? PackMLState.complete
                : unit.mode == UnitMode.auto
                    ? PackMLState.stopped
                    : PackMLState.idle;
    final cylBEvents = _alarms('StationA.ClampStation.CylB');
    final partInStation = _partPresent && unit.mode == UnitMode.auto;
    return ModuleNode(
      path: 'StationA',
      name: 'StationA',
      typeKey: 'project.moduleType.clampStation',
      type: ModuleType.unit,
      displayNameKey: 'project.module.StationA.name',
      descriptionKey: 'project.module.StationA.description',
      controlDomainId: 'Cell1',
      controlDomainName: _domains['Cell1']!.name,
      controlDomainMembers: _domains['Cell1']!.members,
      state: _unitState(unit),
      faultActive: _jamFault && _cylBStuck,
      message: _messageA(unit, chain),
      diagnosticIoTag: _jamFault ? '=A1+S1-B41' : '',
      diagnosticIoAddress: _jamFault ? 'EL1008 Ch1' : '',
      diagnosticSince: _jamFault
          ? _active
              .where((e) => e.sourcePath == 'StationA.ClampStation.CylB')
              .firstOrNull
              ?.comeAt
          : null,
      modelCode: _modelA,
      availableModels: List.unmodifiable(_stationAModels),
      modelCapacity: 8,
      exportCurrentConfigEnabled: true,
      modeActive: unit.mode,
      goodCount: unit.good,
      nokCount: unit.nok,
      reworkCount: unit.rework,
      blocking: blocking,
      activeEvents: _alarms('StationA', subtree: true),
      ringEvents: List.of(_rings['StationA']!.reversed),
      access: _sessionWithClasses(session),
      configPersist: _persistStatus('StationA'),
      safety: SafetyFacet(
        allSafe: !_doorOpen && !_safetyResetRequired,
        demandActive: _doorOpen,
        resetRequired: _safetyResetRequired,
        mutingActive: _within(SimTour.mutingFrom, SimTour.mutingUntil),
        stopRequested: _doorOpen,
        devices: [
          const SafetyDeviceStatus(
              name: 'EStopPanel',
              kind: SafetyDeviceKind.estop,
              state: SafetyState.ready,
              ready: true,
              safeStateActive: false,
              affectedPowerMask: 7,
              description: 'project.safety.estop'),
          SafetyDeviceStatus(
              name: 'DoorNorth',
              kind: SafetyDeviceKind.guardDoor,
              state: _doorOpen
                  ? SafetyState.demand
                  : _safetyResetRequired
                      ? SafetyState.resetRequired
                      : SafetyState.ready,
              ready: !_doorOpen && !_safetyResetRequired,
              demandActive: _doorOpen,
              resetRequired: _safetyResetRequired,
              safeStateActive: _doorOpen || _safetyResetRequired,
              affectedPowerMask: 1,
              description: 'project.safety.doorNorth'),
          SafetyDeviceStatus(
              name: 'LightCurtainInfeed',
              kind: SafetyDeviceKind.lightCurtain,
              state: SafetyState.ready,
              ready: true,
              mutingActive: _within(SimTour.mutingFrom, SimTour.mutingUntil),
              safeStateActive: false,
              affectedPowerMask: 2,
              description: 'project.safety.lightCurtain'),
          const SafetyDeviceStatus(
              name: 'ValveExhaust',
              kind: SafetyDeviceKind.safetyValve,
              state: SafetyState.ready,
              ready: true,
              safeStateActive: false,
              affectedPowerMask: 3,
              description: 'project.safety.safeValve'),
        ],
      ),
      controlPower: _power('StationA'),
      nameplate: const Nameplate(
          productUri: 'https://fraktal.example/StationA/SN-2024-0042',
          manufacturer: 'Fraktal Machinery GmbH',
          designation: 'Clamp & Inspect Station',
          serial: 'SN-2024-0042',
          year: '2024',
          hwVersion: 'HW 2.1',
          fwVersion: 'TC3 4026.14',
          swVersion: 'Fraktal Core 0.25',
          orderCode: 'FRK-CS-200',
          docUrl: 'https://fraktal.example/docs/FRK-CS-200'),
      running: unit.running,
      stopPending: unit.stopRequested,
      runStyle: unit.runStyle,
      supportedModes: unit.modes,
      supportedRunStyles: unit.mode == UnitMode.auto
          ? const [RunStyle.continuous, RunStyle.singleStep, RunStyle.holdToRun]
          : const [RunStyle.continuous],
      modePolicy: const {
        UnitMode.auto:
            ModePolicy(ModeSwitchShield.confirm, ModeSwitchStyle.graceful),
        UnitMode.changeover: ModePolicy(
            ModeSwitchShield.blockedWhileRunning, ModeSwitchStyle.graceful),
        UnitMode.home: ModePolicy(
            ModeSwitchShield.interruptible, ModeSwitchStyle.immediate),
        UnitMode.manual: ModePolicy(
            ModeSwitchShield.interruptible, ModeSwitchStyle.graceful),
      },
      alarmMeta: _alarmMeta,
      oee: _oee(unit),
      shift: _shift(unit),
      packML: packML,
      cycle: auto.lastProfile,
      cycleHistory: auto.history,
      lastCycleTime: auto.lastCycleTime,
      minCycleTime: auto.bestCycleTime,
      machineState: machineState,
      step: chain.currentInfo(
        conds: step == 40 && (_cylBStuck || chain.currentTimedOut)
            ? [
                CondInfo('project.cond.cylBExtended', !_cylBStuck),
                CondInfo('project.cond.areaSafe', !_doorOpen),
              ]
            : const [],
        starved: step == 10 && _airDip,
      ),
      stepStats: auto.stats,
      decision: _decision,
      systemHealth: const SystemHealthFacet(
        healthy: true,
        taskAvailable: true,
        taskCycleUs: 1000,
        taskJitterUs: 28,
        controllerAvailable: true,
        cpuLoadPct: 23.8,
        memoryAvailableMb: 2048,
        ipcAvailable: true,
        ipcTemperatureC: 46.5,
        fanHealthy: true,
        storageHealthPct: 97,
        fieldbusAvailable: true,
        fieldbusMasterHealthy: true,
        dcAvailable: true,
        dcSynchronized: true,
        time: TimeQualityFacet(
            available: true, synchronized: true, source: 'PTP', offsetUs: 12),
      ),
      signalTower: SignalTowerFacet(
        red: testing || faulted,
        amber:
            testing || (!faulted && !unit.running) || !_domainLive('StationA'),
        green: testing || (unit.running && !faulted),
        blue: testing || _decision != null,
        white: testing || _within(SimTour.mutingFrom, SimTour.mutingUntil),
        horn: testing || towerHorn,
        testActive: testing,
      ),
      config: _configFor('StationA'),
      stateFlags: [
        _flag('project.state.homed', true),
        _flag('project.state.guardClosed', !_doorOpen),
        _flag('project.state.airOk', !_airDip),
        _flag('project.state.partPresent', partInStation),
        _flag('project.state.clamped', _clamped),
      ],
      sequenceViewEnabled: true,
      sequenceSteps: chain.rows,
      sequenceStepCount: chain.rows.length,
      currentStepElapsed: chain.currentElapsed,
      currentStepTimedOut: chain.currentTimedOut,
      publishedValues: {
        'OutImm/PartsPerHour': auto.lastCycleTime == Duration.zero
            ? 0
            : (3600000 / auto.lastCycleTime.inMilliseconds).round(),
        'OutImm/CycleTimeS': double.parse(
            (auto.lastCycleTime.inMilliseconds / 1000).toStringAsFixed(1)),
        'OutImm/ClampPressureBar': _clamped ? 5.6 : 0.4,
        'OutImm/SupplyPressureBar': 6.1,
        'OutImm/DoorClosed': !_doorOpen,
        'OutImm/ClampClosed': _clamped,
        'OutImm/PartPresent': partInStation,
        'OutImm/AirOk': !_airDip,
      },
      children: [
        ModuleNode(
          path: 'StationA.Separator1',
          name: 'Separator1',
          typeKey: 'std.moduleType.separator',
          type: ModuleType.controlModule,
          state: _cmdState('StationA.Separator1',
              step == 30 && unit.running ? ExecState.busy : ExecState.done),
          commands: const [
            CommandInfo(1, 'project.command.extend'),
            CommandInfo(2, 'project.command.retract'),
          ],
          commandTimings: _timingsOf('StationA.Separator1'),
        ),
        ModuleNode(
          path: 'StationA.ClampStation',
          name: 'ClampStation',
          typeKey: 'std.moduleType.clamp',
          type: ModuleType.equipmentModule,
          state: _jamFault
              ? ExecState.error
              : _cmdState(
                  'StationA.ClampStation',
                  (step == 40 || step == 70) && unit.running
                      ? ExecState.busy
                      : ExecState.done),
          faultActive: _jamFault && _cylBStuck,
          message:
              _jamFault && _cylBStuck ? 'project.reason.cylinderTimeout' : '',
          commands: const [
            CommandInfo(1, 'project.command.clamp'),
            CommandInfo(2, 'project.command.unclamp'),
          ],
          commandTimings: _timingsOf('StationA.ClampStation'),
          config: _configFor('StationA.ClampStation'),
          children: [
            ModuleNode(
                path: 'StationA.ClampStation.CylA',
                name: 'CylA',
                typeKey: 'std.moduleType.cylinder',
                type: ModuleType.controlModule,
                state: _cmdState('StationA.ClampStation.CylA', ExecState.done),
                motion: MotionFacet(
                    actualPosition: _round(_cylAPos),
                    targetPosition: _cylATarget,
                    moving: (_cylAPos - _cylATarget).abs() > 0.5,
                    unit: 'mm'),
                commands: const [
                  CommandInfo(1, 'project.command.toHome'),
                  CommandInfo(2, 'project.command.toWork')
                ]),
            ModuleNode(
              path: 'StationA.ClampStation.CylB',
              name: 'CylB',
              typeKey: 'std.moduleType.cylinder',
              type: ModuleType.controlModule,
              state: _jamFault
                  ? ExecState.error
                  : _cmdState('StationA.ClampStation.CylB', ExecState.done),
              faultActive: _jamFault && _cylBStuck,
              message: _jamFault && _cylBStuck
                  ? 'project.reason.cylinderTimeout'
                  : '',
              diagnosticIoTag: _jamFault ? '=A1+S1-B41' : '',
              diagnosticIoAddress: _jamFault ? 'EL1008 Ch1' : '',
              activeEvents: cylBEvents,
              motion: MotionFacet(
                  actualPosition: _round(_cylBPos),
                  targetPosition: _cylBTarget,
                  moving: !_cylBStuck && (_cylBPos - _cylBTarget).abs() > 0.5,
                  homed: true,
                  unit: 'mm'), // Annex G
              commands: const [
                CommandInfo(1, 'project.command.toHome'),
                CommandInfo(2, 'project.command.toWork')
              ], // §7.6.1 catalog
              config: _configFor('StationA.ClampStation.CylB'),
              nameplate: const Nameplate(
                  manufacturer: 'PneuParts AG',
                  designation: 'Duplex cylinder DX-50',
                  serial: 'PX-88121',
                  year: '2023',
                  hwVersion: 'Rev C',
                  docUrl: 'https://pneuparts.example/dx-50'),
            ),
          ],
        ),
        ModuleNode(
          path: 'StationA.Robot',
          name: 'Robot',
          typeKey: 'std.moduleType.robot',
          type: ModuleType.controlModule,
          state: _cmdState('StationA.Robot',
              step == 60 && unit.running ? ExecState.busy : ExecState.done),
          message: _toolWorn ? 'project.reason.toolChange' : '',
          activeEvents: _alarms('StationA.Robot'),
          link: LinkFacet(linked: true, lastSeen: _now), // Annex D
          motion: MotionFacet(
              actualPosition: _round(_robotPos),
              actualVelocity: _round(_robotVel),
              targetPosition:
                  step == 60 && unit.running ? 80 : _round(_robotPos),
              moving: _robotVel.abs() > 0.1,
              unit: 'mm',
              homed: true), // Annex I
          part: PartFacet(
              uid: 'SN-$_partSerial',
              present: true,
              verdict: _verdict,
              reason: _verdictReason,
              records: [
                // Annex E
                MeasRecord('Press force', 12.3 + (_partSerial % 5) * 0.1, 10.0,
                    15.0, 12.5, 'kN', true),
                MeasRecord('Depth', _verdict == Verdict.nok ? 5.14 : 4.98, 4.90,
                    5.10, 5.00, 'mm', _verdict != Verdict.nok),
              ]),
          commands: const [
            CommandInfo(1, 'project.command.robotHome'),
            CommandInfo(10, 'project.command.jogPlus',
                style: CommandStyle.held),
            CommandInfo(11, 'project.command.jogMinus',
                style: CommandStyle.held),
          ],
          commandTimings: _timingsOf('StationA.Robot'),
          nameplate: const Nameplate(
              manufacturer: 'Articula Robotics',
              designation: 'SCARA AR-6 600 mm',
              serial: 'AR6-23-1187',
              year: '2023',
              fwVersion: 'RC 5.2.1',
              orderCode: 'AR6-600-S'),
        ),
        ModuleNode(
          path: 'StationA.Camera',
          name: 'Camera',
          typeKey: 'std.moduleType.visionCamera',
          type: ModuleType.controlModule,
          state: _cmdState('StationA.Camera', ExecState.done),
          activeEvents: _alarms('StationA.Camera'),
          link: LinkFacet(linked: true, lastSeen: _now),
          commands: const [
            CommandInfo(1, 'project.command.triggerInspection'),
          ],
          commandTimings: _timingsOf('StationA.Camera'),
          config: _configFor('StationA.Camera'),
          nameplate: const Nameplate(
              manufacturer: 'Lumen Vision',
              designation: 'Smart camera LV-5 mono',
              serial: 'LV5-77810',
              fwVersion: '4.8.0'),
          publishedValues: {
            'OutCmd/JudgeOk': _judgeOk,
            'OutCmd/ResultData': _inspectionResult,
            'OutImm/InspectionCount': _inspections,
          },
        ),
        ModuleNode(
          path: 'StationA.CodeReader',
          name: 'CodeReader',
          typeKey: 'std.moduleType.codeReader',
          type: ModuleType.controlModule,
          state: _cmdState('StationA.CodeReader', ExecState.done),
          activeEvents: _alarms('StationA.CodeReader'),
          link: LinkFacet(linked: true, lastSeen: _now),
          commands: const [CommandInfo(1, 'project.command.triggerRead')],
          commandTimings: _timingsOf('StationA.CodeReader'),
          publishedValues: {
            'OutCmd/Code': _lastCode,
            'OutCmd/NoRead': false,
            'OutCmd/MatchOk': true,
            'OutImm/TriggerCount': _codeTriggers,
            'OutImm/GoodReads': _codeGood,
            'OutImm/NoReads': _codeNoRead,
          },
        ),
        ModuleNode(
          path: 'StationA.RfidReader',
          name: 'RfidReader',
          typeKey: 'project.moduleType.rfidReader',
          type: ModuleType.controlModule,
          state: _cmdState('StationA.RfidReader', ExecState.done),
          commands: const [CommandInfo(1, 'project.command.readTag')],
          commandTimings: _timingsOf('StationA.RfidReader'),
          publishedValues: {
            'OutImm/LastUid': _lastUid,
            'OutImm/TagPresent': _tagPresent,
            'OutImm/ReadQuality': 96,
          },
        ),
      ],
    );
  }

  ModuleNode _conveyorB() {
    final unit = _units['ConveyorB']!;
    final chain = unit.chain!;
    final auto = unit.chains[UnitMode.auto]!;
    final airEvents = _alarms('ConveyorB.AirMonitor');
    final step = chain.currentStep?.stepNo;
    return ModuleNode(
      path: 'ConveyorB',
      name: 'ConveyorB',
      typeKey: 'project.moduleType.transferConveyor',
      type: ModuleType.unit,
      displayNameKey: 'project.module.ConveyorB.name',
      descriptionKey: 'project.module.ConveyorB.description',
      controlDomainId: 'Cell1',
      controlDomainName: _domains['Cell1']!.name,
      controlDomainMembers: _domains['Cell1']!.members,
      state: _unitState(unit),
      message: _airDip
          ? 'project.reason.airPressureLow'
          : _linkLost
              ? 'project.status.heartbeatLost'
              : unit.running
                  ? 'project.status.transporting'
                  : unit.mode == UnitMode.manual
                      ? 'project.status.manualReady'
                      : 'project.status.stopped',
      modelCode: _modelB,
      modeActive: unit.mode,
      goodCount: unit.good,
      activeEvents: _alarms('ConveyorB', subtree: true),
      ringEvents: List.of(_rings['ConveyorB']!.reversed),
      access: _access['ConveyorB'],
      configPersist: _persistStatus('ConveyorB', store: false),
      controlPower: _power('ConveyorB'),
      running: unit.running,
      stopPending: unit.stopRequested,
      supportedModes: unit.modes,
      packML: unit.running ? PackMLState.execute : PackMLState.stopped,
      machineState: !unit.running
          ? MachineState.stopped
          : _airDip
              ? MachineState.starved
              : MachineState.producing,
      link: LinkFacet(
          linked: !_linkLost,
          lastSeen:
              _linkLost ? _now.subtract(const Duration(seconds: 3)) : _now,
          linkReason:
              _linkLost ? 'project.status.heartbeatLost' : ''), // Annex D
      step: chain.currentInfo(starved: step == 10 && _airDip),
      sequenceViewEnabled: true,
      sequenceSteps: chain.rows,
      sequenceStepCount: chain.rows.length,
      currentStepElapsed: chain.currentElapsed,
      currentStepTimedOut: chain.currentTimedOut,
      cycle: auto.lastProfile,
      cycleHistory: auto.history,
      lastCycleTime: auto.lastCycleTime,
      minCycleTime: auto.bestCycleTime,
      stepStats: auto.stats,
      oee: _oee(unit),
      shift: _shift(unit),
      alarmMeta: _alarmMeta,
      config: _configFor('ConveyorB'),
      stateFlags: [
        _flag('project.state.palletAtStop', _palletAtStop),
        // Annex D: the line controller is silent, so this cannot be computed.
        _flag('project.state.downstreamReady', true, stale: _linkLost),
      ],
      nameplate: const Nameplate(
          manufacturer: 'Fraktal Machinery GmbH',
          designation: 'Transfer conveyor TC-1200',
          serial: 'SN-2024-0043',
          year: '2024',
          swVersion: 'Fraktal Core 0.25'),
      publishedValues: {
        'OutImm/PalletAtStop': _palletAtStop,
        'OutImm/AirPressureBar': _airDip ? 3.9 : 6.2,
        'OutImm/BeltSpeed':
            double.tryParse(_cfg['sim.conveyor.beltSpeed']!) ?? 0,
      },
      children: [
        ModuleNode(
          path: 'ConveyorB.Infeed',
          name: 'Infeed',
          type: ModuleType.equipmentModule,
          state: step == 10 && unit.running ? ExecState.busy : ExecState.done,
          children: [
            ModuleNode(
                path: 'ConveyorB.Infeed.Stopper',
                name: 'Stopper',
                typeKey: 'std.moduleType.cylinder',
                type: ModuleType.controlModule,
                state: _cmdState('ConveyorB.Infeed.Stopper', ExecState.done),
                commands: const [
                  CommandInfo(1, 'project.command.open'),
                  CommandInfo(2, 'project.command.close'),
                ]),
          ],
        ),
        ModuleNode(
          path: 'ConveyorB.Lift',
          name: 'Lift',
          typeKey: 'project.moduleType.lift',
          type: ModuleType.equipmentModule,
          state: _cmdState(
              'ConveyorB.Lift',
              (step == 20 || step == 40) && unit.running
                  ? ExecState.busy
                  : ExecState.ready),
          commands: const [
            CommandInfo(1, 'project.command.raise'),
            CommandInfo(2, 'project.command.lower'),
          ],
          commandTimings: _timingsOf('ConveyorB.Lift'),
        ),
        ModuleNode(
          path: 'ConveyorB.AirMonitor',
          name: 'AirMonitor',
          typeKey: 'std.moduleType.airPressure',
          type: ModuleType.controlModule,
          state: ExecState.ready,
          message: _airDip ? 'project.reason.airPressureLow' : '',
          activeEvents: airEvents,
        ),
      ],
    );
  }

  ModuleNode _packerC() {
    final unit = _units['PackerC']!;
    final labeler = _units['PackerC.Labeler']!;
    final chain = unit.chain!;
    final auto = unit.chains[UnitMode.auto]!;
    final labelChain = labeler.chain!;
    const health = SystemHealthFacet(
      healthy: true,
      taskAvailable: true,
      taskCycleUs: 2000,
      taskJitterUs: 41,
      controllerAvailable: true,
      cpuLoadPct: 31.2,
      memoryAvailableMb: 1024,
      fieldbusAvailable: true,
      fieldbusMasterHealthy: true,
      // A measured, unsynchronized clock: the packer's controller has no time
      // source configured, so every timestamp it makes is marked untrusted.
      time: TimeQualityFacet(
          available: true, synchronized: false, source: 'LOCAL', offsetUs: 0),
    );
    return ModuleNode(
      path: 'PackerC',
      name: 'PackerC',
      typeKey: 'project.moduleType.casePacker',
      type: ModuleType.unit,
      displayNameKey: 'project.module.PackerC.name',
      descriptionKey: 'project.module.PackerC.description',
      controlDomainId: 'Cell2',
      controlDomainName: _domains['Cell2']!.name,
      controlDomainMembers: _domains['Cell2']!.members,
      state: _unitState(unit),
      message: unit.running
          ? 'project.status.packing'
          : unit.mode == UnitMode.manual
              ? 'project.status.manualReady'
              : 'project.status.stopped',
      diagnosticTimeSynchronized: false,
      modelCode: _modelC,
      modeActive: unit.mode,
      goodCount: unit.good,
      nokCount: unit.nok,
      activeEvents: _alarms('PackerC', subtree: true),
      ringEvents: List.of(_rings['PackerC']!.reversed),
      access: _access['PackerC'],
      configPersist: _persistStatus('PackerC', kind: ConfigStoreKind.fileJson),
      controlPower: _power('PackerC'),
      safety: const SafetyFacet(devices: [
        SafetyDeviceStatus(
            name: 'GuardFence',
            kind: SafetyDeviceKind.guardDoor,
            state: SafetyState.ready,
            ready: true,
            safeStateActive: false,
            affectedPowerMask: 1,
            description: 'project.safety.packerGuard'),
      ]),
      running: unit.running,
      stopPending: unit.stopRequested,
      supportedModes: unit.modes,
      packML: unit.running ? PackMLState.execute : PackMLState.stopped,
      machineState:
          unit.running ? MachineState.producing : MachineState.stopped,
      step: chain.currentInfo(),
      sequenceViewEnabled: true,
      sequenceSteps: chain.rows,
      sequenceStepCount: chain.rows.length,
      currentStepElapsed: chain.currentElapsed,
      currentStepTimedOut: chain.currentTimedOut,
      cycle: auto.lastProfile,
      cycleHistory: auto.history,
      lastCycleTime: auto.lastCycleTime,
      minCycleTime: auto.bestCycleTime,
      stepStats: auto.stats,
      oee: _oee(unit),
      systemHealth: health,
      signalTower: SignalTowerFacet(green: unit.running, amber: !unit.running),
      config: _configFor('PackerC'),
      nameplate: const Nameplate(
          manufacturer: 'Fraktal Machinery GmbH',
          designation: 'Case packer CP-12',
          serial: 'SN-2025-0107',
          year: '2025',
          fwVersion: 'TC3 4026.14',
          swVersion: 'Fraktal Core 0.25'),
      publishedValues: {
        'OutImm/CartonsPerMinute': 5.8,
        'OutImm/GlueTemperatureC':
            double.tryParse(_cfg['sim.packer.glueTemperature']!) ?? 0,
      },
      children: [
        ModuleNode(
          path: 'PackerC.Erector',
          name: 'Erector',
          type: ModuleType.equipmentModule,
          state: chain.currentStep?.stepNo == 10 && unit.running
              ? ExecState.busy
              : ExecState.done,
          commandTimings: _timingsOf('PackerC.Erector'),
          commands: const [CommandInfo(1, 'project.command.erect')],
          children: [
            ModuleNode(
                path: 'PackerC.Erector.Vacuum',
                name: 'Vacuum',
                type: ModuleType.controlModule,
                state: _cmdState('PackerC.Erector.Vacuum', ExecState.done),
                commands: const [
                  CommandInfo(1, 'project.command.vacuumOn'),
                  CommandInfo(2, 'project.command.vacuumOff'),
                ]),
          ],
        ),
        // §3.1 - a Unit inside a Unit: the labeler runs its own mode and its
        // own chain, and the packer commands it like any other child.
        ModuleNode(
          path: 'PackerC.Labeler',
          name: 'Labeler',
          typeKey: 'project.moduleType.labeler',
          type: ModuleType.unit,
          state: _unitState(labeler),
          message: labeler.running
              ? 'project.status.labeling'
              : 'project.status.stopped',
          modeActive: labeler.mode,
          goodCount: labeler.good,
          running: labeler.running,
          stopPending: labeler.stopRequested,
          supportedModes: labeler.modes,
          step: labelChain.currentInfo(),
          sequenceViewEnabled: true,
          sequenceSteps: labelChain.rows,
          sequenceStepCount: labelChain.rows.length,
          currentStepElapsed: labelChain.currentElapsed,
          currentStepTimedOut: labelChain.currentTimedOut,
          config: _configFor('PackerC.Labeler'),
          children: [
            ModuleNode(
                path: 'PackerC.Labeler.Printer',
                name: 'Printer',
                type: ModuleType.controlModule,
                state: _cmdState('PackerC.Labeler.Printer', ExecState.done),
                commands: const [
                  CommandInfo(1, 'project.command.printTestLabel'),
                ]),
            ModuleNode(
                path: 'PackerC.Labeler.Applicator',
                name: 'Applicator',
                typeKey: 'std.moduleType.cylinder',
                type: ModuleType.controlModule,
                state: _cmdState('PackerC.Labeler.Applicator', ExecState.done),
                commands: const [
                  CommandInfo(1, 'project.command.toHome'),
                  CommandInfo(2, 'project.command.toWork'),
                ]),
          ],
        ),
        ModuleNode(
            path: 'PackerC.Sealer',
            name: 'Sealer',
            type: ModuleType.controlModule,
            state: chain.currentStep?.stepNo == 40 && unit.running
                ? ExecState.busy
                : ExecState.done),
      ],
    );
  }

  static double _round(double v) => (v * 10).roundToDouble() / 10;

  /// §8.9 rationalization records for the reasons this demo raises.
  static const _alarmMeta = [
    AlarmMeta(10112, 'project.action.cylinderTimeout',
        'project.consequence.cylinderTimeout',
        priority: Severity.high, shelvable: true),
    AlarmMeta(10116, 'project.action.positionDiscrepancy',
        'project.consequence.positionDiscrepancy',
        priority: Severity.high, shelvable: false),
    AlarmMeta(
        10205, 'project.action.readRetry', 'project.consequence.readRetry'),
    AlarmMeta(10210, 'project.action.visionReject',
        'project.consequence.visionReject'),
    AlarmMeta(
        10220, 'project.action.toolChange', 'project.consequence.toolChange'),
    AlarmMeta(10301, 'project.action.airPressureLow',
        'project.consequence.airPressureLow',
        priority: Severity.medium, shelvable: true),
    AlarmMeta(10302, 'project.action.linkLost', 'project.consequence.linkLost',
        priority: Severity.medium,
        category: AlarmCategory.system,
        shelvable: true),
    AlarmMeta(
        10401, 'project.action.guardOpened', 'project.consequence.guardOpened',
        priority: Severity.medium, category: AlarmCategory.safety),
  ];

  AccessSession _sessionWithClasses(AccessSession s) => AccessSession(
      level: s.level,
      user: s.user,
      loginFailed: s.loginFailed,
      required: s.required,
      sessionTimeout: s.sessionTimeout,
      classes: List.unmodifiable(_classes.values));

  // ==== fieldbus (Core §10.5.1) ====

  IoChannel _io(String tag, String key, String path, String module,
          ChannelDir dir, String address,
          {bool value = false,
          double analog = 0,
          String unit = '',
          bool forceable = false,
          bool quality = true}) =>
      IoChannel(
          name: tag,
          descriptionKey: key,
          address: address,
          path: path,
          modulePath: module,
          dir: dir,
          kind: unit.isEmpty ? ChannelKind.digital : ChannelKind.analog,
          boolValue: value,
          analogValue: analog,
          unit: unit,
          quality: quality,
          forceable: forceable && commissioning);

  void _publishBus() {
    if (_bus.isClosed) return;
    final a = _units['StationA']!;
    // EtherCAT-style: IPC master -> couplers -> terminals. Channel names are the
    // electrical tags verbatim, so an alarm's IoTag finds its channel.
    final tree = <BusNode>[
      BusNode(
        name: 'EtherCAT Master',
        descriptionKey: 'project.hardware.ethercatMaster',
        typeId: 'Beckhoff CX2040 · TwinCAT EtherCAT',
        address: 'AmsNetId 5.80.201.232.1.1',
        children: [
          BusNode(
            name: '=A1+S1-A10',
            descriptionKey: 'project.hardware.ek1100',
            typeId: 'Beckhoff EK1100',
            address: 'EtherCAT 1001',
            children: [
              BusNode(
                name: '=A1+S1-A11',
                descriptionKey: 'project.hardware.el1008',
                typeId: 'Beckhoff EL1008 (8× DI)',
                address: 'EtherCAT 1002',
                channels: [
                  _io(
                      '=A1+S1-B41',
                      'project.io.cylBWorkFb1',
                      'StationA.ClampStation.CylB.WorkFb1',
                      'StationA.ClampStation.CylB',
                      ChannelDir.input,
                      'EL1008 Ch1',
                      value: _cylBPos >= 49),
                  _io(
                      '=A1+S1-B42',
                      'project.io.cylBWorkFb2',
                      'StationA.ClampStation.CylB.WorkFb2',
                      'StationA.ClampStation.CylB',
                      ChannelDir.input,
                      'EL1008 Ch2',
                      value: _cylBPos >= 49),
                  _io(
                      '=A1+S1-B31',
                      'project.io.cylAHomeFb',
                      'StationA.ClampStation.CylA.HomeFb',
                      'StationA.ClampStation.CylA',
                      ChannelDir.input,
                      'EL1008 Ch3',
                      value: _cylAPos < 1),
                  _io(
                      '=A1+S1-B10',
                      'project.io.separatorExtended',
                      'StationA.Separator1.ExtendedFb',
                      'StationA.Separator1',
                      ChannelDir.input,
                      'EL1008 Ch4',
                      value: _separatorOut),
                  _io(
                      '=A1+S1-B60',
                      'project.io.partPresent',
                      'StationA.PartPresent',
                      'StationA',
                      ChannelDir.input,
                      'EL1008 Ch5',
                      value: _partPresent),
                ],
              ),
              BusNode(
                name: '=A1+S1-A12',
                descriptionKey: 'project.hardware.el1904',
                typeId: 'Beckhoff EL1904 (TwinSAFE 4× DI)',
                address: 'EtherCAT 1003',
                channels: [
                  _io('=A1+S1-S01', 'project.io.guardClosed', 'StationA.Guard',
                      'StationA', ChannelDir.input, 'EL1904 Ch1',
                      value: !_doorOpen),
                ],
              ),
              BusNode(
                name: '=A1+S1-A13',
                descriptionKey: 'project.hardware.el2008',
                typeId: 'Beckhoff EL2008 (8× DO)',
                address: 'EtherCAT 1004',
                channels: [
                  _io(
                      '=A1+S1-Y41',
                      'project.io.cylBToWork',
                      'StationA.ClampStation.CylB.ToWork',
                      'StationA.ClampStation.CylB',
                      ChannelDir.output,
                      'EL2008 Ch1',
                      value: _cylBTarget >= 50,
                      forceable: true),
                  _io(
                      '=A1+S1-Y31',
                      'project.io.cylAToWork',
                      'StationA.ClampStation.CylA.ToWork',
                      'StationA.ClampStation.CylA',
                      ChannelDir.output,
                      'EL2008 Ch2',
                      value: _cylATarget >= 50,
                      forceable: true),
                  _io(
                      '=A1+S1-Y10',
                      'project.io.separatorExtend',
                      'StationA.Separator1.Extend',
                      'StationA.Separator1',
                      ChannelDir.output,
                      'EL2008 Ch3',
                      value: _separatorOut,
                      forceable: true),
                  // A coil the station lights for its own status: never
                  // forceable, so output direction alone grants nothing.
                  _io(
                      '=A1+S1-H01',
                      'project.io.statusLamp',
                      'StationA.StatusLamp',
                      'StationA',
                      ChannelDir.output,
                      'EL2008 Ch4',
                      value: a.running),
                ],
              ),
              BusNode(
                name: '=A1+S1-A14',
                descriptionKey: 'project.hardware.el3021',
                typeId: 'Beckhoff EL3021 (1× AI 4–20 mA)',
                address: 'EtherCAT 1005',
                channels: [
                  _io(
                      '=A1+S1-B50',
                      'project.io.clampPressure',
                      'StationA.ClampStation.Pressure',
                      'StationA.ClampStation',
                      ChannelDir.input,
                      'EL3021 Ch1',
                      analog: _clamped ? 5.6 : 0.4,
                      unit: 'bar'),
                ],
              ),
              const BusNode(
                name: '=A1+S1-A15',
                descriptionKey: 'project.hardware.el6001',
                typeId: 'Beckhoff EL6001 (RS232)',
                address: 'EtherCAT 1006',
              ),
              // A commissioning finding, not a fault in production: the slot
              // was configured for a 16-channel terminal and an 8-channel one
              // is fitted. Nothing is mapped to it yet.
              const BusNode(
                name: '=A1+S1-A16',
                descriptionKey: 'project.hardware.spareSlot',
                typeId: 'Beckhoff EL1809 (configured) · EL1808 (found)',
                address: 'EtherCAT 1007',
                state: NodeState.preop,
                mappingValid: false,
                mappingDiagnosticKey: 'project.hardware.identityMismatch',
              ),
            ],
          ),
          BusNode(
            name: '=A1+S2-T01',
            descriptionKey: 'project.hardware.ax5103',
            typeId: 'Beckhoff AX5103 (servo drive)',
            address: 'EtherCAT 1010',
            channels: [
              _io(
                  '=A1+S2-T01.Pos',
                  'project.io.robotAxis',
                  'StationA.Robot.Axis',
                  'StationA.Robot',
                  ChannelDir.input,
                  'AX5103 Ch A',
                  analog: _round(_robotPos),
                  unit: 'mm'),
            ],
          ),
          BusNode(
            name: '=A2+S1-A10',
            descriptionKey: 'project.hardware.ek1100Conveyor',
            typeId: 'Beckhoff EK1100',
            address: 'EtherCAT 1020',
            children: [
              BusNode(
                name: '=A2+S1-A11',
                descriptionKey: 'project.hardware.el1008',
                typeId: 'Beckhoff EL1008 (8× DI)',
                address: 'EtherCAT 1021',
                channels: [
                  _io(
                      '=A2+S1-B11',
                      'project.io.palletAtStop',
                      'ConveyorB.Infeed.Stopper.PalletFb',
                      'ConveyorB.Infeed.Stopper',
                      ChannelDir.input,
                      'EL1008 Ch1',
                      value: _palletAtStop),
                  _io('=A2+S1-B21', 'project.io.liftUp', 'ConveyorB.Lift.UpFb',
                      'ConveyorB.Lift', ChannelDir.input, 'EL1008 Ch2',
                      value: _liftUp),
                  _io(
                      '=A2+S1-B22',
                      'project.io.liftDown',
                      'ConveyorB.Lift.DownFb',
                      'ConveyorB.Lift',
                      ChannelDir.input,
                      'EL1008 Ch3',
                      value: !_liftUp),
                ],
              ),
              BusNode(
                name: '=A2+S1-A12',
                descriptionKey: 'project.hardware.el2008',
                typeId: 'Beckhoff EL2008 (8× DO)',
                address: 'EtherCAT 1022',
                channels: [
                  _io(
                      '=A2+S1-Y11',
                      'project.io.stopperOpen',
                      'ConveyorB.Infeed.Stopper.Open',
                      'ConveyorB.Infeed.Stopper',
                      ChannelDir.output,
                      'EL2008 Ch1',
                      value: !_palletAtStop,
                      forceable: true),
                  _io(
                      '=A2+S1-Y21',
                      'project.io.liftRaise',
                      'ConveyorB.Lift.Raise',
                      'ConveyorB.Lift',
                      ChannelDir.output,
                      'EL2008 Ch2',
                      value: _liftUp,
                      forceable: true),
                ],
              ),
              BusNode(
                name: '=A2+S1-A13',
                descriptionKey: 'project.hardware.el3021',
                typeId: 'Beckhoff EL3021 (1× AI 4–20 mA)',
                address: 'EtherCAT 1023',
                channels: [
                  _io(
                      '=A2+S1-B30',
                      'project.io.conveyorAir',
                      'ConveyorB.AirMonitor.Pressure',
                      'ConveyorB.AirMonitor',
                      ChannelDir.input,
                      'EL3021 Ch1',
                      analog: _airDip ? 3.9 : 6.2,
                      unit: 'bar'),
                ],
              ),
            ],
          ),
          BusNode(
            name: '=A3+S1-A10',
            descriptionKey: 'project.hardware.ep2338',
            typeId: 'Beckhoff EP2338 (IP67 8× DI/DO)',
            address: 'EtherCAT 1030',
            channels: [
              _io(
                  '=A3+S1-B11',
                  'project.io.cartonPresent',
                  'PackerC.Erector.CartonFb',
                  'PackerC.Erector',
                  ChannelDir.input,
                  'EP2338 Ch1',
                  value: _units['PackerC']!.chain?.currentStep?.stepNo != 10),
              _io(
                  '=A3+S1-Y11',
                  'project.io.vacuumOn',
                  'PackerC.Erector.Vacuum.On',
                  'PackerC.Erector.Vacuum',
                  ChannelDir.output,
                  'EP2338 Ch5',
                  value: _units['PackerC']!.chain?.currentStep?.stepNo == 10,
                  forceable: true),
            ],
          ),
        ],
      ),
    ];
    final mapped = _mapForces(tree);
    _latestChannels.clear();
    _indexChannels(mapped);
    _bus.add(mapped);
  }

  IoChannel _applyForce(IoChannel c) {
    final f = _forced[c.path];
    if (f == null) return c;
    return IoChannel(
        name: c.name,
        descriptionKey: c.descriptionKey,
        address: c.address,
        path: c.path,
        modulePath: c.modulePath,
        dir: c.dir,
        kind: c.kind,
        boolValue: c.kind == ChannelKind.digital ? f.b : c.boolValue,
        analogValue: c.kind == ChannelKind.analog ? f.a : c.analogValue,
        unit: c.unit,
        unitCode: c.unitCode,
        forced: true,
        quality: c.quality,
        faultActive: c.faultActive,
        diagnosticKey: c.diagnosticKey,
        forceable: c.forceable);
  }

  void _indexChannels(List<BusNode> nodes) {
    for (final node in nodes) {
      for (final channel in node.channels) {
        _latestChannels[channel.path] = channel;
      }
      _indexChannels(node.children);
    }
  }

  List<BusNode> _mapForces(List<BusNode> nodes) => [
        for (final n in nodes)
          BusNode(
              name: n.name,
              descriptionKey: n.descriptionKey,
              typeId: n.typeId,
              address: n.address,
              state: n.state,
              linkOk: n.linkOk,
              mappingValid: n.mappingValid,
              mappingDiagnosticKey: n.mappingDiagnosticKey,
              channels: [for (final c in n.channels) _applyForce(c)],
              children: _mapForces(n.children)),
      ];

  // ==== write surface (HMI_CONTRACT: narrow, the PLC re-checks everything) ====

  @override
  Future<bool> forceChannel(String rootPath, String channelPath,
      {required bool force,
      bool boolValue = false,
      double analogValue = 0}) async {
    // output-only rule (§10.5.1): inputs are never forceable through this path
    final channel = _latestChannels[channelPath];
    final owned = channel != null &&
        (channel.modulePath == rootPath ||
            channel.modulePath.startsWith('$rootPath.'));
    if (!owned || channel.dir != ChannelDir.output || !channel.forceable) {
      _audit('Force REJECTED (identity/direction/capability)', channelPath);
      return false;
    }
    // §7.7: MANUAL gate, PLC-side re-check (the client also greys the control)
    if (!_accessFor(rootPath).permits(GatedAction.manual)) {
      _audit('Force DENIED', channelPath);
      return false;
    }
    if (_owningUnit(channel.modulePath)?.mode != UnitMode.manual) {
      _audit('Force REJECTED (not MANUAL)', channelPath);
      return false;
    }
    if (force) {
      _forced[channelPath] = (b: boolValue, a: analogValue);
      _audit('Channel FORCED', channelPath);
    } else {
      _forced.remove(channelPath);
      _audit('Channel force cleared', channelPath);
    }
    _publishBus();
    return true;
  }

  @override
  Future<bool> login(String rootPath, String user, String secret) async {
    final root = _rootOfPath(rootPath);
    if (!_access.containsKey(root)) return false;
    final u = _users[user];
    final ok = u != null && u.$1 == secret;
    final prior = _access[root]!;
    _access[root] = ok
        ? AccessSession(
            level: u.$2,
            user: user,
            required: prior.required,
            sessionTimeout: prior.sessionTimeout)
        : AccessSession(
            level: AccessLevel.none,
            loginFailed: true,
            required: prior.required,
            sessionTimeout: prior.sessionTimeout);
    _publish();
    return ok;
  }

  @override
  Future<void> logout(String rootPath) async {
    final root = _rootOfPath(rootPath);
    final prior = _access[root];
    if (prior == null) return;
    _access[root] = AccessSession(
        required: prior.required, sessionTimeout: prior.sessionTimeout);
    _publish();
  }

  @override
  Future<bool> setAccessLevel(
      String rootPath, GatedAction action, AccessLevel level) async {
    final prior = _accessFor(rootPath);
    if (!prior.permits(GatedAction.accessPolicy)) return false;
    if (action == GatedAction.accessPolicy && level.index > prior.level.index) {
      return false;
    }
    final required = List<AccessLevel>.from(prior.required);
    if (action.index >= required.length) return false;
    required[action.index] = level;
    _setAccess(
        rootPath,
        AccessSession(
            level: prior.level,
            user: prior.user,
            loginFailed: prior.loginFailed,
            required: List.unmodifiable(required),
            sessionTimeout: prior.sessionTimeout));
    _audit('Access policy changed: ${action.name}=${level.name}', rootPath);
    return true;
  }

  @override
  Future<bool> setSessionTimeout(String rootPath, Duration timeout) async {
    final prior = _accessFor(rootPath);
    if (!prior.permits(GatedAction.accessPolicy) ||
        timeout.isNegative ||
        timeout > const Duration(days: 7)) {
      return false;
    }
    _setAccess(
        rootPath,
        AccessSession(
            level: prior.level,
            user: prior.user,
            loginFailed: prior.loginFailed,
            required: prior.required,
            sessionTimeout: timeout));
    _audit('Session timeout changed: ${timeout.inMinutes} min', rootPath);
    return true;
  }

  /// §3.8d(b): only Station A declares data classes; the PLC answers any other
  /// class (or root) with a refusal.
  @override
  Future<bool> setClassLevel(String rootPath, String classId, AccessLevel level,
      {required bool forWrite}) async {
    final policy = _classes[classId];
    if (rootPath != 'StationA' ||
        policy == null ||
        !_accessFor(rootPath).permits(GatedAction.accessPolicy)) {
      return false;
    }
    _classes[classId] = DataClassPolicy(
        classId: classId,
        labelKey: policy.labelKey,
        readLevel: forWrite ? policy.readLevel : level,
        writeLevel: forWrite ? level : policy.writeLevel);
    _audit(
        'Data class ${forWrite ? 'write' : 'read'} level: $classId=${level.name}',
        rootPath);
    return true;
  }

  @override
  Future<bool> setMode(String unitPath, UnitMode mode) async {
    final unit = _units[unitPath];
    if (unit == null ||
        !_accessFor(unitPath).permits(GatedAction.modeChange) ||
        !unit.modes.contains(mode)) {
      return false; // PLC re-check (7.7c), §3.7 _M_Supports
    }
    if (mode == unit.mode) return true;
    unit.chain?.park();
    unit.mode = mode;
    unit.running = false;
    unit.stopRequested = false;
    unit.runStyle = RunStyle.continuous;
    // §3.13: the chart is scoped to the running mode - each builds its own.
    unit.chain?.restart(clearChart: true);
    if (mode != UnitMode.manual) unit.chain?.park();
    if (unitPath == 'StationA' && mode != UnitMode.changeover) {
      _changeoverConfirm = false;
      if (_decision?.prompt == 'project.decision.fingersSwapped') {
        _decision = null;
      }
    }
    _audit('Mode changed: ${mode.name}', unitPath);
    return true;
  }

  @override
  Future<bool> setModel(String rootPath, String modelCode) async {
    if (!_accessFor(rootPath).permits(GatedAction.changeover)) return false;
    switch (rootPath) {
      case 'StationA':
        if (!_stationAModels.contains(modelCode)) return false;
        // In CHANGEOVER the new model is applied by the chain's commit step.
        if (_units['StationA']!.mode == UnitMode.changeover) {
          _pendingModel = modelCode;
        } else {
          _modelA = modelCode;
        }
      case 'ConveyorB':
        _modelB = modelCode;
      case 'PackerC':
        _modelC = modelCode;
      default:
        return false;
    }
    _publish();
    return true;
  }

  @override
  Future<bool> start(String unitPath) async {
    final report = await releaseReportStart(unitPath);
    final unit = _units[unitPath];
    if (!report.released || unit == null) return false;
    final chain = unit.chain!;
    unit.running = true;
    unit.stopRequested = false;
    if (!chain.running) {
      chain.restart(clearChart: chain.finished);
    }
    _publish();
    return true;
  }

  @override
  Future<bool> stop(String unitPath) async {
    final unit = _units[unitPath];
    if (unit == null || !_accessFor(unitPath).permits(GatedAction.startStop)) {
      return false;
    }
    if (unit.running) {
      if (unit.mode == UnitMode.auto) {
        unit.stopRequested = true; // §3.4: finish the cycle, then stop
      } else {
        unit.running = false;
      }
    }
    _publish();
    return true;
  }

  @override
  Future<bool> controlOn(String unitPath) async {
    final domain = _domainOf(unitPath);
    if (domain == null ||
        !_accessFor(unitPath).permits(GatedAction.powerControl)) {
      return false;
    }
    // The certified safety circuit grants the enable, never the HMI: while it
    // demands a safe state the request is refused, not queued (§9.8).
    if (domain.id == 'Cell1' && (_doorOpen || _safetyResetRequired)) {
      _audit('Control On REFUSED (safety)', unitPath);
      return false;
    }
    domain.requested = true;
    domain.rearm = false;
    if (!domain.on || domain.energizingUntil >= 0) {
      domain.on = false;
      domain.energizingUntil = _tick + _ticksOf(const Duration(seconds: 1));
    }
    _audit('Control On', unitPath);
    return true;
  }

  @override
  Future<bool> controlOff(String unitPath) async {
    final domain = _domainOf(unitPath);
    if (domain == null ||
        !_accessFor(unitPath).permits(GatedAction.powerControl)) {
      return false;
    }
    domain.requested = false;
    domain.on = false;
    domain.energizingUntil = -1;
    for (final member in domain.members) {
      for (final unit in _units.values) {
        if (_rootOfPath(unit.path) == member) unit.running = false;
      }
    }
    _audit('Control Off', unitPath);
    return true;
  }

  @override
  Future<bool> operatorReset(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.alarmReset)) return false;
    final root = _rootOfPath(unitPath);
    // §8.3(b): closes every MANUAL_RESET event from ACTIVE or WAIT_RESET, and
    // releases the latched control state - never the condition.
    for (final e in List.of(_active)) {
      if (_rootOfPath(e.sourcePath) == root &&
          e.resetClass == ResetClass.manualReset) {
        _close(e);
      }
    }
    if (root == 'StationA' && _jamFault) {
      _jamFault = false;
      final chain = _units['StationA']!.chains[UnitMode.auto]!;
      chain.clearErrors();
      // The step's latches are re-armed: on Start the clamp command is issued
      // again and tested again. If the cylinder is still stuck - the reset
      // cleared the latch, not the condition - it times out again.
      _jamArmed = _cylBStuck;
      _cylBStuck = false;
      chain.restartStep();
    }
    _publish();
    return true;
  }

  @override
  Future<bool> lampTest(String unitPath) async {
    final unit = _units[unitPath];
    if (!_accessFor(unitPath).permits(GatedAction.manual) ||
        (unit?.running ?? false)) {
      return false;
    }
    _lampTestUntil = _tick + _ticksOf(const Duration(seconds: 3));
    _audit('Signal tower lamp test', unitPath);
    return true;
  }

  @override
  Future<bool> setDecisionAnswer(String unitPath, int option) async {
    final decision = _decision;
    if (unitPath != 'StationA' ||
        !_accessFor(unitPath).permits(GatedAction.startStop) ||
        decision == null ||
        option < 1 ||
        option > decision.options.length) {
      return false;
    }
    _decision = null;
    if (decision.prompt == 'project.decision.fingersSwapped') {
      _changeoverConfirm = false; // releases N30
    } else {
      _toolWorn = false;
      _clear('StationA.Robot', 'project.reason.toolChange');
    }
    _audit('Decision accepted: option $option', unitPath);
    return true;
  }

  @override
  Future<ReleaseReport> releaseReportStart(String unitPath) async {
    final reasons = <ReleaseReason>[];
    final unit = _units[unitPath];
    final root = _rootOfPath(unitPath);
    if (!_accessFor(unitPath).permits(GatedAction.startStop)) {
      reasons.add(ReleaseReason(
          'std.release.insufficientStartStop', ReleaseKind.access,
          sourcePath: unitPath));
    }
    if (_blocking(root)) {
      reasons.add(ReleaseReason('std.release.manualReset', ReleaseKind.alarm,
          sourcePath: root));
    }
    if (root == 'StationA' && _cylBStuck && _jamFault) {
      reasons.add(const ReleaseReason(
          'project.interlock.cylinderPosition', ReleaseKind.interlock,
          sourcePath: 'StationA.ClampStation.CylB'));
    }
    if (root == 'StationA' && (_doorOpen || _safetyResetRequired)) {
      reasons.add(const ReleaseReason(
          'std.release.controlDomainNotReady', ReleaseKind.interlock,
          sourcePath: 'StationA.DoorNorth'));
    }
    if (!_domainLive(unitPath)) {
      reasons.add(ReleaseReason(
          'std.release.controlPowerOff', ReleaseKind.interlock,
          sourcePath: unitPath));
    }
    if (unit == null || unit.mode == UnitMode.manual) {
      reasons.add(ReleaseReason(
          'std.release.manualHasNoAutoSequence', ReleaseKind.mode,
          sourcePath: unitPath));
    }
    return ReleaseReport(reasons.isEmpty, reasons);
  }

  @override
  Future<ReleaseReport> releaseReportAction(
      String unitPath, GatedAction action) async {
    final reasons = <ReleaseReason>[];
    final unit = _units[unitPath];
    if (!_accessFor(unitPath).permits(action)) {
      reasons.add(ReleaseReason(
          'std.release.insufficientAction', ReleaseKind.access,
          sourcePath: unitPath));
    }
    switch (action) {
      case GatedAction.changeover:
        if (unit != null && unit.running && unit.mode == UnitMode.auto) {
          reasons.add(ReleaseReason(
              'std.release.changeoverRunning', ReleaseKind.mode,
              sourcePath: unitPath));
        }
      case GatedAction.powerControl:
        if (_rootOfPath(unitPath) == 'StationA' &&
            (_doorOpen || _safetyResetRequired)) {
          reasons.add(const ReleaseReason(
              'std.release.controlDomainNotReady', ReleaseKind.interlock,
              sourcePath: 'StationA.DoorNorth'));
        }
      case GatedAction.manual:
        if (unit?.running ?? false) {
          reasons.add(ReleaseReason(
              'std.release.unitNotReady', ReleaseKind.mode,
              sourcePath: unitPath));
        }
      default:
    }
    return ReleaseReport(reasons.isEmpty, reasons);
  }

  @override
  Future<ReleaseReport> releaseReportManual(
      String unitPath, String targetPath, int commandValue) async {
    final reasons = <ReleaseReason>[];
    final unit = _owningUnit(targetPath) ?? _units[unitPath];
    if (unit?.mode != UnitMode.manual) {
      reasons.add(ReleaseReason(
          'std.release.manualModeRequired', ReleaseKind.mode,
          sourcePath: unit?.path ?? unitPath));
    }
    if (!_accessFor(unitPath).permits(GatedAction.manual)) {
      reasons.add(ReleaseReason(
          'std.release.insufficientManual', ReleaseKind.access,
          sourcePath: unitPath));
    }
    if (targetPath.startsWith('StationA.Robot') && _doorOpen) {
      reasons.add(const ReleaseReason(
          'project.interlock.areaSafe', ReleaseKind.interlock,
          sourcePath: 'StationA.DoorNorth'));
    }
    if (!_domainLive(unitPath)) {
      reasons.add(ReleaseReason(
          'std.release.controlPowerOff', ReleaseKind.interlock,
          sourcePath: unitPath));
    }
    return ReleaseReport(reasons.isEmpty, reasons);
  }

  @override
  Future<bool> shelveAlarm(String unitPath, String sourcePath,
      String description, Duration duration) async {
    if (!_accessFor(unitPath).permits(GatedAction.alarmShelve)) {
      _audit('Shelve DENIED', sourcePath);
      return false;
    }
    final event = _active
        .where(
            (e) => e.sourcePath == sourcePath && e.description == description)
        .firstOrNull;
    // §8.10: only a rationalized, shelvable reason - and never safety.
    final meta =
        _alarmMeta.where((m) => m.reasonCode == event?.reason).firstOrNull;
    if (event == null || meta == null || !meta.shelvable) {
      _audit('Shelve REFUSED (not shelvable)', sourcePath);
      return false;
    }
    _shelved.add(event.id);
    _audit('Shelved', sourcePath);
    return true;
  }

  @override
  Future<bool> unshelveAlarm(
      String unitPath, String sourcePath, String description) async {
    if (!_accessFor(unitPath).permits(GatedAction.alarmShelve)) return false;
    _shelved.remove('$sourcePath|$description');
    _audit('Unshelved', sourcePath);
    return true;
  }

  @override
  Future<bool> resetOee(String unitPath) async {
    final unit = _units[unitPath];
    if (unit == null || !_accessFor(unitPath).permits(GatedAction.dataWrite)) {
      _audit('OEE reset DENIED', unitPath);
      return false;
    }
    unit.good = 0;
    unit.nok = 0;
    unit.rework = 0;
    unit.oeeTrend.clear();
    _audit('OEE reset', unitPath);
    return true;
  }

  // ---- Core §3.8b parameter sets: named sets of a root's editable values,
  // bounded like the PLC's local store (four sets, no eviction). ----

  final Map<String, Map<String, (CfgKind, Map<String, String>, DateTime)>>
      _sets = {'StationA': {}, 'PackerC': {}};
  String _setRejection = '';
  // §3.8b. Durability is modelled rather than asserted: an accepted write goes
  // PENDING and becomes durable when the declared window elapses, because that
  // is the only way the indication is ever seen working.
  static const Duration _persistWindow = Duration(seconds: 3);
  DateTime? _persistPendingSince;
  bool _restoreAcknowledged = false;

  bool _setsAllowed(String rootPath) =>
      _sets.containsKey(rootPath) &&
      _accessFor(rootPath).permits(GatedAction.configSet);

  /// The value a set records for [field].
  String _stored(CfgField field) => field.kind == CfgKind.lineCfg
      ? _line[field.writeKey]!
      : field.modelScoped
          ? _settle(_modelA)
          : _cfg[field.writeKey]!;

  void _store(CfgField field, String value, {String? model}) {
    if (field.kind == CfgKind.lineCfg) {
      _line[field.writeKey] = value;
    } else if (field.modelScoped) {
      _settleByModel[model ?? _modelA] = value;
    } else {
      _cfg[field.writeKey] = value;
    }
  }

  @override
  Future<List<ConfigSetInfo>?> listConfigSets(String rootPath) async {
    if (!_setsAllowed(rootPath)) return null;
    return [
      for (final entry in _sets[rootPath]!.entries)
        ConfigSetInfo(
            name: entry.key,
            rootIdentity: rootPath,
            kind: entry.value.$1,
            modelCode: entry.value.$1 == CfgKind.parCfg ? _modelA : '',
            recordCount: entry.value.$2.length,
            createdAt: entry.value.$3,
            timeSynchronized: rootPath != 'PackerC'),
    ];
  }

  @override
  Future<bool> saveConfigSet(String rootPath, String name, CfgKind kind) async {
    if (!_setsAllowed(rootPath) || name.trim().isEmpty) return false;
    final records = {
      for (final f in _configFor(rootPath))
        if (f.kind == kind) f.writeKey: _stored(f),
    };
    if (records.isEmpty) return false; // an empty set is refused, as on the PLC
    final sets = _sets[rootPath]!;
    if (!sets.containsKey(name) && sets.length >= 4) return false;
    sets[name] = (kind, records, _now.toUtc());
    _audit('Parameter set saved', '$rootPath.$name');
    return true;
  }

  @override
  Future<bool> loadConfigSet(String rootPath, String name) async {
    final set = _sets[rootPath]?[name];
    if (!_setsAllowed(rootPath) || set == null) {
      _setRejection = name;
      return false;
    }
    final byKey = {for (final f in _configFor(rootPath)) f.writeKey: f};
    for (final entry in set.$2.entries) {
      final field = byKey[entry.key];
      if (field == null || !field.accepts(entry.value)) {
        _setRejection = '$rootPath / ${entry.key}';
        return false; // staged: nothing applied
      }
    }
    for (final entry in set.$2.entries) {
      _store(byKey[entry.key]!, entry.value);
    }
    _setRejection = '';
    _audit('Parameter set loaded', '$rootPath.$name');
    return true;
  }

  @override
  Future<bool> deleteConfigSet(String rootPath, String name) async {
    if (!_setsAllowed(rootPath)) return false;
    return _sets[rootPath]!.remove(name) != null;
  }

  @override
  Future<String?> exportConfigSet(String rootPath, String name) async {
    final set = _sets[rootPath]?[name];
    if (!_setsAllowed(rootPath) || set == null) return null;
    return [
      '{"set":"$name","root":"$rootPath","kind":${set.$1.index},"records":${set.$2.length}}',
      for (final entry in set.$2.entries)
        '{"scope":"$rootPath","key":"${entry.key}","value":"${entry.value}"}',
    ].join('\n');
  }

  @override
  Future<bool> createModel(String rootPath, String code,
      {int sourceModel = 0, String sourceSet = ''}) async {
    if (rootPath != 'StationA' ||
        !_setsAllowed(rootPath) ||
        !_accessFor(rootPath).permits(GatedAction.dataWrite) ||
        !_accessFor(rootPath).permits(GatedAction.dataRead) ||
        _stationAModels.length >= 8 ||
        _stationAModels.contains(code) ||
        !RegExp(r'^[!-~]{1,80}$').hasMatch(code)) {
      return false;
    }
    final source = _modelAt(sourceModel);
    if (source == null) return false;
    String value = _settle(source);
    if (sourceSet.isNotEmpty) {
      final set = _sets['StationA']![sourceSet];
      if (set == null || set.$1 != CfgKind.parCfg) return false;
      value = set.$2['sim.recipe.clamp.settleMs'] ?? '';
      if (int.tryParse(value) == null) return false;
    }
    _settleByModel[code] = value;
    _stationAModels.add(code);
    _audit('Model created', rootPath);
    return true;
  }

  @override
  Future<String?> exportCurrentConfig(String rootPath, CfgKind kind,
      {int modelIndex = 0}) async {
    if (!_setsAllowed(rootPath) ||
        !_accessFor(rootPath).permits(GatedAction.dataRead)) {
      return null;
    }
    final model = rootPath == 'StationA' ? _modelAt(modelIndex) : null;
    if (rootPath == 'StationA' && model == null) return null;
    final fields =
        _configFor(rootPath, model: model).where((f) => f.kind == kind);
    return [
      '{"set":"current-${kind.name}","root":"$rootPath","kind":${kind.index},"records":${fields.length}}',
      for (final f in fields)
        '{"scope":"$rootPath","key":"${f.writeKey}","value":"${f.value}"}',
    ].join('\n');
  }

  @override
  Future<bool> importConfigSet(String rootPath, String document) async {
    if (!_setsAllowed(rootPath)) return false;
    final lines = document
        .split('\n')
        .map((line) => line.trim())
        .where((line) => line.isNotEmpty)
        .toList();
    if (lines.isEmpty) return false;
    final header =
        RegExp(r'"set":"([^"]*)".*"kind":(\d+)').firstMatch(lines.first);
    if (header == null) return false;
    final kind = int.parse(header.group(2)!);
    if (kind < 0 || kind >= CfgKind.values.length) return false;
    final records = <String, String>{};
    for (final line in lines.skip(1)) {
      final record =
          RegExp(r'"key":"([^"]*)".*"value":"([^"]*)"').firstMatch(line);
      if (record == null) return false;
      records[record.group(1)!] = record.group(2)!;
    }
    final name = header.group(1)!;
    final sets = _sets[rootPath]!;
    if (!sets.containsKey(name) && sets.length >= 4) return false;
    sets[name] = (CfgKind.values[kind], records, _now.toUtc());
    return true;
  }

  @override
  Future<String> configSetRejection(String rootPath) async => _setRejection;

  @override
  Future<bool> acknowledgeConfigRestore(String rootPath) async {
    // The loss is ENGINEER-gated on the PLC, and the PLC re-checks whatever the
    // screen showed. The sim applies the same gate so a demo cannot teach a
    // habit the real station refuses.
    if (!_accessFor(rootPath).permits(GatedAction.dataWrite)) {
      _audit('Config restore ack DENIED', rootPath);
      return false;
    }
    if (!restoreLost) return false;
    _restoreAcknowledged = true;
    _audit('Config restore loss acknowledged', rootPath);
    return true;
  }

  @override
  Future<List<CfgField>?> queryModelConfig(
      String rootPath, int modelIndex) async {
    final model = rootPath == 'StationA' ? _modelAt(modelIndex) : null;
    if (model == null || !_accessFor(rootPath).permits(GatedAction.dataRead)) {
      return null;
    }
    return [
      for (final field in _configFor(rootPath, model: model))
        if (field.modelScoped) field,
    ];
  }

  @override
  Future<bool> writeConfig(String nodePath, CfgField field, String value,
      {int modelIndex = 0}) async {
    final session = _accessFor(nodePath);
    CfgField? capability;
    for (final candidate in _configFor(nodePath)) {
      if (candidate.writeKey == field.writeKey) {
        capability = candidate;
        break;
      }
    }
    if (capability == null || !capability.canWriteIn(session)) {
      _audit('Config write DENIED', '$nodePath.${field.name}');
      return false;
    }
    final trimmed = value.trim();
    if (!capability.hasWriteCapability ||
        capability.writeRevision != field.writeRevision ||
        !capability.accepts(trimmed)) {
      _audit('Config write REJECTED', '$nodePath.${field.name}');
      return false;
    }
    String? model;
    if (capability.modelScoped) {
      model = _modelAt(modelIndex);
      if (model == null) {
        _audit('Config write REJECTED', '$nodePath.${field.name}');
        return false;
      }
    }
    _store(capability, trimmed, model: model);
    _audit('Config write', '$nodePath.${capability.name}');
    // Accepted means live. Durability is a separate claim and it is not true
    // yet (§3.8b).
    _persistPendingSince ??= _now.toUtc();
    return true;
  }

  @override
  Future<bool> setRunStyle(String unitPath, RunStyle style) async {
    final unit = _units[unitPath];
    if (unit == null || !_accessFor(unitPath).permits(GatedAction.modeChange)) {
      return false;
    }
    if (unitPath != 'StationA' && style != RunStyle.continuous) return false;
    if (unit.mode != UnitMode.auto && style != RunStyle.continuous) {
      return false;
    }
    unit.runStyle = style;
    unit.stepGranted = false;
    _publish();
    return true;
  }

  @override
  Future<void> stepRequest(String unitPath) async {
    final unit = _units[unitPath];
    if (unit == null || !_accessFor(unitPath).permits(GatedAction.startStop)) {
      return;
    }
    if (unit.running && unit.runStyle == RunStyle.singleStep) {
      unit.stepGranted = true;
    }
  }

  @override
  Future<void> setHoldRun(String unitPath, bool held) async {
    final unit = _units[unitPath];
    if (unit == null || !_accessFor(unitPath).permits(GatedAction.startStop)) {
      return;
    }
    // The client refreshes while the control is down; a lapse lets go.
    unit.holdUntil = held ? _tick + _ticksOf(const Duration(seconds: 1)) : -1;
  }

  @override
  Future<bool> manualCommand(
      String unitPath, String targetPath, int value) async {
    // §7.6.1: MANUAL mode of the owning Unit AND MANUAL access, else reject
    final report = await releaseReportManual(unitPath, targetPath, value);
    if (!report.released) {
      _audit('Manual cmd rejected', targetPath);
      return false;
    }
    _commandBusyUntil[targetPath] =
        _tick + _ticksOf(const Duration(seconds: 1));
    switch ((targetPath, value)) {
      case ('StationA.ClampStation', final v):
        _cylATarget = _cylBTarget = v == 1 ? 50 : 0;
      case ('StationA.ClampStation.CylB', final v):
        _cylBTarget = v == 2 ? 50 : 0;
      case ('StationA.ClampStation.CylA', final v):
        _cylATarget = v == 2 ? 50 : 0;
      case ('StationA.Separator1', final v):
        _separatorOut = v == 1;
      case ('StationA.Robot', 1):
        _robotPos = 0;
      case ('StationA.Camera', 1):
        _inspections++;
        _judgeOk = true;
        _inspectionResult = 'OK  score=0.98  manual trigger';
      case ('StationA.CodeReader', 1):
        _codeTriggers++;
        _codeGood++;
      case ('ConveyorB.Lift', final v):
        _liftUp = v == 1;
      default:
    }
    _audit('Manual cmd: $targetPath = $value', targetPath);
    return true;
  }

  @override
  Future<bool> manualHeld(
      String unitPath, String targetPath, int value, bool held) async {
    // §7.6.1a - same gates as a one-shot manual command; the hold adds no
    // authority, only a longer presence. A release is always honoured.
    if (!held) {
      _jogUntil = -1;
      return true;
    }
    final report = await releaseReportManual(unitPath, targetPath, value);
    if (!report.released) return false;
    _jogDir = value == 11 ? -1 : 1;
    _jogUntil = _tick + _ticksOf(const Duration(milliseconds: 750));
    return true;
  }

  @override
  void setFieldbusViewActive(bool active) {
    // Simulation publishes everything in-memory; there is no read tier to gate.
  }

  @override
  void setModuleDetailActive(String rootPath, bool active,
      {Set<String>? containers}) {}

  @override
  void setModuleIoViewActive(String? modulePath) {}

  @override
  void dispose() {
    _timer?.cancel();
    _ctrl.close();
    _link.close();
    _bus.close();
  }
}
