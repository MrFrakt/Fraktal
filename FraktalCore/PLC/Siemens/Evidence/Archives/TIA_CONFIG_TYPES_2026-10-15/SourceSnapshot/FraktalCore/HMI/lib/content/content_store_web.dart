// ignore_for_file: deprecated_member_use
library;

import 'dart:convert';
import 'dart:html' as html;
import 'content_store_base.dart';

ContentStore createContentStore() => _WebContentStore();

class _WebContentStore implements ContentStore {
  static const _key = 'fraktal.hmi.moduleContent.v1';
  static const _databaseName = 'fraktal.hmi.content';
  static const _objectStore = 'content';

  Future<dynamic> _database() async {
    final factory = html.window.indexedDB;
    if (factory == null) return null;
    return factory.open(
      _databaseName,
      version: 1,
      onUpgradeNeeded: (event) {
        final dynamic database = (event.target as dynamic).result;
        if (!database.objectStoreNames.contains(_objectStore)) {
          database.createObjectStore(_objectStore);
        }
      },
    );
  }

  @override
  Future<Map<String, Object?>> load() async {
    try {
      final database = await _database();
      String? raw;
      if (database != null) {
        final transaction = database.transaction(_objectStore, 'readonly');
        final stored =
            await transaction.objectStore(_objectStore).getObject(_key);
        await transaction.completed;
        raw = stored is String ? stored : null;
      }
      raw ??= html.window.localStorage[_key];
      final value = raw == null ? null : jsonDecode(raw);
      if (raw != null && database != null) {
        await _saveToDatabase(database, raw);
        html.window.localStorage.remove(_key);
      }
      return value is Map ? Map<String, Object?>.from(value) : {};
    } on Object {
      return {};
    }
  }

  @override
  Future<void> save(Map<String, Object?> value) async {
    final encoded = jsonEncode(value);
    final database = await _database();
    if (database == null) {
      html.window.localStorage[_key] = encoded;
      return;
    }
    await _saveToDatabase(database, encoded);
    html.window.localStorage.remove(_key);
  }

  Future<void> _saveToDatabase(dynamic database, String encoded) async {
    final transaction = database.transaction(_objectStore, 'readwrite');
    transaction.objectStore(_objectStore).put(encoded, _key);
    await transaction.completed;
  }
}
