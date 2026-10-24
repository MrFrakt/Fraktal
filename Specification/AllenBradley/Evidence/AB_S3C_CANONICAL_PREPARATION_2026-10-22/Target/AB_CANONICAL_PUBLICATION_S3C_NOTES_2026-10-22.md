# S3c preparation — sequence publication

S3b's accepted subset has 304 paths. The independently recorded
[S3c inventory](AB_CANONICAL_PUBLICATION_S3C_INVENTORY_2026-10-22.json) adds
343, for **647 paths**: 231 sequence-row leaves, 84 annotation leaves, three
cursor leaves, three view/count leaves and 22 current-step/condition leaves.
The first 625-path inventory omitted the HMI contract's main-line detail;
that prototype and its native builds remain in the work evidence. The
647-path revision was recorded before implementing the additional fields.
Only the five approved D2 bound differences remain permitted.

This is offline preparation. No S3c controller operation is authorized or
performed. Shipping Part III/V1 remain authoritative; V2 remains inactive.

## Ownership and acquisition

The existing PLC Chart remains the single owner of visits, durations and
warning marks. A publication service mirrors these facts after their owning
services. Neither the generic reader nor the HMI accumulates history from
polls. A short step remains visible after it completes.

The [V6.2 extension](AB_CANONICAL_PUBLICATION_S3C_WIRE_DRAFT_2026-10-22.md)
binds one read-only step-definition record to the discovered root. Static
definitions are copied only when their discovered row mapping changes;
recipe-dependent ExpectedTime refreshes on change. FragmentRevision lets
clients invalidate cached definitions. Definitions are separate from the
cyclic root. History and sparse annotations are an on-demand view; ActiveSteps
and the small CurrentStep record are live. Transport tier scheduling remains
the S4 client gate, not a claim established by this preparation reader.

The mode-scoped row mapping follows the legacy oracle's discovery order,
including repeated step numbers in different modes and the valid StepNo 0.
Positive authored-source indices distinguish an empty row from step 0.
Private source records, indices and caches have External Access None and
remain outside whole-read public records. The shared diagnostic resolver
supplies warning keys; the sequence publisher adds no second reason lookup.
CurrentStep condition labels are blank when the chart still describes the
previous step. The PLC's condition results, expected time and timeout remain
authoritative.

The migration gate reads the chart and recipe through their existing readers
and compares all 647 native/logical values with the independent projection.
It retains the equal-even whole-scan generation proof, 100 attempts and
five-second budget. A separate 4,000-byte observer keeps mailbox framing at
500 bytes. The inherited 31-row fixture adds read-only sequence captures to
its existing rows, decisions and held/fault captures. It adds no regression
stimuli or simulation writes. The prepared acceptance audit requires mode
clear, retained fast-step history and handled-warning notes across ST/SFC/LD.

## Explicit scope and gaps

The fixture has one Unit and six CMs, no EM or concurrent branch. Its logical
view has 21 rows and 21 annotation slots, as the legacy oracle publishes.
The Core default MAX_SEQUENCE_ANNOTATIONS is 16: this application uses the
larger, bounded 21-slot view to preserve the owner's selected logical path
set. Core defaults are not silently substituted for an existing application's
published extent. String widths come from the Core declarations (120-byte
step/condition/key text and 80-byte paths); durations remain DINT milliseconds.

ErrorActive is false because the old step vocabulary has no §6.9(d) raise.
ActiveSteps.TimedOut remains the oracle's false value. Per-row Active, Elapsed
and TimedOut are absent from the old snapshot; cursor-based liveness remains
derived by the HMI. CurrentStepTimedOut does publish the existing Unit flag.
Starved/Blocked belong to the later MachineState/OEE migration. The earlier
Decision and status gaps remain as recorded for S3a/S3b. This stage does not
claim full Core sequence conformance or EM/parallel runtime acceptance.

## Readiness correction

The inherited S2/S3a/S3b work scripts tested Mode == 0 and labelled it MANUAL.
The declaration and fixture constants define AUTO = 0, MANUAL = 1. A fresh
read on 2026-10-22 confirms Mode 0, idle, logged out. Those earlier MANUAL
claims are unsupported; their evidence is preserved unchanged. This finding
does not invalidate the separately recorded path/value/type comparisons.

S3c preflight/final checks use app.manual_mode and correctly refuse this
AUTO/idle baseline. No preflight file has been recorded yet. A fixed helper
is prepared to log in through the existing fixture mailbox, request MANUAL
and log out, only after current explicit authorization. It changes no access
policy, configuration, clock or simulation stimulus. It will also normalize
the inherited fixture's AUTO cleanup before final checks. Every actual
controller-changing session still requires the exact identity guard and
current approval under AGENTS.md §3a. No commit or push is authorized.


S3c offline gates now pass: 2,052 AB tests, 74 root tests, both v38 builds
and strict read-backs/access, unchanged S2/S3a/S3b generation/replays, automatic
Capacity 1,107,552 / 3,145,728 Blocks (35%, +115,940 over S3b). Prepared ACD
A2559188...0C2286C remains pinned. Runtime and corrected MANUAL readiness remain
pending current session approval. See [preparation evidence](Evidence/AB_S3C_CANONICAL_PREPARATION_2026-10-22.md).
