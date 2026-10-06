import 'dart:convert';

import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../localization/localized_text.dart';

String parameterSetFileName(String name) =>
    '${name.replaceAll(RegExp(r'[^A-Za-z0-9_-]'), '_')}.jsonl';

Future<void> showParameterSetExport(
    BuildContext context, String name, Future<String?> document) async {
  final text = await document;
  if (!context.mounted) return;
  if (text == null) {
    ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(context.tr('Export refused by the PLC'))));
    return;
  }
  await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
            title: Text(name),
            content: SizedBox(
                width: 560,
                child: SingleChildScrollView(child: SelectableText(text))),
            actions: [
              TextButton(
                  onPressed: () => Clipboard.setData(ClipboardData(text: text)),
                  child: const LText('Copy')),
              FilledButton.icon(
                  icon: const Icon(Icons.download_outlined),
                  label: const LText('Download file'),
                  onPressed: () async {
                    try {
                      await FilePicker.saveFile(
                          fileName: parameterSetFileName(name),
                          type: FileType.custom,
                          allowedExtensions: ['jsonl'],
                          bytes: utf8.encode('$text\n'));
                    } catch (_) {
                      if (context.mounted)
                        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                            content: Text(context.tr('File export failed'))));
                    }
                  }),
              TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const LText('Close')),
            ],
          ));
}
