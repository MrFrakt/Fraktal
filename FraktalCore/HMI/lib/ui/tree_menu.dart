/// The shrinkable left tree (Core 3.13): walks the forest, expands/collapses,
/// and implements the EVENT PATH HIGHLIGHT — every ancestor from the root down
/// to the event's source tints with the subtree's highest-severity active event
/// (error > warning > info); the source node renders strongest.
library;

import '../localization/localized_text.dart';
import 'package:flutter/material.dart';
import '../domain/module_node.dart';
import '../domain/types.dart';
import '../state/app_state.dart';
import 'app_theme.dart';

class TreeMenu extends StatelessWidget {
  final AppState app;
  const TreeMenu({super.key, required this.app});

  @override
  Widget build(BuildContext context) {
    final collapsed = app.railCollapsed;
    return ClipRect(
      child: AnimatedContainer(
        key: const Key('navigation-tree-animated-width'),
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOutCubic,
        width: collapsed ? 64 : 300,
        child: LayoutBuilder(
          builder: (context, constraints) {
            // During the width tween the target state changes immediately.
            // Render from the width actually available so the expanded header
            // and indented rows are never laid out inside the 64 px rail.
            final compact = constraints.maxWidth < 180;
            return Material(
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              child: Column(
                children: [
                  _header(context, compact),
                  const Divider(height: 1),
                  Expanded(
                    child: ListView(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      children: [
                        for (final root in app.visibleRoots)
                          ..._nodeTiles(context, root, 0, compact),
                      ],
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _header(BuildContext context, bool compact) {
    return Row(children: [
      IconButton(
        key: const Key('navigation-tree-toggle'),
        tooltip:
            context.tr(app.railCollapsed ? 'Expand menu' : 'Collapse menu'),
        icon:
            Icon(app.railCollapsed ? Icons.chevron_right : Icons.chevron_left),
        onPressed: app.toggleRail,
      ),
      if (!compact)
        Expanded(
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String?>(
              isExpanded: true,
              value: app.scopedRoot,
              items: [
                const DropdownMenuItem(
                    value: null, child: LText('All stations')),
                for (final r in app.forest)
                  DropdownMenuItem(
                      value: r.path,
                      child: LText(r.displayNameKey.isEmpty
                          ? r.name
                          : r.displayNameKey)),
              ],
              onChanged: app.scopeTo, // forest vs single-root scope (Core 3.1a)
            ),
          ),
        ),
    ]);
  }

  List<Widget> _nodeTiles(
      BuildContext context, ModuleNode n, int depth, bool compact) {
    final sev = n.effectiveSeverity; // subtree max -> ancestor tint (Core 3.13)
    final own = n.ownSeverity; // the source itself -> strongest render
    final selected = app.selectedPath == n.path;
    final hasKids = n.children.isNotEmpty;
    final open = app.expanded.contains(n.path) || depth == 0;
    final cs = Theme.of(context).colorScheme;
    final tintColor = sev == null ? null : severityColor(context, sev);
    final tiles = <Widget>[
      InkWell(
        onTap: () => app.select(n.path),
        child: Container(
          // Every tree row is a tap target, so it follows the size preset.
          height: ControlScaleScope.of(context).treeRowHeight,
          margin: EdgeInsets.only(
              left: compact ? 4 : 4.0 + depth * 14, right: 4, bottom: 2),
          decoration: BoxDecoration(
            color: own != null
                ? tintColor!.withValues(alpha: 0.28) // event SOURCE: strongest
                : sev != null
                    ? tintColor!
                        .withValues(alpha: 0.10) // ancestor on the path: tint
                    : selected
                        ? cs.secondaryContainer
                        : null,
            borderRadius: BorderRadius.circular(10),
            border: Border(
              left: BorderSide(
                width: 4,
                color:
                    tintColor ?? (selected ? cs.primary : Colors.transparent),
              ),
            ),
          ),
          child: Row(
              mainAxisAlignment:
                  compact ? MainAxisAlignment.center : MainAxisAlignment.start,
              children: [
                if (!compact && hasKids)
                  IconButton(
                    padding: EdgeInsets.zero,
                    constraints:
                        const BoxConstraints(minWidth: 28, minHeight: 28),
                    iconSize: 18,
                    // Same pairing rule as the label and the type icon beside
                    // it: a selected row is filled with secondaryContainer, so
                    // the chevron must use onSecondaryContainer. Inheriting
                    // onSurface is invisible on the high-contrast themes, where
                    // that container role inverts to a DARK fill (2.33:1 light,
                    // 1.77:1 dark).
                    color: (selected && sev == null)
                        ? cs.onSecondaryContainer
                        : null,
                    icon: Icon(open ? Icons.expand_more : Icons.chevron_right),
                    onPressed: () => app.toggleExpand(n.path),
                  )
                else if (!compact)
                  const SizedBox(width: 28),
                _typeIcon(context, n, tintColor,
                    selected: selected && sev == null),
                if (!compact) ...[
                  const SizedBox(width: 6),
                  Expanded(
                    child: LText(
                      n.displayNameKey.isEmpty ? n.name : n.displayNameKey,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontWeight: selected || own != null
                            ? FontWeight.w600
                            : FontWeight.w400,
                        // A selected row is filled with secondaryContainer, so
                        // its label MUST use the matching onSecondaryContainer.
                        // Leaving it null inherits onSurface, which happens to
                        // work on the normal themes but collapses to 1.8:1 on
                        // the high-contrast ones — where that fill is dark.
                        color: own != null
                            ? tintColor
                            : (selected && sev == null
                                ? cs.onSecondaryContainer
                                : null),
                      ),
                    ),
                  ),
                  _stateDot(context, n),
                  const SizedBox(width: 8),
                ],
              ]),
        ),
      ),
    ];
    if (hasKids && open) {
      for (final c in n.children.where((c) => c.tileEnable)) {
        tiles.addAll(_nodeTiles(context, c, depth + 1, compact));
      }
    }
    return tiles;
  }

  Widget _typeIcon(BuildContext context, ModuleNode n, Color? tint,
      {bool selected = false}) {
    final icon = switch (n.type) {
      ModuleType.unit => Icons.factory_outlined,
      ModuleType.equipmentModule => Icons.widgets_outlined,
      _ => Icons.settings_input_component_outlined,
    };
    // Same pairing rule as the label: on a selected (secondaryContainer) row the
    // icon must use onSecondaryContainer, not the inherited onSurface.
    return Icon(icon,
        size: ControlScaleScope.of(context).iconSize,
        color: tint ??
            (selected
                ? Theme.of(context).colorScheme.onSecondaryContainer
                : null));
  }

  Widget _stateDot(BuildContext context, ModuleNode n) => Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
            color: stateColor(context, n.state), shape: BoxShape.circle),
      );
}
