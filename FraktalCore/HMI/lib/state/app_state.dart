/// App-wide state (pure ChangeNotifier — no packages). Holds the forest, tree
/// selection/expansion, theme index (level-gated), and the collapsed-rail flag.
library;

import 'dart:async';
import 'package:flutter/foundation.dart';
import '../data/panel_platform.dart';
import '../data/plc_repository.dart';
import '../domain/module_node.dart';
import '../domain/fieldbus.dart';
import '../domain/types.dart';
import '../localization/reason_catalog.g.dart';
import '../content/module_content_controller.dart';
import '../localization/localization_controller.dart';
import '../ui/on_screen_keyboard.dart';
import '../ui/app_theme.dart' show ControlScale, UiMetrics;

class HmiConfig {
  /// Theme changing is HMI-local config, gated by a minimum access level
  /// (default: open) — HMI_CONTRACT 'Tree & theming'.
  final AccessLevel themeMinLevel;

  /// Closing the application is deliberately gated higher than theming: on a
  /// machine panel it removes the operator's view of the process. The level is
  /// editable per deployment (a locked cabinet may want ADMIN; a desk station
  /// may want it open) and defaults to TECHNICIAN.
  final AccessLevel closeAppMinLevel;

  /// **Additional** HMI-local floors for two machine actions the PLC already
  /// gates (§7.7 `MANUAL` / `ALARM_RESET`).
  ///
  /// These can only ever *tighten*: the published PLC policy is still consulted
  /// and the PLC re-checks every request, so a panel can require more than the
  /// PLC does but never less. That matters because a shared panel on the shop
  /// floor may warrant stricter rules than the same PLC allows from an
  /// engineering station. Default `NONE` = defer entirely to the PLC, which is
  /// the behaviour before these existed.
  final AccessLevel manualMinLevel;
  final AccessLevel alarmResetMinLevel;

  const HmiConfig({
    this.themeMinLevel = AccessLevel.none,
    this.closeAppMinLevel = AccessLevel.technician,
    this.manualMinLevel = AccessLevel.none,
    this.alarmResetMinLevel = AccessLevel.none,
  });

  /// The HMI-local floor for [action], or null when this panel adds none.
  AccessLevel? localFloor(GatedAction action) => switch (action) {
        GatedAction.manual => manualMinLevel,
        GatedAction.alarmReset => alarmResetMinLevel,
        _ => null,
      };
}

class AppState extends ChangeNotifier {
  final PlcRepository repo;
  final HmiConfig config;
  final LocalizationController localization;
  final ModuleContentController content;

  /// Persisted UI prefs change hook — the bootstrap wires this to save settings,
  /// so a theme/keyboard change survives reconnect (AppState is rebuilt/connect).
  final VoidCallback? _onUiPrefsChanged;
  bool floatingKeyboard;

  /// Operator-selectable control size (touch targets, icons, rail, tree rows).
  /// Panel pixel density varies widely, so the same 48 px target is comfortable
  /// on one screen and fiddly on another — gloves make it worse.
  ControlScale controlScale;

  /// In-app on-screen keyboard for touch panels (Core O9: minimum surface, no
  /// package). Owned here so the Shell overlay and every TouchTextField share one.
  final OnScreenKeyboardController keyboard = OnScreenKeyboardController();

  /// Panel-host services (close app, fullscreen, keep-awake). Injectable so a
  /// test can substitute a recording double.
  final PanelPlatform panel;

  /// §7.7-style gate for quitting the HMI — see [HmiConfig.closeAppMinLevel].
  bool get mayCloseApp =>
      panel.canCloseApp && session.level.index >= config.closeAppMinLevel.index;

  /// The PLC's published policy for [action] AND this panel's local floor.
  ///
  /// **Always use this instead of `session.permits(...)` for a gated machine
  /// action.** The PLC remains authoritative — it re-checks every request and
  /// can still refuse — but a panel may be configured to require more (see
  /// [HmiConfig.manualMinLevel]). Because both must pass, an HMI-local setting
  /// can never grant something the PLC denies.
  bool permitsLocal(GatedAction action, {AccessSession? forSession}) {
    final active = forSession ?? session;
    if (!active.permits(action)) return false;
    final floor = config.localFloor(action);
    return floor == null || active.level.index >= floor.index;
  }

  /// Quit the application. Returns false when refused (insufficient level or an
  /// unsupported host), so the caller can explain rather than silently no-op.
  Future<bool> closeApp() async {
    if (!mayCloseApp) return false;
    await panel.closeApp();
    return true;
  }

  factory AppState(
    PlcRepository repo, {
    HmiConfig config = const HmiConfig(),
    LocalizationController? localization,
    ModuleContentController? content,
    int initialThemeIndex = 0,
    bool initialFloatingKeyboard = true,
    ControlScale initialControlScale = ControlScale.compact,
    VoidCallback? onUiPrefsChanged,
    PanelPlatform? panel,
  }) {
    final resolvedLocalization = localization ?? LocalizationController();
    return AppState._(
      repo,
      config,
      resolvedLocalization,
      content ?? ModuleContentController(localization: resolvedLocalization),
      initialThemeIndex,
      initialFloatingKeyboard,
      initialControlScale,
      onUiPrefsChanged,
      panel ?? createPanelPlatform(),
    );
  }

  AppState._(
      this.repo,
      this.config,
      this.localization,
      this.content,
      int initialThemeIndex,
      bool initialFloatingKeyboard,
      ControlScale initialControlScale,
      this._onUiPrefsChanged,
      this.panel)
      : themeIndex = initialThemeIndex,
        floatingKeyboard = initialFloatingKeyboard,
        controlScale = initialControlScale {
    keyboard.enabled = floatingKeyboard;
    keyboard.applyMetrics(UiMetrics.of(controlScale));
    _sub = repo.forest().listen((f) {
      final byPath = <String, ModuleNode>{};
      final duplicatePaths = <String>[];
      for (final root in f) {
        if (byPath.containsKey(root.path)) {
          duplicatePaths.add(root.path);
        } else {
          byPath[root.path] = root;
        }
      }
      if (duplicatePaths.isNotEmpty) {
        debugPrint('[Fraktal/Forest] duplicate root paths discarded: '
            '${duplicatePaths.join(', ')}');
      }
      forest = byPath.values.toList(growable: false);
      final selectionVisible = forest.any(
          (root) => selectedPath != null && root.find(selectedPath!) != null);
      if (!selectionVisible) {
        selectedPath = forest.isNotEmpty ? forest.first.path : null;
        scopedRoot = null;
        showOverview = true;
      }
      notifyListeners();
    });
    _linkSub = repo.linkState().listen((s) {
      link = s;
      notifyListeners();
    });
    _busSub = repo.fieldbus().listen((b) {
      fieldbus = b;
      notifyListeners();
    });
  }

  late final dynamic _sub;
  late final dynamic _linkSub;
  late final dynamic _busSub;
  List<BusNode> fieldbus = const [];
  bool showFieldbus = false; // Modules view vs Fieldbus view
  ReleaseReport?
      releaseReport; // §7.8 active 'why blocked' report (null = panel hidden)
  String releaseTitle = '';
  bool releaseLoading = false;
  Future<ReleaseReport> Function()?
      _releaseQuery; // re-run at a controlled rate while the panel is open
  Timer? _releaseTimer;
  bool _releaseRefreshing = false;
  LinkState link = LinkState.connecting;
  bool showOverview =
      true; // land on the plant overview (dashboard-first pattern)
  List<ModuleNode> forest = const [];
  String? selectedPath;
  String? scopedRoot; // null = show whole forest; else single-root scope (3.1a)
  final Set<String> expanded = {};
  bool railCollapsed = false;
  int themeIndex; // index into kThemes (app_theme.dart); 0 = Light Blue

  ModuleNode? get selected {
    for (final r in visibleRoots) {
      final hit = r.find(selectedPath ?? '');
      if (hit != null) return hit;
    }
    return null;
  }

  ModuleNode? rootOf(String path) {
    for (final r in forest) {
      if (path == r.path || path.startsWith('${r.path}.')) return r;
    }
    return null;
  }

  List<ModuleNode> get visibleRoots => scopedRoot == null
      ? forest
      : forest.where((r) => r.path == scopedRoot).toList();

  AccessSession get session =>
      rootOf(selectedPath ?? '')?.access ?? const AccessSession();

  void select(String path) {
    selectedPath = path;
    showOverview = false;
    _syncOnDemandScopes();
    notifyListeners();
  }

  void openOverview() {
    showOverview = true;
    showFieldbus = false;
    _syncOnDemandScopes();
    notifyListeners();
  }

  void setFieldbusView(bool on) {
    showFieldbus = on;
    showOverview = false;
    _syncOnDemandScopes();
    notifyListeners();
  }

  // Activates the on-demand (view-gated) read scopes for the current view so the
  // direct OPC UA transport only reads a module's large drill-down rings/trends
  // while its detail is open, and the fieldbus I/O tree only on the bus page.
  // A no-op on transports that publish everything cyclically. Idempotent — the
  // repository ignores unchanged scopes.
  String? _activeDetailRoot;
  void _syncOnDemandScopes() {
    // A module detail is shown when a specific module is selected and neither
    // the plant overview nor the fieldbus page is active.
    final detailRoot = (!showOverview && !showFieldbus)
        ? rootOf(selectedPath ?? '')?.path
        : null;
    if (detailRoot == _activeDetailRoot) return;
    if (_activeDetailRoot != null) {
      repo.setModuleDetailActive(_activeDetailRoot!, false);
    }
    if (detailRoot != null) repo.setModuleDetailActive(detailRoot, true);
    _activeDetailRoot = detailRoot;
  }

  /// §7.8 — surface why an action is blocked (persistent panel). Pure query.
  Future<void> showReleaseReportStart(String unitPath) async {
    await _showReleaseReport(
      title: 'std.release.startBlocked',
      query: () => repo.releaseReportStart(unitPath),
    );
  }

  Future<void> showReleaseReportManual(
      String unitPath, String targetPath, int commandValue) async {
    await _showReleaseReport(
      title: 'std.release.manualBlocked',
      query: () => repo.releaseReportManual(unitPath, targetPath, commandValue),
    );
  }

  Future<void> showReleaseReportAction(
      String unitPath, GatedAction action, String title) async {
    await _showReleaseReport(
      title: title,
      query: () => repo.releaseReportAction(unitPath, action),
    );
  }

  bool get releasePanelVisible => _releaseQuery != null;

  Future<void> _showReleaseReport({
    required String title,
    required Future<ReleaseReport> Function() query,
  }) async {
    _releaseTimer?.cancel();
    _releaseQuery = query;
    releaseTitle = title;
    releaseReport = null;
    releaseLoading = true;
    notifyListeners();
    await _refreshRelease();
    if (identical(_releaseQuery, query)) {
      _releaseTimer = Timer.periodic(
        const Duration(seconds: 2),
        (_) => _refreshRelease(),
      );
    }
  }

  /// §7.8 — keep the panel live without coupling a mailbox query to every
  /// repository snapshot. OPC UA query acknowledgements themselves publish a
  /// snapshot, so snapshot-driven re-querying creates an unbounded feedback loop.
  Future<void> _refreshRelease() async {
    if (_releaseQuery == null || _releaseRefreshing) return;
    final query = _releaseQuery!;
    _releaseRefreshing = true;
    try {
      final r = await query();
      if (identical(_releaseQuery, query)) {
        releaseReport = r;
        releaseLoading = false;
        notifyListeners();
      }
    } on Object {
      if (identical(_releaseQuery, query)) {
        releaseReport = const ReleaseReport(false, [
          ReleaseReason('std.release.transportUnavailable', ReleaseKind.other),
        ]);
        releaseLoading = false;
        notifyListeners();
      }
    } finally {
      _releaseRefreshing = false;
    }
  }

  void clearRelease() {
    _releaseTimer?.cancel();
    _releaseTimer = null;
    releaseReport = null;
    _releaseQuery = null;
    releaseLoading = false;
    notifyListeners();
  }

  /// All active events across the forest, worst-first — for the global banner.
  List<AlarmEvent> get allActiveEvents {
    final out = <AlarmEvent>[];
    void walk(ModuleNode n) {
      out.addAll(n.activeEvents.where((e) => e.state != AlarmState.closed));
      for (final c in n.children) walk(c);
    }

    for (final r in forest) walk(r);
    out.sort((a, b) => b.severity.index - a.severity.index);
    return out;
  }

  /// Core §7.5.2 — the station's ACTIVE commissioning/engineering gates, one
  /// entry per gate, for the permanent banner.
  ///
  /// Matched by the generated reason SYMBOL rather than by a literal code, so
  /// the number stays owned by the PLC `E_Reason` enum (§8.8) and this cannot
  /// drift from it. Deliberately does NOT filter shelved events: the reason is
  /// rationalized as not suppressible (§8.9), and a banner that could be
  /// silenced would defeat the one property this annunciation exists to have.
  ///
  /// Every root raises its own event for a station-wide gate, so entries are
  /// deduplicated by gate description — a two-Unit station shows one line per
  /// gate, not one per Unit.
  List<AlarmEvent> get activeEngineeringGates {
    final seen = <String>{};
    final out = <AlarmEvent>[];
    for (final event in allActiveEvents) {
      if (generatedReasonSymbolByCode[event.reasonCode] !=
          'COMMISSIONING_GATE_ACTIVE') continue;
      if (seen.add(event.description)) out.add(event);
    }
    return out;
  }

  void toggleExpand(String path) {
    expanded.contains(path) ? expanded.remove(path) : expanded.add(path);
    notifyListeners();
  }

  void toggleRail() {
    railCollapsed = !railCollapsed;
    notifyListeners();
  }

  void scopeTo(String? rootPath) {
    scopedRoot = rootPath;
    notifyListeners();
  }

  /// Level-gated theme change (returns false when the session is insufficient).
  bool setTheme(int i) {
    if (session.level.index < config.themeMinLevel.index) return false;
    if (i == themeIndex) return true;
    themeIndex = i;
    notifyListeners();
    _onUiPrefsChanged?.call();
    return true;
  }

  /// Level-gated control-size change — same gate as the theme, since both are
  /// HMI-local presentation config (HMI_CONTRACT 'Tree & theming').
  bool setControlScale(ControlScale scale) {
    if (session.level.index < config.themeMinLevel.index) return false;
    if (scale == controlScale) return true;
    controlScale = scale;
    keyboard.applyMetrics(UiMetrics.of(scale));
    notifyListeners();
    _onUiPrefsChanged?.call();
    return true;
  }

  /// Toggle the floating on-screen keyboard. Persisted alongside the theme.
  void setFloatingKeyboard(bool enabled) {
    if (floatingKeyboard == enabled) return;
    floatingKeyboard = enabled;
    keyboard.setEnabled(enabled);
    notifyListeners();
    _onUiPrefsChanged?.call();
  }

  @override
  void dispose() {
    _releaseTimer?.cancel();
    _sub.cancel();
    _linkSub.cancel();
    _busSub.cancel();
    repo.dispose();
    super.dispose();
  }
}
