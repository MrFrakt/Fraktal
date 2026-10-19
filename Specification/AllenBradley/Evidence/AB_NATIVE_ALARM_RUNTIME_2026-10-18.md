# Native alarm runtime comparison on local Echo — 2026-10-18

The [prepared comparison fixture](AB_NATIVE_ALARM_OBSERVER_PREPARED_2026-10-18.md)
was downloaded under the owner's explicit **“Download, restore and run the
checks”** authorization, naming Echo `601FC87B`, configuration restore,
the 104-second private comparison and 31 tower/Part regressions. The exact
identity/process guard runs immediately before each controller mode change
and download. No clock change, fault clear, Echo scaling change, gateway
reconfiguration or electrical I/O operation occurred.

All **22 native base checks** and **31 tower/Part regressions** pass. The five
saved configuration documents, original policy, session, mode and simulation
inputs are restored. Echo remains Run and fault-free, MANUAL/idle, with no
active command or lamp test. The native alarm stimulus is cleared. This proves
the bounded native comparison on this emulator; it does not accept a production
alarm provider, native subscriber delivery or external operator isolation.

## Artifacts and native scope

| Item | Value |
|---|---|
| Target | `127.0.0.1`, slot 0, serial `601FC87B`, Emulate 5580 / 1756-L81E v38.011 |
| Controller GUID | `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd` |
| Declaration / manifest | `fraktal_ab_tower_demo`, major 5, `EA7BCE24FDA311EB`, config revision 15367118 |
| Generated L5X SHA-256 | `928E4E81444933E0F70958244F5B0B7B93A5B75F96A2083841B278CDB1A0D2ED` |
| Prepared ACD SHA-256 | `01B95D595C5B54EC4F2963593EDE2E3D457BDADB263B26136D70ADFED1C11360` |
| Correlated downloaded ACD SHA-256 | `AEF2679B03224249B45AB9D915DB19C4A78322230BF2C0D5EB34E33E4276F087` |
| Current program backup SHA-256 | `1AF4F2E7B9C29E8E2B02819828C744D234A14F29421CD4DDA4A20CBFD3A56D33` |

ACDs stay outside the repository in `C:/work/fraktal-ab-alarm-runtime-20261018/`.
The downloaded export matches all 44 executable bodies, 20,449 authored
initial values, 21 SFC steps and two native alarm records. Its manifest and
ordinary Core/HMI contract equal the preceding timing fixture. These are
read-back comparisons, not physical capacity or compiled-memory measurements.

## Measured behavior

The PLC retained all 14 phase rows through **104.039169 seconds** of native CST
elapsed time and 10,406 task scans. The collector performs no writes and
accepts only coherent revisions. Phase completion and duration checks are
independent of host polling. No native status fault was seen in any phase.

| Comparison | Tag-based alarm | ALMD |
|---|---|---|
| One task-scan pulse | Count delta **0** | Count delta **1** |
| Sustained input / unlatched return | Detected / cleared | Detected / cleared |
| Latched active, acknowledgement required | Unacknowledged | Unacknowledged |
| Acknowledge while active | Acked; latch stays active | Acked; latch stays active |
| Reset while condition remains active | Refused; alarm stays active | Refused; alarm stays active |
| Condition gone without reset | Latch remains | Latch remains |
| Reset after condition gone | Clears | Clears |
| Program suppression / unsuppression | Observed | Observed |
| Program assignment to `OperShelve` | Shelving takes effect | Shelving takes effect |
| One-minute shelf, 65-second observation | Natural expiry observed | Natural expiry observed |
| Cleanup | Input/latch/suppression/shelving clear | Input/latch/suppression/shelving clear |

The missed short pulse is **one measured alignment**, not a claim that every
short pulse is lost. Sustained detection and the native counts prove the
tag-based condition was operating. It cannot replace the Core fast-event ring
by simply observing the current Boolean state. A future derived plant
projection needs an explicit delivery/backpressure and identity policy; no
second event latch or alarm history is introduced here.

The programmatic shelving result resolves the earlier compiler discriminator
on this exact Echo target: `OperShelve := ...` actually shelves the tag-based
alarm, despite Rockwell's
[programmatic-access table](https://www.rockwellautomation.com/en-il/docs/studio-5000-logix-designer/38-03/contents-ditamap/studio-5000-logix-designer/alarms/tag-based-alarms/access-tag-based-alarms-in-logic/alarm-attributes-that-support-programmatic-access.html)
marking it Read-only. This does not test external CIP/operator permissions.
Read Only on the input tag is not evidence of operator-command isolation.
Native commands must not bypass Core §14 or acquire Core latch/reset/shelf
authority.

The native latch also retains the measured semantic distinction: native reset
requires the condition false. Core §8.3(b) deliberately permits manual reset
from ACTIVE and releases the issued command chain. Keep Core's event and
recovery owner; native acknowledgement does not implement that release.

## Restoration and remaining gates

The ordinary configuration keeper restored station, line and model1–3 through
the controller's set validator. Reopened local documents equal the live values.
The 31 existing checks cover tower controls and the ST/SFC/LD Part/recovery
matrix; all pass, with original required-access levels and simulation stimuli
restored and the session logged out. The final Core health read has no major
or minor fault and the native comparison is done with zero probe fault.

The disposable observer's clock guard remains active after completion: use
prompt bounded collection, not later continuous monitoring. The archived phase
record is the acceptance artifact. No production monitoring claim is made.

Native alarm subscriber delivery, event identity/order under load, subscriber
backpressure, Core-to-native shelf mapping, external native command isolation,
clock adjustment/scaling and physical acceptance remain open. The production
alarm generator and generic HMI gain no provider or public ABI field.

The immutable [runtime payload](AB_NATIVE_ALARM_RUNTIME_2026-10-18/manifest.json)
binds the download, observation, restoration, regression and final-read records.
The separate prepared payload binds the exact source and offline compiler proof.
