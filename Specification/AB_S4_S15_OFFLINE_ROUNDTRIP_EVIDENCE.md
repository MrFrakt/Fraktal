# Fraktal/AB S4/S15 — Disposable Offline Round-Trip and Build Evidence

**Spikes:** S4 L5X fidelity; S15 unattended SDK import/Build/export/diagnostics

**Result:** **S4 PASS — the representative construct matrix, native SFC, and
repeated canonical round trips all hold, and a generated-vs-exported census now
proves nothing is silently dropped. S15 remains OPEN: the SDK online Ethernet
path and the packaged unattended gate are unresolved.**

**Date:** 2026-08-13

**Scope:** disposable v37 and v33 projects in the Windows temporary directory,
plus read-only FactoryTalk Linx/SDK route probes and a Studio USB upload from
the R1 controller. No project in the repository or live controller was
changed. No download, controller-mode change, tag write, clock set, fault
clear, firmware operation, or controller-memory write was used.

## 1. Fixture and toolchain

The installed Logix Designer SDK `2.00.00` / C# client `2.0.861` returned
`1769-L24ER-QB1B` in `GetProcessorTypesAsync(37)`. Rockwell's supplied
`CreateNewProject` example then created:

| Field | Value |
|---|---|
| Logix Designer revision | `37.00` |
| Controller | `1769-L24ER-QB1B` |
| Controller name | `FraktalS15` |
| Build target | physical controller (`RequestedBuildTarget.PhysicalController`) |
| Artifact location | unique `%TEMP%\FraktalAbS15-*` directory, outside the repository |

The SDK created the ACD and the supplied `BuildProject` example completed
`BuildAsync` and `SaveAsync` successfully. This proves the installed v37 SDK
Build-capable path for the same controller catalogue family used at R1; it does
not claim compatibility between firmware v37 and the live v33 controller.

## 2. Round-trip result

The disposable project followed this path without UI automation:

```text
new v37 ACD
  -> SDK Build (physical target)
  -> SDK full-project L5X export, pass 1
  -> SDK Convert/import to a new v37 ACD
  -> SDK Build (physical target)
  -> SDK full-project L5X export, pass 2
```

The import log reported `Warnings="0" Errors="0"`. Both physical-target
Build calls completed successfully. The two 5,016-byte exports had different
raw hashes because Logix Designer rewrote three timestamps:

| Artifact | SHA-256 |
|---|---|
| pass 1 raw L5X | `11260F9262BFEC564309EF01739ADFB8FD2B2EC7A624506D1560E20A74C33CC1` |
| pass 2 raw L5X | `AA08C69BF4E40E60B3042C0AE072FB8266A11575C887816F93D4C05A9E676056` |
| both canonical L5X documents | `7BB045BEF5FC4C7E41EB6D3BB964D46F36AB973A7DB48D7D0C52DEE25DEA4BB8` |

Line comparison found changes only in
`RSLogix5000Content/@ExportDate`, `Controller/@ProjectCreationDate`, and
`Controller/@LastModifiedDate`. The repository tool
[`fraktal_ab_l5x_compare.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_l5x_compare.py)
removes only those three fields, applies XML C14N 2.0, and requires every other
field to match. Its focused tests prove that a tag-value change fails the
comparison and non-project XML is rejected.

## 3. What this settles

- The installed SDK licence/service can create a v37 L24ER project, perform a
  physical-target Build, import a full-project L5X, save ACD, and export L5X
  unattended.
- The successful import exposes a machine-readable zero-warning/zero-error
  summary through the SDK event logger.
- On the empty controller fixture, the ACD→L5X→ACD→L5X cycle is stable after
  excluding exactly the three observed volatile timestamps.
- Raw-file equality is not a valid canonicality rule for Rockwell exports.

## 4. Rich v33 serialization result

A second read-only round trip used the earlier disposable v33 full-project
export associated with the R1 target family. No names, source logic, tag values,
ACD, or L5X from that application are committed. The counted construct surface
was:

| Construct | Count |
|---|---:|
| user data types | 14 |
| AOI definitions | 1 |
| AOI parameters / private local tags | 16 / 15 |
| controller and program tags | 461 |
| programs / tasks | 26 / 1 |
| ladder routines | 26 |
| structured-text routines, including the AOI logic | 2 |
| SFC routines | 0 |

The SDK imported the full project at v33 with `Warnings="0" Errors="0"`, saved
a new ACD, and exported it again. Raw export hashes differed, while the
timestamp-normalized canonical hashes were identical:

| Artifact | SHA-256 |
|---|---|
| source raw L5X | `F32D91751BEAB4BE09A26DE85B5AD45BC1F898F8F1610617A7C677F7C6E94D15` |
| round-trip raw L5X | `EC41B40FCE079656ECA4AC5948A1F713039BAEAA98A89598EA2C414A475BC8AB` |
| both canonical L5X documents | `94D75514673991C804DB0896EC41D995C184BB980FCD021136D33D14580B1F35` |

This positively covers rich UDT/AOI/tag/ST/RLL serialization on v33. It is not
a Fraktal execution fixture, contains no nested AOI or native SFC routine, and
does not prove semantic Verify or behavior.

## 5. Negative gate findings

Two deliberate disposable mutations exposed requirements for the eventual
gate:

- adding the disallowed `Rate` attribute to a continuous task made the SDK
  import log report `Warnings="1" Errors="0"`, but `ConvertAsync`/
  `SaveAsAsync` still returned success; therefore a zero process exit alone is
  insufficient and the gate must parse and reject non-clean import summaries;
- a project containing the invalid ST line `MissingTag := ;` imported with a
  zero-warning/zero-error summary and `BuildAsync` still returned success.
  `BuildAsync` is the SDK's cached-binary build operation, not proof of Studio
  5000's semantic **Verify Project** result. A later controlled Studio v37
  **Verify Controller** rejected the same disposable ACD with exactly
  `2 Errors`, `0 Warnings`: `Invalid expression` and unexpected `;` on line 1.
  The Error List therefore supplies the fail-closed semantic gate that SDK
  Build does not.

These files remained in `%TEMP%`; neither mutation touched the repository or a
controller.

A first read-only `UploadToNewProjectAsync` attempt against the confirmed target
IP failed closed after the SDK rejected the locally supplied route
`Ethernet\192.168.100.89\Backplane\0` with “No module was found.” No ACD was
produced and the controller was not changed.

The route investigation then used the supported FactoryTalk Linx 6.50
Configuration Import Export Tool to add a workstation-only point-to-point
driver alias `Fraktal_AB` whose device list contains only `192.168.100.89`.
Its supported `/Browse /NetworkPath` command completed successfully. The Linx
topology and target record independently returned:

| Field | FactoryTalk Linx result |
|---|---|
| topology path | `Fraktal_AB\192.168.100.89` |
| internal driver / display alias | `Ethernet 2` / `Fraktal_AB` |
| controller name | `FIS_Aptiv_Rev1` |
| catalogue | `1769-L24ER-QB1B` |
| serial | `7036B510` |
| hardware/revision token | `cip=1:14:149:33.14` |

This is positive FactoryTalk Linx discovery evidence for the same device proved
through direct CIP; it is no longer valid to attribute the SDK failure to an
unbrowsed IP. The workstation was then rebooted. `LdSdkServer` started after
boot, the `Fraktal_AB` driver persisted, and the supported Linx browse passed
again, disproving a stale pre-reboot service cache as the complete explanation.

Post-reboot SDK results were:

| SDK path | Result |
|---|---|
| `Fraktal_AB\192.168.100.89` | reached `RxE_COMM_TIMEOUT` after approximately 285 seconds; no ACD |
| `Ethernet 2\192.168.100.89` | “No module was found” after approximately 126 seconds; no ACD and no TCP/44818 session observed |
| `Fraktal_AB\192.168.100.89\Backplane\0` | “No module was found” after approximately 125 seconds; no ACD and no TCP/44818 session observed |

Studio 5000 v33 then supplied the decisive route evidence. Its FactoryTalk Linx
**Who Active** tree selected the controller and displayed
`Fraktal_AB\192.168.100.89`. The **Connected To Upload** dialog successfully
connected and matched project name, catalogue, serial `7036B510`, and
`No Protection`. This proves the Linx/Studio path ends at the integral L24ER
controller; a `Backplane\slot` suffix is wrong for this target.

Saving **Set Project Path** changed only the disposable ACD, but SDK 2.00
`GetCommunicationsPathAsync` still returned an empty string. Studio's read-only
upload transferred the controller tags and built routines locally, then failed
near completion with `Error 731-0` / `Communications timed out` and reverted the
disposable ACD to its last saved copy. The controller's direct CIP identity,
firmware `33.014`, serial, TCP/IP configuration, TCP/44818 reachability, and the
Linx command-line browse all passed immediately after the failure. No download,
controller-memory write, tag write, mode change, fault clear, clock set,
firmware operation, or controller-configuration change occurred.

The Ethernet route is therefore proved but unsuitable for a complete upload in
the observed configuration. That is an Ethernet/SDK online-path blocker, not a
general Studio upload blocker: the subsequent USB result below completed. The
reproducible workstation interfaces and UI automation details are recorded in
[`AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`](AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md).

## 6. USB upload and upload-derived v33 round trip

After the USB cable was reconnected, Windows reported the Rockwell USB CIP
device `USB\VID_14C0&PID_001F\7036B510` as present and healthy. Studio 5000 v33
selected `16, 1769-L24ER-QB1B, FIS_Aptiv_Rev1` under **USB**, displayed the
route `Backplane\16`, and matched serial `7036B510` in **Connected To Upload**.
The read-only upload completed with `0 error(s), 0 warning(s)` and `Upload
complete with no errors or warnings.` Studio saved the result, including the
requested online tag-value refresh, only to a disposable `%TEMP%` ACD.

The repository offline probe then opened that uploaded ACD, proved its input
hash unchanged, and exported a full-project L5X. The construct inventory was:

| Construct | Count |
|---|---:|
| user data types | 14 |
| AOI definitions | 1 |
| AOI parameters / private local tags | 16 / 15 |
| controller and program tags | 461 |
| programs / tasks | 26 / 1 |
| ladder routines | 26 |
| structured-text routines, including the AOI logic | 2 |
| SFC routines | 0 |

SDK conversion of this fresh export to a new v33 ACD reported
`Warnings="0" Errors="0"` and saved successfully. Re-exporting that new ACD
produced the following stable comparison:

| Artifact | SHA-256 |
|---|---|
| uploaded disposable ACD | `B3A1291ACDBFBD1A84C95354D550FB9A6FC6E908D766789508F8EFB2B83C8B60` |
| upload-derived raw L5X | `9B0081E83C0C82A6B9F977E2FECDDBB5E3113907A99B29D77BFCE0BEDA6920B0` |
| converted v33 ACD | `F1E84DA2EEE76A5661E338D0DE9CA4D3B23EDD48EB60BA21C20EAC15AF9974EF` |
| round-trip raw L5X | `870CAF35EB9384B0DE7776282D67AB99A7D0F459E6BCD274A99699C1D6E22003` |
| both canonical L5X documents | `41F3C9F31538FB9BEADECEB0423F6EB84E31447F56707AA89A00AB32A8A89B67` |

The comparison excluded only `RSLogix5000Content/@ExportDate`,
`Controller/@ProjectCreationDate`, and `Controller/@LastModifiedDate`. A
comparison against the earlier offline snapshot was not equivalent, so this
evidence does not claim that the old snapshot matched the live controller.
The upload-derived source compared only against its own fresh conversion and
re-export.

The installed SDK release notes limit project Build support to Logix Designer
v37 and later. Consistently, physical-target `BuildAsync` on the new v33 ACD
returned `Operation not supported on Logix Designer version 33.0`. Conversion,
save, and canonical export still passed; this result is a documented version
boundary, not a semantic compile failure. Studio v33 Verify/Error List remains
the required semantic check for v33 projects.

Studio v33 then opened the uploaded disposable ACD offline and invoked
**Logic > Verify > Controller**. The Error panel reported
`Complete - 0 error(s), 0 warning(s)` and
`Verify complete with no errors or warnings.` with 31 diagnostic messages.
Studio was closed without saving, and the uploaded ACD SHA-256 remained
`B3A1291ACDBFBD1A84C95354D550FB9A6FC6E908D766789508F8EFB2B83C8B60`.
This is positive semantic Verify evidence for the uploaded v33 application.

After Studio was closed, the USB device remained healthy. A new three-sample
EtherNet/IP identity probe still matched firmware `33.014` and serial
`7036B510`, and the supported Linx browse of
`Fraktal_AB\192.168.100.89` succeeded. No controller-changing operation was
issued.

## 6a. The representative construct matrix (closes S4)

[`fraktal_ab_s4_matrix_fixture.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_s4_matrix_fixture.py)
generates, from one declaration set, the constructs a generated Fraktal project
actually contains and that no earlier fixture covered:

| Construct | In the matrix |
|---|---|
| schedules | one PERIODIC and one CONTINUOUS task, each with its scheduled program |
| programs | two, one carrying ST, RLL and SFC routines side by side |
| record shapes | a nested UDT, a four-element UDT array, and a `StringFamily` type of non-default length |
| generated constants | a `Constant="true"` tag, the `FRK_K` enum form of AB §3.8 |
| AOI scan flags | all three `Execute*` flags true, with Prescan, Postscan and EnableInFalse routines supplied |
| documentation | descriptions on a data-type member, a tag, a routine and a rung |

Deliberately out of scope, and recorded as such: FBD, which Fraktal does not
generate; alias and produced/consumed tags, which the binding does not use; and
motion, which S14 gates separately.

| Stage | Result |
|---|---|
| generated L5X | `42718C817C60411D82519E8EA8E8C6454B600C394BA1E2894110ECC1E25F7793` |
| SDK import | `Warnings="0" Errors="0"` |
| converted v33 ACD | `68EB99623BB4390A62BE27721F09EA8BBC4044D4C12DBCCD2F87F826967EA457` |
| Studio v33 **Verify Controller** | `0 errors`, `0 warnings`, every routine verified by name |
| canonical round trip | `1FEC3D96482D01C7AEF10562AE0E9FD6EE190C044207E8A8AD3643E8E2B45A6F` both passes |
| construct census, generated vs first export | equivalent: 3 data types, 1 AOI, 8 controller tags, 2 programs, 2 tasks, 5 descriptions |

### The census closes a hole the canonical comparator could not see

The canonical comparison runs export-against-export, and **both** of those have
already been through Studio. A construct dropped or rewritten during the *first*
import would be equally absent from both passes, and the comparison would report
"equivalent" while the evidence was worthless.
[`fraktal_ab_l5x_inventory.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_l5x_inventory.py)
therefore censuses the **generated declaration** against the **first export**.
It cannot be textual, because Studio reorders siblings, renumbers chart
elements and fills in defaults; it compares identity and executable shape.

### Two rules the matrix produced

**Every generated routine must be reached from its main routine.** The first
matrix revision left the RLL and SFC routines uncalled, and Studio verified with
`0 errors` but **2 warnings**: `Routine cannot be reached by the main routine`.
An errors-only gate would have accepted a project carrying dead generated code,
so the gate requires zero warnings and the generator emits a `JSR` for every
routine it creates.

**Every attribute the generator cares about must be stated.** The SFC step,
action and transition tags were declared without `ExternalAccess`; Studio wrote
its default `Read/Write` on export. Nothing was lost, but the generated document
then differed from its own export, which a later comparison would misread as
drift. The census flags an absent attribute rather than silently treating it as
its default, and the generators now state it. The S11 fixture carried the same
omission and was corrected the same way (see that evidence for the effect on its
recorded hashes).

## 7. Why S15 remains open

The uploaded application and rich fixture cover UDTs, one AOI, controller and
program tags, RLL, ST, programs, and a task, but they are not a representative
Fraktal construct matrix. Subsequent S2 evidence covers the External Access
matrix, eight nested AOIs, complete-L5X-to-ACD conversion, Studio v33 Verify,
and an exact post-download target-binding comparison without weakening the
ordinary canonical comparator.

S11 then closed the native-SFC gap: a generated chart with steps, `NonStored`
actions, transition expressions, two `Simultaneous` branches, the three
controller SFC execution settings, an `SFR` target and `JSR` parameters
imported `0/0`, passed Studio v33 Verify `0/0`, and round-tripped canonically.
Because Studio may renumber chart element IDs, that claim is checked by the
ID-independent
[`fraktal_ab_sfc_roundtrip_compare.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_sfc_roundtrip_compare.py)
as well as the canonical comparator; see
[`AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md`](AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md).
§6a then supplied the construct matrix — schedules, record shapes, generated
constants and the AOI scan routines — with a generated-vs-exported census, so
**S4 is PASS** for the constructs the binding generates.

The negative SDK fixture and Studio verification prove that SDK Build is not
semantic Verify and that the controlled Error List path fails closed. **S15
remains OPEN** on two counts: the SDK online Ethernet workflow is still
unresolved, and while
[`fraktal_ab_phase0_gate.py`](../FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_phase0_gate.py)
now packages seed, regeneration, import, round trip and census as one
repeatable command from a clean checkout, Studio **Verify** remains reachable
only through UI Automation on a logged-in desktop. The gate therefore makes
Verify opt-in and reports which checks ran; a genuinely unattended gate needs
either that constraint accepted or a different toolchain, which is the open
decision S15 records.

No production runtime implementation is authorized by this evidence. R3–R6
remain open.

## 8. Commands

The runs used Rockwell's installed `GetProcessorType`, `CreateNewProject`,
`BuildProject`, and `ConvertProject` C# examples with the local
`RockwellAutomation.LogixDesigner.CSClient` package, plus:

```powershell
dotnet Fraktal.Ab.OfflineProbe.dll <disposable.ACD> --export <pass1.L5X>
dotnet Fraktal.Ab.OfflineProbe.dll <generated.L5X> --export <new.ACD>
dotnet ConvertProject.dll <pass1.L5X> 37 <roundtrip.ACD>
dotnet BuildProject.dll <roundtrip.ACD> 1
dotnet Fraktal.Ab.OfflineProbe.dll <roundtrip.ACD> --export <pass2.L5X>
python fraktal_ab_l5x_compare.py <pass1.L5X> <pass2.L5X>
```

The USB-derived v33 run used the same offline probe, `ConvertProject`, and L5X
comparison sequence with revision `33`. `BuildProject` was invoked to capture
the documented v33 unsupported-version boundary, not counted as a successful
Build.

Both Studio Verify cases were then repeated through the repository's narrow
offline wrapper:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  fraktal_ab_studio_verify.ps1 -Revision 33 -Project <uploaded.ACD> `
  -ExpectedErrors 0 -ExpectedWarnings 0 -TimeoutSeconds 120

powershell.exe -NoProfile -ExecutionPolicy Bypass -File `
  fraktal_ab_studio_verify.ps1 -Revision 37 -Project <invalid.ACD> `
  -ExpectedErrors 2 -ExpectedWarnings 0 -TimeoutSeconds 120
```

Both returned the expected counts, `InputUnchanged=true`,
`CountsMatch=true`, and `ClosedCleanly=true`. The wrapper exposes no download,
online connection, tag write, mode change, or other controller operation.

## 9. Primary references

- Rockwell Automation, [Logix Designer SDK Getting Results Guide](https://literature.rockwellautomation.com/idc/groups/literature/documents/gr/ldsdk-gr001_-en-p.pdf)
- the installed SDK 2.00 C# documentation, examples, release notes, and NuGet
  package used by the recorded runs
