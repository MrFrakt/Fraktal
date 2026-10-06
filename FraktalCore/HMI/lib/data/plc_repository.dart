/// Abstract PLC access — the whole UI is written against this, so transports
/// swap without UI changes (HMI_CONTRACT 'Transports'):
///   SimRepository        — ships now; full demo on every platform (Core O6)
///   OPC UA (FFI client)  — Windows/Linux/Android; deployment adapter
///   Gateway (WebSocket)  — required for Web (browsers cannot open raw TCP)
library;

import '../domain/module_node.dart';
import '../domain/types.dart';
import '../domain/fieldbus.dart';

/// ST_HmiRequest.TextValue is STRING(255): what one request can carry.
const int kConfigSetRequestTextMax = 255;

/// The widest set line the PLC renders and accepts (its STRING(480) document
/// line). A longer line is refused by name before anything is sent.
const int kConfigSetImportLineMax = 480;

/// [line] as the pieces an import sends (§3.8b): at most
/// [kConfigSetRequestTextMax] characters each. Every piece but the last is
/// sent with IntValue = 1 ("more follows"), and the PLC joins them - so a line
/// the PLC exported can always come back, although a request carries 255.
List<String> configSetLinePieces(String line) => [
      for (var start = 0;
          start < line.length || start == 0;
          start += kConfigSetRequestTextMax)
        line.substring(
            start,
            start + kConfigSetRequestTextMax < line.length
                ? start + kConfigSetRequestTextMax
                : line.length),
    ];

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

  /// Core §3.8d(b) - change one data class's read or write level. ACCESS_POLICY
  /// on the PLC, like every other policy edit.
  Future<bool> setClassLevel(String rootPath, String classId, AccessLevel level,
      {required bool forWrite});

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
  ///
  /// [modelIndex] names the model a model-data value ([CfgField.modelScoped])
  /// is written for: 0 = the running model, n = the root's n-th
  /// `availableModels` entry. It is sent only for a model-scoped field - a
  /// controller that publishes none would write the running model instead.
  Future<bool> writeConfig(String nodePath, CfgField field, String value,
      {int modelIndex = 0});

  /// §3.8a — the root's model-data values as stored for model [modelIndex]
  /// (0 = the running model, n = the n-th `availableModels` entry), read from
  /// that model's record without a changeover. Null = refused or unreadable.
  Future<List<CfgField>?> queryModelConfig(String rootPath, int modelIndex);

  /// Core §3.8b - parameter sets on a root. Every call is a CONFIG_SET-gated
  /// PLC request; nothing is cached here. [listConfigSets] returns null when the
  /// PLC refused or the answer could not be read, never an invented empty list.
  Future<List<ConfigSetInfo>?> listConfigSets(String rootPath);
  Future<bool> saveConfigSet(String rootPath, String name, CfgKind kind);

  /// Staged and all-or-nothing on the PLC; a refusal names the offending record
  /// in [configSetRejection].
  Future<bool> loadConfigSet(String rootPath, String name);
  Future<bool> deleteConfigSet(String rootPath, String name);

  /// The set as JSON lines (header first), or null when refused. Each value
  /// needs its own read level on the PLC (§3.8d(e)); an export is never thinned.
  Future<String?> exportConfigSet(String rootPath, String name);
  /// Optional PLC-owned catalog. Clone without changing the running recipe.
  Future<bool> createModel(String rootPath, String code,
      {int sourceModel = 0, String sourceSet = ''});
  /// Immutable PLC snapshot, without consuming a saved-set slot.
  Future<String?> exportCurrentConfig(String rootPath, CfgKind kind,
      {int modelIndex = 0});

  /// Import a document produced by [exportConfigSet]. A line may hold up to
  /// [kConfigSetImportLineMax] characters; longer than one request, it travels
  /// in pieces ([configSetLinePieces]).
  Future<bool> importConfigSet(String rootPath, String document);

  /// The PLC's reason for the last refused set operation ('scope / key'), or ''.
  Future<String> configSetRejection(String rootPath);

  /// §3.8b - accept that a retained configuration image was lost, so the
  /// standing annunciation clears. ENGINEER-gated and re-checked by the PLC.
  ///
  /// This acknowledges the LOSS, never the condition: it does not restore a
  /// value, and under `blockUntilAcknowledged` it is what releases Start - so a
  /// client must never send it on the operator's behalf to clear a banner.
  Future<bool> acknowledgeConfigRestore(String rootPath);

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
  /// [containers] narrows reads to the visible cards (for example History and
  /// StepStats). Null preserves the whole scope; an empty set reads no detail.
  void setModuleDetailActive(String rootPath, bool active,
      {Set<String>? containers}) {}

  void dispose();
}
