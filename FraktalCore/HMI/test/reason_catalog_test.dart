import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/localization/default_catalogs.dart';
import 'package:fraktal_hmi/localization/reason_catalog.g.dart';

void main() {
  test('generated reason codes resolve to standard localization keys', () {
    expect(generatedReasonSymbolByCode[2001], 'TIMEOUT');
    expect(generatedReasonSymbolByCode[10112], 'CYL_WORK_NOT_REACHED');
    expect(reasonDescriptionKey(2001, 'project.error.moreSpecific'),
        'std.reason.2001');
    expect(standardEnglish['std.reason.2001'], 'Timeout.');
    expect(standardEnglish['std.reason.10112'], 'Cylinder work not reached.');
  });

  test('unregistered project codes retain the PLC diagnostic fallback', () {
    expect(reasonDescriptionKey(0, 'project.error.none'), 'project.error.none');
    expect(reasonDescriptionKey(19999, 'project.error.custom'),
        'project.error.custom');
  });

  test('every generated reason has a standard English fallback', () {
    expect(generatedReasonSymbolByCode, hasLength(50));
    for (final code in generatedReasonSymbolByCode.keys) {
      expect(standardEnglish['std.reason.$code'], isNotNull,
          reason: 'missing fallback for reason $code');
    }
  });
}
