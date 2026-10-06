/// Fallback host: every capability reports false and every call is a no-op.
library;

import 'panel_platform_base.dart';

PanelPlatform createPanelPlatform() => const NoopPanelPlatform();
