/// A tab's background image, and the geometry that pins controls to it.
///
/// A control placed on a machine picture must stay on the sensor, door or tank
/// it annotates whatever the panel size, the fit (contain/cover/fit-width/
/// fit-height), the alignment or the margins. So an overlay position is a
/// fraction of the image's own PAINTED box ([paintedImageRect]), computed with
/// exactly the arithmetic Flutter's `paintImage` uses to draw it - never a
/// fraction of the tab, which drifts off the picture the moment it letterboxes.
library;

import 'package:flutter/material.dart';

import '../content/module_layout.dart';
import 'embedded_image.dart';

/// Where [imageSize] is painted in [box] with [fit] and [alignment]: the rect
/// of the WHOLE image, which is larger than [box] (and clipped to it) when
/// `cover` crops. Mirrors `paintImage` (painting/decoration_image.dart).
Rect paintedImageRect({
  required Size imageSize,
  required Rect box,
  required BoxFit fit,
  required Alignment alignment,
}) {
  if (imageSize.isEmpty || box.isEmpty) return Rect.zero;
  final fitted = applyBoxFit(fit, imageSize, box.size);
  final destination = alignment.inscribe(fitted.destination, box);
  final source = alignment.inscribe(fitted.source, Offset.zero & imageSize);
  final scaleX = destination.width / source.width;
  final scaleY = destination.height / source.height;
  return Rect.fromLTWH(
    destination.left - source.left * scaleX,
    destination.top - source.top * scaleY,
    imageSize.width * scaleX,
    imageSize.height * scaleY,
  );
}

/// [placement] in canvas pixels, given the painted [image] rect.
Rect placementRect(ModulePlacement placement, Rect image) => Rect.fromLTWH(
      image.left + placement.x * image.width,
      image.top + placement.y * image.height,
      placement.width * image.width,
      placement.height * image.height,
    );

/// A placement [width] x [height] (fractions of the image) centred on the
/// canvas point [center].
ModulePlacement placementCenteredAt(
  Offset center,
  Rect image, {
  required double width,
  required double height,
}) =>
    ModulePlacement(
      x: (center.dx - image.left) / image.width - width / 2,
      y: (center.dy - image.top) / image.height - height / 2,
      width: width,
      height: height,
    ).clamped();

BoxFit backgroundBoxFit(ModuleBackgroundFit fit) => switch (fit) {
      ModuleBackgroundFit.contain => BoxFit.contain,
      ModuleBackgroundFit.cover => BoxFit.cover,
      ModuleBackgroundFit.fitWidth => BoxFit.fitWidth,
      ModuleBackgroundFit.fitHeight => BoxFit.fitHeight,
    };

Alignment backgroundAlignment(ModuleBackgroundPosition position) =>
    switch (position) {
      ModuleBackgroundPosition.topLeft => Alignment.topLeft,
      ModuleBackgroundPosition.topCenter => Alignment.topCenter,
      ModuleBackgroundPosition.topRight => Alignment.topRight,
      ModuleBackgroundPosition.centerLeft => Alignment.centerLeft,
      ModuleBackgroundPosition.center => Alignment.center,
      ModuleBackgroundPosition.centerRight => Alignment.centerRight,
      ModuleBackgroundPosition.bottomLeft => Alignment.bottomLeft,
      ModuleBackgroundPosition.bottomCenter => Alignment.bottomCenter,
      ModuleBackgroundPosition.bottomRight => Alignment.bottomRight,
    };

/// Draws [background], then [child] over it, then [overlay] - built with the
/// image's painted rect so it can position controls on the picture. The
/// overlay is clipped to the image's box and passes taps through wherever it
/// has no control, so [child] stays usable.
class BackgroundCanvas extends StatefulWidget {
  final ModuleTabBackground background;
  final Widget? child;
  final Widget Function(BuildContext context, Rect imageRect)? overlay;

  const BackgroundCanvas({
    super.key,
    required this.background,
    this.child,
    this.overlay,
  });

  @override
  State<BackgroundCanvas> createState() => _BackgroundCanvasState();
}

class _BackgroundCanvasState extends State<BackgroundCanvas> {
  ImageStream? _stream;
  ImageStreamListener? _listener;
  Size? _imageSize;

  ImageProvider? get _provider =>
      embeddedImage(widget.background.imageBase64, maxWidth: 2560);

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _resolve();
  }

  @override
  void didUpdateWidget(covariant BackgroundCanvas oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (!identical(
        oldWidget.background.imageBase64, widget.background.imageBase64)) {
      _resolve();
    }
  }

  @override
  void dispose() {
    _stopListening();
    super.dispose();
  }

  void _stopListening() {
    final listener = _listener;
    if (listener != null) _stream?.removeListener(listener);
    _stream = null;
    _listener = null;
  }

  // Only the overlay needs the image's size; the image itself draws without it.
  void _resolve() {
    if (widget.overlay == null) return;
    final provider = _provider;
    if (provider == null) {
      _stopListening();
      _imageSize = null;
      return;
    }
    final stream = provider.resolve(createLocalImageConfiguration(context));
    if (stream.key == _stream?.key) return;
    _stopListening();
    final listener = ImageStreamListener((info, _) {
      final size =
          Size(info.image.width.toDouble(), info.image.height.toDouble());
      info.dispose();
      if (mounted && size != _imageSize) setState(() => _imageSize = size);
    });
    stream.addListener(listener);
    _stream = stream;
    _listener = listener;
  }

  @override
  Widget build(BuildContext context) {
    final background = widget.background;
    final image = _provider;
    return LayoutBuilder(builder: (context, constraints) {
      final size = constraints.biggest;
      final box = Rect.fromLTRB(
        background.marginLeft,
        background.marginTop,
        size.width - background.marginRight,
        size.height - background.marginBottom,
      );
      final fit = backgroundBoxFit(background.fit);
      final alignment = backgroundAlignment(background.position);
      final imageSize = _imageSize;
      final overlay = widget.overlay;
      return Stack(
        fit: StackFit.expand,
        children: [
          if (image != null && !box.isEmpty)
            Positioned.fromRect(
              rect: box,
              child: Image(
                image: image,
                fit: fit,
                alignment: alignment,
                gaplessPlayback: true,
              ),
            ),
          if (widget.child != null) widget.child!,
          if (overlay != null && imageSize != null && !box.isEmpty)
            Positioned.fromRect(
              rect: box,
              child: ClipRect(
                child: Builder(
                  builder: (context) => overlay(
                    context,
                    // In the box's own coordinates.
                    paintedImageRect(
                      imageSize: imageSize,
                      box: Offset.zero & box.size,
                      fit: fit,
                      alignment: alignment,
                    ),
                  ),
                ),
              ),
            ),
        ],
      );
    });
  }
}
