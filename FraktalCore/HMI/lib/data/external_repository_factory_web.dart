library;

import 'package:flutter/foundation.dart';

import '../domain/connection_settings.dart';
import 'opcua_gateway_client_web.dart';
import 'opcua_repository.dart';
import 'plc_repository.dart';
import 'reconnecting_opcua_session_client.dart';

Future<PlcRepository> createExternalRepository(
    ConnectionSettings settings) async {
  final endpoint = Uri.parse(settings.endpoint);
  if (endpoint.scheme != 'ws' && endpoint.scheme != 'wss') {
    throw UnsupportedError('Web builds require a ws:// or wss:// Fraktal '
        'gateway endpoint; browsers cannot open opc.tcp sockets.');
  }
  final client = await ReconnectingOpcUaSessionClient.connect(
    factory: () => WebGatewayOpcUaClient.connect(endpoint),
    log: debugPrint,
  );
  return OpcUaRepository.connectWithClient(client);
}
