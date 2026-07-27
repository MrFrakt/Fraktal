library;

import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, kReleaseMode, TargetPlatform;

/// Transport selected by the connection wizard. The gateway option is the
/// deployment seam for OPC UA/ADS on native platforms and WebSocket/REST on Web.
enum ConnectionTransport { gateway, simulation }

/// Const seed for [ConnectionSettings]; the platform-aware default a fresh
/// wizard shows is computed by [defaultConnectionEndpoint] (below), which cannot
/// be const because it reads the runtime platform. Kept as the OPC UA loopback
/// so a const context always has a valid native endpoint.
const String kDefaultEndpoint =
    kIsWeb ? 'ws://127.0.0.1:8080/fraktal' : 'opc.tcp://127.0.0.1:4840';

/// Platform-appropriate default endpoint a fresh connection wizard shows.
///
/// - **Windows (TwinCAT)**: direct **ADS** to the local runtime
///   (`ads://<AmsNetId>:<port>`) — the fast native path, no TF6100 server. The
///   local AmsNetId is machine-specific, so the default targets the loopback
///   `127.0.0.1.1.1`; the operator confirms/edits it in the wizard.
/// - **Other native (Linux/Android)**: direct **OPC UA** (`opc.tcp://…:4840`),
///   since ADS/`TcAdsDll` is Windows-only.
/// - **Deployed Web (release)**: the gateway on the hosting origin, so an
///   installer/reverse proxy needs no second endpoint transcribed. Debug Web
///   keeps the explicit loopback default (Chrome debug server ≠ the gateway).
///
/// OPC UA remains fully selectable on every native platform for a remote or
/// non-Beckhoff PLC. See `external_repository_factory_native.dart`.
String defaultConnectionEndpoint() {
  if (kIsWeb) {
    return kReleaseMode ? gatewayEndpointForWebBase(Uri.base) : kDefaultEndpoint;
  }
  if (defaultTargetPlatform == TargetPlatform.windows) {
    return 'ads://127.0.0.1.1.1:851';
  }
  return kDefaultEndpoint;
}

String gatewayEndpointForWebBase(Uri base) {
  if ((base.scheme != 'http' && base.scheme != 'https') || base.host.isEmpty) {
    return 'ws://127.0.0.1:8080/fraktal';
  }
  return Uri(
    scheme: base.scheme == 'https' ? 'wss' : 'ws',
    host: base.host,
    port: base.hasPort ? base.port : null,
    path: '/fraktal',
  ).toString();
}

class ConnectionSettings {
  final ConnectionTransport transport;
  final String endpoint;
  final bool everConnected;

  /// Stable root-Unit browse paths this HMI is allowed to display and command.
  /// An empty list is valid only while the second wizard step is incomplete.
  final List<String> selectedUnitPaths;
  final bool unitSelectionComplete;
  final List<String> enabledLanguageCodes;
  final String activeLanguageCode;
  final bool languageSelectionComplete;

  const ConnectionSettings({
    this.transport = ConnectionTransport.gateway,
    this.endpoint = kDefaultEndpoint,
    this.everConnected = false,
    this.selectedUnitPaths = const [],
    this.unitSelectionComplete = false,
    this.enabledLanguageCodes = const [],
    this.activeLanguageCode = 'en',
    this.languageSelectionComplete = false,
  });

  ConnectionSettings copyWith({
    ConnectionTransport? transport,
    String? endpoint,
    bool? everConnected,
    List<String>? selectedUnitPaths,
    bool? unitSelectionComplete,
    List<String>? enabledLanguageCodes,
    String? activeLanguageCode,
    bool? languageSelectionComplete,
  }) =>
      ConnectionSettings(
        transport: transport ?? this.transport,
        endpoint: endpoint ?? this.endpoint,
        everConnected: everConnected ?? this.everConnected,
        selectedUnitPaths: selectedUnitPaths ?? this.selectedUnitPaths,
        unitSelectionComplete:
            unitSelectionComplete ?? this.unitSelectionComplete,
        enabledLanguageCodes: enabledLanguageCodes ?? this.enabledLanguageCodes,
        activeLanguageCode: activeLanguageCode ?? this.activeLanguageCode,
        languageSelectionComplete:
            languageSelectionComplete ?? this.languageSelectionComplete,
      );

  Map<String, Object> toJson() => {
        'schemaVersion': 3,
        'transport': transport.name,
        'endpoint': endpoint,
        'everConnected': everConnected,
        'selectedUnitPaths': selectedUnitPaths,
        'unitSelectionComplete': unitSelectionComplete,
        'enabledLanguageCodes': enabledLanguageCodes,
        'activeLanguageCode': activeLanguageCode,
        'languageSelectionComplete': languageSelectionComplete,
      };

  static ConnectionSettings? fromJson(Object? value) {
    if (value is! Map) return null;
    final schemaVersion = value['schemaVersion'];
    if (schemaVersion != 1 && schemaVersion != 2 && schemaVersion != 3) {
      return null;
    }
    final transportName = value['transport'];
    final endpoint = value['endpoint'];
    final everConnected = value['everConnected'];
    if (transportName is! String ||
        endpoint is! String ||
        everConnected is! bool) return null;
    ConnectionTransport? transport;
    for (final candidate in ConnectionTransport.values) {
      if (candidate.name == transportName) transport = candidate;
    }
    if (transport == null) return null;
    final selected = schemaVersion >= 2 ? value['selectedUnitPaths'] : null;
    final selectionComplete =
        schemaVersion >= 2 ? value['unitSelectionComplete'] : null;
    if (schemaVersion >= 2 &&
        (selected is! List ||
            selected.any((item) => item is! String) ||
            selectionComplete is! bool)) {
      return null;
    }
    final languages = schemaVersion == 3 ? value['enabledLanguageCodes'] : null;
    final activeLanguage =
        schemaVersion == 3 ? value['activeLanguageCode'] : null;
    final languageComplete =
        schemaVersion == 3 ? value['languageSelectionComplete'] : null;
    if (schemaVersion == 3 &&
        (languages is! List ||
            languages.any((item) => item is! String) ||
            activeLanguage is! String ||
            languageComplete is! bool)) {
      return null;
    }
    return ConnectionSettings(
      transport: transport,
      endpoint: endpoint,
      everConnected: everConnected,
      selectedUnitPaths:
          selected == null ? const [] : List<String>.from(selected),
      unitSelectionComplete: selectionComplete == true,
      enabledLanguageCodes:
          languages == null ? const [] : List<String>.from(languages),
      activeLanguageCode: activeLanguage is String ? activeLanguage : 'en',
      languageSelectionComplete: languageComplete == true,
    );
  }
}
