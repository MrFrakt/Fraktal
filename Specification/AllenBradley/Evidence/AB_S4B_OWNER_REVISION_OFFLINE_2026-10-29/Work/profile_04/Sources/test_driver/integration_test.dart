// Driver for `flutter drive` against the desktop acceptance target:
//
//   flutter drive --profile -d windows \
//     --driver=test_driver/integration_test.dart \
//     --target=integration_test/ab_desktop_acceptance_test.dart \
//     --dart-define=fraktal.cip.trace=true \
//     "--dart-define=fraktal.ab.desktop.endpoint=cip://127.0.0.1?slot=0&serial=601FC87B" \
//     --dart-define=fraktal.ab.desktop.output=<session>/desktop_profile
import 'package:integration_test/integration_test_driver.dart';

Future<void> main() => integrationDriver();
