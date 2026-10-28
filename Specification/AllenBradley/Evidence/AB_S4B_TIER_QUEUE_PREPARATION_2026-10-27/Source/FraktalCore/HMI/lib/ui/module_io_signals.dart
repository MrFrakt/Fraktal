/// Read-only physical I/O assigned to one module by the published catalog.
library;

import 'package:flutter/material.dart';
import '../domain/fieldbus.dart';
import '../localization/localized_text.dart';
import 'io_signal_led.dart';
import 'theme_chrome.dart';

class ModuleIoSignals extends StatelessWidget {
  final String modulePath;
  final List<BusNode> fieldbus;
  final bool available, expected;
  const ModuleIoSignals(
      {super.key,
      required this.modulePath,
      required this.fieldbus,
      this.available = true,
      this.expected = false});
  @override
  Widget build(BuildContext context) {
    final signals = <({IoChannel channel, bool usable})>[];
    void visit(BusNode bus, bool parentUsable) {
      final usable = parentUsable &&
          bus.mappingValid &&
          bus.linkOk &&
          bus.state == NodeState.operational;
      for (final channel in bus.channels) {
        if (channel.modulePath == modulePath) {
          signals.add((
            channel: channel,
            usable: usable &&
                channel.quality &&
                (channel.kind == ChannelKind.digital ||
                    channel.analogValue.isFinite)
          ));
        }
      }
      for (final child in bus.children) {
        visit(child, usable);
      }
    }

    for (final bus in fieldbus) {
      visit(bus, available);
    }
    if (fieldbus.any((bus) => !bus.mappingValid)) {
      return LText('std.error.fieldbusMappingInvalid',
          style: TextStyle(color: Theme.of(context).colorScheme.error));
    }
    if (signals.isEmpty) {
      return LText(!available
          ? 'std.io.unavailable'
          : expected && fieldbus.isEmpty
              ? 'std.fieldbus.loading'
              : 'std.io.noAssignedSignals');
    }
    final sections = <Widget>[];
    for (final direction in ChannelDir.values) {
      final rows = signals.where((signal) => signal.channel.dir == direction);
      if (rows.isEmpty) continue;
      if (sections.isNotEmpty) sections.add(const SizedBox(height: 14));
      sections.add(_IoSignalGroup(direction: direction, children: [
        for (final signal in rows)
          _IoSignalRow(channel: signal.channel, usable: signal.usable),
      ]));
    }
    return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch, children: sections);
  }
}

class _IoSignalGroup extends StatelessWidget {
  final ChannelDir direction;
  final List<Widget> children;
  const _IoSignalGroup({required this.direction, required this.children});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final bosch = FraktalChromeTheme.of(context) != null;
    final fill = bosch
        ? Colors.white
        : theme.colorScheme.surfaceContainerLow;
    final heading = theme.textTheme.bodyMedium;
    final captionHeight =
        MediaQuery.textScalerOf(context).scale(heading?.fontSize ?? 14) *
            (heading?.height ?? 1.4);
    return Stack(children: [
      Container(
          margin: EdgeInsets.only(top: captionHeight / 2),
          padding: EdgeInsets.fromLTRB(8, captionHeight / 2 + 4, 8, 8),
          decoration: BoxDecoration(
              color: fill,
              border: Border.all(color: bosch ? const Color(0xFFA7AAAC)
                  : theme.colorScheme.outline),
              borderRadius: BorderRadius.circular(bosch ? 0 : 6)),
          child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: children)),
      Positioned(
          left: 8,
          top: 0,
          child: ColoredBox(
              color: fill,
              child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  child: LText(
                      direction == ChannelDir.input
                          ? 'std.io.inputs'
                          : 'std.io.outputs',
                      style: theme.textTheme.bodyMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                          color: theme.colorScheme.onSurface))))),
    ]);
  }
}

class _IoSignalRow extends StatelessWidget {
  final IoChannel channel;
  final bool usable;
  const _IoSignalRow({required this.channel, required this.usable});
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = channel.faultActive
        ? theme.colorScheme.error
        : theme.colorScheme.onSurface;
    final description = channel.descriptionKey.isEmpty
        ? ''
        : context.tr(channel.descriptionKey);
    return Padding(
      key: ValueKey('manual-io-${channel.path}'),
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Tooltip(
        message: [channel.address, channel.path]
            .where((s) => s.isNotEmpty)
            .join(' · '),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
              padding: const EdgeInsets.only(top: 2, right: 8),
              child: channel.kind == ChannelKind.digital
                  ? IoSignalLed(
                      direction: channel.dir,
                      value: usable ? channel.boolValue : null)
                  : Icon(Icons.show_chart, size: 16, color: color)),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text.rich(
                    TextSpan(children: [
                      TextSpan(
                          text: channel.name,
                          style: const TextStyle(fontFamily: 'monospace')),
                      if (description.isNotEmpty)
                        TextSpan(text: ' ($description)'),
                    ]),
                    style: theme.textTheme.bodyMedium?.copyWith(color: color)),
                if (channel.kind == ChannelKind.analog && usable)
                  Text(
                      '${channel.analogValue.toStringAsFixed(2)} ${channel.unit}'
                          .trim(),
                      style:
                          theme.textTheme.bodyMedium?.copyWith(color: color)),
                if (!usable)
                  LText('std.io.unavailable',
                      style: theme.textTheme.bodySmall
                          ?.copyWith(color: theme.colorScheme.error)),
                if (channel.forced)
                  LText('std.io.forced', style: theme.textTheme.bodySmall),
                if (channel.faultActive && channel.diagnosticKey.isNotEmpty)
                  LText(channel.diagnosticKey,
                      style: theme.textTheme.bodySmall?.copyWith(color: color)),
              ])),
        ]),
      ),
    );
  }
}
