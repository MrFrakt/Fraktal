/// A small, durable diagnostic log for problems that only show up on a real
/// panel: a freeze, a slow frame, an uncaught error.
///
/// Each line is appended and flushed synchronously, so the log survives a
/// force-closed HMI, and the LAST line written shows where the app stopped.
/// On Windows it is `%APPDATA%\Fraktal\HMI\hmi.log` (bounded: rotated to
/// `hmi.log.1` at 1 MiB). On Web there is no file, and lines go to the console.
library;

import 'dart:async';
import 'dart:ui' show FrameTiming, PlatformDispatcher;

import 'package:flutter/foundation.dart';
import 'package:flutter/scheduler.dart';

import 'hmi_log_stub.dart' if (dart.library.io) 'hmi_log_io.dart' as sink;

/// Where the log is written, or empty where there is no file (Web, tests).
String get hmiLogPath => sink.logPath;

/// Appends one timestamped line.
void hmiLog(String event) {
  final line = '${DateTime.now().toIso8601String()} $event';
  if (kDebugMode) debugPrint('[hmi] $event');
  try {
    sink.append(line);
  } on Object {
    // A diagnostic log must never become the fault.
  }
}

/// Runs [body], logging its start and how long it took. The start line is what
/// names the culprit when [body] never returns.
Future<T> hmiTimed<T>(String label, Future<T> Function() body) async {
  hmiLog('$label: start');
  final watch = Stopwatch()..start();
  try {
    return await body();
  } finally {
    hmiLog('$label: done in ${watch.elapsedMilliseconds} ms');
  }
}

/// Synchronous [hmiTimed].
T hmiTimedSync<T>(String label, T Function() body) {
  final watch = Stopwatch()..start();
  try {
    return body();
  } finally {
    hmiLog('$label: ${watch.elapsedMilliseconds} ms');
  }
}

/// A frame slower than this is logged with its build and raster split.
const Duration kSlowFrame = Duration(milliseconds: 250);

bool _installed = false;

/// Logs slow frames and every uncaught error. Called once, from `main`.
void installHmiDiagnostics() {
  if (_installed) return;
  _installed = true;
  hmiLog('HMI started${hmiLogPath.isEmpty ? '' : ' (log: $hmiLogPath)'}');
  SchedulerBinding.instance.addTimingsCallback((List<FrameTiming> timings) {
    for (final frame in timings) {
      if (frame.totalSpan < kSlowFrame) continue;
      hmiLog('slow frame: total ${frame.totalSpan.inMilliseconds} ms, '
          'build ${frame.buildDuration.inMilliseconds} ms, '
          'raster ${frame.rasterDuration.inMilliseconds} ms');
    }
  });
  final previousFlutter = FlutterError.onError;
  FlutterError.onError = (details) {
    hmiLog('flutter error: ${details.exceptionAsString()}\n${details.stack}');
    previousFlutter?.call(details);
  };
  final previousPlatform = PlatformDispatcher.instance.onError;
  PlatformDispatcher.instance.onError = (error, stack) {
    hmiLog('uncaught error: $error\n$stack');
    return previousPlatform?.call(error, stack) ?? false;
  };
}

/// Logs [label] once the next frame has been built and handed to the raster
/// thread - "the screen caught up" after an action such as a publish.
void hmiLogNextFrame(String label) {
  final watch = Stopwatch()..start();
  SchedulerBinding.instance.addPostFrameCallback((_) {
    hmiLog('$label: next frame built after ${watch.elapsedMilliseconds} ms');
  });
  SchedulerBinding.instance.ensureVisualUpdate();
}
