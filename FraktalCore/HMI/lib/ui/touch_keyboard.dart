/// The visual on-screen keyboard panel + the [TouchTextField] / [TouchTextFormField]
/// wrappers that route focus into it. See `on_screen_keyboard.dart` for the
/// controller and scope.
library;

import 'package:flutter/material.dart';

import 'on_screen_keyboard.dart';

/// The floating keyboard surface, rendered as a root overlay entry. Adapts its
/// layout to the active field's type (numeric pad vs alpha).
class OnScreenKeyboardPanel extends StatelessWidget {
  final OnScreenKeyboardController controller;
  const OnScreenKeyboardPanel({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    // Rendered as a sibling below the app content (see FraktalHmiApp.builder),
    // so it occupies its own space rather than floating over the active field.
    return FocusScope(
      // Belt and braces with each key's `canRequestFocus: false`: nothing inside
      // the panel may pull focus away from the field being typed into. Losing
      // that focus detaches the field (TouchTextField._focusChanged -> hide()),
      // which is exactly how a key press produced no character and dismissed
      // the keyboard.
      canRequestFocus: false,
      child: SizedBox(
        height: controller.reservedHeight,
        width: double.infinity,
        child: SafeArea(
          top: false,
          child: Material(
            elevation: 12,
            color: ElevationOverlay.applySurfaceTint(
              Theme.of(context).colorScheme.surface,
              Theme.of(context).colorScheme.primary,
              12,
            ),
            child: keyboardTypeIsNumeric(controller.activeType)
                ? _NumericPad(controller: controller)
                : _AlphaPad(controller: controller),
          ),
        ),
      ),
    );
  }
}

/// A single key. Large tap target, feedback on tap.
class _Key extends StatelessWidget {
  final String label;
  final VoidCallback onTap;
  final Widget? icon;
  final bool primary;
  const _Key(this.label, this.onTap, {this.icon, this.primary = false});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    // The whole panel is also wrapped so a tap anywhere on it — the padding
    // between keys, the panel background — cannot move focus either.
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 5),
      child: Ink(
        decoration: BoxDecoration(
          color: primary ? scheme.primary : scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(10),
        ),
        child: InkWell(
          borderRadius: BorderRadius.circular(10),
          // A key must NEVER take focus. InkWell is focusable by default, so a
          // tap moved focus off the text field, which fired the field's
          // focus-lost handler -> controller.hide() -> the active field was
          // detached before insert() could run: the keyboard vanished and not a
          // character arrived.
          canRequestFocus: false,
          onTap: onTap,
          child: Center(
            child: icon ??
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w500,
                    color: primary ? scheme.onPrimary : scheme.onSurface,
                  ),
                ),
          ),
        ),
      ),
    );
  }
}

class _NumericPad extends StatelessWidget {
  final OnScreenKeyboardController controller;
  const _NumericPad({required this.controller});

  @override
  Widget build(BuildContext context) {
    final keys = [
      ['7', '8', '9'],
      ['4', '5', '6'],
      ['1', '2', '3'],
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Column(children: [
          for (final row in keys)
            Expanded(
              child: Row(
                children: [
                  for (final k in row)
                    Expanded(child: _Key(k, () => controller.insert(k))),
                  if (row == keys.first)
                    Expanded(
                      child: _Key('', controller.backspace,
                          icon: const Icon(Icons.backspace_outlined)),
                    )
                  else
                    const Expanded(child: SizedBox.shrink()),
                ],
              ),
            ),
          Expanded(
            child: Row(children: [
              Expanded(
                flex: 2,
                child: _Key('0', () => controller.insert('0')),
              ),
              Expanded(child: _Key('.', () => controller.insert('.'))),
              Expanded(
                child: _Key('', controller.submit,
                    icon: Icon(controller.obscure
                        ? Icons.lock_open_outlined
                        : Icons.check_rounded),
                    primary: true),
              ),
            ]),
          ),
        ]),
      ),
    );
  }
}

class _AlphaPad extends StatefulWidget {
  final OnScreenKeyboardController controller;
  const _AlphaPad({required this.controller});

  @override
  State<_AlphaPad> createState() => _AlphaPadState();
}

class _AlphaPadState extends State<_AlphaPad> {
  bool _shifted = true; // start uppercased (names, labels begin with a capital)
  bool _symbols = false;

  static const _letters = [
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
    ['z', 'x', 'c', 'v', 'b', 'n', 'm'],
  ];
  static const _symbolRows = [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['-', '/', ':', ';', '(', ')', '\$', '&', '@', '"'],
    ['.', ',', '?', '!', "'", '#', '%', '*', '+', '='],
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 10),
      child: Column(children: [
        if (_symbols)
          for (final row in _symbolRows)
            Expanded(child: _row(row.map((c) => c).toList()))
        else
          for (var r = 0; r < _letters.length; r++)
            Expanded(child: _letterRow(_letters[r], r)),
        // bottom action row
        Expanded(
          child: Row(children: [
            Expanded(
              flex: 2,
              child: _Key(
                _symbols ? 'abc' : '123',
                () => setState(() {
                  _symbols = !_symbols;
                  _shifted = false;
                }),
              ),
            ),
            Expanded(
              child: _Key(
                '',
                () => setState(() => _shifted = !_shifted),
                icon: Icon(_shifted
                    ? Icons.arrow_upward
                    : Icons.arrow_upward_outlined),
              ),
            ),
            Expanded(
              flex: 5,
              child: _Key(' ', () => widget.controller.insert(' ')),
            ),
            Expanded(
              child: _Key('', widget.controller.backspace,
                  icon: const Icon(Icons.backspace_outlined)),
            ),
            Expanded(
              child: _Key('', widget.controller.submit,
                  icon: Icon(widget.controller.obscure
                      ? Icons.lock_open_outlined
                      : Icons.check_rounded),
                  primary: true),
            ),
          ]),
        ),
      ]),
    );
  }

  Widget _letterRow(List<String> letters, int rowIndex) {
    final children = <Widget>[];
    if (rowIndex == 2) {
      children.add(Expanded(
        child: _Key('', () => setState(() => _shifted = !_shifted),
            icon: Icon(
                _shifted ? Icons.arrow_upward : Icons.arrow_upward_outlined)),
      ));
    }
    for (final l in letters) {
      final ch = _shifted ? l.toUpperCase() : l;
      children.add(Expanded(
          child: _Key(ch, () {
        widget.controller.insert(ch);
        if (_shifted && !_symbols) setState(() => _shifted = false);
      })));
    }
    if (rowIndex == 2) {
      children.add(Expanded(
        child: _Key('', widget.controller.backspace,
            icon: const Icon(Icons.backspace_outlined)),
      ));
    }
    return Row(children: children);
  }

  Widget _row(List<String> chars) => Row(
        children: [
          for (final c in chars)
            Expanded(child: _Key(c, () => widget.controller.insert(c))),
        ],
      );
}
