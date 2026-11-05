# S6 — The V6.11 host-services candidate, prepared offline

2026-11-04, America/Mexico_City. Entry commit `56ee25a88`, with the
uncommitted working tree. This prepares the first V6.11 image for a native
session, per plan §4 step 1. No controller was contacted. The preparation ran
in `C:/work/fraktal-ab-s6-host-20261104/prepare/`, and its records are copied
into `Gates/Prepare/` without any L5X or ACD.

## The candidate

`fraktal_ab_genealogy_s6_host_demo` is the approved V6.10 owner-revision
profile plus the `canonical_host_services` opt-in, in the same one-flag
pattern as the S4b profile. It is pre-collapse, so it still emits the legacy
host-event ring and staged endpoints beside V6.11. A single native capture can
then compare the canonical ring with the legacy one before WP6.6 removes the
legacy ring.

Its emitted image carries:
- the host request and commit (Read/Write);
- the reply and the ring's owner revision (Read Only);
- the host work and sample storage (None);
- the manifest table and the host set routines.

## Four sources, three defects

The first v38 builds of the V6.11 code found two defects that every offline
gate had passed. Preparation found a third before either was fixed.

| Source | SHA-256 | Result |
|---|---|---|
| 01 | `6F3EAB0D…0B62` | Both v38 targets refused: `RxSTX_E_BOOLOPND_UNEXPECTED - BOOL tag not expected in expression` |
| 02 | `D9628764…1F29` | Both targets build, read back and pass the SDK and access audits; Capacity 2,225,560 of 3,145,728 blocks. Its revision guard refuses every document saved before V6.11 |
| 03 | `97D3B1E8…077B` | Both targets refused: `RxE_EXCEED_MAX_OPERAND_CHAR_LENGTH - Operand exceeds maximum length` |
| 04 | `847C4289…2059` | Every gate passes (below) |

**1. A BOOL comparison operand.** The SDK names no routine or line. A scan of
only the ST lines V6.11 adds found exactly one, in `ScanCanonical`'s ring
change test:
```
Press.HostEvents.Wrapped <> (FRK_Press_HostEvents.Wrapped <> 0)
```
It resolved each dotted operand through the image's tags, structures and AOI
parameters. The canonical `Wrapped` is BOOL, and Logix ST has no BOOL
comparison; `XOR` is its inequality and is what
`fraktal_ab_canonical_traceability` now emits. The executed-ST model accepted
the original because Python's `bool` is an integer.

**2. Documents saved before V6.11 refused.** The set transaction accepts a
document's configuration revision only from an exact list: its own and those
of exact predecessors. The list exists so that a change of build identity alone
never strands an operator's saved sets. The opt-in changes build identity but
not one editable value, yet each derived variant kept the opt-in. So the V6.11
image accepted 61 revisions, of which neither the V6.10 owner image's
(`14896938`) nor the genealogy baseline's (`7203916`) was one. Its first
download would have refused the five documents it must restore.
`fraktal_ab_sets.accepted_revisions` now also accepts each variant without the
opt-in, exactly as it does for the model catalog, the signal tower and live
documents.

**3. The longer guard exceeds a native limit.** That doubles the list to 122
revisions. As one `IF` condition it is 4,529 characters, which v38 refuses,
while the 61-revision one (2,284 characters) builds. `revision_guard` now nests
groups of at most 61 revisions: a revision is refused only when it differs from
every group, the same conjunction in shorter operands. 61 is the most any
earlier declaration has, so every earlier image keeps its single-line guard;
the V6.10 owner image regenerates byte-identical.

## Source 04 gates

`Gates/Prepare/prepare_candidate_04.json`, all exits 0:
- **Image:** generated `847C4289…2059`. The V6.10 owner image regenerates
  byte-identical to before the change. The BOOL-operand scan finds nothing in
  15,893 lines.
- **Both v38 targets** (EchoController, PhysicalController): build, read back
  equivalent, and the SDK log audit (Open project, Build, Save As) passes.
- **Access:** the S5 effective-access audit with only the host ingress added:
  - the request and commit expected writable;
  - the reply and ring revision expected public;
  - the request and chunk types expected Read/Write.

  It passes on both read-backs, 137 canonical types, no finding.
- **ACD:** prepared as `A4B4FC78…17D3`, and its read-back is equivalent to the
  source.
- **Capacity:** Studio's offline estimate on a review copy, with the ACD
  unchanged: 2,233,360 of 3,145,728 blocks (70%), verified fit. The V6.10
  image used 2,077,924 (66%); the longer guard costs 7,800 blocks.

## New offline gates

- **`fraktal_ab_st_bool_operands`** makes defect 1's class an offline failure.
  It resolves each operand per statement, joining the formatter's
  continuation lines, and reports a BOOL beside an arithmetic or comparison
  operator. It reports:
  - nothing in the accepted V6.10 image (14,109 lines);
  - nothing in the fixed one;
  - exactly the refused statement in source 01.

  Its test covers refused and accepted forms, split statements, AOI scopes
  and the emitted V6.11 image. With the old `<>` restored, the image test
  fails.
- **`test_fraktal_ab_host_revision_compatibility`** (7 tests), in the shape of
  the S3k one, executes the guard in the ST model:
  - the V6.10 owner's and the genealogy's revisions are accepted;
  - every revision the predecessor accepts is still accepted;
  - a changed value shape and a foreign station refuse;
  - unknown and future revisions refuse;
  - the nested guard decides every accepted and refused revision as the
    whole conjunction does, within the length v38 has built.
- **The Dart bench** gains a live-documents test:
  - documents saved by the build without host services, with that build's
    revision, are restored through the adapter, with no loss;
  - without the fix it fails, because the restore never completes.

  The bench server's `document` op gains the matching `predecessor` option.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`), all exits 0:
- **Sources:** 8 files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway. Its 25 tests pass (the 21
  bench tests and 4 others), none skipped.
- **Python:**
  - the focused suites pass 242 tests with ResourceWarnings raised as
    errors: the new two, every existing revision-guard suite, and the host
    service, set, live, event and reader suites;
  - full AB discovery passes 2,511 tests in 1,192 s. That is the previous
    2,499 plus the 12 new tests, with all 403 module hashes unchanged during
    the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

## Boundary

All of this is offline. The next step is the native session the plan's §4
describes, on this exact ACD:
- the Dart adapter restoring the candidate's live documents natively;
- the fixture's core rows producing host events;
- a capture of both rings on one quiet state, for the WP6.5 equivalence;
- then the genealogy rollback.
