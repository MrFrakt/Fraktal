library;

import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../content/module_content_controller.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../localization/localized_text.dart';
import '../state/app_state.dart';
import 'touch_text_field.dart';

Future<ModuleTabDefinition?> showModuleTabEditor(
  BuildContext context, {
  ModuleTabDefinition? existing,
  required bool allowGuidance,
}) =>
    showDialog<ModuleTabDefinition>(
      context: context,
      builder: (_) => _TabEditorDialog(
        existing: existing,
        allowGuidance: allowGuidance,
      ),
    );

Future<ModuleControlDefinition?> showModuleControlEditor(
  BuildContext context, {
  ModuleControlDefinition? existing,
  required ModuleNode node,
}) =>
    showDialog<ModuleControlDefinition>(
      context: context,
      builder: (_) => _ControlEditorDialog(existing: existing, node: node),
    );

Future<void> exportHmiCustomization(BuildContext context, AppState app) async {
  await FilePicker.saveFile(
    dialogTitle: context.tr('std.module.editor.exportTitle'),
    fileName: 'fraktal_hmi_customization.json',
    type: FileType.custom,
    allowedExtensions: const ['json'],
    bytes: utf8.encode(app.content.exportBundle()),
  );
}

Future<void> importHmiCustomization(BuildContext context, AppState app) async {
  final picked = await FilePicker.pickFiles(
    dialogTitle: context.tr('std.module.editor.importTitle'),
    type: FileType.custom,
    allowedExtensions: const ['json'],
    withData: true,
  );
  final bytes = picked?.files.single.bytes;
  if (bytes == null || !context.mounted) return;
  final replace = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const LText('std.module.editor.importConfirmTitle'),
          content: const LText('std.module.editor.importConfirmBody'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const LText('std.common.cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const LText('std.common.import'),
            ),
          ],
        ),
      ) ??
      false;
  if (!replace || !context.mounted) return;
  try {
    final report = await app.content.importBundle(
      utf8.decode(bytes, allowMalformed: false),
      availableModulePaths: _modulePaths(app),
    );
    if (context.mounted) {
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: const LText('std.module.editor.imported'),
          content: SizedBox(
            width: 600,
            child: SingleChildScrollView(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  LText('std.module.editor.importSummary', args: {
                    'exact': report.exactPaths.length,
                    'remapped': report.remappedPaths.length,
                    'deferred': report.deferredPaths.length,
                  }),
                  if (report.remappedPaths.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    const LText('std.module.editor.remappedPaths'),
                    const SizedBox(height: 6),
                    for (final entry in report.remappedPaths.entries)
                      SelectableText('${entry.key}  →  ${entry.value}'),
                  ],
                  if (report.deferredPaths.isNotEmpty) ...[
                    const SizedBox(height: 16),
                    const LText('std.module.editor.deferredPaths'),
                    const SizedBox(height: 4),
                    const LText('std.module.editor.deferredHelp'),
                    const SizedBox(height: 6),
                    for (final path in report.deferredPaths)
                      SelectableText(path),
                  ],
                ],
              ),
            ),
          ),
          actions: [
            FilledButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const LText('std.common.close'),
            ),
          ],
        ),
      );
    }
  } on Object {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: LText('std.module.editor.invalidBundle')),
      );
    }
  }
}

Iterable<String> _modulePaths(AppState app) sync* {
  Iterable<String> walk(ModuleNode node) sync* {
    yield node.path;
    for (final child in node.children) {
      yield* walk(child);
    }
  }

  for (final root in app.forest) {
    yield* walk(root);
  }
}

class _TabEditorDialog extends StatefulWidget {
  final ModuleTabDefinition? existing;
  final bool allowGuidance;
  const _TabEditorDialog({this.existing, required this.allowGuidance});

  @override
  State<_TabEditorDialog> createState() => _TabEditorDialogState();
}

class _TabEditorDialogState extends State<_TabEditorDialog> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _title;
  late final TextEditingController _stepNo;
  late final TextEditingController _stepName;
  late final TextEditingController _marginLeft;
  late final TextEditingController _marginTop;
  late final TextEditingController _marginRight;
  late final TextEditingController _marginBottom;
  late AccessLevel _level;
  late ModuleTabKind _kind;
  late ModuleTabIcon _tabIcon;
  late ModuleBackgroundFit _backgroundFit;
  late ModuleBackgroundPosition _backgroundPosition;
  String _backgroundImageBase64 = '';
  String _backgroundImageName = '';
  String? _backgroundImageError;

  @override
  void initState() {
    super.initState();
    final tab = widget.existing;
    _title = TextEditingController(text: tab?.title ?? '');
    _stepNo = TextEditingController(
        text: tab == null || tab.triggerStepNo == 0
            ? ''
            : '${tab.triggerStepNo}');
    _stepName = TextEditingController(text: tab?.triggerStepName ?? '');
    final background = tab?.background;
    _marginLeft = TextEditingController(text: '${background?.marginLeft ?? 0}');
    _marginTop = TextEditingController(text: '${background?.marginTop ?? 0}');
    _marginRight =
        TextEditingController(text: '${background?.marginRight ?? 0}');
    _marginBottom =
        TextEditingController(text: '${background?.marginBottom ?? 0}');
    _level = tab?.requiredLevel ?? AccessLevel.operator;
    _kind = tab?.kind ?? ModuleTabKind.custom;
    _tabIcon = tab?.effectiveIcon ?? ModuleTabIcon.widgets;
    _backgroundFit = background?.fit ?? ModuleBackgroundFit.contain;
    _backgroundPosition =
        background?.position ?? ModuleBackgroundPosition.center;
    _backgroundImageBase64 = background?.imageBase64 ?? '';
    _backgroundImageName = background?.imageName ?? '';
  }

  @override
  void dispose() {
    _title.dispose();
    _stepNo.dispose();
    _stepName.dispose();
    _marginLeft.dispose();
    _marginTop.dispose();
    _marginRight.dispose();
    _marginBottom.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final existing = widget.existing;
    final kindEditable = existing == null;
    return AlertDialog(
      title: LText(existing == null
          ? 'std.module.editor.addTab'
          : 'std.module.editor.editTab'),
      content: SizedBox(
        width: 620,
        child: Form(
          key: _form,
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              TouchTextFormField(
                controller: _title,
                maxLength: 160,
                decoration: InputDecoration(
                  labelText: context.tr('std.module.editor.tabTitle'),
                  helperText: context.tr('std.module.editor.localizedHelp'),
                ),
                validator: (value) => value == null || value.trim().isEmpty
                    ? context.tr('std.module.editor.required')
                    : null,
              ),
              const SizedBox(height: 10),
              DropdownButtonFormField<ModuleTabKind>(
                initialValue: _kind,
                decoration: InputDecoration(
                    labelText: context.tr('std.module.editor.tabKind')),
                items: [
                  if (!kindEditable)
                    DropdownMenuItem(
                        value: _kind, child: LText(_tabKindLabel(_kind))),
                  if (kindEditable)
                    const DropdownMenuItem(
                      value: ModuleTabKind.custom,
                      child: LText('std.module.editor.customTab'),
                    ),
                  if (kindEditable && widget.allowGuidance)
                    const DropdownMenuItem(
                      value: ModuleTabKind.guidance,
                      child: LText('std.module.editor.guidanceTab'),
                    ),
                ],
                onChanged: kindEditable
                    ? (value) => setState(() {
                          _kind = value ?? _kind;
                          _tabIcon = _kind == ModuleTabKind.guidance
                              ? ModuleTabIcon.guidance
                              : ModuleTabIcon.widgets;
                        })
                    : null,
              ),
              if (_kind == ModuleTabKind.custom ||
                  _kind == ModuleTabKind.guidance) ...[
                const SizedBox(height: 10),
                DropdownButtonFormField<ModuleTabIcon>(
                  key: ValueKey('tab-icon-${_kind.name}'),
                  initialValue: _tabIcon,
                  decoration: InputDecoration(
                    labelText: context.tr('std.module.editor.tabIcon'),
                  ),
                  items: [
                    for (final icon in ModuleTabIcon.values)
                      DropdownMenuItem(
                        value: icon,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(_tabIconData(icon), size: 19),
                            const SizedBox(width: 8),
                            LText(_tabIconLabel(icon)),
                          ],
                        ),
                      ),
                  ],
                  onChanged: (value) =>
                      setState(() => _tabIcon = value ?? _tabIcon),
                ),
              ],
              const SizedBox(height: 10),
              DropdownButtonFormField<AccessLevel>(
                initialValue: _level,
                decoration: InputDecoration(
                    labelText: context.tr('std.module.editor.minimumAccess')),
                items: [
                  for (final level in AccessLevel.values)
                    DropdownMenuItem(
                      value: level,
                      child: Text(level.name.toUpperCase()),
                    ),
                ],
                onChanged: (value) => setState(() => _level = value ?? _level),
              ),
              if (_kind == ModuleTabKind.guidance) ...[
                const SizedBox(height: 16),
                const LText('std.module.editor.guidanceTriggerHelp'),
                const SizedBox(height: 10),
                TouchTextFormField(
                  controller: _stepNo,
                  keyboardType: TextInputType.number,
                  decoration: InputDecoration(
                      labelText:
                          context.tr('std.module.editor.triggerStepNumber')),
                  validator: (value) {
                    if ((value ?? '').trim().isEmpty) return null;
                    final number = int.tryParse(value!.trim());
                    return number == null || number < 0
                        ? context.tr('std.module.editor.invalidNumber')
                        : null;
                  },
                ),
                const SizedBox(height: 10),
                TouchTextFormField(
                  controller: _stepName,
                  maxLength: 255,
                  decoration: InputDecoration(
                    labelText: context.tr('std.module.editor.triggerStepName'),
                    helperText:
                        context.tr('std.module.editor.triggerWildcardHelp'),
                  ),
                ),
              ],
              if (_kind == ModuleTabKind.overview) ...[
                const SizedBox(height: 16),
                _backgroundEditor(context),
              ],
            ]),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const LText('std.common.cancel'),
        ),
        FilledButton(
          onPressed: _save,
          child: const LText('std.common.save'),
        ),
      ],
    );
  }

  void _save() {
    if (!(_form.currentState?.validate() ?? false)) return;
    final existing = widget.existing;
    final id = existing?.id ??
        'custom-${DateTime.now().microsecondsSinceEpoch.toRadixString(36)}';
    Navigator.pop(
      context,
      ModuleTabDefinition(
        id: id,
        title: _title.text.trim(),
        kind: _kind,
        requiredLevel: _level,
        controls: existing?.controls ?? const [],
        triggerStepNo: int.tryParse(_stepNo.text.trim()) ?? 0,
        triggerStepName: _stepName.text.trim(),
        tabIcon:
            _kind == ModuleTabKind.custom || _kind == ModuleTabKind.guidance
                ? _tabIcon
                : existing?.tabIcon,
        background: _kind == ModuleTabKind.overview &&
                _backgroundImageBase64.isNotEmpty
            ? ModuleTabBackground(
                imageBase64: _backgroundImageBase64,
                imageName: _backgroundImageName,
                fit: _backgroundFit,
                position: _backgroundPosition,
                marginLeft: double.tryParse(_marginLeft.text.trim()) ?? 0,
                marginTop: double.tryParse(_marginTop.text.trim()) ?? 0,
                marginRight: double.tryParse(_marginRight.text.trim()) ?? 0,
                marginBottom: double.tryParse(_marginBottom.text.trim()) ?? 0,
              )
            : null,
      ),
    );
  }

  Widget _backgroundEditor(BuildContext context) => Card.outlined(
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              LText(
                'std.module.editor.backgroundImage',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 4),
              const LText('std.module.editor.backgroundHelp'),
              const SizedBox(height: 8),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.wallpaper_outlined),
                title: Text(_backgroundImageName.isEmpty
                    ? context.tr('std.module.editor.noBackgroundImage')
                    : _backgroundImageName),
                subtitle: _backgroundImageError == null
                    ? null
                    : LText(_backgroundImageError!),
                trailing: Wrap(
                  spacing: 6,
                  children: [
                    if (_backgroundImageBase64.isNotEmpty)
                      IconButton(
                        tooltip: context.tr('std.common.delete'),
                        onPressed: () => setState(() {
                          _backgroundImageBase64 = '';
                          _backgroundImageName = '';
                          _backgroundImageError = null;
                        }),
                        icon: const Icon(Icons.delete_outline),
                      ),
                    OutlinedButton.icon(
                      onPressed: _pickBackgroundImage,
                      icon: const Icon(Icons.file_open_outlined),
                      label: const LText('std.module.editor.chooseImage'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: DropdownButtonFormField<ModuleBackgroundFit>(
                      initialValue: _backgroundFit,
                      decoration: InputDecoration(
                        labelText:
                            context.tr('std.module.editor.backgroundFit'),
                      ),
                      items: [
                        for (final fit in ModuleBackgroundFit.values)
                          DropdownMenuItem(
                            value: fit,
                            child: LText(_backgroundFitLabel(fit)),
                          ),
                      ],
                      onChanged: (value) => setState(
                        () => _backgroundFit = value ?? _backgroundFit,
                      ),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: DropdownButtonFormField<ModuleBackgroundPosition>(
                      initialValue: _backgroundPosition,
                      decoration: InputDecoration(
                        labelText:
                            context.tr('std.module.editor.backgroundPosition'),
                      ),
                      items: [
                        for (final position in ModuleBackgroundPosition.values)
                          DropdownMenuItem(
                            value: position,
                            child: LText(_backgroundPositionLabel(position)),
                          ),
                      ],
                      onChanged: (value) => setState(
                        () =>
                            _backgroundPosition = value ?? _backgroundPosition,
                      ),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 12),
              LText(
                'std.module.editor.backgroundMargins',
                style: Theme.of(context).textTheme.labelLarge,
              ),
              const SizedBox(height: 6),
              Row(
                children: [
                  _marginField(context, _marginLeft, 'left'),
                  const SizedBox(width: 8),
                  _marginField(context, _marginTop, 'top'),
                  const SizedBox(width: 8),
                  _marginField(context, _marginRight, 'right'),
                  const SizedBox(width: 8),
                  _marginField(context, _marginBottom, 'bottom'),
                ],
              ),
            ],
          ),
        ),
      );

  Widget _marginField(
    BuildContext context,
    TextEditingController controller,
    String side,
  ) =>
      Expanded(
        child: TouchTextFormField(
          controller: controller,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(
            labelText: context.tr('std.module.editor.margin.$side'),
            suffixText: 'px',
          ),
          validator: (source) => _boundedDoubleError(
            context,
            source,
            0,
            ModuleTabBackground.maxMargin,
          ),
        ),
      );

  Future<void> _pickBackgroundImage() async {
    final picked = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['png', 'jpg', 'jpeg', 'webp'],
      withData: true,
    );
    final file = picked?.files.single;
    final bytes = file?.bytes;
    if (bytes == null) return;
    if (bytes.length > ModuleTabBackground.maxImageBytes) {
      setState(
        () =>
            _backgroundImageError = 'std.module.editor.backgroundImageTooLarge',
      );
      return;
    }
    setState(() {
      _backgroundImageBase64 = base64Encode(bytes);
      _backgroundImageName = file!.name;
      _backgroundImageError = null;
    });
  }
}

class _ControlEditorDialog extends StatefulWidget {
  final ModuleControlDefinition? existing;
  final ModuleNode node;
  const _ControlEditorDialog({this.existing, required this.node});

  @override
  State<_ControlEditorDialog> createState() => _ControlEditorDialogState();
}

class _ControlEditorDialogState extends State<_ControlEditorDialog> {
  final _form = GlobalKey<FormState>();
  late final TextEditingController _label;
  late final TextEditingController _text;
  late final TextEditingController _unit;
  late final TextEditingController _actionValue;
  late final TextEditingController _period;
  late final TextEditingController _points;
  late ModuleControlKind _kind;
  late ModuleActionKind _action;
  late bool _confirmAction;
  late ModuleControlWidth _width;
  String _imageBase64 = '';
  String _imageName = '';
  String? _imageError;
  String? _bindingError;
  late List<String> _bindings;

  @override
  void initState() {
    super.initState();
    final control = widget.existing;
    _kind = control?.kind ?? ModuleControlKind.text;
    _action = control?.action ?? ModuleActionKind.none;
    _label = TextEditingController(text: control?.label ?? '');
    _text = TextEditingController(text: control?.text ?? '');
    _bindings = control?.linkedBindings.toList() ?? [];
    _unit = TextEditingController(text: control?.unit ?? '');
    _actionValue = TextEditingController(text: '${control?.actionValue ?? 0}');
    _confirmAction = control?.confirmation != ModuleActionConfirmation.none;
    _width = control?.width ?? ModuleControlWidth.full;
    _period = TextEditingController(text: '${control?.samplePeriodMs ?? 1000}');
    _points = TextEditingController(text: '${control?.historyPoints ?? 120}');
    _imageBase64 = control?.imageBase64 ?? '';
    _imageName = control?.imageName ?? '';
  }

  @override
  void dispose() {
    for (final controller in [
      _label,
      _text,
      _unit,
      _actionValue,
      _period,
      _points,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  bool get _usesBinding => ModuleControlDefinition.usesBindings(_kind);

  int get _maximumBindings => ModuleControlDefinition.maximumBindingsFor(_kind);

  int? get _selectedManualCommand {
    final selected = int.tryParse(_actionValue.text);
    return widget.node.commands.any((command) => command.value == selected)
        ? selected
        : null;
  }

  int? get _selectedDecisionOption {
    final selected = int.tryParse(_actionValue.text);
    final count = widget.node.decision?.options.length ?? 0;
    return selected != null && selected >= 1 && selected <= count
        ? selected
        : null;
  }

  int? _firstCatalogActionValue(ModuleActionKind action) => switch (action) {
        ModuleActionKind.manualCommand =>
          widget.node.commands.firstOrNull?.value,
        ModuleActionKind.decisionAnswer =>
          widget.node.decision?.options.isNotEmpty == true ? 1 : null,
        _ => 0,
      };

  @override
  Widget build(BuildContext context) => AlertDialog(
        title: LText(widget.existing == null
            ? 'std.module.editor.addControl'
            : 'std.module.editor.editControl'),
        content: SizedBox(
          width: 620,
          child: Form(
            key: _form,
            child: SingleChildScrollView(
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                DropdownButtonFormField<ModuleControlKind>(
                  initialValue: _kind,
                  decoration: InputDecoration(
                      labelText: context.tr('std.module.editor.controlKind')),
                  items: [
                    for (final kind in ModuleControlKind.values)
                      DropdownMenuItem(
                        value: kind,
                        child: LText(_controlKindLabel(kind)),
                      ),
                  ],
                  onChanged: (value) => setState(() {
                    if (value != null && value != _kind) {
                      _kind = value;
                      _bindings = [];
                    }
                    _bindingError = null;
                  }),
                ),
                const SizedBox(height: 10),
                DropdownButtonFormField<ModuleControlWidth>(
                  initialValue: _width,
                  decoration: InputDecoration(
                    labelText: context.tr('std.module.editor.controlWidth'),
                  ),
                  items: [
                    for (final width in ModuleControlWidth.values)
                      DropdownMenuItem(
                        value: width,
                        child: LText('std.module.width.${width.name}'),
                      ),
                  ],
                  onChanged: (value) =>
                      setState(() => _width = value ?? _width),
                ),
                const SizedBox(height: 10),
                TouchTextFormField(
                  controller: _label,
                  maxLength: 160,
                  decoration: InputDecoration(
                    labelText: context.tr('std.module.editor.label'),
                    helperText: context.tr('std.module.editor.localizedHelp'),
                  ),
                ),
                if (_kind == ModuleControlKind.text) ...[
                  TouchTextFormField(
                    controller: _text,
                    maxLength: 4000,
                    minLines: 3,
                    maxLines: 8,
                    decoration: InputDecoration(
                        labelText: context.tr('std.module.editor.text')),
                    validator: (value) => value == null || value.trim().isEmpty
                        ? context.tr('std.module.editor.required')
                        : null,
                  ),
                ],
                if (_usesBinding) ...[
                  _OpcUaBindingPicker(
                    candidates: _bindingCandidates(widget.node, _kind),
                    selected: _bindings,
                    maximum: _maximumBindings,
                    errorText: _bindingError,
                    onChanged: (bindings) => setState(() {
                      _bindings = bindings;
                      _bindingError = null;
                    }),
                  ),
                  if (_kind == ModuleControlKind.chart)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Align(
                        alignment: Alignment.centerLeft,
                        child: LText(
                          'std.module.editor.multiBindingHelp',
                          args: {
                            'maximum': ModuleControlDefinition.maxChartBindings,
                          },
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ),
                    ),
                  const SizedBox(height: 10),
                  TouchTextFormField(
                    controller: _unit,
                    maxLength: 40,
                    decoration: InputDecoration(
                        labelText: context.tr('std.module.editor.unit')),
                  ),
                ],
                if (_kind == ModuleControlKind.chart) ...[
                  Row(children: [
                    Expanded(
                      child: TouchTextFormField(
                        controller: _period,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText:
                              context.tr('std.module.editor.samplePeriod'),
                          helperText:
                              '${ModuleControlDefinition.minSamplePeriodMs}–${ModuleControlDefinition.maxSamplePeriodMs} ms',
                        ),
                        validator: (value) => _boundedNumberError(
                          context,
                          value,
                          ModuleControlDefinition.minSamplePeriodMs,
                          ModuleControlDefinition.maxSamplePeriodMs,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: TouchTextFormField(
                        controller: _points,
                        keyboardType: TextInputType.number,
                        decoration: InputDecoration(
                          labelText:
                              context.tr('std.module.editor.historyPoints'),
                          helperText:
                              '${ModuleControlDefinition.minHistoryPoints}–${ModuleControlDefinition.maxHistoryPoints}',
                        ),
                        validator: (value) => _boundedNumberError(
                          context,
                          value,
                          ModuleControlDefinition.minHistoryPoints,
                          ModuleControlDefinition.maxHistoryPoints,
                        ),
                      ),
                    ),
                  ]),
                ],
                if (_kind == ModuleControlKind.button) ...[
                  DropdownButtonFormField<ModuleActionKind>(
                    initialValue: _action == ModuleActionKind.writeConfig
                        ? ModuleActionKind.none
                        : _action,
                    decoration: InputDecoration(
                        labelText: context.tr('std.module.editor.action')),
                    items: [
                      for (final action in ModuleActionKind.values)
                        if (action != ModuleActionKind.writeConfig)
                          DropdownMenuItem(
                            value: action,
                            child: LText(_actionLabel(action)),
                          ),
                    ],
                    onChanged: (value) => setState(() {
                      _action = value ?? _action;
                      final catalog = _firstCatalogActionValue(_action);
                      if (catalog != null) _actionValue.text = '$catalog';
                    }),
                  ),
                  const SizedBox(height: 10),
                  if (_action == ModuleActionKind.manualCommand)
                    DropdownButtonFormField<int>(
                      initialValue: _selectedManualCommand,
                      decoration: InputDecoration(
                        labelText:
                            context.tr('std.module.editor.manualCommand'),
                        helperText:
                            context.tr('std.module.editor.catalogActionHelp'),
                      ),
                      items: [
                        for (final command in widget.node.commands)
                          DropdownMenuItem(
                            value: command.value,
                            child: LText(command.label),
                          ),
                      ],
                      onChanged: (value) {
                        if (value != null) _actionValue.text = '$value';
                      },
                      validator: (value) => value == null
                          ? context.tr('std.module.editor.catalogRequired')
                          : null,
                    ),
                  if (_action == ModuleActionKind.decisionAnswer)
                    DropdownButtonFormField<int>(
                      initialValue: _selectedDecisionOption,
                      decoration: InputDecoration(
                        labelText:
                            context.tr('std.module.editor.decisionOption'),
                        helperText:
                            context.tr('std.module.editor.catalogActionHelp'),
                      ),
                      items: [
                        for (var index = 0;
                            index < (widget.node.decision?.options.length ?? 0);
                            index++)
                          DropdownMenuItem(
                            value: index + 1,
                            child: LText(widget.node.decision!.options[index]),
                          ),
                      ],
                      onChanged: (value) {
                        if (value != null) _actionValue.text = '$value';
                      },
                      validator: (value) => value == null
                          ? context.tr('std.module.editor.catalogRequired')
                          : null,
                    ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const LText('std.module.editor.confirmAction'),
                    subtitle:
                        const LText('std.module.editor.confirmActionHelp'),
                    value: _confirmAction,
                    onChanged: (value) =>
                        setState(() => _confirmAction = value),
                  ),
                ],
                if (_kind == ModuleControlKind.image) ...[
                  ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const Icon(Icons.image_outlined),
                    title: Text(_imageName.isEmpty
                        ? context.tr('std.module.editor.noImage')
                        : _imageName),
                    subtitle: _imageError == null ? null : LText(_imageError!),
                    trailing: OutlinedButton.icon(
                      onPressed: _pickImage,
                      icon: const Icon(Icons.file_open_outlined),
                      label: const LText('std.module.editor.chooseImage'),
                    ),
                  ),
                ],
              ]),
            ),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const LText('std.common.cancel'),
          ),
          FilledButton(
            onPressed: _save,
            child: const LText('std.common.save'),
          ),
        ],
      );

  Future<void> _pickImage() async {
    final picked = await FilePicker.pickFiles(
      type: FileType.custom,
      allowedExtensions: const ['png', 'jpg', 'jpeg', 'webp', 'gif'],
      withData: true,
    );
    final file = picked?.files.single;
    final bytes = file?.bytes;
    if (bytes == null) return;
    if (bytes.length > ModuleControlDefinition.maxImageBytes) {
      setState(() => _imageError = 'std.module.editor.imageTooLarge');
      return;
    }
    setState(() {
      _imageBase64 = base64Encode(bytes);
      _imageName = file!.name;
      _imageError = null;
    });
  }

  void _save() {
    if (!(_form.currentState?.validate() ?? false)) return;
    if (_usesBinding && _bindings.isEmpty) {
      setState(() => _bindingError = 'std.module.editor.bindingRequired');
      return;
    }
    if (_usesBinding && _bindings.length > _maximumBindings) {
      setState(() => _bindingError = 'std.module.editor.tooManyBindings');
      return;
    }
    if (_kind == ModuleControlKind.image && _imageBase64.isEmpty) {
      setState(() => _imageError = 'std.module.editor.imageRequired');
      return;
    }
    final existing = widget.existing;
    Navigator.pop(
      context,
      ModuleControlDefinition(
        id: existing?.id ??
            'control-${DateTime.now().microsecondsSinceEpoch.toRadixString(36)}',
        kind: _kind,
        label: _label.text.trim(),
        text: _text.text.trim(),
        binding: _usesBinding ? _bindings.first : '',
        bindings: _usesBinding ? List.unmodifiable(_bindings) : const [],
        unit: _unit.text.trim(),
        action: _kind == ModuleControlKind.textInput
            ? ModuleActionKind.writeConfig
            : _action,
        actionValue: int.tryParse(_actionValue.text.trim()) ?? 0,
        confirmation: _confirmAction
            ? ModuleActionConfirmation.confirm
            : ModuleActionConfirmation.none,
        width: _width,
        targetPath: '',
        samplePeriodMs: int.tryParse(_period.text.trim()) ?? 1000,
        historyPoints: int.tryParse(_points.text.trim()) ?? 120,
        imageBase64: _imageBase64,
        imageName: _imageName,
      ),
    );
  }
}

class _OpcUaBindingPicker extends StatefulWidget {
  final Map<String, PublishedTagValue> candidates;
  final List<String> selected;
  final int maximum;
  final String? errorText;
  final ValueChanged<List<String>> onChanged;

  const _OpcUaBindingPicker({
    required this.candidates,
    required this.selected,
    required this.maximum,
    required this.errorText,
    required this.onChanged,
  });

  @override
  State<_OpcUaBindingPicker> createState() => _OpcUaBindingPickerState();
}

class _OpcUaBindingPickerState extends State<_OpcUaBindingPicker> {
  TextEditingController? _searchController;

  @override
  Widget build(BuildContext context) {
    final atChartLimit =
        widget.maximum > 1 && widget.selected.length >= widget.maximum;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.selected.isNotEmpty) ...[
          Align(
            alignment: Alignment.centerLeft,
            child: LText(
              'std.module.editor.bindingSelected',
              style: Theme.of(context).textTheme.labelMedium,
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              for (final binding in widget.selected)
                InputChip(
                  key: ValueKey('opcua-binding-chip-$binding'),
                  avatar: widget.candidates.containsKey(binding)
                      ? const Icon(Icons.link, size: 17)
                      : Tooltip(
                          message: context
                              .tr('std.module.editor.bindingUnavailable'),
                          child: Icon(
                            Icons.warning_amber_rounded,
                            size: 17,
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                  label: Text(binding),
                  onDeleted: () => widget.onChanged([
                    for (final item in widget.selected)
                      if (item != binding) item,
                  ]),
                ),
            ],
          ),
          const SizedBox(height: 8),
        ],
        Autocomplete<String>(
          key: const ValueKey('opcua-binding-autocomplete'),
          displayStringForOption: (option) => option,
          optionsBuilder: (editingValue) {
            if (atChartLimit) return const Iterable<String>.empty();
            final query = editingValue.text.trim().toLowerCase();
            return widget.candidates.keys.where((path) {
              if (widget.selected.contains(path)) return false;
              if (query.isEmpty) return true;
              final value = widget.candidates[path];
              return path.toLowerCase().contains(query) ||
                  _bindingValueSummary(value).toLowerCase().contains(query);
            }).take(50);
          },
          onSelected: (binding) {
            final next = widget.maximum == 1
                ? <String>[binding]
                : <String>[...widget.selected, binding];
            widget.onChanged(next);
            _searchController?.clear();
          },
          fieldViewBuilder: (context, controller, focusNode, onFieldSubmitted) {
            _searchController = controller;
            return TouchTextField(
              key: const ValueKey('opcua-binding-search'),
              controller: controller,
              focusNode: focusNode,
              enabled: !atChartLimit,
              onSubmitted: (_) => onFieldSubmitted(),
              decoration: InputDecoration(
                labelText: context.tr('std.module.editor.bindingSearch'),
                helperText: atChartLimit
                    ? context.tr('std.module.editor.bindingLimitReached')
                    : context.tr('std.module.editor.bindingHelp'),
                errorText: widget.errorText == null
                    ? null
                    : context.tr(widget.errorText!),
                prefixIcon: const Icon(Icons.search),
                suffixText: '${widget.selected.length}/${widget.maximum}',
              ),
            );
          },
          optionsViewBuilder: (context, onSelected, options) => Align(
            alignment: Alignment.topLeft,
            child: Material(
              elevation: 8,
              borderRadius: BorderRadius.circular(8),
              clipBehavior: Clip.antiAlias,
              child: ConstrainedBox(
                constraints:
                    const BoxConstraints(maxWidth: 560, maxHeight: 280),
                child: ListView.builder(
                  padding: EdgeInsets.zero,
                  shrinkWrap: true,
                  itemCount: options.length,
                  itemBuilder: (context, index) {
                    final path = options.elementAt(index);
                    final value = widget.candidates[path];
                    return ListTile(
                      dense: true,
                      leading: Icon(_bindingValueIcon(value), size: 19),
                      title: Text(path),
                      subtitle: Text(_bindingValueSummary(value)),
                      onTap: () => onSelected(path),
                    );
                  },
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

Map<String, PublishedTagValue> _bindingCandidates(
  ModuleNode node,
  ModuleControlKind kind,
) {
  final candidates = <String, PublishedTagValue>{};
  if (kind == ModuleControlKind.textInput) {
    for (final field
        in node.config.where((item) => item.type == CfgType.text)) {
      final prefix = field.kind == CfgKind.stationCfg ? 'StationCfg' : 'ParCfg';
      final path = '$prefix/${field.name}';
      candidates[path] =
          node.tagAt(path) ?? PublishedTagValue.good(field.value);
    }
  } else {
    for (final entry in node.hmiTags.entries) {
      final tag = entry.value;
      final accepted = switch (kind) {
        ModuleControlKind.value => _isScalarTag(tag),
        ModuleControlKind.indicator => _isBooleanTag(tag),
        ModuleControlKind.chart => _isNumericTag(tag),
        _ => false,
      };
      if (accepted) candidates[entry.key] = tag;
    }
  }
  return Map.fromEntries(
    candidates.entries.toList()..sort((a, b) => a.key.compareTo(b.key)),
  );
}

IconData _bindingValueIcon(PublishedTagValue? tag) => switch (tag?.value) {
      bool _ => Icons.toggle_on_outlined,
      num _ => Icons.numbers,
      String _ => Icons.text_fields,
      _ when _isBooleanTag(tag) => Icons.toggle_on_outlined,
      _ when _isNumericTag(tag) => Icons.numbers,
      _ when _isStringTag(tag) => Icons.text_fields,
      _ => Icons.data_object,
    };

String _bindingValueSummary(PublishedTagValue? tag) {
  if (tag == null) return 'UNAVAILABLE';
  final rendered = '${tag.value ?? '--'}';
  final shortened =
      rendered.length > 80 ? '${rendered.substring(0, 77)}...' : rendered;
  return '${tag.typeName.toUpperCase()} · '
      '${tag.quality.name.toUpperCase()} · $shortened';
}

bool _isScalarTag(PublishedTagValue? tag) =>
    _isBooleanTag(tag) || _isNumericTag(tag) || _isStringTag(tag);

bool _isBooleanTag(PublishedTagValue? tag) =>
    tag?.value is bool || tag?.typeName.toLowerCase().contains('bool') == true;

bool _isNumericTag(PublishedTagValue? tag) {
  if (tag?.value is num) return true;
  final type = tag?.typeName.toLowerCase() ?? '';
  return const {
    'sbyte',
    'byte',
    'int16',
    'uint16',
    'int32',
    'uint32',
    'int64',
    'uint64',
    'float',
    'double',
    'integer',
    'number',
  }.contains(type);
}

bool _isStringTag(PublishedTagValue? tag) =>
    tag?.value is String ||
    tag?.typeName.toLowerCase().contains('string') == true;

String? _boundedNumberError(
    BuildContext context, String? source, int minimum, int maximum) {
  final value = int.tryParse((source ?? '').trim());
  return value == null || value < minimum || value > maximum
      ? context.tr('std.module.editor.range', {
          'minimum': minimum,
          'maximum': maximum,
        })
      : null;
}

String? _boundedDoubleError(
    BuildContext context, String? source, double minimum, double maximum) {
  final value = double.tryParse((source ?? '').trim());
  return value == null || value < minimum || value > maximum
      ? context.tr('std.module.editor.range', {
          'minimum': minimum.toStringAsFixed(0),
          'maximum': maximum.toStringAsFixed(0),
        })
      : null;
}

String _tabKindLabel(ModuleTabKind kind) => 'std.module.tab.${kind.name}';

String _controlKindLabel(ModuleControlKind kind) =>
    'std.module.control.${kind.name}';

String _actionLabel(ModuleActionKind action) =>
    'std.module.action.${action.name}';

String _backgroundFitLabel(ModuleBackgroundFit fit) =>
    'std.module.background.fit.${fit.name}';

String _backgroundPositionLabel(ModuleBackgroundPosition position) =>
    'std.module.background.position.${position.name}';

String _tabIconLabel(ModuleTabIcon icon) => 'std.module.icon.${icon.name}';

IconData _tabIconData(ModuleTabIcon icon) => switch (icon) {
      ModuleTabIcon.widgets => Icons.widgets_outlined,
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
      ModuleTabIcon.guidance => Icons.assistant_outlined,
      ModuleTabIcon.image => Icons.image_outlined,
      ModuleTabIcon.description => Icons.description_outlined,
      ModuleTabIcon.settings => Icons.settings_outlined,
      ModuleTabIcon.speed => Icons.speed_outlined,
      ModuleTabIcon.electrical => Icons.electrical_services_outlined,
    };
