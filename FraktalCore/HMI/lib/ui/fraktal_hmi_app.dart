library;

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import '../state/app_state.dart';
import '../localization/default_catalogs.dart';
import '../localization/localized_text.dart';
import 'app_theme.dart';
import 'on_screen_keyboard.dart';
import 'panel_window_watcher.dart';
import 'touch_keyboard.dart';
import 'shell.dart';

class FraktalHmiApp extends StatelessWidget {
  final AppState app;
  final VoidCallback? onEditUnitSelection;
  final VoidCallback? onEditConnection;
  final VoidCallback? onEditAppearance;
  final VoidCallback? onEditAccess;
  final ValueChanged<String>? onLanguageChanged;
  const FraktalHmiApp({
    super.key,
    required this.app,
    this.onEditUnitSelection,
    this.onEditConnection,
    this.onEditAppearance,
    this.onEditAccess,
    this.onLanguageChanged,
  });

  @override
  Widget build(BuildContext context) {
    return PanelWindowWatcher(
      platform: app.panel,
      child: KeyboardScope(
        controller: app.keyboard,
        child: LocalizationScope(
          controller: app.localization,
          child: ListenableBuilder(
            listenable: Listenable.merge(
                [app, app.localization, app.content, app.keyboard]),
            builder: (context, _) => MaterialApp(
              title: app.localization.resolve('std.app.title'),
              debugShowCheckedModeBanner: false,
              theme: themeAt(app.themeIndex, app.controlScale),
              scrollBehavior: kTouchScroll,
              // The keyboard is a SIBLING of the app content, not an overlay over
              // it: the content gets the remaining space, so the keyboard can
              // never cover the field it feeds — or that field's submit button.
              // The ControlScaleScope wraps everything (including the keyboard and
              // any dialog route) so a control can size itself from the preset.
              builder: (context, child) => ControlScaleScope(
                metrics: UiMetrics.of(app.controlScale),
                child: Column(
                  children: [
                    Expanded(child: child ?? const SizedBox.shrink()),
                    if (app.keyboard.hasField)
                      OnScreenKeyboardPanel(controller: app.keyboard),
                  ],
                ),
              ),
              locale: app.localization.locale,
              supportedLocales: [
                for (final code in availableLanguages.keys) Locale(code),
              ],
              localizationsDelegates: const [
                GlobalMaterialLocalizations.delegate,
                GlobalWidgetsLocalizations.delegate,
                GlobalCupertinoLocalizations.delegate,
              ],
              home: Shell(
                app: app,
                onEditUnitSelection: onEditUnitSelection,
                onEditConnection: onEditConnection,
                onEditAppearance: onEditAppearance,
                onEditAccess: onEditAccess,
                onLanguageChanged: onLanguageChanged,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
