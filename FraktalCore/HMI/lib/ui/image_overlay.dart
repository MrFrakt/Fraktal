/// Placing controls on a tab's machine picture: the ADMIN editor.
///
/// A control is dragged from the palette (a new one) or from the tab's control
/// list (an existing one) and dropped where it belongs on the picture; a
/// placed control is moved by dragging it and resized from its corner. Every
/// position is a fraction of the image's painted box (background_canvas.dart),
/// so what the author places on a 10" desk monitor lands on the same sensor on
/// a 21" cabinet panel.
library;

import 'dart:math' as math;

import 'package:flutter/gestures.dart' show DragStartBehavior;
import 'package:flutter/material.dart';

import '../content/module_layout.dart';
import '../localization/localized_text.dart';
import 'background_canvas.dart';

/// The size (fractions of the image) a new control of [kind] starts at.
Size defaultOverlaySize(ModuleControlKind kind) => switch (kind) {
      ModuleControlKind.shape => const Size(0.12, 0.10),
      ModuleControlKind.level => const Size(0.06, 0.30),
      ModuleControlKind.indicator => const Size(0.04, 0.04),
      ModuleControlKind.value => const Size(0.16, 0.08),
      ModuleControlKind.text => const Size(0.18, 0.07),
      ModuleControlKind.button => const Size(0.18, 0.09),
      _ => const Size(0.25, 0.18),
    };

/// The kinds offered in the palette: the ones that read well on a picture.
const List<ModuleControlKind> kOverlayPaletteKinds = [
  ModuleControlKind.shape,
  ModuleControlKind.level,
  ModuleControlKind.indicator,
  ModuleControlKind.value,
  ModuleControlKind.text,
  ModuleControlKind.button,
];

/// What a drag onto the picture carries: a new control of a kind, or an
/// existing control (by id) that is not on the picture yet.
sealed class OverlayDrop {
  const OverlayDrop();
}

class NewControlDrop extends OverlayDrop {
  final ModuleControlKind kind;
  const NewControlDrop(this.kind);
}

class ExistingControlDrop extends OverlayDrop {
  final ModuleControlDefinition control;
  const ExistingControlDrop(this.control);
}

/// A drag source for [data]. The pointer is the anchor, so the drop lands the
/// control's centre exactly where the author let go.
class OverlayDragSource extends StatelessWidget {
  final OverlayDrop data;
  final Widget child;
  final Widget feedback;

  const OverlayDragSource({
    super.key,
    required this.data,
    required this.child,
    required this.feedback,
  });

  @override
  Widget build(BuildContext context) => Draggable<OverlayDrop>(
        data: data,
        dragAnchorStrategy: pointerDragAnchorStrategy,
        feedback: FractionalTranslation(
          translation: const Offset(-0.5, -0.5),
          child: Material(
            elevation: 6,
            borderRadius: BorderRadius.circular(10),
            child: feedback,
          ),
        ),
        child: child,
      );
}

/// The editing layer over the picture: drop target, one frame per placed
/// control, and the selected control's handles.
class PlacementEditor extends StatefulWidget {
  /// The image's painted rect, in this layer's coordinates.
  final Rect image;
  final List<ModuleControlDefinition> controls;
  final Widget Function(ModuleControlDefinition control) render;
  final void Function(String id, ModulePlacement? placement)? onPlace;
  final void Function(ModuleControlKind kind, ModulePlacement placement)?
      onAddAt;
  final ValueChanged<ModuleControlDefinition>? onEdit;
  final ValueChanged<String>? onRemove;

  /// Z-order (LOCALIZATION §7.2): drawing order is control order, so "front"
  /// moves the control last and "back" first.
  final void Function(String id, bool front)? onRestack;

  const PlacementEditor({
    super.key,
    required this.image,
    required this.controls,
    required this.render,
    this.onPlace,
    this.onAddAt,
    this.onEdit,
    this.onRemove,
    this.onRestack,
  });

  @override
  State<PlacementEditor> createState() => _PlacementEditorState();
}

class _PlacementEditorState extends State<PlacementEditor> {
  /// Placements being dragged or resized. Written to the draft once, when the
  /// gesture ends: one undo step per move, not one per pointer event.
  final Map<String, ModulePlacement> _live = {};
  String? _selected;

  ModulePlacement _placementOf(ModuleControlDefinition control) =>
      _live[control.id] ?? control.placement!;

  void _drop(DragTargetDetails<OverlayDrop> details) {
    final box = context.findRenderObject();
    if (box is! RenderBox) return;
    final local = box.globalToLocal(details.offset);
    final image = widget.image;
    switch (details.data) {
      case NewControlDrop(:final kind):
        final size = defaultOverlaySize(kind);
        widget.onAddAt?.call(
          kind,
          placementCenteredAt(local, image,
              width: size.width, height: size.height),
        );
      case ExistingControlDrop(:final control):
        final size = defaultOverlaySize(control.kind);
        widget.onPlace?.call(
          control.id,
          placementCenteredAt(local, image,
              width: size.width, height: size.height),
        );
        setState(() => _selected = control.id);
    }
  }

  void _move(ModuleControlDefinition control, Offset delta) {
    final current = _placementOf(control);
    setState(() {
      _selected = control.id;
      _live[control.id] = ModulePlacement(
        x: current.x + delta.dx / widget.image.width,
        y: current.y + delta.dy / widget.image.height,
        width: current.width,
        height: current.height,
      ).clamped();
    });
  }

  void _resize(ModuleControlDefinition control, Offset delta) {
    final current = _placementOf(control);
    setState(() {
      _live[control.id] = ModulePlacement(
        x: current.x,
        y: current.y,
        width: current.width + delta.dx / widget.image.width,
        height: current.height + delta.dy / widget.image.height,
      ).clamped();
    });
  }

  void _commit(ModuleControlDefinition control) {
    final done = _live.remove(control.id);
    if (done != null) widget.onPlace?.call(control.id, done);
    setState(() {});
  }

  @override
  Widget build(BuildContext context) {
    final colors = Theme.of(context).colorScheme;
    final image = widget.image;
    final selected =
        widget.controls.where((item) => item.id == _selected).firstOrNull;
    return LayoutBuilder(
        builder: (context, constraints) => Stack(children: [
              Positioned.fill(
                child: DragTarget<OverlayDrop>(
                  onAcceptWithDetails: _drop,
                  builder: (context, candidates, _) => GestureDetector(
                    behavior: HitTestBehavior.opaque,
                    onTap: () => setState(() => _selected = null),
                    child: CustomPaint(
                      painter: _ImageOutlinePainter(
                        image: image,
                        color: colors.primary,
                        highlighted: candidates.isNotEmpty,
                      ),
                    ),
                  ),
                ),
              ),
              for (final control in widget.controls)
                Positioned.fromRect(
                  rect: placementRect(_placementOf(control), image),
                  child: GestureDetector(
                    key: ValueKey('placed-${control.id}'),
                    behavior: HitTestBehavior.opaque,
                    // From the pointer-down, not after the touch slop: the
                    // control stays under the finger instead of trailing it.
                    dragStartBehavior: DragStartBehavior.down,
                    onTap: () => setState(() => _selected = control.id),
                    onPanUpdate: (details) => _move(control, details.delta),
                    onPanEnd: (_) => _commit(control),
                    onPanCancel: () => _commit(control),
                    child: Stack(fit: StackFit.expand, children: [
                      IgnorePointer(child: widget.render(control)),
                      IgnorePointer(
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            border: Border.all(
                              color: control.id == _selected
                                  ? colors.primary
                                  : colors.primary.withValues(alpha: 0.5),
                              width: control.id == _selected ? 2 : 1,
                            ),
                          ),
                        ),
                      ),
                    ]),
                  ),
                ),
              if (selected != null)
                ..._handles(context, selected, constraints.biggest),
            ]));
  }

  List<Widget> _handles(
      BuildContext context, ModuleControlDefinition control, Size layer) {
    final colors = Theme.of(context).colorScheme;
    final rect = placementRect(_placementOf(control), widget.image);
    // Kept inside the layer: a handle outside its parent's box is never hit.
    double within(double value, double extent, double size) =>
        value.clamp(0.0, math.max(0.0, extent - size));
    const toolbarHeight = 40.0;
    const toolbarWidth = 212.0;
    final toolbarTop = rect.top >= toolbarHeight + 4
        ? rect.top - toolbarHeight - 4
        : rect.bottom + 4;
    return [
      Positioned(
        left: within(rect.right - 14, layer.width, 28),
        top: within(rect.bottom - 14, layer.height, 28),
        width: 28,
        height: 28,
        child: GestureDetector(
          key: ValueKey('resize-${control.id}'),
          behavior: HitTestBehavior.opaque,
          dragStartBehavior: DragStartBehavior.down,
          onPanUpdate: (details) => _resize(control, details.delta),
          onPanEnd: (_) => _commit(control),
          onPanCancel: () => _commit(control),
          child: Center(
            child: Container(
              width: 14,
              height: 14,
              decoration: BoxDecoration(
                color: colors.primary,
                shape: BoxShape.circle,
                border: Border.all(color: colors.onPrimary, width: 2),
              ),
            ),
          ),
        ),
      ),
      Positioned(
        left: within(rect.left, layer.width, toolbarWidth),
        top: within(toolbarTop, layer.height, toolbarHeight),
        height: toolbarHeight,
        child: Material(
          elevation: 4,
          borderRadius: BorderRadius.circular(8),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            IconButton(
              tooltip: context.tr('std.common.edit'),
              visualDensity: VisualDensity.compact,
              onPressed: () => widget.onEdit?.call(control),
              icon: const Icon(Icons.edit_outlined, size: 18),
            ),
            IconButton(
              tooltip: context.tr('std.module.editor.bringToFront'),
              visualDensity: VisualDensity.compact,
              onPressed: () => widget.onRestack?.call(control.id, true),
              icon: const Icon(Icons.flip_to_front, size: 18),
            ),
            IconButton(
              tooltip: context.tr('std.module.editor.sendToBack'),
              visualDensity: VisualDensity.compact,
              onPressed: () => widget.onRestack?.call(control.id, false),
              icon: const Icon(Icons.flip_to_back, size: 18),
            ),
            IconButton(
              tooltip: context.tr('std.module.editor.removeFromImage'),
              visualDensity: VisualDensity.compact,
              onPressed: () {
                setState(() => _selected = null);
                widget.onPlace?.call(control.id, null);
              },
              icon: const Icon(Icons.move_down, size: 18),
            ),
            IconButton(
              tooltip: context.tr('std.common.delete'),
              visualDensity: VisualDensity.compact,
              onPressed: () {
                setState(() => _selected = null);
                widget.onRemove?.call(control.id);
              },
              icon: const Icon(Icons.delete_outline, size: 18),
            ),
          ]),
        ),
      ),
    ];
  }
}

/// While editing, the picture's bounds are drawn so the author sees exactly
/// which area positions are relative to (letterbox bars are not part of it).
class _ImageOutlinePainter extends CustomPainter {
  final Rect image;
  final Color color;
  final bool highlighted;

  const _ImageOutlinePainter({
    required this.image,
    required this.color,
    required this.highlighted,
  });

  @override
  void paint(Canvas canvas, Size size) {
    if (highlighted) {
      canvas.drawRect(image, Paint()..color = color.withValues(alpha: 0.10));
    }
    canvas.drawRect(
      image.deflate(0.5),
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = highlighted ? 2 : 1
        ..color = color.withValues(alpha: highlighted ? 0.9 : 0.45),
    );
  }

  @override
  bool shouldRepaint(_ImageOutlinePainter old) =>
      old.image != image ||
      old.color != color ||
      old.highlighted != highlighted;
}
