library;

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart'
    show CipSessionClient;

import '../domain/connection_settings.dart';
import 'ads_session_client.dart';
import 'opcua_gateway_client_io.dart';
import 'opcua_native_client.dart';
import 'opcua_repository.dart';
import 'plc_repository.dart';
import 'reconnecting_opcua_session_client.dart';

Future<PlcRepository> createExternalRepository(
    ConnectionSettings settings) async {
  final endpoint = Uri.parse(settings.endpoint);
  // Direct ADS (TwinCAT-native fast path): ads://<AmsNetId>:<port>, e.g.
  // ads://127.0.0.1.1.1:851. No TF6100 server; the bridge speaks ADS directly.
  if (endpoint.scheme == 'ads') {
    final amsNetId = endpoint.host; // "127.0.0.1.1.1" (dots are not a port sep)
    final amsPort = endpoint.hasPort ? endpoint.port : 851;
    if (amsNetId.split('.').length != 6) {
      throw UnsupportedError(
          'ADS endpoint needs ads://<AmsNetId a.b.c.d.e.f>:<port>, got "$amsNetId".');
    }
    debugPrint('[Fraktal/Connection] stage=ads-connect '
        'amsNetId=$amsNetId amsPort=$amsPort');
    final client =
        await AdsSessionClient.connect(amsNetId: amsNetId, amsPort: amsPort);
    return OpcUaRepository.connectWithClient(client);
  }
  if (endpoint.scheme == 'ws' || endpoint.scheme == 'wss') {
    final security = IoGatewaySecurityOptions(
      bearerToken: Platform.environment['FRAKTAL_GATEWAY_BEARER_TOKEN'] ?? '',
      clientCertificatePath:
          Platform.environment['FRAKTAL_WSS_CLIENT_CERTIFICATE'] ?? '',
      clientPrivateKeyPath:
          Platform.environment['FRAKTAL_WSS_CLIENT_PRIVATE_KEY'] ?? '',
      clientPrivateKeyPassword:
          Platform.environment['FRAKTAL_WSS_CLIENT_KEY_PASSWORD'] ?? '',
      trustedCaPath: Platform.environment['FRAKTAL_WSS_TRUSTED_CA'] ?? '',
    );
    final client = await ReconnectingOpcUaSessionClient.connect(
      factory: () => IoGatewayOpcUaClient.connect(
        endpoint,
        security: security,
      ),
      log: debugPrint,
    );
    return OpcUaRepository.connectWithClient(client);
  }
  // Direct unsecured CIP is a canonical, read-only desktop connection.
  if (endpoint.scheme == 'cip') {
    if (endpoint.host.isEmpty ||
        endpoint.userInfo.isNotEmpty ||
        endpoint.fragment.isNotEmpty ||
        endpoint.path.isNotEmpty && endpoint.path != '/' ||
        endpoint.queryParametersAll.entries.any((e) =>
            !const {'slot', 'serial'}.contains(e.key) || e.value.length != 1))
      throw const FormatException('Invalid CIP endpoint.');
    final slot = int.tryParse(endpoint.queryParameters['slot'] ?? '0');
    if (slot == null || slot < 0 || slot > 255)
      throw const FormatException('Invalid CIP slot.');
    final port = endpoint.hasPort ? endpoint.port : 44818;
    debugPrint('[Fraktal/Connection] stage=cip-connect host=${endpoint.host} '
        'port=$port');
    final client = await ReconnectingOpcUaSessionClient.connect(
        factory: () => CipSessionClient.connect(
            host: endpoint.host,
            port: port,
            slot: slot,
            expectSerial: endpoint.queryParameters['serial']),
        log: debugPrint);
    return OpcUaRepository.connectWithClient(client);
  }
  if (endpoint.scheme != 'opc.tcp') {
    throw UnsupportedError(
        'Native connections require opc.tcp, ws, wss, or cip.');
  }
  // Direct native OPC UA remains the explicit local/commissioning path. The
  // production plug-and-produce path is WSS through the machine gateway, whose
  // PLC session is configured with a named security profile.
  debugPrint('[Fraktal/Connection] stage=security-warning '
      'profile=direct-anonymous '
      'detail=opc.tcp direct mode uses SecurityPolicy None and Anonymous; '
      'use only for commissioning/troubleshooting or a physically isolated PLC.');
  final client = await NativeOpcUaClient.connect(endpoint);
  return OpcUaRepository.connectWithClient(client);
}
