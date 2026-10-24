# Echo emulator startup crash — root cause via dump + Ghidra, 2026-10-24

Engagement: the Fraktal owner reported "Logix Echo keeps crashing on download".
The Fraktal evidence dirs (`AB_S3H_CANONICAL_ECHO_RESTART_2026-10-23.md`,
`AB_S3H_CANONICAL_ECHO_POST_REBOOT_2026-10-24.md`) had already recorded the
signature: the native emulator (v38.011, firmware package
`979cf5b0-3243-581d-819c-2c9f87041c39`) exits with code 1 on every
controller enable, native exception 0xC0000005 in `libComms.dll +0x50C2A4`
(read of NULL), identical frame offsets every time.

## Targets and provenance

| File | Role | SHA-256 (prefix) |
|---|---|---|
| `...\Firmware Packages\979cf5b0-...\libComms.dll` (31,347,304 B, x86, GCC-built, Rockwell-signed, v38.011) | crashed module, copied to `targets/echo_libcomms/` | see archive |
| `...\Controllers\91dec7d6-...\Root\sd\RockwellAutomation\601FC87B\Faults\FaultDump.dmp` (1,035,743,890 B) | native crash dump of the 00:26 (2026-10-24) startup crash; archived to `Documents\EchoFaultArchive\FaultDump_601FC87B_2026-10-24_0026.dmp` after parsing | — |

Legal basis: black-box observation and decompilation of the owner's lawfully
licensed software for interoperability and defect diagnosis (Directive
2009/24/EC Art. 5(3)/6; workspace AGENTS.md). No protection circumvention:
the module is unobfuscated, and the crash path is an ordinary bug.

## Method

1. Parsed the minidump directly (stdlib): exception stream thread 21232,
   0xC0000005 read at `libComms.dll` RVA **0x50C2A4**, params [0,0]; x86
   CONTEXT EBP=0x4fe5fdc8; module base 0xda000000 (preferred base, no ASLR
   shift). Extracted the stack; return addresses into libComms at RVAs
   0x53068b, 0x5306b4, 0x36bc94, 0x465761, plus 0x23df2e / 0xab024 from the
   Fraktal frame-chain record — matching their evidence exactly.
2. Ghidra headless (`tools/ghidra`, project `echo_libcomms5`). Full analysis
   is not feasible on this host: the GCC exception analyzer and X86 constant
   propagation blow the JVM heap on the 31 MB binary (OOM even at 8G via
   `GHIDRA_HEADLESS_MAXMEM`; the launcher knob is `GHIDRA_HEADLESS_MAXMEM`,
   not MAXMEMORY). Script `scripts/studio5000/java/GhidraCrashAnalyze.java`
   instead derives each frame's function entry directly from the dump: a
   return address minus 5 is an `E8 rel32` call, whose target is the callee
   entry; each successive EBP-chain return address yields the next caller up.
   Only those functions are disassembled and decompiled. Output:
   `logs/ghidra_libcomms10.log`.

## Crash chain (bottom-up, decompiled)

1. **Faulting function `FUN_da50c280` @ RVA 0x50c280** — a record-append
   writer. `CMP dword ptr [ESI],1` with `ESI = [EBP+8] = param_1 = NULL`
   faults. Semantics: if `param_1[0] == 1` (armed), append a 3-word record +
   two timestamp words + flags at cursor `param_1[1]`, bump the cursor,
   wrap at end `param_1[2]` — a trace/telemetry ring-buffer append.
2. **Caller `FUN_da530600` @ 0x530600** — an I/O wrapper: performs a transfer
   of expected length `param_1` via handle `_DAT_db584a38`
   (`func_0xda0a4b18`); asserts the handle and buffer (assert sites 0x18d,
   0x18e guarded by `func_0xda0aff70`). **On a length mismatch it calls
   `FUN_da50c280(*_DAT_dba1a6dc, 0xf8006148, actual, expected, errno)`** —
   i.e. "log the truncated transfer to the trace buffer" — and returns 10.
   The global `*_DAT_dba1a6dc` (pointer to the trace context) is **NULL** on
   this path → the crash.
3. `FUN_da5306a0` — thin wrapper.
4. **`FUN_da36bb40` @ 0x36bb40** — channel state machine: walks a channel
   list (asserts state words 0x1000002/3/5 at offsets 0xc/0x10, spins on
   0x10000001), iterates channel descriptors (28-byte `0x1c` stride, count
   guarded by `len/0x1c`), performing per-channel expected-length I/O via
   (2)/(3); on failure asserts (0x1fb/0x201/0x218/0x21e) and tears down with
   state 0x10000004.
5. **`FUN_da465590` @ 0x465590** — the startup/state-restore orchestrator:
   compares 16-byte persisted-vs-expected identities (project/controller
   GUIDs at structure offsets 0x18/0x1e), then walks the persisted channel
   descriptor table (0x30-byte header + `0x1c` entries) restoring each
   channel.

## Root cause

The emulator's startup restore performs expected-length I/O per persisted
comm channel. Since the 2026-10-23 22:37 force-kill (controller hung on a
fault, service killed it mid-save; `pwrDown.dat` 43,164,904 B is that
force-written state), that restore I/O comes back short/mismatched for the
corrupted persisted state. The error path that should record the failure
dereferences a **NULL global trace context** (`*_DAT_dba1a6dc`) — an
unguarded vendor bug (RVA 0x50c2a4, read of NULL, deterministic) — so the
emulator dies with 0xC0000005, exit code 1, and writes a ~1 GB fault dump
each time. The NULL context is secondary: the *trigger* is the corrupt
retained power-down state; the *crash* is the unguarded trace call.

Both the Oct 11 1.4 GB dump and the Oct 24 1.0 GB dump follow this pattern;
each crash also re-drops a `FaultRecord.bin` in the controller Root and (if a
dump stays in `sd/.../Faults`) re-creates the slow service-start condition
fixed on 2026-10-22 (the 45 s SCM timeout while the service digests the dump
at every start).

## Fix

Cold-boot the virtual controller: archive `Root\FaultRecord.bin`,
`pwrDown.dat`, `pwrDown.inf`, `pwrDownBc.dat` (controller 91dec7d6), restart
the Echo service. The controller then restores from flash (`relfs1/2`,
project intact) instead of the corrupt RAM image; channel restore I/O
succeeds; the buggy error path is never entered. Prepared as the Desktop
script `coldboot-echo-controller.cmd` (2026-10-23). The 1.0 GB dump was
archived out of the Faults dir 2026-10-24 so the next service restart is not
slow-scanned again. Note: the vendor bug remains — any *future* I/O-length
mismatch on an uninitialised trace path can reproduce the crash; the durable
mitigation is to keep fault dumps cleared and, ideally, report the
`libComms.dll 38.011 +0x50C2A4` NULL deref to Rockwell with this analysis.

## Artifacts

- `scripts/studio5000/java/GhidraAnalysisOptions.java`, `GhidraCrashAnalyze.java`
- `logs/ghidra_libcomms10.log` (final run), `ghidra_libcomms{,2..9}.log` (failed attempts, kept)
- `targets/echo_libcomms/libComms.dll`
- Ghidra project `ghidra-projects/echo_libcomms5`
- Fix script: `C:\Users\SoftIndVM\Desktop\coldboot-echo-controller.cmd`
- Dump archive: `C:\Users\SoftIndVM\Documents\EchoFaultArchive\`
