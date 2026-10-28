/// Shared parent lookup for publication paths, including array row containers.
/// Build once so indexed row lookup is O(1); scanning a large value map for
/// each row previously blocked the UI and command acknowledgement polling.
Set<String> buildBrowseParentPaths(Iterable<String> paths) {
  final parents = <String>{};
  for (final path in paths) {
    var cut = path.lastIndexOf('/');
    while (cut > 0) {
      final parent = path.substring(0, cut);
      if (!parents.add(parent)) break;
      cut = parent.lastIndexOf('/');
    }
  }
  return parents;
}

/// Use a discovered compact array container for manifest metadata. Static-only
/// arrays keep their original paths when no published row proves that form.
String resolveManifestBrowsePath(
    String base, String item, Set<String> parents) {
  final segments = base.split('/');
  for (final segment in item.split('/')) {
    final bracket = segment.indexOf('[');
    if (bracket > 0 && segments.last == segment.substring(0, bracket)) {
      final compact =
          [...segments.take(segments.length - 1), segment].join('/');
      if (parents.contains(compact)) segments.removeLast();
    }
    segments.add(segment);
  }
  return segments.join('/');
}
