import 'package:flutter/material.dart';

import '../localization/localized_text.dart';
import 'app_theme.dart';

/// A two-way view selector, built from primitives rather than configured.
///
/// This replaced a `SegmentedButton`, and not for taste. That widget's
/// `segmentStyleFor` copies a fixed list of style properties onto each segment
/// and **hard-codes the segment shape**, discarding the one in the style; the
/// same method drops `minimumSize`. So the control could not be sized or
/// shaped from the theme, which on the larger presets left a 76 px-tall
/// lozenge that no amount of theming would square off.
///
/// Everything here is drawn from the scheme's own guaranteed pairs - a
/// selected half is `primary`/`onPrimary`, an unselected one
/// `surface`/`onSurfaceVariant` - so the contrast scan covers it by
/// construction rather than by a special case.
class ViewSwitch<T> extends StatelessWidget {
  final List<ViewSwitchOption<T>> options;
  final T value;
  final ValueChanged<T> onChanged;

  const ViewSwitch({
    super.key,
    required this.options,
    required this.value,
    required this.onChanged,
  }) : assert(options.length >= 2, 'a switch needs something to switch between');

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final m = ControlScaleScope.of(context);
    // Deliberately squarer than Material's default. An industrial selector
    // reads as a piece of equipment, not a lozenge, and a modest radius keeps
    // the same silhouette whether the control is 48 or 76 px tall.
    final radius = BorderRadius.circular(8);
    return Container(
      height: m.touchTarget,
      decoration: BoxDecoration(
        borderRadius: radius,
        border: Border.all(color: scheme.outline),
        color: scheme.surface,
      ),
      clipBehavior: Clip.antiAlias,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        // A Row centres its children, so each half was only as tall as its
        // own icon and label and the selected fill floated inside the border
        // instead of reaching it. The fill IS the selection indicator, so it
        // has to occupy the whole half.
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (var i = 0; i < options.length; i++) ...[
            if (i > 0) VerticalDivider(width: 1, thickness: 1,
                color: scheme.outline, indent: 0, endIndent: 0),
            _Half(
              option: options[i],
              selected: options[i].value == value,
              metrics: m,
              onTap: () => onChanged(options[i].value),
            ),
          ],
        ],
      ),
    );
  }
}

class ViewSwitchOption<T> {
  final T value;
  final IconData icon;

  /// A localization key or literal; [LText] resolves either.
  final String label;

  const ViewSwitchOption(
      {required this.value, required this.icon, required this.label});
}

class _Half<T> extends StatelessWidget {
  final ViewSwitchOption<T> option;
  final bool selected;
  final UiMetrics metrics;
  final VoidCallback onTap;

  const _Half({
    required this.option,
    required this.selected,
    required this.metrics,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    // Scheme pairs, so legibility is the scheme's guarantee and the contrast
    // scan already measures it. Never a bare fill with inherited ink.
    final fill = selected ? scheme.primary : Colors.transparent;
    final ink = selected ? scheme.onPrimary : scheme.onSurfaceVariant;
    return Material(
      color: fill,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.symmetric(horizontal: metrics.touchTarget * 0.32),
          // The half now fills the switch's height, so its content has to be
          // centred in it rather than inheriting the top.
          child: Row(
            mainAxisSize: MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(option.icon, size: metrics.iconSize, color: ink),
              const SizedBox(width: 8),
              LText(
                option.label,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      color: ink,
                      fontWeight:
                          selected ? FontWeight.w600 : FontWeight.w500,
                    ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
