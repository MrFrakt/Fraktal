/// Editor for the PLC-authoritative §7.7 access policy of one root Unit.
/// Changes are serialized through that root's mailbox and rechecked by the PLC.
library;

import 'package:flutter/material.dart';

import '../domain/types.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';

Future<void> showAccessPolicyEditor(
    BuildContext context, AppState app, String rootPath) {
  return showDialog<void>(
    context: context,
    builder: (context) => _AccessPolicyEditor(app: app, rootPath: rootPath),
  );
}

class _AccessPolicyEditor extends StatefulWidget {
  final AppState app;
  final String rootPath;
  const _AccessPolicyEditor({required this.app, required this.rootPath});

  @override
  State<_AccessPolicyEditor> createState() => _AccessPolicyEditorState();
}

class _AccessPolicyEditorState extends State<_AccessPolicyEditor> {
  late final List<AccessLevel> _initial;
  late final List<AccessLevel> _required;
  late final TextEditingController _timeout;
  bool _saving = false;
  String? _statusKey;

  @override
  void initState() {
    super.initState();
    final access =
        widget.app.rootOf(widget.rootPath)?.access ?? const AccessSession();
    _initial = List<AccessLevel>.generate(
      GatedAction.values.length,
      (index) => index < access.required.length
          ? access.required[index]
          : AccessLevel.admin,
    );
    _required = List<AccessLevel>.from(_initial);
    _timeout =
        TextEditingController(text: '${access.sessionTimeout.inMinutes}');
  }

  @override
  void dispose() {
    _timeout.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final minutes = int.tryParse(_timeout.text.trim());
    if (minutes == null || minutes < 0 || minutes > 10080) {
      setState(() => _statusKey = 'std.accessPolicy.timeoutInvalid');
      return;
    }
    final currentLevel =
        widget.app.rootOf(widget.rootPath)?.access?.level ?? AccessLevel.none;
    if (_required[GatedAction.accessPolicy.index].index > currentLevel.index) {
      setState(() => _statusKey = 'std.accessPolicy.selfLockout');
      return;
    }
    setState(() {
      _saving = true;
      _statusKey = null;
    });

    final current = widget.app.rootOf(widget.rootPath)?.access;
    if (current == null || current.sessionTimeout.inMinutes != minutes) {
      final accepted = await widget.app.repo
          .setSessionTimeout(widget.rootPath, Duration(minutes: minutes));
      if (!accepted) {
        if (mounted) {
          setState(() {
            _saving = false;
            _statusKey = 'std.accessPolicy.rejected';
          });
        }
        return;
      }
    }

    // ACCESS_POLICY is applied last: raising its threshold must not lock the
    // current editor out before the rest of this explicit save is sent.
    final actions = <GatedAction>[
      for (final action in GatedAction.values)
        if (action != GatedAction.accessPolicy) action,
      GatedAction.accessPolicy,
    ];
    for (final action in actions) {
      if (_required[action.index] == _initial[action.index]) continue;
      final accepted = await widget.app.repo
          .setAccessLevel(widget.rootPath, action, _required[action.index]);
      if (!accepted) {
        if (mounted) {
          setState(() {
            _saving = false;
            _statusKey = 'std.accessPolicy.rejected';
          });
        }
        return;
      }
    }

    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final open = _required.every((level) => level == AccessLevel.none);
    return AlertDialog(
      title: const LText('std.accessPolicy.title'),
      content: SizedBox(
        width: 660,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(widget.rootPath,
                  style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 8),
              const LText('std.accessPolicy.help'),
              if (open) ...[
                const SizedBox(height: 12),
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(12),
                    child: Row(children: [
                      Icon(Icons.warning_amber_outlined),
                      SizedBox(width: 10),
                      Expanded(child: LText('std.accessPolicy.openWarning')),
                    ]),
                  ),
                ),
              ],
              const SizedBox(height: 12),
              for (final action in GatedAction.values) ...[
                DropdownButtonFormField<AccessLevel>(
                  key: ValueKey('policy-${action.name}'),
                  initialValue: _required[action.index],
                  decoration: InputDecoration(
                    labelText: context.tr('std.gatedAction.${action.name}'),
                    border: const OutlineInputBorder(),
                  ),
                  items: [
                    for (final level in AccessLevel.values)
                      DropdownMenuItem(
                        value: level,
                        child: LText('std.access.${level.name}'),
                      ),
                  ],
                  onChanged: _saving
                      ? null
                      : (value) => setState(() => _required[action.index] =
                          value ?? _required[action.index]),
                ),
                const SizedBox(height: 10),
              ],
              TextField(
                controller: _timeout,
                enabled: !_saving,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: context.tr('std.accessPolicy.timeoutMinutes'),
                  helperText: context.tr('std.accessPolicy.timeoutHelp'),
                  border: const OutlineInputBorder(),
                ),
              ),
              if (_statusKey != null) ...[
                const SizedBox(height: 10),
                LText(_statusKey!,
                    style:
                        TextStyle(color: Theme.of(context).colorScheme.error)),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: _saving ? null : () => Navigator.pop(context),
          child: const LText('std.common.cancel'),
        ),
        FilledButton.icon(
          onPressed: _saving ? null : _save,
          icon: _saving
              ? const SizedBox.square(
                  dimension: 16,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : const Icon(Icons.save_outlined),
          label: const LText('std.common.save'),
        ),
      ],
    );
  }
}
