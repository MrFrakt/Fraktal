/// Right-hand detail: header + Status/PLCopen strip, then whichever facets the
/// module publishes (link/part/PackML/motion — the data-bearing annexes), the
/// §6.11 decision prompt, Unit controls (mode/start/stop, blocked banner),
/// §8.11.4 cycle profile, §3.8a config editor, and §8.3 history. All writes are
/// access-gated (7.7) and re-checked in the PLC.
library;

import 'dart:convert';

import 'package:flutter/material.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../state/app_state.dart';
import '../content/module_content_controller.dart';
import '../localization/localized_text.dart';
import 'app_theme.dart';
import 'cycle_profile_view.dart';
import 'cycle_trend_view.dart';
import 'config_and_history.dart';
import 'facet_cards.dart';
import 'overview_and_indicators.dart';
import 'module_information.dart';
import 'custom_module_tabs.dart';
import 'touch_text_field.dart';
import 'module_layout_editor.dart';

class ModuleDetail extends StatefulWidget {
  final AppState app;
  const ModuleDetail({super.key, required this.app});

  @override
  State<ModuleDetail> createState() => _ModuleDetailState();
}

class _ModuleDetailState extends State<ModuleDetail> {
  bool _editing = false;
  String? _draftPath;
  List<ModuleTabDefinition> _draftTabs = const [];
  final List<List<ModuleTabDefinition>> _undoDrafts = [];
  final List<List<ModuleTabDefinition>> _redoDrafts = [];
  bool _guidanceOpen = false;
  String? _lastGuidanceFingerprint;

  AppState get app => widget.app;

  @override
  Widget build(BuildContext context) {
    final node = app.selected;
    if (node == null) return const Center(child: LText('Select a module'));
    final capabilities = moduleTabCapabilities(node);
    final isAdmin = app.session.level == AccessLevel.admin;
    if ((!isAdmin || _draftPath != node.path) && _editing) {
      _clearDraft();
    }
    final allTabs = _editing && _draftPath == node.path
        ? _draftTabs
        : app.content.tabsFor(node.path, capabilities);
    final visibleTabs = allTabs
        .where((tab) => app.session.level.index >= tab.requiredLevel.index)
        .toList(growable: false);
    _scheduleGuidance(node, visibleTabs);

    if (visibleTabs.isEmpty) {
      return Column(children: [
        _header(context, node, isAdmin),
        const Expanded(
          child: Center(child: LText('std.module.tabs.noneVisible')),
        ),
      ]);
    }

    final controllerKey = ValueKey(
      '${node.path}:${visibleTabs.map((tab) => tab.id).join(',')}:$_editing',
    );
    return DefaultTabController(
      key: controllerKey,
      length: visibleTabs.length,
      // Operator tabs change atomically. Flutter's TabController otherwise
      // drives the indicator and PageView through separate animations; under
      // live PLC rebuild load those can visibly pause near completion.
      animationDuration: Duration.zero,
      child: Builder(builder: (tabContext) {
        final controller = DefaultTabController.of(tabContext);
        return Column(children: [
          _header(context, node, isAdmin),
          if (visibleTabs.length > 1)
            Material(
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              child: TabBar(
                isScrollable: true,
                tabAlignment: TabAlignment.start,
                indicatorAnimation: TabIndicatorAnimation.linear,
                tabs: [
                  for (final tab in visibleTabs)
                    Tab(
                      icon: Icon(_tabIcon(tab.effectiveIcon), size: 19),
                      text: context.tr(tab.title),
                    ),
                ],
              ),
            ),
          if (isAdmin && _editing)
            AnimatedBuilder(
              // Only this lightweight toolbar depends on the selected index.
              // Rebuilding the complete TabBarView here makes its chart-heavy
              // Overview pause each tab transition.
              animation: controller,
              builder: (context, _) {
                final selectedIndex =
                    controller.index.clamp(0, visibleTabs.length - 1).toInt();
                return _editToolbar(
                  context,
                  node,
                  capabilities,
                  visibleTabs[selectedIndex],
                );
              },
            ),
          Expanded(
            child: visibleTabs.length == 1
                ? _tabContent(context, node, visibleTabs.single, capabilities)
                : TabBarView(
                    physics: const NeverScrollableScrollPhysics(),
                    children: [
                      for (final tab in visibleTabs)
                        _tabContent(context, node, tab, capabilities),
                    ],
                  ),
          ),
        ]);
      }),
    );
  }

  Widget _header(BuildContext context, ModuleNode node, bool isAdmin) =>
      Material(
        color: Theme.of(context).colorScheme.surface,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 12, 10),
          child: Row(children: [
            Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                color: stateColor(context, node.state),
                shape: BoxShape.circle,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: LText(
                node.path,
                style: Theme.of(context).textTheme.titleLarge,
                overflow: TextOverflow.ellipsis,
              ),
            ),
            Chip(label: LText(node.state.name.toUpperCase())),
            if (isAdmin) ...[
              const SizedBox(width: 8),
              IconButton.filledTonal(
                key: const Key('module-layout-edit-toggle'),
                tooltip: context.tr(_editing
                    ? 'std.module.editor.finishEditing'
                    : 'std.module.editor.startEditing'),
                onPressed: () => _toggleEditing(node),
                icon: Icon(_editing ? Icons.close : Icons.edit_outlined),
              ),
            ],
          ]),
        ),
      );

  Widget _editToolbar(
    BuildContext context,
    ModuleNode node,
    ModuleTabCapabilities capabilities,
    ModuleTabDefinition selectedTab,
  ) =>
      Material(
        color: Theme.of(context).colorScheme.primaryContainer,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              const Icon(Icons.admin_panel_settings_outlined, size: 20),
              const SizedBox(width: 8),
              const LText('std.module.editor.active'),
              const SizedBox(width: 20),
              IconButton(
                tooltip: context.tr('std.common.undo'),
                onPressed: _undoDrafts.isEmpty ? null : _undoDraft,
                icon: const Icon(Icons.undo),
              ),
              IconButton(
                tooltip: context.tr('std.common.redo'),
                onPressed: _redoDrafts.isEmpty ? null : _redoDraft,
                icon: const Icon(Icons.redo),
              ),
              if (selectedTab.kind == ModuleTabKind.custom ||
                  selectedTab.kind == ModuleTabKind.guidance)
                IconButton(
                  tooltip: context.tr('std.module.editor.addControl'),
                  onPressed: () => _addControl(node, selectedTab, capabilities),
                  icon: const Icon(Icons.add_box_outlined),
                ),
              IconButton(
                tooltip: context.tr('std.module.editor.editTab'),
                onPressed: () => _editTab(node, selectedTab, capabilities),
                icon: const Icon(Icons.tab_outlined),
              ),
              if (!selectedTab.builtIn)
                IconButton(
                  tooltip: context.tr('std.module.editor.deleteTab'),
                  onPressed: () => _deleteTab(node, selectedTab, capabilities),
                  icon: const Icon(Icons.delete_outline),
                ),
              IconButton(
                tooltip: context.tr('std.module.editor.addTab'),
                onPressed: () => _addTab(node, capabilities),
                icon: const Icon(Icons.add_to_photos_outlined),
              ),
              const VerticalDivider(width: 18),
              IconButton(
                tooltip: context.tr('std.module.editor.history'),
                onPressed: () => _showRevisionHistory(node, capabilities),
                icon: const Icon(Icons.history),
              ),
              IconButton.filled(
                tooltip: context.tr('std.module.editor.publish'),
                onPressed: () => _publishDraft(node, capabilities),
                icon: const Icon(Icons.publish),
              ),
              IconButton(
                tooltip: context.tr('std.module.editor.discardDraft'),
                onPressed: _discardDraft,
                icon: const Icon(Icons.close),
              ),
              const VerticalDivider(width: 18),
              IconButton(
                tooltip: context.tr('std.module.editor.importTitle'),
                onPressed: () => importHmiCustomization(context, app),
                icon: const Icon(Icons.file_upload_outlined),
              ),
              IconButton(
                tooltip: context.tr('std.module.editor.exportTitle'),
                onPressed: () => exportHmiCustomization(context, app),
                icon: const Icon(Icons.file_download_outlined),
              ),
            ]),
          ),
        ),
      );

  Widget _tabContent(
    BuildContext context,
    ModuleNode node,
    ModuleTabDefinition tab,
    ModuleTabCapabilities capabilities,
  ) =>
      switch (tab.kind) {
        ModuleTabKind.overview =>
          _ModuleOverviewTab(app: app, background: tab.background),
        ModuleTabKind.description => ListView(
            padding: const EdgeInsets.all(16),
            children: [
              ModuleInformationCard(app: app, node: node),
              ModuleDocumentsCard(app: app, node: node),
            ],
          ),
        ModuleTabKind.motion => MotionModuleTab(node: node),
        ModuleTabKind.vision => VisionModuleTab(app: app, node: node),
        ModuleTabKind.codeReader => CodeReaderModuleTab(app: app, node: node),
        ModuleTabKind.rfid => RfidModuleTab(app: app, node: node),
        ModuleTabKind.custom || ModuleTabKind.guidance => CustomModuleTabView(
            app: app,
            node: node,
            tab: tab,
            editing: _editing,
            onEditControl: (control) =>
                _editControl(node, tab, control, capabilities),
            onRemoveControl: (id) =>
                _removeControl(node, tab, id, capabilities),
            onMoveControlUp: (index) =>
                _moveControl(node, tab, index, -1, capabilities),
            onMoveControlDown: (index) =>
                _moveControl(node, tab, index, 1, capabilities),
            onReorderControl: (oldIndex, newIndex) =>
                _reorderControl(node, tab, oldIndex, newIndex, capabilities),
          ),
      };

  Future<void> _addTab(
      ModuleNode node, ModuleTabCapabilities capabilities) async {
    final tab = await showModuleTabEditor(
      context,
      allowGuidance: node.isUnit,
    );
    if (tab != null) {
      _upsertDraftTab(tab);
    }
  }

  Future<void> _editTab(ModuleNode node, ModuleTabDefinition existing,
      ModuleTabCapabilities capabilities) async {
    final tab = await showModuleTabEditor(
      context,
      existing: existing,
      allowGuidance: node.isUnit,
    );
    if (tab != null) {
      _upsertDraftTab(tab);
    }
  }

  Future<void> _deleteTab(ModuleNode node, ModuleTabDefinition tab,
      ModuleTabCapabilities capabilities) async {
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const LText('std.module.editor.deleteTab'),
            content: LText('std.module.editor.deleteTabConfirm',
                args: {'title': context.tr(tab.title)}),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const LText('std.common.cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const LText('std.common.delete'),
              ),
            ],
          ),
        ) ??
        false;
    if (confirmed) {
      _applyDraft(_draftTabs.where((item) => item.id != tab.id).toList());
    }
  }

  Future<void> _addControl(ModuleNode node, ModuleTabDefinition tab,
      ModuleTabCapabilities capabilities) async {
    final control = await showModuleControlEditor(context, node: node);
    if (control != null) {
      _upsertDraftTab(tab.copyWith(controls: [...tab.controls, control]));
    }
  }

  Future<void> _editControl(
      ModuleNode node,
      ModuleTabDefinition tab,
      ModuleControlDefinition existing,
      ModuleTabCapabilities capabilities) async {
    final control = await showModuleControlEditor(
      context,
      existing: existing,
      node: node,
    );
    if (control == null) return;
    final controls = tab.controls.toList();
    final index = controls.indexWhere((item) => item.id == existing.id);
    if (index < 0) return;
    controls[index] = control;
    _upsertDraftTab(tab.copyWith(controls: controls));
  }

  Future<void> _removeControl(ModuleNode node, ModuleTabDefinition tab,
      String id, ModuleTabCapabilities capabilities) async {
    _upsertDraftTab(
      tab.copyWith(
          controls: tab.controls.where((item) => item.id != id).toList()),
    );
  }

  Future<void> _moveControl(ModuleNode node, ModuleTabDefinition tab, int from,
      int delta, ModuleTabCapabilities capabilities) async {
    final to = from + delta;
    if (from < 0 ||
        from >= tab.controls.length ||
        to < 0 ||
        to >= tab.controls.length) {
      return;
    }
    final controls = tab.controls.toList();
    final moved = controls.removeAt(from);
    controls.insert(to, moved);
    _upsertDraftTab(tab.copyWith(controls: controls));
  }

  void _reorderControl(ModuleNode node, ModuleTabDefinition tab, int oldIndex,
      int newIndex, ModuleTabCapabilities capabilities) {
    if (oldIndex < 0 || oldIndex >= tab.controls.length) return;
    final controls = tab.controls.toList();
    if (newIndex < 0 || newIndex >= controls.length) return;
    final moved = controls.removeAt(oldIndex);
    controls.insert(newIndex, moved);
    _upsertDraftTab(tab.copyWith(controls: controls));
  }

  void _toggleEditing(ModuleNode node) {
    if (_editing) {
      _discardDraft();
      return;
    }
    final capabilities = moduleTabCapabilities(node);
    setState(() {
      _editing = true;
      _draftPath = node.path;
      _draftTabs =
          List.unmodifiable(app.content.tabsFor(node.path, capabilities));
      _undoDrafts.clear();
      _redoDrafts.clear();
    });
  }

  void _clearDraft() {
    _editing = false;
    _draftPath = null;
    _draftTabs = const [];
    _undoDrafts.clear();
    _redoDrafts.clear();
  }

  void _discardDraft() => setState(_clearDraft);

  void _applyDraft(List<ModuleTabDefinition> next) {
    if (!_editing || next.isEmpty) return;
    setState(() {
      _undoDrafts.add(_draftTabs);
      if (_undoDrafts.length > 50) _undoDrafts.removeAt(0);
      _draftTabs = List.unmodifiable(next);
      _redoDrafts.clear();
    });
  }

  void _upsertDraftTab(ModuleTabDefinition tab) {
    final tabs = _draftTabs.toList();
    final index = tabs.indexWhere((item) => item.id == tab.id);
    if (index < 0) {
      tabs.add(tab);
    } else {
      tabs[index] = tab;
    }
    _applyDraft(tabs);
  }

  void _undoDraft() {
    if (_undoDrafts.isEmpty) return;
    setState(() {
      _redoDrafts.add(_draftTabs);
      _draftTabs = _undoDrafts.removeLast();
    });
  }

  void _redoDraft() {
    if (_redoDrafts.isEmpty) return;
    setState(() {
      _undoDrafts.add(_draftTabs);
      _draftTabs = _redoDrafts.removeLast();
    });
  }

  Future<void> _publishDraft(
      ModuleNode node, ModuleTabCapabilities capabilities) async {
    final comment = TextEditingController();
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            title: const LText('std.module.editor.publishTitle'),
            content: TouchTextField(
              controller: comment,
              maxLength: 240,
              maxLines: 3,
              decoration: InputDecoration(
                labelText: dialogContext.tr('std.module.editor.changeComment'),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: const LText('std.common.cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(dialogContext, true),
                child: const LText('std.module.editor.publish'),
              ),
            ],
          ),
        ) ??
        false;
    final changeComment = comment.text;
    comment.dispose();
    if (!confirmed || !mounted || _draftPath != node.path) return;
    await app.content.publishTabs(
      node.path,
      _draftTabs,
      capabilities,
      author: app.session.user,
      comment: changeComment,
    );
    if (mounted) setState(_clearDraft);
  }

  Future<void> _showRevisionHistory(
      ModuleNode node, ModuleTabCapabilities capabilities) async {
    final revisions = app.content.revisionsFor(node.path);
    final revisionId = await showDialog<String>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const LText('std.module.editor.history'),
        content: SizedBox(
          width: 620,
          height: revisions.isEmpty ? 120 : 480,
          child: revisions.isEmpty
              ? const LText('std.module.editor.noHistory')
              : ListView.separated(
                  shrinkWrap: true,
                  itemCount: revisions.length,
                  separatorBuilder: (_, __) => const Divider(height: 1),
                  itemBuilder: (context, index) {
                    final revision = revisions[index];
                    return ListTile(
                      title: Text(revision.comment),
                      subtitle: Text(
                        '${revision.createdAt.toLocal()} · ${revision.author}',
                      ),
                      trailing: OutlinedButton(
                        onPressed: () =>
                            Navigator.pop(dialogContext, revision.id),
                        child: const LText('std.module.editor.restore'),
                      ),
                    );
                  },
                ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const LText('std.common.close'),
          ),
        ],
      ),
    );
    if (revisionId == null || !mounted) return;
    await app.content.restoreRevision(
      node.path,
      revisionId,
      capabilities,
      author: app.session.user,
    );
    if (mounted) setState(_clearDraft);
  }

  void _scheduleGuidance(
      ModuleNode node, List<ModuleTabDefinition> visibleTabs) {
    final step = node.step;
    if (!node.isUnit || step == null || !step.active) {
      _lastGuidanceFingerprint = null;
      return;
    }
    final tab = visibleTabs.where((candidate) {
      if (!candidate.triggers(step.stepNo, step.stepName)) return false;
      return candidate.triggerStepName.trim() != '*' ||
          step.timeClass == TimeClass.waitOperator;
    }).firstOrNull;
    if (tab == null) return;
    final fingerprint =
        '${node.path}:${tab.id}:${step.stepNo}:${step.stepName}';
    if (_guidanceOpen || _lastGuidanceFingerprint == fingerprint) return;
    _lastGuidanceFingerprint = fingerprint;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted || _guidanceOpen) return;
      _guidanceOpen = true;
      await showDialog<void>(
        context: context,
        barrierDismissible: false,
        builder: (dialogContext) => Dialog.fullscreen(
          child: Scaffold(
            appBar: AppBar(
              leading: IconButton(
                tooltip: dialogContext.tr('std.common.close'),
                onPressed: () => Navigator.pop(dialogContext),
                icon: const Icon(Icons.close),
              ),
              title: LText(tab.title),
              actions: [
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  child: Center(
                    child: LText('std.guidance.step', args: {
                      'number': step.stepNo,
                      'name': dialogContext.tr(step.stepName),
                    }),
                  ),
                ),
              ],
            ),
            body: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                CurrentStepCard(step: step),
                DecisionPrompt(app: app, node: node),
                SizedBox(
                  height: 520,
                  child: CustomModuleTabView(
                    app: app,
                    node: node,
                    tab: tab,
                  ),
                ),
              ],
            ),
          ),
        ),
      );
      _guidanceOpen = false;
    });
  }
}

IconData _tabIcon(ModuleTabIcon icon) => switch (icon) {
      ModuleTabIcon.widgets => Icons.widgets_outlined,
      ModuleTabIcon.dashboard => Icons.dashboard_outlined,
      ModuleTabIcon.tune => Icons.tune,
      ModuleTabIcon.monitoring => Icons.monitor_heart_outlined,
      ModuleTabIcon.chart => Icons.show_chart,
      ModuleTabIcon.information => Icons.info_outline,
      ModuleTabIcon.build => Icons.build_outlined,
      ModuleTabIcon.science => Icons.science_outlined,
      ModuleTabIcon.machine => Icons.precision_manufacturing_outlined,
      ModuleTabIcon.camera => Icons.camera_alt_outlined,
      ModuleTabIcon.scanner => Icons.qr_code_scanner,
      ModuleTabIcon.contactless => Icons.contactless_outlined,
      ModuleTabIcon.checklist => Icons.checklist_outlined,
      ModuleTabIcon.guidance => Icons.assistant_outlined,
      ModuleTabIcon.image => Icons.image_outlined,
      ModuleTabIcon.description => Icons.description_outlined,
      ModuleTabIcon.settings => Icons.settings_outlined,
      ModuleTabIcon.speed => Icons.speed_outlined,
      ModuleTabIcon.electrical => Icons.electrical_services_outlined,
    };

BoxFit _backgroundBoxFit(ModuleBackgroundFit fit) => switch (fit) {
      ModuleBackgroundFit.contain => BoxFit.contain,
      ModuleBackgroundFit.cover => BoxFit.cover,
      ModuleBackgroundFit.fitWidth => BoxFit.fitWidth,
      ModuleBackgroundFit.fitHeight => BoxFit.fitHeight,
    };

Alignment _backgroundAlignment(ModuleBackgroundPosition position) =>
    switch (position) {
      ModuleBackgroundPosition.topLeft => Alignment.topLeft,
      ModuleBackgroundPosition.topCenter => Alignment.topCenter,
      ModuleBackgroundPosition.topRight => Alignment.topRight,
      ModuleBackgroundPosition.centerLeft => Alignment.centerLeft,
      ModuleBackgroundPosition.center => Alignment.center,
      ModuleBackgroundPosition.centerRight => Alignment.centerRight,
      ModuleBackgroundPosition.bottomLeft => Alignment.bottomLeft,
      ModuleBackgroundPosition.bottomCenter => Alignment.bottomCenter,
      ModuleBackgroundPosition.bottomRight => Alignment.bottomRight,
    };

class _ModuleOverviewTab extends StatelessWidget {
  final AppState app;
  final ModuleTabBackground? background;
  const _ModuleOverviewTab({required this.app, this.background});

  @override
  Widget build(BuildContext context) {
    final n = app.selected;
    if (n == null) return const Center(child: LText('Select a module'));
    final s = app.session;
    final operations =
        app.content.permits(n.path, ModuleSection.operations, s.level);
    final diagnostics =
        app.content.permits(n.path, ModuleSection.diagnostics, s.level);
    final configuration =
        app.content.permits(n.path, ModuleSection.configuration, s.level);
    final history = app.content.permits(n.path, ModuleSection.history, s.level);
    final content = ListView(padding: const EdgeInsets.all(16), children: [
      if (diagnostics && n.message.isNotEmpty)
        Padding(
          padding: const EdgeInsets.only(top: 8),
          child: LText(n.message,
              style: TextStyle(
                  color: n.faultActive
                      ? Theme.of(context).colorScheme.error
                      : null)),
        ),
      if (diagnostics && n.message.isNotEmpty && !n.diagnosticTimeSynchronized)
        const Align(
          alignment: Alignment.centerLeft,
          child: Chip(
            avatar: Icon(Icons.schedule_outlined, size: 18),
            label: LText('TIME UNSYNCHRONIZED'),
          ),
        ),
      if (diagnostics && n.diagnosticIoTag.isNotEmpty)
        Align(
          alignment: Alignment.centerLeft,
          child: Chip(
            avatar: const Icon(Icons.sensors, size: 18),
            label: Text(n.diagnosticIoAddress.isEmpty
                ? n.diagnosticIoTag
                : '${n.diagnosticIoTag} · ${n.diagnosticIoAddress}'),
          ),
        ),
      if (operations) DecisionPrompt(app: app, node: n),
      if (operations && n.step != null) CurrentStepCard(step: n.step!),
      if (diagnostics && n.link != null) LinkCard(link: n.link!),
      if (diagnostics && n.packML != null) PackMLCard(state: n.packML!),
      if (diagnostics && n.motion != null) MotionCard(m: n.motion!),
      if (diagnostics && n.part != null) PartCard(part: n.part!),
      if (diagnostics && n.safety != null) SafetyCard(safety: n.safety!),
      if (diagnostics && n.systemHealth != null)
        SystemHealthCard(
          health: n.systemHealth!,
          tower: n.signalTower,
          canLampTest:
              operations && !n.running && s.permits(GatedAction.manual),
          onLampTest: () => app.repo.lampTest(n.path),
          onExplain: () => app.showReleaseReportAction(
              n.path, GatedAction.manual, 'Lamp test blocked'),
        ),
      if (operations && n.controlPower != null)
        ControlPowerCard(
          power: n.controlPower!,
          domainId: n.controlDomainId,
          domainName: n.controlDomainName,
          memberUnits: n.controlDomainMembers,
          canControl: s.permits(GatedAction.powerControl),
          onControlOn: () => app.repo.controlOn(n.path),
          onControlOff: () => app.repo.controlOff(n.path),
          onExplain: () => app.showReleaseReportAction(
              n.path, GatedAction.powerControl, 'Control power blocked'),
        ),
      if (diagnostics && n.nameplate != null && !n.nameplate!.isEmpty)
        NameplateCard(plate: n.nameplate!),
      if (diagnostics && n.oee != null)
        OeeCard(
          oee: n.oee!,
          onReset: () async {
            // §7.8 act-or-explain: blocked reset opens the release panel
            if (!app.session.permits(GatedAction.dataWrite)) {
              app.showReleaseReportAction(
                  n.path, GatedAction.dataWrite, 'OEE reset blocked');
              return;
            }
            final ok = await app.repo.resetOee(n.path);
            if (!ok)
              app.showReleaseReportAction(
                  n.path, GatedAction.dataWrite, 'OEE reset blocked');
          },
        ),
      if (operations && n.commands.isNotEmpty) _manualPanel(context, n),
      if (operations && n.isUnit) ...[
        const SizedBox(height: 12),
        if (n.blocking)
          MaterialBanner(
            backgroundColor: Theme.of(context).colorScheme.errorContainer,
            content: const LText(
                'Blocked — a manual-reset event awaits operator intervention (8.3)'),
            actions: [
              FilledButton(
                onPressed: app.permitsLocal(GatedAction.alarmReset)
                    ? () => app.repo.operatorReset(n.path)
                    : () => app.showReleaseReportAction(
                        n.path, GatedAction.alarmReset, 'Reset blocked'),
                child: const LText('Operator reset'),
              ),
            ],
          ),
        Wrap(spacing: 8, runSpacing: 8, children: [
          Chip(
              avatar: const Icon(Icons.qr_code_2, size: 18),
              label: LText('Model ${n.modelCode}')),
          Chip(label: LText('Mode ${n.modeActive?.name.toUpperCase() ?? '-'}')),
          if (n.machineState != null)
            Chip(
                avatar: const Icon(Icons.factory_outlined, size: 18),
                label: LText(n.machineState!.name.toUpperCase())),
          Chip(label: LText('Good ${n.goodCount}')),
          Chip(label: LText('NOK ${n.nokCount}')),
          if (n.reworkCount > 0) Chip(label: LText('Rework ${n.reworkCount}')),
          if (n.lastCycleTime > Duration.zero)
            Chip(
                avatar: const Icon(Icons.timer_outlined, size: 18),
                label: LText(
                    'Cycle ${(n.lastCycleTime.inMilliseconds / 1000).toStringAsFixed(1)}s'
                    ' (best ${(n.minCycleTime.inMilliseconds / 1000).toStringAsFixed(1)}s)')),
        ]),
        const SizedBox(height: 8),
        _controls(context, n, s),
        const SizedBox(height: 12),
        // §8.11.4(c) cycle-time analysis: trend (why it moved) -> waterfall
        // (which step) -> Pareto (which step, over time) -> command timing
        // per child module (which command) below.
        CycleTrendView(history: n.cycleHistory, minCycleTime: n.minCycleTime),
        if (n.cycle != null) CycleProfileView(profile: n.cycle!),
        if (n.stepStats.isNotEmpty) StepParetoView(stats: n.stepStats),
        for (final child in n.children)
          if (child.commandTimings.isNotEmpty)
            CommandTimingView(
                moduleName: child.name, rows: child.commandTimings),
      ],
      if (configuration) ConfigEditor(app: app, node: n),
      if (diagnostics) const SizedBox(height: 8),
      if (diagnostics)
        LText('Active events', style: Theme.of(context).textTheme.titleMedium),
      if (diagnostics)
        for (final e in n.activeEvents) _eventTile(context, e),
      if (diagnostics && n.activeEvents.isEmpty)
        const ListTile(dense: true, title: LText('—')),
      if (history && n.isUnit && s.permits(GatedAction.alarmHistory))
        HistoryBrowser(node: n),
    ]);
    final configured = background;
    if (configured == null || configured.imageBase64.isEmpty) return content;
    try {
      final bytes = base64Decode(configured.imageBase64);
      return Stack(
        fit: StackFit.expand,
        children: [
          Padding(
            padding: EdgeInsets.fromLTRB(
              configured.marginLeft,
              configured.marginTop,
              configured.marginRight,
              configured.marginBottom,
            ),
            child: Image.memory(
              bytes,
              fit: _backgroundBoxFit(configured.fit),
              alignment: _backgroundAlignment(configured.position),
              gaplessPlayback: true,
            ),
          ),
          content,
        ],
      );
    } on FormatException {
      return content;
    }
  }

  Widget _manualPanel(BuildContext context, ModuleNode n) {
    final root = app.rootOf(n.path);
    final inManual = root?.modeActive == UnitMode.manual;
    // PLC policy AND this panel's local floor (app_state.permitsLocal).
    final canManual = app.permitsLocal(GatedAction.manual);
    final enabled = inManual && canManual;
    // deliberately distinct from the fieldbus force: a bordered 'Manual commands'
    // card with a hand icon, on the module itself (routes THROUGH the module).
    // Blue, not the theme's tertiary role — a manual command is a normal operator
    // action, and red/pink on a machine panel reads as a fault (see app_theme).
    return Card(
      color: operatorActionContainer(context),
      shape: RoundedRectangleBorder(
          side: const BorderSide(color: kOperatorActionColor),
          borderRadius: BorderRadius.circular(12)),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.pan_tool_outlined, color: kOperatorActionColor),
            const SizedBox(width: 8),
            LText('Manual commands',
                style: Theme.of(context).textTheme.titleMedium),
            const Spacer(),
            if (!inManual)
              const Chip(label: LText('Unit not in MANUAL'))
            else if (!canManual)
              const Chip(
                  avatar: Icon(Icons.lock_outline, size: 16),
                  label: LText('MANUAL access')),
          ]),
          const SizedBox(height: 4),
          LText('Routed through the module — interlocks still apply (§7.6.1).',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final c in n.commands)
              FilledButton.tonal(
                style: enabled
                    ? FilledButton.styleFrom(
                        backgroundColor: kOperatorActionColor,
                        foregroundColor: Colors.white)
                    : null,
                // §7.6.0: a blocked manual button reveals WHY instead of being inert
                onPressed: enabled
                    ? () => _manual(context, n, c)
                    : () => app.showReleaseReportManual(
                        app.rootOf(n.path)?.path ?? '', n.path, c.value),
                child: LText(c.label),
              ),
          ]),
        ]),
      ),
    );
  }

  Future<void> _manual(
      BuildContext context, ModuleNode n, CommandInfo c) async {
    final root = app.rootOf(n.path)?.path ?? '';
    final ok = await app.repo.manualCommand(root, n.path, c.value);
    if (!ok) {
      await app.showReleaseReportManual(root, n.path, c.value);
    }
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
            content: LText(ok
                ? 'std.manual.commandAccepted'
                : 'std.manual.commandRejected')),
      );
    }
  }

  Widget _controls(BuildContext context, ModuleNode n, AccessSession s) {
    return Row(children: [
      const Expanded(
          child: LText('Sequence and mode controls are in the mode bar.')),
      OutlinedButton.icon(
        icon: const Icon(Icons.swap_horiz),
        label: const LText('Changeover'),
        onPressed: s.permits(GatedAction.changeover)
            ? () => _changeover(context, n)
            : () => app.showReleaseReportAction(
                n.path, GatedAction.changeover, 'Changeover blocked'),
      ),
    ]);
  }

  Future<void> _changeover(BuildContext context, ModuleNode n) async {
    final ctrl = TextEditingController(text: n.modelCode);
    var selectedModel = n.availableModels.contains(n.modelCode)
        ? n.modelCode
        : (n.availableModels.isEmpty ? '' : n.availableModels.first);
    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setDialogState) {
        return AlertDialog(
          title: const LText('Changeover — set model'),
          content: n.availableModels.isEmpty
              ? TouchTextField(
                  controller: ctrl,
                  decoration:
                      InputDecoration(labelText: context.tr('Model code')))
              : DropdownButtonFormField<String>(
                  initialValue: selectedModel,
                  decoration:
                      InputDecoration(labelText: context.tr('Model code')),
                  items: [
                    for (final model in n.availableModels)
                      DropdownMenuItem(value: model, child: Text(model)),
                  ],
                  onChanged: (value) =>
                      setDialogState(() => selectedModel = value ?? ''),
                ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const LText('Cancel')),
            FilledButton(
              onPressed: () async {
                final model = n.availableModels.isEmpty
                    ? ctrl.text.trim()
                    : selectedModel;
                if (model.isEmpty) return;
                final modeAccepted =
                    await app.repo.setMode(n.path, UnitMode.changeover);
                final modelAccepted =
                    modeAccepted && await app.repo.setModel(n.path, model);
                final started = modelAccepted && await app.repo.start(n.path);
                if (!ctx.mounted) return;
                if (started) {
                  Navigator.pop(ctx);
                } else {
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                      content: LText('std.changeover.requestRejected')));
                }
              },
              child: const LText('Start changeover'),
            ),
          ],
        );
      }),
    );
  }

  Widget _eventTile(BuildContext context, AlarmEvent e) {
    final c = severityColor(context, e.severity);
    final dur = e.duration == null ? '' : ' · ${e.duration!.inSeconds}s';
    final st = switch (e.state) {
      AlarmState.waitReset => ' · awaiting reset',
      AlarmState.closed => ' · closed',
      _ => ''
    };
    // §8.9 rationalization join: what should the operator DO about this reason?
    final root = app.rootOf(e.sourcePath);
    AlarmMeta? meta;
    for (final m in root?.alarmMeta ?? const <AlarmMeta>[]) {
      if (m.reasonCode == e.reasonCode &&
          e.reasonCode != 0 &&
          m.operatorAction.isNotEmpty) {
        meta = m;
        break;
      }
    }
    final active = e.state != AlarmState.closed;
    return Opacity(
      opacity: e.shelved
          ? 0.45
          : 1.0, // §8.10 de-emphasis, still listed (never hidden)
      child: ListTile(
        dense: true,
        leading: Icon(
          e.shelved
              ? Icons.notifications_paused_outlined
              : switch (e.severity) {
                  Severity.high => Icons.error,
                  Severity.medium => Icons.warning_amber,
                  Severity.low => Icons.info_outline
                },
          color: c,
        ),
        title: LText(
            '${context.tr(e.description)}${e.shelved ? '  ·  ${context.tr('SHELVED')}' : ''}'),
        subtitle: LText(
            '${e.sourcePath}${e.ioTag.isEmpty ? '' : '\n${e.ioTag}${e.ioAddress.isEmpty ? '' : ' · ${e.ioAddress}'}'}$st$dur${e.timestampsSynchronized ? '' : ' · TIME UNSYNCHRONIZED'}${meta != null ? '\n→ ${context.tr(meta.operatorAction)}' : ''}'),
        isThreeLine: meta != null,
        trailing: !active || e.severity == Severity.low
            ? null
            : IconButton(
                tooltip: context.tr(e.shelved
                    ? 'Unshelve (restore annunciation)'
                    : (meta?.shelvable == true
                        ? 'Shelve annunciation (§8.10, logged; control unaffected)'
                        : 'Not shelvable — rationalize first (§8.10)')),
                icon: Icon(
                    e.shelved
                        ? Icons.notifications_active_outlined
                        : Icons.notifications_paused_outlined,
                    size: 20),
                onPressed: () => _shelve(context, e, meta),
              ),
      ),
    );
  }

  Future<void> _shelve(
      BuildContext context, AlarmEvent e, AlarmMeta? meta) async {
    final root = app.rootOf(e.sourcePath)?.path ?? '';
    if (e.shelved) {
      final ok =
          await app.repo.unshelveAlarm(root, e.sourcePath, e.description);
      if (!ok && context.mounted)
        app.showReleaseReportAction(
            root, GatedAction.alarmShelve, 'Unshelve blocked');
      return;
    }
    // act-or-explain: unrationalized/unshelvable explains instead of a dead press
    if (meta == null || !meta.shelvable) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: LText(
              'Not shelvable: this reason has no rationalization record or is flagged non-shelvable (§8.10). Safety alarms are never shelvable.')));
      return;
    }
    if (!app.session.permits(GatedAction.alarmShelve)) {
      app.showReleaseReportAction(
          root, GatedAction.alarmShelve, 'Shelve blocked');
      return;
    }
    final ok = await app.repo.shelveAlarm(
        root, e.sourcePath, e.description, const Duration(minutes: 30));
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: LText(ok
              ? 'Shelved 30 min (logged). Control is unaffected — a blocking alarm still blocks.'
              : 'Shelve refused by the PLC')));
    }
  }
}
