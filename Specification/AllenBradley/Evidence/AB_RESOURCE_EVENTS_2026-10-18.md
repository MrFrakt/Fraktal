# Confirmed tool/material events on local Echo — 2026-10-18

Unit-chain MARK annotations now publish `TOOL_CHANGED` and `MATERIAL_CHANGED`
through the existing PLC-owned host ring. This closes the confirmed resource
producer seam for bounded subjects and signed DINT values. Arbitrary textual
values, actual resource device/carrier protocols and genealogy remain separate.

Both v38 compiler targets and prepared/downloaded actual read-back pass.
All **31 live tower/Part regressions** pass, including resource checks on
21 ST/SFC/LD recovery rows. All **27 final checks** pass: configuration values
match the pre-download documents, access policy/session/inputs are restored,
and live resource delivery to SQLite reopens without duplicates. Echo is Run,
not faulted, MANUAL/idle, with no Part or lamp test active.

Final automated validation passes **1,855 AB tests**, **88 focused resource/
host/Part/tower tests** and **74 root gate tests**. Specification, frozen-contract
and strict consistency gates are clean. The final source also proves one V3
emitter body for both carrier compositions while preserving the exact downloaded
fixture bytes. Earlier successful test logs retain their narrower scope.

## Authority, native reuse and behavior

The owner explicitly states **“simulated plc is available for you to download
anytime”**, in the ongoing request to close the AB gaps. This download targets
only local Echo `601FC87B`; it authorizes no physical-controller operation.
The existing image and all five configuration documents are backed up before
replacement. Exact local identity checks run immediately before mode changes
and download. No fault clear, clock/scaling change, network/gateway
reconfiguration or electrical I/O write occurs.

TwinCAT's `M_PublishToolChanged` / `M_PublishMaterialChanged` are the behavioral
reference: the owning process publishes at its actual confirmation boundary.
The AB declaration annotates that MARK with kind, subject and a value source.
The framework captures it once per visit; there is no per-scan project call,
configuration watcher, remote resource command, new device driver or second
history. A failed Part helper on the MARK prevents resource publication.

Native UDT/AOI and ST/SFC/LD execution remain the backing mechanisms. The
existing host emitter is the single append owner. Physical host schema V3
shares V2's 64 DINT ASCII identity cells: PartUid for kinds 1–4, resource Subject
for kinds 7–8, empty for other kinds. Resource subjects are 1..63 printable
ASCII characters; Value snapshots a signed DINT literal or exact existing
Cfg/Unit/module scalar and renders it as decimal text. It is not reconstructed
from later mutable state. Resource events carry empty PartUid, NONE verdict
and zero reason. V3 required-InOut types receive new Unit/Part-service AOI
names; V1/V2 output stays unchanged.

The MARK is a process assertion, not evidence that changing a recipe moved a
tool. The disposable fixture confirms a fictitious material lot at successful
Part receive and a fictitious tool at Part start, using existing chart rows.
Actual projects must bind those annotations to their actual confirmation
boundaries. The existing generic HMI already defines both event kinds.

## Native artifacts and acceptance

| Item | Value |
| --- | --- |
| Target | `127.0.0.1`, slot 0, serial `601FC87B`, Emulate 5580, v38.011, product 288 |
| Controller GUID | `91dec7d6-8ac3-45c9-ab2e-0d039c7006fd` |
| Declaration / manifest | `fraktal_ab_resource_demo`, major 5, `EBF1887B15E96453`, revision 15462792 |
| Source L5X SHA-256 | `445FFD50B129DEE4D1338A3C73B6F5BD60BFDFF02EA91B24CDD0DC48688C33A2` |
| Prepared ACD SHA-256 | `0C85C9EAACBE0A7EB81994252E15D4F54D5C84469AD5E14CC70B600929C8208B` |
| Correlated downloaded ACD SHA-256 | `79EA84F64754CF5850BEF92B1EA124E92C7C47D0EBB602B45A353AD77C08FFB4` |
| Previous image backup ACD SHA-256 | `A1B73E27D56F7AC2429ADD27C9A1656668E9D2756034CEB6FBA27F0B4868A50C` |

ACDs and the uploaded prior image remain under
`C:/work/fraktal-ab-resources-20261018/`; they are not repository payloads.
Generated L5X and native exports also remain there; the payload binds their
hashes and actual comparison/build records.
SDK 2.1.974 builds EchoController and PhysicalController offline with clean
import/build logs. The ACD reopens/builds before download. All read-backs match
**42 executable bodies, 20,446 authored initial values and 21 SFC steps**.
PhysicalController compilation is not a physical installation or capacity claim.
The final authored source reproduces the exact compiled L5X hash.

The 31 restored regressions retain tower timer/access/arbitration checks and
the Part OK/NOK/HELD/resume/abort/mode-change/adopted-fault/one-reset matrix.
The 21 language/recovery rows also reject resource duplicates/order errors,
wrong captured subject/value and PartUid/reason leakage. Completed OK, NOK and
HELD-resume cycles each retain material then tool confirmation. Earlier aborts
legitimately retain the material confirmation without the later tool event.

Configuration compatibility accepts only the exact current declaration with
resource annotations omitted and the already supported historical variants.
Unrelated revisions remain refused; ordinary schema/range validation is intact.
The five saved/live documents reopen equal and retain the pre-download values.
The final read-only host collector stores 16 retained events plus one explicit
overwrite notice in SQLite, passes integrity checks and adds no rows on reopen.

Compared with the otherwise identical tower fixture, declared data remains
**122,868 bytes**, RLL stays at 23 rungs, and chart rows do not grow. ST source
grows 14,900 bytes / 264 terminators. These are source/layout measurements;
AOI storage, metadata and compiled instruction size are excluded. No physical
L24ER fit/headroom claim follows. The opt-out tower export is byte-identical to
the previous accepted generation (`03BE7A3D4F16118E328673F096EA06C250D2D64FC14027BE043B824F535A99ED`).

## Reproduction and limits

Select `FRAKTAL_AB_DECLARATION=fraktal_ab_resource_demo` for the current local
Echo gateway/tools. The major-4 direct-CIP HMI spike remains ineligible.
`fraktal_ab_resource_execute.py` requires explicit arming, exact declaration,
serial `601FC87B`, a local fixture credential file and a new evidence path.
It reuses the existing tower/Part restoration owner; credentials are never
printed or archived. Before any future controller-changing run, apply the
current authorization and target rules in AGENTS.md §3a.

Focused tests cover invalid kinds/ASCII/operands/ranges, snapshot immutability,
all-language cycles, Part-helper failure, step-mark ordering, identity isolation,
wrap/loss, carrier-off refusal of Part events, exact revision compatibility and
fixture refusal guards. The immutable [payload manifest](AB_RESOURCE_EVENTS_2026-10-18/manifest.json)
binds source snapshots, compiler/read-back, backup/download, runtime, restoration,
sink and validation artifacts. Baseline commit is
`db924620a1ac4508dcdd4e5e918cd46481a4041d`.

Native alarm subscribers, native health/time production qualification, textual
resource values, device-backed carriers/genealogy, Line sharing, external host
delivery, gateway-service recovery and physical/browser/retention acceptance
remain open in the [completion tracker](../AB_PORT_COMPLETION_PLAN_2026-10-04.md#remaining-work-after-the-2026-10-18-host-recovery-checks).
