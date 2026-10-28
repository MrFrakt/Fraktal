import 'dart:convert';
import 'dart:io';
import 'scalar_probe.dart';
Future<void> main() async {
  final result={'host':'Dart CLI','worker':await measureWorker()};
  final file=File(Platform.environment['FRAKTAL_SCALAR_OUTPUT']!);
  if(file.existsSync()) throw StateError('Refusing existing probe output.');
  file.writeAsStringSync(jsonEncode(result));
  print(jsonEncode(result));
}
