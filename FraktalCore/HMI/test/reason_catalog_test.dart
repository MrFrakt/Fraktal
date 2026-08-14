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
    expect(generatedReasonSymbolByCode, hasLength(52));
    for (final code in generatedReasonSymbolByCode.keys) {
      expect(standardEnglish['std.reason.$code'], isNotNull,
          reason: 'missing fallback for reason $code');
      expect(standardEnglish['std.reason.$code.consequence'], isNotNull,
          reason: 'missing consequence for reason $code');
      expect(generatedReasonPriorityByCode[code], inInclusiveRange(0, 2));
      expect(generatedReasonCategoryByCode[code], inInclusiveRange(0, 2));
      expect(generatedReasonShelvableByCode[code], isNotNull);
    }
  });

  test('alarm metadata is actionable while lifecycle entries remain events',
      () {
    expect(reasonActionKey(2001), 'std.reason.2001.action');
    expect(
        standardEnglish[reasonActionKey(2001)], contains('awaited condition'));
    expect(reasonActionKey(2024), isEmpty);
    expect(generatedReasonShelvableByCode[2024], isFalse);
    expect(generatedReasonSymbolByCode[2901], 'TEST_FAULT');
  });
}
