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

/// Reserved scope for the fieldbus topology (not a module identity).
const String kManifestFieldbusScope = '#Fieldbus';

/// Entries per manifest page — mirrors `PL_Fraktal.MAX_CONFIG_PAGE`.
const int kManifestPageEntries = 16;

class ConfigManifestEntry {
  final String scope; // dotted module identity, or [kManifestFieldbusScope]
  final String item; // browse fragment relative to the scope's base
  final String valueText;

  const ConfigManifestEntry(this.scope, this.item, this.valueText);
}

/// Item leaves that carry integer values (enum ordinals and counts). Everything
/// else stays a string — deterministic typing, no value-shape guessing.
const Set<String> _integerItemLeaves = {
  'Value', 'Dir', 'Kind', 'Shield', 'Style',
  'ParentIdx', 'ChannelCount', 'CatalogCount', 'AvailableModelCount',
};

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
    values['$base/${entry.item}'] = _integerItemLeaves.contains(leaf)
        ? int.tryParse(entry.valueText) ?? 0
        : entry.valueText;
  }
  return values;
}
