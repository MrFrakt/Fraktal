import 'dart:async';
import 'dart:io';

import 'package:fraktal_gateway/fraktal_gateway.dart';
import 'package:fraktal_opcua_client/ads_session_client.dart';
import 'package:fraktal_opcua_client/opcua_native_client.dart';
import 'package:fraktal_opcua_client/opcua_session_client.dart';
import 'package:fraktal_opcua_client/webapi_session_client.dart';

Future<void> main(List<String> arguments) async {
  _GatewayOptions options;
  try {
    options = _GatewayOptions.parse(arguments);
  } on FormatException catch (error) {
    stderr.writeln('fraktal_gateway: ${error.message}');
    stderr.writeln('Use --help for usage.');
    exitCode = 64;
    return;
  }
  if (options.help) {
    stdout.write(_usage);
    return;
  }

  OpcUaSessionClient? client;
  FraktalGatewayServer? gateway;
  // Register the basic configuration up front so every run — including an
  // immediate start-failure (e.g. missing credentials, thrown below) — records
  // WHAT the gateway was trying to do, not just a bare error string.
  final securityProfileName = _securityProfileName(options.securityProfile);
  final plcScheme = options.plcEndpoint.scheme;
  final isAds = plcScheme == 'ads';
  final isWebApi = plcScheme == 's7web';
  stdout.writeln('[Fraktal/Gateway] stage=config '
      'instance=${options.instanceName.isEmpty ? '(unnamed)' : options.instanceName} '
      'plcEndpoint=${options.plcEndpoint} '
      'plcTransport=${plcScheme.isEmpty ? "(unknown)" : plcScheme} '
      // On ADS the OPC UA profile is not applied at all; say so explicitly so a
      // leftover --security-profile in gateway.args is not mistaken for active.
      'securityProfile=${isAds ? "$securityProfileName (ignored: ADS transport)" : isWebApi ? "$securityProfileName (ignored: Web API transport)" : securityProfileName} '
      'listenPort=${options.port} path=${options.path} '
      'webRoot=${options.webRoot.isEmpty ? "(none)" : options.webRoot} '
      'readRoots=${options.readRoots.isEmpty ? "(OPC-authorized)" : options.readRoots.join(",")} '
      'writeRoots=${options.writeRoots.isEmpty ? "(none)" : options.writeRoots.join(",")}');
  if (options.writeRoots.isEmpty && !options.allowAllRootMailboxes) {
    // A very common misconfiguration: the gateway starts and serves data but
    // every HMI command is refused, which looks like "the HMI cannot control".
    stdout.writeln('[Fraktal/Gateway] stage=config-warning '
        'detail=No --write-root configured: the gateway is READ-ONLY and every '
        'HMI command will be refused. Add "--write-root <PLC1/MAIN/YourUnit>".');
  }
  try {
    if (plcScheme == 'ads') {
      // Native TwinCAT ADS: the AMS route is the trust boundary, so the OPC UA
      // security profile / credential provisioning does not apply.
      final amsNetId = options.plcEndpoint.host;
      final amsPort =
          options.plcEndpoint.hasPort ? options.plcEndpoint.port : 851;
      stdout.writeln('[Fraktal/Gateway] stage=ads-connect '
          'amsNetId=$amsNetId amsPort=$amsPort');
      client = await AdsSessionClient.connect(
        amsNetId: amsNetId,
        amsPort: amsPort,
        timeout: options.connectTimeout,
      );
      stdout.writeln('[Fraktal/Gateway] stage=connected '
          'transport=ads amsNetId=$amsNetId amsPort=$amsPort');
    } else if (isWebApi) {
      // Siemens S7 Web API (Fraktal/TIA Part IV §11.1a): licence-free HTTPS to
      // the CPU's web server, trusting exactly the pinned server certificate;
      // the web user's rights in the CPU are the PLC-side write gate.
      final user = Platform.environment['FRAKTAL_TIA_WEB_USER'] ?? '';
      final password = Platform.environment['FRAKTAL_TIA_WEB_PASSWORD'] ?? '';
      if (user.isEmpty || password.isEmpty) {
        throw const FormatException(
          'The s7web transport requires FRAKTAL_TIA_WEB_USER and '
          'FRAKTAL_TIA_WEB_PASSWORD (never on the command line).',
        );
      }
      final host = options.plcEndpoint.host;
      final port = options.plcEndpoint.hasPort ? options.plcEndpoint.port : 443;
      stdout.writeln('[Fraktal/Gateway] stage=webapi-connect '
          'host=$host port=$port user=$user '
          'pinnedCertificate=${options.plcCertificatePath} '
          'batch=${options.webApiBatch}');
      client = await WebApiSessionClient.connect(
        transport: HttpsWebApiTransport(
          host: host,
          port: port,
          pinnedCertificate: File(options.plcCertificatePath).readAsBytesSync(),
          timeout: options.connectTimeout * 2,
        ),
        user: user,
        password: password,
        batchSize: options.webApiBatch,
      );
      stdout.writeln('[Fraktal/Gateway] stage=connected '
          'transport=s7web host=$host port=$port');
    } else {
      final configuredUsername =
          Platform.environment['FRAKTAL_OPCUA_USERNAME'] ?? '';
      final configuredPassword =
          Platform.environment['FRAKTAL_OPCUA_PASSWORD'] ?? '';
      final configuredPrivateKeyPassword =
          Platform.environment['FRAKTAL_OPCUA_PRIVATE_KEY_PASSWORD'] ?? '';
      final security = options.security(
        privateKeyPassword: configuredPrivateKeyPassword,
      );
      options.validateCredentials(
        username: configuredUsername,
        password: configuredPassword,
        security: security,
      );
      final useUserCredentials =
          options.securityProfile == OpcUaSecurityProfile.production;
      stdout.writeln('[Fraktal/Gateway] stage=opcua-connect '
          'endpoint=${options.plcEndpoint} '
          'securityProfile=$securityProfileName '
          'authenticatedUser=${useUserCredentials && configuredUsername.isNotEmpty}');
      if (!security.encrypted) {
        stdout.writeln('[Fraktal/Gateway] stage=security-warning '
            'profile=$securityProfileName '
            'detail=OPC UA messages are not signed or encrypted.');
      }
      client = await NativeOpcUaClient.connect(
        options.plcEndpoint,
        username: useUserCredentials ? configuredUsername : '',
        password: useUserCredentials ? configuredPassword : '',
        timeout: options.connectTimeout,
        security: security,
      );
      stdout.writeln('[Fraktal/Gateway] stage=connected '
          'transport=opcua endpoint=${options.plcEndpoint}');
    }
    gateway = FraktalGatewayServer(
      client,
      config: FraktalGatewayConfig(
        port: options.port,
        webSocketPath: options.path,
        instanceName: options.instanceName,
        allowedOrigins: options.allowedOrigins,
        readRoots: options.readRoots,
        writeRoots: options.writeRoots,
        allowAllRootMailboxes: options.allowAllRootMailboxes,
        initialPlcReady: true,
        webRoot: options.webRoot.isEmpty ? null : Directory(options.webRoot),
      ),
      log: stdout.writeln,
    );
    await gateway.start();
  } on Object catch (error) {
    stderr.writeln('[Fraktal/Gateway] stage=start-failed error=$error');
    await gateway?.close();
    if (gateway == null) await client?.close();
    exitCode = 1;
    return;
  }

  final stopped = Completer<void>();
  var stopping = false;
  Future<void> stop() async {
    if (stopping) return;
    stopping = true;
    await gateway?.close();
    if (!stopped.isCompleted) stopped.complete();
  }

  Timer? commissioningTimer;
  if (options.securityProfile == OpcUaSecurityProfile.commissioningAnonymous) {
    commissioningTimer = Timer(
      options.commissioningTtl,
      () {
        stdout.writeln('[Fraktal/Gateway] stage=commissioning-expired '
            'action=shutdown');
        unawaited(stop());
      },
    );
    stdout.writeln('[Fraktal/Gateway] stage=commissioning-expiry '
        'afterMinutes=${options.commissioningTtl.inMinutes}');
  }

  final subscriptions = <StreamSubscription<ProcessSignal>>[
    ProcessSignal.sigint.watch().listen((_) => unawaited(stop())),
  ];
  if (!Platform.isWindows) {
    subscriptions.add(
      ProcessSignal.sigterm.watch().listen((_) => unawaited(stop())),
    );
  }
  await stopped.future;
  commissioningTimer?.cancel();
  for (final subscription in subscriptions) {
    await subscription.cancel();
  }
}

class _GatewayOptions {
  final Uri plcEndpoint;
  final int port;
  final String path;
  final String instanceName;
  final Duration connectTimeout;
  final Set<String> allowedOrigins;
  final Set<String> readRoots;
  final Set<String> writeRoots;
  final bool allowAllRootMailboxes;
  final String webRoot;
  final OpcUaSecurityProfile securityProfile;
  final String securityPolicyUri;
  final String applicationUri;
  final String clientCertificatePath;
  final String clientPrivateKeyPath;
  final String trustListPath;
  final String revocationListPath;
  final Duration commissioningTtl;
  final String plcCertificatePath;
  final int webApiBatch;
  final bool help;

  const _GatewayOptions({
    required this.plcEndpoint,
    required this.port,
    required this.path,
    required this.instanceName,
    required this.connectTimeout,
    required this.allowedOrigins,
    required this.readRoots,
    required this.writeRoots,
    required this.allowAllRootMailboxes,
    required this.webRoot,
    required this.securityProfile,
    required this.securityPolicyUri,
    required this.applicationUri,
    required this.clientCertificatePath,
    required this.clientPrivateKeyPath,
    required this.trustListPath,
    required this.revocationListPath,
    required this.commissioningTtl,
    required this.plcCertificatePath,
    required this.webApiBatch,
    required this.help,
  });

  OpcUaSecurityOptions security({String privateKeyPassword = ''}) =>
      OpcUaSecurityOptions(
        profile: securityProfile,
        securityPolicyUri: securityPolicyUri,
        applicationUri: applicationUri,
        clientCertificatePath: clientCertificatePath,
        clientPrivateKeyPath: clientPrivateKeyPath,
        clientPrivateKeyPassword: privateKeyPassword,
        trustListPath: trustListPath,
        revocationListPath: revocationListPath,
      );

  void validateCredentials({
    required String username,
    required String password,
    required OpcUaSecurityOptions security,
  }) {
    security.validate(username: username);
    if (securityProfile == OpcUaSecurityProfile.production &&
        password.isEmpty) {
      throw const FormatException(
        'The production profile requires FRAKTAL_OPCUA_PASSWORD.',
      );
    }
  }

  static _GatewayOptions parse(List<String> arguments) {
    var endpoint = Uri.parse('opc.tcp://127.0.0.1:4840');
    var port = 8080;
    var path = '/fraktal';
    var instanceName = '';
    var timeout = const Duration(seconds: 5);
    final origins = <String>{};
    final readRoots = <String>{};
    final writeRoots = <String>{};
    var allowAllRootMailboxes = false;
    var webRoot = '';
    var securityProfile = OpcUaSecurityProfile.production;
    var securityPolicyUri = kOpcUaBasic256Sha256;
    var applicationUri = '';
    var clientCertificatePath = '';
    var clientPrivateKeyPath = '';
    var trustListPath = '';
    var revocationListPath = '';
    var commissioningTtl = const Duration(hours: 2);
    var plcCertificatePath = '';
    var webApiBatch = 20;
    var help = false;

    String valueAfter(int index, String option) {
      if (index + 1 >= arguments.length) {
        throw FormatException('$option requires a value.');
      }
      return arguments[index + 1];
    }

    for (var index = 0; index < arguments.length; index++) {
      final argument = arguments[index];
      switch (argument) {
        case '--help':
        case '-h':
          help = true;
        case '--plc-endpoint':
          endpoint = Uri.parse(valueAfter(index, argument));
          index++;
        case '--port':
          port = int.parse(valueAfter(index, argument));
          index++;
        case '--path':
          path = valueAfter(index, argument);
          index++;
        case '--instance-name':
          instanceName = valueAfter(index, argument);
          index++;
        case '--connect-timeout-ms':
          timeout = Duration(
            milliseconds: int.parse(valueAfter(index, argument)),
          );
          index++;
        case '--allow-origin':
          origins.add(valueAfter(index, argument));
          index++;
        case '--read-root':
          readRoots.add(valueAfter(index, argument));
          index++;
        case '--write-root':
          writeRoots.add(valueAfter(index, argument));
          index++;
        case '--allow-all-root-mailboxes':
          allowAllRootMailboxes = true;
        case '--web-root':
          webRoot = valueAfter(index, argument);
          index++;
        case '--security-profile':
          securityProfile = _parseSecurityProfile(valueAfter(index, argument));
          index++;
        case '--security-policy':
          securityPolicyUri = valueAfter(index, argument);
          index++;
        case '--application-uri':
          applicationUri = valueAfter(index, argument);
          index++;
        case '--client-certificate':
          clientCertificatePath = valueAfter(index, argument);
          index++;
        case '--client-private-key':
          clientPrivateKeyPath = valueAfter(index, argument);
          index++;
        case '--trust-list':
          trustListPath = valueAfter(index, argument);
          index++;
        case '--revocation-list':
          revocationListPath = valueAfter(index, argument);
          index++;
        case '--commissioning-ttl-minutes':
          commissioningTtl = Duration(
            minutes: int.parse(valueAfter(index, argument)),
          );
          index++;
        case '--plc-certificate':
          plcCertificatePath = valueAfter(index, argument);
          index++;
        case '--webapi-batch':
          webApiBatch = int.parse(valueAfter(index, argument));
          index++;
        default:
          throw FormatException('Unknown option: $argument');
      }
    }
    // Two PLC transports: opc.tcp (TF6100/multi-brand) and ads (native TwinCAT,
    // ads://<AmsNetId a.b.c.d.e.f>:<port>). ADS bypasses the OPC UA security
    // profile entirely — the AMS route is the trust boundary.
    if (endpoint.scheme == 'ads') {
      if (endpoint.host.split('.').length != 6) {
        throw const FormatException(
          '--plc-endpoint ads:// needs a six-part AmsNetId, e.g. '
          'ads://5.132.128.188.1.1:851.',
        );
      }
    } else if (endpoint.scheme == 's7web') {
      // Siemens S7 Web API: s7web://<host>[:443]. The server certificate is
      // pinned; there is no "accept any certificate" mode.
      if (endpoint.host.isEmpty) {
        throw const FormatException('--plc-endpoint s7web:// needs a host.');
      }
      if (plcCertificatePath.isEmpty) {
        throw const FormatException(
          's7web:// requires --plc-certificate (the CPU web server certificate '
          'captured at commissioning, PEM or DER).',
        );
      }
      if (webApiBatch < 1 || webApiBatch > 200) {
        throw const FormatException('--webapi-batch must be between 1 and 200.');
      }
    } else if (endpoint.scheme != 'opc.tcp' || endpoint.host.isEmpty) {
      throw const FormatException(
        '--plc-endpoint must be a complete opc.tcp://, ads:// or s7web:// URI.',
      );
    }
    if (port < 1 || port > 65535) {
      throw const FormatException('--port must be between 1 and 65535.');
    }
    if (instanceName.isNotEmpty &&
        !RegExp(r'^[A-Za-z0-9._-]{1,32}$').hasMatch(instanceName)) {
      throw const FormatException(
        '--instance-name must be 1-32 letters, digits, dots, underscores, or '
        'hyphens (it also names the instance folder and log directory).',
      );
    }
    if (timeout.inMilliseconds < 100 || timeout.inSeconds > 60) {
      throw const FormatException(
        '--connect-timeout-ms must be between 100 and 60000.',
      );
    }
    if (commissioningTtl.inMinutes < 1 || commissioningTtl.inMinutes > 1440) {
      throw const FormatException(
        '--commissioning-ttl-minutes must be between 1 and 1440.',
      );
    }
    return _GatewayOptions(
      plcEndpoint: endpoint,
      port: port,
      path: path,
      instanceName: instanceName,
      connectTimeout: timeout,
      allowedOrigins: origins,
      readRoots: readRoots,
      writeRoots: writeRoots,
      allowAllRootMailboxes: allowAllRootMailboxes,
      webRoot: webRoot,
      securityProfile: securityProfile,
      securityPolicyUri: securityPolicyUri,
      applicationUri: applicationUri,
      clientCertificatePath: clientCertificatePath,
      clientPrivateKeyPath: clientPrivateKeyPath,
      trustListPath: trustListPath,
      revocationListPath: revocationListPath,
      commissioningTtl: commissioningTtl,
      plcCertificatePath: plcCertificatePath,
      webApiBatch: webApiBatch,
      help: help,
    );
  }
}

OpcUaSecurityProfile _parseSecurityProfile(String value) => switch (value) {
      'production' => OpcUaSecurityProfile.production,
      'secure-anonymous' => OpcUaSecurityProfile.secureAnonymous,
      'commissioning-anonymous' => OpcUaSecurityProfile.commissioningAnonymous,
      'isolated-anonymous' => OpcUaSecurityProfile.isolatedAnonymous,
      _ => throw FormatException('Unknown security profile: $value'),
    };

String _securityProfileName(OpcUaSecurityProfile profile) => switch (profile) {
      OpcUaSecurityProfile.production => 'production',
      OpcUaSecurityProfile.secureAnonymous => 'secure-anonymous',
      OpcUaSecurityProfile.commissioningAnonymous => 'commissioning-anonymous',
      OpcUaSecurityProfile.isolatedAnonymous => 'isolated-anonymous',
    };

const String _usage = '''
Fraktal OPC UA WebSocket gateway

One process serves exactly one PLC. To serve several controllers from one host,
run one process per PLC, each with its own --port and --instance-name; on
Windows the tray supervises them from %LOCALAPPDATA%\\Fraktal\\Gateway\\instances.

Usage:
  fraktal_gateway [options]

Options:
  --plc-endpoint URI       PLC endpoint. Three transports:
                             opc.tcp://<host>:4840  (TF6100, default)
                             ads://<AmsNetId>:851   (native TwinCAT; the AMS
                             route is the trust boundary, so the OPC UA security
                             profile/credentials below are ignored)
                             s7web://<host>[:443]   (Siemens S7 Web API, no
                             runtime licence; needs --plc-certificate and the
                             FRAKTAL_TIA_WEB_* variables; OPC UA profile ignored)
  --plc-certificate PATH   s7web: the CPU web server certificate (PEM or DER)
                            pinned at commissioning; nothing else is trusted
  --webapi-batch N         s7web: leaves per Web API request (default 20); the
                            CPU serves one request at a time, so small batches
                            keep a mailbox acknowledgement from queueing
  --port PORT              Loopback WebSocket port (default 8080)
  --path PATH              WebSocket path (default /fraktal)
  --instance-name NAME     Label for this gateway when several run on one host,
                            one per PLC. Reported by /healthz and every log
                            line; it is also the instance folder name.
  --connect-timeout-ms MS  PLC connect timeout (default 5000)
  --allow-origin ORIGIN    Add an exact remote Web origin; repeatable
  --read-root BROWSE_PATH  Limit discovery/reads to this subtree; repeatable
  --write-root BROWSE_PATH Limit writes to this root Unit; repeatable
  --allow-all-root-mailboxes
                            Commissioning override for every root mailbox
  --web-root PATH           Serve a compiled Flutter Web HMI from this folder
  --security-profile NAME  production (default), secure-anonymous,
                            commissioning-anonymous, or isolated-anonymous
  --security-policy URI    SecureChannel policy (default Basic256Sha256)
  --application-uri URI    URI encoded in the gateway client certificate
  --client-certificate PATH
                            Gateway application certificate (DER or PEM)
  --client-private-key PATH
                            Gateway private key (protected file, never source)
  --trust-list PATH        Trusted server/CA certificate file or directory
  --revocation-list PATH   Optional CRL file or directory
  --commissioning-ttl-minutes MINUTES
                            Auto-stop commissioning-anonymous (default 120)
  --help                    Show this help

Environment:
  FRAKTAL_OPCUA_USERNAME   Dedicated TF6100 user (required by production)
  FRAKTAL_OPCUA_PASSWORD   TF6100 password (required by production; never CLI)
  FRAKTAL_OPCUA_PRIVATE_KEY_PASSWORD
                            Optional encrypted client-key password
  FRAKTAL_OPCUA_LIBRARY    Absolute native bridge library path (optional)
  FRAKTAL_TIA_WEB_USER     s7web: the CPU web (UMAC) user
  FRAKTAL_TIA_WEB_PASSWORD s7web: its password (never CLI)

The gateway listens on 127.0.0.1 only. Local http(s) origins are accepted by
default. Remote browsers require a same-host TLS/authenticating reverse proxy
and an exact --allow-origin entry.
''';
