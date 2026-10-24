# AB S3c sequence publication ? offline preparation, 2026-10-22

S3c passes its offline compiler, read-back, access, test and measured Capacity
gates at **647 explicit paths**. No S3c controller change is authorized or
performed. Runtime equivalence, candidate/rollback regressions, rendition
coverage and native scan measurements remain open. The corrected readiness
gate deliberately refuses the current AUTO/idle baseline; MANUAL normalization
requires current approval. Shipping Part III/V1 remain authoritative; V2 is
an approved target and remains inactive.

See the [notes](../AB_CANONICAL_PUBLICATION_S3C_NOTES_2026-10-22.md),
[independent inventory](../AB_CANONICAL_PUBLICATION_S3C_INVENTORY_2026-10-22.json),
[V6.2 draft](../AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md) and
[payload hashes](AB_S3C_CANONICAL_PREPARATION_2026-10-22/manifest.json).
Date follows the client's America/Mexico_City date. Source commit is
`a1163c7c7bec21988167bc971145b1366206e9ce` plus uncommitted work. No commit,
push, fault clear or clock change ran. Credentials and ACD binaries are not
archived. The owner's unrelated edits remain intact.

## Scope and ownership

The inventory extends the sealed S3b 304 paths by 343: 231 sequence-row,
84 annotation, three cursor, three view/count and 22 current-step/condition
leaves. The initial 625-path prototype omitted the HMI contract's main-line
detail; its inventory/builds remain historical work artifacts. The 647-path
revision was recorded from the frozen legacy projection before implementing
those 22 fields. No discovered output chooses its own expected subset.

The existing PLC Chart owns visits, durations and warning marks. Static row
definitions occupy a separate read-only record linked by a PLC-published V6.2
binding; a live FragmentRevision invalidates cached definitions independently
of the schema hash. Root history/annotations remain an on-demand view, and
ActiveSteps/CurrentStep remain live. S4 still owns transport tier scheduling.
Private authored source/caches stay outside public whole-read records.

The generic reader validates bindings, native layouts, matching containers,
disjoint leaves, identity, bounds and logical types. It imports no station or
projection. The model executes the generated ST against the independent legacy
projection, including mode clear, valid step 0, repeated numbers across modes,
recipe changes, warning text/source and condition coherence. These are offline
model checks, not controller captures. Fast-step history is never accumulated
by the reader.

The fixture has no EM or concurrent branch. Its bounded 21-slot annotation
view preserves the legacy oracle above Core's default 16. ErrorActive and
cursor TimedOut retain the oracle's false values; missing per-row liveness and
the earlier Core gaps remain explicit. CurrentStepTimedOut publishes the
existing Unit flag. Starved/Blocked await the later MachineState/OEE stage.
No full-Core or parallel-runtime claim is made.

## Exact artifacts and native checks

Work folder:
`C:/work/fraktal-ab-s3c-20261022/prepare_147ef60398974c44abf7b2959b2d813f/`.

| Artifact | SHA-256 |
|---|---|
| genealogy_s3c_04.L5X | E58BB88F9E63BE9144AF90C4032714F9B44B167CA02E2B2A64C933788F4E70A2 |
| s3c_canonical.ACD | A255918860C3062D8F0DF3FA4E70373EF84372DDB3214E050AF23A08A0C2286C |
| Echo native read-back | 96493AE0A45313BF0236D03498B6D4DB48DD4758FB0CF32292154F1C6E383A5A |
| Physical native read-back | 7E1E6C12F7632C2F694CC2F5886738FCFBB686F73766F219B6389D30443E1CA6 |

Both v38 offline targets pass clean import/Build/Save As audits. Each strict
read-back compares 95 UDTs, seven AOIs, 130 tags, one program/task, 45 executable
bodies, the 21-step SFC graph, 352 descriptions and **26,230 authored initial
values**, with no differences. The prepared ACD was reopened/rebuilt/exported
equivalently before pinning. Source/native/prepared access audits check all
130 top-level tags and 37 canonical types. The only added public allow-list
entry is the engineered definition binding; private records remain None.

Generated V6.2: 175 Fields, hash
`32B222528280D017FFE0C2B646B099DD8C79A30897A9E42D4F322BD944B4BC80`,
revision 53158437. V5 remains `6DEC4C1DC2F7F78A`. These are offline generated
identities, not live S3c observations. The SDK helper builds with zero warnings
and errors, binds both native results to the exact source, and requires current
exact-pin approval, measured Capacity, backup and strict preflight.

## Automatic Capacity

The qualified hidden Studio driver opens only an offline review copy. Two
stable Standard samples, source hash preservation and process closure pass
normalization. The owner's new driver/provider source is preserved and pinned
in this record; no screenshot was requested.

| Image | Used Standard | Available | Total | Displayed |
|---|---:|---:|---:|---:|
| S3b sealed baseline | 991,612 | 2,154,116 | 3,145,728 | 31% |
| S3c automatic measurement | 1,107,552 | 2,038,176 | 3,145,728 | 35% |

Growth is **115,940 Blocks**. Blocks are not assumed bytes; this is Studio's
offline Capacity estimate, not online memory. The advisory forecast excluded
S3c from calibration: 1,114,908, error +7,356 (+0.6642%); planning budget
1,338,899. It supplies no guaranteed bound and does not replace the measurement.
Native scan and download gates remain open.

## Readiness correction and pending session

The inherited work scripts called Mode 0 MANUAL. The declaration and fixture
define AUTO=0, MANUAL=1. Fresh guarded reads show AUTO/idle, logged out, Run,
not faulted, Remote keyswitch, scanning, not restoring and five saved documents
equal live. Earlier MANUAL readiness claims are unsupported. All predecessor
evidence stays unchanged; the separate recorded equivalence results are not
rewritten. S3c preflight/final checks now derive app.manual_mode. The expected
preflight refusal is retained; **no preflight.json exists**.

A fixed helper is prepared, not executed, for existing LOGIN/SET_MODE(1)/LOGOUT
mailbox frames under current authorization and exact identity/image guards.
It requires an already idle, unlatched, logged-out, restored image and changes
no policy, clock or stimulus. It also corrects the inherited fixture's AUTO
cleanup before final checks. No authorization.json, backup or deploy marker
exists; only a false authorization template is present. The immutable genealogy
original still hashes to
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

The proposed session is: guarded MANUAL normalization; one preflight and fresh
backup; Program/download/Run of the pinned candidate; five-document restore
and 31 regressions with four decision pairs, held/fault coverage across all
three renditions and 21 sequence pairs; 647-path idle equivalence and native
scan; hash-checked-copy genealogy rollback; five-document restore and 31
baseline regressions; MANUAL normalization and final checks. The prepared
read-only audit requires mode clear, sparse warning notes and retained completed
steps shorter than 100 ms. No additional regression stimuli are introduced.
AGENTS.md ?3a requires current explicit approval for this new session; the
completed S3b authorization is historical. Fault clear remains separate.

## Checks and retained failures

- AB discovery: `Ran 2052 tests in 271.430s` / `OK`.
- Root suite: `Ran 74 tests in 4.686s` / `OK`.
- Focused sequence/fragment/fixture checks: 26 pass, included in the full suite.
- Spec: `Fraktal/AB specification gate: clean.`
- Contracts: `Fraktal/AB frozen-contract gate: clean.`
- Strict consistency: `0 error(s), 0 warning(s)` across inventory,
  localization, parity and readsurface. CR-at-EOL whitespace check passes.
- S2/S3a/S3b regeneration retains all three accepted hashes; sealed captures
  replay identical snapshots, values/types at 46/94/304 paths.
- All eleven predecessor seals / 1,548 artifacts verify unchanged.
- Final preparation verification binds 64 source files and all exact artifacts.
- HMI/Flutter gates are not applicable: this stage changes no HMI source.
  Physical hardware, security and all S3c runtime gates remain unrun.

Retained failures include the initial ad hoc inventory NameError; formatter
rejection of WHILE; native rejection of nested indexed-structure subscripts
(fixed by an explicit DINT index); the physical-probe invocation's wrong target
argument; initial model findings for step-0 clearing and warning-source ordinal;
model harness corrections for duplicated HOME and the base-owned StepNo;
missing local SDK NuGet source; and a copied work-path error caught before SDK
preparation. Failed logs, exit records, prototype inventories and generated
L5X remain in the payload. BuildAccepted/content audits supplement SDK exit
codes. No failure was waived and no earlier evidence was overwritten.
