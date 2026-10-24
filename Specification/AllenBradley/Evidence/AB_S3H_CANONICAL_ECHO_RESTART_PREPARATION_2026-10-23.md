# Echo ClosedExternally restart preparation — 2026-10-23

The owner reports Logix Echo running. The service is Running, but read-only
SDK metadata reports controller 601FC87B as ClosedExternally. No emulator
process or port 44818 listener exists. Diagnostic approval remains recorded
and unused. No new controller-changing operation has run.

| Read-only target observation | Value |
|---|---|
| Controller GUID | 91dec7d6-8ac3-45c9-ab2e-0d039c7006fd |
| Serial / address / slot | 601FC87B / 127.0.0.1 / 0 |
| Firmware | ControlLogix 5580 Emulator, 38.011 |
| Enabled / SDK error | true / ClosedExternally |
| Mode / keyswitch / fault | RemoteProgram / Remote / false |
| Emulator / CIP listener | Absent / absent |
| Loaded project / project path | Empty SDK strings; persisted-image content remains unknown until emulation is available |

The older inspection summary serialized the SDK mode as 2. Reflection of the
installed public SDK enum confirms 2 means RemoteProgram. A new read-only
metadata utility exposes enabled/error/project fields; it invokes ReadController
only. Its first build correctly stopped on Windows platform annotation CA1416;
targeting net10.0-windows fixes that build, with zero warnings/errors. The host
has the net10 reference pack, and this utility references the already installed
Echo SDK assemblies rather than downloading packages.

Prepared restart: a one-shot public SDK UpdateController with only IsEnabled
changed from true to false, then false to true. Before use it verifies exact
serial, GUID, address, slot, firmware 38.011, Remote keyswitch, no fault,
ClosedExternally/RemoteProgram/enabled state, and no emulator/listener. It
refuses if the target has recovered or changed. Each state-changing request
is preceded by a fresh SDK target check. If disable reports an error after
taking effect, the approved enable is completed only after exact-target checks;
there is no repeated disable or retry of an already requested enable. A one-shot
attempt file prevents an unreviewed repeat.

| Preparation gate | Result |
|---|---|
| Restart helper build | Pass, zero warnings/errors |
| Offline authorization tests | Six pass: current approval, restart permission, exact serial and fault/clock exclusions |
| Controller update requests executed | None |
| Restart approval / attempt file | Absent; false template only |
| Existing diagnostic image/sources | Unchanged; original diagnostic approval is separate and unused |

This restart is an additional controller power-state operation. It requires
current explicit authorization under AGENTS.md §3a; the diagnostic download
approval is not being reused for it. The restart performs no project download,
keyswitch/mode command, network edit, fault clear or clock set.

After a successful restart, read-only CIP identity/fault/keyswitch, MANUAL/idle,
HMI logout and five-document/policy checks must pass before resuming the
already approved diagnostic session. If the loaded baseline cannot be verified,
the workflow stops before any download. Empty SDK project strings alone never
authorize overwriting a controller. S3h remains incomplete; V2 stays inactive.
No commit or push.

Work folder: `C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb`. Helper source:
`EchoRestart/Program.cs`. Payload:
[manifest](AB_S3H_CANONICAL_ECHO_RESTART_PREPARATION_2026-10-23/manifest.json). Credentials and native ACD binaries are not
archived. Earlier stopped-service evidence remains sealed unchanged.
