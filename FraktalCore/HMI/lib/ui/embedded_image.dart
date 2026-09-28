/// Images embedded in a module layout as base64 (image controls, the Overview
/// background), decoded ONCE and reused across rebuilds.
///
/// A layout widget rebuilds every time the connection publishes - once a second
/// on the simulator, faster on a live PLC. Decoding the base64 and handing
/// `Image.memory` a fresh byte buffer on every build is a guaranteed image-cache
/// miss (a MemoryImage is identified by its buffer), so each rebuild re-decoded
/// the full-resolution photo; a camera JPEG froze the HMI right after Publish.
/// Here the provider is created once per embedded string and decoded no larger
/// than it can be shown.
library;

import 'dart:collection';
import 'dart:convert';

import 'package:flutter/widgets.dart';

import '../diagnostics/hmi_log.dart';

// Keyed by the IDENTITY of the base64 string: a published layout keeps the same
// string instance across rebuilds, so a lookup never hashes or compares
// megabytes of text. A layout reloaded from storage is a new instance and is
// decoded once more, which is correct. A null value remembers undecodable data.
final LinkedHashMap<String, ImageProvider?> _decoded =
    LinkedHashMap<String, ImageProvider?>(
        equals: identical, hashCode: identityHashCode);

/// Bounded so a layout history full of replaced images cannot pin them all.
const int kEmbeddedImageCacheEntries = 16;

/// The provider for an embedded image, decoded at most [maxWidth] pixels wide
/// (never upscaled). Null for an empty or undecodable image.
ImageProvider? embeddedImage(String base64, {required int maxWidth}) {
  if (base64.isEmpty) return null;
  if (_decoded.containsKey(base64)) {
    final hit = _decoded.remove(base64);
    _decoded[base64] = hit; // most recently used last
    return hit;
  }
  ImageProvider? provider;
  hmiLog('image: new decode of ${base64.length ~/ 1024} KiB base64 '
      'at max ${maxWidth}px');
  try {
    provider = ResizeImage(
      MemoryImage(base64Decode(base64)),
      width: maxWidth,
      policy: ResizeImagePolicy.fit,
      allowUpscaling: false,
    );
  } on FormatException {
    provider = null;
  }
  _decoded[base64] = provider;
  while (_decoded.length > kEmbeddedImageCacheEntries) {
    _decoded.remove(_decoded.keys.first);
  }
  return provider;
}
