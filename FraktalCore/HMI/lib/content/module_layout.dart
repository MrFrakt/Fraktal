library;

import 'dart:convert';

import '../domain/types.dart';

/// The Unit modes in which auto-opening operator guidance is appropriate: the
/// SETUP modes, where the operator is being walked through a procedure.
///
/// AUTO is deliberately absent. A production cycle waits for the operator as a
/// matter of course — the press bench parks AUTO on a two-hand start, a
/// WAIT_OPERATOR step — so a wildcard guidance trigger threw a fullscreen
/// dialog over the machine view the instant AUTO was selected. Guidance that
/// interrupts routine running teaches the operator to dismiss it, including
/// when it matters.
///
/// Derived from the enum rather than written as ordinals: `UnitMode` is the PLC
/// contract, and a literal list here would silently rot if a member moved.
final List<int> kSetupGuidanceModes = List<int>.unmodifiable([
  UnitMode.changeover.index,
  UnitMode.home.index,
  UnitMode.calibration.index,
  UnitMode.capability.index,
  UnitMode.adjustment.index,
]);

/// How insistent an auto-opened guidance tab is.
///
/// The distinction is about what the step NEEDS from the operator, not about
/// how important the content is:
///
/// * [optional] — reference material. The operator may already know the job, so
///   the panel offers it and gets out of the way: dismissible, and the rest of
///   the HMI stays reachable while it is open.
/// * [forced] — the step is *waiting on this person*. A changeover model
///   selection, or confirming it is safe to open the doors before tooling is
///   swapped. Acknowledgement is the point, so it cannot be waved away.
///
/// Forced is deliberately the narrower case. Guidance that blocks the screen
/// when it did not need to is the fastest way to teach an operator to dismiss
/// guidance without reading it — including the time it mattered.
enum GuidanceMode { optional, forced }

enum ModuleTabKind {
  overview,
  description,
  sequence,
  motion,
  vision,
  codeReader,
  rfid,
  custom,
  guidance,
}

enum ModuleControlKind {
  text,
  value,
  indicator,
  chart,
  button,
  textInput,
  image,
}

enum ModuleBackgroundFit { contain, cover, fitWidth, fitHeight }

enum ModuleBackgroundPosition {
  topLeft,
  topCenter,
  topRight,
  centerLeft,
  center,
  centerRight,
  bottomLeft,
  bottomCenter,
  bottomRight,
}

/// Whitelisted Material icon presets keep imported layouts portable across
/// Windows, Linux, Android, and Web without persisting font code points.
enum ModuleTabIcon {
  widgets,
  dashboard,
  tune,
  monitoring,
  chart,
  information,
  build,
  science,
  machine,
  camera,
  scanner,
  contactless,
  checklist,
  guidance,
  image,
  description,
  settings,
  speed,
  electrical,
}

/// Custom buttons deliberately map only to the existing PLC-owned write
/// surfaces. The HMI layout can choose and label an action; it cannot invent a
/// writable OPC UA path or bypass the Unit mailbox/release checks.
enum ModuleActionKind {
  none,
  manualCommand,
  unitStart,
  unitStop,
  operatorReset,
  decisionAnswer,
  writeConfig,
}

enum ModuleActionConfirmation { none, confirm }

enum ModuleControlWidth { quarter, third, half, twoThirds, full }

class ModuleTabCapabilities {
  final bool unit;
  final bool sequence;
  final bool motion;
  final bool vision;
  final bool codeReader;
  final bool rfid;

  const ModuleTabCapabilities({
    this.unit = false,
    this.sequence = false,
    this.motion = false,
    this.vision = false,
    this.codeReader = false,
    this.rfid = false,
  });
}

class ModuleTabBackground {
  static const maxImageBytes = 10 * 1024 * 1024;
  static const maxMargin = 600.0;

  final String imageBase64;
  final String imageName;
  final ModuleBackgroundFit fit;
  final ModuleBackgroundPosition position;
  final double marginLeft;
  final double marginTop;
  final double marginRight;
  final double marginBottom;

  const ModuleTabBackground({
    required this.imageBase64,
    this.imageName = '',
    this.fit = ModuleBackgroundFit.contain,
    this.position = ModuleBackgroundPosition.center,
    this.marginLeft = 0,
    this.marginTop = 0,
    this.marginRight = 0,
    this.marginBottom = 0,
  });

  Map<String, Object?> toJson() => {
        'imageBase64': imageBase64,
        'imageName': imageName,
        'fit': fit.name,
        'position': position.name,
        'marginLeft': marginLeft,
        'marginTop': marginTop,
        'marginRight': marginRight,
        'marginBottom': marginBottom,
      };

  static ModuleTabBackground? fromJson(Object? source) {
    if (source is! Map) return null;
    final image = source['imageBase64'];
    if (image is! String || image.isEmpty) return null;
    if (image.length > ((maxImageBytes * 4 / 3).ceil() + 16)) return null;
    try {
      if (base64Decode(image).length > maxImageBytes) return null;
    } on FormatException {
      return null;
    }
    final fit = ModuleBackgroundFit.values
            .where((value) => value.name == source['fit'])
            .firstOrNull ??
        ModuleBackgroundFit.contain;
    final position = ModuleBackgroundPosition.values
            .where((value) => value.name == source['position'])
            .firstOrNull ??
        ModuleBackgroundPosition.center;
    double margin(String name) {
      final value = source[name];
      return value is num ? value.clamp(0, maxMargin).toDouble() : 0;
    }

    final name = source['imageName'];
    return ModuleTabBackground(
      imageBase64: image,
      imageName: name is String && name.length <= 255 ? name : '',
      fit: fit,
      position: position,
      marginLeft: margin('marginLeft'),
      marginTop: margin('marginTop'),
      marginRight: margin('marginRight'),
      marginBottom: margin('marginBottom'),
    );
  }
}

class ModuleControlDefinition {
  static const minSamplePeriodMs = 250;
  static const maxSamplePeriodMs = 60000;
  static const minHistoryPoints = 20;
  static const maxHistoryPoints = 600;
  static const maxImageBytes = 5 * 1024 * 1024;
  static const maxChartBindings = 8;

  static bool usesBindings(ModuleControlKind kind) => const {
        ModuleControlKind.value,
        ModuleControlKind.indicator,
        ModuleControlKind.chart,
        ModuleControlKind.textInput,
      }.contains(kind);

  static int maximumBindingsFor(ModuleControlKind kind) => switch (kind) {
        ModuleControlKind.chart => maxChartBindings,
        ModuleControlKind.value ||
        ModuleControlKind.indicator ||
        ModuleControlKind.textInput =>
          1,
        _ => 0,
      };

  final String id;
  final ModuleControlKind kind;
  final String label;
  final String text;
  final String binding;
  final List<String> bindings;
  final String unit;
  final ModuleActionKind action;
  final int actionValue;
  final ModuleActionConfirmation confirmation;
  final ModuleControlWidth width;
  // Retained only to import older layout files. New actions ignore this path.
  final String targetPath;
  final int samplePeriodMs;
  final int historyPoints;
  final String imageBase64;
  final String imageName;

  const ModuleControlDefinition({
    required this.id,
    required this.kind,
    this.label = '',
    this.text = '',
    this.binding = '',
    this.bindings = const [],
    this.unit = '',
    this.action = ModuleActionKind.none,
    this.actionValue = 0,
    this.confirmation = ModuleActionConfirmation.confirm,
    this.width = ModuleControlWidth.full,
    this.targetPath = '',
    this.samplePeriodMs = 1000,
    this.historyPoints = 120,
    this.imageBase64 = '',
    this.imageName = '',
  });

  /// Version-2 layouts stored one `binding`. New layouts store a list while
  /// retaining the first item in that legacy field for downgrade/import
  /// compatibility.
  List<String> get linkedBindings {
    if (bindings.isNotEmpty) return List.unmodifiable(bindings);
    final legacy = binding.trim();
    return legacy.isEmpty ? const [] : [legacy];
  }

  String get primaryBinding => linkedBindings.firstOrNull ?? '';

  bool get bindingsAreValid {
    final linked = linkedBindings;
    return linked.length <= maximumBindingsFor(kind) &&
        linked.every((item) => item.trim().isNotEmpty && item.length <= 512) &&
        linked.toSet().length == linked.length;
  }

  ModuleControlDefinition copyWith({
    String? id,
    ModuleControlKind? kind,
    String? label,
    String? text,
    String? binding,
    List<String>? bindings,
    String? unit,
    ModuleActionKind? action,
    int? actionValue,
    ModuleActionConfirmation? confirmation,
    ModuleControlWidth? width,
    String? targetPath,
    int? samplePeriodMs,
    int? historyPoints,
    String? imageBase64,
    String? imageName,
  }) =>
      ModuleControlDefinition(
        id: id ?? this.id,
        kind: kind ?? this.kind,
        label: label ?? this.label,
        text: text ?? this.text,
        binding: binding ?? this.binding,
        bindings: bindings ?? this.bindings,
        unit: unit ?? this.unit,
        action: action ?? this.action,
        actionValue: actionValue ?? this.actionValue,
        confirmation: confirmation ?? this.confirmation,
        width: width ?? this.width,
        targetPath: targetPath ?? this.targetPath,
        samplePeriodMs: (samplePeriodMs ?? this.samplePeriodMs)
            .clamp(minSamplePeriodMs, maxSamplePeriodMs)
            .toInt(),
        historyPoints: (historyPoints ?? this.historyPoints)
            .clamp(minHistoryPoints, maxHistoryPoints)
            .toInt(),
        imageBase64: imageBase64 ?? this.imageBase64,
        imageName: imageName ?? this.imageName,
      );

  Map<String, Object?> toJson() => {
        'id': id,
        'kind': kind.name,
        'label': label,
        'text': text,
        'binding': primaryBinding,
        'bindings': linkedBindings,
        'unit': unit,
        'action': action.name,
        'actionValue': actionValue,
        'confirmation': confirmation.name,
        'width': width.name,
        'targetPath': targetPath,
        'samplePeriodMs': samplePeriodMs,
        'historyPoints': historyPoints,
        'imageBase64': imageBase64,
        'imageName': imageName,
      };

  static ModuleControlDefinition? fromJson(Object? source) {
    if (source is! Map) return null;
    final id = source['id'];
    final kindName = source['kind'];
    if (id is! String || id.isEmpty || id.length > 120 || kindName is! String) {
      return null;
    }
    final kind = ModuleControlKind.values
        .where((value) => value.name == kindName)
        .firstOrNull;
    if (kind == null) return null;
    final actionName = source['action'];
    final action = ModuleActionKind.values
            .where((value) => value.name == actionName)
            .firstOrNull ??
        ModuleActionKind.none;
    final image =
        source['imageBase64'] is String ? source['imageBase64'] as String : '';
    if (image.length > ((maxImageBytes * 4 / 3).ceil() + 16)) return null;
    if (image.isNotEmpty) {
      try {
        if (base64Decode(image).length > maxImageBytes) return null;
      } on FormatException {
        return null;
      }
    }
    String field(String name, [int maximum = 512]) {
      final value = source[name];
      return value is String && value.length <= maximum ? value : '';
    }

    int number(String name, int fallback) {
      final value = source[name];
      return value is num ? value.toInt() : fallback;
    }

    final bindings = <String>[];
    final rawBindings = source['bindings'];
    if (rawBindings is List) {
      final maximum = maximumBindingsFor(kind);
      if (rawBindings.length > maximum) return null;
      for (final item in rawBindings) {
        if (item is! String ||
            item.trim().isEmpty ||
            item.length > 512 ||
            bindings.contains(item.trim())) {
          return null;
        }
        bindings.add(item.trim());
      }
    }
    final legacyBinding = field('binding').trim();
    if (usesBindings(kind) && bindings.isEmpty && legacyBinding.isNotEmpty) {
      bindings.add(legacyBinding);
    }

    return ModuleControlDefinition(
      id: id,
      kind: kind,
      label: field('label', 160),
      text: field('text', 4000),
      binding: bindings.firstOrNull ?? '',
      bindings: bindings,
      unit: field('unit', 40),
      action: action,
      actionValue: number('actionValue', 0),
      confirmation: ModuleActionConfirmation.values
              .where((value) => value.name == source['confirmation'])
              .firstOrNull ??
          ModuleActionConfirmation.confirm,
      width: ModuleControlWidth.values
              .where((value) => value.name == source['width'])
              .firstOrNull ??
          ModuleControlWidth.full,
      targetPath: field('targetPath'),
      samplePeriodMs: number('samplePeriodMs', 1000)
          .clamp(minSamplePeriodMs, maxSamplePeriodMs)
          .toInt(),
      historyPoints: number('historyPoints', 120)
          .clamp(minHistoryPoints, maxHistoryPoints)
          .toInt(),
      imageBase64: image,
      imageName: field('imageName', 255),
    );
  }
}

class ModuleTabDefinition {
  final String id;
  final String title;
  final ModuleTabKind kind;
  final AccessLevel requiredLevel;
  final List<ModuleControlDefinition> controls;
  final int triggerStepNo;
  final String triggerStepName;

  /// Unit modes this guidance may auto-open in, by `UnitMode.index`. Empty =
  /// every mode.
  ///
  /// Without this a wildcard trigger fires in ANY mode: the press bench parks
  /// AUTO on `pressAwaitTwoHand`, a WAIT_OPERATOR step, so simply selecting
  /// AUTO threw a fullscreen dialog over the machine view before the operator
  /// had done anything. Guidance that interrupts routine running is worse than
  /// no guidance — the operator learns to dismiss it, including when it matters.
  final List<int> triggerModes;

  /// Whether the operator may dismiss this guidance and carry on, or must
  /// acknowledge it. See [GuidanceMode]. Defaults to [GuidanceMode.optional]:
  /// blocking the panel is opt-in, never the accident of leaving a field unset.
  final GuidanceMode guidanceMode;
  final ModuleTabBackground? background;
  final ModuleTabIcon? tabIcon;

  const ModuleTabDefinition({
    required this.id,
    required this.title,
    required this.kind,
    this.requiredLevel = AccessLevel.none,
    this.controls = const [],
    this.triggerStepNo = 0,
    this.triggerStepName = '',
    this.triggerModes = const [],
    this.guidanceMode = GuidanceMode.optional,
    this.background,
    this.tabIcon,
  });

  ModuleTabIcon get effectiveIcon =>
      tabIcon ??
      switch (kind) {
        ModuleTabKind.overview => ModuleTabIcon.dashboard,
        ModuleTabKind.description => ModuleTabIcon.description,
        ModuleTabKind.sequence => ModuleTabIcon.checklist,
        ModuleTabKind.motion => ModuleTabIcon.machine,
        ModuleTabKind.vision => ModuleTabIcon.camera,
        ModuleTabKind.codeReader => ModuleTabIcon.scanner,
        ModuleTabKind.rfid => ModuleTabIcon.contactless,
        ModuleTabKind.custom => ModuleTabIcon.widgets,
        ModuleTabKind.guidance => ModuleTabIcon.guidance,
      };

  bool get builtIn => const {
        'overview',
        'description',
        'motion',
        'vision',
        'code-reader',
        'rfid',
        'operator-guidance',
      }.contains(id);

  /// Whether this guidance tab should auto-open for the given live step.
  ///
  /// [modeIndex] is the Unit's active `UnitMode.index`, or null when unknown;
  /// an unknown mode never satisfies a mode-scoped trigger, because opening a
  /// fullscreen dialog on a guess is the failure this scoping exists to stop.
  bool triggers(int stepNo, String stepName, {int? modeIndex}) {
    if (kind != ModuleTabKind.guidance || stepNo == 0) return false;
    final hasNumber = triggerStepNo > 0;
    final hasName = triggerStepName.trim().isNotEmpty;
    if (!hasNumber && !hasName) return false;
    if (hasNumber && triggerStepNo != stepNo) return false;
    if (hasName &&
        triggerStepName.trim() != '*' &&
        triggerStepName.trim() != stepName) {
      return false;
    }
    if (triggerModes.isNotEmpty &&
        (modeIndex == null || !triggerModes.contains(modeIndex))) {
      return false;
    }
    return true;
  }

  ModuleTabDefinition copyWith({
    String? id,
    String? title,
    ModuleTabKind? kind,
    AccessLevel? requiredLevel,
    List<ModuleControlDefinition>? controls,
    int? triggerStepNo,
    String? triggerStepName,
    List<int>? triggerModes,
    GuidanceMode? guidanceMode,
    ModuleTabBackground? background,
    ModuleTabIcon? tabIcon,
  }) =>
      ModuleTabDefinition(
        id: id ?? this.id,
        title: title ?? this.title,
        kind: kind ?? this.kind,
        requiredLevel: requiredLevel ?? this.requiredLevel,
        controls: controls ?? this.controls,
        triggerStepNo: triggerStepNo ?? this.triggerStepNo,
        triggerStepName: triggerStepName ?? this.triggerStepName,
        triggerModes: triggerModes ?? this.triggerModes,
        guidanceMode: guidanceMode ?? this.guidanceMode,
        background: background ?? this.background,
        tabIcon: tabIcon ?? this.tabIcon,
      );

  Map<String, Object?> toJson() => {
        'id': id,
        'title': title,
        'kind': kind.name,
        'requiredLevel': requiredLevel.name,
        'triggerStepNo': triggerStepNo,
        'triggerStepName': triggerStepName,
        if (triggerModes.isNotEmpty) 'triggerModes': triggerModes,
        if (guidanceMode != GuidanceMode.optional)
          'guidanceMode': guidanceMode.name,
        if (background != null) 'background': background!.toJson(),
        if (tabIcon != null) 'tabIcon': tabIcon!.name,
        'controls': [for (final control in controls) control.toJson()],
      };

  static ModuleTabDefinition? fromJson(Object? source) {
    if (source is! Map) return null;
    final id = source['id'];
    final title = source['title'];
    if (id is! String ||
        id.isEmpty ||
        id.length > 120 ||
        title is! String ||
        title.isEmpty ||
        title.length > 160) {
      return null;
    }
    final kind = ModuleTabKind.values
        .where((value) => value.name == source['kind'])
        .firstOrNull;
    final level = AccessLevel.values
        .where((value) => value.name == source['requiredLevel'])
        .firstOrNull;
    if (kind == null || level == null) return null;
    final controls = <ModuleControlDefinition>[];
    final rawControls = source['controls'];
    if (rawControls is List) {
      if (rawControls.length > 64) return null;
      for (final item in rawControls) {
        final control = ModuleControlDefinition.fromJson(item);
        if (control == null) return null;
        controls.add(control);
      }
    }
    final triggerStepNo = source['triggerStepNo'];
    final triggerStepName = source['triggerStepName'];
    // Absent in a profile exported before mode scoping existed: an empty list
    // means "every mode", which is exactly the old behaviour, so an imported
    // legacy bundle keeps working unchanged.
    final rawModes = source['triggerModes'];
    final triggerModes = <int>[];
    if (rawModes is List) {
      for (final item in rawModes) {
        if (item is num) {
          final index = item.toInt();
          if (index >= 0 && index < 64 && !triggerModes.contains(index)) {
            triggerModes.add(index);
          }
        }
      }
    }
    final rawBackground = source['background'];
    final background = ModuleTabBackground.fromJson(rawBackground);
    if (rawBackground != null && background == null) return null;
    return ModuleTabDefinition(
      id: id,
      title: title,
      kind: kind,
      requiredLevel: level,
      controls: controls,
      triggerStepNo: triggerStepNo is num ? triggerStepNo.toInt() : 0,
      triggerStepName:
          triggerStepName is String && triggerStepName.length <= 255
              ? triggerStepName
              : '',
      triggerModes: triggerModes,
      // Absent (or unrecognised) = optional: an imported profile can only ever
      // become LESS insistent by accident, never more.
      guidanceMode: GuidanceMode.values
              .where((value) => value.name == source['guidanceMode'])
              .firstOrNull ??
          GuidanceMode.optional,
      background: background,
      tabIcon: ModuleTabIcon.values
          .where((value) => value.name == source['tabIcon'])
          .firstOrNull,
    );
  }

  static List<ModuleTabDefinition> defaults(
      ModuleTabCapabilities capabilities) {
    return [
      const ModuleTabDefinition(
        id: 'overview',
        title: 'std.module.tab.overview',
        kind: ModuleTabKind.overview,
      ),
      const ModuleTabDefinition(
        id: 'description',
        title: 'std.module.tab.description',
        kind: ModuleTabKind.description,
      ),
      if (capabilities.sequence)
        const ModuleTabDefinition(
          id: 'sequence',
          title: 'std.module.tab.sequence',
          kind: ModuleTabKind.sequence,
        ),
      if (capabilities.motion)
        const ModuleTabDefinition(
          id: 'motion',
          title: 'std.module.tab.motion',
          kind: ModuleTabKind.motion,
          requiredLevel: AccessLevel.operator,
        ),
      if (capabilities.vision)
        const ModuleTabDefinition(
          id: 'vision',
          title: 'std.module.tab.vision',
          kind: ModuleTabKind.vision,
          requiredLevel: AccessLevel.operator,
        ),
      if (capabilities.codeReader)
        const ModuleTabDefinition(
          id: 'code-reader',
          title: 'std.module.tab.codeReader',
          kind: ModuleTabKind.codeReader,
          requiredLevel: AccessLevel.operator,
        ),
      if (capabilities.rfid)
        const ModuleTabDefinition(
          id: 'rfid',
          title: 'std.module.tab.rfid',
          kind: ModuleTabKind.rfid,
          requiredLevel: AccessLevel.operator,
        ),
      if (capabilities.unit)
        // Not const: triggerModes is derived from the UnitMode enum rather than
        // written as literal ordinals, so the list cannot be a compile-time
        // constant. Deriving it is the point — a hand-written [3, 2, 4, 5, 6]
        // would rot silently the day a mode is inserted.
        ModuleTabDefinition(
          id: 'operator-guidance',
          title: 'std.module.tab.guidance',
          kind: ModuleTabKind.guidance,
          requiredLevel: AccessLevel.operator,
          // The renderer limits this wildcard to WAIT_OPERATOR steps. Admins
          // can replace it with an exact StepName or StepNo.
          triggerStepName: '*',
          // ...and to the SETUP modes. A WAIT_OPERATOR step is not by itself a
          // reason to take over the screen: a production AUTO cycle waits for
          // the operator all the time (the press parks on a two-hand start),
          // and throwing a fullscreen dialog there interrupts normal running
          // the moment the mode is selected. Changeover, home, calibration,
          // capability and adjustment are the modes where the operator IS
          // being walked through something, so guidance belongs to them.
          // Admins can widen or narrow this per Unit.
          triggerModes: kSetupGuidanceModes,
        ),
    ];
  }
}
