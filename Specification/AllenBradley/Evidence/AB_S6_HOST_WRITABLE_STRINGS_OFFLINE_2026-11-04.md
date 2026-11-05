# S6 — A writable host request, after the first native session

2026-11-04, America/Mexico_City. Entry commit `a1bb0b9be`, with the
uncommitted working tree. This fixes the defect the
[first V6.11 host session](AB_S6_HOST_SESSION_ATTEMPT_2026-11-04.md) found,
and adds the offline gate that would have caught it. No controller was
contacted.

## The defect and the fix

The controller refused the Dart adapter's first host request with CIP 0x0F
(privilege violation). The request tag and both of its types are Read/Write,
but each text member of the chunk (`Scope`, `Name`, `Model`, `Line`, `Keys`)
used a published canonical string type whose `LEN` and `DATA` are Read Only.
So the request was not writable as a whole.

The chunk now uses a family of its own,
`FRK_T_CanonicalString{64,80,160,480}HostV611`, with Read/Write members.
`fraktal_ab_host_services.string_data_types` emits it only when an image has
a mutating host service. It is named within the canonical string family, so
the generator, the tests and both clients recognize it by structure as before.
The canonical width set leaves it out, so no other image changes; the V6.10
owner image regenerates byte-identical. This mirrors the typed command
ingress, which already carries its own Read/Write family
(`FRK_T_CanonicalString{w}CmdV66`).

## The gate that missed it

The effective-access audit checked the ingress types' own members, never the
members of the types nested inside them. A tag's own External Access is not
its effective access: Logix refuses a whole-structure write when any nested
member is less than Read/Write.

`fraktal_ab_access_audit.unwritable_members` now walks every member reachable
from each named writable tag, through every nested type, and reports any that
is not Read/Write. Validated on real images:
- the session's candidate, source 04: exactly the defect (10 findings: `LEN`
  and `DATA` of the five strings);
- the V6.10 owner image's typed command ingress, which S5 wrote natively:
  nothing.

`test_fraktal_ab_v611_image` generates the V6.11 image once and holds both
native rules found on 2026-11-04:
- no BOOL comparison operand (moved from `test_fraktal_ab_st_bool_operands`);
- every member a client writes is writable, across the host request and
  commit and the typed command payload and commit.

Synthetic cases cover a nested Read Only member at depth, a fully writable
closure, and an unknown tag that refuses rather than passes. With the new
family emitted Read Only again, the image test fails.

## Source 05

The preparation in `C:/work/fraktal-ab-s6-host-20261104/prepare`
(`Gates/Prepare/`), all exits 0:
- **Image:** generated `5ADEF279…E2FA`. The V6.10 owner image is
  byte-identical. The BOOL scan is clean.
- **Both v38 targets** build, read back equivalent, and pass the SDK log
  audit.
- **Access:** the candidate access audit now adds the nested closure of every
  writable ingress tag, and the new family to the Read/Write types. It passes
  on both read-backs, 141 canonical types, no finding. Run against source
  04's read-back, it fails on exactly the defect.
- **ACD:** `902831B4…E5C4`, with a read-back equivalent to the source.
- **Capacity:** 2,234,288 of 3,145,728 blocks (71%), verified fit; the
  family costs 928 blocks.

## Gate results

`Investigation/run_gates_01.py` (`Gates/gate_summary_01.json`), all exits 0:
- **Sources:** 5 files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway, and its 25 tests pass,
  none skipped.
- **Python:**
  - the focused suites pass 306 tests with ResourceWarnings raised as
    errors: the image, access, publication, host-service and revision suites;
  - full AB discovery passes 2,515 tests in 1,318 s. That is the previous
    2,511 plus 4: five new image tests, one of which moved from the
    BOOL-operand suite. All 404 module hashes are unchanged during the run.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

## Next

A fresh session on this ACD. It repeats session 01's stages unchanged: the
download, the native restore, the events, the capture and the rollback.
