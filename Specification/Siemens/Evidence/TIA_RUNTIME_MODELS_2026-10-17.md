# Bounded runtime models and atomic config recovery (2026-10-17)

Generator 0.24 implements Core §3.8's optional runtime catalog and completes
P7's model-creation software scope. The isolated CPU1516 passes **31 PLC
assertions and 110 live checks**. Creation from either an existing model or a
complete saved/imported model set leaves the running and prepared recipes
unchanged, including while BUSY. Activation uses ordinary changeover.

## Implementation

`model_config.capacity` opts in; missing/zero retains the static profile. Each
root owns a bounded catalog, including roots of the same FB type. Nested Units
use their root's provider. Normal creation appends and preserves existing
indices. The press now advertises capacity 4 over ALUMINUM, PLASTIC and STEEL.
Its five model config fields require one additional document, conservatively
bounded at 2,872 serialized bytes. No project wiring call is added.

One shared typed validator checks source identity/schema, every value's type,
range and read/write access. CONFIG_SET is also required. The complete source
is validated before reserving every destination; copying cannot partially
apply a model. Creation uses private set workspace and cache rows, without
calling the project's recipe prepare/commit phases. The catalog stays private
until the selected LOAD_DB document has been saved and read back. Pending
covers the whole interval; publication advances ConfigRev once.

Catalog plus all created-model config rows form **one atomic document per
root**. Its key hashes the canonical root identity; runtime model codes never
become storage paths. Optional documents append after the existing domains.
Seed-model documents, existing action/class/user/set layouts and indices keep
their identities. Declaration admission checks the Core recipe, record, byte
and persistence-key bounds. This profile requires complete model records at
every root and explicit named-set support. Oversized profiles are refused.

LOAD_DB startup clears the working cache before restoring accepted documents.
The complete catalog and its typed rows validate before any restore mutation.
Missing/corrupt commissioned storage discards that created-model domain,
falls back to the complete seed catalog and reports configuration loss requiring
explicit acknowledgment. It does not reconstruct identities from orphan rows.
Peer catalogs and action/class policies remain independent. Download is a
separate boundary.

Scalar writes, named-set loads and clones now share one row commit and one
medium notification. Set loads reserve missing cache rows before commit.
Changing the active model through a set also notifies station persistence even
when its saved values were unchanged. Complete typed model sets with an absent
catalog code can be imported/exported as recovery sources; LOAD refuses such an
identity, while CREATE can clone it under a new code. New responses clear the
generic unsupported-request report. Class-default literals are inserted after
template expansion so token-looking identities remain data.

The additional LOCAL_RETAIN compile exposed a teach-capture warning: lifecycle
code was reading a VAR_OUTPUT before publication. Captured OutImm/OutCmd records
now use the binding's existing readonly published-static rule (TIA §3.3), as
LOAD_DB quiescence already did. This keeps one owned value and adds no copy or
per-project update call. Conditional startup assignment alone did not remove
the native warning; that attempt was discarded. The final branch is clean.

## Native and runtime results

| Gate | Result |
|---|---|
| Final model fixture | software 0 errors / 0 warnings; 573 canonical objects, 137 FB/type interfaces, 101 DB interfaces match |
| Entirely fresh model project | same clean compile and 573 / 137 / 101 read-back; no prior application types/functions required |
| LOCAL_RETAIN branch | final software 0/0; 412 canonical objects / 103 interfaces / 33 DB interfaces match in the separately created project |
| PLC assertions | 15 model/catalog/reservation checks plus 16 inherited class checks; zero failures |
| Live mailbox/restart checks | 110 pass, zero failures |
| Current press | both software stages 0/0; 591 canonical objects, 156 interfaces, 66 DB interfaces match |
| Source replay / native renditions | 268 press sources; GRAPH AUTO 19, HOME 4, CHANGEOVER 6, LoadPosition 4 steps; LD 198 networks / 192 calls |
| Tool and contract gates | 263 tool tests; repository consistency, Siemens lint and candidate V1 contract gate clean (31 records / 22 enums; full R3 remains open) |

The live checks include both clone sources, independent roots, permission
refusals, malformed/duplicate/oversized code and source-index refusal, a damaged
last source record, full capacity, clear accepted release reports, BUSY and
prepared-recipe isolation, ordinary activation, dynamic writes, unchanged-value
model-set cursor persistence, missing-cache repair, actual restart after retained
catalog poisoning, isolated model-document corruption, peer/policy preservation,
explicit recovery acknowledgment and subsequent creation.

Earlier probe attempts are recorded: the Web API refused a newline STRING
before mailbox commit, so the control-character check moved into a PLC
assertion; an independently restricted commissioning-class read correctly
refused `preset`, so the write-only test now opens that read permission first.
These were fixture expectations/transport constraints. Accepted mutations are
not replayed after an uncertain result.

## Scope and evidence

Native-first review (roadmap §7): no Siemens system instruction supplies the
Core's typed root catalog, clone admission and stable-index transaction. Those
semantics stay in Fraktal; `Serialize`, `WRIT_DBL` and `READ_DBL` remain the
existing native medium. No parallel file store or recipe CSV engine is added.
The LOCAL_RETAIN branch uses the same complete memory transaction; the measured
live restart/loss results above concern LOAD_DB.

The saved original `Fraktal` remains RUN/TCPIP CPU1516 at
169.254.212.49 / 192.168.1.1, unmapped, with Press_Complete_20261015. The fixed
`.55` test CPU is released by its host context. Only copied/offline projects are
compiled; physical 1214C I/O, commissioning gates, saved storage and certificates
are preserved. Offline compiles finish before simulator downloads. The approved
Openness driver is unchanged; no rebuild/whitelist step was needed.

The [sealed payload](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_RUNTIME_MODELS_2026-10-17/packaging.json)
binds raw compile/export data, runtime checks, current source witnesses,
knowledge-index results and SHA-256 checksums. Private credential initializer
bodies, certificates, projects, simulator storage and SQLite backups are omitted
explicitly. A separate current-source witness removes trailing whitespace only
from generated persistence status; all 573 native canonical objects still match.

Seal: 6,738 payloads plus the checksum manifest, 144,074,777 bytes. The checksum
manifest SHA-256 is
`ca9ef9a7f943ea8e49bdc534f98c668da13077e68872ebebdba8e1c9ce2fc6ae`.
Seven private initializer/export bodies are omitted; three public source
derivatives remove only their credential initializer. Public canonical counts
are 572 for Models/FreshModels/CurrentModels, 412 for LOCAL_RETAIN and 591 for
the press; interfaces and DB counts remain unchanged. The exact staged source
checkout also passes all 263 tests. The knowledge index updates four documents
and passes SQLite integrity checks without changing project/general tables.

P7's classes, creation and capture are implemented. Complete Line/press profile
admission, manual held actions, OUC line transport, I/O/PROFINET/forcing, module
expansion, durable host delivery, reusable connectors and full R3/R5/R6/HMI and
deployment/physical qualification remain. Device-specific P15 ports stay deferred
by owner decision. This evidence is a simulated S7-1500 candidate qualification.
