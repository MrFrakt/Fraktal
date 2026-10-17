# Runtime models and atomic catalog recovery (2026-10-17)

Generator 0.24 implements Core §3.8 runtime creation. The declaration opts in
with `model_config.capacity`; missing/zero leaves the static provider and does
not advertise ModelCapacity. Each root owns its catalog, even with reused Unit
types. Nested Units share the root. Named-set support is an explicit prerequisite.
**[measured]**

## Transaction and encapsulation

CREATE_MODEL37 uses NameValue=new code, IntValue=source index (0=current), or
BoolValue=TRUE/TextValue=complete saved model set. It requires CONFIG_SET and
every copied value's read AND write access. Typed schema/type/range validation
finishes before all destinations are reserved; then one same-scan memory commit
copies the rows. No project recipe staging/commit is invoked. BUSY creation
preserves live values, prepared values, active identity and existing indices.
Activate through ordinary SET_MODEL/changeover. **[measured]**

Publication waits for one atomic LOAD_DB document containing the catalog and
all runtime-created model config. Pending covers the entire transaction;
ConfigRev changes when the entry becomes public. Keys hash the root identity,
never runtime model names. Optional documents append after old domains. Record,
recipe, key and document-byte limits are checked before generation. The press
uses capacity4 over three seeds; its five config fields add one 2,872-byte
conservative document. **[measured]**

Scalar writes, named-set loads and clones use FRK_ConfigCommit plus the single
ConfigChanged hook. Set loads reserve missing cache rows before commit and
notify ActiveChanged even when loading unchanged model values. Typed complete
sets with an absent catalog code can be imported/exported for recovery; LOAD
requires a known code, CREATE can clone the source to a new one. **[measured]**

## Native and live proof

- Model fixture and an entirely fresh project: software0/0,573 canonical
  objects /137 FB/type interfaces /101 DB interfaces match.15 model checks
  and16 inherited class checks pass. **[measured]**
- 110 live checks pass: both clone sources, permission/refusal paths, BUSY
  isolation, ordinary activation, unchanged-value cursor persistence,
  missing-cache repair, actual restart after retained cache poisoning,
  catalog-domain corruption, peer/policy preservation, explicit ACK and
  subsequent creation. The original Fraktal remains unchanged. **[measured]**
- Updated press: both native stages0/0,591/156/66 read-back;268 sources replay.
  GRAPH AUTO19/HOME4/CHANGEOVER6/LoadPosition4 and LD198networks/192calls are
  unchanged.263 Siemens tool tests and root/lint/candidate gates pass.
  Full R3/R5/R6/HMI and physical qualification remain open. **[measured]**
- LOCAL_RETAIN: final native0/0 and412/103/33 read-back in a separate fresh
  project. Live restart/loss results above concern LOAD_DB. **[measured]**

The fixture is `FraktalCore/PLC/Siemens/Tests/Models`; report is
`Specification/Siemens/Evidence/TIA_RUNTIME_MODELS_2026-10-17.md`.

## Recovery and engineering lessons

LOAD_DB startup clears cache/active scratch state before accepted documents
restore. Whole-image validation/reservation precedes any cache/catalog mutation.
Missing/corrupt commissioned model storage falls back to complete seeds and
requires configuration-loss ACK. Never rebuild catalog identities from orphan
rows. Peer catalogs and class/action policies have independent documents.
Download is a separate boundary. LOCAL_RETAIN shares the memory transaction;
the live restart/corruption evidence above concerns LOAD_DB. **[measured]**

Native-first review: Core owns the typed catalog/clone contract; Serialize,
WRIT_DBL and READ_DBL continue to own persistence. No second file/CSV store.
Definitions needed by typed catalog helpers import as18_Def_* before19_Model*
and20_FB*; the fresh-project proof catches accidental old-object dependencies.
Public ModelCapacity is readonly; private backing storage and authored-logic
guards remain enforced. **[measured]**

Teach capture reads its source record as lifecycle state. Such OutImm/OutCmd
records must be readonly published statics (TIA §3.3), as LOAD_DB's quiescence
already required for OutImm. Reading a VAR_OUTPUT before cyclic publication
produces an S7 warning; a conditional startup assignment did not cure it. The
final owning-storage rule needs no mirror/copy or project update call. The
LOAD_DB sources remain identical to the tested branch. **[measured]**

The Web API refused a newline STRING before mailbox commit; test control
characters inside PLC assertions instead. To isolate write access, open ALL
source reads first, including commissioning-class reads. A report left by
the generic unsupported handler must be cleared when a typed handler accepts.
Avoid JSON/PowerShell quote loss in Python -c; use a script file. **[measured]**

Finish offline TIA compiles before full simulator downloads. One extra CPU is
not sufficient protection against overlapping compiler/download disk usage.
Fresh read-only SDK status can retry AccessViolationException; uncertain
mutations must not replay. Download can already start the CPU: observe status
before issuing RUN. The isolated host always closes in finally. **[measured]**

P7 classes/creation/capture are implemented. Complete Line/press admission,
MANUAL_HELD, OUC TCP, I/O/PROFINET/forcing, module expansion, durable host FIFO,
reusable connectors and deployment/conformance gates remain. Device-specific
P15 targets remain deferred by owner decision.
