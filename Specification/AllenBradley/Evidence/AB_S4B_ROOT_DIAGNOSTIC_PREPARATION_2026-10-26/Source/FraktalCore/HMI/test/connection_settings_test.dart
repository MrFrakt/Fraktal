import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_hmi/domain/connection_settings.dart';

void main() {
  test('display target retains address and runtime without URI credentials',
      () {
    const settings = ConnectionSettings(
      endpoint:
          'wss://operator:secret@cell.example:8443/fraktal?token=secret#secret',
    );
    expect(settings.displayEndpoint, 'wss://cell.example:8443/fraktal');
    expect(settings.endpoint, contains('token=secret'));
    expect(
        const ConnectionSettings(endpoint: 'ads://192.168.0.49.1.1:852')
            .displayEndpoint,
        'ads://192.168.0.49.1.1:852');
    expect(
        const ConnectionSettings(endpoint: 'cip://192.168.100.89:44818')
            .displayEndpoint,
        'cip://192.168.100.89:44818');
    expect(
        const ConnectionSettings(transport: ConnectionTransport.simulation)
            .displayEndpoint,
        isEmpty);
    expect(const ConnectionSettings(endpoint: 'not a URI').displayEndpoint,
        isEmpty);
  });

  test('current settings retain completed language setup after reload', () {
    const settings = ConnectionSettings(
      everConnected: true,
      selectedUnitPaths: ['Press'],
      unitSelectionComplete: true,
      enabledLanguageCodes: ['en', 'es'],
      activeLanguageCode: 'es',
      languageSelectionComplete: true,
      appearanceSetupComplete: true,
    );
    final restored = ConnectionSettings.fromJson(settings.toJson());

    expect(restored?.enabledLanguageCodes, ['en', 'es']);
    expect(restored?.activeLanguageCode, 'es');
    expect(restored?.languageSelectionComplete, isTrue);
    expect(restored?.appearanceSetupComplete, isTrue);
  });

  test('connection settings persist the administrator-selected Unit scope', () {
    const settings = ConnectionSettings(
      everConnected: true,
      selectedUnitPaths: ['StationA', 'ConveyorB'],
      unitSelectionComplete: true,
    );
    final restored = ConnectionSettings.fromJson(settings.toJson());

    expect(restored?.selectedUnitPaths, ['StationA', 'ConveyorB']);
    expect(restored?.unitSelectionComplete, isTrue);
  });

  test('schema 1 settings migrate to an incomplete Unit selection', () {
    final restored = ConnectionSettings.fromJson({
      'schemaVersion': 1,
      'transport': 'gateway',
      'endpoint': 'ws://127.0.0.1/fraktal',
      'everConnected': true,
    });

    expect(restored?.everConnected, isTrue);
    expect(restored?.selectedUnitPaths, isEmpty);
    expect(restored?.unitSelectionComplete, isFalse);
  });

  test('deployed Web HMI derives a same-origin secure gateway endpoint', () {
    expect(
      gatewayEndpointForWebBase(
        Uri.parse('https://hmi.cell.example/operator/'),
      ),
      'wss://hmi.cell.example/fraktal',
    );
    expect(
      gatewayEndpointForWebBase(Uri.parse('http://127.0.0.1:8080/')),
      'ws://127.0.0.1:8080/fraktal',
    );
  });
}
