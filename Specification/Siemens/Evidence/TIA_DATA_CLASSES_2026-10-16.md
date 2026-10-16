# TIA data classes and independent policy recovery — 2026-10-16

Generator0.23 implements Core§3.8d over the existing typed configuration path.
The isolated CPU1516 fixture passes16 PLC assertions and97 live checks. Both
the class fixture and the separately regenerated press compile with zero
software errors and warnings. This extends the candidate implementation;
full R3/R5/R6, generic HMI acceptance and physical conformance remain open.

## Behavior and ownership

The composition declares named classes per deployed root, with stable identity,
label and default read/write levels. A registered value optionally selects a
class and may raise its minima. One shared resolver computes the effective
level. Blank class identities retain DATA_READ/DATA_WRITE; undeclared classes
and invalid levels resolve to ADMIN. Each typed ownership walk carries the
requesting root's policy, including shared line values and nested modules.

Manifests publish ClassId and effective levels. Unreadable entries retain their
metadata and serve an empty value. Individual writes, teach capture, line edits,
set loads/import validation and exports use the same authorization service.
Refusals publish the first scope/key, an ACCESS release record and an audited
required level. Cyclic symbol confidentiality remains the transport's job;
manifest redaction does not claim to secure raw process-data reads.

SET_CLASS_LEVEL uses ACCESS_POLICY, rejects unknown classes, invalid levels and
self-lockout, audits the identity/direction/level and invalidates ConfigRev.
An unchanged level is accepted without another class-storage generation.
The policy table is externally readonly; application code cannot assemble its
boot/save/operation calls or mutate its private backing store. Owning frames
perform those calls automatically; projects add no per-scan correctness call.

The set paths previously required read access when saving and both read/write
access when loading. Core§3.8d(e) requires CONFIG_SET for saving/deleting, each
record's write level for loading, and each read level for export. The shared
walk now applies those rules. Validation finishes before any staged value is
committed. Changing a policy also affects previously saved sets.

## Native-first review and compatibility

Roadmap§7 was updated outside this session and has been incorporated. Native
UMAC/web-server roles establish identities and transport rights; they do not
own Fraktal's root-scoped value classes, minima, manifest presentation or atomic
set admission. Those Core behaviors therefore remain in one shared service.
Storage continues using native Serialize/Deserialize, WRIT_DBL and READ_DBL.
The existing owned CRC primitives remain the integrity algorithm; no LGF
dependency or additional credential provider was introduced.

Class policy has its own version1 image and optional LOAD_DB documents, appended
after the existing documents. ST_AccessPolicy, FRK_AccessPolicyImage and prior
document identities/layouts remain unchanged. Declaring defaults at startup
preserves commissioned levels by identity. New deployments without class
declarations allocate no class table. A damaged class domain fails closed,
blocks writes and requires explicit acknowledgment of its restrictive ADMIN
fallback. It does not overwrite a healthy action policy or a peer's classes.
This is not a full-download retention qualification.

## Measured gates

| Gate | Result |
|---|---|
| Class fixture native software compile |0 errors,0 warnings |
| Class canonical source/type read-back |537 matches |
| Class FB/type interfaces |132 matches |
| Class global DB interfaces |94 matches |
| Class PLC assertions |16 passed |
| Final real-mailbox/restart probe |97 checks,0 failures |
| Current press software compile |Both stages0 errors,0 warnings |
| Press canonical sources / FB-type interfaces / DB interfaces |561 /152 /62 matches |
| Press generated-source replay |254 sources |
| Independent native GRAPH parity |AUTO19, HOME4, CHANGEOVER6, LoadPosition4 steps |
| Independent native LD parity |198 networks,192 calls across five examples |
| Siemens tool suite |254 passed |
| Root consistency / candidate contract / Siemens lint |Clean; immutable V1 subset remains31 records/22 enums |

The live probe verifies public classes below blanket DATA_READ/DATA_WRITE,
raised minima, unknown-class fallback, readonly policy storage, class editing,
teach capture and separate peer policies on the same shared line. It saves a
set containing unreadable values, refuses its export, rejects an unauthorized
load without changing earlier staged values, and proves that an authorized
write-only session can load a set despite lacking read access.

After commissioning a class at level2, the fixture poisons its retained cache
to level0 with an invalid checksum. An actual simulated power cycle restores
level2 from LOAD_DB and clears the login grant. A second power cycle follows
damage to both anchors of only StationA's class document: its classes become
ADMIN, writes remain blocked until acknowledgment, StationB keeps its own
level2 policy, and existing action thresholds survive. The probe recommissions
the fallback, removes its sets, restores its settings and logs out.

## Probe and resource corrections

Earlier attempts used incorrect manifest field names, omitted the inherited
CONFIG_SET=ENGINEER prerequisite, or sampled the initial FALSE Restoring flag
before the first OB scan initialized the roots. The final probe uses the actual
EntryCount/PageCount contract, explicitly commissions its test action gate, and
waits for the declared root class counts after the restore barrier.

One SDK run request reported RUN and then failed in CInstanceNet.Dispose with
AccessViolationException. The action was not replayed; the disposable session
was released before a new run. Downloads now observe actual state first and
avoid a redundant RUN mutation when the download already started the CPU.

Overlapping a second offline TIA compiler with the disposable CPU's full
download left about150MB on C:. Releasing that CPU recovered over4GB without
deleting files. Complete offline imports/compiles before hosting/downloading;
one extra CPU alone is insufficient when two TIA processes overlap. The final
run was sequential and its host cleanup completed. Session cleanup also waits
for the host when an external stop file already exists.

The saved original Fraktal remains RUN/TCPIP at169.254.212.49 and192.168.1.1,
with zero interface mappings. Its storage, certificates and program were
preserved. The physical1214C and output commissioning gates were untouched.

## Remaining scope and payloads

P7 runtime model creation remains. Full Line-profile press integration, manual
held commands, generic topology/PN health/forcing, module expansion, durable host
delivery, owner-selected OUC TCP replication, reusable connectors and broader
deployment/physical gates remain in the roadmap. The normal generator still
refuses partial Line profiles. Native alarm/recipe/identity projections and the
UMAC provider proposals in roadmap§7 retain their stated target prerequisites.

Raw native exports, source snapshots and run/cleanup logs are in
[`TIA_DATA_CLASSES_2026-10-16`](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_DATA_CLASSES_2026-10-16/).
Credential initializer bodies, engineering projects, simulator storage,
certificates, SQLite backups and caches are excluded. Hash witnesses record
private omissions. Prior sealed archives are unchanged.

Seal:3,558 payloads plus SHA256SUMS.txt,72,447,445 bytes including that file.
The checksum file's SHA-256 is
`646d8c24c0911d7c4401b489d51627f37a0fdb4eb6ea250e616f335305e001dc`.
There are three private initializer/source-export omissions with hash witnesses
and one public derivative preserving the other functions in a combined source.
Independent public replay verifies536/132/94 class objects/interfaces/DBs and
561/152/62 press objects/interfaces/DBs. All3,559 archive files byte-match the
Git index. The intended staged source also passes254 tool tests independently
of unrelated working-tree edits. SiemensAgent indexes43 curated/report
documents, preserves project/general tables and passes SQLite integrity.
