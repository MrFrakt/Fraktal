/// Abstract PLC access — the whole UI is written against this, so transports
/// swap without UI changes (HMI_CONTRACT 'Transports'):
///   SimRepository        — ships now; full demo on every platform (Core O6)
///   OPC UA (FFI client)  — Windows/Linux/Android; deployment adapter
///   Gateway (WebSocket)  — required for Web (browsers cannot open raw TCP)
library;

import '../domain/module_node.dart';
import '../domain/types.dart';
import '../domain/fieldbus.dart';

abstract class PlcRepository {
  /// The forest (Core 3.1a): one or more root Units, republished on change.
  Stream<List<ModuleNode>> forest();

  /// Transport liveness — an HMI must always show whether it's talking to the PLC.
  Stream<LinkState> linkState();

  /// Fieldbus topology (Core §10.5.1): auto-detected physical bus tree. Empty
  /// stream is valid (no fieldbus diagnostics available on this transport).
  Stream<List<BusNode>> fieldbus();

  /// Whether a fieldbus topology has been discovered but its tree may not be
  /// populated yet. Lets the fieldbus view show a loading indicator (data is on
  /// its way) instead of the "no fieldbus" empty state. Transports that publish
  /// the tree cyclically leave this false (an empty [fieldbus] then means truly
  /// none); the direct OPC UA/ADS transport sets it once the topology symbol is
  /// discovered, before the on-demand read has filled the tree.
  bool get fieldbusExpected => false;

  // ---- write surface (HMI_CONTRACT: narrow, PLC re-checks everything, 7.7) ----
  Future<bool> login(String rootPath, String user, String secret);
  Future<void> logout(String rootPath);

  /// §7.7 — edit the PLC-authoritative per-root access policy. The PLC gates
  /// these writes with ACCESS_POLICY and persists them; the HMI is only an
  /// editor for the published policy.
  Future<bool> setAccessLevel(
      String rootPath, GatedAction action, AccessLevel level);
  Future<bool> setSessionTimeout(String rootPath, Duration timeout);

  Future<bool> setMode(String unitPath, UnitMode mode);
  Future<bool> setModel(String rootPath, String modelCode);
  Future<bool> start(String unitPath);
  Future<bool> stop(String unitPath);
  Future<bool> controlOn(String unitPath);
  Future<bool> controlOff(String unitPath);
  Future<bool> operatorReset(String unitPath);

  /// §8.13 — starts the PLC-bounded signal-tower lamp/horn test.
  Future<bool> lampTest(String unitPath);
  Future<bool> setDecisionAnswer(String unitPath, int option);

  /// §7.6.1 — issue a manual command to a module. Accepted only when the owning
  /// Unit is in MANUAL (§3.4) and the user holds MANUAL access (§7.7); routed
  /// through the module so interlocks still defend. Returns false if rejected.
  Future<bool> manualCommand(String unitPath, String targetPath, int value);

  /// §7.6.1a hold-to-run. [held] true latches/refreshes the request; false
  /// releases it. Implementations do NOT need the client to poll - but a held
  /// control MUST refresh within the PLC's MANUAL_HELD_REFRESH_MS window or the
  /// root lets go on the client's behalf.
  Future<bool> manualHeld(
      String unitPath, String targetPath, int value, bool held);

  // §3.4.2 run style + single-step (Units)
  Future<bool> setRunStyle(String unitPath, RunStyle style);
  Future<void> stepRequest(String unitPath);
  Future<void> setHoldRun(String unitPath, bool held);

  /// §7.8 — pure queries: the full rollup of why Start / a manual command is
  /// blocked right now (mode + access + alarms + interlocks). Never commands.
  Future<ReleaseReport> releaseReportStart(String unitPath);
  Future<ReleaseReport> releaseReportManual(
      String unitPath, String targetPath, int commandValue);

  /// §7.8 — generic rollup for the simpler gated Unit actions (Stop, reset,
  /// changeover, step, mode change). Same predicate the gate uses.
  Future<ReleaseReport> releaseReportAction(
      String unitPath, GatedAction action);

  /// §8.5.1 — clear OEE accumulators + trend (shift start). DATA_WRITE-gated, audited.
  Future<bool> resetOee(String unitPath);

  /// §3.8a — write one published ParCfg/StationCfg field. The PLC validates
  /// type/schema and re-checks DATA_WRITE; false means rejected with no partial load.
  Future<bool> writeConfig(String nodePath, CfgField field, String value);

  /// §8.10 — shelve/unshelve an active alarm's ANNUNCIATION (never control).
  /// Identity = sourcePath+description of the active event. ALARM_SHELVE-gated.
  Future<bool> shelveAlarm(String unitPath, String sourcePath,
      String description, Duration duration);
  Future<bool> unshelveAlarm(
      String unitPath, String sourcePath, String description);

  /// §7.6.0 — full rollup of why a gated action is currently withheld (empty =
  /// released). Read-only; safe to poll while a 'not released' panel is shown.

  /// Force/unforce a fieldbus channel (Core §10.5.1). Gated by §7.6 (manual
  /// release) + §7.7 (MANUAL level) and re-checked in the PLC; every force is a
  /// logged §8.3 event. Returns false if denied. rootPath supplies the session.
  Future<bool> forceChannel(String rootPath, String channelPath,
      {required bool force, bool boolValue = false, double analogValue = 0});

  /// Signals whether the operator is currently viewing the fieldbus diagnostics
  /// page. Transports that publish the fieldbus tree cyclically ignore this; the
  /// direct OPC UA transport treats the fieldbus I/O tree as on-demand data and
  /// only reads it while the page is active, keeping it off the 2 Hz snapshot
  /// (Core §3.13 — the bus view is a drill-down, not always-visible). Default
  /// no-op so a transport opts in only when it tiers reads.
  void setFieldbusViewActive(bool active) {}

  /// Signals whether a module detail page for [rootPath] is open. The direct
  /// OPC UA transport gates that root's large drill-down rings/trends (alarm
  /// history, cycle/OEE trend, part records, command timing) as on-demand data —
  /// read only while its detail is visible, never cyclically — so continuous
  /// polling of history arrays cannot flood the server's ADS handle pool or
  /// stall interactive commands. Default no-op.
  void setModuleDetailActive(String rootPath, bool active) {}

  void dispose();
}
