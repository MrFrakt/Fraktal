# S4b V6.10 Python collector correction — 2026-10-29

The collector now captures every revision/progress scalar declared by the
existing ReadCoherenceBindings and new OwnerReadBindings tables. It discovers
and validates each through the live Symbol list, de-duplicates shared counters,
and retains the exact DINT/scalar requirement. Command/service payloads remain
outside the cyclic read plan. No station declaration or naming inference is
added to this reader.

The [native failure](AB_S4B_OWNER_REVISION_RUNTIME_ATTEMPT_2026-10-29.md) arose
because the earlier collector retained structured Symbols and existing scan/
commit scalars but omitted the new owner scalars. A new test exercises the full
`read_document` acquisition seam with frozen product bytes and synthetic V6.10
metadata. The old sealed code reproduces the same refusal; the corrected code
returns 5,407 values/types. Missing, structured, array and non-DINT owner
counters still refuse. Shared progress appears once; no command payload is read.

Final fresh AB discovery: **2,356 tests pass**. Focused seam/reader suite:
**26 pass**. Root tests/spec/contracts/strict consistency and whitespace pass.
This correction changes only the collector and its tests; plan/status/frozen
status references are updated. Every other one of the original 638 source
bindings matches, including all 35 HMI rehearsal inputs. The [offline proof](AB_S4B_OWNER_REVISION_OFFLINE_2026-10-29.md)
therefore retains 759 HMI passed/12 skips, locked dependencies/analyzer/Windows
build, three final-source 31-view profile passes (383.054/407.711/420.990 ms),
debug STALE comparison, 100 zero-Bad observer samples and four configuration
pages/1,100 exact scalars. Those are peer/offline results, not new native acceptance.

The image is unchanged: ACD
`84EC495F9D526316BC73C8412FAFAF4067B6A942BF1FD27E2369CCC3C516FBAC`, source
`22DD1C2EBBDEFAB9BF45896F810B56DA9D90058274B0C0B1E497FAA303DAEE06`.
Both v38 build/read-back/access/SDK gates and exact automatic Capacity transfer
by these bytes: 66%, 2,077,924 used / 1,067,804 available / 3,145,728 Blocks.
The unchanged image was downloaded/read back successfully in the failed session;
full native value/fixture/desktop acceptance remains open.

That session restored genealogy, the five exact original documents, 31 baseline
cases and all final checks. Echo remains Run/not faulted, MANUAL/idle/logout,
no dumps. This collector correction performs zero controller changes. No
fault/TASK clears, clocks, power/vendor-state operations, hard kills or
credential/binary/ACD archival. The original genealogy ACD stays unopened.

Workspace `C:/work/fraktal-ab-s4b-owner-20261029/offline_01`. The append-only
payload binds the final sources, fresh tests and exact retained-proof transfer.
Next: fresh sealed preparation with measured Capacity confirmation, then E1–E9
together and genealogy rollback under standing O3. V2/Part III stay inactive;
S4b/S5/S6 remain, physical S7 deferred, no commit/push before stage exit.
