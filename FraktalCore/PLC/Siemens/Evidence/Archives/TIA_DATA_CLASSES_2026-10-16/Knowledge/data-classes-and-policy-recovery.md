# Root data classes and independent policy recovery (2026-10-16)

Generator0.23 implements Core3.8d over the shared typed config path. The
composition declares classes per root; registered values optionally select a
class and raise their own minima. One resolver computes all effective levels.
Unclassified values retain DATA_READ/DATA_WRITE; unknown classes or corrupt
levels resolve to ADMIN. Nested modules and shared line values use the requesting
root's policy. **[measured]**

## Native and runtime evidence

- Class fixture: software0errors/0warnings,537 canonical sources,132 FB/type
  interfaces and94 DB interfaces match.16 native assertions and97 live
  mailbox/restart checks pass. **[measured]**
- Current shipped press:254 generated sources replay; both native software
  stages0/0,561 canonical/152 interfaces/62 DB match. Independent native
  GRAPH parity is AUTO19/HOME4/CHANGEOVER6/LoadPosition4; the five LD examples
  retain198 networks/192 calls.254 Siemens tool tests and root/candidate/lint
  gates pass. Full R3/R5/R6, physical and full-download retention are not closed.
  **[measured]**

## Policy and storage

SET_CLASS_LEVEL is ACCESS_POLICY gated, audited and ConfigRev invalidating.
Unknown identities, invalid levels and self-lockout are refused. Policy fields
are externally readonly. Repeating an unchanged level does not advance the
class storage generation. Manifests carry the class identity/effective levels,
keep unreadable metadata and blank only the values. Cyclic data confidentiality
still belongs to the transport. **[measured]**

Classes have a separate version1 image and appended LOAD_DB documents; the
existing ST_AccessPolicy/image and prior document identities/layouts stay
unchanged. Declaring defaults again preserves edited levels by identity. The
native primitive CRC implementation is reused; Serialize/WRIT_DBL/READ_DBL
remain the storage medium. **[measured]**

Actual simulated power cycles override a deliberately poisoned retained class
cache from LOAD_DB and clear the login grant. Damage to both anchors of only
StationA's class document produces an ADMIN fallback and blocks writes until
explicit acknowledgment. StationB's classes and the action policy survive.
Acknowledgment saves the restrictive fallback; recommission its levels through
the normal audited path. **[measured]**

## Set authorization is operation-specific

Saving/deleting require CONFIG_SET, not every record's read level. Loading
requires every record's write level before any staged value commits. Export
requires every read level. A write-authorized but read-denied session can load
a complete model set while its export is refused. Teach capture and line writes
share the same effective-level service. Rejections name the first scope/key and
audit the required level. **[measured]**

## Harness lessons

ST_ConfigPage uses EntryCount/PageCount. Restoring initially reads FALSE before
the first OB scan, so it alone is not an initialized-root witness. The class
probe additionally waits for the declared root class counts2/1. The inherited
fixture deliberately sets CONFIG_SET=ENGINEER; commission a lower test action
gate explicitly before attributing its refusal to class policy. **[measured]**

Complete offline imports/compiles before the simulator's full download. Even
with one extra CPU, overlapping a second TIA compiler left about150MB on C:;
closing only the disposable CPU recovered over4GB without deleting files.
The final run is sequential and cleans up the host. The session owner must
wait for cleanup even if an external stop file already exists. **[measured]**

An SDK RUN call reported RUN and then AccessViolationException in Dispose.
Do not replay that uncertain mutation. Release its disposable session, then
start a separately witnessed attempt. Downloads now observe actual state and
skip a redundant RUN mutation when the CPU is already running; fresh status
observations retain the existing bounded read-only retry rule. **[measured]**

## Native-first scope and continuation

The owner externally updated roadmap7: prefer native S7-1500 mechanisms.
UMAC/web roles do not replace the Core's per-root class/minimum/set semantics;
this service is contract-required. Native alarm/recipe/identity projections and
the V3.1+ UMAC provider retain their target prerequisites. **[owner decision /
Core requirement]**

Runtime model creation, complete Line profile/press integration, manual held,
I/O/PN/forcing, modules, durable host FIFO, OUC line replication, reusable
connectors and broader deployment qualification remain. P12 is OUC TCP by owner
decision; P15 device-specific ports remain deferred. **[measured / owner decision]**

Source of truth: C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_DATA_CLASSES_2026-10-16.md.
Fixture: FraktalCore/PLC/Siemens/Tests/DataClasses. Private native work:
AppData/Local/Fraktal/TiaSpikes/Operations_20261016/classes03 and press_classes01;
final live log classes03_live5.jsonl. Original Fraktal stays RUN/TCPIP at.49 and
192.168.1.1, maps0; physical1214C, storage and certificates remain untouched.
The approved driver hash remains
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
