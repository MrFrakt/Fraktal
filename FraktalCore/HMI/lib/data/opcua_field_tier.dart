/// Read-tier classification for the native OPC UA client (Core §3.10.2/§3.13).
///
/// The generic HMI browses the whole Fraktal contract, but most published leaves
/// are drill-down data — bounded history/trend rings, analytics, and the
/// fieldbus I/O tree — that only specific views render. Polling them at the
/// cyclic snapshot rate dominates read latency, so each leaf is assigned a tier:
///
/// - [FieldTier.live] — always-visible data (tiles, banner, counters, active
///   alarms, current step). Read every snapshot.
/// - [FieldTier.slow] — rings/trends that change per cycle/event (closed alarm
///   history, cycle profile history, OEE trend, part records). Read once at
///   discovery plus a slow heartbeat; charts tolerate the latency.
/// - [FieldTier.onDemand] — view-gated drill-down data (fieldbus live I/O).
///   Never read in the snapshot; the client reads it via a targeted batch read
///   only while the owning view is visible.
/// - [FieldTier.config] — activation-static identity (catalogs, models, policy,
///   fieldbus tags). Excluded from the cyclic tree (`OPC.UA.DA := '0'`) and
///   served through the QUERY_CONFIG manifest; this tier is informational for
///   completeness.
///
/// This is the **single source of truth**. The bridge stays generic (three
/// read buckets + targeted reads); only this classifier changes when the
/// contract grows. **Fail toward fresh**: an unknown leaf is [FieldTier.live].
library;

enum FieldTier { live, slow, onDemand, config }

/// Classifies a flattened OPC UA browse path (array indices in any published
/// form) into a read tier.
class OpcUaFieldTier {
  const OpcUaFieldTier._();

  /// Wholly dynamic subtrees — every leaf under these updates cyclically or per
  /// event and feeds an always-visible widget. Checked AFTER the onDemand/slow
  /// containers so a bulk ring inside a live container still wins its tier.
  static const Set<String> liveContainers = {
    'Diagnostic', 'Pending', 'CurrentStep', 'Decision',
    'Oee', 'HmiResponse', 'HmiRequest', 'Domain',
    'Access', 'Model',
    'Active', // AlarmLog/Active — the global alarm banner needs this fresh
    // Status is the module discovery identity (Name/ModuleType) plus live state
    // (State/ConfigRev). It MUST stay cyclic: the mapper drops any module whose
    // Status/Name is absent, so excluding it (its Name/ModuleType leaves match
    // configLeaves) would make the whole module tree vanish. Checked before the
    // configLeaves rule so Status/Name is live, not config.
    'Status',
  };

  /// Always-visible but slow-changing facets, published redundantly on every
  /// module: safety and control-power status change only on safety/power events,
  /// yet at ~265 nodes each across a forest they dominate the fast read. Read on
  /// a heartbeat (cached between) so the cyclic live poll stays small and
  /// interactive commands are not queued behind a large snapshot. Display lag is
  /// bounded by the heartbeat; the PLC safety authority is unaffected (these are
  /// read-only HMI status facets). Checked BEFORE liveContainers.
  static const Set<String> slowContainers = {
    'Safety', // §9 safety facet (mirror; ownership stays in the domain)
    'ControlPower', // §9 control-power facet
  };

  /// View-gated subtrees: read only while their owning view is visible, via a
  /// targeted batch read scoped to the module in view — NEVER in the cyclic
  /// snapshot. These are the large bounded rings/trends and the fieldbus I/O
  /// tree, which flood the server's ADS handle pool if polled continuously and
  /// only feed drill-down widgets (history browser, cycle trend, OEE trend, part
  /// records, command timing, fieldbus page). Checked BEFORE liveContainers so a
  /// ring nested under a live container is still gated.
  static const Set<String> onDemandContainers = {
    'Ring', // AlarmLog/Ring — closed-event history (history browser)
    'History', // Profiler/History + diagnostic history ring (cycle trend)
    'StepStats', // Profiler/StepStats per-step aggregates (step pareto)
    'OeeTrend', // OEE trend ring (OEE card sparkline)
    'Records', // Part/Result/Records measured values (part card)
    'Timing', // per-command timing tables (command-timing view)
    'Topology', // GVL_<Project>Fieldbus.Topology live I/O (fieldbus page)
  };

  /// Wholly static subtrees: change only on activation or a deliberate write.
  static const Set<String> configContainers = {
    'Nameplate',
    'Catalog',
    'AvailableModels',
    'ModePolicy',
    'ParCfg',
    'StationCfg',
    'Meta',
  };

  /// Static leaves that sit on a mixed struct next to live siblings.
  ///
  /// NOT here: SupportedModesPublished / SupportedRunStylesPublished — those are
  /// the Unit's mode/run-style CAPABILITY, read every snapshot to populate the
  /// mode dropdown, and are cyclically published by design (never obscured).
  /// Excluding them left the dropdown showing only the current mode.
  static const Set<String> configLeaves = {
    'Name',
    'DisplayNameKey',
    'DescriptionKey',
    'ModuleType',
    'TileEnable',
    'ControlDomainId',
    'StallTime',
    'CatalogCount',
    'AvailableModelCount',
    'MetaCount',
    'TypeId',
    'ParentIdx',
    'ChannelCount',
    'Address',
    'Path',
    'ModulePath',
    'Dir',
    'Kind',
    'Unit',
  };

  /// Reserved on-demand scope key for the fieldbus topology (owned by no module).
  static const String fieldbusScope = '#fieldbus';

  static FieldTier classify(String browsePath) {
    final segments = browsePath.split('/');
    var configContainer = false;
    var slowContainer = false;
    for (final raw in segments) {
      final seg = _stripIndex(raw);
      if (seg.isEmpty) continue;
      if (onDemandContainers.contains(seg)) return FieldTier.onDemand;
      if (slowContainers.contains(seg)) slowContainer = true;
      if (configContainers.contains(seg)) configContainer = true;
    }
    // Slow before live so a Safety/ControlPower facet nested under a live-ish
    // parent (e.g. Domain/Safety) is still demoted to the heartbeat.
    if (slowContainer) return FieldTier.slow;
    // liveContainers checked after onDemand/slow so a ring nested under a live
    // container (e.g. Profiler/History) is still gated on-demand.
    for (final raw in segments) {
      final seg = _stripIndex(raw);
      if (seg.isEmpty) continue;
      if (liveContainers.contains(seg)) return FieldTier.live;
    }
    if (configContainer) return FieldTier.config;
    final leaf = _stripIndex(segments.isEmpty ? '' : segments.last);
    if (configLeaves.contains(leaf)) return FieldTier.config;
    return FieldTier.live; // default: fresh every snapshot
  }

  /// The activation scope that owns an on-demand [browsePath] within [forestRoots]
  /// (the discovered root-Unit browse bases), or `null` if it is not on-demand.
  ///
  /// - fieldbus topology → [fieldbusScope] (one shared scope; the bus page owns it)
  /// - everything else → the browse base of the root Unit the path belongs to, so
  ///   a module detail page activates only its own root's drill-down data.
  static String? onDemandScopeOf(
      String browsePath, Iterable<String> forestRoots) {
    if (classify(browsePath) != FieldTier.onDemand) return null;
    for (final raw in browsePath.split('/')) {
      if (_stripIndex(raw) == 'Topology') return fieldbusScope;
    }
    // Longest matching root base wins (nested roots would prefix-collide).
    String? best;
    for (final root in forestRoots) {
      if ((browsePath == root || browsePath.startsWith('$root/')) &&
          (best == null || root.length > best.length)) {
        best = root;
      }
    }
    return best;
  }

  static String _stripIndex(String segment) {
    final bracket = segment.indexOf('[');
    final base = bracket >= 0 ? segment.substring(0, bracket) : segment;
    if (base.isNotEmpty && int.tryParse(base) != null) return '';
    return base;
  }
}
