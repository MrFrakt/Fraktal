import 'dart:io';

Future<void> main(List<String> arguments) async {
  if (!Platform.isWindows) {
    stderr.writeln('The Windows installer can only be built on Windows.');
    exitCode = 1;
    return;
  }
  if (arguments.length != 1) {
    stderr.writeln('Usage: dart run tool/build_windows_installer.dart '
        '<windows-package-directory>');
    exitCode = 64;
    return;
  }
  final gatewayRoot = Directory.current.absolute;
  final package = Directory(arguments.single).absolute;
  final hmiRoot = gatewayRoot.parent;
  final output = Directory('${hmiRoot.path}/build/gateway/installer');
  final staging = Directory('${output.path}/staging');
  if (staging.existsSync()) staging.deleteSync(recursive: true);
  staging.createSync(recursive: true);
  output.createSync(recursive: true);

  final webRoot = Directory('${package.path}/web');
  if (!File('${webRoot.path}/index.html').existsSync()) {
    throw StateError('Packaged Web HMI is missing: ${webRoot.path}');
  }
  final webArchive = File('${output.path}/web_hmi.zip');
  if (webArchive.existsSync()) webArchive.deleteSync();
  final tar = File('${Platform.environment['SystemRoot']}\\System32\\tar.exe');
  if (!tar.existsSync()) {
    throw StateError('Windows tar.exe was not found for Web HMI packaging.');
  }
  final caddyPayload = await _prepareCaddyPayload(output, tar);
  final archiveResult = await Process.run(
    tar.path,
    ['-a', '-c', '-f', webArchive.path, '-C', webRoot.path, '.'],
    runInShell: false,
  );
  if (archiveResult.exitCode != 0 || !webArchive.existsSync()) {
    throw ProcessException(
      tar.path,
      ['-a', '-c', '-f', webArchive.path, '-C', webRoot.path, '.'],
      '${archiveResult.stdout}\n${archiveResult.stderr}',
      archiveResult.exitCode,
    );
  }

  // Package the native HMI desktop app. The whole Release/ directory is zipped
  // so its contents (which vary — fraktal_ads.dll is only built when the TcAdsSdk
  // is present, native_assets.json is harmless metadata) are shipped verbatim.
  final hmiRelease =
      Directory('${hmiRoot.path}/build/windows/x64/runner/Release');
  if (!File('${hmiRelease.path}/fraktal_hmi.exe').existsSync()) {
    throw StateError(
        'HMI Windows release build is missing: ${hmiRelease.path}. '
        'Run "flutter build windows --release" in the HMI directory.');
  }
  final hmiArchive = File('${output.path}/hmi_app.zip');
  if (hmiArchive.existsSync()) hmiArchive.deleteSync();
  final hmiArchiveResult = await Process.run(
    tar.path,
    ['-a', '-c', '-f', hmiArchive.path, '-C', hmiRelease.path, '.'],
    runInShell: false,
  );
  if (hmiArchiveResult.exitCode != 0 || !hmiArchive.existsSync()) {
    throw ProcessException(
      tar.path,
      ['-a', '-c', '-f', hmiArchive.path, '-C', hmiRelease.path, '.'],
      '${hmiArchiveResult.stdout}\n${hmiArchiveResult.stderr}',
      hmiArchiveResult.exitCode,
    );
  }

  final sources = <String, File>{
    'fraktal_gateway.exe': File('${package.path}/fraktal_gateway.exe'),
    'fraktal_gateway_tray.exe':
        File('${package.path}/fraktal_gateway_tray.exe'),
    'fraktal_opcua.dll': File('${package.path}/fraktal_opcua.dll'),
    ...caddyPayload,
    'DEPLOYMENT.md': File('${gatewayRoot.path}/DEPLOYMENT.md'),
    'WEB_HMI_GATEWAY_DEPLOYMENT.md':
        File('${package.path}/WEB_HMI_GATEWAY_DEPLOYMENT.md'),
    'gateway.args.example':
        File('${gatewayRoot.path}/deploy/windows/gateway.args.example'),
    // The instance model (discovery, validation, arguments-file editing) the
    // wizard, the installer, and the reverse-proxy configurator all dot-source.
    'fraktal_instances.ps1':
        File('${gatewayRoot.path}/deploy/windows/fraktal_instances.ps1'),
    'configure_reverse_proxy.ps1':
        File('${gatewayRoot.path}/deploy/windows/configure_reverse_proxy.ps1'),
    'configure_proxy_firewall.ps1':
        File('${gatewayRoot.path}/deploy/windows/configure_proxy_firewall.ps1'),
    'install_gateway.cmd':
        File('${gatewayRoot.path}/deploy/windows/install_gateway.cmd'),
    'install_gateway.ps1':
        File('${gatewayRoot.path}/deploy/windows/install_gateway.ps1'),
    'uninstall_gateway.ps1':
        File('${gatewayRoot.path}/deploy/windows/uninstall_gateway.ps1'),
    'install_fraktal.cmd':
        File('${gatewayRoot.path}/deploy/windows/install_fraktal.cmd'),
    'fraktal_wizard.ps1':
        File('${gatewayRoot.path}/deploy/windows/fraktal_wizard.ps1'),
    'install_hmi.ps1':
        File('${gatewayRoot.path}/deploy/windows/install_hmi.ps1'),
    'uninstall_hmi.ps1':
        File('${gatewayRoot.path}/deploy/windows/uninstall_hmi.ps1'),
    'web_hmi.zip': webArchive,
    'hmi_app.zip': hmiArchive,
  };
  for (final entry in sources.entries) {
    if (!entry.value.existsSync()) {
      throw StateError('Installer input is missing: ${entry.value.path}');
    }
    await entry.value.copy('${staging.path}/${entry.key}');
  }

  // fraktal_ads.dll is optional (built only with the TwinCAT ADS SDK). When
  // present, stage it so the installed gateway can use an ads:// PLC endpoint;
  // install_gateway.ps1 copies it beside the gateway exe if it exists.
  //
  // It MUST also be added to the packed-file list below. Staging alone is not
  // enough: IExpress packs exactly the names in that list, so a staged-but-
  // unlisted file is silently dropped and the deployed gateway fails at runtime
  // with LoadLibrary error 126 — which reads as a missing dependency rather than
  // a packaging bug, and cost a full field debugging cycle.
  final packedNames = sources.keys.toList();
  final gatewayAds = File('${package.path}/fraktal_ads.dll');
  if (gatewayAds.existsSync()) {
    await gatewayAds.copy('${staging.path}/fraktal_ads.dll');
    packedNames.add('fraktal_ads.dll');
  } else {
    stdout.writeln('WARNING: fraktal_ads.dll is absent from the gateway '
        'package; the installed gateway will not support ads:// endpoints.');
  }

  final setup = File('${output.path}/FraktalSetup.exe');
  if (setup.existsSync()) setup.deleteSync();
  final sed = File('${output.path}/FraktalSetup.sed');
  final names = List<String>.unmodifiable(packedNames);
  final fileEntries = <String>[];
  final sourceEntries = <String>[];
  for (var index = 0; index < names.length; index++) {
    fileEntries.add('FILE$index="${names[index]}"');
    sourceEntries.add('%FILE$index%=');
  }
  await sed.writeAsString('''
[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=
DisplayLicense=
FinishMessage=Fraktal HMI / Gateway was installed for the current Windows user.
TargetName=${setup.path}
FriendlyName=Fraktal Setup
AppLaunched=install_fraktal.cmd
PostInstallCmd=<None>
AdminQuietInstCmd=install_fraktal.cmd
UserQuietInstCmd=install_fraktal.cmd
SourceFiles=SourceFiles
[Strings]
${fileEntries.join('\n')}
[SourceFiles]
SourceFiles0=${staging.path}\\
[SourceFiles0]
${sourceEntries.join('\n')}
''');

  final iexpress =
      File('${Platform.environment['SystemRoot']}\\System32\\iexpress.exe');
  if (!iexpress.existsSync()) {
    throw StateError('Windows IExpress was not found.');
  }
  final result = await Process.run(
    iexpress.path,
    ['/N', sed.path],
    workingDirectory: output.path,
    runInShell: false,
  );
  if (result.exitCode != 0 || !setup.existsSync()) {
    throw ProcessException(
      iexpress.path,
      ['/N', sed.path],
      '${result.stdout}\n${result.stderr}',
      result.exitCode,
    );
  }
  stdout.writeln('Windows installer: ${setup.path}');
  stdout.writeln('The installer is unsigned; sign it with the organization\'s '
      'Authenticode certificate before production distribution.');
}

const _caddyVersion = '2.11.4';
const _caddyArchiveSha512 =
    'cd5ccfd86a4b40732cf715890d0dca5bf3f63adefec5a7914de85adf240c60ce'
    '7e5d2791631b88ef9758e46b23bb1730e020b9c5d696889740b284ffd4788e35';

Future<Map<String, File>> _prepareCaddyPayload(
  Directory output,
  File tar,
) async {
  final override = Platform.environment['FRAKTAL_CADDY_ARCHIVE'];
  late final File archive;
  if (override != null && override.trim().isNotEmpty) {
    archive = File(override.trim()).absolute;
    if (!archive.existsSync()) {
      throw StateError('FRAKTAL_CADDY_ARCHIVE does not exist: ${archive.path}');
    }
  } else {
    final downloads = Directory('${output.path}/downloads')
      ..createSync(recursive: true);
    archive =
        File('${downloads.path}/caddy_${_caddyVersion}_windows_amd64.zip');
    if (!archive.existsSync()) {
      final uri = Uri.parse(
        'https://github.com/caddyserver/caddy/releases/download/'
        'v$_caddyVersion/caddy_${_caddyVersion}_windows_amd64.zip',
      );
      stdout.writeln('Downloading pinned Caddy v$_caddyVersion from $uri');
      await _download(uri, archive);
    }
  }

  final digestResult = await Process.run(
    'certutil.exe',
    ['-hashfile', archive.path, 'SHA512'],
    runInShell: false,
  );
  final digestMatch = RegExp(r'\b[0-9a-fA-F]{128}\b')
      .firstMatch('${digestResult.stdout}\n${digestResult.stderr}');
  if (digestResult.exitCode != 0 || digestMatch == null) {
    throw ProcessException(
      'certutil.exe',
      ['-hashfile', archive.path, 'SHA512'],
      'Could not calculate the Caddy archive SHA-512 digest.',
      digestResult.exitCode,
    );
  }
  final actualDigest = digestMatch.group(0)!.toLowerCase();
  if (actualDigest != _caddyArchiveSha512) {
    if (override == null || override.trim().isEmpty) {
      archive.deleteSync();
    }
    throw StateError(
      'Caddy v$_caddyVersion archive checksum mismatch. '
      'Expected $_caddyArchiveSha512, received $actualDigest.',
    );
  }

  final extracted = Directory('${output.path}/caddy-$_caddyVersion');
  if (extracted.existsSync()) extracted.deleteSync(recursive: true);
  extracted.createSync(recursive: true);
  final extractResult = await Process.run(
    tar.path,
    ['-xf', archive.path, '-C', extracted.path],
    runInShell: false,
  );
  if (extractResult.exitCode != 0) {
    throw ProcessException(
      tar.path,
      ['-xf', archive.path, '-C', extracted.path],
      '${extractResult.stdout}\n${extractResult.stderr}',
      extractResult.exitCode,
    );
  }

  final executable = File('${extracted.path}/caddy.exe');
  final license = File('${extracted.path}/LICENSE');
  final readme = File('${extracted.path}/README.md');
  for (final input in [executable, license, readme]) {
    if (!input.existsSync()) {
      throw StateError(
          'The verified Caddy archive is missing ${input.uri.pathSegments.last}.');
    }
  }
  stdout.writeln(
      'Bundled Caddy v$_caddyVersion (verified SHA-512: $actualDigest).');
  return {
    'caddy.exe': executable,
    'CADDY_LICENSE.txt': license,
    'CADDY_README.md': readme,
  };
}

Future<void> _download(Uri uri, File destination) async {
  final partial = File('${destination.path}.partial');
  if (partial.existsSync()) partial.deleteSync();
  final client = HttpClient()..userAgent = 'FraktalGatewayInstallerBuilder/1.0';
  try {
    final request = await client.getUrl(uri);
    final response = await request.close();
    if (response.statusCode != HttpStatus.ok) {
      await response.drain<void>();
      throw HttpException(
        'Download failed with HTTP ${response.statusCode}.',
        uri: uri,
      );
    }
    await response.pipe(partial.openWrite());
    await partial.rename(destination.path);
  } finally {
    client.close(force: true);
    if (partial.existsSync()) partial.deleteSync();
  }
}
