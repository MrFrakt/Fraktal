library;

import 'panel_platform_base.dart';
import 'panel_platform_stub.dart'
    if (dart.library.io) 'panel_platform_io.dart'
    if (dart.library.html) 'panel_platform_web.dart' as platform;

export 'panel_platform_base.dart';

PanelPlatform createPanelPlatform() => platform.createPanelPlatform();
