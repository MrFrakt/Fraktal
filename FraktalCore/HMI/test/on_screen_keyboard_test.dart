// The on-screen keyboard must never take focus away from the field it feeds.
//
// Regression: every key was a plain `InkWell`, which is focusable by default.
// On a real touch panel (and in a browser) tapping a key moved focus off the
// text field, which fired `TouchTextField._focusChanged` -> `controller.hide()`
// -> the active field was detached before `insert()` could run. The operator saw
// the keyboard vanish on the first key press with nothing typed.
//
// The guard is structural — no key may be able to request focus — because the
// symptom depends on real focus traversal that a synthesized `tester.tap` does
// not fully reproduce.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:fraktal_hmi/ui/on_screen_keyboard.dart';
import 'package:fraktal_hmi/ui/touch_keyboard.dart';
import 'package:fraktal_hmi/ui/touch_text_field.dart';

Future<OnScreenKeyboardController> _mount(
  WidgetTester tester,
  TextEditingController controller, {
  TextInputType? type,
}) async {
  final keyboard = OnScreenKeyboardController();
  await tester.pumpWidget(MaterialApp(
    home: KeyboardScope(
      controller: keyboard,
      child: Scaffold(
        body: Column(children: [
          TouchTextField(controller: controller, keyboardType: type),
          AnimatedBuilder(
            animation: keyboard,
            builder: (_, __) => OnScreenKeyboardPanel(controller: keyboard),
          ),
        ]),
      ),
    ),
  ));
  await tester.pump();
  await tester.tap(find.byType(TextField));
  await tester.pumpAndSettle();
  return keyboard;
}

void main() {
  testWidgets('no key can request focus (alpha pad)', (tester) async {
    final controller = TextEditingController();
    addTearDown(controller.dispose);
    await _mount(tester, controller);

    final keys = tester.widgetList<InkWell>(find.descendant(
        of: find.byType(OnScreenKeyboardPanel), matching: find.byType(InkWell)));
    expect(keys, isNotEmpty, reason: 'the panel rendered no keys');
    expect(keys.where((k) => k.canRequestFocus), isEmpty,
        reason: 'a focusable key steals focus from the field and dismisses '
            'the keyboard before the character is inserted');
  });

  testWidgets('no key can request focus (numeric pad)', (tester) async {
    final controller = TextEditingController();
    addTearDown(controller.dispose);
    await _mount(tester, controller, type: TextInputType.number);

    final keys = tester.widgetList<InkWell>(find.descendant(
        of: find.byType(OnScreenKeyboardPanel), matching: find.byType(InkWell)));
    expect(keys, isNotEmpty);
    expect(keys.where((k) => k.canRequestFocus), isEmpty);
  });

  testWidgets('a key press types into the field and keeps it focused',
      (tester) async {
    final controller = TextEditingController();
    addTearDown(controller.dispose);
    final keyboard = await _mount(tester, controller);

    await tester.tap(find.text('Q').first);
    await tester.pumpAndSettle();
    expect(controller.text, 'Q');
    // The field must still be attached: the NEXT key press has to land too.
    expect(keyboard.hasField, isTrue,
        reason: 'the keyboard detached after one key — the field lost focus');

    await tester.tap(find.text('w').first); // shift auto-releases after one
    await tester.pumpAndSettle();
    expect(controller.text, 'Qw', reason: 'the second key press was lost');
  });

  testWidgets('backspace edits at the cursor without dismissing', (tester) async {
    final controller = TextEditingController();
    addTearDown(controller.dispose);
    final keyboard = await _mount(tester, controller, type: TextInputType.number);

    for (final digit in ['1', '2', '3']) {
      await tester.tap(find.text(digit).first);
      await tester.pumpAndSettle();
    }
    expect(controller.text, '123');
    await tester.tap(find.byIcon(Icons.backspace_outlined).first);
    await tester.pumpAndSettle();
    expect(controller.text, '12');
    expect(keyboard.hasField, isTrue);
  });
}
