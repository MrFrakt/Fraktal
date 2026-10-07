/// Shared semantic symbols. Device identity comes from the published TypeKey,
/// never an instance name, translation, platform, or current fault state.
library;

import 'dart:math' as math;
import 'package:flutter/material.dart';
import '../content/module_layout.dart';
import '../domain/fieldbus.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';

enum ModuleSymbol {
  unit,
  assembly,
  device,
  cylinder,
  configurableCylinder,
  separator,
  axis,
  robot,
  pressure,
  digitalInput,
  power,
  twoHand,
  clamp,
  camera,
  codeReader,
}

const _moduleSymbols = {
  'std.moduleType.cylinder': ModuleSymbol.cylinder,
  'std.moduleType.configurableCylinder': ModuleSymbol.configurableCylinder,
  'std.moduleType.separator': ModuleSymbol.separator,
  'std.moduleType.axis': ModuleSymbol.axis,
  'std.moduleType.robot': ModuleSymbol.robot,
  'std.moduleType.airPressure': ModuleSymbol.pressure,
  'std.moduleType.digitalInput': ModuleSymbol.digitalInput,
  'std.moduleType.powerGroup': ModuleSymbol.power,
  'std.moduleType.twoHand': ModuleSymbol.twoHand,
  'std.moduleType.clamp': ModuleSymbol.clamp,
  'std.moduleType.visionCamera': ModuleSymbol.camera,
  'std.moduleType.codeReader': ModuleSymbol.codeReader,
};

ModuleSymbol moduleSymbolFor(ModuleNode node) =>
    _moduleSymbols[node.typeKey] ??
    (node.type == ModuleType.controlModule && node.motion != null
        ? ModuleSymbol.axis
        : switch (node.type) {
            ModuleType.unit => ModuleSymbol.unit,
            ModuleType.equipmentModule => ModuleSymbol.assembly,
            _ => ModuleSymbol.device,
          });

class ModuleIcon extends StatelessWidget {
  final ModuleNode node;
  final double? size;
  final Color? color;
  const ModuleIcon({super.key, required this.node, this.size, this.color});

  @override
  Widget build(BuildContext context) {
    final symbol = moduleSymbolFor(node);
    final theme = IconTheme.of(context);
    final resolvedSize = size ?? theme.size ?? 24;
    final custom = const {
      ModuleSymbol.cylinder,
      ModuleSymbol.configurableCylinder,
      ModuleSymbol.separator,
      ModuleSymbol.twoHand,
    }.contains(symbol);
    if (custom) {
      return SizedBox.square(
          dimension: resolvedSize,
          child: CustomPaint(
              painter: DeviceSymbolPainter(
                  symbol,
                  (color ??
                          theme.color ??
                          Theme.of(context).colorScheme.onSurface)
                      .withValues(alpha: theme.opacity ?? 1))));
    }
    return Icon(
        switch (symbol) {
          ModuleSymbol.unit => Icons.factory_outlined,
          ModuleSymbol.assembly => Icons.account_tree_outlined,
          ModuleSymbol.axis => Icons.straighten,
          ModuleSymbol.robot => Icons.precision_manufacturing_outlined,
          ModuleSymbol.pressure => Icons.speed,
          ModuleSymbol.digitalInput => Icons.input,
          ModuleSymbol.power => Icons.electrical_services_outlined,
          ModuleSymbol.clamp => Icons.compress,
          ModuleSymbol.camera => Icons.camera_alt_outlined,
          ModuleSymbol.codeReader => Icons.qr_code_scanner,
          _ => Icons.sensors_outlined,
        },
        size: resolvedSize,
        color: color);
  }
}

/// Small engineering pictograms without raster assets or a new font package.
class DeviceSymbolPainter extends CustomPainter {
  final ModuleSymbol symbol;
  final Color color;
  const DeviceSymbolPainter(this.symbol, this.color);

  @override
  void paint(Canvas canvas, Size size) {
    canvas.save();
    canvas.scale(size.width / 24, size.height / 24);
    final pen = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.7
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    void line(double x, double y, double endX, double endY) =>
        canvas.drawLine(Offset(x, y), Offset(endX, endY), pen);
    switch (symbol) {
      case ModuleSymbol.cylinder:
      case ModuleSymbol.configurableCylinder:
        canvas.drawRect(const Rect.fromLTWH(2, 6, 14, 11), pen);
        line(10, 7, 10, 16);
        line(10, 11.5, 22, 11.5);
        line(22, 8, 22, 15);
        line(5, 17, 5, 20);
        line(13, 17, 13, 20);
        if (symbol == ModuleSymbol.configurableCylinder) {
          line(2, 2, 16, 2);
          canvas.drawCircle(const Offset(6, 2), 1.3, pen);
        }
      case ModuleSymbol.separator:
        line(1, 20, 23, 20);
        canvas.drawRect(const Rect.fromLTWH(2, 14, 5, 4), pen);
        canvas.drawRect(const Rect.fromLTWH(10, 14, 5, 4), pen);
        line(8, 6, 8, 17);
        line(17, 6, 17, 13);
        line(6, 5, 19, 5);
        line(19, 5, 19, 9);
      case ModuleSymbol.twoHand:
        for (final x in [4.0, 16.0]) {
          canvas.drawArc(
              Rect.fromLTWH(x - 2, 12, 8, 6), math.pi, math.pi, false, pen);
          line(x - 2, 18, x + 6, 18);
          line(x + 2, 3, x + 2, 10);
          line(x, 8, x + 2, 10);
          line(x + 4, 8, x + 2, 10);
        }
      default:
        break;
    }
    canvas.restore();
  }

  @override
  bool shouldRepaint(DeviceSymbolPainter old) =>
      old.symbol != symbol || old.color != color;
}

IconData moduleTabIcon(ModuleTabIcon icon) => switch (icon) {
      ModuleTabIcon.widgets => Icons.dashboard_customize_outlined,
      ModuleTabIcon.dashboard => Icons.dashboard_outlined,
      ModuleTabIcon.tune => Icons.tune,
      ModuleTabIcon.monitoring => Icons.monitor_heart_outlined,
      ModuleTabIcon.chart => Icons.show_chart,
      ModuleTabIcon.information => Icons.info_outline,
      ModuleTabIcon.build => Icons.build_outlined,
      ModuleTabIcon.science => Icons.science_outlined,
      ModuleTabIcon.machine => Icons.precision_manufacturing_outlined,
      ModuleTabIcon.camera => Icons.camera_alt_outlined,
      ModuleTabIcon.scanner => Icons.qr_code_scanner,
      ModuleTabIcon.contactless => Icons.contactless_outlined,
      ModuleTabIcon.checklist => Icons.checklist_outlined,
      ModuleTabIcon.guidance => Icons.menu_book_outlined,
      ModuleTabIcon.image => Icons.image_outlined,
      ModuleTabIcon.description => Icons.description_outlined,
      ModuleTabIcon.settings => Icons.settings_outlined,
      ModuleTabIcon.speed => Icons.speed_outlined,
      ModuleTabIcon.electrical => Icons.electrical_services_outlined,
      ModuleTabIcon.events => Icons.notifications_outlined,
    };

IconData channelIcon(ChannelKind kind, ChannelDir direction) => switch (kind) {
      ChannelKind.analog => Icons.multiline_chart,
      _ => direction == ChannelDir.input ? Icons.input : Icons.output,
    };

IconData fieldbusIcon(BusNode node) {
  if (node.children.isNotEmpty) return Icons.lan_outlined;
  final signatures = {for (final c in node.channels) (c.kind, c.dir)};
  if (signatures.length == 1) {
    final (kind, dir) = signatures.single;
    return channelIcon(kind, dir);
  }
  return Icons.settings_ethernet;
}

IconData safetyDeviceIcon(SafetyDeviceKind kind) => switch (kind) {
      SafetyDeviceKind.estop => Icons.emergency_outlined,
      SafetyDeviceKind.guardDoor => Icons.door_sliding_outlined,
      SafetyDeviceKind.lightCurtain => Icons.view_week_outlined,
      SafetyDeviceKind.safetyScanner => Icons.radar,
      SafetyDeviceKind.safetyMat => Icons.grid_on,
      SafetyDeviceKind.enableSwitch => Icons.touch_app_outlined,
      SafetyDeviceKind.safetyValve => Icons.air,
      SafetyDeviceKind.safeDrive => Icons.electric_bolt_outlined,
      SafetyDeviceKind.safetySensor => Icons.sensors_outlined,
      SafetyDeviceKind.twoHandControl => Icons.pan_tool_outlined,
      _ => Icons.health_and_safety_outlined,
    };

IconData powerGroupIcon(PowerGroupKind kind) => switch (kind) {
      PowerGroupKind.control => Icons.electrical_services_outlined,
      PowerGroupKind.valveZone => Icons.air,
      PowerGroupKind.driveGroup => Icons.rotate_right,
      PowerGroupKind.heater => Icons.thermostat_outlined,
      PowerGroupKind.processEnergy => Icons.bolt,
      PowerGroupKind.auxiliary => Icons.power_outlined,
    };
