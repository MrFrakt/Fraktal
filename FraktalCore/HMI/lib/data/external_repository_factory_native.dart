library;

import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:fraktal_opcua_client/fraktal_opcua_client.dart'
    show CipSessionClient;
import 'package:fraktal_opcua_client/cip_session_client.dart' show CipEndpoint;
import 'package:fraktal_opcua_client/webapi_session_client.dart';

import '../domain/connection_settings.dart';
import 'ads_session_client.dart';
import 'opcua_gateway_client_io.dart';
import 'opcua_native_client.dart';
import 'opcua_repository.dart';
import 'opcua_session_client.dart' show OpcUaRemoteException;
import 'plc_repository.dart';
import 'reconnecting_opcua_session_client.dart';
import 's7web_credentials.dart';
import 's7web_endpoint.dart';

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
  // Direct Siemens S7 Web API (TIA-native path, the counterpart of ADS):
  // s7web://<cpu>?pin=<sha256>. HTTPS trusting only the pinned CPU
  // certificate, a CPU web-user login, and a write surface the CPU itself
  // limits to the published HmiRequest mailbox; the PLC re-checks every
  // command through its own access and release gates.
  if (endpoint.scheme == S7WebEndpoint.scheme) {
    final target = S7WebEndpoint.parse(endpoint);
    // An unattended panel provides the CPU web login through the environment;
    // otherwise the operator enters it, in process memory only unless they
    // chose to remember it (sealed for the Windows user, S7WebCredentialStore).
    final environmentUser = Platform.environment['FRAKTAL_TIA_WEB_USER'] ?? '';
    final environmentPassword =
        Platform.environment['FRAKTAL_TIA_WEB_PASSWORD'] ?? '';
    final fromEnvironment =
        environmentUser.isNotEmpty && environmentPassword.isNotEmpty;
    if (!fromEnvironment) await s7WebCredentials.ready();
    final entered = fromEnvironment ? null : s7WebCredentials.lookup(target);
    if (!fromEnvironment && entered == null) {
      throw const S7WebLoginRequired(rejected: false);
    }
    final user = fromEnvironment ? environmentUser : entered!.user;
    final password = fromEnvironment ? environmentPassword : entered!.password;
    debugPrint('[Fraktal/Connection] stage=s7web-connect '
        'host=${target.host} port=${target.port} user=$user '
        'login=${fromEnvironment ? 'environment' : s7WebCredentials.isRemembered(target) ? 'remembered' : 'entered'} '
        'pin=${target.pinSha256.substring(0, 16)}… batch=${target.batchSize}');
    final ReconnectingOpcUaSessionClient client;
    try {
      client = await ReconnectingOpcUaSessionClient.connect(
        factory: () => WebApiSessionClient.connect(
          transport: HttpsWebApiTransport.fingerprint(
            host: target.host,
            port: target.port,
            sha256Fingerprint: target.pinSha256,
          ),
          user: user,
          password: password,
          roots: target.roots,
          batchSize: target.batchSize,
        ),
        log: debugPrint,
      );
    } on OpcUaRemoteException catch (error) {
      // The CPU answered Api.Login with a refusal: an entered login is
      // dropped so it is not offered again; an environment login cannot be
      // corrected from the HMI, so that failure stays a diagnostic.
      if (!error.message.startsWith('Api.Login') || fromEnvironment) rethrow;
      s7WebCredentials.forget(target);
      throw const S7WebLoginRequired(rejected: true);
    }
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
    final cip = CipEndpoint.parse(settings.endpoint);
    final port = cip.port;
    debugPrint('[Fraktal/Connection] stage=cip-connect host=${endpoint.host} '
        'port=$port');
    final client = await ReconnectingOpcUaSessionClient.connect(
        factory: () => CipSessionClient.connect(
            host: endpoint.host,
            port: port,
            slot: cip.slot,
            expectSerial: cip.serial),
        log: debugPrint);
    return OpcUaRepository.connectWithClient(client);
  }
  if (endpoint.scheme != 'opc.tcp') {
    throw UnsupportedError(
        'Native connections require opc.tcp, ads, s7web, ws, wss, or cip.');
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
