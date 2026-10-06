# Fraktal/AB Phase 0 physical download and execution evidence

**Date:** 2026-08-13  
**Target:** `1769-L24ER-QB1B/A LOGIX5324ER`, firmware `33.014`, serial
`7036B510`  
**Result:** **PASS — v33 import/Verify, two isolated USB downloads, Remote Run,
controller/program-scope and fragmented EtherNet/IP write/read matrices, access
controls, transport/recovery budget, commissioned wall clock, and cleanup**

## 1. Authorization and isolation

The user explicitly authorized download and execution on this physical PLC and
confirmed that all I/O was disconnected. Firmware v37 was explicitly excluded;
the fixture and controller remained at v33. The downloaded task also had
`DisableUpdateOutputs="true"`, and the embedded `Discrete_IO` module was
inhibited. The generated L5X contained zero `Local:` or `Discrete_IO:` operands.

No firmware operation, fault clear, controller network change, or physical-I/O
write was performed. Studio changed Remote Run to Remote Program for each
download and returned the controller to Remote Run afterward. After the
expanded fixture run, one fixed serial- and fixture-guarded operation set only
the controller wall clock from host UTC; §5 records that authorized change.

## 2. Rollback and exact artifact

Before the first download, the successful USB upload was copied outside the
repository to:

```text
C:\Users\Rockwell Automation\Documents\Studio 5000\Projects\Fraktal_Rollback\FIS_Aptiv_Rev1_USB_upload_2026-08-13_serial_7036B510.ACD
```

Its SHA-256 is
`B3A1291ACDBFBD1A84C95354D550FB9A6FC6E908D766789508F8EFB2B83C8B60`.
It matched the successful disposable USB upload byte for byte. This local file
contains the pre-test application and shall not be committed.

The Phase 0 source was generated from a fresh SDK-created v33 project by
[`fraktal_ab_phase0_fixture.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase0_fixture.py).
The corrected generated L5X SHA-256 was
`2F7D82F5A6CE4F5B2D408513B0B50A48C511D91EC3C1CD3679199A9F0FDD2A00`.
SDK conversion reported `Warnings="0" Errors="0"`; Studio v33 **Verify
Controller** reported zero errors and warnings without changing the ACD.

Because Studio normalizes tag order, L5K array/REAL representations, and CDATA
whitespace, the generated L5X was imported, exported, converted once more, and
exported again. The two Studio/SDK exports had different raw hashes but the same
canonical hash
`316F532C7FD32D705A5F6BC3AD18228A71EE12C970638715564F9CFDB38D8887`
after excluding exactly the three known volatile timestamp attributes. The
downloaded canonical ACD SHA-256 before Studio opened it was
`5A5AC11631F18C388CBCB71AE46E7C85CB50CFBFA69D30C40196A3E20AF52D5D`.

The expanded fixture added one controller `DINT[1024]`, controller result
members for its boundary samples/checksum, and controller/program-scope DINT
write/result cases. Its generated L5X SHA-256 was
`08C7AB715215D59DF025BD3EFBB910C64E682A8C595C71A5686236637A55C8F1`.
SDK import again reported zero warnings/errors. The canonical ACD downloaded in
the second run was
`FraktalPhase0_fixture_v33_r3_large_canonical.ACD`, SHA-256
`0D5922E9B70722636273FB258607A414E5DA56545E58DA191DE8251220387CBE`.
Studio v33 Verify reported zero errors/warnings without changing that hash. Two
successive SDK/Studio exports had different raw hashes but the identical
canonical SHA-256
`5FFA6B112D71AECA15FEB5F3A0504BB075A32BB091CB486EAA427F726742264D`
after excluding exactly the same three timestamp attributes.

## 3. Studio/USB download result

Studio 5000 Logix Designer v33 **Who Active** expanded **USB** and selected:

```text
16, 1769-L24ER-QB1B, FIS_Aptiv_Rev1
Path: Backplane\16
```

The pre-download dialog independently reported:

| Field | Visible value |
|---|---|
| Connected controller name | `FIS_Aptiv_Rev1` |
| Type | `1769-L24ER-QB1B/A CompactLogix 5370 Controller` |
| Path | `Backplane\16` |
| Serial | `7036B510` |
| Security | `No Protection` |
| Starting mode | Remote Run |

Studio completed the download and displayed `Download complete with no errors
or warnings.` After accepting the mode prompt, the online status showed
`Controller OK`, expected `I/O Not Present`, and controller revision `33.14`.
No firmware-update prompt was accepted or required.

The expanded canonical ACD was then downloaded through the same USB node after
the dialog again matched `Backplane\16`, serial `7036B510`, exact type, Remote
Run, and `No Protection`. Studio again reported `0 errors / 0 warnings`, and the
controller returned to Remote Run before the expanded EtherNet/IP probes ran.

The UI Automation diagnostics used for this proven path were Who Active
Download `AutomationId=32086`, pre-download confirmation `AutomationId=1`, and
the completed-download Remote Run prompt `Yes`/`No` IDs `6`/`7`. These native
buttons exposed handles but not a reliable InvokePattern; the run used Win32
`BM_CLICK` only after re-reading the visible target, path, catalogue, revision,
and serial. These IDs are diagnostics for v33, not a supported Rockwell API.

## 4. Physical EtherNet/IP execution matrix

Immediately after download, the fixed identity probe again matched firmware
`33.014`, serial `7036B510`, and `192.168.100.89/24`. The redacting symbolic
probe successfully read the fixture scan count, heartbeat, test-complete flag,
read-only scalar, 25-element array, and 28-byte UDT result.

The serial-guarded
[`fraktal_ab_phase0_execute.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase0_execute.py)
then ran the fixed memory-only vector. It is not a generic writer: it requires
both `--expect-serial` and `--execute-fixture`, fingerprints the exact `FRK_*`
fixture before its first write, exposes no caller-selected tag or value, and
restores every writable input to zero/empty before exit.

```powershell
$python = 'C:\Users\Rockwell Automation\AppData\Local\Python\pythoncore-3.14-64\python.exe'
$env:PYTHONPATH = Join-Path $env:TEMP 'FraktalPylogix'
& $python FraktalCore\PLC\Allen-Bradley\tools\fraktal_ab_phase0_execute.py `
  192.168.100.89 --expect-serial 7036B510 --timeout 5 --execute-fixture
```

| Case | Physical result |
|---|---|
| Controller fingerprint | PASS; exact serial/model/revision, all browsable fixture tags present, `ExternalAccess=None` tag hidden and unreadable |
| `DINT` | write/read and PLC result PASS |
| `REAL` | write/read PASS |
| `DINT[25]` | complete array write/read PASS; boundary samples 0, 1, 23, 24 copied by PLC and matched |
| `DINT[1024]` | fragmented 4 KiB whole-array write/read PASS; boundary samples and PLC checksum matched |
| program-scope `DINT` | write/read and program result PASS |
| standard `STRING` | write/read PASS; PLC length contributed to the expected checksum |
| UDT members | scalar and four-element member-array writes/readback PASS |
| PLC cyclic derivation | result scalars, samples, and checksum PASS |
| `ExternalAccess=Read Only` | write rejected with `Privilege violation`; PLC-owned value remained readable and correctly derived |
| `ExternalAccess=None` | omitted from tag browse; read and write rejected with `Path segment error` |
| execution/liveness | test-complete true; scan count and heartbeat advanced |
| cleanup | every write returned Success; all scalars, arrays, STRING, UDT members, and derived result checksum verified zero/empty |

The tool returned `execution_passed=true` using pylogix `1.1.5`. Output values
were redacted; only status, type/shape, and Boolean comparisons were emitted.

## 5. Transport, recovery, and time evidence

The read-only, serial- and fixture-guarded
[`fraktal_ab_transport_budget_probe.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_transport_budget_probe.py)
read the 4 KiB array successfully at requested connection sizes 128, 256, 500,
1000, 2000, and 4000 bytes. The respective elapsed times were 899.692, 462.634,
265.608, 200.895, 176.773, and 132.423 ms. All 25 independent
connect/read/close cycles passed (89.838 ms minimum, 111.867 ms median, 151.260
ms maximum). An induced 0.1 ms session timeout failed as intended and the next
normal client recovered in 103.246 ms. Concurrent levels 1, 2, 4, 8, 12, and 16
all passed; the 16-reader maximum elapsed time was 262.793 ms. No value was
printed and no tag was written.

The first guarded wall-clock read returned 1998, about 902,980,517 seconds
behind the host. Under the user's standing authorization for this isolated
fixture, the fixed
[`fraktal_ab_time_probe.py`](../../../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_time_probe.py)
was explicitly armed with `--set-to-host`. It matched the exact serial and
fixture fingerprint, called only `SetPLCTime(dst=0)`, and obtained seven
successful post-set samples. Controller minus host-midpoint offset ranged from
-19.855 ms to -12.629 ms. Direct Time Sync Object reads reported PTP disabled
and unsynchronized before and after the set, so Fraktal records these source
timestamps with `TimeSynchronized=FALSE`. Firmware, IP configuration, project,
and Remote Run state remained unchanged.

## 6. Negative and normalization findings

- A first generated ST body used `TRUE`; Studio v33 correctly rejected it as an
  undefined tag. The fixture generator now assigns BOOL `1`, and a regression
  test covers the corrected v33 source.
- The first generated L5X is not itself Studio-canonical. Canonicality is proved
  only after an import/export stabilization pass; generator source equivalence
  and Studio round-trip equivalence are distinct gates.
- A serial match alone is insufficient to authorize a write. The execution tool
  also requires the complete fixture fingerprint. Its first physical attempt
  stopped with zero writes when the fingerprint incorrectly expected the
  `ExternalAccess=None` tag to be browsable; the corrected rule requires it to
  be hidden and unreadable.

## 7. Current controller state and next use

At the end of this evidence run the controller remained in Remote Run with the
expanded memory-only `FraktalPhase0` fixture, `Controller OK`, expected `I/O Not
Present`, all writable test inputs cleaned (including all 1024 large-array
elements), and the wall clock aligned to host UTC with unsynchronized quality.
This paragraph is the historical closeout of the S1/data fixture. S2 later
replaced it with the clean eight-level nested-AOI fixture; the current physical
state is recorded in
[`AB_S2_AOI_PARAMETER_EVIDENCE.md`](AB_S2_AOI_PARAMETER_EVIDENCE.md). The
original application has deliberately not yet been restored because the same
isolated controller is needed for subsequent R2 execution-form spikes.

Restoring the rollback ACD is a controller-changing download and still requires
the current user authorization and the same immediate identity check. Do not
restore it merely to tidy the workstation while physical Phase 0 work remains.

This result closes S1, including controlled-write, External Access, bounded
transport/recovery, and honest time-quality behavior. S2 is now separately
PASS; R2 still requires S4, S11, and S12. R4/R5/R6 also remain open. This PASS does not authorize
production runtime/library implementation.
