// Drives the HMI from a JSON script and writes what it saw - PNGs and the
// on-screen text - so a person or an agent can look at any state of the
// integrated demo with one command and no display, browser or MCP server.
//
//   FRAKTAL_HMI_SCRIPT=path/to/script.json \
//     flutter test tool/screenshots/script_test.dart
//
// FRAKTAL_HMI_SCRIPT may also hold the JSON itself. Each "describe" step
// prints the screen as text to stdout, between ==== HMI <name> ==== markers.
// See tool/screenshots/README.md for the step vocabulary and an example.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/app_theme.dart';

import 'demo_content.dart';
import 'hmi_driver.dart';

void main() {
  final source = Platform.environment['FRAKTAL_HMI_SCRIPT'] ?? '';
  final script = source.isEmpty
      ? null
      : (jsonDecode(source.trimLeft().startsWith('{')
          ? source
          : File(source).readAsStringSync()) as Map<String, Object?>);

  setUpAll(loadHmiFonts);

  testWidgets('HMI script', (tester) async {
    final boot = Map<String, Object?>.from(script!['boot'] as Map? ?? {});
    final out = Directory(script['out'] as String? ?? 'build/hmi_script');
    final driver = HmiDriver(tester, out,
        pixelRatio: (boot['scale'] as num? ?? 1).toDouble());
    try {
      final size = (boot['size'] as List?)?.cast<num>();
      await driver.boot(
        repository: SimRepository(
          epoch: boot['epoch'] == null
              ? demoEpoch
              : DateTime.parse(boot['epoch'] as String),
          commissioning: boot['commissioning'] as bool? ?? false,
          restoreLost: boot['restoreLost'] as bool? ?? false,
          restoreLostPath: boot['restoreLostPath'] as String? ?? '',
          persistFailed: boot['persistFailed'] as bool? ?? false,
        ),
        theme: boot['theme'] as String? ?? 'processGrey',
        language: boot['language'] as String? ?? 'en',
        size: size == null
            ? const Size(1440, 900)
            : Size(size[0].toDouble(), size[1].toDouble()),
        scale: ControlScale.values
            .byName(boot['controls'] as String? ?? 'compact'),
        floatingKeyboard: boot['keyboard'] as bool? ?? false,
      );
      if (boot['content'] as bool? ?? true) await seedDemoContent(driver);
      final user = boot['user'] as String? ?? 'admin1';
      if (user.isNotEmpty) await driver.login(user);
      var index = 0;
      for (final raw in (script['steps'] as List? ?? const [])) {
        index++;
        await _step(driver, Map<String, Object?>.from(raw as Map), index);
      }
    } finally {
      await driver.dispose();
    }
  }, skip: script == null); // set FRAKTAL_HMI_SCRIPT to a script or a file
}

Future<void> _step(HmiDriver d, Map<String, Object?> step, int index) async {
  String text(String key) => step[key] as String;
  Map<String, Object?> args(String key) =>
      Map<String, Object?>.from(step[key] as Map);
  final verb = step.keys.first;
  switch (verb) {
    case 'advance':
      await d.advance(
          Duration(milliseconds: ((step[verb] as num) * 1000).round()));
    case 'until':
      final a = args('until');
      final path = a['path'] as String? ?? 'StationA';
      final within = Duration(seconds: (step['within'] as num? ?? 200).round());
      bool Function() condition;
      if (a.containsKey('step')) {
        condition = () => d.node(path).step?.stepNo == a['step'];
      } else if (a.containsKey('fault')) {
        condition = () => d.node(path).faultActive == a['fault'];
      } else if (a.containsKey('decision')) {
        condition = () => (d.node(path).decision != null) == a['decision'];
      } else if (a.containsKey('blocking')) {
        condition = () => d.node(path).blocking == a['blocking'];
      } else if (a.containsKey('running')) {
        condition = () => d.node(path).running == a['running'];
      } else if (a.containsKey('event')) {
        condition = () => d.node(path).activeEvents.isNotEmpty == a['event'];
      } else {
        throw ArgumentError('step $index: until needs step|fault|decision|'
            'blocking|running|event');
      }
      await d.until('step $index $a', condition, within: within);
    case 'open':
      await d.open(text('open'), tab: step['tab'] as String?);
    case 'overview':
      await d.overview();
    case 'fieldbus':
      await d.fieldbus();
    case 'login':
      await d.login(text('login'), roots: (step['roots'] as List?)?.cast());
    case 'logout':
      for (final root in d.app.forest) {
        await d.sim.logout(root.path);
      }
      await d.settle();
    case 'mode':
      final a = args('mode');
      _accepted(
          await d.sim.setMode(
              a['path'] as String, UnitMode.values.byName(a['mode'] as String)),
          step);
    case 'model':
      final a = args('model');
      _accepted(await d.sim.setModel(a['path'] as String, a['model'] as String),
          step);
    case 'start':
      _accepted(await d.sim.start(text('start')), step);
    case 'stop':
      _accepted(await d.sim.stop(text('stop')), step);
    case 'reset':
      _accepted(await d.sim.operatorReset(text('reset')), step);
    case 'controlOn':
      _accepted(await d.sim.controlOn(text('controlOn')), step);
    case 'controlOff':
      _accepted(await d.sim.controlOff(text('controlOff')), step);
    case 'command':
      final a = args('command');
      final path = a['path'] as String;
      _accepted(
          await d.sim.manualCommand(
              d.app.rootOf(path)!.path, path, (a['value'] as num).toInt()),
          step);
    case 'answer':
      final a = args('answer');
      _accepted(
          await d.sim.setDecisionAnswer(
              a['path'] as String? ?? 'StationA', (a['option'] as num).toInt()),
          step);
    case 'force':
      final a = args('force');
      final channel = a['channel'] as String;
      final value = a['value'];
      _accepted(
          await d.sim.forceChannel(
              d.app.rootOf(channel)?.path ?? 'StationA', channel,
              force: a['release'] != true,
              boolValue: value == true,
              analogValue: value is num ? value.toDouble() : 0),
          step);
    case 'why':
      await d.app.showReleaseReportStart(text('why'));
      await d.settle();
    case 'tap':
      final a = args('tap');
      if (a['key'] != null) {
        await d.tapKey(a['key'] as String);
      } else if (a['text'] != null) {
        await d.tapText(a['text'] as String);
      } else if (a['tooltip'] != null) {
        await d.tapTooltip(a['tooltip'] as String);
      } else {
        throw ArgumentError('step $index: tap needs key|text|tooltip');
      }
    case 'enterText':
      await d.enterText(text('enterText'),
          index: (step['field'] as num? ?? 0).toInt());
    case 'scrollTo':
      final a = args('scrollTo');
      await d.scrollTo(a['key'] != null
          ? find.byKey(ValueKey(a['key'] as String))
          : find.textContaining(a['text'] as String));
    case 'expand':
      d.app.toggleExpand(text('expand'));
      await d.settle();
    case 'theme':
      await d.setTheme(text('theme'));
    case 'language':
      await d.setLanguage(text('language'));
    case 'dismiss':
      await d.dismiss();
    case 'capture':
      final capture = await d.capture(text('capture'));
      // ignore: avoid_print
      print('HMI capture ${capture.png.absolute.path}');
    case 'describe':
      // ignore: avoid_print
      print('==== HMI ${text('describe')} ====\n${d.describe()}'
          '==== /HMI ${text('describe')} ====');
    default:
      throw ArgumentError('step $index: unknown step "$verb"');
  }
}

void _accepted(bool ok, Map<String, Object?> step) {
  if (!ok) throw StateError('the PLC refused $step');
}
