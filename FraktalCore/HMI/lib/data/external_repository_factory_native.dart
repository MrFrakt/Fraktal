library;

import 'dart:io';

import 'package:flutter/foundation.dart';

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
  if (endpoint.scheme != 'opc.tcp') {
    throw UnsupportedError('Native connections require opc.tcp, ws, or wss.');
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
