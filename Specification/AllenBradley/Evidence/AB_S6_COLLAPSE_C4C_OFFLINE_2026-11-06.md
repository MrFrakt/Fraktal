# S6 WP6.6 C4c ? derived module AOI storage

Recorded 2026-11-06. Offline preparation only; no controller accessed or changed.
This finishes the C4a?C4c split at the handover's accounted press scope. The
remaining HX migrations and their extra facts stay open with O11 in C5/S6-Q.

## Change and preservation

C3 made every module-context field an Input parameter. C4c renders the full
C3 owners temporarily and derives one immutable storage plan from executable
ST, SFC and ladder references. Comments, strings, metadata and serialized
initializers do not count as consumers. No declaration supplies a parallel
field-role list. The plan governs the final AOI definition, instance initial
data and V5 field metadata together.

- An externally written member remains Input. An AOI-owned member read by
  another owner, including O10, becomes Output.
- A member only its AOI uses becomes a local with its declared default.
- A used member whose instance-specific initial value differs from its type
  default stays a parameter; a type local cannot hold that distinction.
- A member with no executable use disappears. An unknown whole-instance
  consumer refuses generation rather than hiding required fields.

All required O10 facts remain parameters. One AOI definition serves every
instance of a module type in an application; its externally required field
set is the union across those instances. Derived signature suffixes prevent
applications with different layouts from reusing a module AOI name. The Unit
AOI also gets a distinct, bounded name because its typed module InOuts change.
The legacy branch stays byte-identical. The original declaration is not
mutated; a private derived emission context carries the plan during generation.

No executable logic is removed. A token comparison against C4b permits only
the intended AOI names, V5 localization-key renumbering, derived counts/build
revision, and text-pool offsets whose full referenced byte slice is identical.
A separate compiled read-back audit checks every parameter/local default and
every module instance's initial values.

## Results

- **2,584 AB tests pass** by full discovery on 422 frozen tool sources/fixtures;
  the primary tree matches every hash. All 18 focused storage/image tests and six portable predicate tests pass.
- **85 root tests pass**, including a fresh primary-tree run; AB spec/contracts
  and strict consistency pass. The predicate baseline carries the six C3 function bodies and provenance hashes;
  the tests need no Git history. The 44 passing Dart gateway tests/analyzer are
  rebound to the unchanged tracked C4b gateway bytes.
- Final source 17 builds and reads back on both v38 targets for genealogy and
  on Echo for press. SDK/access audits and all three initialization audits pass.
- Executable token proof passes over **71 genealogy and 63 press routines**.
  Primary-tree regeneration is byte-identical to both prepared source 17 images.
  The schema-identity gates pass; no undeclared public surface change occurs.
- Offline Studio Capacity: **60%, 1,914,768 used /
  1,230,960 available / 3,145,728 Blocks**, 6,816 below C4b.
- Source SHA-256: genealogy `29AD37C6CD81699B6D6D2DBCFDF51CF9EC8C2D8D26241D4A893E44333E4E9DE3`; press `B39A002ABBB7A927EAE70E6702C0E471C1469E5963AE099C828D540FA772A696`.
  Prepared ACD `E484569007E916997478DCE708A0CDEDE8EF2C00777A8197669E835401D57CE1`.
- Derived roles across each application's four module-type definitions:
  genealogy `{'Unused': 13, 'Output': 36, 'Local': 59, 'Input': 34}`; press `{'Unused': 13, 'Output': 37, 'Local': 58, 'Input': 34}`.
  Counts are per type definition, not per instance; existing `ExecState` is
  additional to these former-context roles.

No download, tag write, mode operation, native scan measurement or retention
acceptance was performed. Capacity is an offline Studio estimate.

The ten storage tests cover actual press/genealogy ownership, O10 visibility,
instance-specific defaults, removal of dead fields, V5 metadata consistency,
unknown whole-instance consumers and distinct bounded AOI names. Existing
scan-by-scan type parity and schema-identity tests remain gates. The C4b
native-capture replay remains an offline replay; it is not a native C4c run.

## Retained investigations

The first edit script misdecoded UTF-8 metadata and changed legacy images.
The exact-output gate caught it. The generator was restored from C4a bytes
and only the intended changes reapplied. Old AOI-name assertions were updated
for the new layout. A root test then found an unconditional planner import in
the legacy projection's isolated module loader; the import is now confined to
the opt-in collapse. A final naming review added derived signatures for
different application-owned layouts. Superseded tests, preparations and their
failed/partial logs are retained separately; none qualifies the final source.
The first token-proof script also used the wrong pool tag, then treated the
packed pool as zero-terminated. Its corrected form uses the emitted Length
and compares the entire referenced slice. The proof also learned both truncated and untruncated Unit-name forms. All earlier findings remain recorded.

## Remaining work and next step

C5 moves the remaining harness command paths to O11 `writeBatch`, accounts
any additional private facts before migrating their reads, and removes Frame
and staged services under V6.12. C6 removes legacy tables/tag exposure; C7
selects one production AUTO rendition. Only then does guarded native S6-Q
measure integrated regression, coherence, retention and scan behavior.
Host-event/persistence ownership, final retirement/documentation and S7 on
physical CIP Security hardware remain open as the plan records. This offline
Capacity result is not a controller scan or native acceptance claim.
