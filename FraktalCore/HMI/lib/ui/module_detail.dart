/// Right-hand detail: header + Status/PLCopen strip, then whichever facets the
/// module publishes (link/part/PackML/motion — the data-bearing annexes), the
/// §6.11 decision prompt, Unit controls (mode/start/stop, blocked banner),
/// §8.11.4 cycle profile, §3.8a config editor, and §8.3 history. All writes are
/// access-gated (7.7) and re-checked in the PLC.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'theme_surfaces.dart';
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
import 'flow_columns.dart';
import 'overview_and_indicators.dart';
import 'module_information.dart';
import 'custom_module_tabs.dart';
import 'sequence_module_tab.dart';
import 'touch_text_field.dart';
import '../diagnostics/hmi_log.dart';
import 'module_layout_editor.dart';

class ModuleDetail extends StatefulWidget {
  final AppState app;
  const ModuleDetail({super.key, required this.app});

  @override
  State<ModuleDetail> createState() => _ModuleDetailState();
}

class _ModuleDetailState extends State<ModuleDetail> {
  bool _editing = false;

  /// Editing the layout every module of this module's TYPE shares, rather
  /// than this module's own (LOCALIZATION §7.1).
  bool _typeScope = false;
  String? _draftPath;
  List<ModuleTabDefinition> _draftTabs = const [];
  final List<List<ModuleTabDefinition>> _undoDrafts = [];
  final List<List<ModuleTabDefinition>> _redoDrafts = [];
  bool _guidanceOpen = false;
  String? _lastGuidanceFingerprint;

  /// The module's guidance tab, rendered again by the operator-guidance card.
  ModuleTabDefinition? _guidanceTab;

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
        : app.content.tabsFor(node.path, capabilities, typeKey: node.typeKey);
    final visibleTabs = allTabs
        .where((tab) => app.session.level.index >= tab.requiredLevel.index)
        .toList(growable: false);
    _guidanceTab =
        allTabs.where((tab) => tab.kind == ModuleTabKind.guidance).firstOrNull;
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
          if (isAdmin && _editing) _tabOrderStrip(context),
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
            // The state badge. The coloured dot to the left already carries the
            // §8.1 state semantics as a GLYPH; this chip is a SENTENCE and only
            // has to be readable on its own fill (4.5:1), so it pairs rather
            // than tinting itself.
            _pairedChip(context, null, node.state.name.toUpperCase()),
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
              if (node.typeKey.isNotEmpty) ...[
                // What this draft is published to: this module alone, or
                // every module of its type. Fixed while changes are pending.
                ChoiceChip(
                  key: const Key('layout-scope-module'),
                  label: const LText('std.module.editor.scopeModule'),
                  selected: !_typeScope,
                  onSelected: _undoDrafts.isEmpty
                      ? (_) => _setScope(node, false)
                      : null,
                ),
                const SizedBox(width: 6),
                ChoiceChip(
                  key: const Key('layout-scope-type'),
                  label: LText('std.module.editor.scopeType',
                      args: {'type': context.tr(node.typeKey)}),
                  selected: _typeScope,
                  onSelected: _undoDrafts.isEmpty
                      ? (_) => _setScope(node, true)
                      : null,
                ),
                if (!_typeScope && app.content.hasLayout(node.path))
                  IconButton(
                    key: const Key('layout-use-type'),
                    tooltip: context.tr('std.module.editor.useTypeLayout'),
                    onPressed: () => _useTypeLayout(node, capabilities),
                    icon: const Icon(Icons.layers_clear_outlined),
                  ),
                const SizedBox(width: 12),
              ],
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
              IconButton(
                key: const Key('tab-default-toggle'),
                tooltip: context.tr(selectedTab.isDefault
                    ? 'std.module.editor.clearDefaultTab'
                    : 'std.module.editor.setDefaultTab'),
                onPressed: () => _toggleDefaultTab(selectedTab),
                icon: Icon(selectedTab.isDefault
                    ? Icons.star
                    : Icons.star_outline),
              ),
              if (selectedTab.kind.hostsCards) ...[
                const SizedBox(width: 6),
                const LText('std.module.editor.columns'),
                const SizedBox(width: 4),
                DropdownButton<int>(
                  key: const Key('tab-columns'),
                  value: selectedTab.effectiveColumns,
                  items: [
                    for (var c = 1; c <= ModuleTabDefinition.maxColumns; c++)
                      DropdownMenuItem(value: c, child: Text('$c')),
                  ],
                  onChanged: (value) => value == null
                      ? null
                      : _upsertDraftTab(selectedTab.copyWith(columns: value)),
                ),
                PopupMenuButton<ModuleCardKind>(
                  key: const Key('tab-add-card'),
                  tooltip: context.tr('std.module.editor.addCard'),
                  icon: const Icon(Icons.add_card_outlined),
                  itemBuilder: (_) => [
                    for (final kind in ModuleCardKind.values)
                      if (!selectedTab.effectiveCards
                          .any((card) => card.kind == kind))
                        PopupMenuItem(
                          value: kind,
                          child: LText('std.module.card.${kind.name}'),
                        ),
                  ],
                  onSelected: (kind) => _upsertDraftTab(selectedTab.copyWith(
                    cards: [
                      ...selectedTab.effectiveCards,
                      ModuleCardPlacement(kind),
                    ],
                  )),
                ),
              ],
              // §7.5: only a root Unit has a station tile on the overview.
              if (app.rootOf(node.path)?.path == node.path)
                IconButton(
                  key: const Key('station-tile-edit'),
                  tooltip: context.tr('std.module.editor.stationTile'),
                  onPressed: () => _editStationTile(node),
                  icon: const Icon(Icons.dashboard_customize_outlined),
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
        ModuleTabKind.overview ||
        ModuleTabKind.description ||
        ModuleTabKind.configuration ||
        ModuleTabKind.hardware ||
        ModuleTabKind.statistics ||
        ModuleTabKind.events =>
          _ModuleCardsTab(
            app: app,
            node: node,
            tab: tab,
            guidanceTab: _guidanceTab,
            editing: _editing,
            onChanged: _upsertDraftTab,
          ),
        ModuleTabKind.sequence => SequenceModuleTab(app: app, node: node),
        ModuleTabKind.motion => MotionModuleTab(node: node),
        ModuleTabKind.vision => VisionModuleTab(app: app, node: node),
        ModuleTabKind.codeReader => CodeReaderModuleTab(app: app, node: node),
        ModuleTabKind.rfid => RfidModuleTab(app: app, node: node),
        ModuleTabKind.custom || ModuleTabKind.guidance => _ViewClassBadge(
            viewClass: tab.kind.acceptsBackground ? tab.viewClass : null,
            child: CustomModuleTabView(
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
            onPlaceControl: (id, placement) =>
                _placeControl(tab, id, placement),
            onAddControlAt: (kind, placement) => _addControl(
                node, tab, capabilities,
                kind: kind, placement: placement),
          ),
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

  /// [kind]/[placement]: dropped from the palette onto the tab's picture.
  Future<void> _addControl(ModuleNode node, ModuleTabDefinition tab,
      ModuleTabCapabilities capabilities,
      {ModuleControlKind? kind, ModulePlacement? placement}) async {
    final control = await showModuleControlEditor(context,
        node: node, initialKind: kind, placement: placement);
    if (control != null) {
      _upsertDraftTab(tab.copyWith(controls: [...tab.controls, control]));
    }
  }

  /// A control dragged or resized on the picture (or taken off it: null).
  /// One draft step per completed gesture, so undo steps back a whole move.
  void _placeControl(
      ModuleTabDefinition tab, String id, ModulePlacement? placement) {
    final controls = tab.controls.toList();
    final index = controls.indexWhere((item) => item.id == id);
    if (index < 0 || controls[index].placement == placement) return;
    controls[index] = controls[index].withPlacement(placement);
    _upsertDraftTab(tab.copyWith(controls: controls));
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
      _draftTabs = List.unmodifiable(_scopeTabs(node, capabilities));
      _undoDrafts.clear();
      _redoDrafts.clear();
    });
  }

  /// The scope a draft is edited and published in.
  String _scope(ModuleNode node) => _typeScope && node.typeKey.isNotEmpty
      ? ModuleContentController.typeScope(node.typeKey)
      : node.path;

  /// A draft starts from what that scope shows today: the type's layout, or -
  /// for a module - its own layout, else the type's it would override.
  List<ModuleTabDefinition> _scopeTabs(
          ModuleNode node, ModuleTabCapabilities capabilities) =>
      _typeScope && node.typeKey.isNotEmpty
          ? app.content.tabsFor(_scope(node), capabilities)
          : app.content
              .tabsFor(node.path, capabilities, typeKey: node.typeKey);

  /// Switching scope reloads the draft, so it is only offered while the draft
  /// has no unpublished change to lose.
  void _setScope(ModuleNode node, bool typeScope) {
    if (_typeScope == typeScope || _undoDrafts.isNotEmpty) return;
    final capabilities = moduleTabCapabilities(node);
    setState(() {
      _typeScope = typeScope;
      _draftTabs = List.unmodifiable(_scopeTabs(node, capabilities));
      _redoDrafts.clear();
    });
  }

  /// Publishes a station tile to the edit scope - this station, or every
  /// station of its type. Published directly: a tile is not part of the tab
  /// draft, and its slots are validated like any control.
  Future<void> _editStationTile(ModuleNode node) async {
    final scope = _scope(node);
    final profile = await showStationTileEditor(
      context,
      node: node,
      existing: _typeScope
          ? app.content.tileFor(scope)
          : app.content.tileFor(node.path, typeKey: node.typeKey),
    );
    if (profile == null || !mounted) return;
    try {
      await app.content.publishTile(scope, profile);
    } on FormatException catch (refused) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(context.tr(refused.message))));
      }
    }
  }

  Future<void> _useTypeLayout(
      ModuleNode node, ModuleTabCapabilities capabilities) async {
    await app.content.clearLayout(node.path, capabilities,
        author: app.session.user);
    if (!mounted) return;
    setState(() {
      _draftTabs = List.unmodifiable(_scopeTabs(node, capabilities));
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

  /// One default tab at most, and it leads the row.
  void _toggleDefaultTab(ModuleTabDefinition selected) {
    final makeDefault = !selected.isDefault;
    _applyDraft(ModuleContentController.defaultFirst([
      for (final tab in _draftTabs)
        tab.copyWith(isDefault: makeDefault && tab.id == selected.id),
    ]));
  }

  /// Edit mode: the tabs as chips, dragged into order. The default tab is
  /// pinned first and is not draggable.
  Widget _tabOrderStrip(BuildContext context) {
    final tabs = _draftTabs;
    final pinned = tabs.isNotEmpty && tabs.first.isDefault;
    return Material(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      child: SizedBox(
        height: 52,
        child: Row(children: [
          const SizedBox(width: 12),
          const LText('std.module.editor.tabOrder'),
          const SizedBox(width: 8),
          Expanded(
            child: ReorderableListView(
              key: const Key('tab-order-strip'),
              scrollDirection: Axis.horizontal,
              buildDefaultDragHandles: false,
              // newIndex is already the position after the item is removed.
              onReorderItem: (oldIndex, newIndex) {
                if (pinned && oldIndex == 0) return;
                var target = newIndex;
                if (pinned && target == 0) target = 1;
                final list = tabs.toList();
                final moved = list.removeAt(oldIndex);
                list.insert(target.clamp(0, list.length).toInt(), moved);
                _applyDraft(list);
              },
              children: [
                for (var i = 0; i < tabs.length; i++)
                  Padding(
                    key: ValueKey('tab-order-${tabs[i].id}'),
                    padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
                    child: tabs[i].isDefault
                        ? Chip(
                            avatar: const Icon(Icons.star, size: 18),
                            label: LText(tabs[i].title),
                          )
                        : ReorderableDragStartListener(
                            index: i,
                            child: Chip(
                              avatar: const Icon(Icons.drag_indicator, size: 18),
                              label: LText(tabs[i].title),
                            ),
                          ),
                  ),
              ],
            ),
          ),
        ]),
      ),
    );
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
    // Null = cancelled; otherwise the change comment (possibly empty).
    final changeComment = await showDialog<String>(
      context: context,
      builder: (dialogContext) => WithTextController(
        builder: (context, comment) => AlertDialog(
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
              onPressed: () => Navigator.pop(dialogContext),
              child: const LText('std.common.cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, comment.text),
              child: const LText('std.module.editor.publish'),
            ),
          ],
        ),
      ),
    );
    final confirmed = changeComment != null;
    hmiLog('publish ${node.path}: dialog closed, confirmed=$confirmed');
    if (changeComment == null || !mounted || _draftPath != node.path) return;
    try {
      await app.content.publishTabs(
        _scope(node),
        _draftTabs,
        capabilities,
        author: app.session.user,
        comment: changeComment,
        typeKey: _typeScope ? '' : node.typeKey,
      );
    } on FormatException catch (refused) {
      // A rule refused at publish (§7.3 budget, §7.4 class): say which, and
      // keep the draft so the author can fix it.
      hmiLog('publish ${node.path}: refused: ${refused.message}');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(context.tr(refused.message))));
      }
      return;
    }
    if (!mounted) return;
    hmiTimedSync(
        'publish ${node.path}: leave editing', () => setState(_clearDraft));
    hmiLogNextFrame('publish ${node.path}');
  }

  Future<void> _showRevisionHistory(
      ModuleNode node, ModuleTabCapabilities capabilities) async {
    final revisions = app.content.revisionsFor(_scope(node));
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
      _scope(node),
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
    // The Unit's ACTIVE mode gates the trigger: a WAIT_OPERATOR step in AUTO is
    // routine (the press parks on a two-hand start) and must not take over the
    // screen, while the same step in CHANGEOVER is exactly when the operator
    // wants walking through. See kSetupGuidanceModes.
    final modeIndex = node.modeActive?.index;
    final tab = visibleTabs.where((candidate) {
      if (!candidate.triggers(step.stepNo, step.stepName,
          modeIndex: modeIndex)) {
        return false;
      }
      return candidate.triggerStepName.trim() != '*' ||
          step.timeClass == TimeClass.waitOperator;
    }).firstOrNull;
    if (tab == null) return;
    // The mode is part of the identity: leaving CHANGEOVER and coming back is a
    // new occasion to guide, even on the same step number.
    final fingerprint =
        '${node.path}:${tab.id}:$modeIndex:${step.stepNo}:${step.stepName}';
    if (_guidanceOpen || _lastGuidanceFingerprint == fingerprint) return;
    _lastGuidanceFingerprint = fingerprint;
    final forced = tab.guidanceMode == GuidanceMode.forced;
    WidgetsBinding.instance.addPostFrameCallback((_) async {
      if (!mounted || _guidanceOpen) return;
      _guidanceOpen = true;
      await showDialog<void>(
        context: context,
        // FORCED guidance is the step waiting on this person (a changeover
        // model choice, confirming it is safe to open the doors). OPTIONAL
        // guidance is reference material the operator may already know, so it
        // must never trap them: tapping outside closes it and the rest of the
        // HMI stays reachable.
        barrierDismissible: !forced,
        builder: (dialogContext) {
          final body = Scaffold(
            appBar: AppBar(
              automaticallyImplyLeading: false,
              leading: forced
                  ? null
                  : IconButton(
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
                if (forced)
                  // The acknowledgement IS the point of a forced prompt, so it
                  // is an explicit button rather than a corner X. It stays
                  // available even when the PLC also wants a decision: the
                  // operator can read, answer below, and close deliberately.
                  Padding(
                    padding: const EdgeInsets.only(right: 12),
                    child: Center(
                      child: FilledButton.icon(
                        onPressed: () => Navigator.pop(dialogContext),
                        icon: const Icon(Icons.check),
                        label: const LText('std.guidance.acknowledge'),
                      ),
                    ),
                  ),
              ],
            ),
            body: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                if (forced)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 12),
                    child: FraktalCard(
                      color: operatorActionContainer(context),
                      child: const Padding(
                        padding: EdgeInsets.all(12),
                        child: Row(children: [
                          Icon(Icons.pan_tool_alt_outlined),
                          SizedBox(width: 10),
                          Expanded(child: LText('std.guidance.forcedNotice')),
                        ]),
                      ),
                    ),
                  ),
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
          );
          // Only a forced prompt swallows the system Back gesture; an optional
          // one must stay as easy to leave as any other panel.
          return PopScope(
            canPop: !forced,
            child: Dialog.fullscreen(child: body),
          );
        },
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
      ModuleTabIcon.events => Icons.notifications_outlined,
    };

/// A view's display class, shown ON the view (LOCALIZATION §7.4): a
/// maintenance display standing in as an operating screen is apparent to
/// anyone at the panel. Null = a fixed view with no authored class.
class _ViewClassBadge extends StatelessWidget {
  final ModuleViewClass? viewClass;
  final Widget child;
  const _ViewClassBadge({required this.viewClass, required this.child});

  @override
  Widget build(BuildContext context) {
    final value = viewClass;
    if (value == null) return child;
    final colors = Theme.of(context).colorScheme;
    return Stack(children: [
      Positioned.fill(child: child),
      Positioned(
        right: 8,
        bottom: 8,
        child: IgnorePointer(
          child: Container(
            key: ValueKey('view-class-${value.name}'),
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: colors.surfaceContainerHighest.withValues(alpha: 0.92),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: colors.outlineVariant),
            ),
            child: LText('std.module.viewClass.${value.name}',
                style: TextStyle(
                  color: colors.onSurfaceVariant,
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.6,
                )),
          ),
        ),
      ),
    ]);
  }
}

/// The Configuration tab. The HMI's per-module section policy still decides
/// who may see it (Configuration defaults to ENGINEER, LOCALIZATION §5); below
/// that level the tab says what it needs instead of rendering empty.
/// A card tab (Overview, Hardware, Statistics, Events, Description,
/// Configuration): the tab's cards, in its order, flowed across its columns.
/// In edit mode every card carries a header to drag, hide, gate and remove it.
class _ModuleCardsTab extends StatelessWidget {
  final AppState app;
  final ModuleNode node;
  final ModuleTabDefinition tab;

  /// The module's guidance tab, rendered by the operator-guidance card.
  final ModuleTabDefinition? guidanceTab;
  final bool editing;
  final ValueChanged<ModuleTabDefinition>? onChanged;
  const _ModuleCardsTab({
    required this.app,
    required this.node,
    required this.tab,
    this.guidanceTab,
    this.editing = false,
    this.onChanged,
  });

  static const _gap = 12.0;

  /// Narrower than this and a column is dropped: a card needs room to read.
  static const _minCardWidth = 320.0;

  @override
  Widget build(BuildContext context) {
    final n = node;
    final s = app.session;
    final placements = tab.effectiveCards;
    final items = <Widget>[];
    for (final placement in placements) {
      final permitted = _sectionPermits(placement.kind) &&
          s.level.index >= placement.requiredLevel.index;
      if (!editing) {
        if (placement.hidden || !permitted) continue;
        final card = _card(context, n, placement.kind);
        if (card != null) {
          items.add(KeyedSubtree(
              key: ValueKey('module-card-${placement.kind.name}'), child: card));
        }
      } else {
        items.add(_editableCard(context, n, placement, placements));
      }
    }
    if (editing) items.add(_endDropTarget(context, placements));
    if (items.isEmpty) {
      return const Center(child: LText('std.module.cards.none'));
    }
    return LayoutBuilder(builder: (context, constraints) {
      final available = constraints.maxWidth - 32;
      var columns = tab.effectiveColumns;
      while (columns > 1 &&
          (available - _gap * (columns - 1)) / columns < _minCardWidth) {
        columns--;
      }
      // A flow, not a grid: each card goes to the shortest column, so a tall
      // card leaves no row-high gap beside it.
      return SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: FlowColumns(columns: columns, gap: _gap, children: items),
      );
    });
  }

  ModuleSection _section(ModuleCardKind kind) => switch (kind) {
        ModuleCardKind.decision ||
        ModuleCardKind.currentStep ||
        ModuleCardKind.controlPower ||
        ModuleCardKind.manualCommands ||
        ModuleCardKind.unitControls ||
        ModuleCardKind.counters ||
        ModuleCardKind.cycleAnalysis ||
        ModuleCardKind.operatorGuidance =>
          ModuleSection.operations,
        ModuleCardKind.history => ModuleSection.history,
        ModuleCardKind.description => ModuleSection.information,
        ModuleCardKind.documents => ModuleSection.documentation,
        ModuleCardKind.modelData ||
        ModuleCardKind.stationData ||
        ModuleCardKind.lineData =>
          ModuleSection.configuration,
        _ => ModuleSection.diagnostics,
      };

  bool _sectionPermits(ModuleCardKind kind) =>
      // Configuration explains its own lock rather than vanishing (§7.8).
      kind.configKind != null ||
      app.content.permits(node.path, _section(kind), app.session.level);

  /// One card's content, or null when this module has nothing for it.
  Widget? _card(BuildContext context, ModuleNode n, ModuleCardKind kind) {
    final s = app.session;
    final operations =
        app.content.permits(n.path, ModuleSection.operations, s.level);
    switch (kind) {
      case ModuleCardKind.diagnostic:
        if (n.message.isEmpty) return null;
        return FraktalCard(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              LText(n.message,
                  style: TextStyle(
                      color: n.faultActive
                          ? Theme.of(context).colorScheme.error
                          : null)),
              if (!n.diagnosticTimeSynchronized)
                const Chip(
                  avatar: Icon(Icons.schedule_outlined, size: 18),
                  label: LText('TIME UNSYNCHRONIZED'),
                ),
              if (n.diagnosticIoTag.isNotEmpty)
                Chip(
                  avatar: const Icon(Icons.sensors, size: 18),
                  label: Text(n.diagnosticIoAddress.isEmpty
                      ? n.diagnosticIoTag
                      : '${n.diagnosticIoTag} · ${n.diagnosticIoAddress}'),
                ),
            ]),
          ),
        );
      case ModuleCardKind.decision:
        // Only while a decision is pending: an empty prompt is no card.
        final decision = n.decision;
        return decision == null || !decision.pending
            ? null
            : DecisionPrompt(app: app, node: n);
      case ModuleCardKind.currentStep:
        return n.step == null ? null : CurrentStepCard(step: n.step!);
      case ModuleCardKind.link:
        return n.link == null ? null : LinkCard(link: n.link!);
      case ModuleCardKind.packML:
        return n.packML == null ? null : PackMLCard(state: n.packML!);
      case ModuleCardKind.motion:
        return n.motion == null ? null : MotionCard(m: n.motion!);
      case ModuleCardKind.part:
        return n.part == null ? null : PartCard(part: n.part!);
      case ModuleCardKind.safety:
        return n.safety == null ? null : SafetyCard(safety: n.safety!);
      case ModuleCardKind.systemHealth:
        if (n.systemHealth == null) return null;
        return SystemHealthCard(
          health: n.systemHealth!,
          tower: n.signalTower,
          canLampTest:
              operations && !n.running && s.permits(GatedAction.manual),
          onLampTest: () => app.repo.lampTest(n.path),
          onExplain: () => app.showReleaseReportAction(
              n.path, GatedAction.manual, 'Lamp test blocked'),
        );
      case ModuleCardKind.controlPower:
        if (n.controlPower == null) return null;
        return ControlPowerCard(
          power: n.controlPower!,
          domainId: n.controlDomainId,
          domainName: n.controlDomainName,
          memberUnits: n.controlDomainMembers,
          canControl: s.permits(GatedAction.powerControl),
          onControlOn: () => app.repo.controlOn(n.path),
          onControlOff: () => app.repo.controlOff(n.path),
          onExplain: () => app.showReleaseReportAction(
              n.path, GatedAction.powerControl, 'Control power blocked'),
        );
      case ModuleCardKind.nameplate:
        return n.nameplate == null || n.nameplate!.isEmpty
            ? null
            : NameplateCard(plate: n.nameplate!);
      case ModuleCardKind.shift:
        return n.shift == null ? null : ShiftCard(shift: n.shift!);
      case ModuleCardKind.oee:
        if (n.oee == null) return null;
        return OeeCard(
          oee: n.oee!,
          onReset: () async {
            // §7.8 act-or-explain: blocked reset opens the release panel
            if (!app.session.permits(GatedAction.dataWrite)) {
              app.showReleaseReportAction(
                  n.path, GatedAction.dataWrite, 'OEE reset blocked');
              return;
            }
            final ok = await app.repo.resetOee(n.path);
            if (!ok) {
              app.showReleaseReportAction(
                  n.path, GatedAction.dataWrite, 'OEE reset blocked');
            }
          },
        );
      case ModuleCardKind.manualCommands:
        return n.commands.isEmpty ? null : _manualPanel(context, n);
      case ModuleCardKind.unitControls:
        if (!n.isUnit) return null;
        return FraktalCard(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
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
                Chip(
                    label: LText(
                        'Mode ${n.modeActive?.name.toUpperCase() ?? '-'}')),
                if (n.machineState != null)
                  Chip(
                      avatar: const Icon(Icons.factory_outlined, size: 18),
                      label: LText(n.machineState!.name.toUpperCase())),
              ]),
              if (n.stateFlags.isNotEmpty) _stateFlags(context, n.stateFlags),
              const SizedBox(height: 8),
              _controls(context, n, s),
            ]),
          ),
        );
      case ModuleCardKind.counters:
        if (!n.isUnit) return null;
        return FraktalCard(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Wrap(spacing: 8, runSpacing: 8, children: [
              Chip(label: LText('Good ${n.goodCount}')),
              Chip(label: LText('NOK ${n.nokCount}')),
              if (n.reworkCount > 0)
                Chip(label: LText('Rework ${n.reworkCount}')),
              if (n.lastCycleTime > Duration.zero)
                Chip(
                    avatar: const Icon(Icons.timer_outlined, size: 18),
                    label: LText(
                        'Cycle ${(n.lastCycleTime.inMilliseconds / 1000).toStringAsFixed(1)}s'
                        ' (best ${(n.minCycleTime.inMilliseconds / 1000).toStringAsFixed(1)}s)')),
            ]),
          ),
        );
      case ModuleCardKind.cycleAnalysis:
        if (!n.isUnit) return null;
        // §8.11.4(c) cycle-time analysis: trend (why it moved) -> Gantt (which
        // step, and where in the cycle) -> Pareto (which step, over time) ->
        // command timing per child module (which command).
        return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          CycleTrendView(history: n.cycleHistory, minCycleTime: n.minCycleTime),
          if (n.cycle != null) CycleProfileView(profile: n.cycle!),
          if (n.stepStats.isNotEmpty) StepParetoView(stats: n.stepStats),
          for (final child in n.children)
            if (child.commandTimings.isNotEmpty)
              CommandTimingView(
                  moduleName: child.name, rows: child.commandTimings),
        ]);
      case ModuleCardKind.activeEvents:
        return FraktalCard(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              LText('Active events',
                  style: Theme.of(context).textTheme.titleMedium),
              for (final e in n.activeEvents) _eventTile(context, e),
              if (n.activeEvents.isEmpty)
                const ListTile(dense: true, title: LText('—')),
            ]),
          ),
        );
      case ModuleCardKind.history:
        return n.isUnit && s.permits(GatedAction.alarmHistory)
            ? HistoryBrowser(node: n)
            : null;
      case ModuleCardKind.description:
        return ModuleInformationCard(app: app, node: n);
      case ModuleCardKind.documents:
        return ModuleDocumentsCard(app: app, node: n);
      case ModuleCardKind.modelData:
      case ModuleCardKind.stationData:
      case ModuleCardKind.lineData:
        final cfgKind = kind.configKind!;
        if (!ConfigEditor.shows(n, cfgKind)) return null;
        if (app.content.permits(n.path, ModuleSection.configuration, s.level)) {
          return ConfigEditor(app: app, node: n, kind: cfgKind);
        }
        final (title, _, icon) = ConfigEditor.kindGroups[cfgKind]!;
        return FraktalCard(
          child: ListTile(
            leading: Icon(icon),
            title: LText(title),
            subtitle: Text('${context.tr('Requires')} '
                '${context.tr('std.access.${app.content.requiredLevel(n.path, ModuleSection.configuration).name}')}'),
            trailing: const Icon(Icons.lock_outline),
          ),
        );
      case ModuleCardKind.operatorGuidance:
        final guidance = guidanceTab;
        if (guidance == null ||
            guidance.controls.isEmpty ||
            s.level.index < guidance.requiredLevel.index) {
          return null;
        }
        return FraktalCard(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              LText(guidance.title,
                  style: Theme.of(context).textTheme.titleMedium),
              const SizedBox(height: 8),
              SizedBox(
                height: 420,
                child: CustomModuleTabView(app: app, node: n, tab: guidance),
              ),
            ]),
          ),
        );
    }
  }

  // ---- edit mode ----

  void _commit(List<ModuleCardPlacement> cards) =>
      onChanged?.call(tab.copyWith(cards: cards));

  void _move(List<ModuleCardPlacement> cards, ModuleCardKind kind, int before) {
    final list = cards.toList();
    final from = list.indexWhere((card) => card.kind == kind);
    if (from < 0) return;
    final moved = list.removeAt(from);
    var at = before > from ? before - 1 : before;
    at = at.clamp(0, list.length).toInt();
    list.insert(at, moved);
    _commit(list);
  }

  Widget _editableCard(BuildContext context, ModuleNode n,
      ModuleCardPlacement placement, List<ModuleCardPlacement> cards) {
    final index = cards.indexOf(placement);
    final content = _card(context, n, placement.kind);
    final theme = Theme.of(context);
    final header = Row(children: [
      Draggable<ModuleCardKind>(
        data: placement.kind,
        feedback: Material(
          elevation: 6,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: LText('std.module.card.${placement.kind.name}'),
          ),
        ),
        child: Tooltip(
          message: context.tr('std.module.editor.dragCard'),
          child: const Padding(
            padding: EdgeInsets.all(6),
            child: Icon(Icons.drag_indicator),
          ),
        ),
      ),
      Expanded(
        child: LText('std.module.card.${placement.kind.name}',
            style: theme.textTheme.titleSmall, overflow: TextOverflow.ellipsis),
      ),
      PopupMenuButton<AccessLevel>(
        key: ValueKey('card-level-${placement.kind.name}'),
        tooltip: context.tr('std.module.editor.cardLevel'),
        initialValue: placement.requiredLevel,
        onSelected: (level) => _commit([
          for (final card in cards)
            card == placement ? card.copyWith(requiredLevel: level) : card,
        ]),
        itemBuilder: (_) => [
          for (final level in AccessLevel.values)
            PopupMenuItem(
                value: level, child: LText('std.access.${level.name}')),
        ],
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 6),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.lock_outline, size: 16),
            const SizedBox(width: 4),
            LText('std.access.${placement.requiredLevel.name}',
                style: theme.textTheme.labelSmall),
          ]),
        ),
      ),
      IconButton(
        key: ValueKey('card-visibility-${placement.kind.name}'),
        tooltip: context.tr(placement.hidden
            ? 'std.module.editor.showCard'
            : 'std.module.editor.hideCard'),
        onPressed: () => _commit([
          for (final card in cards)
            card == placement ? card.copyWith(hidden: !card.hidden) : card,
        ]),
        icon: Icon(placement.hidden
            ? Icons.visibility_off_outlined
            : Icons.visibility_outlined),
      ),
      IconButton(
        tooltip: context.tr('std.module.editor.removeCard'),
        onPressed: () =>
            _commit([for (final card in cards) if (card != placement) card]),
        icon: const Icon(Icons.close),
      ),
    ]);
    final body = Opacity(
      opacity: placement.hidden ? 0.4 : 1,
      child: IgnorePointer(
        // Arranging, not operating: the card's own buttons stay inert.
        child: content ??
            Padding(
              padding: const EdgeInsets.all(12),
              child: LText('std.module.editor.cardNoData',
                  style: theme.textTheme.bodySmall),
            ),
      ),
    );
    return DragTarget<ModuleCardKind>(
      onWillAcceptWithDetails: (details) => details.data != placement.kind,
      onAcceptWithDetails: (details) => _move(cards, details.data, index),
      builder: (context, candidates, _) => Container(
        key: ValueKey('card-${placement.kind.name}'),
        decoration: BoxDecoration(
          border: Border.all(
            color: candidates.isNotEmpty
                ? theme.colorScheme.primary
                : theme.colorScheme.outlineVariant,
            width: candidates.isNotEmpty ? 2 : 1,
          ),
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          header,
          body,
        ]),
      ),
    );
  }

  /// Dropping here moves a card to the end.
  Widget _endDropTarget(BuildContext context, List<ModuleCardPlacement> cards) =>
      DragTarget<ModuleCardKind>(
        onAcceptWithDetails: (details) =>
            _move(cards, details.data, cards.length),
        builder: (context, candidates, _) => Container(
          height: 56,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            border: Border.all(
                color: candidates.isNotEmpty
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.outlineVariant),
            borderRadius: BorderRadius.circular(10),
          ),
          child: const LText('std.module.editor.dropCardHere'),
        ),
      );

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
    // The card paints a tinted fill, so its content is wrapped in onContainer:
    // a Card only paints, it does not re-pair the foreground, and without this
    // every glyph inside inherits whatever style encloses the card (app_theme).
    final cardFill = operatorActionContainer(context);
    return FraktalCard(
      color: cardFill,
      shape: RoundedRectangleBorder(
          side: const BorderSide(color: kOperatorActionColor),
          borderRadius: BorderRadius.circular(12)),
      child: onContainer(
        context,
        cardFill,
        Padding(
          padding: const EdgeInsets.all(12),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Wrap(
                spacing: 8,
                runSpacing: 6,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
              const Icon(Icons.pan_tool_outlined, color: kOperatorActionColor),
              LText('Manual commands',
                  style: Theme.of(context).textTheme.titleMedium),
              // Each chip paints its own fill inside the tinted card, so each
              // pairs its own foreground rather than inheriting the card's.
              if (!inManual)
                _pairedChip(context, null, 'Unit not in MANUAL')
              else if (!canManual)
                _pairedChip(context, Icons.lock_outline, 'MANUAL access'),
            ]),
            const SizedBox(height: 4),
            LText(
                'Routed through the module — interlocks still apply (§7.6.1).',
                style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final c in n.commands)
                // §7.6.1a - a HELD command is hold-to-run, not a click: the control
                // refreshes the request while it is down and releases it on lift,
                // cancel, dispose - anything that ends the asking stops the motion.
                if (c.style == CommandStyle.held)
                  _HeldManualButton(app: app, node: n.path, command: c)
                else
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

/// §3.12 — the module's derived state, rendered generically: the HMI knows only
/// that these are named facts with a value and a moment, never what the module is.
Widget _stateFlags(BuildContext context, List<StateFlag> flags) {
  final scheme = Theme.of(context).colorScheme;
  final now = DateTime.now();
  return Padding(
    padding: const EdgeInsets.only(top: 8),
    child: Wrap(spacing: 8, runSpacing: 8, children: [
      for (final f in flags)
        Chip(
          avatar: Icon(
            // Stale is neither true nor false: the PLC stopped computing it, so
            // showing a confident "off" would be a claim nobody is making.
            f.stale
                ? Icons.help_outline
                : (f.value
                    ? Icons.check_circle_outline
                    : Icons.circle_outlined),
            size: 18,
            color: f.stale
                ? scheme.onSurfaceVariant
                : (f.value ? scheme.primary : scheme.onSurfaceVariant),
          ),
          label: LText(_flagLabel(f, now)),
        ),
    ]),
  );
}

String _flagLabel(StateFlag f, DateTime now) {
  if (f.stale || f.since == null) return f.key;
  final held = now.difference(f.since!);
  if (held.isNegative || held.inSeconds < 1) return f.key;
  if (held.inMinutes < 1) return '${f.key} · ${held.inSeconds}s';
  if (held.inHours < 1) return '${f.key} · ${held.inMinutes}m';
  return '${f.key} · ${held.inHours}h';
}

/// §7.6.1a refresh cadence for hold-to-run: 300 ms against the PLC's 750 ms
/// MANUAL_HELD_REFRESH_MS deadline, so two lost frames are tolerated before the
/// hold lapses. One constant, shared by every held control, so the cadence can
/// never drift per-button.
const _heldManualRefresh = Duration(milliseconds: 300);

/// A chip whose label and icon are explicitly paired to the chip's OWN fill.
///
/// Every bare `Chip` in this file was a latent white-on-white: Material gives it
/// a fill but leaves the label to whatever DefaultTextStyle encloses it, so the
/// ink came out with NO colour at all and landed on whatever the ancestor
/// happened to set — which is how the READY/BUSY/DONE state badge and the manual
/// card's blocked chip both went invisible on the light themes.
///
/// Library-level, not a method, so BOTH the detail state and the overview tab
/// share one pairing rule and a new chip cannot reintroduce the defect by
/// omission (app_theme.foregroundOn).
Widget _pairedChip(BuildContext context, IconData? icon, String label) {
  final fill = Theme.of(context).colorScheme.surface;
  final ink = foregroundOn(context, fill);
  return Chip(
    backgroundColor: fill,
    avatar: icon == null ? null : Icon(icon, size: 16, color: ink),
    label: LText(label, style: TextStyle(color: ink)),
  );
}

/// §7.6.1a — the press-and-hold control for a `Style = HELD` manual command.
///
/// Pointer DOWN latches the request on the PLC and starts a refresh timer;
/// pointer UP, pointer CANCEL, the widget's disposal, or the app going stale
/// releases it. Every path that ends the asking ends the motion — that is the
/// whole property of hold-to-run, and it is enforced on both ends: the PLC's
/// own `MANUAL_HELD_REFRESH_MS` deadline lets go if refreshes stop for any
/// reason this widget did not foresee.
///
/// Non-safety by construction (§9): no panel control is a dead-man. The
/// enabling-device fact is derived on the PLC from the §9 safety facet and
/// weighed there; this control only asks.
class _HeldManualButton extends StatefulWidget {
  final AppState app;
  final String node;
  final CommandInfo command;
  const _HeldManualButton(
      {required this.app, required this.node, required this.command});

  @override
  State<_HeldManualButton> createState() => _HeldManualButtonState();
}

class _HeldManualButtonState extends State<_HeldManualButton> {
  Timer? _refresh;
  bool _down = false;

  String get _root => widget.app.rootOf(widget.node)?.path ?? '';

  Future<void> _send(bool held) async {
    try {
      await widget.app.repo
          .manualHeld(_root, widget.node, widget.command.value, held);
    } catch (_) {
      // Transport gone: stop asking. The PLC deadline is the backstop; this
      // merely stops paying refreshes into a dead link.
      _stop();
    }
  }

  void _start() {
    if (_down) return;
    _down = true;
    _send(true);
    _refresh?.cancel();
    // §7.6.1a refresh cadence: 300 ms against the PLC's 750 ms deadline, so two
    // lost frames are tolerated before the hold lapses.
    _refresh = Timer.periodic(_heldManualRefresh, (_) {
      if (_down) {
        _send(true);
      } else {
        _stop();
      }
    });
    if (mounted) setState(() {});
  }

  void _stop() {
    if (!_down) return;
    _down = false;
    _refresh?.cancel();
    _refresh = null;
    _send(false);
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    // Disposal while held is the "operator navigated away mid-hold" case: the
    // release is issued without awaiting, because there is no frame left to
    // await it in. The PLC deadline covers the case where even this does not
    // get through.
    if (_down) {
      _send(false);
    }
    _refresh?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Listener(
      // Pointer-level rather than GestureDetector: a tap detector can swallow
      // the UP event in drag contexts, and a hold control must never miss the
      // release. onPointerCancel covers focus loss and route pops.
      onPointerDown: (_) => _start(),
      onPointerUp: (_) => _stop(),
      onPointerCancel: (_) => _stop(),
      child: FilledButton.tonal(
        style: FilledButton.styleFrom(
          backgroundColor: _down ? kOperatorActionColor : null,
          foregroundColor: _down ? Colors.white : null,
        ),
        onPressed: () {
          // Keyboard/assistive-tech activation has no "hold" semantics. For a
          // hold-to-run control, a click must NOT latch motion it cannot later
          // release through the same gesture - so it explains instead.
          widget.app.showReleaseReportManual(
              _root, widget.node, widget.command.value);
        },
        child: LText(widget.command.label),
      ),
    );
  }
}
