/// Demo/dev transport: a two-root forest (Core 3.1a/3.1b) with live events so the
/// tree highlighting, alarm list, access gating, and counters are all exercisable
/// on any platform with zero infrastructure. Behaviour mirrors the PLC contracts.
library;

import 'dart:async';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../domain/fieldbus.dart';
import 'plc_repository.dart';

class SimRepository implements PlcRepository {
  final _ctrl = StreamController<List<ModuleNode>>.broadcast();
  Timer? _timer;
  int _tick = 0;

  // mutable sim state
  AccessSession _accessA = const AccessSession();
  AccessSession _accessB = const AccessSession();
  bool _cylBError = false; // ERROR on StationA.ClampStation.CylB
  bool _convWarn = false; // WARNING on ConveyorB.Infeed
  bool _robotMsg = false; // MESSAGE on StationA.Robot
  bool _blockingA = false;
  UnitMode _modeA = UnitMode.auto, _modeB = UnitMode.auto;
  RunStyle _runStyleA = RunStyle.continuous;
  bool _stopPendingA = false;
  bool _controlOnA = true;
  int _stopTicks = 0;
  String _modelA = 'MODEL-A', _modelB = 'MODEL-B';
  int _goodA = 128, _nokA = 3, _goodB = 902;
  final int _nokB = 11;
  final List<AlarmEvent> _ringA = [];
  final Map<String, ({bool b, double a})> _forced =
      {}; // channelPath -> forced value
  final Map<String, IoChannel> _latestChannels = {};
  final Set<String> _shelved =
      {}; // §8.10 'src|desc' keys with suppressed annunciation
  final Map<String, String> _configValues = {
    'MES endpoint IP': '10.20.0.14',
    'MES port': '4840',
    'Clamp settle time': '150',
  };

  List<CfgField> _configFields() => [
        CfgField('MES endpoint IP', CfgKind.stationCfg, CfgType.text,
            _configValues['MES endpoint IP']!,
            labelKey: 'project.config.mesEndpointIp',
            writeKey: 'sim.station.mes.endpointIp',
            writeRevision: 1,
            writable: true),
        CfgField('MES port', CfgKind.stationCfg, CfgType.number,
            _configValues['MES port']!,
            labelKey: 'project.config.mesPort',
            writeKey: 'sim.station.mes.port',
            writeRevision: 1,
            writable: true,
            minimum: 1,
            maximum: 65535),
        CfgField('Clamp settle time', CfgKind.parCfg, CfgType.time,
            _configValues['Clamp settle time']!,
            unit: 'ms',
            labelKey: 'project.config.clampSettleTime',
            writeKey: 'sim.recipe.clamp.settleMs',
            writeRevision: 1,
            writable: true,
            minimum: 0,
            maximum: 60000),
      ];

  // demo users (FB_LocalAccessProvider analogue)
  static const _users = {
    'op1': ('1111', AccessLevel.operator),
    'tech1': ('4711', AccessLevel.technician),
    'eng1': ('9999', AccessLevel.engineer),
    'admin1': ('2468', AccessLevel.admin),
  };

  final _link = StreamController<LinkState>.broadcast();
  @override
  Stream<LinkState> linkState() {
    scheduleMicrotask(() => _link.add(LinkState.live));
    return _link.stream;
  }

  @override
  Stream<List<ModuleNode>> forest() {
    _timer ??= Timer.periodic(const Duration(seconds: 1), (_) => _step());
    scheduleMicrotask(_publish);
    return _ctrl.stream;
  }

  void _step() {
    _tick++;
    if (_stopPendingA) {
      _stopTicks--;
      if (_stopTicks <= 0) {
        _stopPendingA = false;
        _modeA = _modeA;
      }
    }
    if (_tick % 12 == 4) {
      _cylBError = true; // come
      _blockingA = true; // MANUAL_RESET blocks Start (8.3b)
    }
    _convWarn = (_tick % 9) >= 5; // AUTO_RESET warning comes and goes
    _robotMsg = (_tick % 15) == 7;
    if (_tick % 5 == 0 && !_cylBError && !_blockingA) _goodA++;
    if (_tick % 3 == 0) _goodB++;
    _publish();
    _publishBus();
  }

  AlarmEvent _ev(Severity severity, String text, String src, ResetClass rc,
          AlarmState st, {int reason = 0}) =>
      AlarmEvent(
          severity: severity,
          description: text,
          sourcePath: src,
          resetClass: rc,
          state: st,
          comeAt: DateTime.now(),
          reasonCode: reason,
          shelved: _shelved.contains('$src|$text'));

  void _publish() {
    final cylBEvents = _cylBError
        ? [
            _ev(
                Severity.high,
                'project.reason.cylinderTimeout',
                'StationA.ClampStation.CylB',
                ResetClass.manualReset,
                AlarmState.active,
                reason: 10112)
          ]
        : <AlarmEvent>[];
    final stationAEvents = <AlarmEvent>[
      ...cylBEvents, // rolled-up view on the root's log (8.2/8.3c)
      if (_robotMsg)
        _ev(Severity.low, 'project.reason.toolChange', 'StationA.Robot',
            ResetClass.autoReset, AlarmState.active),
      if (_blockingA && !_cylBError)
        _ev(
            Severity.high,
            'project.reason.cylinderTimeout',
            'StationA.ClampStation.CylB',
            ResetClass.manualReset,
            AlarmState.waitReset),
    ];
    final stationA = ModuleNode(
      path: 'StationA', name: 'StationA', type: ModuleType.unit,
      displayNameKey: 'project.module.StationA.name',
      descriptionKey: 'project.module.StationA.description',
      controlDomainId: 'CageA',
      controlDomainName: 'Cage A',
      controlDomainMembers: const ['StationA'],
      state: _blockingA ? ExecState.error : ExecState.busy,
      faultActive: _cylBError,
      message: _cylBError
          ? 'project.reason.cylinderTimeout'
          : (_blockingA
              ? 'project.status.awaitingReset'
              : 'project.status.clampStep'),
      modelCode: _modelA,
      availableModels: const ['A100', 'A200', 'A300'],
      modeActive: _modeA,
      goodCount: _goodA, nokCount: _nokA, blocking: _blockingA,
      activeEvents: stationAEvents, ringEvents: List.of(_ringA.reversed),
      access: _accessA,
      safety: const SafetyFacet(devices: [
        SafetyDeviceStatus(
            name: 'DoorNorth',
            kind: SafetyDeviceKind.guardDoor,
            state: SafetyState.ready,
            ready: true,
            safeStateActive: false,
            affectedPowerMask: 1,
            description: 'project.safety.doorNorth'),
        SafetyDeviceStatus(
            name: 'LightCurtainInfeed',
            kind: SafetyDeviceKind.lightCurtain,
            state: SafetyState.ready,
            ready: true,
            safeStateActive: false,
            affectedPowerMask: 2,
            description: 'project.safety.lightCurtain'),
        SafetyDeviceStatus(
            name: 'ValveExhaust',
            kind: SafetyDeviceKind.safetyValve,
            state: SafetyState.ready,
            ready: true,
            safeStateActive: false,
            affectedPowerMask: 3,
            description: 'project.safety.safeValve'),
      ]),
      controlPower: ControlPowerFacet(
          requestedOn: _controlOnA,
          controlOn: _controlOnA,
          groups: [
            PowerGroupStatus(
                name: 'ValveZoneA',
                kind: PowerGroupKind.valveZone,
                state: _controlOnA ? PowerState.on : PowerState.off,
                requestedOn: _controlOnA,
                powerOn: _controlOnA,
                safetyPermit: true,
                fieldbusLossReaction: FieldbusLossReaction.controlOff),
            PowerGroupStatus(
                name: 'ValveZoneB',
                kind: PowerGroupKind.valveZone,
                state: _controlOnA ? PowerState.on : PowerState.off,
                requestedOn: _controlOnA,
                powerOn: _controlOnA,
                safetyPermit: true,
                fieldbusLossReaction: FieldbusLossReaction.powerGroupOff),
          ]),
      nameplate: const Nameplate(
          productUri: 'https://fraktal.example/StationA/SN-2024-0042',
          manufacturer: 'Fraktal Machinery GmbH',
          designation: 'Clamp & Separate Station',
          serial: 'SN-2024-0042',
          year: '2024',
          hwVersion: 'HW 2.1',
          fwVersion: 'TC3 4024.12',
          swVersion: 'Fraktal 1.0',
          orderCode: 'FRK-CS-200',
          docUrl: 'https://fraktal.example/docs/FRK-CS-200'),
      running:
          _modeA == UnitMode.auto && !_blockingA, // §3.4 sequence executing
      stopPending: _stopPendingA, // §3.4 blink while finishing
      runStyle: _runStyleA,
      supportedModes: const [
        UnitMode.auto,
        UnitMode.manual,
        UnitMode.home,
        UnitMode.changeover
      ],
      supportedRunStyles: _modeA == UnitMode.auto
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
      alarmMeta: const [
        AlarmMeta(
            10116,
            'Check both position sensors and cylinder air supply; test in MANUAL',
            'Clamp position unproven - parts may be unclamped during process',
            shelvable: false),
        AlarmMeta(
            10112,
            'Inspect for mechanical jam; verify air pressure at the valve',
            'Cycle blocked until the cylinder reaches position',
            shelvable: true),
      ],
      oee: OeeSnapshot(
        availability: _cylBError ? 0.71 : 0.93,
        availValid: true,
        performance: 0.88,
        perfValid: true,
        quality: _nokA + _goodA > 0 ? _goodA / (_goodA + _nokA) : 0,
        qualValid: _goodA + _nokA > 0,
        oee: (_cylBError ? 0.71 : 0.93) *
            0.88 *
            (_nokA + _goodA > 0 ? _goodA / (_goodA + _nokA) : 1),
        oeeValid: true,
        trend: [
          for (var i = 0; i < 24; i++)
            (0.78 + 0.12 * ((i * 7 + _tick) % 10) / 10) -
                (_cylBError && i > 18 ? 0.2 : 0)
        ],
      ),
      packML: _cylBError ? PackMLState.held : PackMLState.execute, // Annex F
      cycle: _profileA(), // §8.11.4
      cycleHistory: _historyA(),
      lastCycleTime: const Duration(milliseconds: 8200),
      minCycleTime: const Duration(milliseconds: 7400),
      machineState:
          _cylBError ? MachineState.down : MachineState.producing, // §8.11.3
      step: StepInfo(
        stepNo: _cylBError ? 200 : 300,
        stepName: _cylBError ? 'Clamp part' : 'Robot pick',
        awaitingLabel: _cylBError ? 'ClampStation.CLAMP' : '',
        timeClass: TimeClass.work,
        expected: const Duration(milliseconds: 2300),
        starved: false,
        blocked: false,
        conds: _cylBError
            ? const [
                CondInfo('CylB extended', false),
                CondInfo('Area safe', true)
              ]
            : const [],
      ),
      stepStats: const [
        StepStat(90, 'Await pallet', TimeClass.waitUpstream,
            Duration(milliseconds: 2000), Duration(milliseconds: 3400)),
        StepStat(200, 'Clamp', TimeClass.work, Duration(milliseconds: 2300),
            Duration(milliseconds: 2600)),
        StepStat(100, 'Separate', TimeClass.work, Duration(milliseconds: 1600),
            Duration(milliseconds: 1800)),
        StepStat(300, 'Robot pick', TimeClass.work,
            Duration(milliseconds: 1500), Duration(milliseconds: 1700)),
        StepStat(400, 'Await outfeed', TimeClass.waitDownstream,
            Duration(milliseconds: 700), Duration(milliseconds: 1900)),
      ],
      decision: _robotMsg
          ? const DecisionRequest(
              prompt: 'project.decision.toolWorn',
              options: [
                'project.decision.replaceNow',
                'project.decision.finishBatch'
              ],
              defaultOption: 1)
          : null, // §6.11
      systemHealth: const SystemHealthFacet(
        healthy: true,
        taskAvailable: true,
        taskCycleUs: 1000,
        taskJitterUs: 30,
        controllerAvailable: true,
        cpuLoadPct: 24.5,
        memoryAvailableMb: 2048,
        fieldbusAvailable: true,
        fieldbusMasterHealthy: true,
        dcAvailable: true,
        dcSynchronized: true,
        time: TimeQualityFacet(
            available: true,
            synchronized: true,
            source: 'SIMULATED',
            offsetUs: 0),
      ),
      signalTower: SignalTowerFacet(
        red: _cylBError,
        green: !_cylBError,
        blue: _robotMsg,
      ),
      config: _configFields(),
      children: [
        const ModuleNode(
            path: 'StationA.Separator1',
            name: 'Separator1',
            type: ModuleType.controlModule,
            state: ExecState.ready),
        ModuleNode(
          path: 'StationA.ClampStation',
          name: 'ClampStation',
          type: ModuleType.equipmentModule,
          state: _cylBError ? ExecState.error : ExecState.busy,
          faultActive: _cylBError,
          message: _cylBError ? 'project.reason.cylinderTimeout' : '',
          children: [
            const ModuleNode(
                path: 'StationA.ClampStation.CylA',
                name: 'CylA',
                type: ModuleType.controlModule,
                state: ExecState.done,
                commands: [
                  CommandInfo(1, 'project.command.toHome'),
                  CommandInfo(2, 'project.command.toWork')
                ]),
            ModuleNode(
              path: 'StationA.ClampStation.CylB', name: 'CylB',
              type: ModuleType.controlModule,
              state: _cylBError ? ExecState.error : ExecState.busy,
              faultActive: _cylBError,
              message: _cylBError ? 'project.reason.cylinderTimeout' : '',
              activeEvents: cylBEvents,
              motion: MotionFacet(
                  actualPosition: _cylBError ? 12.4 : 50.0,
                  targetPosition: 50.0,
                  moving: !_cylBError,
                  homed: true,
                  unit: 'mm'), // Annex G
              commands: const [
                CommandInfo(1, 'project.command.toHome'),
                CommandInfo(2, 'project.command.toWork')
              ], // §7.6.1 catalog
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
          path: 'StationA.Robot', name: 'Robot', type: ModuleType.controlModule,
          state: ExecState.busy,
          message: _robotMsg ? 'project.reason.toolChange' : '',
          activeEvents: _robotMsg
              ? [
                  _ev(Severity.low, 'project.reason.toolChange',
                      'StationA.Robot', ResetClass.autoReset, AlarmState.active)
                ]
              : const [],
          motion: const MotionFacet(
              actualPosition: 245.7,
              actualVelocity: 0,
              targetPosition: 245.7,
              unit: 'mm',
              homed: true), // Annex I
          part: PartFacet(
              uid: 'SN-${1000 + _goodA}',
              present: true,
              verdict: _cylBError ? Verdict.nok : Verdict.ok,
              reason: _cylBError ? 'project.reason.clampNotConfirmed' : '',
              records: const [
                // Annex E
                MeasRecord('Press force', 12.3, 10.0, 15.0, 12.5, 'kN', true),
                MeasRecord('Depth', 4.98, 4.90, 5.10, 5.00, 'mm', true),
              ]),
        ),
      ],
    );

    final convWarnEvents = _convWarn
        ? [
            _ev(Severity.medium, 'project.reason.airPressureLow',
                'ConveyorB.Infeed', ResetClass.autoReset, AlarmState.active)
          ]
        : <AlarmEvent>[];
    final conveyorB = ModuleNode(
      path: 'ConveyorB', name: 'ConveyorB', type: ModuleType.unit,
      displayNameKey: 'project.module.ConveyorB.name',
      descriptionKey: 'project.module.ConveyorB.description',
      state: ExecState.busy,
      message: _convWarn
          ? 'project.reason.airPressureLow'
          : 'project.status.transporting',
      modelCode: _modelB, modeActive: _modeB, goodCount: _goodB,
      nokCount: _nokB,
      activeEvents: convWarnEvents, access: _accessB,
      running: _modeB == UnitMode.auto,
      supportedModes: const [UnitMode.auto, UnitMode.manual],
      packML: PackMLState.execute, // Annex F
      link: LinkFacet(
          linked: !_convWarn,
          lastSeen: DateTime.now(),
          linkReason:
              _convWarn ? 'project.status.heartbeatLost' : ''), // Annex D
      step: StepInfo(
          stepNo: 50,
          stepName: 'project.step.transport',
          timeClass: _convWarn ? TimeClass.waitUpstream : TimeClass.work,
          starved: _convWarn),
      children: [
        ModuleNode(
          path: 'ConveyorB.Infeed',
          name: 'Infeed',
          type: ModuleType.equipmentModule,
          state: ExecState.busy,
          message: _convWarn ? 'project.reason.airPressureLow' : '',
          activeEvents: convWarnEvents,
          children: [
            const ModuleNode(
                path: 'ConveyorB.Infeed.Stopper',
                name: 'Stopper',
                type: ModuleType.controlModule,
                state: ExecState.busy),
          ],
        ),
        const ModuleNode(
            path: 'ConveyorB.Lift',
            name: 'Lift',
            type: ModuleType.equipmentModule,
            state: ExecState.ready),
      ],
    );
    _ctrl.add([stationA, conveyorB]);
  }

  CycleProfile _profileA() => CycleProfile(
        cycleNo: _goodA,
        total: const Duration(milliseconds: 8200),
        workTime: const Duration(milliseconds: 5400),
        waitTime: const Duration(milliseconds: 2800),
        steps: const [
          StepTiming(90, 'Await pallet', TimeClass.waitUpstream,
              Duration(milliseconds: 2100)),
          StepTiming(100, 'Separate', TimeClass.work,
              Duration(milliseconds: 1600), Duration(milliseconds: 2000)),
          StepTiming(200, 'Clamp', TimeClass.work, Duration(milliseconds: 2300),
              Duration(milliseconds: 2000)),
          StepTiming(300, 'Robot pick', TimeClass.work,
              Duration(milliseconds: 1500), Duration(milliseconds: 2000)),
          StepTiming(400, 'Await outfeed', TimeClass.waitDownstream,
              Duration(milliseconds: 700)),
        ],
      );

  /// §8.11.4 sim trend: a slow clamp drift (work share grows) plus one starved
  /// excursion — the two causes the trend chart exists to separate.
  List<CycleSummary> _historyA() => [
        for (var i = 0; i < 20; i++)
          CycleSummary(
            cycleNo: _goodA - 20 + i,
            total: Duration(milliseconds: 7600 + i * 30 + (i == 12 ? 2600 : 0)),
            workTime: Duration(milliseconds: 5200 + i * 30),
            waitTime: Duration(milliseconds: 2400 + (i == 12 ? 2600 : 0)),
            byClass: [
              Duration(milliseconds: 5200 + i * 30), // work: creeping up
              Duration(milliseconds: 1700 + (i == 12 ? 2600 : 0)), // starved
              const Duration(milliseconds: 700), // blocked
              Duration.zero,
              Duration.zero,
            ],
          ),
      ];

  final _bus = StreamController<List<BusNode>>.broadcast();
  @override
  Stream<List<BusNode>> fieldbus() {
    scheduleMicrotask(_publishBus);
    return _bus.stream;
  }

  // The simulation publishes its bus tree immediately, so an empty fieldbus
  // means none — no separate loading state.
  @override
  bool get fieldbusExpected => false;

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
        forced: true,
        quality: c.quality,
        faultActive: c.faultActive,
        diagnosticKey: c.diagnosticKey,
        forceable: c.forceable);
  }

  void _publishBus() {
    // EtherCAT-style: IPC master -> coupler -> terminals. CylB's sensor terminal
    // reflects the same fault the module tree shows (two lenses on one event).
    final tree = <BusNode>[
      BusNode(
        name: 'EtherCAT Master',
        descriptionKey: 'project.hardware.ethercatMaster',
        typeId: 'TwinCAT EtherCAT',
        address: 'AmsNetId .1.1',
        state: NodeState.operational,
        children: [
          BusNode(
            name: 'EK1100 Coupler',
            descriptionKey: 'project.hardware.ek1100',
            typeId: 'Beckhoff EK1100',
            address: 'pos 0',
            state: _cylBError ? NodeState.safeop : NodeState.operational,
            children: [
              BusNode(
                name: 'EL1008 DI',
                descriptionKey: 'project.hardware.el1008',
                typeId: 'Beckhoff EL1008 (8x DI)',
                address: 'pos 1',
                state: _cylBError ? NodeState.fault : NodeState.operational,
                linkOk: !_cylBError,
                channels: [
                  IoChannel(
                      name: 'CylB.WorkFb[1]',
                      descriptionKey: 'project.io.cylBWorkFb1',
                      path: 'StationA.ClampStation.CylB.WorkFb1',
                      modulePath: 'StationA.ClampStation.CylB',
                      dir: ChannelDir.input,
                      kind: ChannelKind.digital,
                      boolValue: !_cylBError,
                      quality: !_cylBError),
                  IoChannel(
                      name: 'CylB.WorkFb[2]',
                      descriptionKey: 'project.io.cylBWorkFb2',
                      path: 'StationA.ClampStation.CylB.WorkFb2',
                      modulePath: 'StationA.ClampStation.CylB',
                      dir: ChannelDir.input,
                      kind: ChannelKind.digital,
                      boolValue: false,
                      quality: !_cylBError),
                  const IoChannel(
                      name: 'CylA.HomeFb[1]',
                      path: 'StationA.ClampStation.CylA.HomeFb1',
                      modulePath: 'StationA.ClampStation.CylA',
                      dir: ChannelDir.input,
                      kind: ChannelKind.digital,
                      boolValue: true),
                  const IoChannel(
                      name: 'Guard closed',
                      descriptionKey: 'project.io.guardClosed',
                      path: 'StationA.Guard',
                      modulePath: 'StationA',
                      dir: ChannelDir.input,
                      kind: ChannelKind.digital,
                      boolValue: true),
                ],
              ),
              const BusNode(
                name: 'EL2008 DO',
                typeId: 'Beckhoff EL2008 (8x DO)',
                address: 'pos 2',
                channels: [
                  IoChannel(
                      name: 'CylB.ToWorkOut',
                      path: 'StationA.ClampStation.CylB.ToWork',
                      modulePath: 'StationA.ClampStation.CylB',
                      dir: ChannelDir.output,
                      kind: ChannelKind.digital,
                      forceable: true,
                      boolValue: true),
                  IoChannel(
                      name: 'Separator.Extend',
                      path: 'StationA.Separator1.Extend',
                      modulePath: 'StationA.Separator1',
                      dir: ChannelDir.output,
                      kind: ChannelKind.digital,
                      forceable: true,
                      boolValue: false),
                  IoChannel(
                      name: 'StatusLamp',
                      path: 'StationA.StatusLamp',
                      modulePath: 'StationA',
                      dir: ChannelDir.output,
                      kind: ChannelKind.digital,
                      boolValue: false),
                ],
              ),
              const BusNode(
                name: 'EL3021 AI',
                typeId: 'Beckhoff EL3021 (analog in)',
                address: 'pos 3',
                channels: [
                  IoChannel(
                      name: 'Clamp pressure',
                      path: 'StationA.ClampStation.Pressure',
                      modulePath: 'StationA.ClampStation',
                      dir: ChannelDir.input,
                      kind: ChannelKind.analog,
                      analogValue: 5.8,
                      unit: 'bar'),
                  IoChannel(
                      name: 'Supply pressure',
                      path: 'StationA.Supply',
                      modulePath: 'StationA',
                      dir: ChannelDir.input,
                      kind: ChannelKind.analog,
                      analogValue: 6.1,
                      unit: 'bar'),
                ],
              ),
            ],
          ),
          const BusNode(
            name: 'AX5000 Drive',
            typeId: 'Beckhoff AX5000',
            address: 'pos 4',
            state: NodeState.operational,
            channels: [
              IoChannel(
                  name: 'Robot axis position',
                  path: 'StationA.Robot.Axis',
                  modulePath: 'StationA.Robot',
                  dir: ChannelDir.input,
                  kind: ChannelKind.analog,
                  analogValue: 245.7,
                  unit: 'mm'),
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
    final mode = rootPath.startsWith('StationA') ? _modeA : _modeB;
    if (mode != UnitMode.manual) {
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

  void _audit(String what, String who) {
    // §8.3: forces are logged events (audit trail); come+gone -> lands in the ring
    _ringA.add(AlarmEvent(
        severity: Severity.low,
        description: '$what: $who',
        sourcePath: 'Access',
        resetClass: ResetClass.autoReset,
        state: AlarmState.closed,
        comeAt: DateTime.now(),
        goneAt: DateTime.now(),
        duration: Duration.zero));
    _publish();
  }

  @override
  Future<bool> login(String rootPath, String user, String secret) async {
    final u = _users[user];
    final ok = u != null && u.$1 == secret;
    final prior = _accessFor(rootPath);
    final next = ok
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
    if (rootPath.startsWith('ConveyorB')) {
      _accessB = next;
    } else {
      _accessA = next;
    }
    _publish();
    return ok;
  }

  @override
  Future<void> logout(String rootPath) async {
    final prior = _accessFor(rootPath);
    if (rootPath.startsWith('ConveyorB')) {
      _accessB = AccessSession(
          required: prior.required, sessionTimeout: prior.sessionTimeout);
    } else {
      _accessA = AccessSession(
          required: prior.required, sessionTimeout: prior.sessionTimeout);
    }
    _publish();
  }

  @override
  Future<bool> setAccessLevel(
      String rootPath, GatedAction action, AccessLevel level) async {
    final prior = _accessFor(rootPath);
    if (!prior.permits(GatedAction.accessPolicy)) return false;
    if (action == GatedAction.accessPolicy && level.index > prior.level.index)
      return false;
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
        timeout > const Duration(days: 7)) return false;
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

  @override
  Future<bool> setMode(String unitPath, UnitMode mode) async {
    if (!_accessFor(unitPath).permits(GatedAction.modeChange))
      return false; // PLC re-check (7.7c)
    if (unitPath.startsWith('StationA'))
      _modeA = mode;
    else
      _modeB = mode;
    _publish();
    return true;
  }

  @override
  Future<bool> setModel(String rootPath, String modelCode) async {
    if (!_accessFor(rootPath).permits(GatedAction.changeover)) return false;
    if (rootPath == 'StationA')
      _modelA = modelCode;
    else
      _modelB = modelCode;
    _publish();
    return true;
  }

  @override
  Future<bool> start(String unitPath) async {
    final report = await releaseReportStart(unitPath);
    return report.released;
  }

  @override
  Future<bool> stop(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.startStop)) return false;
    if (unitPath.startsWith('StationA')) {
      _stopPendingA = true;
      _stopTicks = 3;
      _publish();
    } // finishing window
    return true;
  }

  @override
  Future<bool> controlOn(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.powerControl)) return false;
    if (unitPath.startsWith('StationA')) _controlOnA = true;
    _publish();
    return true;
  }

  @override
  Future<bool> controlOff(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.powerControl)) return false;
    if (unitPath.startsWith('StationA')) _controlOnA = false;
    _publish();
    return true;
  }

  @override
  Future<bool> operatorReset(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.alarmReset)) return false;
    if (!unitPath.startsWith('StationA')) return false;
    if (_cylBError) {
      _cylBError = false; // condition gone -> WAIT_RESET stays blocking...
    } else if (_blockingA) {
      _blockingA = false; // ...until this deliberate reset closes it (8.3b)
      _ringA.add(AlarmEvent(
          severity: Severity.high,
          description: 'Cylinder did not reach extended',
          sourcePath: 'StationA.ClampStation.CylB',
          resetClass: ResetClass.manualReset,
          state: AlarmState.closed,
          comeAt: DateTime.now().subtract(const Duration(seconds: 8)),
          goneAt: DateTime.now(),
          duration: const Duration(seconds: 8)));
    }
    _publish();
    return true;
  }

  @override
  Future<bool> lampTest(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.manual)) return false;
    _audit('Signal tower lamp test', unitPath);
    return true;
  }

  @override
  Future<bool> setDecisionAnswer(String unitPath, int option) async {
    if (!_accessFor(unitPath).permits(GatedAction.startStop) ||
        !_robotMsg ||
        option < 1 ||
        option > 2) return false;
    _robotMsg = false;
    _audit('Decision accepted: option $option', unitPath);
    return true;
  }

  @override
  Future<ReleaseReport> releaseReportStart(String unitPath) async {
    final reasons = <ReleaseReason>[];
    final stationA = unitPath.startsWith('StationA');
    final mode = stationA ? _modeA : _modeB;
    if (!_accessFor(unitPath).permits(GatedAction.startStop)) {
      reasons.add(ReleaseReason(
          'std.release.insufficientStartStop', ReleaseKind.access,
          sourcePath: unitPath));
    }
    if (stationA && _blockingA) {
      reasons.add(ReleaseReason('std.release.manualReset', ReleaseKind.alarm,
          sourcePath: unitPath));
    }
    if (stationA && _cylBError) {
      reasons.add(const ReleaseReason(
          'project.interlock.cylinderPosition', ReleaseKind.interlock,
          sourcePath: 'StationA.ClampStation.CylB'));
    }
    if (stationA && !_controlOnA) {
      reasons.add(ReleaseReason(
          'std.release.controlPowerOff', ReleaseKind.interlock,
          sourcePath: unitPath));
    }
    if (mode != UnitMode.auto) {
      reasons.add(ReleaseReason('std.release.notRunnable', ReleaseKind.mode,
          sourcePath: unitPath));
    }
    return ReleaseReport(reasons.isEmpty, reasons);
  }

  @override
  Future<ReleaseReport> releaseReportAction(
      String unitPath, GatedAction action) async {
    final reasons = <ReleaseReason>[];
    final stationA = unitPath.startsWith('StationA');
    if (!_accessFor(unitPath).permits(action)) {
      reasons.add(ReleaseReason(
          'std.release.insufficientAction', ReleaseKind.access,
          sourcePath: unitPath));
    }
    switch (action) {
      case GatedAction.changeover:
        if ((stationA ? _modeA : _modeB) == UnitMode.auto &&
            !(stationA && _blockingA))
          reasons.add(ReleaseReason(
              'std.release.changeoverRunning', ReleaseKind.mode,
              sourcePath: unitPath));
      case GatedAction.alarmReset:
        if (!stationA || !_blockingA)
          reasons.add(ReleaseReason(
              'std.release.noBlockingAlarm', ReleaseKind.other,
              sourcePath: unitPath));
      default:
    }
    return ReleaseReport(reasons.isEmpty, reasons);
  }

  @override
  Future<ReleaseReport> releaseReportManual(
      String unitPath, String targetPath, int commandValue) async {
    final reasons = <ReleaseReason>[];
    final mode = unitPath.startsWith('StationA') ? _modeA : _modeB;
    if (mode != UnitMode.manual)
      reasons.add(ReleaseReason(
          'std.release.manualModeRequired', ReleaseKind.mode,
          sourcePath: unitPath));
    if (!_accessFor(unitPath).permits(GatedAction.manual))
      reasons.add(ReleaseReason(
          'std.release.insufficientManual', ReleaseKind.access,
          sourcePath: unitPath));
    return ReleaseReport(reasons.isEmpty, reasons);
  }

  @override
  Future<bool> shelveAlarm(String unitPath, String sourcePath,
      String description, Duration duration) async {
    if (!_accessFor(unitPath).permits(GatedAction.alarmShelve)) {
      _audit('Shelve DENIED', sourcePath);
      return false;
    }
    // §8.10: only rationalized+shelvable reasons; CylB timeout (10112) is, discrepancy isn't
    final key = '$sourcePath|$description';
    _shelved.add(key);
    _audit('Shelved', sourcePath);
    _publish();
    return true;
  }

  @override
  Future<bool> unshelveAlarm(
      String unitPath, String sourcePath, String description) async {
    if (!_accessFor(unitPath).permits(GatedAction.alarmShelve)) return false;
    _shelved.remove('$sourcePath|$description');
    _audit('Unshelved', sourcePath);
    _publish();
    return true;
  }

  @override
  Future<bool> resetOee(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.dataWrite)) {
      _audit('OEE reset DENIED', unitPath);
      return false;
    }
    if (unitPath.startsWith('StationA')) {
      _goodA = 0;
      _nokA = 0;
    } else {
      _goodB = 0;
    }
    _audit('OEE reset', unitPath);
    _publish();
    return true;
  }

  @override
  Future<bool> writeConfig(
      String nodePath, CfgField field, String value) async {
    if (!_accessFor(nodePath).permits(GatedAction.dataWrite)) {
      _audit('Config write DENIED', '$nodePath.${field.name}');
      return false;
    }
    CfgField? capability;
    if (nodePath == 'StationA') {
      for (final candidate in _configFields()) {
        if (candidate.writeKey == field.writeKey) {
          capability = candidate;
          break;
        }
      }
    }
    final trimmed = value.trim();
    if (capability == null ||
        !capability.hasWriteCapability ||
        capability.writeRevision != field.writeRevision ||
        !capability.accepts(trimmed)) {
      _audit('Config write REJECTED', '$nodePath.${field.name}');
      return false;
    }
    _configValues[capability.name] = trimmed;
    _audit('Config write', '$nodePath.${capability.name}');
    _publish();
    return true;
  }

  @override
  Future<bool> setRunStyle(String unitPath, RunStyle style) async {
    if (!_accessFor(unitPath).permits(GatedAction.modeChange)) return false;
    if (!unitPath.startsWith('StationA') && style != RunStyle.continuous)
      return false;
    if (unitPath.startsWith('StationA')) _runStyleA = style;
    _publish();
    return true;
  }

  @override
  Future<void> stepRequest(String unitPath) async {
    if (!_accessFor(unitPath).permits(GatedAction.startStop)) return;
    if (unitPath.startsWith('StationA') && _runStyleA == RunStyle.singleStep) {
      _goodA++;
      _publish();
    }
  } // sim: one step ~ one cycle tick

  @override
  Future<void> setHoldRun(String unitPath, bool held) async {}

  @override
  Future<bool> manualCommand(
      String unitPath, String targetPath, int value) async {
    // §7.6.1: MANUAL mode of the owning Unit AND MANUAL access, else reject (audited)
    final inManual =
        _modeA == UnitMode.manual; // StationA is the commandable root here
    if (!inManual) {
      _audit('Manual cmd rejected (not MANUAL)', targetPath);
      return false;
    }
    if (!_accessFor(unitPath).permits(GatedAction.manual)) {
      _audit('Manual cmd DENIED', targetPath);
      return false;
    }
    _audit('Manual cmd: $targetPath = $value', targetPath);
    return true;
  }

  @override
  void setFieldbusViewActive(bool active) {
    // Simulation publishes everything in-memory; there is no read tier to gate.
  }

  @override
  void setModuleDetailActive(String rootPath, bool active) {}

  @override
  void dispose() {
    _timer?.cancel();
    _ctrl.close();
    _link.close();
    _bus.close();
  }

  AccessSession _accessFor(String path) =>
      path.startsWith('ConveyorB') ? _accessB : _accessA;

  void _setAccess(String path, AccessSession value) {
    if (path.startsWith('ConveyorB')) {
      _accessB = value;
    } else {
      _accessA = value;
    }
    _publish();
  }
}
