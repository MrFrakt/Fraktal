// Test-only: the S7WebVault contract without a platform store.
import 'package:fraktal_hmi/data/s7web_vault.dart';

class MemoryS7WebVault implements S7WebVault {
  Map<String, S7WebLogin> logins = {};
  int saves = 0;

  @override
  Future<Map<String, S7WebLogin>?> load() async => {...logins};

  @override
  Future<void> save(Map<String, S7WebLogin> value) async {
    saves++;
    logins = {...value};
  }
}
