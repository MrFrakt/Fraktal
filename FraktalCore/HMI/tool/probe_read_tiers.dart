// Shared probe helper: put a bare session client into the SAME read tiers the
// operator HMI uses.
//
// A probe that connects and calls snapshot() measures a client nobody ships.
// OpcUaRepository classifies the discovered contract and pushes an excluded set
// to the transport before it ever polls, so an unconfigured probe reads the
// whole ADS symbol table — including the composition root's private instances
// and every manifest-served subtree — and reports a cyclic cost several times
// the real one. That over-report is not conservative: it points the next fix at
// subtrees the HMI already skips.
//
// This mirrors OpcUaRepository._maybeUpdatePathTiers. It deliberately does NOT
// re-implement the classification — same classifier, same order — so the two
// cannot drift.
import 'package:fraktal_hmi/data/opcua_field_tier.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart';

/// Discovered root-Unit browse bases: a module whose `Status/Name` is published
/// and whose base has no other module base above it. The repository takes these
/// from the mapper's projection; a probe derives them from the raw paths so it
/// stays independent of the mapper.
List<String> discoveredRootBases(Map<String, Object?> snapshot) {
  final paths = snapshot['paths'];
  if (paths is! List) return const [];
  final bases = <String>{};
  for (final raw in paths) {
    final path = '$raw';
    if (!path.endsWith('/Status/Name')) continue;
    bases.add(path.substring(0, path.length - '/Status/Name'.length));
  }
  // Keep only the outermost: a child module publishes Status/Name too.
  final roots = <String>[];
  for (final base in bases) {
    if (bases.any((other) => other != base && base.startsWith('$other/'))) {
      continue;
    }
    roots.add(base);
  }
  return roots..sort();
}

/// The paths the HMI keeps OUT of its cyclic snapshot, in repository order.
List<String> excludedPathsFor(Map<String, Object?> snapshot) {
  final paths = snapshot['paths'];
  if (paths is! List) return const [];
  final roots = discoveredRootBases(snapshot);
  final excluded = <String>[];
  for (final raw in paths) {
    final path = '$raw';
    if (OpcUaFieldTier.isOutsidePublishedRoots(path, roots) ||
        OpcUaFieldTier.isManifestServed(path) ||
        OpcUaFieldTier.classify(path) == FieldTier.onDemand) {
      excluded.add(path);
    }
  }
  return excluded;
}

/// Applies the HMI's read tiers to [client] from a discovery [snapshot], and
/// returns a one-line summary of what it took out.
Future<String> applyReadTiers(
    OpcUaSessionClient client, Map<String, Object?> snapshot) async {
  final paths = snapshot['paths'];
  final discovered = paths is List ? paths.length : 0;
  final excluded = excludedPathsFor(snapshot);
  await client.setExcludedPaths(excluded);
  final summary = '[tier] discovered=$discovered '
      'cyclic=${discovered - excluded.length} excluded=${excluded.length} '
      'roots=${discoveredRootBases(snapshot).join(', ')}';
  // ignore: avoid_print
  print(summary);
  return summary;
}
