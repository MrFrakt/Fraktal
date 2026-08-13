/// Config-manifest hydration for the OPC UA transports (Core §3.10.2).
///
/// Activation-static configuration (command catalogs, model lists, mode policy,
/// fieldbus tag identity) is deliberately excluded from the cyclic OPC UA tree
/// (`OPC.UA.DA := '0'`) to keep the published address space small. The PLC
/// serves it instead through the `QUERY_CONFIG` request mailbox as pages of
/// `{Scope, Item, ValueText}` entries, where `Item` reproduces the server's
/// array naming (`Catalog/Catalog[2]/Label`, `Nodes/Nodes[3]/Channels/...`).
///
/// [synthesizeManifestValues] turns those entries back into the exact flat
/// browse-path keys the snapshot mapper would have read from a fully published
/// tree — so the mapper, facets, and views stay completely unchanged; the
/// repository just overlays this map under the live snapshot values.
library;

import '../domain/types.dart';

/// Reserved scope for the fieldbus topology (not a module identity).
const String kManifestFieldbusScope = '#Fieldbus';

/// Entries per manifest page — mirrors `PL_Fraktal.MAX_CONFIG_PAGE`.
const int kManifestPageEntries = 16;

class ConfigManifestEntry {
  final String scope; // dotted module identity, or [kManifestFieldbusScope]
  final String item; // browse fragment relative to the scope's base
  final String valueText;
  final String writeKey;
  final int writeRevision;
  final int configKind;
  final int valueType;
  final bool writable;
  final bool requiresReady;
  final bool hasMinimum;
  final bool hasMaximum;
  final double minimum;
  final double maximum;
  final String unit;
  final String labelKey;
  final String enumDomain;

  const ConfigManifestEntry(this.scope, this.item, this.valueText,
      {this.writeKey = '',
      this.writeRevision = 0,
      this.configKind = 0,
      this.valueType = 1,
      this.writable = false,
      this.requiresReady = false,
      this.hasMinimum = false,
      this.hasMaximum = false,
      this.minimum = 0,
      this.maximum = 0,
      this.unit = '',
      this.labelKey = '',
      this.enumDomain = ''});
}

/// Builds the editable surface exclusively from explicit PLC capabilities.
/// Missing/invalid metadata and duplicate `(Scope, WriteKey)` registrations are
/// omitted, so older servers and conflicting owners fail closed.
Map<String, List<CfgField>> configFieldsFromManifest(
    Iterable<ConfigManifestEntry> entries) {
  final fields = <String, Map<String, CfgField>>{};
  final conflicted = <String>{};
  for (final entry in entries) {
    if (!entry.writable ||
        entry.scope.isEmpty ||
        entry.item.isEmpty ||
        entry.writeKey.isEmpty ||
        entry.writeRevision <= 0 ||
        entry.configKind < 0 ||
        entry.configKind >= CfgKind.values.length ||
        entry.valueType < 0 ||
        entry.valueType >= CfgType.values.length ||
        (entry.hasMinimum &&
            entry.hasMaximum &&
            entry.minimum > entry.maximum)) {
      continue;
    }
    final identity = '${entry.scope}\u0000${entry.writeKey}';
    if (conflicted.contains(identity)) continue;
    final owner = fields.putIfAbsent(entry.scope, () => <String, CfgField>{});
    if (owner.containsKey(entry.writeKey)) {
      owner.remove(entry.writeKey);
      conflicted.add(identity);
      continue;
    }
    final domain = entry.enumDomain.isEmpty
        ? const <String>[]
        : entry.enumDomain
            .split('|')
            .map((value) => value.trim())
            .where((value) => value.isNotEmpty)
            .toList(growable: false);
    final field = CfgField(
      entry.item,
      CfgKind.values[entry.configKind],
      CfgType.values[entry.valueType],
      entry.valueText,
      unit: entry.unit,
      labelKey: entry.labelKey,
      writeKey: entry.writeKey,
      writeRevision: entry.writeRevision,
      writable: true,
      requiresReady: entry.requiresReady,
      minimum: entry.hasMinimum ? entry.minimum : null,
      maximum: entry.hasMaximum ? entry.maximum : null,
      enumDomain: domain,
    );
    if (field.accepts(entry.valueText)) owner[entry.writeKey] = field;
  }
  return {
    for (final entry in fields.entries)
      if (entry.value.isNotEmpty)
        entry.key: (entry.value.values.toList()
          ..sort((left, right) => left.name.compareTo(right.name))),
  };
}

/// Item leaves that carry integer values (enum ordinals and counts).
///
/// **Fallback only.** The entry's own `ValueType` is authoritative and is used
/// first; this list exists for a PLC built before `M_AppendNumber` stamped
/// `NUMBER` on the entries it writes.
///
/// Keeping a hand-maintained name list as the PRIMARY rule is what broke the
/// §3.13 flow chart: `StepNo` was never added, so every row's step number
/// arrived as the string "100", `_integer()` fell back to 0, and the whole
/// chart rendered as "N0" with empty drill-downs. A type the sender knows must
/// never be re-derived by the receiver.
const Set<String> _integerItemLeaves = {
  'Value',
  'Dir',
  'Kind',
  'Shield',
  'Style',
  'ParentIdx',
  'ChannelCount',
  'CatalogCount',
  'AvailableModelCount',
  'MetaCount',
  'ReasonCode',
  'StallTime',
  // §3.13 flow-chart row definition (the leaves the PLC appends as numbers).
  'StepNo',
  'Branch',
  'TimeClass',
  'ExpectedTime',
};

const Set<String> _booleanItemLeaves = {'Forceable', 'Shelvable'};

/// Rebuilds flat browse-path keys from manifest entries.
///
/// [browseBaseByModulePath] maps a dotted Fraktal module identity to its OPC UA
/// browse base (from the projection); [topologyBase] is the browse path of the
/// `ST_FieldbusTopology` instance (the prefix of `.../Topology/NodeCount`).
/// Entries whose scope cannot be resolved yet are skipped — the next fetch
/// after a fuller projection resolves them.
Map<String, Object?> synthesizeManifestValues(
  Iterable<ConfigManifestEntry> entries, {
  required Map<String, String> browseBaseByModulePath,
  required String? topologyBase,
}) {
  final values = <String, Object?>{};
  for (final entry in entries) {
    if (entry.item.isEmpty) continue;
    final String? base = entry.scope == kManifestFieldbusScope
        ? topologyBase
        : browseBaseByModulePath[entry.scope];
    if (base == null || base.isEmpty) continue;
    final leaf = entry.item.substring(entry.item.lastIndexOf('/') + 1);
    // The entry's DECLARED type wins; the leaf-name lists are only consulted
    // when the PLC did not say (an older build, where every entry is TEXT).
    // Deriving the type from the name was the primary rule once and it silently
    // stringified every flow-chart step number — see _integerItemLeaves.
    final declared = entry.valueType >= 0 &&
            entry.valueType < CfgType.values.length
        ? CfgType.values[entry.valueType]
        : CfgType.text;
    // CfgType.time is the PLC's DURATION (renamed: TIME is reserved in ST); it
    // travels as a millisecond count, so it is numeric here too.
    final numeric = declared == CfgType.number ||
        declared == CfgType.time ||
        (declared == CfgType.text && _integerItemLeaves.contains(leaf));
    final boolean = declared == CfgType.boolean ||
        (declared == CfgType.text && _booleanItemLeaves.contains(leaf));
    values['$base/${entry.item}'] = numeric
        ? (int.tryParse(entry.valueText) ?? 0)
        : boolean
            ? entry.valueText.toUpperCase() == 'TRUE'
            : entry.valueText;
  }
  return values;
}
