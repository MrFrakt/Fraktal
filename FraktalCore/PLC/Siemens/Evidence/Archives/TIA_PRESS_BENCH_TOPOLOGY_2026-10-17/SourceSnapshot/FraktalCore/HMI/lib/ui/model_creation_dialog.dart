import 'package:flutter/material.dart';

import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';

Future<void> showModelCreationDialog(
        BuildContext context, AppState app, ModuleNode root,
        {int sourceModel = 0, String sourceSet = ''}) =>
    showDialog<void>(
      context: context,
      builder: (_) => _ModelCreationDialog(
          app: app, root: root, sourceModel: sourceModel, sourceSet: sourceSet),
    );

class _ModelCreationDialog extends StatefulWidget {
  final AppState app;
  final ModuleNode root;
  final int sourceModel;
  final String sourceSet;
  const _ModelCreationDialog(
      {required this.app,
      required this.root,
      required this.sourceModel,
      required this.sourceSet});
  @override
  State<_ModelCreationDialog> createState() => _ModelCreationDialogState();
}

class _ModelCreationDialogState extends State<_ModelCreationDialog> {
  final _code = TextEditingController();
  late int _source = widget.sourceModel;
  bool _busy = false;
  String _error = '';

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _create() async {
    final code = _code.text.trim();
    if (!RegExp(r'^[!-~]{1,80}$').hasMatch(code) ||
        widget.root.availableModels.contains(code)) {
      setState(() => _error = context
          .tr('Enter a unique model code (1–80 characters, no spaces).'));
      return;
    }
    setState(() {
      _busy = true;
      _error = '';
    });
    final ok = await widget.app.repo.createModel(widget.root.path, code,
        sourceModel: _source, sourceSet: widget.sourceSet);
    if (!mounted) return;
    if (ok) {
      Navigator.pop(context);
      return;
    }
    setState(() {
      _busy = false;
      _error = context.tr('Refused by the PLC');
    });
  }

  @override
  Widget build(BuildContext context) {
    final root = widget.root;
    final session = widget.app.session;
    final permitted = session.permits(GatedAction.configSet) &&
        session.permits(GatedAction.dataWrite) &&
        root.availableModels.length < root.modelCapacity;
    return AlertDialog(
      title: const LText('New model'),
      content: SizedBox(
          width: 440,
          child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const LText(
                    'Creates an inactive copy. Edit its values, then use Changeover to activate it.'),
                const SizedBox(height: 16),
                TextField(
                    controller: _code,
                    enabled: !_busy,
                    maxLength: 80,
                    decoration: InputDecoration(
                        labelText: context.tr('New model code'),
                        border: const OutlineInputBorder())),
                const SizedBox(height: 8),
                if (widget.sourceSet.isNotEmpty)
                  Text('${context.tr('Model set')}: ${widget.sourceSet}')
                else
                  DropdownButtonFormField<int>(
                      initialValue: _source,
                      decoration: InputDecoration(
                          labelText: context.tr('Copy values from')),
                      items: [
                        DropdownMenuItem(
                            value: 0,
                            child: Text(
                                '${root.modelCode} (${context.tr('running')})')),
                        for (var i = 0; i < root.availableModels.length; i++)
                          DropdownMenuItem(
                              value: i + 1,
                              child: Text(root.availableModels[i])),
                      ],
                      onChanged: _busy
                          ? null
                          : (value) => setState(() => _source = value ?? 0)),
                const SizedBox(height: 12),
                Text(
                    '${root.availableModels.length} / ${root.modelCapacity} ${context.tr('models')}'),
                if (_error.isNotEmpty)
                  Text(_error,
                      style: TextStyle(
                          color: Theme.of(context).colorScheme.error)),
              ])),
      actions: [
        TextButton(
            onPressed: _busy ? null : () => Navigator.pop(context),
            child: const LText('Cancel')),
        FilledButton(
            key: const ValueKey('create-model-confirm'),
            onPressed: permitted && !_busy ? _create : null,
            child: _busy
                ? const SizedBox(
                    width: 18,
                    height: 18,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const LText('Create')),
      ],
    );
  }
}
