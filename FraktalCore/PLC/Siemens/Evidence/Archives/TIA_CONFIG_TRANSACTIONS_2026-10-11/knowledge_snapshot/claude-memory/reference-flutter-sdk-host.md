---
name: reference-flutter-sdk-host
description: "Where the Flutter/Dart SDK actually is on this workstation (not the AGENTS.md path, not on PATH)"
metadata:
  node_type: memory
  type: reference
  originSessionId: 557e92d1-b71c-4c7c-8e05-907ccca6dc19
  modified: 2026-10-08T20:25:29.368Z
---

Flutter **3.47.6** (Dart 3.13.5) is at `C:\Users\Siemens\Documents\FlutterSdk\flutter\bin` — NOT on PATH and NOT at the `C:\Apps\FlutterSdk\v3475` path AGENTS.md names (that folder does not exist, checked 2026-10-08). Prepend it to PATH per command; use `flutter pub get --enforce-lockfile` (3.47.6 resolved the 3.47.5 lockfile unchanged). Related: [[project-siemens-port]].
