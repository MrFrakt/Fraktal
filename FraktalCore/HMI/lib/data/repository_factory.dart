library;

import 'dart:async';
import 'package:flutter/foundation.dart';
import '../domain/connection_settings.dart';
import 'connection_preflight.dart';
import 'external_repository_factory.dart';
import 'plc_repository.dart';
import 'sim_repository.dart';

typedef ConnectionRepositoryFactory = FutureOr<PlcRepository> Function(
    ConnectionSettings settings);

class ConnectionStartupException implements Exception {
  final String stage;
  final String message;
  final String remediation;

  const ConnectionStartupException({
    required this.stage,
    required this.message,
    required this.remediation,
  });

  @override
  String toString() => '[$stage] $message $remediation';
}

Future<PlcRepository> createRepository(ConnectionSettings settings) async {
  if (settings.transport == ConnectionTransport.simulation) {
    debugPrint('[Fraktal/Connection] stage=repository transport=simulation');
    return SimRepository();
  }

  final endpoint = Uri.parse(settings.endpoint);

  // ADS connects through the AMS router (TcAdsDll), not a TCP socket to
  // host:port, and an AmsNetId is not a DNS name — a TCP/host-lookup preflight
  // is meaningless here and would always fail. The ADS client surfaces its own
  // connect/discovery diagnostics, so route straight to the adapter.
  if (endpoint.scheme == 'ads') {
    debugPrint('[Fraktal/Connection] stage=repository-adapter '
        'scheme=ads preflight=skipped');
    return createExternalRepository(settings);
  }

  debugPrint('[Fraktal/Connection] stage=tcp-preflight '
      'endpoint=$endpoint host=${endpoint.host}');
  final probe = await preflightExternalEndpoint(endpoint);
  debugPrint('[Fraktal/Connection] stage=tcp-preflight '
      'target=${probe.host}:${probe.port} reachable=${probe.reachable} '
      'elapsedMs=${probe.elapsed.inMilliseconds} detail=${probe.detail}');
  if (!probe.reachable) {
    throw ConnectionStartupException(
      stage: 'tcp-preflight',
      message: '${probe.host}:${probe.port} is not reachable: ${probe.detail}',
      remediation: endpoint.scheme == 'opc.tcp'
          ? 'Verify that the TwinCAT OPC UA Server (TF6100) is installed, '
              'licensed, configured, and listening on this port.'
          : 'Start the Fraktal WebSocket/REST gateway and verify its address, '
              'port, firewall, and route.',
    );
  }

  debugPrint('[Fraktal/Connection] stage=repository-adapter '
      'scheme=${endpoint.scheme}');
  return createExternalRepository(settings);
}
