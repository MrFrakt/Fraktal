/// A flow of cards across a fixed number of equal columns. Each child goes
/// into whichever column is currently shortest (ties go left), so the columns
/// stack independently: a tall card never leaves a gap beside it the way a
/// row-aligned grid does. A child that lays out with no height takes no place.
library;

import 'dart:math' as math;

import 'package:flutter/rendering.dart';
import 'package:flutter/widgets.dart';

class FlowColumns extends MultiChildRenderObjectWidget {
  final int columns;
  final double gap;
  const FlowColumns({
    super.key,
    required this.columns,
    this.gap = 12,
    required super.children,
  });

  @override
  RenderFlowColumns createRenderObject(BuildContext context) =>
      RenderFlowColumns(columns: columns, gap: gap);

  @override
  void updateRenderObject(BuildContext context, RenderFlowColumns renderObject) {
    renderObject
      ..columns = columns
      ..gap = gap;
  }
}

class FlowColumnsParentData extends ContainerBoxParentData<RenderBox> {}

class RenderFlowColumns extends RenderBox
    with
        ContainerRenderObjectMixin<RenderBox, FlowColumnsParentData>,
        RenderBoxContainerDefaultsMixin<RenderBox, FlowColumnsParentData> {
  RenderFlowColumns({required int columns, required double gap})
      : _columns = math.max(1, columns),
        _gap = gap;

  int _columns;
  set columns(int value) {
    value = math.max(1, value);
    if (value == _columns) return;
    _columns = value;
    markNeedsLayout();
  }

  double _gap;
  set gap(double value) {
    if (value == _gap) return;
    _gap = value;
    markNeedsLayout();
  }

  @override
  void setupParentData(RenderBox child) {
    if (child.parentData is! FlowColumnsParentData) {
      child.parentData = FlowColumnsParentData();
    }
  }

  double _columnWidth(double width) =>
      math.max(0, (width - _gap * (_columns - 1)) / _columns);

  /// Places every child and returns the height the flow needs. [place] is
  /// false for a dry layout, which measures without moving anything.
  double _flow(double width, {required bool place}) {
    final columnWidth = _columnWidth(width);
    final heights = List<double>.filled(_columns, 0);
    final used = List<bool>.filled(_columns, false);
    var child = firstChild;
    while (child != null) {
      final data = child.parentData! as FlowColumnsParentData;
      final constraints = BoxConstraints.tightFor(width: columnWidth);
      final Size size;
      if (place) {
        child.layout(constraints, parentUsesSize: true);
        size = child.size;
      } else {
        size = child.getDryLayout(constraints);
      }
      if (size.height > 0) {
        var column = 0;
        for (var i = 1; i < _columns; i++) {
          if (heights[i] < heights[column]) column = i;
        }
        final top = heights[column] + (used[column] ? _gap : 0);
        if (place) {
          data.offset = Offset(column * (columnWidth + _gap), top);
        }
        heights[column] = top + size.height;
        used[column] = true;
      } else if (place) {
        data.offset = Offset.zero;
      }
      child = data.nextSibling;
    }
    return heights.fold<double>(0, math.max);
  }

  @override
  void performLayout() {
    final width = constraints.maxWidth;
    size = constraints.constrain(Size(width, _flow(width, place: true)));
  }

  @override
  Size computeDryLayout(covariant BoxConstraints constraints) {
    final width = constraints.maxWidth;
    return constraints.constrain(Size(width, _flow(width, place: false)));
  }

  @override
  void paint(PaintingContext context, Offset offset) =>
      defaultPaint(context, offset);

  @override
  bool hitTestChildren(BoxHitTestResult result, {required Offset position}) =>
      defaultHitTestChildren(result, position: position);
}
