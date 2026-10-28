/// The HMI-side content an administrator authors on a real panel - station
/// tiles, a maintenance view drawn on a machine picture, changeover guidance,
/// a manual - built for the integrated demo through the same content API the
/// layout editor publishes with. Nothing here is a PLC value: it is presentation
/// the panel owns (LOCALIZATION_AND_MODULE_CONTENT §7).
///
/// The machine picture is painted, not shipped: the repository carries no
/// binary asset for it, and every overlay below is placed against the same
/// fractions the painting uses, so the two cannot drift apart.
library;

import 'dart:convert';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:fraktal_hmi/content/module_layout.dart';
import 'package:fraktal_hmi/domain/types.dart';
import 'package:fraktal_hmi/ui/custom_module_tabs.dart'
    show moduleTabCapabilities;

import 'hmi_driver.dart';

const _picture = Size(1200, 700);

/// Where each element sits, as fractions of the picture (the overlay unit).
const _door = Rect.fromLTWH(0.885, 0.16, 0.07, 0.62);
const _clamp = Rect.fromLTWH(0.405, 0.38, 0.17, 0.24);
const _cylA = Rect.fromLTWH(0.315, 0.43, 0.09, 0.07);
const _cylB = Rect.fromLTWH(0.575, 0.43, 0.09, 0.07);
const _camera = Rect.fromLTWH(0.455, 0.06, 0.07, 0.11);
const _robotBase = Rect.fromLTWH(0.74, 0.48, 0.10, 0.14);
const _conveyor = Rect.fromLTWH(0.02, 0.54, 0.30, 0.07);
const _pallet = Rect.fromLTWH(0.10, 0.475, 0.13, 0.065);

Rect _px(Rect f) => Rect.fromLTWH(
    f.left * _picture.width,
    f.top * _picture.height,
    f.width * _picture.width,
    f.height * _picture.height);

/// A schematic of Station A. Run inside `tester.runAsync`.
Future<Uint8List> paintStationPicture() async {
  final recorder = ui.PictureRecorder();
  final canvas = Canvas(recorder, Offset.zero & _picture);
  final ink = Paint()
    ..color = const Color(0xFF5B6773)
    ..style = PaintingStyle.stroke
    ..strokeWidth = 3;
  Paint fill(int argb) => Paint()..color = Color(argb);

  canvas.drawRect(Offset.zero & _picture, fill(0xFFF4F6F8));
  final grid = Paint()
    ..color = const Color(0xFFE3E7EB)
    ..strokeWidth = 1;
  for (var x = 0.0; x < _picture.width; x += 40) {
    canvas.drawLine(Offset(x, 0), Offset(x, _picture.height), grid);
  }
  for (var y = 0.0; y < _picture.height; y += 40) {
    canvas.drawLine(Offset(0, y), Offset(_picture.width, y), grid);
  }

  // Machine base and guard fence.
  final base = _px(const Rect.fromLTWH(0.06, 0.62, 0.88, 0.16));
  canvas.drawRRect(RRect.fromRectAndRadius(base, const Radius.circular(10)),
      fill(0xFFCBD3DB));
  canvas.drawRRect(
      RRect.fromRectAndRadius(base, const Radius.circular(10)), ink);
  final fence = _px(const Rect.fromLTWH(0.36, 0.03, 0.60, 0.80));
  final dashed = Paint()
    ..color = const Color(0xFF9AA6B2)
    ..strokeWidth = 2;
  for (var x = fence.left; x < fence.right; x += 18) {
    canvas.drawLine(Offset(x, fence.top), Offset(x + 9, fence.top), dashed);
  }
  for (var y = fence.top; y < fence.bottom; y += 18) {
    canvas.drawLine(Offset(fence.left, y), Offset(fence.left, y + 9), dashed);
    canvas.drawLine(Offset(fence.right, y), Offset(fence.right, y + 9), dashed);
  }

  // Conveyor with rollers and a pallet.
  final conveyor = _px(_conveyor);
  canvas.drawRect(conveyor, fill(0xFFB8C2CC));
  canvas.drawRect(conveyor, ink);
  for (var x = conveyor.left + 18; x < conveyor.right; x += 36) {
    canvas.drawCircle(Offset(x, conveyor.center.dy), 11, fill(0xFF8E9AA6));
  }
  canvas.drawRect(_px(_pallet), fill(0xFFD9A35A));
  canvas.drawRect(_px(_pallet), ink);

  // Clamp fixture with its two cylinders.
  final clamp = _px(_clamp);
  canvas.drawRRect(RRect.fromRectAndRadius(clamp, const Radius.circular(6)),
      fill(0xFF9FB3C8));
  canvas.drawRRect(
      RRect.fromRectAndRadius(clamp, const Radius.circular(6)), ink);
  canvas.drawRect(
      Rect.fromCenter(
          center: clamp.center,
          width: clamp.width * 0.42,
          height: clamp.height * 0.36),
      fill(0xFFE8EDF2));
  for (final cyl in [_px(_cylA), _px(_cylB)]) {
    canvas.drawRRect(RRect.fromRectAndRadius(cyl, const Radius.circular(8)),
        fill(0xFF7F95AB));
    canvas.drawRRect(
        RRect.fromRectAndRadius(cyl, const Radius.circular(8)), ink);
  }

  // Camera looking down at the fixture.
  final camera = _px(_camera);
  canvas.drawRRect(RRect.fromRectAndRadius(camera, const Radius.circular(6)),
      fill(0xFF44505C));
  final cone = Paint()
    ..color = const Color(0x5539A0E5)
    ..style = PaintingStyle.fill;
  canvas.drawPath(
      Path()
        ..moveTo(camera.center.dx - 10, camera.bottom)
        ..lineTo(clamp.left + 30, clamp.top)
        ..lineTo(clamp.right - 30, clamp.top)
        ..lineTo(camera.center.dx + 10, camera.bottom)
        ..close(),
      cone);

  // SCARA robot: base, two links, gripper over the fixture.
  final robot = _px(_robotBase);
  canvas.drawRRect(RRect.fromRectAndRadius(robot, const Radius.circular(8)),
      fill(0xFFF0A23B));
  canvas.drawRRect(
      RRect.fromRectAndRadius(robot, const Radius.circular(8)), ink);
  final arm = Paint()
    ..color = const Color(0xFFE08A1E)
    ..strokeWidth = 22
    ..strokeCap = StrokeCap.round;
  final shoulder = Offset(robot.center.dx, robot.top - 6);
  final elbow = Offset(robot.center.dx - 40, robot.top - 150);
  final wrist = Offset(clamp.right + 30, clamp.top - 70);
  canvas.drawLine(shoulder, elbow, arm);
  canvas.drawLine(elbow, wrist, arm);
  canvas.drawCircle(elbow, 16, fill(0xFF5B6773));
  canvas.drawLine(
      wrist,
      wrist + const Offset(0, 46),
      Paint()
        ..color = const Color(0xFF5B6773)
        ..strokeWidth = 8);

  // Guard door (right side of the fence).
  canvas.drawRect(_px(_door), fill(0x14000000));

  final image = await recorder
      .endRecording()
      .toImage(_picture.width.toInt(), _picture.height.toInt());
  final data = await image.toByteData(format: ui.ImageByteFormat.png);
  image.dispose();
  return data!.buffer.asUint8List();
}

ModulePlacement _at(Rect f) =>
    ModulePlacement(x: f.left, y: f.top, width: f.width, height: f.height);

ModuleControlDefinition _tag(String id, String text, Rect at) =>
    ModuleControlDefinition(
        id: id,
        kind: ModuleControlKind.text,
        text: text,
        layer: 'I/O tags',
        placement: _at(at));

/// The maintenance view of Station A: the picture with live state on it.
ModuleTabDefinition cellView(String imageBase64) => ModuleTabDefinition(
      id: 'cell-view',
      title: 'Cell view',
      kind: ModuleTabKind.custom,
      declaredClass: ModuleViewClass.maintenance,
      tabIcon: ModuleTabIcon.machine,
      requiredLevel: AccessLevel.operator,
      background: ModuleTabBackground(
          imageBase64: imageBase64, imageName: 'station-a.png'),
      controls: [
        ModuleControlDefinition(
          id: 'door',
          kind: ModuleControlKind.shape,
          label: 'Guard door',
          bindings: const ['OutImm/DoorClosed'],
          shape: ModuleShape.rounded,
          rules: const [
            ModuleStateRule(
                compare: ModuleCompare.isFalse,
                token: ModuleStateToken.error,
                blink: true,
                glyph: ModuleGlyph.lockOpen),
          ],
          defaultToken: ModuleStateToken.ok,
          defaultGlyph: ModuleGlyph.lock,
          placement: _at(_door),
        ),
        ModuleControlDefinition(
          id: 'clamp',
          kind: ModuleControlKind.shape,
          label: 'Clamp',
          bindings: const ['OutImm/ClampClosed'],
          shape: ModuleShape.rounded,
          rules: const [
            ModuleStateRule(
                compare: ModuleCompare.isTrue,
                token: ModuleStateToken.ok,
                glyph: ModuleGlyph.check),
          ],
          defaultToken: ModuleStateToken.neutral,
          placement: _at(_clamp),
        ),
        ModuleControlDefinition(
          id: 'pressure',
          kind: ModuleControlKind.level,
          label: 'Clamp pressure',
          bindings: const ['OutImm/ClampPressureBar'],
          unit: 'bar',
          minimum: 0,
          maximum: 8,
          defaultToken: ModuleStateToken.info,
          placement: _at(const Rect.fromLTWH(0.585, 0.64, 0.04, 0.13)),
        ),
        ModuleControlDefinition(
          id: 'part',
          kind: ModuleControlKind.indicator,
          label: 'Part present',
          binding: 'OutImm/PartPresent',
          placement: _at(const Rect.fromLTWH(0.41, 0.66, 0.14, 0.06)),
        ),
        ModuleControlDefinition(
          id: 'rate',
          kind: ModuleControlKind.value,
          label: 'Parts / hour',
          binding: 'OutImm/PartsPerHour',
          placement: _at(const Rect.fromLTWH(0.03, 0.07, 0.17, 0.08)),
        ),
        ModuleControlDefinition(
          id: 'cycle',
          kind: ModuleControlKind.value,
          label: 'Last cycle',
          binding: 'OutImm/CycleTimeS',
          unit: 's',
          placement: _at(const Rect.fromLTWH(0.03, 0.17, 0.17, 0.08)),
        ),
        ModuleControlDefinition(
          id: 'air',
          kind: ModuleControlKind.value,
          label: 'Supply air',
          binding: 'OutImm/SupplyPressureBar',
          unit: 'bar',
          placement: _at(const Rect.fromLTWH(0.03, 0.27, 0.17, 0.08)),
        ),
        _tag('tag-b41', '=A1+S1-B41',
            const Rect.fromLTWH(0.575, 0.33, 0.1, 0.05)),
        _tag('tag-b31', '=A1+S1-B31',
            const Rect.fromLTWH(0.305, 0.33, 0.1, 0.05)),
        _tag('tag-s01', '=A1+S1-S01',
            const Rect.fromLTWH(0.86, 0.80, 0.1, 0.05)),
        _tag('tag-cam', 'Camera LV-5',
            const Rect.fromLTWH(0.54, 0.08, 0.12, 0.05)),
      ],
    );

/// Changeover guidance: walks the operator through the WAIT_OPERATOR step.
ModuleTabDefinition guidance(String imageBase64) => ModuleTabDefinition(
      id: 'operator-guidance',
      title: 'std.module.tab.guidance',
      kind: ModuleTabKind.guidance,
      requiredLevel: AccessLevel.operator,
      triggerStepName: '*',
      triggerModes: kSetupGuidanceModes,
      controls: [
        const ModuleControlDefinition(
          id: 'g-text',
          kind: ModuleControlKind.text,
          label: 'Swap the gripper fingers',
          text: '1. Open the north guard door - the valve zones drop out.\n'
              '2. Release both quick-change pins and lift the fingers off.\n'
              '3. Fit the finger set marked with the new model code.\n'
              '4. Push both pins home until they click, then close the guard.\n'
              '5. Confirm on the station: "Yes - fingers swapped".',
          width: ModuleControlWidth.half,
        ),
        ModuleControlDefinition(
          id: 'g-image',
          kind: ModuleControlKind.image,
          label: 'Gripper location',
          imageBase64: imageBase64,
          imageName: 'station-a.png',
          width: ModuleControlWidth.half,
        ),
      ],
    );

/// Overview tile slots per station TYPE (LOCALIZATION §7.5): every station of
/// a type shows the same metrics in the same columns.
const tiles = {
  'project.moduleType.clampStation': ModuleTileProfile(metrics: [
    ModuleControlDefinition(
        id: 'm-rate',
        kind: ModuleControlKind.value,
        label: 'Parts / h',
        binding: 'OutImm/PartsPerHour'),
    ModuleControlDefinition(
        id: 'm-cycle',
        kind: ModuleControlKind.value,
        label: 'Cycle',
        binding: 'OutImm/CycleTimeS',
        unit: 's'),
    ModuleControlDefinition(
        id: 'm-clamp',
        kind: ModuleControlKind.value,
        label: 'Clamp',
        binding: 'OutImm/ClampPressureBar',
        unit: 'bar'),
  ], badges: [
    ModuleControlDefinition(
        id: 'b-door',
        kind: ModuleControlKind.shape,
        label: 'Guard',
        bindings: ['OutImm/DoorClosed'],
        rules: [
          ModuleStateRule(
              compare: ModuleCompare.isFalse, token: ModuleStateToken.error)
        ],
        defaultToken: ModuleStateToken.ok),
    ModuleControlDefinition(
        id: 'b-air',
        kind: ModuleControlKind.shape,
        label: 'Air',
        bindings: ['OutImm/AirOk'],
        rules: [
          ModuleStateRule(
              compare: ModuleCompare.isFalse, token: ModuleStateToken.warning)
        ],
        defaultToken: ModuleStateToken.ok),
  ]),
  'project.moduleType.transferConveyor': ModuleTileProfile(metrics: [
    ModuleControlDefinition(
        id: 'm-air',
        kind: ModuleControlKind.value,
        label: 'Air',
        binding: 'OutImm/AirPressureBar',
        unit: 'bar'),
    ModuleControlDefinition(
        id: 'm-speed',
        kind: ModuleControlKind.value,
        label: 'Belt',
        binding: 'OutImm/BeltSpeed',
        unit: 'm/min'),
  ], badges: [
    ModuleControlDefinition(
        id: 'b-pallet',
        kind: ModuleControlKind.shape,
        label: 'Pallet at stop',
        bindings: ['OutImm/PalletAtStop'],
        rules: [
          ModuleStateRule(
              compare: ModuleCompare.isTrue, token: ModuleStateToken.info)
        ],
        defaultToken: ModuleStateToken.off),
  ]),
  'project.moduleType.casePacker': ModuleTileProfile(metrics: [
    ModuleControlDefinition(
        id: 'm-cpm',
        kind: ModuleControlKind.value,
        label: 'Cartons / min',
        binding: 'OutImm/CartonsPerMinute'),
    ModuleControlDefinition(
        id: 'm-glue',
        kind: ModuleControlKind.value,
        label: 'Glue',
        binding: 'OutImm/GlueTemperatureC',
        unit: '°C'),
  ]),
};

/// A one-page PDF, built by hand so nothing binary is checked in.
Uint8List manualPdf(String title) {
  final text = 'BT /F1 28 Tf 72 700 Td ($title) Tj ET\n'
      'BT /F1 14 Tf 72 660 Td (Fraktal integrated demo - operating manual) Tj ET';
  final objects = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] '
        '/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    '<< /Length ${text.length} >>\nstream\n$text\nendstream',
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];
  final out = StringBuffer('%PDF-1.4\n');
  final offsets = <int>[];
  for (var i = 0; i < objects.length; i++) {
    offsets.add(out.length);
    out.write('${i + 1} 0 obj\n${objects[i]}\nendobj\n');
  }
  final xref = out.length;
  out.write('xref\n0 ${objects.length + 1}\n0000000000 65535 f \n');
  for (final offset in offsets) {
    out.write('${offset.toString().padLeft(10, '0')} 00000 n \n');
  }
  out.write('trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\n'
      'startxref\n$xref\n%%EOF\n');
  return Uint8List.fromList(latin1.encode(out.toString()));
}

/// Publishes the demo's authored content into [driver]'s panel, as ADMIN.
Future<void> seedDemoContent(HmiDriver driver) async {
  late Uint8List png;
  await driver.tester.runAsync(() async => png = await paintStationPicture());
  final picture = base64Encode(png);
  for (final entry in tiles.entries) {
    await driver.content.publishTile('type:${entry.key}', entry.value);
  }
  final station = driver.node('StationA');
  final capabilities = moduleTabCapabilities(station);
  final tabs = [
    for (final tab in driver.content
        .tabsFor('StationA', capabilities, typeKey: station.typeKey))
      tab.kind == ModuleTabKind.guidance ? guidance(picture) : tab,
    cellView(picture),
  ];
  await driver.content.publishTabs('StationA', tabs, capabilities,
      author: 'admin1', comment: 'Integrated demo content');
  await driver.content.addPdf(
      modulePath: 'StationA',
      fileName: 'station-a-manual.pdf',
      bytes: manualPdf('Station A - Operating manual'),
      title: 'Station A operating manual',
      uploadedBy: 'admin1');
  await driver.content.addPdf(
      modulePath: 'StationA',
      fileName: 'clamp-maintenance.pdf',
      bytes: manualPdf('Clamp fixture - Maintenance'),
      title: 'Clamp fixture maintenance',
      uploadedBy: 'admin1');
  await driver.settle();
}
