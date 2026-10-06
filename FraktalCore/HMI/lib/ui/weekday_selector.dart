import 'package:flutter/material.dart';
import '../localization/localized_text.dart';
import 'app_theme.dart';
import 'theme_surfaces.dart';

/// Portable calendar V2, Monday bit 0 through Sunday bit 6.
class WeekdaySelector extends StatelessWidget {
  final int mask;
  final bool enabled;
  final ValueChanged<int> onChanged;
  final String keyPrefix;
  const WeekdaySelector({super.key, required this.mask, required this.enabled,
    required this.onChanged, required this.keyPrefix});

  @override
  Widget build(BuildContext context) {
    const days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'];
    void toggle(int i, bool selected) =>
        onChanged((selected ? mask | (1 << i) : mask & ~(1 << i)) & 127);
    return Wrap(spacing: kInlineItemGap, runSpacing: kInlineItemGap, children: [
      for (var i = 0; i < days.length; i++)
        PresetToggle(child: InkWell(
          onTap: enabled ? () => toggle(i, (mask & (1 << i)) == 0) : null,
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Checkbox(key: ValueKey('$keyPrefix-$i'),
              value: (mask & (1 << i)) != 0,
              onChanged: enabled ? (value) => toggle(i, value == true) : null),
            LText('std.weekday.${days[i]}'),
          ]),
        )),
    ]);
  }
}
