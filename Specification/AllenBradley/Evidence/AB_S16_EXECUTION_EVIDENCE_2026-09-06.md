# Fraktal/AB S16 — command handshake and mode execution: executed on the v33 bench

**Spike:** S16 command-handshake and mode execution on Logix

**Result:** **EXECUTED AND PASSING. The Core §6.1 handshake and the §6.2 mode
chain run on a physical CompactLogix 5370 through generated composition. All
nine phases pass, identically, on three consecutive runs: a held command is
BUSY at LOW severity with reason 6101 and no `Error`; a fault raises `Error`
with `ErrorID` 6102 at HIGH severity in ERROR state; abort never self-resumes;
and the module AOI ran ahead of sequence intent on every scan with a
command/result latency of exactly one scan. Getting there required fixing two
defects in the executor that no unit test could have caught, one of which had
been silently producing unrepeatable results.**

**Date:** 2026-09-06

**Repository revision at start:** `54bcba0`

**Scope:** the section 7 import package of
[`AB_S16_COMMAND_HANDSHAKE_DECLARATION_2026-09-06.md`](AB_S16_COMMAND_HANDSHAKE_DECLARATION_2026-09-06.md),
executed on the licensed Studio 5000 v33 workstation under explicit,
freshly-granted download authorization with all I/O disconnected. One download
occurred. No tag write outside the fixture's five declared inputs, and no mode
change, fault clear, clock set, firmware, controller-network or physical-I/O
operation of any kind.

## 1. Why this record exists, and which workstation it is

The declaration record was written on a machine with no Studio v33 and no
established SDK entitlement, so it deliberately recorded nothing about
execution and did not hash the generated L5X. This record supplies both.

**This is not the 2026-09-06 VM** described in
[`AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md),
which that addendum found blocked. It is `DESKTOP-07VCTIN`, the workstation the
access runbook was verified on. The two are distinguishable by measurement, and
were distinguished before anything was run:

| Item | This workstation | The blocked 2026-09-06 VM |
|---|---|---|
| Operating system | Windows 10 Pro `10.0.19044` | Windows 11 Pro `10.0.22631` |
| Studio 5000 revisions | `v21`–`v37`, **including `v33`** | `v37`, `v38` only — no v33 |
| Studio v33 binary | `V33.00.00`, SHA-256 `B1ADC6962DC04863FFD032D3721791B1FD4E7643A6E95AE8A091503001EDE41F` | absent |
| FactoryTalk Linx | `6.50.00` | `6.60.00` |
| Logix Designer SDK | `2.00.00`, `LdSdkServer.exe` `2.0.861.0` | `2.01.00` |
| .NET SDK | `10.0.400` present | none installed |
| Host address | `Ethernet1` `192.168.100.123/24` | no `192.168.100.0/24` adapter |

Three divergences from the runbook's own baseline are recorded rather than
silently accepted: the host address is `192.168.100.123`, not the proven
`192.168.100.99` (same adapter and subnet; the download used USB, so it is not
load-bearing here); the SDK is the **historical** `2.00`/`2.0.861`, not the
`2.02`/`2.2.1109` the runbook calls current; and the runbook's Linx
command-line browse does not work on this workstation at all.

That last one is an end-of-session check that **failed**, and it is recorded as
a failure. `FTLinxCfgIETool.exe /Browse` returns
`Failed to browse Fraktal_AB\192.168.100.89, status is 2.`, and it returns the
same `status is 2` for `Ethernet\192.168.100.89` — a driver that demonstrably
exists, since Studio's **Who Active** listed it as `Ethernet, Ethernet` beside
`1789-A17, Backplane` and `USB`, and there is no `Fraktal_AB` alias in that
tree. So the utility itself is failing here, not merely the documented alias.
No driver was added or altered to work around it: that would be a workstation
configuration change, and nothing in this record needed it. Controller
reachability is proved twice over without Linx — Studio's Who Active browsed
USB and downloaded through `Backplane\16`, and every probe here speaks raw
EtherNet/IP or pylogix directly. Treat the runbook's step 4 as unverified on
this machine until someone establishes why the tool fails.

## 2. The SDK entitlement question, answered

The 2026-08-26 blocker recorded that every licensed project creation returned
`No valid license`, with `LDSDK.EXE` missing from the local activation store.
**That blocker does not reproduce on the SDK version this machine now carries.**

Read-only inspection of the FactoryTalk Activation store still shows **no
`LDSDK.EXE` feature in any local licence file** — only `fta.system` and a
single 2009 disk-serial-locked set whose features are all pre-Logix-5000
products — and **no `ftaservers.txt`**, so no activation server is configured.
Studio v33 itself is covered by `rs5000.exe` in that node-locked set. No key
material, host-lock identifier or activation identifier is recorded here.

Nevertheless, SDK `2.00` / client `2.0.861` **creates projects successfully**:

```
[INFO][C:\work\seed_v33.ACD] CreateProject started
[INFO][C:\work\seed_v33.ACD] CreateProject succeeded.
[INFO][C:\work\seed_v33.ACD] SaveAsAsync succeeded
```

The harmless open/export probe then passed as well, reporting
`InputUnchanged: true` and an empty `CommunicationsPath`. **The correct
conclusion is narrow:** the `2.00` path does not gate on an `LDSDK.EXE`
feature, and the 2026-08-26 failure belongs to the `2.02` / `2.2.1109` client,
which is not installed here and could not be re-tested. Nothing in this record
claims the entitlement was restored.

### A build divergence that must not be papered over

**The repository's probe cannot be built on this machine as pinned.**
`Fraktal.Ab.OfflineProbe.csproj` pins `RockwellAutomation.LogixDesigner.CSClient`
`2.2.1109` and targets `net10.0`. That package is absent from this machine and
from nuget.org, and although .NET SDK `10.0.400` is installed, the **x86**
runtime here is `8.0.7` only — a `net10.0`/`win-x86` build compiles and then
fails to launch with `You must install or update .NET to run this application`.
The probe must be `win-x86` to match Rockwell's 32-bit client.

Every SDK stage in this record therefore ran a build made **outside the
repository**, from `Program.cs` **byte-identical** to the tracked source
(`0b0872f143b7081fda1c0d590175df94ae68ba75d21847b38bc88b6e2627c7e0`), with
exactly two project changes: `net8.0` and package `2.0.861` — the versions this
workstation actually has. The seed is a genuine SDK artifact, not hand-authored.
The repository file was not modified, and reconciling that pin against the two
workstations is left open rather than decided here.

## 3. Offline stages

| Stage | Required | Result |
|---|---|---|
| Seed through `--create-seed` | SDK, never hand-authored | **PASS** |
| Fixture generation | `PhysicalIoReferences` = 0 | **PASS** — 0, I/O inhibited, output updates disabled |
| SDK import | `Warnings="0" Errors="0"` | **PASS** — and log-gated, `Clean: true` |
| Studio v33 Verify Controller | 0 errors, 0 warnings | **PASS** |
| Canonical round trip | structurally identical | **PASS** |
| Construct census | 2 AOIs, 1 UDT, 1 program, 1 routine, 1 task | **PASS** |

The generator reported `PhysicalIoReferences: 0`, `EmbeddedIoInhibited: true`,
`TaskOutputUpdatesDisabled: true`, 39 context members, and task `FRK_S16Task`
PERIODIC at 10 ms with a 500 ms watchdog.

The import log gate returned `Clean: true` with one
`<Summary Warnings="0" Errors="0"/>` and `SdkErrorEventCount: 0`. Studio v33
**Verify Controller** returned:

```
"Errors": 0, "Warnings": 0, "CountsMatch": true,
"StatusText": "Verify complete with no errors or warnings.",
"Summary": "Complete - 0 error(s), 0 warning(s)",
"InputUnchanged": true, "ClosedCleanly": true
```

Studio Verify is the semantic gate; SDK `BuildAsync` was not used and is not
recorded as one.

**The canonical comparison is export-against-export**, as
`fraktal_ab_phase0_gate.py` defines it: the SDK legitimately rewrites the
generated declaration on first import, so comparing the generator's output with
its first export is not the round trip and reports a false difference. The
census is what bridges generated to first export. Both passed:

- round trip pass 1 vs pass 2 — `Equivalent: true`, identical canonical hash;
- census generated vs first export — `Differences: []`, `Equivalent: true`.

Verified independently on the exported file: exactly one program routine
(`FRK_S16Main`, which is `MainRoutineName`, so no unreferenced routine), the
other two `Routine` elements being the two AOI bodies; **zero** `Local:` or
`Discrete_IO:` operands anywhere; `Discrete_IO` inhibited; and the context UDT
carrying **39 `DINT` members with no `BOOL` or `BIT` member and none hidden**,
which keeps the recorded S12 hole a hole. The scope-exclusion scan for
`Recipe`, `ParCfg`, `Manifest`, `Registry`, `Mailbox`, `Traceability` and
`ReleaseReport` returned zero for all seven.

**`fraktal_ab_phase0_gate.py` has no S16 leg** — the string `s16` does not occur
in it, so the gate still generates and round-trips only S1, S2, S11, S12, S4
matrix, S7 and S9. The stages above were run by hand in that gate's exact
order and semantics. Registering S16 in the gate is owed.

## 4. The download

Target verified immediately before, by fixed read-only probe and by USB
identity: `1769-L24ER-QB1B/A LOGIX5324ER`, revision **`33.014`**, serial
**`7036B510`**, `serial_matches: true`; USB present as
`USB\VID_14C0&PID_001F\7036B510`. All I/O disconnected, confirmed by the user.
Authorization was requested fresh after the offline stages and granted; the
prior sessions' authorizations were treated as historical and not inferred.

**Two automated download attempts crashed Studio v33 outright**, at the same
step, with two different faults:

| Attempt | Invocation | Fault |
|---|---|---|
| 1 | `PostMessage` `BM_CLICK` on Who Active `32086`, the runbook's method | `0xc0150010` — SxS early deactivation |
| 2 | UIA `InvokePattern` on the same button | `0xc0000005` — `EXCEPTION_ACCESS_VIOLATION` |

```
Fatal Error!
Application Path: ...\Studio 5000\Logix Designer\ENU\v33\Bin\LogixDesigner.Exe
Version: V33.00.00 (Release)
Location: 0xffffffffffffffff+-1
Error 0xc0000005 (-1073741819)
EXCEPTION_ACCESS_VIOLATION - An "access violation" exception was generated.
One project file is currently open:
    C:\WORK\s16_fixture.ACD
```

Everything up to the click verified on both attempts: the Who Active tree node
read `16, 1769-L24ER-QB1B, FraktalPhase0`, and path pane `1335` read
**`Backplane\16`**, re-read immediately before invoking. **Neither crash
changed the controller**: identity, `state` 3 and `device_status` 48 were
byte-identical before and after, and the S9 fixture still answered reads. The
disposable ACD hash was unchanged.

Two corrections to what was believed mid-session, both recorded because they
changed the diagnosis: the crash was first attributed to a newer FactoryTalk
Linx, but this machine runs Linx **6.50.00**, the *historical* Phase 0 version;
and the runbook's note that "native Studio buttons did not expose an
InvokePattern" is **not true of this dialog** — `1456` and `32086` both expose
`InvokePatternIdentifiers.Pattern`. Disk (131 GB free) and memory (21.5 GB free)
were ruled out. **No root cause was established.** Automated download of this
fixture through Who Active on this workstation is recorded as an open blocker,
not as a solved problem.

**The download was then performed manually by the user**, in the Studio session
opened on the verified ACD, and completed successfully. Confirmed afterwards by
measurement rather than by the on-screen message:

- Studio's title changed from `[1769-L24ER-QB1B 33.11]` to `[... 33.14]`, the
  `controller minor 11 -> 14` binding change S2 already documented;
- `FRK_S16_ScanCount`, `FRK_S16_OrderFail`, `FRK_S16_LatencyBad` and
  `FRK_S16_Command` all read `Success`;
- `FRK_S9_Freeze` now returns **`Path segment error`** — the S9 fixture is gone,
  replaced, exactly as intended.

## 4a. Addendum — the download crash, diagnosed from the dumps

Added after the fact, from the two crash dumps Studio left behind. They are
evidence, and they were read before anything was deleted.

**Both crashes are the same fault.** §4 above reported "two different faults"
from the two codes in Studio's own fatal-error log. Read from the minidumps
themselves, the exception records are identical:

| | first crash | second crash |
|---|---|---|
| exception code | `0xC0000005` | `0xC0000005` |
| meaning | `EXCEPTION_ACCESS_VIOLATION` | `EXCEPTION_ACCESS_VIOLATION` |
| faulting address | `mfc140u.dll` **+0x2A6C04** | `mfc140u.dll` **+0x2A6C04** |
| access | **read of `0x74`**, unmapped | **read of `0x74`**, unmapped |

The `0xc0150010` in the first log is what Studio's own crash handler reported,
not the fault that occurred. Reading offset `0x74` from a null base is a
null-pointer dereference — a member access on an object that was expected to
exist and did not — inside the shared MFC runtime, at the same instruction both
times.

**It is not "UI Automation crashes Studio".** That hypothesis was tested and
falsified: with the same dialog open, the same selected node and the same UIA
`InvokePattern`, invoking the harmless **Set Project Path** button (`1456`)
left Studio running, and the effect was confirmed on screen — the *Path in
Project* pane changed from `<none>` to `Backplane\16`. Programmatic invocation
of this dialog's native buttons is therefore not inherently fatal. **The fault
is specific to Studio v33's Download command path when it is invoked
programmatically on this workstation.**

Two further facts, both measured, neither sufficient to close the question:

* the MFC runtime is the shared `C:\Windows\System32\mfc140u.dll` at
  **14.40.33816** (VC++ 2015-2022 redistributable, dated 2024). Studio v33 is a
  2020 product and ships no private copy, so it runs against an MFC several
  years newer than the one it was built against. That is a plausible
  contributing condition — but the **manual** download succeeded under exactly
  the same MFC, so the version alone is not the cause;
* disk (131 GB free) and memory (21.5 GB free) were ruled out.

**Root cause, as far as the evidence supports it:** a null-pointer dereference
inside the MFC runtime, reached only through Studio v33's Download command path
under programmatic invocation, on a Studio build running against a much newer
shared MFC than it shipped with. What is *not* established is which pointer, or
why the manual path initialises it and the programmatic path does not — that
needs Studio symbols this workstation does not have.

**Bounded workaround, and its boundary.** The download is performed by a person
in the Studio session, with the target identity re-read immediately beforehand
and all I/O disconnected. That path is proved: it completed here with the
controller-minor rebinding visible in the title bar and the fixture live on the
bench. The boundary is that this is a **deployment** step, not a test step — it
does not make S15's unattended-automation claim true, and §9 keeps that owed.

### The downloaded artifact's provenance

Studio saved the project during the download session, so the file at
`C:\work\s16_fixture.ACD` **no longer hashes to the value §7 records**. That is
the expected post-download rebinding S2 documented (`controller minor 11 → 14`),
not drift in the evidence. Studio's own pre-save backup preserves the artifact
that was Verified `0/0` and downloaded, and it hashes to exactly the recorded
value:

`0AEAF984F4EA97C880979E1884CC971592AFD3A1D836B12FC05FA9E842568904`

The hash in §7 is therefore correct as recorded, and the artifact behind it is
still recoverable. A later diagnostic copy was taken from the post-save file and
did not alter either.

## 5. Two executor defects the unit tests could not catch

The nine-phase matrix did not run clean on first contact with hardware. Both
causes were in `fraktal_ab_s16_execute.py`, and both are fixed here. Neither
was a fixture, L5X, import or Verify problem.

### 5.1 The serial format crash

The tool aborted before its first write:

```
File ".../fraktal_ab_s16_execute.py", line 436, in main
    serial = f"{getattr(device, 'SerialNumber', 0):08X}"
ValueError: Unknown format code 'X' for object of type 'str'
```

`_normalize_serial` already existed in the file and was applied to
`--expect-serial`, but the **controller's** serial went through a raw `:08X`
instead. Real pylogix returns that field as a `str`. The four sibling executors
(S9, S11, S12, phase 0) all call `_normalize_serial(device.SerialNumber)`; S16
was the outlier. `main()` had no test at all, and the fake controller modelled
the serial as an `int`, so nothing exercised the path that reaches hardware.

### 5.2 The observation tore, and made the whole matrix unrepeatable

**This is the finding worth carrying forward.** `_read_context` assembled each
observation from **25 separate CIP reads**, one per member, with no coherence
guard. The fixture task runs at **10 ms** and every counter in the record
advances on its own, so each observation spanned **60–212 ms — roughly 6 to 21
scans — and reported a state the controller never held.**

This is precisely the tearing [`AB_S9_COHERENCE_EVIDENCE.md`](AB_S9_COHERENCE_EVIDENCE.md)
measured, and it is the configuration that record's own rule forbids: a
mutation interval shorter than the read window never converges, and at 10 ms
mutation S9 measured **0 of 10** accepted snapshots. S16 was reading a 10 ms
mutator through a ~120 ms window.

The symptom was not a clean failure but an **unrepeatable** one. Across three
runs of the identical vector:

| phase | run 1 | run 2 | run 3 |
|---|---|---|---|
| `auto_cycle` | pass | fail | fail |
| `fault_error_id` | fail | fail | fail |

and `fault_error_id` reported three *different* observations — `ErrorID` 0,
then **6102**, then 0; `ExecState` 0, 2, 2. One run had already seen the
correct `ErrorID`, which is what showed the fixture was not at fault. A phase
that passes on one run and fails on the next, with nothing changed, is not
evidence in either direction, and the eight phases that "passed" under that
observer were no more trustworthy than the one that failed.

**The fix:** the context is 39 `DINT`s, so one structured read returns the whole
record as a single 156-byte CIP payload — measured exactly 156 bytes,
unpacking at offset 0 to `SchemaVersion` 1, `Par_Speed` 25, `Par_TimeoutMs` 500
— which is atomic on the wire. S9's own rule is that a row small enough for one
request needs no retry at all. `_read_context` now issues that one request and
unpacks it against the declared member layout, failing closed on a short or
non-binary payload.

Observation cost fell from ~120 ms to **~2.7 ms**, below the 10 ms task period.

### 5.3 A third defect the fix then exposed

With coherent observations, `auto_cycle` failed *deterministically*. Its
assertion required `ErrorCount == 0` and `AbortCount == 0` — the fixture's
**lifetime** counters — while its own stated expectation, and the declaration's
matrix, say "no Error and no Aborted", which are the instantaneous flags and
were both clear. The fixture free-runs from the moment it is downloaded and
nothing resets it, and the vector's own later phases deliberately raise aborts
and faults. So the phase could only ever pass on the **first** run after a
download, and its `CycleCount >= 1` limb was equally satisfiable by history
alone without a single cycle completing during the phase.

It now takes a baseline immediately before the phase and requires that
`CycleCount` **advanced** while `ErrorCount` and `AbortCount` did **not** — a
claim about this cycle rather than about the fixture's lifetime. Phase 3 should
confirm that reading of the matrix.

### 5.4 Tests

Ten tests added; the AB suite is green at **218** (was 208).

The coherence tests are built on a controller that advances a generation on
every request, mirroring the S9 fixture's design — every member carries the
current generation, so a coherent snapshot is all-equal and a torn one names
the generations it straddles. They were verified to **fail against the old
observer** before the fix was kept: 4 failures, the key one reporting
`AssertionError: 25 != 1 : members came from more than one generation: the
snapshot tore` — one generation per member read, the tearing quantified. A
companion test asserts that a per-member sweep *does* tear, so the guard cannot
pass vacuously. The fake controller's counters now accumulate as a real
fixture's do, and it returns a `str` serial as real pylogix does.

## 6. The executed matrix

Run with the repository's fixed probe and hash-verified `pylogix 1.1.5`
(`--require-hashes`) in a virtual environment **outside** the repository.
Values are reported as status and shape; the record carries
`values_redacted: true`.

**Three consecutive runs, all nine phases passing, identically.**

| # | Phase | Result | Observed |
|---|---|---|---|
| 1 | `auto_cycle` | **PASS** | a further cycle completed, no `Error`, no `Aborted` |
| 2 | `abort_no_resume` | **PASS** | `Aborted` raised, ABORTED state, `Busy` stayed clear |
| 3 | `execute_drop_ready` | **PASS** | dropping Execute mid-BUSY returned READY, `Busy` clear |
| 4 | `held_low_reason` | **PASS** | `ExecState` 1 BUSY, `Held` 1, reason **6101**, severity **0 LOW**, `Error` **0** |
| 5 | `held_auto_resume` | **PASS** | progress resumed on its own, no re-issue |
| 6 | `fault_error_id` | **PASS** | `Error` 1, `ErrorID` **6102**, `ExecState` **3 ERROR**, severity **2 HIGH** |
| 7 | `restart_by_reissue` | **PASS** | a fresh Execute edge restarted the command |
| 8 | `mode_switch_midcycle` | **PASS** | mode change observed, chain stood down to its init step |
| 9 | `ordering_and_latency` | **PASS** | `OrderFail` **0**, `LatencyBad` **0**, `LatencyScans` **1** |

Phases 4, 6 and 9 returned **byte-identical observations on all three runs**.

### Timings against the fixture's task period

The fixture task is **PERIODIC at 10 ms**, watchdog 500 ms. Phase elapsed times
across the three runs:

| Phase | run 7 | run 8 | run 9 |
|---|---:|---:|---:|
| `auto_cycle` | 88.5 | 84.6 | 100.5 |
| `abort_no_resume` | 3.2 | 1.7 | 2.8 |
| `execute_drop_ready` | 70.2 | 30.1 | 71.0 |
| `held_low_reason` | 16.9 | 17.1 | 17.1 |
| `held_auto_resume` | 16.3 | 16.1 | 2.8 |
| `fault_error_id` | 2.8 | 2.9 | 2.9 |
| `restart_by_reissue` | 2.8 | 2.7 | 2.8 |
| `mode_switch_midcycle` | 28.6 | 2.7 | 2.8 |
| `ordering_and_latency` | 0.0 | 0.0 | 0.0 |

All values are milliseconds. A single observation now costs about **2.7 ms**,
which is where the floor comes from: a phase whose state is already settled
reports one round trip, below one 10 ms scan. `auto_cycle` at 85–100 ms is the
plant moving 100 units at 25 units per scan — four scans per move plus the
chain's own steps — and is the fixture working, not transport cost.

**Phase 9 restates the S11 ordering rule for commands and it held:** the module
AOI ran unconditionally ahead of sequence intent on every scan, and the interval
between the chain raising Execute and the module accepting the edge was exactly
one scan, every time, with the fixture's own `OrderFail` counter at zero.

### Write surface and cleanup

Every run wrote only the five declared tags — `FRK_S16_Command`,
`FRK_S16_Abort`, `FRK_S16_ModeSelect`, `FRK_S16_HoldRequest`,
`FRK_S16_FaultRequest` — and every run's `_disarm` reported **all five
`cleared`**, including the runs that failed. The fixture fingerprint passed
before the first write on every run. Cleanup was independently re-verified
afterwards by read-only probe.

## 7. Artifacts and hashes

| File | SHA-256 |
|---|---|
| `seed_v33.ACD` | `1EB6082E5A63AA2E9BB9FEF8B0277976255FD9C39C074303F2409860A52D0406` |
| `seed_v33.L5X` | `0E596EC140BB4FA24B089942A6AE3825ABC7B0898E06AB0D2298252FA5475E7A` |
| seed open/export probe L5X | `93A8B4C790F99FE98B739CA4B1186D83E73364686A5201CA7D625C1D80071764` |
| **`s16_fixture.L5X`** (generated) | **`103DF28E902F1B1A67DDDE491169C3CC8488051F2F6C5ED1318143746EEAC0BC`** |
| **`s16_fixture.ACD`** (imported, verified, downloaded) | **`0AEAF984F4EA97C880979E1884CC971592AFD3A1D836B12FC05FA9E842568904`** |
| `s16_roundtrip.L5X` (export pass 1) | `015237D4861FCEECAB00301EE991B7C1AEEA1B8F1D55B964E6B97D6DFCEE19C3` |
| `s16_pass2.ACD` | `EAF2C6E759E51ABA70CFDFCE17F1CD2234D16CFF01114BBA954F4C12B05A7012` |
| `s16_pass2.L5X` (export pass 2) | `8EE25BD5544DED90B3551057182BD75D922D950E8E01DA8CAF6B7F3419E6423A` |
| **canonical, both exports** | **`427129CAA95C68338BC9D8823C186C8866B460EAFF4C88BD85BDE3751BCF9958`** |

The declaration record deliberately left the generated L5X unhashed because it
is a function of a seed only a licensed workstation can create. The seed and
the L5X above are that artifact.

| Tool | SHA-256 |
|---|---|
| `tools/fraktal_ab_s16_fixture.py` (unchanged) | `F9579BE24AD20A124BDF027F5A9BD55968608856A7B06F80062646D00E06F86C` |
| `tools/fraktal_ab_s16_execute.py` (fixed) | `49D91EE5B68F623960DE14A5BC705C49B93E4241B4E3B220748D574EF158E009` |
| `tools/test_fraktal_ab_s16_fixture.py` (unchanged) | `B96296543AFB4FBB700906C5BE5A1590DA8919F3581901D856CCC0BFED26E379` |
| `tools/test_fraktal_ab_s16_execute.py` (extended) | `E50B6741EA854D70B373A0825EE9FBA198DE56A57FC9CD6CC200A80A37FCE03E` |

Project artifacts live in a disposable `C:\work` outside the repository and are
not committed, per the runbook.

## 8. Bench handoff state and rollback

The controller **retains the clean S16 fixture in Remote Run**, all five
writable inputs restored to zero and verified. Identity re-read at close:
`1769-L24ER-QB1B/A LOGIX5324ER`, `33.014`, `7036B510`, `state` 3,
`device_status` 48, PTP disabled and `is_synchronized` false.

**The S9 rollback path is recorded, not executed.** Returning the bench to the
S9 coherence fixture means regenerating it from a seed with
`fraktal_ab_s9_coherence_fixture.py`, importing and verifying it as section 3
above, and downloading it over the same USB `Backplane\16` route under fresh
authorization — the procedure and its acceptance criteria are in
[`AB_S9_COHERENCE_EVIDENCE.md`](AB_S9_COHERENCE_EVIDENCE.md) §2 and §8. Note
that the S9 fixture's own tags are now absent from the controller, so that
record's handoff state no longer describes the bench.

No firmware, fault-clear, clock, controller-network, safety, SD-card or
physical-I/O operation occurred at any point.

## 9. What S16 still owes

1. **Register S16 in `fraktal_ab_phase0_gate.py`.** The gate has no S16 leg, so
   none of section 3 is reproducible by running the gate.
2. **Automated download on this workstation.** Two invocation methods crashed
   Studio v33 with two different faults and no root cause; the successful
   download was manual. S15's unattended-automation claim is not advanced by
   this record.
3. **Reconcile the offline probe's package pin** — `2.2.1109`/`net10.0` against
   a workstation carrying `2.0.861` and an x86 `8.0.7` runtime.
4. **Core §6.1 still owes an answer on held-plus-timeout.** The fixture freezes
   the elapsed-time accumulator while held, so a held command never times out.
   That remains a fixture decision, and this execution does not settle it: the
   matrix never held a command past its 500 ms timeout.
5. **The `BOOL`-member UDT layout is still unmeasured.** This fixture is 39
   `DINT`s, and a production binding wanting real `BOOL` members in a public
   contract UDT is an S12 rerun, not an assumption.
6. **MANUAL mode is only lightly exercised** — one command per request, observed
   through the mode switch of phase 8. The AUTO chain carried the evidence.
7. **The Linx command-line browse fails on this workstation** with `status is 2`
   for every path tried, including a driver Studio can see. The runbook's
   step 4 end-of-session check cannot currently be satisfied here.

## 10. Status

| Item | State |
|---|---|
| S16 declaration and generator | complete, unchanged |
| S16 import package | **executed on the licensed v33 workstation** |
| S16 execution matrix | **executed; nine of nine phases pass, three consecutive runs** |
| S16 spike | **PASS** for the §6.1 handshake and §6.2 mode chain on the pinned v33 baseline |
| R0–R6 | unchanged; no gate state changes on this record |

No conformance claim is made. No production Fraktal/AB runtime or
module-library code was written, and none is authorized until every R0–R6 gate
records PASS.
