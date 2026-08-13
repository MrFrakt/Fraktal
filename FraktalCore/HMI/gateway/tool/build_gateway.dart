import 'dart:io';

Future<void> main(List<String> arguments) async {
  if (!Platform.isWindows && !Platform.isLinux) {
    stderr.writeln('Gateway packaging supports Windows and Linux only.');
    exitCode = 1;
    return;
  }
  if (arguments.isNotEmpty &&
      (arguments.length != 1 || arguments.single != '--clean')) {
    stderr.writeln('Usage: dart run tool/build_gateway.dart [--clean]');
    exitCode = 64;
    return;
  }

  final project = Directory.current.absolute;
  final hmiRoot = project.parent;
  final nativeSource = Directory('${hmiRoot.path}/native/opcua');
  if (!File('${project.path}/pubspec.yaml').existsSync() ||
      !File('${nativeSource.path}/CMakeLists.txt').existsSync()) {
    stderr.writeln('Run this command from FraktalCore/HMI/gateway.');
    exitCode = 1;
    return;
  }

  final platformName = Platform.isWindows ? 'windows-x64' : 'linux-x64';
  final nativeBuild =
      Directory('${hmiRoot.path}/build/gateway-native/$platformName');
  final output = Directory('${hmiRoot.path}/build/gateway/$platformName');
  if (arguments.contains('--clean')) {
    if (nativeBuild.existsSync()) nativeBuild.deleteSync(recursive: true);
    if (output.existsSync()) output.deleteSync(recursive: true);
  }
  nativeBuild.createSync(recursive: true);
  output.createSync(recursive: true);

  final flutter = await _findFlutter();
  await _run(
    flutter,
    ['build', 'web', '--release', '--no-pub'],
    workingDirectory: hmiRoot.path,
  );
  final builtWeb = Directory('${hmiRoot.path}/build/web');
  if (!File('${builtWeb.path}/index.html').existsSync()) {
    throw StateError('Flutter Web build did not produce index.html.');
  }
  final packagedWeb = Directory('${output.path}/web');
  if (packagedWeb.existsSync()) packagedWeb.deleteSync(recursive: true);
  await _copyDirectory(builtWeb, packagedWeb);

  final cmake = await _findCmake();
  await _run(cmake, [
    '-S',
    nativeSource.path,
    '-B',
    nativeBuild.path,
    '-DCMAKE_BUILD_TYPE=Release',
  ]);
  await _run(cmake, [
    '--build',
    nativeBuild.path,
    '--config',
    'Release',
    '--parallel',
  ]);

  final executableName =
      Platform.isWindows ? 'fraktal_gateway.exe' : 'fraktal_gateway';
  await _run(Platform.resolvedExecutable, [
    'compile',
    'exe',
    '${project.path}/bin/fraktal_gateway.dart',
    '-o',
    '${output.path}/$executableName',
  ]);

  final libraryName =
      Platform.isWindows ? 'fraktal_opcua.dll' : 'libfraktal_opcua.so';
  final libraries = nativeBuild
      .listSync(recursive: true, followLinks: false)
      .whereType<File>()
      .where((file) => file.uri.pathSegments.last == libraryName)
      .toList();
  if (libraries.length != 1) {
    throw StateError(
      'Expected one $libraryName below ${nativeBuild.path}; '
      'found ${libraries.length}.',
    );
  }
  await libraries.single.copy('${output.path}/$libraryName');
  await File('${project.path}/DEPLOYMENT.md')
      .copy('${output.path}/DEPLOYMENT.md');
  final walkthrough = File(
    '${hmiRoot.parent.parent.path}/Specification/'
    'WEB_HMI_GATEWAY_DEPLOYMENT.md',
  );
  if (!walkthrough.existsSync()) {
    throw StateError('Web HMI deployment walkthrough is missing.');
  }
  await walkthrough.copy(
    '${output.path}/WEB_HMI_GATEWAY_DEPLOYMENT.md',
  );
  if (Platform.isWindows) {
    final trayExecutables = nativeBuild
        .listSync(recursive: true, followLinks: false)
        .whereType<File>()
        .where(
            (file) => file.uri.pathSegments.last == 'fraktal_gateway_tray.exe')
        .toList();
    if (trayExecutables.length != 1) {
      throw StateError('Expected one fraktal_gateway_tray.exe below '
          '${nativeBuild.path}; found ${trayExecutables.length}.');
    }
    await trayExecutables.single
        .copy('${output.path}/fraktal_gateway_tray.exe');
    await File('${project.path}/deploy/windows/run_gateway.ps1')
        .copy('${output.path}/run_gateway.ps1');
    await File('${project.path}/deploy/windows/gateway.args.example')
        .copy('${output.path}/gateway.args.example');
    // The combined Windows installer also packages the native HMI desktop app,
    // so build it now. The installer builder expects the Release output below.
    await _run(
      flutter,
      ['build', 'windows', '--release', '--no-pub'],
      workingDirectory: hmiRoot.path,
    );
    // The HMI Release build produces fraktal_ads.dll when the TwinCAT ADS SDK is
    // present (it self-skips otherwise). Ship it beside the gateway exe so the
    // gateway can use an ads:// PLC endpoint; without it, ads:// simply fails to
    // load the library and opc.tcp:// still works.
    final hmiAds = File('${hmiRoot.path}/build/windows/x64/runner/'
        'Release/fraktal_ads.dll');
    if (hmiAds.existsSync()) {
      await hmiAds.copy('${output.path}/fraktal_ads.dll');
      stdout.writeln('Bundled fraktal_ads.dll (ADS PLC transport available).');
    } else {
      stdout.writeln('fraktal_ads.dll not built (TwinCAT ADS SDK absent); '
          'the gateway will support opc.tcp:// endpoints only.');
    }
    await _run(Platform.resolvedExecutable, [
      'run',
      '${project.path}/tool/build_windows_installer.dart',
      output.path,
    ]);
  } else {
    final runScript = await File('${project.path}/deploy/linux/run_gateway.sh')
        .copy('${output.path}/run_gateway.sh');
    await Process.run('chmod', ['0755', runScript.path]);
    await File('${project.path}/deploy/linux/fraktal-gateway.service')
        .copy('${output.path}/fraktal-gateway.service');
    await File('${project.path}/deploy/linux/fraktal-gateway.env.example')
        .copy('${output.path}/fraktal-gateway.env.example');
    // The multi-PLC form: one templated unit instance per controller.
    await File('${project.path}/deploy/linux/fraktal-gateway@.service')
        .copy('${output.path}/fraktal-gateway@.service');
    await File('${project.path}/deploy/linux/fraktal-gateway-instance.env.example')
        .copy('${output.path}/fraktal-gateway-instance.env.example');
  }
  stdout.writeln('Gateway package: ${output.path}');
}

Future<String> _findCmake() async {
  final pathResult = await Process.run(
    Platform.isWindows ? 'where.exe' : 'which',
    ['cmake'],
    runInShell: false,
  );
  if (pathResult.exitCode == 0) {
    final first = '${pathResult.stdout}'
        .split(RegExp(r'[\r\n]+'))
        .firstWhere((line) => line.trim().isNotEmpty)
        .trim();
    if (first.isNotEmpty) return first;
  }
  if (Platform.isWindows) {
    final programFiles = Platform.environment['ProgramFiles'];
    if (programFiles != null) {
      final visualStudio = Directory('$programFiles/Microsoft Visual Studio');
      if (visualStudio.existsSync()) {
        for (final version in visualStudio.listSync().whereType<Directory>()) {
          for (final edition in version.listSync().whereType<Directory>()) {
            final candidate =
                File('${edition.path}/Common7/IDE/CommonExtensions/'
                    'Microsoft/CMake/CMake/bin/cmake.exe');
            if (candidate.existsSync()) return candidate.path;
          }
        }
      }
    }
  }
  throw StateError('CMake was not found. Install CMake and a C/C++ toolchain.');
}

Future<String> _findFlutter() async {
  final result = await Process.run(
    Platform.isWindows ? 'where.exe' : 'which',
    [Platform.isWindows ? 'flutter.bat' : 'flutter'],
    runInShell: false,
  );
  if (result.exitCode == 0) {
    final first = '${result.stdout}'
        .split(RegExp(r'[\r\n]+'))
        .firstWhere((line) => line.trim().isNotEmpty)
        .trim();
    if (first.isNotEmpty) return first;
  }
  throw StateError(
    'Flutter was not found. The gateway package includes the Web HMI and '
    'requires the Flutter SDK on the build machine.',
  );
}

Future<void> _copyDirectory(Directory source, Directory destination) async {
  destination.createSync(recursive: true);
  await for (final entity in source.list(followLinks: false)) {
    final name =
        entity.uri.pathSegments.where((segment) => segment.isNotEmpty).last;
    final target = '${destination.path}/$name';
    if (entity is Directory) {
      await _copyDirectory(entity, Directory(target));
    } else if (entity is File) {
      await entity.copy(target);
    }
  }
}

Future<void> _run(
  String executable,
  List<String> arguments, {
  String? workingDirectory,
}) async {
  stdout.writeln('> $executable ${arguments.join(' ')}');
  final process = await Process.start(
    executable,
    arguments,
    workingDirectory: workingDirectory,
    mode: ProcessStartMode.inheritStdio,
    runInShell: Platform.isWindows && executable.toLowerCase().endsWith('.bat'),
  );
  final result = await process.exitCode;
  if (result != 0) {
    throw ProcessException(executable, arguments, 'Command failed', result);
  }
}
