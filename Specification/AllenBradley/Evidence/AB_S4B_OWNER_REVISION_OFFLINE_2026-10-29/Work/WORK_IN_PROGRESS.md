# Active O9 implementation, 2026-10-29

Owner approved V6.10 via call_440bb9c9544b4ea78c5cfdde3f44d706:0. Approval is
recorded in live review/plan/status, sealed investigation is untouched. No native
changes in this implementation yet; Echo remains genealogy. Standing O3 allows
guarded sessions after all gates. No commit/push until stage exit. No subagents.

Inventory correction: existing root Status has ConfigRev; six children do not.
Actual selection 29 fields, seven header owners plus one config-view owner.
rows() derives members from schema; do not add six new Core fields.

Current Python: new canonical_owner_revisions opt-in, owner_read_bindings module,
owner profile, schema/header/manifest V6.10, conditional header writes at original
points (open odd once, close all at publisher end), config-view rebuild/clear
seqlock plus versioned private WORK and LastInvalid. Old V6.8 output must remain
unchanged. Six owner-binding/VM tests passed (owner_binding_tests_01). Python
snapshot metadata validation partly integrated. Need complete scope checks,
writer coverage and executable config-view tests. Existing old unittest process
72105 still running at last poll (unlogged initial dots; capture completion).

Current Dart: binding protocol/progress/proofWindow fields, protocol-2 guard max
1s, manifest table parsing/hash/bindingFor, publication owner validation, plan
leaf-cache, owner lookup, progress refresh and partial group partitioning. First
50 existing focused tests passed (hmi_coherence_tests_01). New protocol tests are
added but unrun. Needs rigorous new-owner golden/capture, freeze-progress,
partition/coherence/source-age tests; progress refresh failure abort/bounds audit.

Generated metadata-only fixture (no native ABI claim):
HMI/test/fixtures/cip_owner_manifest_v610.json.gz via AB/tools/
fraktal_ab_owner_read_fixture.py. Use it for cross-language manifest tests.

Next: finish tests/reader, compile both v38/readbacks, exact Capacity, create a
V6.10 rehearsal fixture by retaining frozen native V6.8 Core bytes and generating
only new metadata/templates/counter symbols (explicit synthetic apparatus).
Rehearsal peer must serve owner revision symbols as stable DINTs and preserve
dynamic scan ProgressSymbol. Need three exact-source profile passes/debug before
native prep. New protocol uses row-owned versions, not simply a wider old guard.
Old protocol still <10ms, fast 1/3s and slow 7.5/15s unchanged. All E1–E9 in one
guarded session + genealogy rollback remain; S5/S6 follow, physical S7 deferred.

Toolchain: C:/Python314/python.exe; Flutter3.47.5/Dart3.13.4 at
C:/work/fraktal-toolchains/flutter-3.47.5. run_logged.py creates exclusive logs.
Never include credential contents or ACD/binaries in repository evidence.

## Superseding checkpoint, 2026-10-29 22:48 UTC

All implementation and new tests are present. Python/Dart validators require
exact eight scopes/29 header leaves, separate counters and exact schema members.
Progress refresh bounds/aborts are complete. 10 publisher/VM tests and 3 synthetic
apparatus Python tests passed; 5 owner integration tests + guards/manifests pass.
New migration oracle factory support has two tests; full discovery now includes
2,354 tests (first full discovery ran 2,349 before those five tests were added).

Both v38 builds/readbacks/access/SDK audits pass. Canonical L5X SHA22DD1C2E...,
prepared ACD SHA84EC495F...516FBAC, Capacity66%=2077924 used/1067804 available/
3145728 total Blocks. Eight mutable header writes verified guarded, no whole-
record bypass. Current opt-out generation is byte-identical to the old V6.8
L5X SHA60C0AB6C... . Owner token wrap proof conservatively uses2^30-1 recurring
stable values (zero is initial, wrap goes to two); emitted PLC logic unchanged.

Synthetic V6.10 apparatus fixture `test/fixtures/cip_owner_apparatus_v610.json.gz`
retains all native product bytes; 5407 values/types exact. SHA87653d5b... . Peer
serves stable owner counters and independent dynamic scan progress. No native
ABI claim. Metadata-only fixture also retained.

P4 FINAL SOURCE PASSES: profile_03(seed7)383054us, profile_04(seed8)407711us,
profile_05(seed9)420990us; all31views, same35 source pins, <=700ms. Proof in
three_profiles_01.json. Debug reproduces STALE after overview, replyWait522097us.
Observer/config peer passes100samples zeroBad and4pages/1100exactscalars.
profile01 passed earlier variant; profile02 failed transient inter-sample STALE.
New consumed-scope index avoids counts for wholly excluded arrays, preserves
targeted/live consumers. 37 focused tests pass. Before/after replay1228->1222
reads,1955identical values/types. Do not claim this proves causality for STALE.

Fresh full HMI03=759 passed/12skipped (serial). Earlier full01 failed a timing
case and isolated recheck failed another timing case during SDK preparation;
full02 passed758 before count optimization. Preserve every log.

RUNNING: AB discovery02 session26136 (started22:44), final owner generation01
session64308. Need confirm regenerated L5X identical22DD. Final locked/analyze/
Windows gates02 are starting via final_hmi_gates_01.py. Root gates01 passed74;
rerun after docs/frozen status updates. No controller changes, Echo genealogy;
O3 standing use only AFTER all gates and sealed preparation. No new session
workspace yet (plan P4 prerequisite now met). Next: final gates, seal offline
proof, create fresh session with new pins/owner declaration and explicit oracle
factory, SDK/helper/denial/workflow tests, prebuilt native desktop, seal prep,
apply O3, run E1-E9 + genealogy rollback. Use independent configuration_comparison
from this W, not old conditional observer producer.
