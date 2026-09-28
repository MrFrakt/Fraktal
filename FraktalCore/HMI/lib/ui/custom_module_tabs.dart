library;

import 'embedded_image.dart';
import 'dart:math' as math;

import 'background_canvas.dart';
import 'image_overlay.dart';

import 'package:flutter/material.dart';
import 'theme_surfaces.dart';

import '../content/module_content_controller.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';
import 'app_theme.dart';
import 'facet_cards.dart';
import 'touch_text_field.dart';

ModuleTabCapabilities moduleTabCapabilities(ModuleNode node) {
  final keys = node.hmiTags.keys.map((key) => key.toLowerCase()).toList();
  final identity = '${node.name} ${node.displayNameKey} ${node.descriptionKey}'
      .toLowerCase();
  bool hasKey(String suffix) => keys.any((key) => key.endsWith(suffix));
  return ModuleTabCapabilities(
    unit: node.isUnit,
    configuration: node.config.isNotEmpty,
    // The PLC owns this one: SequenceViewEnabled is published per module,
    // so a type too simple to draw suppresses its own tab (§3.13).
    // Keyed on the COUNT, not the rows: the rows are an on-demand subtree read
    // only while this tab is open, so requiring them here would mean the tab could
    // never appear to be opened. The count is live at the module root.
    sequence: node.sequenceViewEnabled && node.sequenceStepCount > 0,
    motion: node.motion != null,
    vision: identity.contains('vision') ||
        identity.contains('camera') ||
        hasKey('outcmd/judgeok') ||
        hasKey('outcmd/resultdata'),
    codeReader: identity.contains('codereader') ||
        identity.contains('barcode') ||
        identity.contains('dmc') ||
        hasKey('outcmd/code') ||
        hasKey('parcfg/triggercmd'),
    rfid: identity.contains('rfid') ||
        hasKey('outcmd/uid') ||
        hasKey('outimm/tagpresent') ||
        hasKey('outimm/lastuid'),
  );
}

class CustomModuleTabView extends StatefulWidget {
  final AppState app;
  final ModuleNode node;
  final ModuleTabDefinition tab;
  final bool editing;
  final ValueChanged<ModuleControlDefinition>? onEditControl;
  final ValueChanged<String>? onRemoveControl;
  final ValueChanged<int>? onMoveControlUp;
  final ValueChanged<int>? onMoveControlDown;
  final void Function(int oldIndex, int newIndex)? onReorderControl;

  /// A control moved on the tab's picture, or taken off it (null).
  final void Function(String id, ModulePlacement? placement)? onPlaceControl;

  /// A new control dropped from the palette onto the picture.
  final void Function(ModuleControlKind kind, ModulePlacement placement)?
      onAddControlAt;

  const CustomModuleTabView({
    super.key,
    required this.app,
    required this.node,
    required this.tab,
    this.editing = false,
    this.onEditControl,
    this.onRemoveControl,
    this.onMoveControlUp,
    this.onMoveControlDown,
    this.onReorderControl,
    this.onPlaceControl,
    this.onAddControlAt,
  });

  @override
  State<CustomModuleTabView> createState() => _CustomModuleTabViewState();
}

class _CustomModuleTabViewState extends State<CustomModuleTabView> {
  final Map<String, _ChartSeries> _series = {};

  /// Layers this viewer has hidden. Per panel and per session: a show/hide
  /// set is a way of looking, not a setting of the machine.
  final Set<String> _hiddenLayers = {};

  /// Whether [control] is drawn right now. While editing, everything is, so
  /// nothing can be lost from the editor behind a hidden layer.
  bool _shown(ModuleControlDefinition control) {
    if (widget.editing) return true;
    if (control.layer.isNotEmpty && _hiddenLayers.contains(control.layer)) {
      return false;
    }
    final condition = control.visibleWhen;
    if (condition == null) return true;
    final tag = widget.node.tagAt(condition.binding);
    // Unavailable data never hides an indicator.
    return tag?.usable != true || condition.matches(tag!.value);
  }

  List<ModuleControlDefinition> get _controls =>
      [for (final control in widget.tab.controls) if (_shown(control)) control];

  /// §7.4: on an operating view colour is reserved for the abnormal, so an OK
  /// state draws neutral there; on maintenance/engineering views it is green.
  Color _tokenColor(BuildContext context, ModuleStateToken token) =>
      stateTokenColor(
        context,
        token == ModuleStateToken.ok &&
                widget.tab.viewClass == ModuleViewClass.operating
            ? ModuleStateToken.neutral
            : token,
      );

  Widget? _layerBar(BuildContext context) {
    final layers = widget.tab.layers;
    if (widget.editing || layers.isEmpty) return null;
    return Wrap(spacing: 6, runSpacing: 6, children: [
      for (final layer in layers)
        FilterChip(
          key: ValueKey('layer-$layer'),
          label: LText(layer),
          selected: !_hiddenLayers.contains(layer),
          onSelected: (show) => setState(() =>
              show ? _hiddenLayers.remove(layer) : _hiddenLayers.add(layer)),
        ),
    ]);
  }

  @override
  void initState() {
    super.initState();
    _sampleCharts();
  }

  @override
  void didUpdateWidget(covariant CustomModuleTabView oldWidget) {
    super.didUpdateWidget(oldWidget);
    _sampleCharts();
  }

  void _sampleCharts() {
    final now = DateTime.now();
    final chartSeriesKeys = <String>{};
    for (final control in widget.tab.controls) {
      if (control.kind != ModuleControlKind.chart) continue;
      for (final binding in control.linkedBindings) {
        final key = _chartSeriesKey(control.id, binding);
        chartSeriesKeys.add(key);
        final tag = widget.node.tagAt(binding);
        final value = tag?.value;
        if (tag?.usable != true || value is! num) continue;
        final series = _series.putIfAbsent(
          key,
          () => _ChartSeries(binding, control.samplePeriodMs),
        );
        if (series.binding != binding ||
            series.periodMs != control.samplePeriodMs) {
          series.reset(binding, control.samplePeriodMs);
        }
        if (series.lastSample != null &&
            now.difference(series.lastSample!).inMilliseconds <
                control.samplePeriodMs) {
          continue;
        }
        series.lastSample = now;
        series.values.add(value.toDouble());
        while (series.values.length > control.historyPoints) {
          series.values.removeAt(0);
        }
      }
    }
    _series.removeWhere((key, _) => !chartSeriesKeys.contains(key));
  }

  /// A custom tab with a picture is a canvas: placed controls sit on the
  /// picture, the rest beside it. Never over it - a card floating over the
  /// machine would hide the very door or sensor it is next to.
  bool get _hasCanvas {
    final background = widget.tab.background;
    return widget.tab.kind.acceptsBackground &&
        background != null &&
        background.imageBase64.isNotEmpty;
  }

  @override
  Widget build(BuildContext context) {
    if (_hasCanvas) return _canvasLayout(context);
    if (widget.tab.controls.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: LText(widget.editing
              ? 'std.module.editor.emptyTab'
              : 'std.module.custom.empty'),
        ),
      );
    }
    if (widget.editing) {
      return ReorderableListView.builder(
        padding: const EdgeInsets.all(16),
        buildDefaultDragHandles: false,
        itemCount: widget.tab.controls.length,
        onReorderItem: (oldIndex, newIndex) =>
            widget.onReorderControl?.call(oldIndex, newIndex),
        itemBuilder: (context, index) =>
            _editableControl(context, widget.tab.controls[index], index),
      );
    }
    final layerBar = _layerBar(context);
    return LayoutBuilder(builder: (context, constraints) {
      final available = math.max(0.0, constraints.maxWidth - 32);
      return SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            if (layerBar != null) SizedBox(width: available, child: layerBar),
            for (final control in _controls)
              SizedBox(
                width: _responsiveControlWidth(available, control.width),
                child: _renderControl(context, control),
              ),
          ],
        ),
      );
    });
  }

  Widget _canvasLayout(BuildContext context) {
    final placed = [
      for (final control in _controls)
        if (control.placement != null) control,
    ];
    final flow = [
      for (final control in _controls)
        if (control.placement == null) control,
    ];
    final layerBar = _layerBar(context);
    final picture = BackgroundCanvas(
      background: widget.tab.background!,
      overlay: (context, image) => widget.editing
          ? PlacementEditor(
              image: image,
              controls: placed,
              render: (control) => _overlayControl(context, control),
              onPlace: widget.onPlaceControl,
              onAddAt: widget.onAddControlAt,
              onEdit: widget.onEditControl,
              onRemove: widget.onRemoveControl,
              onRestack: (id, front) {
                final all = widget.tab.controls;
                final from = all.indexWhere((control) => control.id == id);
                final to = front ? all.length - 1 : 0;
                if (from >= 0 && from != to) {
                  widget.onReorderControl?.call(from, to);
                }
              },
            )
          : Stack(children: [
              for (final control in placed)
                Positioned.fromRect(
                  rect: placementRect(control.placement!, image),
                  child: _overlayControl(context, control),
                ),
            ]),
    );
    final Widget? side = widget.editing
        ? _canvasEditPanel(context, flow)
        : flow.isEmpty
            ? null
            : ListView(padding: const EdgeInsets.all(12), children: [
                for (final control in flow)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 10),
                    child: _renderControl(context, control),
                  ),
              ]);
    final canvas = layerBar == null
        ? picture
        : Stack(fit: StackFit.expand, children: [
            picture,
            Positioned(left: 8, top: 8, right: 8, child: layerBar),
          ]);
    if (side == null) return canvas;
    return LayoutBuilder(builder: (context, constraints) {
      if (constraints.maxWidth >= 900) {
        return Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(child: canvas),
          SizedBox(width: 320, child: side),
        ]);
      }
      return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Expanded(child: canvas),
        SizedBox(
          height: math.max(160.0, constraints.maxHeight * 0.38),
          child: side,
        ),
      ]);
    });
  }

  Widget _canvasEditPanel(
      BuildContext context, List<ModuleControlDefinition> flow) {
    final text = Theme.of(context).textTheme;
    return ListView(padding: const EdgeInsets.all(12), children: [
      LText('std.module.editor.paletteTitle', style: text.titleSmall),
      const SizedBox(height: 4),
      LText('std.module.editor.paletteHelp', style: text.bodySmall),
      const SizedBox(height: 10),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final kind in kOverlayPaletteKinds)
          OverlayDragSource(
            key: ValueKey('palette-${kind.name}'),
            data: NewControlDrop(kind),
            feedback: _paletteChip(kind),
            child: _paletteChip(kind),
          ),
      ]),
      if (flow.isNotEmpty) ...[
        const SizedBox(height: 18),
        LText('std.module.editor.notOnImage', style: text.titleSmall),
        const SizedBox(height: 8),
        for (final control in flow)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: _editableControl(
              context,
              control,
              widget.tab.controls.indexOf(control),
              reorderable: false,
            ),
          ),
      ],
    ]);
  }

  Widget _paletteChip(ModuleControlKind kind) => Chip(
        avatar: Icon(_controlIcon(kind), size: 18),
        label: LText(_controlKindKey(kind)),
      );

  /// A control drawn on the picture, filling its placed box.
  Widget _overlayControl(
      BuildContext context, ModuleControlDefinition control) {
    final tags = [
      for (final binding in control.linkedBindings) widget.node.tagAt(binding)
    ];
    // Bad/Uncertain data renders unavailable, never as a state: a door drawn
    // green from a stale value is worse than a door drawn "unknown".
    final usable =
        tags.isNotEmpty && tags.every((tag) => tag?.usable == true);
    final values = [for (final tag in tags) tag?.value];
    final token = usable ? control.resolveState(values) : null;
    final color = token == null ? null : _tokenColor(context, token);
    final label = control.label.isEmpty ? control.primaryBinding : control.label;
    final unit = control.unit.isEmpty ? '' : ' ${control.unit}';
    final Widget body = switch (control.kind) {
      ModuleControlKind.shape =>
        _OverlayShape(shape: control.shape, color: color),
      ModuleControlKind.level => _OverlayLevel(
          control: control,
          value: usable ? values.first : null,
          color: color,
        ),
      ModuleControlKind.indicator =>
        _OverlayLed(on: usable ? _asBool(values.first) : null),
      ModuleControlKind.value => _OverlayChip(
          text: usable ? '${_formatValue(values.first)}$unit' : '?',
          unavailable: !usable,
        ),
      ModuleControlKind.text => _OverlayChip(
          text: context.tr(control.text.isEmpty ? label : control.text),
          unavailable: false,
        ),
      _ => FittedBox(
          child: SizedBox(width: 280, child: _renderControl(context, control)),
        ),
    };
    final state = switch (control.kind) {
      ModuleControlKind.text => '',
      _ when tags.isEmpty => '',
      _ when !usable => _tagQualityText(
          tags.firstWhere((tag) => tag?.usable != true, orElse: () => null)),
      ModuleControlKind.shape ||
      ModuleControlKind.level =>
        context.tr(_stateTokenKey(token!)),
      _ => '${_formatValue(values.first)}$unit',
    };
    final name = context.tr(label);
    return Tooltip(
      message: state.isEmpty ? name : '$name: $state',
      child: usable && control.ruleFor(values)?.blink == true
          ? _Blink(child: body)
          : body,
    );
  }

  Widget _editableControl(
      BuildContext context, ModuleControlDefinition control, int index,
      {bool reorderable = true}) {
    final rendered = _renderControl(context, control);
    if (!widget.editing) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: rendered,
      );
    }
    return FraktalCard(
      key: ValueKey('edit-control-${control.id}'),
      shape: RoundedRectangleBorder(
        side: BorderSide(color: Theme.of(context).colorScheme.primary),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(children: [
        Row(children: [
          const SizedBox(width: 8),
          if (reorderable)
            ReorderableDragStartListener(
              index: index,
              child: const Padding(
                padding: EdgeInsets.all(8),
                child: Icon(Icons.drag_indicator),
              ),
            )
          else
            // Beside a picture the handle places the control ON the picture.
            OverlayDragSource(
              data: ExistingControlDrop(control),
              feedback: _paletteChip(control.kind),
              child: Tooltip(
                message: context.tr('std.module.editor.dragOntoImage'),
                child: const Padding(
                  padding: EdgeInsets.all(8),
                  child: Icon(Icons.open_with),
                ),
              ),
            ),
          Icon(_controlIcon(control.kind), size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: LText(
                control.label.isEmpty ? control.kind.name : control.label),
          ),
          if (reorderable) ...[
            IconButton(
              tooltip: context.tr('std.common.moveUp'),
              onPressed: index == 0
                  ? null
                  : () => widget.onMoveControlUp?.call(index),
              icon: const Icon(Icons.arrow_upward),
            ),
            IconButton(
              tooltip: context.tr('std.common.moveDown'),
              onPressed: index == widget.tab.controls.length - 1
                  ? null
                  : () => widget.onMoveControlDown?.call(index),
              icon: const Icon(Icons.arrow_downward),
            ),
          ],
          IconButton(
            tooltip: context.tr('std.common.edit'),
            onPressed: () => widget.onEditControl?.call(control),
            icon: const Icon(Icons.edit_outlined),
          ),
          IconButton(
            tooltip: context.tr('std.common.delete'),
            onPressed: () => widget.onRemoveControl?.call(control.id),
            icon: const Icon(Icons.delete_outline),
          ),
        ]),
        IgnorePointer(child: rendered),
      ]),
    );
  }

  Widget _renderControl(BuildContext context, ModuleControlDefinition control) {
    final tag = widget.node.tagAt(control.primaryBinding);
    return switch (control.kind) {
      ModuleControlKind.text => _TextControl(control: control),
      ModuleControlKind.value => _ValueControl(control: control, tag: tag),
      ModuleControlKind.indicator =>
        _IndicatorControl(control: control, tag: tag),
      ModuleControlKind.chart => _ChartControl(
          control: control,
          series: {
            for (final binding in control.linkedBindings)
              binding: _series[_chartSeriesKey(control.id, binding)]?.values ??
                  const [],
          },
          current: {
            for (final binding in control.linkedBindings)
              binding: widget.node.tagAt(binding),
          },
        ),
      ModuleControlKind.button => _ActionControl(
          app: widget.app,
          node: widget.node,
          control: control,
        ),
      ModuleControlKind.textInput => _TextInputControl(
          app: widget.app,
          node: widget.node,
          control: control,
          tag: tag,
        ),
      ModuleControlKind.image => _ImageControl(control: control),
      ModuleControlKind.shape || ModuleControlKind.level => _StateCard(
          control: control,
          tokenColor: _tokenColor,
          tags: [
            for (final binding in control.linkedBindings)
              widget.node.tagAt(binding)
          ],
        ),
    };
  }
}

class MotionModuleTab extends StatelessWidget {
  final ModuleNode node;
  const MotionModuleTab({super.key, required this.node});

  @override
  Widget build(BuildContext context) {
    final motion = node.motion;
    if (motion == null)
      return const Center(child: LText('std.module.motion.notPublished'));
    final error = motion.targetPosition - motion.actualPosition;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Wrap(spacing: 12, runSpacing: 12, children: [
        _MetricCard(
            label: 'std.module.motion.actualPosition',
            value: _formatNumber(motion.actualPosition),
            unit: motion.unit,
            icon: Icons.straighten),
        _MetricCard(
            label: 'std.module.motion.targetPosition',
            value: _formatNumber(motion.targetPosition),
            unit: motion.unit,
            icon: Icons.flag_outlined),
        _MetricCard(
            label: 'std.module.motion.velocity',
            value: _formatNumber(motion.actualVelocity),
            unit: '${motion.unit}/s',
            icon: Icons.speed),
        _MetricCard(
            label: 'std.module.motion.positionError',
            value: _formatNumber(error),
            unit: motion.unit,
            icon: Icons.compare_arrows),
      ]),
      const SizedBox(height: 12),
      FraktalCard(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            LText('std.module.motion.axisState',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              _StateChip(
                  label: 'std.module.motion.homed',
                  active: motion.homed,
                  abnormalWhenFalse: true),
              _StateChip(
                  label: 'std.module.motion.moving', active: motion.moving),
              _StateChip(
                  label: 'std.module.motion.fault',
                  active: node.faultActive,
                  abnormalWhenTrue: true),
            ]),
            const SizedBox(height: 12),
            const LText('std.module.motion.nonSafetyNotice'),
          ]),
        ),
      ),
      if (node.motion != null) MotionCard(m: node.motion!),
    ]);
  }
}

class VisionModuleTab extends StatelessWidget {
  final AppState app;
  final ModuleNode node;
  const VisionModuleTab({super.key, required this.app, required this.node});

  @override
  Widget build(BuildContext context) {
    final judged = node.valueAt('OutCmd/JudgeOk') != null;
    final judgeOk = _asBool(node.valueAt('OutCmd/JudgeOk'));
    final result = _firstValue(node, const [
      'OutCmd/ResultData',
      'OutImm/LastResponse',
    ]);
    final trigger = node.commands.where((command) {
      final label = command.label.toLowerCase();
      return label.contains('trigger') ||
          label.contains('inspect') ||
          label.contains('acquire');
    }).firstOrNull;
    final colors = Theme.of(context).colorScheme;
    return ListView(padding: const EdgeInsets.all(16), children: [
      FraktalCard(
        color: !judged
            ? colors.surfaceContainerLow
            : judgeOk
                ? colors.primaryContainer
                : colors.errorContainer,
        // A filled Card does not restyle its content, so pair the foreground
        // explicitly or the text keeps inheriting onSurface (app_theme).
        child: onContainer(
          context,
          !judged
              ? colors.surfaceContainerLow
              : judgeOk
                  ? colors.primaryContainer
                  : colors.errorContainer,
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(children: [
              Row(children: [
                Icon(judgeOk
                    ? Icons.check_circle_outline
                    : Icons.highlight_off_outlined),
                const SizedBox(width: 10),
                Expanded(
                  child: LText(
                    !judged
                        ? 'std.module.vision.noResult'
                        : judgeOk
                            ? 'std.module.vision.ok'
                            : 'std.module.vision.ng',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ),
                if (trigger != null)
                  FilledButton.tonalIcon(
                    onPressed: () =>
                        _manualCommand(context, app, node, trigger),
                    icon: const Icon(Icons.camera_alt_outlined),
                    label: const LText('std.module.vision.trigger'),
                  ),
              ]),
              const SizedBox(height: 16),
              Align(
                alignment: Alignment.centerLeft,
                child: SelectableText(
                  result == null || '$result'.isEmpty ? '—' : '$result',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                        fontFamily: 'monospace',
                      ),
                ),
              ),
            ]),
          ),
        ),
      ),
      const SizedBox(height: 12),
      const FraktalCard(
        child: ListTile(
          leading: Icon(Icons.image_outlined),
          title: LText('std.module.vision.imageUnavailable'),
          subtitle: LText('std.module.vision.imagePublicationHelp'),
        ),
      ),
      if (node.link != null) LinkCard(link: node.link!),
    ]);
  }
}

class CodeReaderModuleTab extends StatelessWidget {
  final AppState app;
  final ModuleNode node;
  const CodeReaderModuleTab({super.key, required this.app, required this.node});

  @override
  Widget build(BuildContext context) {
    final code = _firstValue(node, const [
      'OutCmd/Code',
      'OutImm/LastCode',
      'OutImm/LastResponse',
    ]);
    final noRead = _asBool(_firstValue(node, const ['OutCmd/NoRead']));
    final matchOk = _asBool(_firstValue(node, const ['OutCmd/MatchOk']));
    final triggers = _asInt(_firstValue(node, const [
      'OutImm/TriggerCount',
      'OutImm/Triggers',
    ]));
    final good = _asInt(_firstValue(node, const [
      'OutImm/GoodReads',
      'OutImm/ReadCount',
    ]));
    final failures = _asInt(_firstValue(node, const [
      'OutImm/NoReads',
      'OutImm/NoReadCount',
    ]));
    final trigger = node.commands.where((command) {
      final label = command.label.toLowerCase();
      return label.contains('trigger') || label.contains('read');
    }).firstOrNull;
    return ListView(padding: const EdgeInsets.all(16), children: [
      Wrap(spacing: 12, runSpacing: 12, children: [
        _MetricCard(
            label: 'std.module.reader.triggers',
            value: '$triggers',
            icon: Icons.bolt_outlined),
        _MetricCard(
            label: 'std.module.reader.goodReads',
            value: '$good',
            icon: Icons.check_circle_outline),
        _MetricCard(
            label: 'std.module.reader.noReads',
            value: '$failures',
            icon: Icons.error_outline),
      ]),
      const SizedBox(height: 12),
      FraktalCard(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.qr_code_scanner),
              const SizedBox(width: 8),
              LText('std.module.reader.lastResult',
                  style: Theme.of(context).textTheme.titleMedium),
              const Spacer(),
              if (trigger != null)
                FilledButton.tonalIcon(
                  onPressed: () => _manualCommand(context, app, node, trigger),
                  icon: const Icon(Icons.play_arrow),
                  label: const LText('std.module.reader.trigger'),
                ),
            ]),
            const SizedBox(height: 14),
            SelectableText(
              code == null || '$code'.isEmpty ? '—' : '$code',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 12),
            Wrap(spacing: 8, children: [
              _StateChip(
                  label: 'std.module.reader.noRead',
                  active: noRead,
                  abnormalWhenTrue: true),
              _StateChip(
                  label: 'std.module.reader.matchOk',
                  active: matchOk,
                  abnormalWhenFalse: true),
              if (node.link != null)
                _StateChip(
                    label: 'std.module.reader.linked',
                    active: node.link!.linked,
                    abnormalWhenFalse: true),
            ]),
          ]),
        ),
      ),
    ]);
  }
}

class RfidModuleTab extends StatelessWidget {
  final AppState app;
  final ModuleNode node;
  const RfidModuleTab({super.key, required this.app, required this.node});

  @override
  Widget build(BuildContext context) {
    final uid = _firstValue(node, const [
      'OutCmd/Uid',
      'OutImm/LastUid',
      'OutImm/Uid',
      'Part/Uid',
    ]);
    final present = _asBool(_firstValue(node, const [
      'OutImm/TagPresent',
      'Part/Present',
    ]));
    final quality = _firstValue(node, const [
      'OutImm/ReadQuality',
      'OutImm/Quality',
    ]);
    final read = node.commands.where((command) {
      final label = command.label.toLowerCase();
      return label.contains('read') || label.contains('scan');
    }).firstOrNull;
    return ListView(padding: const EdgeInsets.all(16), children: [
      FraktalCard(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.contactless_outlined),
              const SizedBox(width: 8),
              LText('std.module.rfid.currentTag',
                  style: Theme.of(context).textTheme.titleMedium),
              const Spacer(),
              if (read != null)
                FilledButton.tonalIcon(
                  onPressed: () => _manualCommand(context, app, node, read),
                  icon: const Icon(Icons.rss_feed),
                  label: const LText('std.module.rfid.read'),
                ),
            ]),
            const SizedBox(height: 14),
            SelectableText(
              uid == null || '$uid'.isEmpty ? '—' : '$uid',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontFamily: 'monospace',
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 12),
            Wrap(spacing: 8, children: [
              _StateChip(label: 'std.module.rfid.tagPresent', active: present),
              if (quality != null)
                Chip(
                    label: Text(
                        '${context.tr('std.module.rfid.quality')}: $quality')),
              if (node.link != null)
                _StateChip(
                    label: 'std.module.reader.linked',
                    active: node.link!.linked,
                    abnormalWhenFalse: true),
            ]),
          ]),
        ),
      ),
    ]);
  }
}

class _TextControl extends StatelessWidget {
  final ModuleControlDefinition control;
  const _TextControl({required this.control});

  @override
  Widget build(BuildContext context) => FraktalCard(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            if (control.label.isNotEmpty)
              LText(control.label,
                  style: Theme.of(context).textTheme.titleMedium),
            if (control.label.isNotEmpty) const SizedBox(height: 8),
            LText(control.text),
          ]),
        ),
      );
}

class _ValueControl extends StatelessWidget {
  final ModuleControlDefinition control;
  final PublishedTagValue? tag;
  const _ValueControl({required this.control, required this.tag});

  @override
  Widget build(BuildContext context) {
    if (tag?.usable == true) {
      return _MetricCard(
        label: control.label.isEmpty ? control.primaryBinding : control.label,
        value: _formatValue(tag!.value),
        unit: control.unit,
        icon: Icons.data_object,
      );
    }
    return _UnavailableTagCard(control: control, tag: tag);
  }
}

class _IndicatorControl extends StatelessWidget {
  final ModuleControlDefinition control;
  final PublishedTagValue? tag;
  const _IndicatorControl({required this.control, required this.tag});

  @override
  Widget build(BuildContext context) {
    final usable = tag?.usable == true;
    final active = usable && _asBool(tag?.value);
    final colors = Theme.of(context).colorScheme;
    return FraktalCard(
      child: ListTile(
        leading: Container(
          width: 18,
          height: 18,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: !usable
                ? colors.errorContainer
                : active
                    ? colors.primary
                    : colors.outlineVariant,
            border: Border.all(color: colors.outline),
          ),
        ),
        title: LText(
            control.label.isEmpty ? control.primaryBinding : control.label),
        subtitle: Text(!usable
            ? _tagQualityText(tag)
            : active
                ? (control.text.isEmpty ? 'ON' : control.text)
                : 'OFF'),
        trailing: usable ? null : const Icon(Icons.warning_amber_rounded),
      ),
    );
  }
}

/// A shape or level control away from a picture: its state as a card.
class _StateCard extends StatelessWidget {
  final ModuleControlDefinition control;
  final List<PublishedTagValue?> tags;
  final Color Function(BuildContext, ModuleStateToken) tokenColor;
  const _StateCard(
      {required this.control, required this.tags, required this.tokenColor});

  @override
  Widget build(BuildContext context) {
    final unusable =
        tags.where((tag) => tag?.usable != true).toList(growable: false);
    if (tags.isEmpty || unusable.isNotEmpty) {
      return _UnavailableTagCard(
          control: control, tag: unusable.firstOrNull);
    }
    final values = [for (final tag in tags) tag!.value];
    final token = control.resolveState(values);
    final color = tokenColor(context, token);
    final level = control.kind == ModuleControlKind.level;
    return FraktalCard(
      child: ListTile(
        leading: SizedBox(
          width: level ? 16 : 28,
          height: 32,
          child: level
              ? _OverlayLevel(
                  control: control,
                  value: values.first,
                  color: color,
                  showValue: false,
                )
              : _OverlayShape(shape: control.shape, color: color),
        ),
        title: LText(
            control.label.isEmpty ? control.primaryBinding : control.label),
        subtitle: level
            ? Text('${_formatValue(values.first)}'
                '${control.unit.isEmpty ? '' : ' ${control.unit}'}')
            : LText(_stateTokenKey(token)),
      ),
    );
  }
}

/// Flashes [child] about once a second - for the one state that must catch
/// the eye. Steady when the platform asks for reduced motion.
class _Blink extends StatefulWidget {
  final Widget child;
  const _Blink({required this.child});

  @override
  State<_Blink> createState() => _BlinkState();
}

class _BlinkState extends State<_Blink> with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 500),
    lowerBound: 0.25,
  )..repeat(reverse: true);

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => MediaQuery.disableAnimationsOf(context)
      ? widget.child
      : FadeTransition(opacity: _pulse, child: widget.child);
}

/// A coloured outline over a picture: a door, a guard, an e-stop. The fill is
/// translucent so the machine stays visible through it, and a state glows.
class _OverlayShape extends StatelessWidget {
  final ModuleShape shape;

  /// Null = the data is unavailable.
  final Color? color;
  const _OverlayShape({required this.shape, required this.color});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final tint = color;
    final box = DecoratedBox(
      decoration: BoxDecoration(
        color: tint == null
            ? colors.surface.withValues(alpha: 0.35)
            : tint.withValues(alpha: 0.32),
        shape: shape == ModuleShape.circle ? BoxShape.circle : BoxShape.rectangle,
        borderRadius: shape == ModuleShape.rounded
            ? BorderRadius.circular(12)
            : null,
        border: Border.all(color: tint ?? colors.error, width: 2),
        boxShadow: tint == null
            ? null
            : [
                BoxShadow(
                  color: tint.withValues(alpha: 0.55),
                  blurRadius: 14,
                  spreadRadius: 1,
                ),
              ],
      ),
      child: tint == null
          ? FittedBox(
              child: Padding(
                padding: const EdgeInsets.all(4),
                child: Icon(Icons.help_outline, color: colors.error),
              ),
            )
          : const SizedBox.expand(),
    );
    if (shape != ModuleShape.circle) return box;
    return Center(child: AspectRatio(aspectRatio: 1, child: box));
  }
}

/// A level bar over a picture - a tank's contents. Vertical when its box is
/// taller than wide, so the author chooses the orientation by drawing it.
class _OverlayLevel extends StatelessWidget {
  final ModuleControlDefinition control;
  final Object? value;

  /// Null = the data is unavailable.
  final Color? color;
  final bool showValue;

  const _OverlayLevel({
    required this.control,
    required this.value,
    required this.color,
    this.showValue = true,
  });

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final number = switch (value) {
      num n => n.toDouble(),
      String s => double.tryParse(s),
      _ => null,
    };
    final span = control.maximum - control.minimum;
    final fraction = number == null || span <= 0
        ? 0.0
        : ((number - control.minimum) / span).clamp(0.0, 1.0);
    final fill = color ?? colors.outline;
    return LayoutBuilder(builder: (context, constraints) {
      final vertical = constraints.maxHeight >= constraints.maxWidth;
      return Stack(fit: StackFit.expand, children: [
        DecoratedBox(
          decoration: BoxDecoration(
            color: colors.surface.withValues(alpha: 0.45),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: color == null ? colors.error : colors.outline,
              width: 1.5,
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(3),
          child: Align(
            alignment:
                vertical ? Alignment.bottomCenter : Alignment.centerLeft,
            child: FractionallySizedBox(
              heightFactor: vertical ? fraction : 1,
              widthFactor: vertical ? 1 : fraction,
              child: DecoratedBox(
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(4),
                  gradient: LinearGradient(
                    begin: vertical
                        ? Alignment.bottomCenter
                        : Alignment.centerLeft,
                    end: vertical ? Alignment.topCenter : Alignment.centerRight,
                    colors: [fill.withValues(alpha: 0.7), fill],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: fill.withValues(alpha: 0.45),
                      blurRadius: 8,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
        if (showValue)
          Center(
            child: _OverlayChip(
              text: number == null
                  ? '?'
                  : '${_formatValue(value)}'
                      '${control.unit.isEmpty ? '' : ' ${control.unit}'}',
              unavailable: color == null,
              expand: false,
            ),
          ),
      ]);
    });
  }
}

/// A lamp over a picture - a part-present sensor. Lit it glows; unlit it is
/// dark; unavailable it is outlined in the error colour.
class _OverlayLed extends StatelessWidget {
  final bool? on;
  const _OverlayLed({required this.on});

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final lit = on == true;
    final base = on == null
        ? colors.surface
        : lit
            ? okColor(context)
            : colors.outlineVariant;
    return Center(
      child: AspectRatio(
        aspectRatio: 1,
        child: DecoratedBox(
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            // The off-centre highlight is the lamp's reflection.
            gradient: RadialGradient(
              center: const Alignment(-0.35, -0.35),
              colors: [
                Color.lerp(base, Colors.white, lit ? 0.55 : 0.15)!,
                base,
              ],
            ),
            border: Border.all(
              color: on == null ? colors.error : colors.outline,
              width: 1.5,
            ),
            boxShadow: lit
                ? [
                    BoxShadow(
                      color: base.withValues(alpha: 0.75),
                      blurRadius: 12,
                      spreadRadius: 2,
                    ),
                  ]
                : null,
          ),
        ),
      ),
    );
  }
}

/// A value or caption over a picture, on a translucent plate that keeps it
/// readable over any image.
class _OverlayChip extends StatelessWidget {
  final String text;
  final bool unavailable;
  final bool expand;

  const _OverlayChip({
    required this.text,
    required this.unavailable,
    this.expand = true,
  });

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final chip = Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: colors.surface.withValues(alpha: 0.82),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: unavailable ? colors.error : colors.outlineVariant,
        ),
      ),
      child: FittedBox(
        fit: BoxFit.scaleDown,
        child: Text(
          text,
          maxLines: 1,
          style: TextStyle(
            color: unavailable ? colors.error : colors.onSurface,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
    return expand ? SizedBox.expand(child: Center(child: chip)) : chip;
  }
}

class _UnavailableTagCard extends StatelessWidget {
  final ModuleControlDefinition control;
  final PublishedTagValue? tag;

  const _UnavailableTagCard({required this.control, required this.tag});

  @override
  Widget build(BuildContext context) => FraktalCard(
        child: ListTile(
          leading: Icon(
            Icons.warning_amber_rounded,
            color: Theme.of(context).colorScheme.error,
          ),
          title: LText(
              control.label.isEmpty ? control.primaryBinding : control.label),
          subtitle: Text(_tagQualityText(tag)),
          trailing: Text(tag?.typeName ?? '--'),
        ),
      );
}

class _ChartControl extends StatelessWidget {
  final ModuleControlDefinition control;
  final Map<String, List<double>> series;
  final Map<String, PublishedTagValue?> current;
  const _ChartControl({
    required this.control,
    required this.series,
    required this.current,
  });

  @override
  Widget build(BuildContext context) {
    final bindings = control.linkedBindings;
    final colors = _chartLineColors(context, bindings.length);
    final pointCount = series.values.fold<int>(
      0,
      (maximum, values) => math.max(maximum, values.length),
    );
    return FraktalCard(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          LText(
            control.label.isEmpty ? 'std.module.custom.trend' : control.label,
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 14,
            runSpacing: 6,
            children: [
              for (var index = 0; index < bindings.length; index++)
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 18,
                      height: 3,
                      color: colors[index],
                    ),
                    const SizedBox(width: 6),
                    Text(
                      '${bindings[index]}: '
                      '${current[bindings[index]]?.usable == true ? _formatValue(current[bindings[index]]!.value) : _tagQualityText(current[bindings[index]])}'
                      '${control.unit.isEmpty ? '' : ' ${control.unit}'}',
                    ),
                  ],
                ),
            ],
          ),
          const SizedBox(height: 12),
          SizedBox(
            height: 150,
            child: CustomPaint(
              painter: _TrendPainter(
                [for (final binding in bindings) series[binding] ?? const []],
                colors,
                Theme.of(context).colorScheme.outlineVariant,
              ),
              child: const SizedBox.expand(),
            ),
          ),
          const SizedBox(height: 6),
          Text(
            '${control.samplePeriodMs} ms · '
            '$pointCount/${control.historyPoints}',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ]),
      ),
    );
  }
}

class _ActionControl extends StatefulWidget {
  final AppState app;
  final ModuleNode node;
  final ModuleControlDefinition control;
  const _ActionControl({
    required this.app,
    required this.node,
    required this.control,
  });

  @override
  State<_ActionControl> createState() => _ActionControlState();
}

class _ActionControlState extends State<_ActionControl> {
  bool _busy = false;

  bool get _catalogAvailable {
    final control = widget.control;
    return switch (control.action) {
      ModuleActionKind.none || ModuleActionKind.writeConfig => false,
      ModuleActionKind.manualCommand => widget.node.commands
          .any((command) => command.value == control.actionValue),
      ModuleActionKind.decisionAnswer => () {
          final decision = widget.app.rootOf(widget.node.path)?.decision;
          return decision?.pending == true &&
              control.actionValue >= 1 &&
              control.actionValue <= decision!.options.length;
        }(),
      _ => true,
    };
  }

  @override
  Widget build(BuildContext context) {
    final control = widget.control;
    final available =
        _catalogAvailable && _enabledByBinding(widget.node, control);
    return Align(
      alignment: Alignment.centerLeft,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        FilledButton.tonalIcon(
          onPressed: !available || _busy ? null : _invoke,
          icon: _busy
              ? const SizedBox.square(
                  dimension: 18,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.touch_app_outlined),
          label: LText(
              control.label.isEmpty ? control.action.name : control.label),
        ),
        if (!available)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: LText(
              'std.module.custom.catalogUnavailable',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ),
      ]),
    );
  }

  Future<void> _invoke() async {
    final control = widget.control;
    if (control.confirmation == ModuleActionConfirmation.confirm) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const LText('std.module.custom.confirmActionTitle'),
          content: LText(
            'std.module.custom.confirmActionBody',
            args: {
              'action': context.tr(
                  control.label.isEmpty ? control.action.name : control.label),
            },
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const LText('std.common.cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const LText('std.common.confirm'),
            ),
          ],
        ),
      );
      if (confirmed != true || !mounted) return;
    }
    setState(() => _busy = true);
    var accepted = false;
    try {
      accepted = await _performAction(
          context, widget.app, widget.node, widget.control);
    } on Object {
      accepted = false;
    }
    if (!mounted) return;
    setState(() => _busy = false);
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: LText(accepted
          ? 'std.module.custom.actionAccepted'
          : 'std.module.custom.actionRejected'),
    ));
  }
}

class _TextInputControl extends StatefulWidget {
  final AppState app;
  final ModuleNode node;
  final ModuleControlDefinition control;
  final PublishedTagValue? tag;
  const _TextInputControl({
    required this.app,
    required this.node,
    required this.control,
    required this.tag,
  });

  @override
  State<_TextInputControl> createState() => _TextInputControlState();
}

class _TextInputControlState extends State<_TextInputControl> {
  late final TextEditingController _controller;
  late final FocusNode _focusNode;
  bool _dirty = false;
  bool _writing = false;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: '${widget.tag?.value ?? ''}');
    _focusNode = FocusNode();
  }

  @override
  void didUpdateWidget(covariant _TextInputControl oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!_focusNode.hasFocus &&
        !_dirty &&
        oldWidget.tag?.value != widget.tag?.value) {
      _controller.text = '${widget.tag?.value ?? ''}';
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final capability = _capability;
    final rootReady =
        widget.app.rootOf(widget.node.path)?.state == ExecState.ready;
    final available = widget.tag?.usable == true &&
        _enabledByBinding(widget.node, widget.control) &&
        capability != null &&
        capability.hasWriteCapability &&
        (!capability.requiresReady || rootReady);
    return FraktalCard(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Row(children: [
          Expanded(
            child: TouchTextField(
              controller: _controller,
              focusNode: _focusNode,
              enabled: available && !_writing,
              onChanged: (_) => setState(() => _dirty = true),
              decoration: InputDecoration(
                labelText: widget.control.label.isEmpty
                    ? widget.control.primaryBinding
                    : widget.control.label,
                suffixText: widget.control.unit,
                helperText: capability == null
                    ? 'No PLC write capability'
                    : capability.requiresReady && !rootReady
                        ? 'Unit must be READY'
                        : widget.tag?.usable == true
                            ? null
                            : _tagQualityText(widget.tag),
              ),
            ),
          ),
          const SizedBox(width: 10),
          FilledButton(
            onPressed: available && _dirty && !_writing
                ? () => _writeConfig(context)
                : null,
            child: _writing
                ? const SizedBox.square(
                    dimension: 18,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const LText('std.common.apply'),
          ),
        ]),
      ),
    );
  }

  CfgField? get _capability {
    final binding = widget.control.primaryBinding;
    for (final field in widget.node.config) {
      if (field.name == binding) return field;
    }
    return null;
  }

  Future<void> _writeConfig(BuildContext context) async {
    final root = widget.app.rootOf(widget.node.path);
    if (root == null) return;
    if (!widget.app.session.permits(GatedAction.dataWrite)) {
      widget.app.showReleaseReportAction(
          root.path, GatedAction.dataWrite, 'std.release.configBlocked');
      return;
    }
    final field = _capability;
    if (field == null || !field.accepts(_controller.text)) return;
    setState(() => _writing = true);
    var accepted = false;
    try {
      accepted = await widget.app.repo
          .writeConfig(widget.node.path, field, _controller.text);
    } on Object {
      accepted = false;
    }
    if (mounted) {
      setState(() {
        _writing = false;
        if (accepted) _dirty = false;
      });
    }
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: LText(accepted
          ? 'std.module.custom.writeAccepted'
          : 'std.module.custom.writeRejected'),
    ));
  }
}

class _ImageControl extends StatelessWidget {
  final ModuleControlDefinition control;
  const _ImageControl({required this.control});

  @override
  Widget build(BuildContext context) {
    // Decoded once per image and reused: this widget rebuilds on every
    // published snapshot (see embedded_image.dart).
    final image = embeddedImage(control.imageBase64, maxWidth: 1600);
    return FraktalCard(
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (image == null)
          const SizedBox(
            height: 160,
            child: Center(child: Icon(Icons.broken_image_outlined, size: 48)),
          )
        else
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 460),
            child: Center(
                child: Image(
                    image: image, fit: BoxFit.contain, gaplessPlayback: true)),
          ),
        if (control.label.isNotEmpty)
          Padding(
            padding: const EdgeInsets.all(12),
            child: LText(control.label),
          ),
      ]),
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final String unit;
  final IconData icon;
  const _MetricCard({
    required this.label,
    required this.value,
    this.unit = '',
    required this.icon,
  });

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 220,
        child: FraktalCard(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Icon(icon, size: 18),
                const SizedBox(width: 7),
                Expanded(child: LText(label, overflow: TextOverflow.ellipsis)),
              ]),
              const SizedBox(height: 10),
              Text('$value${unit.isEmpty ? '' : ' $unit'}',
                  style: Theme.of(context).textTheme.headlineSmall),
            ]),
          ),
        ),
      );
}

class _StateChip extends StatelessWidget {
  final String label;
  final bool active;
  final bool abnormalWhenTrue;
  final bool abnormalWhenFalse;
  const _StateChip({
    required this.label,
    required this.active,
    this.abnormalWhenTrue = false,
    this.abnormalWhenFalse = false,
  });

  @override
  Widget build(BuildContext context) {
    final abnormal =
        (active && abnormalWhenTrue) || (!active && abnormalWhenFalse);
    final colors = Theme.of(context).colorScheme;
    return Chip(
      avatar: Icon(
        active ? Icons.circle : Icons.circle_outlined,
        size: 15,
        color: abnormal
            ? colors.error
            : (active ? colors.primary : colors.outline),
      ),
      label: LText(label),
      side: abnormal ? BorderSide(color: colors.error) : null,
    );
  }
}

class _ChartSeries {
  String binding;
  int periodMs;
  DateTime? lastSample;
  final List<double> values = [];
  _ChartSeries(this.binding, this.periodMs);

  void reset(String nextBinding, int nextPeriodMs) {
    binding = nextBinding;
    periodMs = nextPeriodMs;
    lastSample = null;
    values.clear();
  }
}

class _TrendPainter extends CustomPainter {
  final List<List<double>> series;
  final List<Color> lineColors;
  final Color gridColor;
  const _TrendPainter(this.series, this.lineColors, this.gridColor);

  @override
  void paint(Canvas canvas, Size size) {
    final grid = Paint()
      ..color = gridColor
      ..strokeWidth = 1;
    for (var row = 0; row <= 4; row++) {
      final y = size.height * row / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), grid);
    }
    final allValues = series.expand((values) => values).toList();
    if (allValues.isEmpty) return;
    var minimum = allValues.reduce(math.min);
    var maximum = allValues.reduce(math.max);
    if ((maximum - minimum).abs() < 0.000001) {
      minimum -= 1;
      maximum += 1;
    }
    for (var seriesIndex = 0; seriesIndex < series.length; seriesIndex++) {
      final values = series[seriesIndex];
      if (values.length < 2) continue;
      final path = Path();
      for (var index = 0; index < values.length; index++) {
        final x = size.width * index / (values.length - 1);
        final y = size.height -
            ((values[index] - minimum) / (maximum - minimum)) * size.height;
        if (index == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      }
      canvas.drawPath(
        path,
        Paint()
          ..color = lineColors[seriesIndex]
          ..strokeWidth = 2
          ..style = PaintingStyle.stroke,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _TrendPainter oldDelegate) {
    if (oldDelegate.series.length != series.length ||
        oldDelegate.lineColors.length != lineColors.length ||
        oldDelegate.gridColor != gridColor) {
      return true;
    }
    for (var index = 0; index < series.length; index++) {
      final previous = oldDelegate.series[index];
      final current = series[index];
      if (previous.length != current.length ||
          (current.isNotEmpty && previous.last != current.last) ||
          oldDelegate.lineColors[index] != lineColors[index]) {
        return true;
      }
    }
    return false;
  }
}

/// A button's or input's bound `enabled` (LOCALIZATION §7.3). An unavailable
/// tag disables: Bad/Uncertain data never enables an input.
bool _enabledByBinding(ModuleNode node, ModuleControlDefinition control) {
  final condition = control.enabledWhen;
  if (condition == null) return true;
  final tag = node.tagAt(condition.binding);
  return tag?.usable == true && condition.matches(tag!.value);
}

String _controlKindKey(ModuleControlKind kind) =>
    'std.module.control.${kind.name}';

String _stateTokenKey(ModuleStateToken token) =>
    'std.module.state.${token.name}';

String _chartSeriesKey(String controlId, String binding) =>
    '$controlId\u0000$binding';

double _responsiveControlWidth(double available, ModuleControlWidth width) {
  if (available <= 0 || available < 600) return available;
  final fraction = available < 900
      ? switch (width) {
          ModuleControlWidth.quarter ||
          ModuleControlWidth.third ||
          ModuleControlWidth.half =>
            0.5,
          ModuleControlWidth.twoThirds || ModuleControlWidth.full => 1.0,
        }
      : switch (width) {
          ModuleControlWidth.quarter => 0.25,
          ModuleControlWidth.third => 1 / 3,
          ModuleControlWidth.half => 0.5,
          ModuleControlWidth.twoThirds => 2 / 3,
          ModuleControlWidth.full => 1.0,
        };
  return ((available + 10) * fraction - 10)
      .clamp(math.min(240.0, available), available)
      .toDouble();
}

List<Color> _chartLineColors(BuildContext context, int count) {
  final primary = HSLColor.fromColor(Theme.of(context).colorScheme.primary);
  return [
    for (var index = 0; index < count; index++)
      primary
          .withHue((primary.hue + index * 47) % 360)
          .withSaturation(math.max(primary.saturation, 0.55))
          .toColor(),
  ];
}

IconData _controlIcon(ModuleControlKind kind) => switch (kind) {
      ModuleControlKind.text => Icons.notes,
      ModuleControlKind.value => Icons.data_object,
      ModuleControlKind.indicator => Icons.lightbulb_outline,
      ModuleControlKind.chart => Icons.show_chart,
      ModuleControlKind.button => Icons.smart_button_outlined,
      ModuleControlKind.textInput => Icons.input,
      ModuleControlKind.image => Icons.image_outlined,
      ModuleControlKind.shape => Icons.crop_square,
      ModuleControlKind.level => Icons.battery_5_bar,
    };

Object? _firstValue(ModuleNode node, List<String> paths) {
  for (final path in paths) {
    final value = node.valueAt(path);
    if (value != null) return value;
  }
  return null;
}

bool _asBool(Object? value) => switch (value) {
      bool result => result,
      num result => result != 0,
      String result => result.toLowerCase() == 'true' || result == '1',
      _ => false,
    };

int _asInt(Object? value) => value is num ? value.toInt() : 0;

/// How a bound value is shown anywhere a control shows one (tabs, tiles).
String formatControlValue(Object? value) => _formatValue(value);

String _formatValue(Object? value) => switch (value) {
      null => '—',
      double number => _formatNumber(number),
      num number => '$number',
      bool flag => flag ? 'ON' : 'OFF',
      _ => '$value',
    };

String _formatNumber(double value) {
  if (value.abs() >= 1000) return value.toStringAsFixed(0);
  if (value.abs() >= 10) return value.toStringAsFixed(1);
  return value.toStringAsFixed(2);
}

String _tagQualityText(PublishedTagValue? tag) {
  if (tag == null) return 'UNAVAILABLE';
  final status =
      tag.statusCode.toUnsigned(32).toRadixString(16).padLeft(8, '0');
  return '${tag.quality.name.toUpperCase()} · 0x$status';
}

Future<void> _manualCommand(BuildContext context, AppState app, ModuleNode node,
    CommandInfo command) async {
  final root = app.rootOf(node.path);
  if (root == null) return;
  if (!app.permitsLocal(GatedAction.manual)) {
    await app.showReleaseReportManual(root.path, node.path, command.value);
    return;
  }
  final accepted =
      await app.repo.manualCommand(root.path, node.path, command.value);
  if (!accepted) {
    await app.showReleaseReportManual(root.path, node.path, command.value);
  }
}

Future<bool> _performAction(BuildContext context, AppState app, ModuleNode node,
    ModuleControlDefinition control) async {
  final root = app.rootOf(node.path);
  if (root == null) return false;
  var accepted = false;
  switch (control.action) {
    case ModuleActionKind.none:
    case ModuleActionKind.writeConfig:
      return false;
    case ModuleActionKind.manualCommand:
      final cataloged =
          node.commands.any((command) => command.value == control.actionValue);
      if (!cataloged) return false;
      if (!app.permitsLocal(GatedAction.manual)) {
        await app.showReleaseReportManual(
            root.path, node.path, control.actionValue);
        return false;
      }
      accepted = await app.repo
          .manualCommand(root.path, node.path, control.actionValue);
      if (!accepted) {
        await app.showReleaseReportManual(
            root.path, node.path, control.actionValue);
      }
      break;
    case ModuleActionKind.unitStart:
      accepted = await app.repo.start(root.path);
      if (!accepted) await app.showReleaseReportStart(root.path);
      break;
    case ModuleActionKind.unitStop:
      accepted = await app.repo.stop(root.path);
      if (!accepted) {
        await app.showReleaseReportAction(
            root.path, GatedAction.startStop, 'std.release.stopBlocked');
      }
      break;
    case ModuleActionKind.operatorReset:
      if (!app.permitsLocal(GatedAction.alarmReset)) {
        await app.showReleaseReportAction(
            root.path, GatedAction.alarmReset, 'std.release.resetBlocked');
        return false;
      }
      accepted = await app.repo.operatorReset(root.path);
      if (!accepted) {
        await app.showReleaseReportAction(
            root.path, GatedAction.alarmReset, 'std.release.resetBlocked');
      }
      break;
    case ModuleActionKind.decisionAnswer:
      final decision = root.decision;
      if (decision?.pending != true ||
          control.actionValue < 1 ||
          control.actionValue > decision!.options.length) {
        return false;
      }
      accepted =
          await app.repo.setDecisionAnswer(root.path, control.actionValue);
      if (!accepted) {
        await app.showReleaseReportAction(
            root.path, GatedAction.startStop, 'Decision answer blocked');
      }
      break;
  }
  return accepted;
}
