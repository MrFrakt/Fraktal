/// [TextField] / [TextFormField] wrappers that route focus into the in-app
/// on-screen keyboard when it is enabled (touch panels). When disabled they are
/// ordinary editable fields, so a desktop with a physical keyboard is unaffected.
///
/// A wrapper is `readOnly` + `showCursor` while the keyboard is enabled, which
/// keeps the OS soft keyboard from appearing and lets the operator tap to place
/// the cursor; key presses from the keyboard mutate the controller at the cursor.
library;

import 'package:flutter/material.dart';

import 'on_screen_keyboard.dart';

/// Looks up the keyboard controller, if any is in scope (null in tests/contexts
/// that don't mount the scope — the field then behaves as a plain TextField).
OnScreenKeyboardController? _keyboardOf(BuildContext context) {
  return context
      .dependOnInheritedWidgetOfExactType<KeyboardScope>()
      ?.controller;
}

/// A drop-in [TextField] that drives the on-screen keyboard.
class TouchTextField extends StatefulWidget {
  final TextEditingController? controller;
  final FocusNode? focusNode;
  final InputDecoration? decoration;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final bool obscureText;
  final bool autofocus;
  final bool enabled;
  final int? maxLines;
  final int? maxLength;
  final ValueChanged<String>? onSubmitted;
  final ValueChanged<String>? onChanged;
  final Iterable<String>? autofillHints;
  final String? initialValue;

  const TouchTextField({
    super.key,
    this.controller,
    this.focusNode,
    this.decoration,
    this.keyboardType,
    this.textInputAction,
    this.obscureText = false,
    this.autofocus = false,
    this.enabled = true,
    this.maxLines,
    this.maxLength,
    this.onSubmitted,
    this.onChanged,
    this.autofillHints,
    this.initialValue,
  });

  @override
  State<TouchTextField> createState() => _TouchTextFieldState();
}

class _TouchTextFieldState extends State<TouchTextField> {
  late final TextEditingController _owned;
  TextEditingController get _effective => widget.controller ?? _owned;
  FocusNode? _ownedFocus;
  FocusNode get _focus => widget.focusNode ?? (_ownedFocus ??= FocusNode());

  @override
  void initState() {
    super.initState();
    _owned = TextEditingController(text: widget.initialValue);
    _focus.addListener(_focusChanged);
  }

  @override
  void dispose() {
    _focus.removeListener(_focusChanged);
    _owned.dispose();
    _ownedFocus?.dispose();
    super.dispose();
  }

  void _focusChanged() {
    final kb = _keyboardOf(context);
    if (kb == null || !kb.enabled) return;
    if (_focus.hasFocus) {
      kb.attach(
        _effective,
        widget.keyboardType ?? TextInputType.text,
        obscure: widget.obscureText,
        onSubmit: () => widget.onSubmitted?.call(_effective.text),
      );
    } else {
      kb.hide();
    }
  }

  @override
  Widget build(BuildContext context) {
    return TextField(
      controller: _effective,
      focusNode: _focus,
      decoration: widget.decoration,
      keyboardType: widget.keyboardType,
      textInputAction: widget.textInputAction,
      obscureText: widget.obscureText,
      autofocus: widget.autofocus,
      enabled: widget.enabled,
      // Match TextField's own default of 1. Defaulting to null would make every
      // field multiline, which trips the "obscured fields cannot be multiline"
      // assertion on the login PIN.
      maxLines: widget.maxLines ?? 1,
      maxLength: widget.maxLength,
      onSubmitted: widget.onSubmitted,
      onChanged: widget.onChanged,
      autofillHints: widget.autofillHints,
      // Deliberately NOT readOnly. The in-app keyboard writes through the shared
      // controller, so the field stays normally editable and a physical keyboard
      // (or an engineer's USB keyboard on the panel) still works. Desktop Flutter
      // never raises an OS soft keyboard, so there is nothing to suppress here.
      showCursor: true,
    );
  }
}

/// A drop-in [TextFormField] (for [Form] widgets with validators).
class TouchTextFormField extends StatefulWidget {
  final TextEditingController? controller;
  final FocusNode? focusNode;
  final InputDecoration? decoration;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final bool obscureText;
  final bool autofocus;
  final bool enabled;
  final int? minLines;
  final int? maxLines;
  final int? maxLength;
  final FormFieldSetter<String>? onSaved;
  final ValueChanged<String>? onChanged;
  final FormFieldValidator<String>? validator;
  final ValueChanged<String>? onFieldSubmitted;
  final Iterable<String>? autofillHints;
  final String? initialValue;

  const TouchTextFormField({
    super.key,
    this.controller,
    this.focusNode,
    this.decoration,
    this.keyboardType,
    this.textInputAction,
    this.obscureText = false,
    this.autofocus = false,
    this.enabled = true,
    this.minLines,
    this.maxLines,
    this.maxLength,
    this.onSaved,
    this.onChanged,
    this.validator,
    this.onFieldSubmitted,
    this.autofillHints,
    this.initialValue,
  });

  @override
  State<TouchTextFormField> createState() => _TouchTextFormFieldState();
}

class _TouchTextFormFieldState extends State<TouchTextFormField> {
  late final TextEditingController _owned;
  TextEditingController get _effective => widget.controller ?? _owned;
  FocusNode? _ownedFocus;
  FocusNode get _focus => widget.focusNode ?? (_ownedFocus ??= FocusNode());

  @override
  void initState() {
    super.initState();
    _owned = TextEditingController(text: widget.initialValue);
    _focus.addListener(_focusChanged);
  }

  @override
  void dispose() {
    _focus.removeListener(_focusChanged);
    _owned.dispose();
    _ownedFocus?.dispose();
    super.dispose();
  }

  void _focusChanged() {
    final kb = _keyboardOf(context);
    if (kb == null || !kb.enabled) return;
    if (_focus.hasFocus) {
      kb.attach(
        _effective,
        widget.keyboardType ?? TextInputType.text,
        obscure: widget.obscureText,
        onSubmit: () => widget.onFieldSubmitted?.call(_effective.text),
      );
    } else {
      kb.hide();
    }
  }

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      key: widget.key,
      controller: _effective,
      focusNode: _focus,
      decoration: widget.decoration,
      keyboardType: widget.keyboardType,
      textInputAction: widget.textInputAction,
      obscureText: widget.obscureText,
      autofocus: widget.autofocus,
      enabled: widget.enabled,
      minLines: widget.minLines,
      // As above: default to 1 like TextFormField does, but never override an
      // explicit minLines (a multiline control passes both).
      maxLines: widget.maxLines ?? (widget.minLines == null ? 1 : null),
      maxLength: widget.maxLength,
      onSaved: widget.onSaved,
      onChanged: widget.onChanged,
      validator: widget.validator,
      onFieldSubmitted: widget.onFieldSubmitted,
      autofillHints: widget.autofillHints,
      // See TouchTextField: kept normally editable so a physical keyboard works.
      showCursor: true,
    );
  }
}
