import 'package:flutter_test/flutter_test.dart';
import 'package:fraktal_opcua_client/opcua_native_client.dart';
import 'package:fraktal_hmi/data/opcua_gateway_client_io.dart';

void main() {
  const secureMaterial = OpcUaSecurityOptions(
    profile: OpcUaSecurityProfile.production,
    applicationUri: 'urn:fraktal:gateway:test',
    clientCertificatePath: 'own/cert.der',
    clientPrivateKeyPath: 'own/key.pem',
    trustListPath: 'trusted/certs',
  );

  test('production requires secure material and an authenticated user', () {
    expect(
      () => const OpcUaSecurityOptions(
        profile: OpcUaSecurityProfile.production,
      ).validate(username: 'gateway'),
      throwsArgumentError,
    );
    expect(
      () => secureMaterial.validate(username: ''),
      throwsArgumentError,
    );
    expect(
      () => const OpcUaSecurityOptions(
        profile: OpcUaSecurityProfile.production,
        securityPolicyUri: '',
        applicationUri: 'urn:fraktal:gateway:test',
        clientCertificatePath: 'own/cert.der',
        clientPrivateKeyPath: 'own/key.pem',
        trustListPath: 'trusted/certs',
      ).validate(username: 'gateway'),
      throwsArgumentError,
    );
    expect(
      () => secureMaterial.validate(username: 'gateway'),
      returnsNormally,
    );
  });

  test('secure anonymous retains certificate trust without a user token', () {
    const options = OpcUaSecurityOptions(
      profile: OpcUaSecurityProfile.secureAnonymous,
      applicationUri: 'urn:fraktal:gateway:test',
      clientCertificatePath: 'own/cert.der',
      clientPrivateKeyPath: 'own/key.pem',
      trustListPath: 'trusted/certs',
    );

    expect(() => options.validate(username: ''), returnsNormally);
    expect(options.encrypted, isTrue);
    expect(options.nativeProfile, 2);
  });

  test('insecure anonymous profiles are explicit native profile zero', () {
    const commissioning = OpcUaSecurityOptions.commissioningAnonymous();
    const isolated = OpcUaSecurityOptions.isolatedAnonymous();

    expect(() => commissioning.validate(username: ''), returnsNormally);
    expect(() => isolated.validate(username: ''), returnsNormally);
    expect(commissioning.encrypted, isFalse);
    expect(isolated.encrypted, isFalse);
    expect(commissioning.nativeProfile, 0);
    expect(isolated.nativeProfile, 0);
  });

  test('native gateway credentials are accepted only over WSS', () {
    const bearer = IoGatewaySecurityOptions(bearerToken: 'deployment-secret');
    const incompleteIdentity = IoGatewaySecurityOptions(
      clientCertificatePath: 'device.pem',
    );
    const completeIdentity = IoGatewaySecurityOptions(
      clientCertificatePath: 'device.pem',
      clientPrivateKeyPath: 'device-key.pem',
    );

    expect(
      () => bearer.validate(Uri.parse('ws://127.0.0.1:8080/fraktal')),
      throwsArgumentError,
    );
    expect(
      () => incompleteIdentity.validate(
        Uri.parse('wss://hmi.example.com/fraktal'),
      ),
      throwsArgumentError,
    );
    expect(
      () => completeIdentity.validate(
        Uri.parse('wss://hmi.example.com/fraktal'),
      ),
      returnsNormally,
    );
  });
}
