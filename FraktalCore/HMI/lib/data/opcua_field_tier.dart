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
    // §3.13 the per-leg step cursor: ~30 leaves, and it is what makes the chart
    // correct the moment its tab opens rather than after the first on-demand read.
    // The 128-row tables it points INTO stay on-demand.
    'ActiveSteps',
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
    // §3.13 flow-chart rows. Bounded at MAX_SEQUENCE_STEPS (128) x 17 fields = 2176
    // nodes per Unit, and they only feed the Sequence tab. Cyclic they would dominate
    // the fast read exactly like the rings above; SequenceStepCount, CurrentStep*
    // and SequenceViewEnabled stay live at the module root, which is all the rest of
    // the UI needs to know the chart exists.
    'SequenceSteps',
    // §6.9 error/message notes for those rows: same view, same lifetime.
    'SequenceAnnotations',
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
    // §3.13 static half of each flow-chart row. Marked `OPC.UA.DA := '0'` on
    // FB_UnitBase, so TF6100 never publishes it; the manifest re-serves the same
    // fields under the LIVE `SequenceSteps/SequenceSteps[i]/…` paths, which is
    // what the mapper reads. Nothing in the HMI ever names `SequenceStepDef`.
    'SequenceStepDef',
  };

  /// Config containers the §3.10.2 manifest **re-serves**, so the cyclic read
  /// owes them nothing (Core §3.10.2, OPCUA_TRANSPORT "config" tier).
  ///
  /// This is the container half of the config tier and it is matched on a path
  /// SEGMENT, which is why it can be excluded when [configLeaves] cannot: a
  /// container name is unambiguous, whereas the leaf list is a heuristic that
  /// also catches cyclically-required fields (`Status/Name`, the
  /// `SupportedModes` capability) whose exclusion emptied the module tree and
  /// the mode dropdown. Every entry here was checked against `M_AppendConfig`:
  /// the manifest appends the identical browse paths (`Nameplate/*`,
  /// `Catalog/Catalog[i]/*`, `AlarmLog/Meta/Meta[i]/*`, `ModePolicy/*`,
  /// `AvailableModels/AvailableModels[i]/ModelCode`), so excluding them makes
  /// ADS read exactly what TF6100 publishes instead of the whole symbol table.
  static const Set<String> manifestContainers = {
    'Nameplate',
    'Catalog',
    'AvailableModels',
    'ModePolicy',
    'Meta',
    'SequenceStepDef',
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

  /// Leaves that stay LIVE even inside an on-demand subtree (§10.5.1).
  ///
  /// The fieldbus topology is on-demand because its identity, addressing and
  /// diagnostic text are large and view-gated — but a channel's VALUE is the one
  /// thing an operator watches without opening the bus page (an interlock that
  /// will not clear, a sensor that never comes on). It is one leaf per channel,
  /// so promoting it costs a fraction of the subtree it lives in while everything
  /// around it — `Address`, `Path`, `Diagnostic`, `Forced`, `Quality` — stays
  /// gated. Checked BEFORE the container rules, which is what lets it win.
  static const Set<String> liveLeaves = {
    'BoolValue', // digital channel state
    'AnalogValue', // the analog channel's equivalent — same role, same argument
  };

  /// True when [browsePath] lies inside a subtree the PLC marks
  /// `OPC.UA.DA := '0'` and the §3.10.2 manifest re-serves under the same browse
  /// paths — so the cyclic read may skip it and still show a complete tree.
  ///
  /// Container-matched on purpose: see [manifestContainers] for why the leaf
  /// half of the config tier stays cyclic.
  static bool isManifestServed(String browsePath) {
    for (final raw in browsePath.split('/')) {
      if (manifestContainers.contains(_stripIndex(raw))) return true;
    }
    return false;
  }

  /// True when [browsePath] sits under a program container that owns a
  /// discovered root Unit (`PLC1/MAIN`) but outside every root in [rootBases].
  ///
  /// TF6100 TMC-Filtered publication starts at the instances explicitly marked
  /// `{attribute 'OPC.UA.DA' := '1'}` — the deployed root Units — and their
  /// inherited children (OPCUA_TRANSPORT, Part II §3.10). ADS has no such
  /// filter: `SYM_UPLOAD` exposes the entire program, so the direct transport
  /// discovers the composition root's private instances too — the part carrier
  /// and its result ring, the I/O driver and its bus health, the recipe
  /// catalogue, the config store, the access provider, the HAL structs and the
  /// simulation controls. None of that is in the published contract, no widget
  /// reads it, and over OPC UA it does not exist. Reading it every cycle is the
  /// direct transport inventing work for itself.
  ///
  /// Discovery still enumerates these leaves, so they stay writable by path —
  /// which is what `MAIN.FieldbusViewActive`, the §10.5.1 demand gate, needs.
  ///
  /// The containers are derived from the discovered roots rather than matched
  /// against the name `MAIN`, so this holds for any program name and for a
  /// forest whose roots sit side by side (Core §3.1a). With no roots discovered
  /// yet, nothing is outside them: the first snapshot reads everything, which is
  /// how the roots become known in the first place.
  static bool isOutsidePublishedRoots(
      String browsePath, Iterable<String> rootBases) {
    var underContainer = false;
    for (final base in rootBases) {
      final cut = base.lastIndexOf('/');
      if (cut <= 0) continue;
      if (browsePath.startsWith('${base.substring(0, cut)}/')) {
        underContainer = true;
        break;
      }
    }
    if (!underContainer) return false;
    for (final base in rootBases) {
      if (browsePath == base || browsePath.startsWith('$base/')) return false;
    }
    return true;
  }

  static FieldTier classify(String browsePath) {
    final segments = browsePath.split('/');
    if (liveLeaves.contains(_stripIndex(segments.isEmpty ? '' : segments.last))) {
      return FieldTier.live;
    }
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
