# Echo authorized restart and startup crash — 2026-10-23

**The authorized restart failed. S3h diagnostics have not run.** The owner
approved `call_37bd66c3442340b08084fd7b2deb2ce5:0`, “Approve guarded Echo
restart”, for exact virtual controller 601FC87B / 127.0.0.1 / slot 0 / v38.011.
The helper passed its fresh GUID/serial/firmware/slot/Remote/no-fault and
ClosedExternally/no-process/no-listener guards. It applied disable, then
requested enable once. The emulator exited with code 1 during enable, and
the SDK returned ServiceException. That one-shot approval is consumed.

| Outcome | Measured result |
|---|---|
| Power flag sequence | true → false → true; enable request reports emulator startup failure |
| Post-state | Enabled, ClosedExternally, RemoteProgram, Remote, not faulted |
| Service / port 44818 | Running / no listener |
| PLC downloads / tag writes / mode commands | 0 / 0 / 0 |
| Fault clears / clock changes | 0 / 0 |
| Original diagnostic session | Not started; approval b76d12f2… remains recorded and unused |
| Source pins | All 159 existing project and two diagnostic files unchanged |
| Controller definition / retained-state files | Preserved; no agent deletion or file modification |

The Windows Application events for EchoRestart.exe describe the SDK wrapper's
unhandled ServiceException (managed exception 0xE0434352). Separately, the
fresh native emulator dump records **0xC0000005 in libComms.dll**, v38.011
firmware package 979cf5b0-3243-581d-819c-2c9f87041c39, module offset
**0x50C2A4**, exception parameters [0, 0]. The x86 EBP-chain walk returns
libComms offsets 50C2A4, 53068B, 5306B4, 36BC94, 465761, 23DF2E and AB024,
followed by msvcrt/kernel32/ntdll thread frames. It is a frame-chain observation
without private symbols, not a full symbolized root-cause analysis. The DLL
has no named executable exports to refine those internal functions.

Service logs show that the earlier Windows shutdown timed out and forced the
emulator process closed. They also show startup exit code 1 when the service
first restarted, before this authorized attempt. The runtime pwrDown.dat is
43,164,904 bytes; its timestamps/hashes and related-state metadata are recorded.
These observations do not prove retained-state corruption. No raw state file
was reset, renamed or deleted, and no controller recreation was attempted.
The SDK's generic deletion suggestion was not acted on.

The 1,035,901,098-byte native dump remains in its original vendor folder.
It was not copied or archived. Only exception/module metadata and bounded
frame-chain control addresses were read and recorded; no global-memory or
stack-argument values are exported. No credential file is archived. The
metadata parser and frame-chain reader are included for review/reproduction.

Rockwell's [Echo 4.00 release notes](https://compatibility.rockwellautomation.com/GeneratedReleaseNote.aspx?v1=66077) document an initialization
issue involving ASLR and recommend restarting the Windows host. A host reboot
is the next supported recovery step to consider; ASLR is unconfirmed in this
case. If it persists afterward, vendor diagnosis is needed before selecting
a state reset, controller recreation or firmware change. No such additional
operation is authorized by the completed one-shot restart approval.

The unchanged S3h C6 image, 79% Capacity and 2,149 AB / 74 root test evidence
remain bound. They do not establish current controller readiness. The native
baseline identity/session/documents cannot be verified while no controller is
listening, so the prepared diagnostic download stays blocked at its original
guards. Historical 39 successful comparisons and 31 baseline regressions remain
at their recorded scope; no new acceptance is claimed. V2 remains inactive.

Work folder: `C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb`. Payload:
[manifest](AB_S3H_CANONICAL_ECHO_RESTART_2026-10-23/manifest.json). It retains all restart logs, metadata and
source hashes, and references the 36 prior immutable canonical records.
No commit or push.
