import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/data/sim_repository.dart';
import 'package:fraktal_hmi/state/app_state.dart';
import 'package:fraktal_hmi/ui/fraktal_hmi_app.dart';
import 'scalar_probe.dart';
void main() {
  final binding=LiveTestWidgetsFlutterBinding.ensureInitialized();
  binding.framePolicy=LiveTestWidgetsFlutterBindingFramePolicy.fullyLive;
  testWidgets('read-only scalar/timer timing on the restored baseline',(tester) async {
    final rows=<Map<String,Object?>>[];
    await tester.runAsync(() async {
      rows.add({'phase':'no widgets','worker':await measureWorker()});
    });
    final app=AppState(SimRepository());
    try {
      await tester.pumpWidget(FraktalHmiApp(app:app));
      await tester.runAsync(() async {
        rows.add({'phase':'simulator UI rendering only','worker':await measureWorker()});
      });
    } finally {
      await tester.pumpWidget(const SizedBox.shrink());
      app.dispose();
    }
    final file=File(Platform.environment['FRAKTAL_SCALAR_OUTPUT']!);
    expect(file.existsSync(),false);
    file.writeAsStringSync(jsonEncode({'host':'Flutter test host','rows':rows,
      'canonicalAcceptanceClaim':false,'desktopAcceptanceClaim':false}));
    expect(rows.every((row)=>(row['worker'] as Map)['reads']==160),true);
  },timeout:const Timeout(Duration(seconds:60)));
}
