/// Commissioning step: who may do what **on this panel**.
///
/// These are HMI-local floors, not PLC policy. Each is ANDed with the access
/// level the PLC publishes per root (§7.7), and the PLC re-checks every request,
/// so a setting here can only ever *tighten*: a panel may require more than the
/// PLC does, never less. That matters because a shared panel on the shop floor
/// often warrants stricter rules than the same PLC allows from an engineering
/// station. `NONE` means "defer entirely to the PLC".
library;

import 'package:flutter/material.dart';

import '../domain/types.dart';
import '../localization/localized_text.dart';

class AccessSetupResult {
  final AccessLevel themeMinLevel;
  final AccessLevel closeAppMinLevel;
  final AccessLevel manualMinLevel;
  final AccessLevel alarmResetMinLevel;
  const AccessSetupResult({
    required this.themeMinLevel,
    required this.closeAppMinLevel,
    required this.manualMinLevel,
    required this.alarmResetMinLevel,
  });
}

class AccessSetupScreen extends StatefulWidget {
  final AccessLevel initialThemeMinLevel;
  final AccessLevel initialCloseAppMinLevel;
  final AccessLevel initialManualMinLevel;
  final AccessLevel initialAlarmResetMinLevel;
  final ValueChanged<AccessSetupResult> onContinue;
  final VoidCallback? onBack;

  const AccessSetupScreen({
    super.key,
    required this.initialThemeMinLevel,
    required this.initialCloseAppMinLevel,
    required this.initialManualMinLevel,
    required this.initialAlarmResetMinLevel,
    required this.onContinue,
    this.onBack,
  });

  @override
  State<AccessSetupScreen> createState() => _AccessSetupScreenState();
}

class _AccessSetupScreenState extends State<AccessSetupScreen> {
  late AccessLevel _theme = widget.initialThemeMinLevel;
  late AccessLevel _close = widget.initialCloseAppMinLevel;
  late AccessLevel _manual = widget.initialManualMinLevel;
  late AccessLevel _reset = widget.initialAlarmResetMinLevel;

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
                      Icon(Icons.admin_panel_settings_outlined,
                          size: 52,
                          color: Theme.of(context).colorScheme.primary),
                      const SizedBox(height: 12),
                      LText('std.access.setupTitle',
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineSmall),
                      const SizedBox(height: 8),
                      const LText('std.access.setupHelp',
                          textAlign: TextAlign.center),
                      const SizedBox(height: 20),

                      // Machine actions first: these are the ones that move
                      // equipment, so they matter most on a shared panel.
                      _group(context, 'std.access.machineActions'),
                      Card(
                        color: Theme.of(context)
                            .colorScheme
                            .surfaceContainerHighest,
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Row(children: [
                            Icon(Icons.info_outline,
                                size: 20,
                                color: Theme.of(context).colorScheme.primary),
                            const SizedBox(width: 10),
                            const Expanded(
                                child: LText('std.access.plcStillDecides')),
                          ]),
                        ),
                      ),
                      const SizedBox(height: 12),
                      _picker(
                        key: const Key('manual-min-level'),
                        label: 'std.access.manualMinLevel',
                        help: 'std.access.manualMinLevelHelp',
                        value: _manual,
                        onChanged: (v) => setState(() => _manual = v),
                      ),
                      const SizedBox(height: 16),
                      _picker(
                        key: const Key('alarm-reset-min-level'),
                        label: 'std.access.alarmResetMinLevel',
                        help: 'std.access.alarmResetMinLevelHelp',
                        value: _reset,
                        onChanged: (v) => setState(() => _reset = v),
                      ),
                      const SizedBox(height: 28),

                      _group(context, 'std.access.panelActions'),
                      _picker(
                        key: const Key('theme-min-level'),
                        label: 'std.appearance.themeMinLevel',
                        help: 'std.access.themeMinLevelHelp',
                        value: _theme,
                        onChanged: (v) => setState(() => _theme = v),
                      ),
                      const SizedBox(height: 16),
                      _picker(
                        key: const Key('close-min-level'),
                        label: 'std.appearance.closeAppMinLevel',
                        help: 'std.access.closeAppMinLevelHelp',
                        value: _close,
                        onChanged: (v) => setState(() => _close = v),
                      ),
                      const SizedBox(height: 24),

                      Row(children: [
                        if (widget.onBack != null)
                          TextButton.icon(
                            onPressed: widget.onBack,
                            icon: const Icon(Icons.arrow_back),
                            label: const LText('std.common.back'),
                          ),
                        const Spacer(),
                        FilledButton.icon(
                          key: const Key('save-access'),
                          onPressed: () => widget.onContinue(AccessSetupResult(
                            themeMinLevel: _theme,
                            closeAppMinLevel: _close,
                            manualMinLevel: _manual,
                            alarmResetMinLevel: _reset,
                          )),
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

  Widget _group(BuildContext context, String key) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: LText(key,
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.w600)),
      );

  Widget _picker({
    required Key key,
    required String label,
    required String help,
    required AccessLevel value,
    required ValueChanged<AccessLevel> onChanged,
  }) =>
      Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          DropdownButtonFormField<AccessLevel>(
            key: key,
            initialValue: value,
            decoration: InputDecoration(
              labelText: context.tr(label),
              border: const OutlineInputBorder(),
            ),
            items: [
              for (final level in AccessLevel.values)
                DropdownMenuItem(
                  value: level,
                  child: LText(level == AccessLevel.none
                      ? context.tr('std.access.noneOrPlc')
                      : context.tr('std.access.${level.name}')),
                ),
            ],
            onChanged: (v) => onChanged(v ?? value),
          ),
          const SizedBox(height: 4),
          LText(help, style: Theme.of(context).textTheme.bodySmall),
        ],
      );
}
