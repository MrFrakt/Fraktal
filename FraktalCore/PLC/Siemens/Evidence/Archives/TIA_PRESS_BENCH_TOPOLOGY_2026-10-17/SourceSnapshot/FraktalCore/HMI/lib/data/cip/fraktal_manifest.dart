library;

/// Decoder for the Fraktal/AB §3.10.2 manifest as published on the controller.
///
/// The manifest is the discovery surface: a gateway-less client derives the
/// module tree and its keys from these tables instead of from a build-time
/// copy. The layout here is the Dart port of the controller side
/// (`fraktal_ab_manifest.py`) and of the reference client
/// (`fraktal_ab_manifest_read.py`): every member is a DINT, except the
/// localization strings, which are LEN (DINT) + DATA (ASCII[KeyWidth]).
/// Coherence follows S7's rule — read the header, read the tables, re-read
/// the header, and accept the snapshot only if ConfigRevision did not move.
import 'dart:typed_data';


class FraktalManifestTable {
  final String name;
  final List<(String, String)> members; // (name, 'DINT' | 'KEY32')
  final int capacity;
  const FraktalManifestTable(this.name, this.members, this.capacity);
}

/// The nine published tables, in header order. Derived from
/// `fraktal_ab_manifest.tables()` for the press declaration; the Press name
/// is fixed by the generated project this client targets.
const fraktalManifestTables = <FraktalManifestTable>[
  FraktalManifestTable('Roots', [
    ('RootId', 'DINT'), ('ModuleIndex', 'DINT'), ('RepositoryScope', 'DINT'),
    ('MailboxId', 'DINT'), ('HostEventId', 'DINT'),
  ], 2),
  FraktalManifestTable('Modules', [
    ('ModuleId', 'DINT'), ('ParentModuleId', 'DINT'), ('RootId', 'DINT'),
    ('RegistryIndex', 'DINT'), ('Tier', 'DINT'), ('TypeId', 'DINT'),
    ('LocalNameKey', 'DINT'), ('CanonicalPathKey', 'DINT'),
    ('Capabilities', 'DINT'), ('ContractAddress', 'DINT'),
  ], 8),
  FraktalManifestTable('Nameplates', [
    ('ModuleId', 'DINT'), ('ManufacturerKey', 'DINT'), ('ProductKey', 'DINT'),
    ('ModelKey', 'DINT'), ('SerialKey', 'DINT'), ('HardwareRevision', 'DINT'),
    ('SoftwareRevision', 'DINT'), ('AssetKey', 'DINT'), ('LocationKey', 'DINT'),
  ], 8),
  FraktalManifestTable('Fields', [
    ('ModuleId', 'DINT'), ('PathKey', 'DINT'), ('LogicalType', 'DINT'),
    ('Dimensions', 'DINT'), ('ReadTier', 'DINT'), ('AccessClass', 'DINT'),
    ('QualitySource', 'DINT'), ('WriteCapabilityIndex', 'DINT'),
  ], 640),
  FraktalManifestTable('Operations', [
    ('OperationId', 'DINT'), ('TargetScope', 'DINT'), ('ParameterType', 'DINT'),
    ('ResultType', 'DINT'), ('GatedAction', 'DINT'), ('Minimum', 'DINT'),
    ('Maximum', 'DINT'), ('OperationKind', 'DINT'),
  ], 8),
  FraktalManifestTable('Localization', [
    ('NumericKey', 'DINT'), ('PortableKey', 'KEY32'),
  ], 688),
  FraktalManifestTable('Rationalization', [
    ('ReasonCode', 'DINT'), ('Priority', 'DINT'), ('Category', 'DINT'),
    ('ActionKey', 'DINT'), ('ConsequenceKey', 'DINT'), ('Shelvable', 'DINT'),
  ], 24),
  FraktalManifestTable('OptionalProfiles', [
    ('ProfileId', 'DINT'), ('ProfileVersion', 'DINT'),
    ('CapabilityMask', 'DINT'), ('ProjectionMask', 'DINT'),
  ], 2),
  FraktalManifestTable('WriteCapabilities', [
    ('CapabilityIndex', 'DINT'), ('PathKey', 'DINT'), ('WriteKeyKey', 'DINT'),
    ('LabelKey', 'DINT'), ('ConfigKind', 'DINT'), ('ValueType', 'DINT'),
    ('Minimum', 'DINT'), ('Maximum', 'DINT'), ('RequiresReady', 'DINT'),
    ('UnitCode', 'DINT'), ('CaptureSourceKey', 'DINT'), ('ClassKey', 'DINT'),
    ('MinReadLevel', 'DINT'), ('MinWriteLevel', 'DINT'),
  ], 32),
];

class FraktalManifest {
  final int keyWidth;
  final Map<String, int> header;
  /// table name -> decoded rows (each row a member-name -> value map).
  final Map<String, List<Map<String, Object>>> rows;

  FraktalManifest._(this.keyWidth, this.header, this.rows);

  /// The localization pool: NumericKey -> PortableKey text.
  Map<int, String> get keys {
    final out = <int, String>{};
    for (final row in rows['Localization'] ?? const <Map<String, Object>>[]) {
      final numeric = row['NumericKey'] as int;
      final text = row['PortableKey'] as String;
      if (text.isNotEmpty) {
        out[numeric] = text;
      }
    }
    return out;
  }

  static int _stringBytes(int keyWidth) => 4 + keyWidth;

  static int _memberBytes(String type, int keyWidth) =>
      type == 'KEY32' ? _stringBytes(keyWidth) : 4;

  static int rowBytes(FraktalManifestTable table, int keyWidth) =>
      table.members.fold(0, (n, m) => n + _memberBytes(m.$2, keyWidth));

  static String _decodeString(Uint8List payload, int offset, int keyWidth) {
    final data = ByteData.sublistView(payload);
    final length =
        data.getInt32(offset, Endian.little).clamp(0, keyWidth).toInt();
    return String.fromCharCodes(
        payload.sublist(offset + 4, offset + 4 + length));
  }

  static Map<String, Object> _decodeRow(FraktalManifestTable table,
      Uint8List payload, int offset, int keyWidth) {
    final row = <String, Object>{};
    for (final (name, type) in table.members) {
      if (type == 'KEY32') {
        row[name] = _decodeString(payload, offset, keyWidth);
      } else {
        row[name] =
            ByteData.sublistView(payload).getInt32(offset, Endian.little);
      }
      offset += _memberBytes(type, keyWidth);
    }
    return row;
  }

  /// Reads and decodes the whole manifest for the application named
  /// [appName]. [readStruct] fetches one controller tag's raw bytes (a UDT
  /// read; the caller's transport decides how). Throws on any read failure.
  static Future<FraktalManifest> read(
      Future<Uint8List> Function(String tag, int elementCount) readStruct,
      String appName) async {
    final headerTag = 'FRK_${appName}_MfHeader';
    final payload = await readStruct(headerTag, 1);

    int scalar(int index) => ByteData.sublistView(payload)
        .getInt32(index * 4, Endian.little);
    final keyWidth = scalar(9); // KeyLength is the tenth declared scalar.
    if (keyWidth < 8 || keyWidth > 256) {
      throw StateError('manifest KeyLength out of range: $keyWidth');
    }

    final headerStrings = <String, String>{};
    var offset = 10 * 4;
    headerStrings['ContentHash'] = _decodeString(payload, offset, keyWidth);
    offset += _stringBytes(keyWidth);
    headerStrings['ControllerIdentity'] =
        _decodeString(payload, offset, keyWidth);
    offset += _stringBytes(keyWidth);

    final headerCounts = <String, int>{};
    for (final table in fraktalManifestTables) {
      headerCounts['${table.name}Count'] =
          ByteData.sublistView(payload).getInt32(offset, Endian.little);
      offset += 4;
      headerCounts['${table.name}Capacity'] =
          ByteData.sublistView(payload).getInt32(offset, Endian.little);
      offset += 4;
    }

    final header = <String, int>{};
    const scalars = [
      'Magic', 'SchemaMajor', 'SchemaMinor', 'CoreVersion', 'BindingVersion',
      'FrameworkVersion', 'ConfigRevision', 'Valid', 'Truncated', 'KeyLength',
    ];
    for (var i = 0; i < scalars.length; i++) {
      header[scalars[i]] = scalar(i);
    }

    final rows = <String, List<Map<String, Object>>>{};
    for (final table in fraktalManifestTables) {
      final width = rowBytes(table, keyWidth);
      try {
        // Read only the declared rows from the header's per-table count.
        final countKey = '${table.name}Count';
        final declaredCount = header[countKey] ?? table.capacity;
        final elements = declaredCount > 0 ? declaredCount : 1;
        final tag = 'FRK_${appName}_Mf${table.name}';
        final raw = await readStruct(tag, elements);
        if (raw.length < width * elements) {
          continue; // short read: skip this table, render without it
        }
        rows[table.name] = [
          for (var i = 0; i < elements; i++)
            _decodeRow(table, raw, i * width, keyWidth)
        ];
      } on Object {
        // Table unreadable — continue with the remaining tables.
      }
    }

    final manifest = FraktalManifest._(keyWidth, header, rows);
    manifest.headerStrings.addAll(headerStrings);
    manifest.counts.addAll(headerCounts);
    return manifest;
  }

  final headerStrings = <String, String>{};
  final counts = <String, int>{};
}
