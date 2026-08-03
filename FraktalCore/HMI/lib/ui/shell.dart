/// Responsive app shell: on wide screens the tree is a persistent left panel; on
/// narrow (phone/Android portrait) it becomes a Drawer. Global alarm banner and
/// connection chip are always visible; the plant overview is the landing screen.
library;

import 'package:flutter/material.dart';
import '../domain/types.dart';
import '../state/app_state.dart';
import 'login_dialog.dart';
import 'module_detail.dart';
import 'overview_and_indicators.dart';
import 'tree_menu.dart';
import 'fieldbus_tree.dart';
import 'mode_bar.dart';
import 'release_panel.dart';
import 'global_reset_button.dart';
import 'settings_dialog.dart';
import '../localization/localized_text.dart';

class Shell extends StatelessWidget {
  final AppState app;
  final VoidCallback? onEditUnitSelection;
  final VoidCallback? onEditConnection;
  final VoidCallback? onEditAppearance;
  final VoidCallback? onEditAccess;
  final ValueChanged<String>? onLanguageChanged;
  const Shell({
    super.key,
    required this.app,
    this.onEditUnitSelection,
    this.onEditConnection,
    this.onEditAppearance,
    this.onEditAccess,
    this.onLanguageChanged,
  });

  static const _breakpoint = 900.0;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(builder: (context, box) {
      final wide = box.maxWidth >= _breakpoint;
      final Widget body;
      if (app.showFieldbus) {
        body = FieldbusTree(app: app);
      } else if (app.showOverview) {
        body = PlantOverview(app: app);
      } else {
        body = ModuleDetail(app: app);
      }
      return Scaffold(
        appBar: _appBar(context, wide),
        drawer:
            wide ? null : Drawer(child: SafeArea(child: TreeMenu(app: app))),
        body: Column(children: [
          GlobalAlarmBanner(app: app),
          if (!app.showFieldbus && !app.showOverview) ReleasePanel(app: app),
          Expanded(
            child: app.showFieldbus
                ? body
                : wide
                    ? Row(children: [
                        TreeMenu(app: app),
                        const VerticalDivider(width: 1),
                        Expanded(child: body),
                        if (!app.showOverview) ...[
                          const VerticalDivider(width: 1),
                          ModeBar(app: app),
                        ],
                      ])
                    : (app.showOverview
                        ? body
                        : Row(children: [
                            Expanded(child: body),
                            const VerticalDivider(width: 1),
                            ModeBar(app: app),
                          ])),
          ),
        ]),
      );
    });
  }

  PreferredSizeWidget _appBar(BuildContext context, bool wide) {
    final s = app.session;
    return AppBar(
      title: Row(children: [
        Flexible(
          child: InkWell(
            onTap: app.openOverview,
            child: const LText('Fraktal HMI',
                maxLines: 1, overflow: TextOverflow.ellipsis),
          ),
        ),
      ]),
      actions: [
        ConnectionChip(state: app.link),
        if (wide)
          // +2 px overall (1 px per side). Applied from OUTSIDE the widget:
          // SegmentedButton recomputes its own padding for icon segments and
          // drops `minimumSize` entirely, so neither the theme nor the widget's
          // own style can widen it — a wrapping pad is what actually holds.
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 1),
            child: SegmentedButton<bool>(
              segments: const [
                ButtonSegment(
                    value: false,
                    icon: Icon(Icons.account_tree),
                    label: LText('Modules')),
                ButtonSegment(
                    value: true,
                    icon: Icon(Icons.lan_outlined),
                    label: LText('Fieldbus')),
              ],
              selected: {app.showFieldbus},
              onSelectionChanged: (s) => app.setFieldbusView(s.first),
              showSelectedIcon: false,
            ),
          )
        else
          IconButton(
            tooltip:
                context.tr(app.showFieldbus ? 'Show modules' : 'Show fieldbus'),
            icon: Icon(
                app.showFieldbus ? Icons.account_tree : Icons.lan_outlined),
            onPressed: () => app.setFieldbusView(!app.showFieldbus),
          ),
        const SizedBox(width: 8),
        IconButton(
          tooltip: context.tr('std.nav.overview'),
          icon: const Icon(Icons.dashboard_outlined),
          onPressed: app.openOverview,
        ),
        // One settings entry consolidates theme, language, keyboard, and the
        // admin connection/unit-edit flows (declutters the bar; Core O9).
        IconButton(
          key: const Key('settings'),
          tooltip: context.tr('std.settings.title'),
          icon: const Icon(Icons.settings_outlined),
          onPressed: () => showSettingsDialog(context, app,
              onEditConnection: onEditConnection,
              onEditUnitSelection: onEditUnitSelection,
              onEditAppearance: onEditAppearance,
              onEditAccess: onEditAccess,
              onLanguageChanged: onLanguageChanged),
        ),
        if (s.level == AccessLevel.none && wide)
          TextButton.icon(
              onPressed: () => showLoginDialog(context, app),
              icon: const Icon(Icons.login),
              label: const LText('Login'))
        else if (s.level == AccessLevel.none)
          IconButton(
            tooltip: context.tr('std.login.title'),
            onPressed: () => showLoginDialog(context, app),
            icon: const Icon(Icons.login),
          )
        else if (wide)
          TextButton.icon(
            onPressed: () =>
                app.repo.logout(app.rootOf(app.selectedPath ?? '')?.path ?? ''),
            icon: const Icon(Icons.logout),
            label: LText('${s.user} (${s.level.name})'),
          )
        else
          IconButton(
            tooltip: context.tr('Logout {user} ({level})', {
              'user': s.user,
              'level': context.tr('std.access.${s.level.name}'),
            }),
            onPressed: () =>
                app.repo.logout(app.rootOf(app.selectedPath ?? '')?.path ?? ''),
            icon: const Icon(Icons.logout),
          ),
        // §8.3(b) fault clear — fixed upper-right position, right of login.
        GlobalResetButton(app: app),
        const SizedBox(width: 8),
      ],
    );
  }
}
