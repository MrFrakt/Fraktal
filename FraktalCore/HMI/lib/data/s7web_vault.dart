library;

import 's7web_vault_base.dart';
import 's7web_vault_stub.dart'
    if (dart.library.io) 's7web_vault_io.dart' as platform;

export 's7web_vault_base.dart';

S7WebVault createS7WebVault() => platform.createS7WebVault();
