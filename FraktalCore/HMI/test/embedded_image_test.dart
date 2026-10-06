// Regression: publishing a layout with an image control froze the HMI. The
// control base64-decoded the image and built a fresh Image.memory on EVERY
// rebuild - once a second on the simulator - so Flutter's image cache (keyed by
// the byte buffer) missed every time and re-decoded the full-resolution photo.
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/ui/embedded_image.dart';

// A 1x1 transparent PNG.
const _png =
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

void main() {
  test('the same embedded image yields the same provider on every rebuild', () {
    final first = embeddedImage(_png, maxWidth: 1600);
    final again = embeddedImage(_png, maxWidth: 1600);
    expect(first, isNotNull);
    expect(identical(first, again), isTrue,
        reason: 'a new provider per build is an image-cache miss per build');
  });

  test('decoding is bounded to the display width and never upscales', () {
    final provider = embeddedImage(String.fromCharCodes(_png.codeUnits),
        maxWidth: 1600);
    expect(provider, isA<ResizeImage>());
    final resize = provider! as ResizeImage;
    expect(resize.width, 1600);
    expect(resize.allowUpscaling, isFalse);
  });

  test('undecodable or empty data yields no image instead of throwing', () {
    expect(embeddedImage('', maxWidth: 1600), isNull);
    expect(embeddedImage('not base64 at all!', maxWidth: 1600), isNull);
  });

  test('the cache is bounded', () {
    // Distinct string instances, each a valid image.
    final base = base64Decode(_png);
    for (var i = 0; i < kEmbeddedImageCacheEntries + 8; i++) {
      final fresh = base64Encode(List<int>.from(base));
      expect(embeddedImage(fresh, maxWidth: 800), isNotNull);
    }
    // The first probe string was evicted long ago; asking again still works.
    expect(embeddedImage(String.fromCharCodes(_png.codeUnits), maxWidth: 800),
        isNotNull);
  });
}
