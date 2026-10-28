/// One picker for commissioning and settings, with real material previews.
library;

import 'package:flutter/material.dart';

import '../localization/localized_text.dart';
import 'app_theme.dart';
import 'theme_surfaces.dart';
import 'theme_chrome.dart';

class ThemePicker extends StatelessWidget {
  final int selectedIndex;
  final ValueChanged<int>? onChanged;
  const ThemePicker({super.key, required this.selectedIndex, this.onChanged});

  @override
  Widget build(BuildContext context) {
    final order = kThemeDisplayOrder;
    Widget group(String title, String help, Iterable<int> indices) => Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LText(title, style: Theme.of(context).textTheme.titleSmall),
            LText(help, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 8),
            Wrap(spacing: 10, runSpacing: 10, children: [
              for (final i in indices)
                _ThemePreview(
                  spec: kThemes[i],
                  selected: i == selectedIndex,
                  onTap: onChanged == null ? null : () => onChanged!(i),
                ),
            ]),
          ],
        );
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      group('std.theme.group.standard', 'std.theme.group.standardHelp',
          order.where((i) => kThemes[i].group == ThemeGroup.standard)),
      const SizedBox(height: 16),
      group('std.theme.group.modern', 'std.theme.group.modernHelp',
          order.where((i) => kThemes[i].group == ThemeGroup.modern)),
      const SizedBox(height: 16),
      group('std.theme.group.inspired', 'std.theme.group.inspiredHelp',
          order.where((i) => kThemes[i].group == ThemeGroup.inspired)),
    ]);
  }
}

class _ThemePreview extends StatelessWidget {
  final FraktalThemeSpec spec;
  final bool selected;
  final VoidCallback? onTap;
  const _ThemePreview({required this.spec, required this.selected, this.onTap});

  @override
  Widget build(BuildContext context) {
    final outer = Theme.of(context).colorScheme;
    final theme = spec.toThemeData();
    final cs = theme.colorScheme;
    final fill = selected ? outer.primaryContainer : outer.surfaceContainerLow;
    return Semantics(
      selected: selected,
      button: true,
      enabled: onTap != null,
      label: context.tr(spec.nameKey),
      child: ExcludeSemantics(
        child: SizedBox(
          width: 132,
          child: Material(
            color: fill,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(
                color: selected ? outer.primary : outer.outlineVariant,
                width: selected ? 2 : 1,
              ),
            ),
            clipBehavior: Clip.antiAlias,
            child: InkWell(
              key: ValueKey('theme-${spec.nameKey}'),
              onTap: onTap,
              child: Padding(
                padding: const EdgeInsets.all(8),
                child: Column(children: [
                  IgnorePointer(
                    child: Theme(
                      data: theme,
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(7),
                        child: SizedBox(
                          height: 62,
                          child: ColoredBox(
                            color: cs.surface,
                            child: spec.chrome != null
                                ? Column(children: [
                                    FraktalAccentBand(colors: spec.chrome!.bandColors),
                                    Expanded(child: Row(children: [
                                      SizedBox(width: 25, child: ColoredBox(
                                        color: spec.chrome!.navigation,
                                        child: Align(alignment: Alignment.center,
                                          child: Container(height: 14, color: spec.chrome!.selection)))),
                                      Expanded(child: ColoredBox(color: cs.surfaceContainerLow,
                                        child: Center(child: Container(width: 52, height: 20, color: cs.primary)))),
                                    ])),
                                  ])
                                : FraktalBackdrop(
                              child: FraktalCard(
                                margin: const EdgeInsets.all(9),
                                child: Padding(
                                  padding: const EdgeInsets.all(8),
                                  child: Row(children: [
                                    Container(
                                      width: 20,
                                      decoration: BoxDecoration(
                                        color: cs.primary,
                                        borderRadius: BorderRadius.circular(4),
                                      ),
                                      child: Icon(Icons.palette_outlined,
                                          size: 14, color: cs.onPrimary),
                                    ),
                                    const SizedBox(width: 8),
                                    Expanded(
                                      child: Column(
                                        mainAxisAlignment:
                                            MainAxisAlignment.center,
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Container(
                                              height: 3, color: cs.onSurface),
                                          const SizedBox(height: 5),
                                          FractionallySizedBox(
                                            widthFactor: 0.65,
                                            child: Container(
                                                height: 3, color: cs.outline),
                                          ),
                                        ],
                                      ),
                                    ),
                                  ]),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(height: 7),
                  onContainer(
                    context,
                    fill,
                    Row(children: [
                      if (selected) ...[
                        const Icon(Icons.check_circle, size: 15),
                        const SizedBox(width: 4),
                      ],
                      Expanded(
                        child: LText(spec.nameKey,
                            style: const TextStyle(fontSize: 12),
                            textAlign: TextAlign.center),
                      ),
                    ]),
                  ),
                  if (spec.isa101)
                    Padding(
                      padding: const EdgeInsets.only(top: 3),
                      child: onContainer(
                        context,
                        fill,
                        const LText('std.theme.isa101Badge',
                            style: TextStyle(
                                fontSize: 10, fontWeight: FontWeight.w700)),
                      ),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
