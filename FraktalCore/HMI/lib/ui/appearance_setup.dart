/// Commissioning step: how this panel looks, and who may change it.
///
/// Theme and control size are chosen here because they depend on the physical
/// panel (a sunlit cabinet wants high contrast; a high-density screen wants
/// larger targets) and the commissioning engineer is the one standing in front
/// of it. The two access levels are panel policy — the PLC's own §7.7 gates are
/// published per root and are never overridden from here.
library;

import 'package:flutter/material.dart';

import '../localization/localized_text.dart';
import 'app_theme.dart';

class AppearanceSetupResult {
  final int themeIndex;
  final ControlScale controlScale;
  const AppearanceSetupResult({
    required this.themeIndex,
    required this.controlScale,
  });
}

class AppearanceSetupScreen extends StatefulWidget {
  final int initialThemeIndex;
  final ControlScale initialControlScale;
  final ValueChanged<AppearanceSetupResult> onContinue;

  /// Live preview hook: the wizard re-themes itself as the engineer chooses, so
  /// the panel is judged as it will actually look rather than from a swatch.
  final void Function(int themeIndex, ControlScale scale)? onPreview;
  final VoidCallback? onBack;

  const AppearanceSetupScreen({
    super.key,
    required this.initialThemeIndex,
    required this.initialControlScale,
    required this.onContinue,
    this.onPreview,
    this.onBack,
  });

  @override
  State<AppearanceSetupScreen> createState() => _AppearanceSetupScreenState();
}

class _AppearanceSetupScreenState extends State<AppearanceSetupScreen> {
  late int _themeIndex = widget.initialThemeIndex;
  late ControlScale _scale = widget.initialControlScale;

  void _preview() => widget.onPreview?.call(_themeIndex, _scale);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 760),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(24),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Icon(Icons.tune,
                          size: 52,
                          color: Theme.of(context).colorScheme.primary),
                      const SizedBox(height: 12),
                      LText('std.appearance.title',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineSmall),
                      const SizedBox(height: 8),
                      const LText('std.appearance.help',
                          textAlign: TextAlign.center),
                      const SizedBox(height: 24),
                      _label(context, 'std.settings.appearance'),
                      Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: [
                          for (var i = 0; i < kThemes.length; i++)
                            _ThemeSwatch(
                              spec: kThemes[i],
                              selected: i == _themeIndex,
                              onTap: () {
                                setState(() => _themeIndex = i);
                                _preview();
                              },
                            ),
                        ],
                      ),
                      const SizedBox(height: 24),
                      _label(context, 'std.settings.controlSize'),
                      SegmentedButton<ControlScale>(
                        segments: [
                          ButtonSegment(
                              value: ControlScale.compact,
                              icon: const Icon(Icons.density_small),
                              label: LText(
                                  context.tr('std.settings.sizeCompact'))),
                          ButtonSegment(
                              value: ControlScale.medium,
                              icon: const Icon(Icons.density_medium),
                              label:
                                  LText(context.tr('std.settings.sizeMedium'))),
                          ButtonSegment(
                              value: ControlScale.large,
                              icon: const Icon(Icons.density_large),
                              label:
                                  LText(context.tr('std.settings.sizeLarge'))),
                        ],
                        selected: {_scale},
                        showSelectedIcon: false,
                        onSelectionChanged: (sel) {
                          setState(() => _scale = sel.first);
                          _preview();
                        },
                      ),
                      const SizedBox(height: 6),
                      LText('std.settings.sizeHelp',
                          style: Theme.of(context).textTheme.bodySmall),
                      const SizedBox(height: 24),
                      const SizedBox(height: 24),
                      Row(children: [
                        if (widget.onBack != null)
                          TextButton(
                            onPressed: widget.onBack,
                            child: const LText('std.common.back'),
                          ),
                        const Spacer(),
                        FilledButton.icon(
                          key: const Key('save-appearance'),
                          onPressed: () => widget.onContinue(
                            AppearanceSetupResult(
                              themeIndex: _themeIndex,
                              controlScale: _scale,
                            ),
                          ),
                          icon: const Icon(Icons.arrow_forward),
                          label: const LText('std.languages.continue'),
                        ),
                      ]),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _label(BuildContext context, String key) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: LText(key,
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.w600)),
      );
}

class _ThemeSwatch extends StatelessWidget {
  final FraktalThemeSpec spec;
  final bool selected;
  final VoidCallback onTap;
  const _ThemeSwatch(
      {required this.spec, required this.selected, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        width: 92,
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected
              ? scheme.primaryContainer
              : scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
          border: selected ? Border.all(color: scheme.primary, width: 2) : null,
        ),
        child: Column(children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: spec.seed,
              shape: BoxShape.circle,
              border: spec.highContrast
                  ? Border.all(color: scheme.onSurface, width: 2)
                  : null,
            ),
            child: spec.trueBlack
                ? const Icon(Icons.dark_mode, size: 18, color: Colors.white70)
                : null,
          ),
          const SizedBox(height: 6),
          LText(spec.nameKey,
              style: const TextStyle(fontSize: 12),
              textAlign: TextAlign.center),
        ]),
      ),
    );
  }
}
