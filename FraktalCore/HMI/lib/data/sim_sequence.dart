/// The sequence engine behind [SimRepository]'s chains (Core §3.13, §6.5,
/// §6.9, §6.12, §8.11.4).
///
/// One engine runs every chain the demo publishes, so the flow chart, the
/// current step, the cycle profile, the trend and the step Pareto are all
/// derived from the steps the chain actually took - the way the PLC base
/// derives them - instead of from tables invented separately for each view.
/// That is the property a screenshot of the demo has to be honest about: a
/// Gantt bar and the chart row it came from always agree.
library;

import '../domain/types.dart';

/// One step of a simulated chain, in chart order.
///
/// A step with [legs] is a §6.12 fork: the main line stays on it while every
/// leg runs on its own row, and it completes when the last leg has. Each leg
/// is a single step here, which is all the demo needs to draw a parallel
/// branch; a PLC leg is a whole sub-chain.
class SimStepDef {
  final int stepNo;

  /// Catalog key of the step's title, exactly as `M_Step` publishes it.
  final String name;
  final String awaitingLabel;

  /// The module this step commands; empty = not click-through (§3.13).
  final String awaitsPath;
  final TimeClass timeClass;

  /// The §8.11.4(c) declared guard; zero = none declared.
  final Duration expected;

  /// How long the simulated plant normally takes for this step.
  final Duration nominal;
  final List<SimStepDef> legs;

  /// §3.4.2 per-step stop point for single-step running.
  final bool steppable;

  const SimStepDef(
    this.stepNo,
    this.name, {
    this.awaitingLabel = '',
    this.awaitsPath = '',
    this.timeClass = TimeClass.work,
    this.expected = Duration.zero,
    this.nominal = const Duration(seconds: 1),
    this.legs = const [],
    this.steppable = true,
  });
}

/// One chart row's live bookkeeping (the §3.13 `SequenceSteps` record).
class _Row {
  final SimStepDef def;
  final int branch;
  bool visited = false;
  Duration lastDuration = Duration.zero;
  bool active = false;
  Duration elapsed = Duration.zero;
  Duration required = Duration.zero;
  bool done = false; // a leg that finished while its fork is still open
  String errorSource = '';
  bool error = false;
  String warningKey = '';
  String warningSource = '';
  bool warning = false;

  _Row(this.def, this.branch);

  SequenceStep publish({required bool timedOut}) => SequenceStep(
        stepNo: def.stepNo,
        branch: branch,
        stepName: def.name,
        awaitingLabel: def.awaitingLabel,
        awaitsPath: def.awaitsPath,
        timeClass: def.timeClass,
        expected: def.expected,
        visited: visited,
        lastDuration: lastDuration,
        active: active,
        elapsed: active ? elapsed : Duration.zero,
        timedOut: timedOut,
        errorActive: error,
        errorSourcePath: errorSource,
        warningActive: warning,
        warningKey: warningKey,
        warningSourcePath: warningSource,
      );
}

/// A simulated chain: a cursor over [steps] advanced by [advance].
///
/// The plant decides the timing through [duration] (how long a step takes on
/// this pass) and [holds] (a step that may not complete yet - a fault, an
/// unanswered prompt). Everything the HMI renders is then read back from the
/// rows, exactly once.
class SimChain {
  final List<SimStepDef> steps;

  /// AUTO repeats; HOME and CHANGEOVER run once and finish.
  final bool repeats;
  final Duration Function(SimStepDef step, int cycleNo) duration;
  final bool Function(SimStepDef step)? holds;
  final void Function(SimStepDef step, int cycleNo)? onEnter;
  final void Function(SimStepDef step, Duration took, int cycleNo)? onComplete;
  final void Function(int cycleNo)? onCycle;

  /// §8.11.4 ring depth, as the PLC profiler keeps it.
  static const historyDepth = 20;

  final List<_Row> _rows = [];
  final Map<int, _Row> _mainRows = {};
  final Map<int, List<_Row>> _legRows = {};
  int _index = -1;
  bool _finished = false;
  int cycleNo = 0;

  final Map<int, Duration> _thisCycle = {};
  final List<CycleSummary> _history = [];
  final Map<int, ({int count, Duration total, Duration max})> _stats = {};
  CycleProfile? _lastProfile;

  SimChain({
    required this.steps,
    required this.duration,
    this.repeats = true,
    this.holds,
    this.onEnter,
    this.onComplete,
    this.onCycle,
  }) {
    for (final step in steps) {
      final row = _Row(step, 0);
      _rows.add(row);
      _mainRows[step.stepNo] = row;
      final legs = <_Row>[];
      for (var i = 0; i < step.legs.length; i++) {
        final leg = _Row(step.legs[i], i + 1);
        _rows.add(leg);
        legs.add(leg);
      }
      _legRows[step.stepNo] = legs;
    }
  }

  bool get running => _index >= 0 && !_finished;

  /// A chain that ran once to its end (HOME, CHANGEOVER).
  bool get finished => _finished;

  SimStepDef? get currentStep => running ? steps[_index] : null;

  /// Start from the first step. [clearChart] is the §3.13 mode boundary: a new
  /// mode builds its own chart, so the rows it inherited are forgotten.
  void restart({bool clearChart = false}) {
    for (final row in _rows) {
      row.active = false;
      row.done = false;
      row.elapsed = Duration.zero;
      row.error = false;
      row.errorSource = '';
      if (clearChart) {
        row.visited = false;
        row.lastDuration = Duration.zero;
        row.warning = false;
        row.warningKey = '';
        row.warningSource = '';
      }
    }
    _finished = false;
    _thisCycle.clear();
    _enter(0);
  }

  /// §6.9(d) - once the error is reset the step it stopped on is re-armed:
  /// its command is issued again and tested again, never resumed mid-way.
  void restartStep() {
    if (!running) return;
    for (final row in _rows) {
      row.active = false;
      row.elapsed = Duration.zero;
    }
    _enter(_index);
  }

  /// Park the cursor: nothing is live, the history stays.
  void park() {
    for (final row in _rows) {
      row.active = false;
      row.elapsed = Duration.zero;
    }
    _index = -1;
    _finished = false;
  }

  /// Run [dt] of plant time. [mayComplete] is false while a §3.4.2 single
  /// step waits for its next step request: the step runs, but does not leave.
  /// [stopAtCycleEnd] is a graceful Stop: the cycle finishes, then the chain
  /// parks instead of starting the next one. Returns true when a cycle ended.
  bool advance(Duration dt,
      {bool mayComplete = true, bool stopAtCycleEnd = false}) {
    if (!running) return false;
    final step = steps[_index];
    final row = _mainRows[step.stepNo]!;
    row.elapsed += dt;
    final legs = _legRows[step.stepNo]!;
    var legsOpen = false;
    for (final leg in legs) {
      if (leg.done) continue;
      leg.elapsed += dt;
      if (leg.elapsed >= leg.required && !(holds?.call(leg.def) ?? false)) {
        _close(leg, leg.required);
        leg.done = true;
        onComplete?.call(leg.def, leg.lastDuration, cycleNo);
      } else {
        legsOpen = true;
      }
    }
    final due = legs.isEmpty ? row.elapsed >= row.required : !legsOpen;
    if (!due || !mayComplete || (holds?.call(step) ?? false)) return false;
    // A step that was held past its time took as long as it was held.
    final took = legs.isEmpty && row.elapsed <= row.required + dt
        ? row.required
        : row.elapsed;
    _close(row, took);
    _thisCycle[step.stepNo] = took;
    onComplete?.call(step, took, cycleNo);
    if (_index + 1 < steps.length) {
      _enter(_index + 1);
      return false;
    }
    _completeCycle();
    if (repeats && !stopAtCycleEnd) {
      _enter(0);
    } else if (repeats) {
      park();
    } else {
      _finished = true;
      _index = -1;
    }
    return true;
  }

  /// §6.9(d) - the chain stops ON the step; its row carries the error and the
  /// drill-down link to the module that actually failed.
  void raiseError(int stepNo, String sourcePath) {
    final row = _row(stepNo);
    if (row == null) return;
    row.error = true;
    row.errorSource = sourcePath;
  }

  void clearErrors() {
    for (final row in _rows) {
      row.error = false;
      row.errorSource = '';
    }
  }

  /// §6.9(e) - a handled condition: the step reports it and carries on. The
  /// mark is history (this pass warned), cleared when the step is next entered.
  void markWarning(int stepNo, String key, String sourcePath) {
    final row = _row(stepNo);
    if (row == null) return;
    row.warning = true;
    row.warningKey = key;
    row.warningSource = sourcePath;
  }

  _Row? _row(int stepNo) {
    for (final row in _rows) {
      if (row.def.stepNo == stepNo) return row;
    }
    return null;
  }

  void _enter(int index) {
    _index = index;
    final step = steps[index];
    final row = _mainRows[step.stepNo]!;
    row.active = true;
    row.elapsed = Duration.zero;
    row.warning = false;
    row.warningKey = '';
    row.warningSource = '';
    row.required = duration(step, cycleNo);
    for (final leg in _legRows[step.stepNo]!) {
      leg.active = true;
      leg.done = false;
      leg.elapsed = Duration.zero;
      leg.warning = false;
      leg.warningKey = '';
      leg.warningSource = '';
      leg.required = duration(leg.def, cycleNo);
      onEnter?.call(leg.def, cycleNo);
    }
    onEnter?.call(step, cycleNo);
  }

  void _close(_Row row, Duration took) {
    row.active = false;
    row.visited = true;
    row.lastDuration = took;
    row.elapsed = Duration.zero;
  }

  void _completeCycle() {
    final timings = [
      for (final step in steps)
        StepTiming(step.stepNo, step.name, step.timeClass,
            _thisCycle[step.stepNo] ?? Duration.zero, step.expected),
    ];
    final byClass =
        List<Duration>.filled(TimeClass.values.length, Duration.zero);
    var total = Duration.zero;
    for (final t in timings) {
      byClass[t.timeClass.index] += t.duration;
      total += t.duration;
      final prior = _stats[t.stepNo];
      _stats[t.stepNo] = (
        count: (prior?.count ?? 0) + 1,
        total: (prior?.total ?? Duration.zero) + t.duration,
        max: prior == null || t.duration > prior.max ? t.duration : prior.max,
      );
    }
    final work = byClass[TimeClass.work.index];
    cycleNo++;
    _lastProfile = CycleProfile(
      cycleNo: cycleNo,
      total: total,
      workTime: work,
      waitTime: total - work,
      steps: timings,
    );
    _history.add(CycleSummary(
      cycleNo: cycleNo,
      total: total,
      workTime: work,
      waitTime: total - work,
      byClass: List.unmodifiable(byClass),
    ));
    if (_history.length > historyDepth) _history.removeAt(0);
    _thisCycle.clear();
    onCycle?.call(cycleNo);
  }

  // ---- what the HMI reads ----

  /// The §3.13 rows, in chart order (a fork's legs follow it).
  List<SequenceStep> get rows {
    final current = currentStep;
    return [
      for (final row in _rows)
        row.publish(
          timedOut: row.active &&
              row.def.expected > Duration.zero &&
              row.elapsed > row.def.expected &&
              (row.branch > 0 || row.def.stepNo == current?.stepNo),
        ),
    ];
  }

  /// §6.5 - the main line's current step; stepNo 0 = none.
  StepInfo currentInfo({
    List<CondInfo> conds = const [],
    bool starved = false,
    bool blocked = false,
  }) {
    final step = currentStep;
    if (step == null) return const StepInfo();
    return StepInfo(
      stepNo: step.stepNo,
      stepName: step.name,
      awaitingLabel: step.awaitingLabel,
      timeClass: step.timeClass,
      expected: step.expected,
      conds: conds,
      starved: starved,
      blocked: blocked,
      steppable: step.steppable,
    );
  }

  Duration get currentElapsed {
    final step = currentStep;
    return step == null ? Duration.zero : _mainRows[step.stepNo]!.elapsed;
  }

  /// The main line outran its guard (§6.9 stall watchdog).
  bool get currentTimedOut {
    final step = currentStep;
    return step != null &&
        step.expected > Duration.zero &&
        _mainRows[step.stepNo]!.elapsed > step.expected;
  }

  CycleProfile? get lastProfile => _lastProfile;

  /// §8.11.4 trend ring, oldest first.
  List<CycleSummary> get history => List.unmodifiable(_history);

  Duration get lastCycleTime => _lastProfile?.total ?? Duration.zero;

  Duration get bestCycleTime => _history.isEmpty
      ? Duration.zero
      : _history.map((c) => c.total).reduce((a, b) => a < b ? a : b);

  /// §8.11.4 Pareto source: average and worst per main-line step.
  List<StepStat> get stats => [
        for (final step in steps)
          if (_stats[step.stepNo] case final s?)
            StepStat(step.stepNo, step.name, step.timeClass, s.total ~/ s.count,
                s.max),
      ];
}
