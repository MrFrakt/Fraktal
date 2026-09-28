/// Core §3.8b parameter sets: save the station's editable values under a name,
/// load one back (staged and all-or-nothing on the PLC), delete, and move a set
/// as text. Every action is a CONFIG_SET-gated PLC request the PLC re-checks; a
/// load or export additionally needs the level of every value it touches
/// (§3.8d(e)), and a refusal shows the record the PLC named.
library;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../data/plc_repository.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';

Future<void> showConfigSetsDialog(
    BuildContext context, AppState app, String rootPath) {
  return showDialog<void>(
    context: context,
    builder: (_) => ConfigSetsDialog(app: app, rootPath: rootPath),
  );
}

class ConfigSetsDialog extends StatefulWidget {
  final AppState app;
  final String rootPath;
  const ConfigSetsDialog({super.key, required this.app, required this.rootPath});

  @override
  State<ConfigSetsDialog> createState() => _ConfigSetsDialogState();
}

class _ConfigSetsDialogState extends State<ConfigSetsDialog> {
  List<ConfigSetInfo>? _sets;
  bool _busy = false;
  String _message = '';
  bool _messageIsError = false;
  final _name = TextEditingController();
  CfgKind _kind = CfgKind.stationCfg;

  PlcRepository get _repo => widget.app.repo;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _refresh() async {
    setState(() => _busy = true);
    final sets = await _repo.listConfigSets(widget.rootPath);
    if (!mounted) return;
    setState(() {
      _sets = sets;
      _busy = false;
    });
  }

  Future<void> _run(Future<bool> Function() action, String success) async {
    setState(() => _busy = true);
    final ok = await action();
    final reason = ok ? '' : await _repo.configSetRejection(widget.rootPath);
    if (!mounted) return;
    setState(() {
      _message = ok
          ? context.tr(success)
          : '${context.tr('Refused by the PLC')}'
              '${reason.isEmpty ? '' : ': $reason'}';
      _messageIsError = !ok;
    });
    await _refresh();
  }

  Future<bool> _confirm(String question) async {
    final answer = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        content: Text(question),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const LText('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const LText('Continue')),
        ],
      ),
    );
    return answer == true;
  }

  String _kindName(CfgKind kind) => switch (kind) {
        CfgKind.parCfg => context.tr('Model set'),
        CfgKind.stationCfg => context.tr('Station set'),
        CfgKind.lineCfg => context.tr('Line set'),
      };

  Future<void> _export(ConfigSetInfo set) async {
    setState(() => _busy = true);
    final document = await _repo.exportConfigSet(widget.rootPath, set.name);
    if (!mounted) return;
    setState(() => _busy = false);
    if (document == null) {
      setState(() {
        _message = context.tr('Export refused by the PLC');
        _messageIsError = true;
      });
      return;
    }
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(set.name),
        content: SizedBox(
          width: 560,
          child: SingleChildScrollView(child: SelectableText(document)),
        ),
        actions: [
          TextButton(
              onPressed: () =>
                  Clipboard.setData(ClipboardData(text: document)),
              child: const LText('Copy')),
          FilledButton(
              onPressed: () => Navigator.pop(context),
              child: const LText('Close')),
        ],
      ),
    );
  }

  Future<void> _import() async {
    final text = TextEditingController();
    final document = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: const LText('Import parameter set'),
        content: SizedBox(
          width: 560,
          child: TextField(
            controller: text,
            maxLines: 12,
            decoration: InputDecoration(
              border: const OutlineInputBorder(),
              hintText: context.tr('Paste an exported set (JSON lines)'),
            ),
          ),
        ),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context),
              child: const LText('Cancel')),
          FilledButton(
              onPressed: () => Navigator.pop(context, text.text),
              child: const LText('Import')),
        ],
      ),
    );
    text.dispose();
    if (document == null || document.trim().isEmpty || !mounted) return;
    final lines = document.split('\n');
    for (var i = 0; i < lines.length; i++) {
      if (lines[i].trim().length > kConfigSetImportLineMax) {
        setState(() {
          _message = '${context.tr('Line')} ${i + 1} '
              '${context.tr('is longer than the PLC accepts')} '
              '($kConfigSetImportLineMax)';
          _messageIsError = true;
        });
        return;
      }
    }
    await _run(() => _repo.importConfigSet(widget.rootPath, document),
        'Parameter set imported');
  }

  @override
  Widget build(BuildContext context) {
    final permitted = widget.app.session.permits(GatedAction.configSet);
    final theme = Theme.of(context);
    final sets = _sets;
    return AlertDialog(
      title: Row(children: [
        const Icon(Icons.inventory_2_outlined),
        const SizedBox(width: 8),
        const Expanded(child: LText('Parameter sets')),
        if (_busy)
          const SizedBox(
              width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)),
      ]),
      content: SizedBox(
        width: 640,
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (!permitted)
            const ListTile(
                leading: Icon(Icons.lock_outline),
                title: LText('Parameter sets require the CONFIG_SET level')),
          Row(children: [
            Expanded(
              child: TextField(
                controller: _name,
                enabled: permitted && !_busy,
                decoration: InputDecoration(
                    isDense: true,
                    border: const OutlineInputBorder(),
                    labelText: context.tr('New set name')),
              ),
            ),
            const SizedBox(width: 8),
            DropdownButton<CfgKind>(
              value: _kind,
              items: [
                for (final kind in CfgKind.values)
                  DropdownMenuItem(value: kind, child: Text(_kindName(kind))),
              ],
              onChanged: permitted && !_busy
                  ? (kind) => setState(() => _kind = kind ?? _kind)
                  : null,
            ),
            const SizedBox(width: 8),
            FilledButton.icon(
              icon: const Icon(Icons.save_outlined),
              label: const LText('Save'),
              onPressed: permitted && !_busy
                  ? () {
                      final name = _name.text.trim();
                      if (name.isEmpty) return;
                      _run(
                          () => _repo.saveConfigSet(
                              widget.rootPath, name, _kind),
                          'Parameter set saved');
                    }
                  : null,
            ),
          ]),
          const SizedBox(height: 12),
          if (sets == null && !_busy)
            const LText('The PLC did not return a set listing.')
          else if (sets != null && sets.isEmpty)
            const LText('No parameter sets are stored.')
          else if (sets != null)
            Flexible(
              child: ListView(shrinkWrap: true, children: [
                for (final set in sets)
                  ListTile(
                    dense: true,
                    title: Text(set.name),
                    subtitle: Text([
                      _kindName(set.kind),
                      '${set.recordCount} ${context.tr('values')}',
                      if (set.modelCode.isNotEmpty) set.modelCode,
                      if (set.createdAt != null)
                        '${set.createdAt!.toIso8601String()} UTC'
                            '${set.timeSynchronized ? '' : ' (${context.tr('clock not synchronized')})'}',
                    ].join(' · ')),
                    trailing: Wrap(children: [
                      IconButton(
                        tooltip: context.tr('Load (replaces the current values)'),
                        icon: const Icon(Icons.download_outlined),
                        onPressed: permitted && !_busy
                            ? () async {
                                if (await _confirm(
                                    '${context.tr('Load')} "${set.name}"? '
                                    '${context.tr('Every value it carries replaces the current one; if any is refused, nothing changes.')}')) {
                                  await _run(
                                      () => _repo.loadConfigSet(
                                          widget.rootPath, set.name),
                                      'Parameter set loaded');
                                }
                              }
                            : null,
                      ),
                      IconButton(
                        tooltip: context.tr('Export'),
                        icon: const Icon(Icons.ios_share_outlined),
                        onPressed: permitted && !_busy ? () => _export(set) : null,
                      ),
                      IconButton(
                        tooltip: context.tr('Delete'),
                        icon: const Icon(Icons.delete_outline),
                        onPressed: permitted && !_busy
                            ? () async {
                                if (await _confirm(
                                    '${context.tr('Delete')} "${set.name}"?')) {
                                  await _run(
                                      () => _repo.deleteConfigSet(
                                          widget.rootPath, set.name),
                                      'Parameter set deleted');
                                }
                              }
                            : null,
                      ),
                    ]),
                  ),
              ]),
            ),
          if (_message.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(_message,
                  style: theme.textTheme.bodySmall?.copyWith(
                      color: _messageIsError ? theme.colorScheme.error : null)),
            ),
        ]),
      ),
      actions: [
        TextButton.icon(
          icon: const Icon(Icons.upload_file_outlined),
          label: const LText('Import'),
          onPressed: permitted && !_busy ? _import : null,
        ),
        FilledButton(
            onPressed: () => Navigator.pop(context),
            child: const LText('Close')),
      ],
    );
  }
}
