/// In-app floating on-screen keyboard for touch panels (no package; Core O9
/// minimum-surface). A [TouchTextField] registers with the [OnScreenKeyboardController]
/// when it gains focus; the controller raises a root [Overlay] entry rendering the
/// keyboard. The layout adapts to the field's [TextInputType] — a numeric pad for
/// number fields, a compact alpha layout otherwise.
///
/// When the keyboard is disabled (HMI config) the fields behave as ordinary
/// editable fields and the platform soft keyboard is used, so a desktop with a
/// physical keyboard is never obstructed.
library;

import 'package:flutter/material.dart';

import 'app_theme.dart' show ControlScale, UiMetrics;

/// The active field the keyboard is feeding. Held by the controller so key taps
/// mutate the right [TextEditingController] at its cursor.
class _ActiveField {
  final TextEditingController controller;
  final TextInputType keyboardType;
  final bool obscure;
  final VoidCallback? onSubmit;
  _ActiveField(this.controller, this.keyboardType, this.obscure, this.onSubmit);
}

/// Owns keyboard visibility and dispatches key presses to the focused field.
/// AppState holds one instance; [KeyboardScope] exposes it down the tree.
class OnScreenKeyboardController extends ChangeNotifier {
  bool enabled = true;
  _ActiveField? _field;

  bool get hasField => _field != null;
  TextInputType? get activeType => _field?.keyboardType;
  bool get obscure => _field?.obscure ?? false;

  /// Height the visible keyboard occupies at the bottom of the screen. The app
  /// reserves exactly this much, so the keyboard can never cover the field (or
  /// that field's submit button) it is feeding. 0 when hidden.
  ///
  /// Set from the active [UiMetrics] so the keys grow with the size preset —
  /// a keyboard is the densest cluster of tap targets in the whole HMI.
  double numericHeight =
      UiMetrics.of(ControlScale.compact).keyboardNumericHeight;
  double alphaHeight = UiMetrics.of(ControlScale.compact).keyboardAlphaHeight;

  double get reservedHeight => _field == null
      ? 0
      : (keyboardTypeIsNumeric(activeType) ? numericHeight : alphaHeight);

  /// Called when the operator changes the control-size preset.
  void applyMetrics(UiMetrics metrics) {
    if (numericHeight == metrics.keyboardNumericHeight &&
        alphaHeight == metrics.keyboardAlphaHeight) {
      return;
    }
    numericHeight = metrics.keyboardNumericHeight;
    alphaHeight = metrics.keyboardAlphaHeight;
    notifyListeners();
  }

  void setEnabled(bool value) {
    if (enabled == value) return;
    enabled = value;
    if (!value) hide();
    notifyListeners();
  }

  /// A [TouchTextField] that gained focus registers here. The panel is rendered
  /// by the app as a SIBLING of the content (not an overlay inside it), so the
  /// reserved space genuinely removes it from the content's area — an overlay
  /// would still float over the field and its submit button.
  void attach(
    TextEditingController controller,
    TextInputType keyboardType, {
    bool obscure = false,
    VoidCallback? onSubmit,
  }) {
    if (!enabled) return;
    _field = _ActiveField(controller, keyboardType, obscure, onSubmit);
    notifyListeners();
  }

  /// The focused field lost focus, or the keyboard was dismissed.
  void hide() {
    if (_field == null) return;
    _field = null;
    notifyListeners();
  }

  void _replace(String text, TextSelection selection) {
    final field = _field;
    if (field == null) return;
    field.controller.value = TextEditingValue(
      text: text,
      selection: selection,
      composing: TextRange.empty,
    );
  }

  /// Insert [text] at the cursor, replacing any selection.
  void insert(String text) {
    final field = _field;
    if (field == null) return;
    final c = field.controller;
    final sel = c.selection.isValid
        ? c.selection
        : TextSelection.collapsed(offset: c.text.length);
    final start = sel.start.clamp(0, c.text.length);
    final end = sel.end.clamp(0, c.text.length);
    final out = c.text.replaceRange(start, end, text);
    _replace(out, TextSelection.collapsed(offset: start + text.length));
  }

  /// Delete the selection or the character before the cursor.
  void backspace() {
    final field = _field;
    if (field == null) return;
    final c = field.controller;
    final sel = c.selection.isValid
        ? c.selection
        : TextSelection.collapsed(offset: c.text.length);
    if (sel.isCollapsed) {
      final pos = sel.baseOffset.clamp(0, c.text.length);
      if (pos == 0) return;
      _replace(
        c.text.substring(0, pos - 1) + c.text.substring(pos),
        TextSelection.collapsed(offset: pos - 1),
      );
    } else {
      _replace(
        c.text.substring(0, sel.start) + c.text.substring(sel.end),
        TextSelection.collapsed(offset: sel.start),
      );
    }
  }

  void submit() => _field?.onSubmit?.call();
}

/// [InheritedWidget] exposing the controller. Provided near the app root.
class KeyboardScope extends InheritedWidget {
  final OnScreenKeyboardController controller;
  const KeyboardScope({
    super.key,
    required this.controller,
    required super.child,
  });

  static OnScreenKeyboardController of(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<KeyboardScope>()!.controller;

  @override
  bool updateShouldNotify(KeyboardScope oldWidget) =>
      controller != oldWidget.controller;
}

/// Whether a [TextInputType] asks for numeric entry (drives the pad layout).
bool keyboardTypeIsNumeric(TextInputType? t) {
  if (t == null) return false;
  // Compare to the named numeric instances — `number` is a static const here,
  // not an instance getter, so we test equality rather than a boolean flag.
  return t == TextInputType.number ||
      t == const TextInputType.numberWithOptions(decimal: true) ||
      t == TextInputType.phone;
}
