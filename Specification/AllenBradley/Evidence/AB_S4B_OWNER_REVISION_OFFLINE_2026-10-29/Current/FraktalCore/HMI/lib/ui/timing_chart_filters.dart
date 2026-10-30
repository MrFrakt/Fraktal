/// Presentation filters for timing charts. PLC samples and aggregates remain
/// authoritative; filtering only changes which rows/series are drawn.
library;

import 'package:flutter/material.dart';
import 'theme_surfaces.dart' show kInlineItemGap;
import 'app_theme.dart'
    show ControlScaleScope, PresetChip, kFilterChipAnimationStyle;

import '../domain/types.dart';
import '../localization/localized_text.dart';

// Fixed categorical assignment, shared by every timing chart and its legend.
Color timeClassColor(TimeClass c) => switch (c) {
      TimeClass.work => const Color(0xFF2E7D32),
      TimeClass.waitUpstream => const Color(0xFF1565C0),
      TimeClass.waitDownstream => const Color(0xFFAD1457),
      TimeClass.waitOperator => const Color(0xFFB26A00),
      TimeClass.waitExternal => const Color(0xFF0097A7),
    };

String timeClassLabel(TimeClass c) => switch (c) {
      TimeClass.work => 'Work',
      TimeClass.waitUpstream => 'Wait ↑ (starved)',
      TimeClass.waitDownstream => 'Wait ↓ (blocked)',
      TimeClass.waitOperator => 'Wait operator',
      TimeClass.waitExternal => 'Wait external',
    };

class TimingChartOption<T> {
  final T id;
  final String label;
  final Color color;
  final String? detail;
  const TimingChartOption(this.id, this.label, this.color, {this.detail});
}

/// Owns selection, pruning disappeared choices, and the legend's accessible
/// on/off encoding once for Gantt, trend and Pareto.
class TimingChartFilters<T> extends StatefulWidget {
  final List<TimingChartOption<T>> options;
  final Set<T>? hiddenOptions;
  final Widget Function(BuildContext, Set<T>, Widget) builder;
  const TimingChartFilters(
      {super.key, required this.options, required this.builder,
      this.hiddenOptions});

  @override
  State<TimingChartFilters<T>> createState() => _TimingChartFiltersState<T>();
}

class _TimingChartFiltersState<T> extends State<TimingChartFilters<T>> {
  final Set<T> _localHidden = {};
  Set<T> get _hidden => widget.hiddenOptions ?? _localHidden;

  @override
  void didUpdateWidget(TimingChartFilters<T> oldWidget) {
    super.didUpdateWidget(oldWidget);
    final present = widget.options.map((o) => o.id).toSet();
    _hidden.removeWhere((id) => !present.contains(id));
  }

  @override
  Widget build(BuildContext context) => widget.builder(
        context,
        Set<T>.unmodifiable(_hidden),
        Wrap(
          spacing: kInlineItemGap,
          runSpacing: kInlineItemGap,
          children: [
          for (final option in widget.options) _chip(context, option),
          if (_hidden.isNotEmpty)
            PresetChip(
              child: ActionChip(
                chipAnimationStyle: kFilterChipAnimationStyle,
                onPressed: () => setState(_hidden.clear),
                label: LText(
                  'Show all',
                  style: Theme.of(context).textTheme.labelMedium,
                ),
              ),
            ),
        ]),
      );

  Widget _chip(BuildContext context, TimingChartOption<T> option) {
    final shown = !_hidden.contains(option.id);
    final theme = Theme.of(context);
    final markerSize = 12 * ControlScaleScope.of(context).toggleScale;
    return PresetChip(
      child: FilterChip(
        chipAnimationStyle: kFilterChipAnimationStyle,
        selected: shown,
        onSelected: (_) => setState(() {
          if (shown) {
            _hidden.add(option.id);
          } else {
            _hidden.remove(option.id);
          }
        }),
        tooltip: context.tr(
          shown ? 'Filter out of the chart' : 'Add to the chart',
        ),
        label: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: markerSize,
              height: markerSize,
              decoration: BoxDecoration(
                color: shown ? option.color : Colors.transparent,
                border: Border.all(color: option.color, width: 2),
                borderRadius: BorderRadius.circular(3),
              ),
            ),
            const SizedBox(width: 6),
            LText(
              option.label,
              style: theme.textTheme.labelMedium?.copyWith(
                decoration: shown ? null : TextDecoration.lineThrough,
              ),
            ),
            if (option.detail != null) ...[
              const SizedBox(width: 6),
              LText(
                option.detail!,
                style: theme.textTheme.labelSmall?.copyWith(
                  fontFeatures: const [FontFeature.tabularFigures()],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
