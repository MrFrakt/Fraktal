/// §3.8a persistent-data editor + §8.3 history browser + §6.11 decision prompt.
library;

import '../localization/localized_text.dart';
import 'package:flutter/material.dart';
import 'theme_surfaces.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../state/app_state.dart';
import 'touch_text_field.dart';
import 'app_theme.dart';

/// §3.8a/§3.8d/§3.8e - editable persistent data, grouped by what it is (model,
/// station, line) and within that by data class. Every value carries the levels
/// the PLC computed for it, so one class can be open to an OPERATOR while the
/// rest stays at ENGINEER; a value the session may not read is listed without
/// its value. Presentation only: the PLC re-checks every write (§7.7).
class ConfigEditor extends StatelessWidget {
  final AppState app;
  final ModuleNode node;
  const ConfigEditor({super.key, required this.app, required this.node});

  static const _kindTitles = {
    CfgKind.parCfg: 'Model data (ParCfg) — versioned, per model',
    CfgKind.stationCfg: 'Station config (StationCfg) — per deployment, not in recipes',
    CfgKind.lineCfg: 'Line data (LineCfg) — held once, shared by the line',
  };

  @override
  Widget build(BuildContext context) {
    if (node.config.isEmpty) return const SizedBox.shrink();
    final s = app.session;
    final rootReady = app.rootOf(node.path)?.state == ExecState.ready;
    final anyEditable = node.config
        .any((f) => f.hasWriteCapability && f.canReadIn(s) && f.canWriteIn(s));
    return FraktalCard(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.tune),
            const SizedBox(width: 8),
            LText('Configuration',
                style: Theme.of(context).textTheme.titleMedium),
            const Spacer(),
            if (!anyEditable)
              const Chip(
                  avatar: Icon(Icons.lock_outline, size: 16),
                  label: LText('read-only')),
          ]),
          for (final kind in CfgKind.values)
            ..._kindSection(context, kind, s, rootReady),
        ]),
      ),
    );
  }

  List<Widget> _kindSection(
      BuildContext context, CfgKind kind, AccessSession s, bool rootReady) {
    final fields = node.config.where((f) => f.kind == kind).toList();
    if (fields.isEmpty) return const [];
    // Classes in first-seen order, so the PLC's walk order is kept within each.
    final classes = <String>[];
    for (final f in fields) {
      if (!classes.contains(f.classId)) classes.add(f.classId);
    }
    return [
      const SizedBox(height: 8),
      LText(_kindTitles[kind]!, style: Theme.of(context).textTheme.labelMedium),
      for (final classId in classes) ...[
        if (classId.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 6, bottom: 2),
            child: Row(children: [
              const Icon(Icons.folder_shared_outlined, size: 16),
              const SizedBox(width: 6),
              Text('${context.tr('Data class')}: $classId',
                  style: Theme.of(context).textTheme.labelSmall),
            ]),
          ),
        for (final f in fields.where((f) => f.classId == classId))
          _row(context, f, s, rootReady),
      ],
    ];
  }

  String _levelName(BuildContext context, AccessLevel? level) =>
      level == null ? '' : context.tr('std.access.${level.name}');

  Widget _row(
      BuildContext context, CfgField f, AccessSession s, bool rootReady) {
    final label = SizedBox(
        width: 160, child: LText(f.labelKey.isEmpty ? f.name : f.labelKey));
    if (!f.canReadIn(s)) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [
          label,
          const Icon(Icons.visibility_off_outlined, size: 18),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
                f.readLevel == null
                    ? context.tr('Hidden (requires DATA_READ)')
                    : '${context.tr('Hidden - requires')} '
                        '${_levelName(context, f.readLevel)}',
                style: Theme.of(context).textTheme.bodySmall),
          ),
        ]),
      );
    }
    var edited = f.value;
    final levelOk = f.canWriteIn(s);
    final fieldCanWrite = f.hasWriteCapability &&
        levelOk &&
        (!f.requiresReady || rootReady);
    final String? helper;
    if (!f.writable) {
      helper = context.tr('Mirrored line data - edit it at the line owner');
    } else if (!levelOk) {
      helper = f.writeLevel == null
          ? context.tr('Requires DATA_WRITE')
          : '${context.tr('Requires')} ${_levelName(context, f.writeLevel)}';
    } else if (f.requiresReady && !rootReady) {
      helper = context.tr('Unit must be READY');
    } else {
      helper = null;
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        label,
        Expanded(
          child: TouchTextFormField(
            initialValue: f.value,
            enabled: fieldCanWrite,
            decoration: InputDecoration(
              isDense: true,
              border: const OutlineInputBorder(),
              suffixText: f.unit.isEmpty ? null : f.unit,
              helperText: helper,
            ),
            keyboardType: f.type == CfgType.number || f.type == CfgType.time
                ? TextInputType.number
                : TextInputType.text,
            onChanged: (value) => edited = value,
          ),
        ),
        if (fieldCanWrite)
          IconButton(
            tooltip: context.tr('Write to PLC (re-checked, 7.7)'),
            icon: const Icon(Icons.save_outlined),
            onPressed: () async {
              final ok = f.accepts(edited)
                  ? await app.repo.writeConfig(node.path, f, edited)
                  : false;
              if (!ok) {
                final root = app.rootOf(node.path);
                if (root != null) {
                  await app.showReleaseReportAction(root.path,
                      GatedAction.dataWrite, 'Configuration write blocked');
                }
              }
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: LText(
                      ok ? '${f.name} saved' : '${f.name} rejected by PLC'),
                ));
              }
            },
          ),
      ]),
    );
  }
}

/// §8.3 — full event history browser (gated by ALARM_HISTORY), newest-first,
/// with durations and reset-class/state, filterable by severity.
class HistoryBrowser extends StatefulWidget {
  final ModuleNode node;
  const HistoryBrowser({super.key, required this.node});
  @override
  State<HistoryBrowser> createState() => _HistoryBrowserState();
}

class _HistoryBrowserState extends State<HistoryBrowser> {
  final Set<Severity> _show = {Severity.high, Severity.medium, Severity.low};
  @override
  Widget build(BuildContext context) {
    final events = widget.node.ringEvents
        .where((e) => _show.contains(e.severity))
        .toList();
    return FraktalCard(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.history),
            const SizedBox(width: 8),
            LText('Event history',
                style: Theme.of(context).textTheme.titleMedium),
            const Spacer(),
            for (final k in Severity.values)
              Padding(
                padding: const EdgeInsets.only(left: 4),
                child: FilterChip(
                  label: LText(k.name),
                  selected: _show.contains(k),
                  onSelected: (v) =>
                      setState(() => v ? _show.add(k) : _show.remove(k)),
                ),
              ),
          ]),
          const SizedBox(height: 8),
          if (events.isEmpty)
            const ListTile(dense: true, title: LText('No matching events'))
          else
            for (final e in events.take(50)) _row(context, e),
        ]),
      ),
    );
  }

  Widget _row(BuildContext context, AlarmEvent e) {
    final c = severityColor(context, e.severity);
    final dur = e.duration == null ? '' : '${e.duration!.inSeconds}s';
    return ListTile(
      dense: true,
      leading: Icon(
        switch (e.severity) {
          Severity.high => Icons.error,
          Severity.medium => Icons.warning_amber,
          Severity.low => Icons.info_outline
        },
        color: c,
      ),
      title: LText(e.description),
      subtitle: LText(
          '${e.sourcePath}${e.ioTag.isEmpty ? '' : ' · ${e.ioTag}${e.ioAddress.isEmpty ? '' : ' · ${e.ioAddress}'}'} · ${e.resetClass.name}${e.timestampsSynchronized ? '' : ' · TIME UNSYNCHRONIZED'}'),
      trailing: LText(dur, style: Theme.of(context).textTheme.labelLarge),
    );
  }
}

/// §6.11 — operator decision prompt (typed request; answer written back).
class DecisionPrompt extends StatelessWidget {
  final AppState app;
  final ModuleNode node;
  const DecisionPrompt({super.key, required this.app, required this.node});
  @override
  Widget build(BuildContext context) {
    final d = node.decision;
    if (d == null || !d.pending) return const SizedBox.shrink();
    return FraktalCard(
      // Operator action, not a fault — blue like the manual panel (app_theme).
      color: operatorActionContainer(context),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.help_outline),
            const SizedBox(width: 8),
            LText('Operator decision',
                style: Theme.of(context).textTheme.titleMedium)
          ]),
          const SizedBox(height: 6),
          LText(d.prompt),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [
            for (var i = 0; i < d.options.length; i++)
              FilledButton.tonal(
                onPressed: () async {
                  final accepted =
                      await app.repo.setDecisionAnswer(node.path, i + 1);
                  if (!accepted) {
                    await app.showReleaseReportAction(node.path,
                        GatedAction.startStop, 'Decision answer blocked');
                  }
                },
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  LText(d.options[i]),
                  if (i == d.defaultOption)
                    const LText('std.decision.defaultSuffix'),
                ]),
              ),
          ]),
        ]),
      ),
    );
  }
}
