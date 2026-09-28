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
  // Appended: kinds persist by name, and new ones go last regardless.
  configuration;

  /// The tabs that may carry a background image: the Overview and the tabs an
  /// administrator authors. The others are fixed views of PLC data. The one
  /// rule the editor offers and the module view honours.
  bool get acceptsBackground => this == overview || this == custom;
}

enum ModuleControlKind {
  text,
  value,
  indicator,
  chart,
  button,
  textInput,
  image,
  // Appended (kinds persist by name): overlay-first kinds for a machine
  // picture - a door or e-stop drawn as a coloured shape, a tank level bar.
  shape,
  level,
}

/// A view's display class (LOCALIZATION §7.4). The authoring rules tighten
/// with it: an OPERATING view is a primary production display and carries no
/// imagery; a MAINTENANCE view may carry a picture and the overlay on it
/// (locating a sensor is a maintenance task); ENGINEERING is unrestricted.
enum ModuleViewClass { operating, maintenance, engineering }

/// The outline of a [ModuleControlKind.shape].
enum ModuleShape { rectangle, rounded, circle }

/// The semantic state an overlay control shows. A TOKEN, never a literal
/// colour: every theme is measured against these (theme_contrast_test), and a
/// literal would leave that guarantee.
enum ModuleStateToken { neutral, ok, warning, error, info, off }

/// The bounded comparisons a [ModuleStateRule] may make. Deliberately no
/// expression language: a surface nobody reviews, at a cost nobody bounds on
/// a picture holding hundreds of indicators.
enum ModuleCompare { isTrue, isFalse, equals, notEquals, above, below }

/// One "this binding compares so -> this state" rule. A control checks its
/// rules in order and takes the first match, else its default state: a door is
/// `Faulted isTrue -> error`, `Closed isTrue -> ok`, default `warning`.
class ModuleStateRule {
  static const maxRules = 4;

  /// Index into the control's linked bindings.
  final int bindingIndex;
  final ModuleCompare compare;
  final double constant;
  final ModuleStateToken token;

  const ModuleStateRule({
    this.bindingIndex = 0,
    this.compare = ModuleCompare.isTrue,
    this.constant = 0,
    this.token = ModuleStateToken.ok,
  });

  /// Whether [value] satisfies this rule. A value that is neither a number nor
  /// a Boolean never matches, so a rule cannot claim a state from text.
  bool matches(Object? value) {
    final number = switch (value) {
      bool b => b ? 1.0 : 0.0,
      num n => n.toDouble(),
      String s when s.toLowerCase() == 'true' => 1.0,
      String s when s.toLowerCase() == 'false' => 0.0,
      String s => double.tryParse(s),
      _ => null,
    };
    if (number == null) return false;
    return switch (compare) {
      ModuleCompare.isTrue => number != 0,
      ModuleCompare.isFalse => number == 0,
      ModuleCompare.equals => number == constant,
      ModuleCompare.notEquals => number != constant,
      ModuleCompare.above => number > constant,
      ModuleCompare.below => number < constant,
    };
  }

  Map<String, Object?> toJson() => {
        'binding': bindingIndex,
        'compare': compare.name,
        'constant': constant,
        'token': token.name,
      };

  static ModuleStateRule? fromJson(Object? source, int bindingCount) {
    if (source is! Map) return null;
    final index = source['binding'];
    final constant = source['constant'];
    final compare = ModuleCompare.values
        .where((value) => value.name == source['compare'])
        .firstOrNull;
    final token = ModuleStateToken.values
        .where((value) => value.name == source['token'])
        .firstOrNull;
    if (index is! num ||
        index < 0 ||
        index >= bindingCount ||
        compare == null ||
        token == null) {
      return null;
    }
    final value = constant is num ? constant.toDouble() : 0.0;
    return ModuleStateRule(
      bindingIndex: index.toInt(),
      compare: compare,
      constant: value.isFinite ? value : 0,
      token: token,
    );
  }
}

/// Where a control sits on its tab's background image, as fractions (0..1) of
/// the image's own PAINTED box - never of the tab. A grid cell stops covering
/// the sensor it annotates the moment the image letterboxes; a position in the
/// image's own box does not, whatever the panel size, fit or margins.
class ModulePlacement {
  static const minSize = 0.01;

  final double x;
  final double y;
  final double width;
  final double height;

  const ModulePlacement({
    required this.x,
    required this.y,
    required this.width,
    required this.height,
  });

  /// The same placement kept inside the image and at least [minSize] big.
  ModulePlacement clamped() {
    double unit(double v) => v.isFinite ? v.clamp(0.0, 1.0) : 0.0;
    final w = unit(width).clamp(minSize, 1.0);
    final h = unit(height).clamp(minSize, 1.0);
    return ModulePlacement(
      x: unit(x).clamp(0.0, 1.0 - w),
      y: unit(y).clamp(0.0, 1.0 - h),
      width: w,
      height: h,
    );
  }

  @override
  bool operator ==(Object other) =>
      other is ModulePlacement &&
      other.x == x &&
      other.y == y &&
      other.width == width &&
      other.height == height;

  @override
  int get hashCode => Object.hash(x, y, width, height);

  Map<String, Object?> toJson() =>
      {'x': x, 'y': y, 'width': width, 'height': height};

  static ModulePlacement? fromJson(Object? source) {
    if (source is! Map) return null;
    double? read(String name) {
      final value = source[name];
      return value is num && value.isFinite ? value.toDouble() : null;
    }

    final x = read('x'), y = read('y'), w = read('width'), h = read('height');
    if (x == null || y == null || w == null || h == null) return null;
    return ModulePlacement(x: x, y: y, width: w, height: h).clamped();
  }
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

  /// The module publishes editable configuration (Core §3.10.2 capabilities).
  final bool configuration;

  const ModuleTabCapabilities({
    this.unit = false,
    this.sequence = false,
    this.motion = false,
    this.vision = false,
    this.codeReader = false,
    this.rfid = false,
    this.configuration = false,
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

  /// A shape may read several signals (door closed + door faulted).
  static const maxShapeBindings = ModuleStateRule.maxRules;

  static bool usesBindings(ModuleControlKind kind) => const {
        ModuleControlKind.value,
        ModuleControlKind.indicator,
        ModuleControlKind.chart,
        ModuleControlKind.textInput,
        ModuleControlKind.shape,
        ModuleControlKind.level,
      }.contains(kind);

  /// The kinds whose colour comes from [rules] and [defaultToken].
  static bool usesRules(ModuleControlKind kind) =>
      kind == ModuleControlKind.shape || kind == ModuleControlKind.level;

  static int maximumBindingsFor(ModuleControlKind kind) => switch (kind) {
        ModuleControlKind.chart => maxChartBindings,
        ModuleControlKind.shape => maxShapeBindings,
        ModuleControlKind.value ||
        ModuleControlKind.indicator ||
        ModuleControlKind.textInput ||
        ModuleControlKind.level =>
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
  final ModuleShape shape;
  final List<ModuleStateRule> rules;
  final ModuleStateToken defaultToken;

  /// The range a [ModuleControlKind.level] bar spans.
  final double minimum;
  final double maximum;

  /// Set = drawn over the tab's background image at this position; null = in
  /// the tab's normal flow.
  final ModulePlacement? placement;

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
    this.shape = ModuleShape.rectangle,
    this.rules = const [],
    this.defaultToken = ModuleStateToken.neutral,
    this.minimum = 0,
    this.maximum = 100,
    this.placement,
  });

  /// The state [values] (this control's linked bindings, in order) put it in:
  /// the first matching rule, else [defaultToken].
  ModuleStateToken resolveState(List<Object?> values) {
    for (final rule in rules) {
      if (rule.bindingIndex < values.length &&
          rule.matches(values[rule.bindingIndex])) {
        return rule.token;
      }
    }
    return defaultToken;
  }

  /// This control moved onto the image, or back into the flow (null).
  ModuleControlDefinition withPlacement(ModulePlacement? next) =>
      ModuleControlDefinition(
        id: id,
        kind: kind,
        label: label,
        text: text,
        binding: binding,
        bindings: bindings,
        unit: unit,
        action: action,
        actionValue: actionValue,
        confirmation: confirmation,
        width: width,
        targetPath: targetPath,
        samplePeriodMs: samplePeriodMs,
        historyPoints: historyPoints,
        imageBase64: imageBase64,
        imageName: imageName,
        shape: shape,
        rules: rules,
        defaultToken: defaultToken,
        minimum: minimum,
        maximum: maximum,
        placement: next?.clamped(),
      );

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
    ModuleShape? shape,
    List<ModuleStateRule>? rules,
    ModuleStateToken? defaultToken,
    double? minimum,
    double? maximum,
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
        shape: shape ?? this.shape,
        rules: rules ?? this.rules,
        defaultToken: defaultToken ?? this.defaultToken,
        minimum: minimum ?? this.minimum,
        maximum: maximum ?? this.maximum,
        placement: placement,
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
        'shape': shape.name,
        'rules': [for (final rule in rules) rule.toJson()],
        'defaultToken': defaultToken.name,
        'minimum': minimum,
        'maximum': maximum,
        if (placement != null) 'placement': placement!.toJson(),
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
    // Rules are all-or-nothing: a layout whose rule points past its bindings
    // is rejected, never half-applied (a door that silently lost its fault
    // rule would read green).
    final rules = <ModuleStateRule>[];
    final rawRules = source['rules'];
    if (rawRules is List) {
      if (rawRules.length > ModuleStateRule.maxRules) return null;
      for (final item in rawRules) {
        final rule = ModuleStateRule.fromJson(item, bindings.length);
        if (rule == null) return null;
        rules.add(rule);
      }
    }
    double real(String name, double fallback) {
      final value = source[name];
      return value is num && value.isFinite ? value.toDouble() : fallback;
    }

    var minimum = real('minimum', 0);
    var maximum = real('maximum', 100);
    if (!(minimum < maximum)) {
      minimum = 0;
      maximum = 100;
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
      shape: ModuleShape.values
              .where((value) => value.name == source['shape'])
              .firstOrNull ??
          ModuleShape.rectangle,
      rules: rules,
      defaultToken: ModuleStateToken.values
              .where((value) => value.name == source['defaultToken'])
              .firstOrNull ??
          ModuleStateToken.neutral,
      minimum: minimum,
      maximum: maximum,
      placement: ModulePlacement.fromJson(source['placement']),
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

  /// The class this view declares; null = never declared (a layout from
  /// before §7.4), see [viewClass].
  final ModuleViewClass? declaredClass;

  /// A view's reads are bounded (LOCALIZATION §7.3): every bound tag is a
  /// read, so the budget is refused at publish, not discovered on the panel.
  static const maxBoundReads = 200;

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
    this.declaredClass,
  });

  /// The class in force. An undeclared view with a picture is a maintenance
  /// view and one without is an operating view, so no layout saved before
  /// §7.4 becomes invalid - and the class is still always visible.
  ModuleViewClass get viewClass =>
      declaredClass ??
      (background == null
          ? ModuleViewClass.operating
          : ModuleViewClass.maintenance);

  /// The tag reads this view makes each refresh.
  int get boundReads => controls.fold(
      0, (sum, control) => sum + control.linkedBindings.length);

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
        ModuleTabKind.configuration => ModuleTabIcon.tune,
      };

  bool get builtIn => const {
        'overview',
        'description',
        'motion',
        'vision',
        'code-reader',
        'rfid',
        'operator-guidance',
        'configuration',
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
    ModuleViewClass? declaredClass,
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
        declaredClass: declaredClass ?? this.declaredClass,
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
        // Recorded in the export (§7.4): a class claimed silently would be.
        if (declaredClass != null) 'viewClass': declaredClass!.name,
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
      declaredClass: ModuleViewClass.values
          .where((value) => value.name == source['viewClass'])
          .firstOrNull,
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
      // Its own tab rather than a card under Overview: configuration is
      // edited deliberately, not scrolled past. Only for a module that has any.
      if (capabilities.configuration)
        const ModuleTabDefinition(
          id: 'configuration',
          title: 'std.module.tab.configuration',
          kind: ModuleTabKind.configuration,
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
