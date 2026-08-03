/// Fullscreen settings dialog (Core O9: one place for HMI-local configuration).
/// Consolidates the twelve-theme picker, the active language, the floating-keyboard
/// toggle, and entries that invoke the existing connection / unit-assignment edit
/// flows (those stay phase transitions in ConnectionBootstrap — not reimplemented).
library;

import 'package:flutter/material.dart';
import '../localization/default_catalogs.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';
import '../domain/types.dart';
import 'app_theme.dart';
import 'access_policy_editor.dart';
import 'language_settings.dart';

Future<void> showSettingsDialog(
  BuildContext context,
  AppState app, {
  VoidCallback? onEditConnection,
  VoidCallback? onEditUnitSelection,
  VoidCallback? onEditAppearance,
  VoidCallback? onEditAccess,
  ValueChanged<String>? onLanguageChanged,
}) {
  return showDialog<void>(
    context: context,
    builder: (context) => _SettingsDialog(
      app: app,
      onEditConnection: onEditConnection,
      onEditUnitSelection: onEditUnitSelection,
      onEditAppearance: onEditAppearance,
      onEditAccess: onEditAccess,
      onLanguageChanged: onLanguageChanged,
    ),
  );
}

class _SettingsDialog extends StatefulWidget {
  final AppState app;
  final VoidCallback? onEditConnection;
  final VoidCallback? onEditUnitSelection;
  final VoidCallback? onEditAppearance;
  final VoidCallback? onEditAccess;
  final ValueChanged<String>? onLanguageChanged;
  const _SettingsDialog({
    required this.app,
    this.onEditConnection,
    this.onEditUnitSelection,
    this.onEditAppearance,
    this.onEditAccess,
    this.onLanguageChanged,
  });

  @override
  State<_SettingsDialog> createState() => _SettingsDialogState();
}

class _SettingsDialogState extends State<_SettingsDialog> {
  late String _language;
  bool _fullscreen = false;

  @override
  void initState() {
    super.initState();
    _language = widget.app.localization.activeLanguage;
    // The browser may already be fullscreen (F11) — reflect reality, not a guess.
    widget.app.panel.isFullscreen().then((value) {
      if (mounted) setState(() => _fullscreen = value);
    });
  }

  /// Quitting hides the machine view, so it is confirmed rather than immediate.
  Future<void> _confirmClose(BuildContext context, AppState app) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const LText('std.settings.closeApp'),
        content: const LText('std.settings.closeAppConfirm'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const LText('std.common.cancel')),
          FilledButton(
            style: FilledButton.styleFrom(
                backgroundColor: Theme.of(ctx).colorScheme.error,
                foregroundColor: Theme.of(ctx).colorScheme.onError),
            onPressed: () => Navigator.pop(ctx, true),
            child: const LText('std.settings.closeApp'),
          ),
        ],
      ),
    );
    if (confirmed == true) await app.closeApp();
  }

  @override
  Widget build(BuildContext context) {
    final app = widget.app;
    final themeOk = app.session.level.index >= app.config.themeMinLevel.index;
    final isAdmin = app.session.level == AccessLevel.admin;
    final root = app.rootOf(app.selectedPath ?? '') ??
        (app.visibleRoots.isEmpty ? null : app.visibleRoots.first);
    final canEditPlcPolicy = root != null &&
        app.permitsLocal(GatedAction.accessPolicy,
            forSession: root.access ?? const AccessSession());
    return Dialog(
      insetPadding: EdgeInsets.zero,
      child: Scaffold(
        appBar: AppBar(
          title: const LText('std.settings.title'),
          leading: IconButton(
            icon: const Icon(Icons.close),
            onPressed: () => Navigator.of(context).maybePop(),
          ),
        ),
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(20),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 760),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _sectionLabel('std.settings.appearance'),
                    _ThemeGrid(app: app, enabled: themeOk),
                    const SizedBox(height: 24),
                    _sectionLabel('std.settings.language'),
                    DropdownButtonFormField<String>(
                      initialValue: _language,
                      decoration: InputDecoration(
                        labelText: context.tr('std.common.language'),
                        border: const OutlineInputBorder(),
                      ),
                      items: [
                        for (final code in app.localization.enabledLanguages)
                          DropdownMenuItem(
                              value: code,
                              child: LText(availableLanguages[code] ?? code)),
                      ],
                      onChanged: (value) {
                        final code = value ?? _language;
                        setState(() => _language = code);
                        app.localization.setActiveLanguage(code);
                        widget.onLanguageChanged?.call(code);
                      },
                    ),
                    const SizedBox(height: 8),
                    Align(
                      alignment: Alignment.centerLeft,
                      child: TextButton.icon(
                        onPressed: isAdmin
                            ? () => showLanguageSettings(
                                context, app.localization,
                                canAdminister: true)
                            : null,
                        icon: const Icon(Icons.translate_outlined),
                        label: const LText('std.languages.settings'),
                      ),
                    ),
                    const SizedBox(height: 16),
                    _sectionLabel('std.settings.touch'),
                    // Control size: bigger targets for high-density panels and
                    // for gloved operation. Same gate as the theme.
                    SegmentedButton<ControlScale>(
                      segments: [
                        ButtonSegment(
                            value: ControlScale.compact,
                            icon: const Icon(Icons.density_small),
                            label:
                                LText(context.tr('std.settings.sizeCompact'))),
                        ButtonSegment(
                            value: ControlScale.medium,
                            icon: const Icon(Icons.density_medium),
                            label:
                                LText(context.tr('std.settings.sizeMedium'))),
                        ButtonSegment(
                            value: ControlScale.large,
                            icon: const Icon(Icons.density_large),
                            label: LText(context.tr('std.settings.sizeLarge'))),
                      ],
                      selected: {app.controlScale},
                      showSelectedIcon: false,
                      onSelectionChanged: themeOk
                          ? (sel) => app.setControlScale(sel.first)
                          : null,
                    ),
                    const SizedBox(height: 6),
                    LText('std.settings.sizeHelp',
                        style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 16),
                    SwitchListTile(
                      value: app.floatingKeyboard,
                      onChanged: app.setFloatingKeyboard,
                      title: const LText('std.settings.floatingKeyboard'),
                      subtitle:
                          const LText('std.settings.floatingKeyboardHelp'),
                    ),
                    const Divider(height: 40),
                    _sectionLabel('std.settings.station'),
                    if (isAdmin && widget.onEditConnection != null)
                      ListTile(
                        key: const Key('edit-connection'),
                        leading: const Icon(Icons.settings_ethernet),
                        title: const LText('std.connection.edit'),
                        subtitle: const LText('std.connection.editHelp'),
                        trailing: const Icon(Icons.chevron_right),
                        // Close first, then hand off. The callback rebuilds the
                        // bootstrap phase (tearing down this app and this dialog's
                        // context), so grab it before popping and invoke it after
                        // the frame the pop is processed in.
                        onTap: () {
                          final edit = widget.onEditConnection!;
                          Navigator.of(context).pop();
                          WidgetsBinding.instance
                              .addPostFrameCallback((_) => edit());
                        },
                      ),
                    if (isAdmin && widget.onEditUnitSelection != null)
                      ListTile(
                        key: const Key('edit-unit-assignment'),
                        leading: const Icon(Icons.factory_outlined),
                        title: const LText('std.settings.editUnitAssignment'),
                        subtitle:
                            const LText('std.settings.editUnitAssignmentHelp'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () {
                          final edit = widget.onEditUnitSelection!;
                          Navigator.of(context).pop();
                          WidgetsBinding.instance
                              .addPostFrameCallback((_) => edit());
                        },
                      ),
                    if (isAdmin && widget.onEditAppearance != null)
                      ListTile(
                        key: const Key('edit-appearance'),
                        leading: const Icon(Icons.tune),
                        title: const LText('std.appearance.title'),
                        subtitle: const LText('std.appearance.editHelp'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () {
                          final edit = widget.onEditAppearance!;
                          Navigator.of(context).pop();
                          WidgetsBinding.instance
                              .addPostFrameCallback((_) => edit());
                        },
                      ),
                    if (isAdmin && widget.onEditAccess != null)
                      ListTile(
                        key: const Key('edit-access'),
                        leading:
                            const Icon(Icons.admin_panel_settings_outlined),
                        title: const LText('std.access.panelSetupTitle'),
                        subtitle: const LText('std.access.panelEditHelp'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () {
                          final edit = widget.onEditAccess!;
                          Navigator.of(context).pop();
                          WidgetsBinding.instance
                              .addPostFrameCallback((_) => edit());
                        },
                      ),
                    if (root != null)
                      ListTile(
                        key: const Key('edit-plc-access-policy'),
                        leading: const Icon(Icons.policy_outlined),
                        title: const LText('std.accessPolicy.title'),
                        subtitle: LText(canEditPlcPolicy
                            ? 'std.accessPolicy.tileHelp'
                            : 'std.accessPolicy.deniedHelp'),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: canEditPlcPolicy
                            ? () =>
                                showAccessPolicyEditor(context, app, root.path)
                            : () => app.showReleaseReportAction(
                                root.path,
                                GatedAction.accessPolicy,
                                'std.accessPolicy.blocked'),
                      ),
                    if (!isAdmin) const LText('std.settings.adminOnly'),
                    // Web only: a browser grants fullscreen solely from a user
                    // gesture, so it needs an explicit control. Native follows
                    // the window state (PanelWindowWatcher) and shows nothing.
                    if (app.panel.needsFullscreenGesture &&
                        app.panel.canToggleFullscreen) ...[
                      const Divider(height: 40),
                      _sectionLabel('std.settings.display'),
                      ListTile(
                        key: const Key('toggle-fullscreen'),
                        leading: Icon(_fullscreen
                            ? Icons.fullscreen_exit
                            : Icons.fullscreen),
                        title: LText(_fullscreen
                            ? 'std.settings.exitFullscreen'
                            : 'std.settings.enterFullscreen'),
                        subtitle: const LText('std.settings.fullscreenHelp'),
                        onTap: () async {
                          final reached =
                              await app.panel.setFullscreen(!_fullscreen);
                          if (mounted) setState(() => _fullscreen = reached);
                        },
                      ),
                    ],
                    if (app.panel.canCloseApp) ...[
                      const Divider(height: 40),
                      _sectionLabel('std.settings.session'),
                      ListTile(
                        key: const Key('close-app'),
                        leading: Icon(Icons.power_settings_new,
                            color: Theme.of(context).colorScheme.error),
                        title: const LText('std.settings.closeApp'),
                        subtitle: LText(app.mayCloseApp
                            ? 'std.settings.closeAppHelp'
                            : 'std.settings.closeAppDenied'),
                        enabled: app.mayCloseApp,
                        onTap: app.mayCloseApp
                            ? () => _confirmClose(context, app)
                            : null,
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _sectionLabel(String key) => Padding(
        padding: const EdgeInsets.only(top: 8, bottom: 10),
        child: LText(key,
            style: Theme.of(context)
                .textTheme
                .titleSmall
                ?.copyWith(fontWeight: FontWeight.w600)),
      );
}

class _ThemeGrid extends StatelessWidget {
  final AppState app;
  final bool enabled;
  const _ThemeGrid({required this.app, required this.enabled});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Opacity(
      opacity: enabled ? 1.0 : 0.5,
      child: AbsorbPointer(
        absorbing: !enabled,
        child: Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (var i = 0; i < kThemes.length; i++)
              _ThemeSwatch(
                spec: kThemes[i],
                selected: i == app.themeIndex,
                onTap: () => app.setTheme(i),
                fallback: scheme,
              ),
          ],
        ),
      ),
    );
  }
}

class _ThemeSwatch extends StatelessWidget {
  final FraktalThemeSpec spec;
  final bool selected;
  final VoidCallback onTap;
  final ColorScheme fallback;
  const _ThemeSwatch(
      {required this.spec,
      required this.selected,
      required this.onTap,
      required this.fallback});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: onTap,
      child: Container(
        width: 92,
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: selected
              ? fallback.primaryContainer
              : fallback.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(12),
          border:
              selected ? Border.all(color: fallback.primary, width: 2) : null,
        ),
        child: Column(children: [
          Container(
            width: 34,
            height: 34,
            decoration: BoxDecoration(
              color: spec.seed,
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                    color: spec.brightness == Brightness.dark
                        ? Colors.black54
                        : Colors.black26,
                    blurRadius: 3,
                    offset: const Offset(0, 1)),
              ],
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
