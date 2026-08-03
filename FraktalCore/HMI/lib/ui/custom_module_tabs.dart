library;

import 'dart:convert';
import 'dart:math' as math;
import 'dart:typed_data';

import 'package:flutter/material.dart';

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
  });

  @override
  State<CustomModuleTabView> createState() => _CustomModuleTabViewState();
}

class _CustomModuleTabViewState extends State<CustomModuleTabView> {
  final Map<String, _ChartSeries> _series = {};

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

  @override
  Widget build(BuildContext context) {
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
    return LayoutBuilder(builder: (context, constraints) {
      final available = math.max(0.0, constraints.maxWidth - 32);
      return SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final control in widget.tab.controls)
              SizedBox(
                width: _responsiveControlWidth(available, control.width),
                child: _renderControl(context, control),
              ),
          ],
        ),
      );
    });
  }

  Widget _editableControl(
      BuildContext context, ModuleControlDefinition control, int index) {
    final rendered = _renderControl(context, control);
    if (!widget.editing) {
      return Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: rendered,
      );
    }
    return Card(
      key: ValueKey('edit-control-${control.id}'),
      shape: RoundedRectangleBorder(
        side: BorderSide(color: Theme.of(context).colorScheme.primary),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(children: [
        Row(children: [
          const SizedBox(width: 8),
          ReorderableDragStartListener(
            index: index,
            child: const Padding(
              padding: EdgeInsets.all(8),
              child: Icon(Icons.drag_indicator),
            ),
          ),
          Icon(_controlIcon(control.kind), size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: LText(
                control.label.isEmpty ? control.kind.name : control.label),
          ),
          IconButton(
            tooltip: context.tr('std.common.moveUp'),
            onPressed:
                index == 0 ? null : () => widget.onMoveControlUp?.call(index),
            icon: const Icon(Icons.arrow_upward),
          ),
          IconButton(
            tooltip: context.tr('std.common.moveDown'),
            onPressed: index == widget.tab.controls.length - 1
                ? null
                : () => widget.onMoveControlDown?.call(index),
            icon: const Icon(Icons.arrow_downward),
          ),
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
      Card(
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
      Card(
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
      const Card(
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
      Card(
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
      Card(
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
  Widget build(BuildContext context) => Card(
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
    return Card(
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

class _UnavailableTagCard extends StatelessWidget {
  final ModuleControlDefinition control;
  final PublishedTagValue? tag;

  const _UnavailableTagCard({required this.control, required this.tag});

  @override
  Widget build(BuildContext context) => Card(
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
    return Card(
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
    final available = _catalogAvailable;
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
        capability != null &&
        capability.hasWriteCapability &&
        (!capability.requiresReady || rootReady);
    return Card(
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
    Uint8List? bytes;
    try {
      if (control.imageBase64.isNotEmpty)
        bytes = base64Decode(control.imageBase64);
    } on FormatException {
      bytes = null;
    }
    return Card(
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        if (bytes == null)
          const SizedBox(
            height: 160,
            child: Center(child: Icon(Icons.broken_image_outlined, size: 48)),
          )
        else
          ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 460),
            child: Center(child: Image.memory(bytes, fit: BoxFit.contain)),
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
        child: Card(
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
