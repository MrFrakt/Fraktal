# S4b V6.10 owner revisions — offline qualification, 2026-10-29

O9 is implemented and passes its offline prerequisites. This record claims no
new native ABI, controller runtime, scan improvement or S4b exit. Echo stays on
the restored genealogy baseline; controller changes in this work are zero.

The generated opt-in `canonical_owner_revisions` publishes eight hash-covered
OwnerReadBindings: seven module headers (29 existing leaves) and one read-only
configuration view. The draft's 35-leaf estimate incorrectly assumed ConfigRev
on every child; no field is added. Eight mutable header assignments open their
owner before writing and close once at publication end. Static identity has no
cyclic writer or whole-record copy bypass. View rebuilds, masking and clears
share one owner transaction. Protocol 2 proves equal even versions within its
declared one-second bound, while independent scan progress remains required.
The wrap bound uses 2^30−1 recurring stable tokens; zero initializes the counter
and the recurring sequence wraps to two. Protocol 1, source ages, tiers,
freshness, attempts and D9 write policy remain unchanged.

Python/Dart tests cover malformed and correctly rehashed metadata, schema/scope
coverage, separate DINT counters, mixed-owner partitioning, mutation/deadline
refusal, frozen progress, payload-free Uncertain values, transport retirement,
guarded writes, wrap/odd recovery, access masking, full-width clears, retained
and cold view behavior. The migration oracle accepts the engineering factory
explicitly, preserving its existing default and avoiding a declaration fallback.

The planner also skips routing counts when every array descendant is excluded.
Live scalar count consumers and targeted array reads keep their proofs. An
independent before/after replay has 1,228 → 1,222 reads and 1,955 identical
consumed values/types. This is an optimization, not proof of the earlier
transient STALE cause.

Final gates on Python 3.14 and Flutter 3.47.5 / Dart 3.13.4 at
`C:/work/fraktal-toolchains/flutter-3.47.5`:

- AB discovery: **2,354 passed** (`ab_suite_02.log`).
- HMI: **759 passed / 12 skipped** (`full_hmi_03.log`); locked dependencies,
  analyzer and Windows profile build pass on that source.
- Both v38 targets build/read back equivalently; SDK and effective-access
  audits pass. Eight mutable header writers are verified guarded.
- Root tests: 74 passed; spec, contracts and strict consistency gates pass.
- ACD `84EC495F9D526316BC73C8412FAFAF4067B6A942BF1FD27E2369CCC3C516FBAC`:
  automatic Studio Capacity **66%**, 2,077,924 used / 1,067,804 available /
  3,145,728 Blocks. No byte conversion is inferred.
- L5X `22DD1C2EBBDEFAB9BF45896F810B56DA9D90058274B0C0B1E497FAA303DAEE06`:
  final regeneration is byte-identical to the compiled/Capacity-bound source.
  Opt-out V6.8 output is byte-identical to its earlier source `60C0AB6C…`.

The synthetic rehearsal fixture retains every product byte from sealed native
V6.8 capture `B0EBFBD06853FBAF1262C3B74549F88F99BD9AF37E1585844DC5B9A4291AFB4A`.
All 5,407 values/types match in Python and Dart. Only V6.10 manifest discovery
metadata, Template handles/layouts and owner-counter Symbols are synthetic.
Fixture SHA-256 is `87653D5BC9DC585B0B13B4F451B79330CA8CA8EF2940CCD631A93E8D366B4DE6`.
The peer uses stable owner versions and independent dynamic scan progress;
delay quantiles remain unchanged. Native Symbol/Template ABI must be measured
after the new image is downloaded.

Three consecutive final-source Windows profile rehearsals pass all 31 views:
seeds 7/8/9 have maximum mapped effective ages **383.054 / 407.711 / 420.990 ms**,
all below 700 ms. All 35 source pins agree and still match the working tree.
Debug reproduces STALE after Overview, with 522.097 ms reply wait in the retained
trace. The independent observer passes 100 samples, zero Bad, zero writes and
four pages; a separate configuration producer matches 1,100 oracle scalars.

Earlier failures are retained: the initial HMI run times out in the stalled-RPC
recovery case under concurrent work; an isolated recheck fails the overrun
timing case during SDK preparation. Serial full runs subsequently pass. Profile
01 passes an earlier variant; profile 02 briefly goes STALE between samples.
The final count-walk source then passes profiles 03–05. Initial apparatus/script
invocation failures are retained too. No failed run is erased or reclassified.

Workspace: `C:/work/fraktal-ab-s4b-owner-20261029/offline_01`. The append-only
payload contains source snapshots, logs, failed and passing runs, proofs and
hashes. Credentials, binaries and ACD/BAK are excluded; private image artifacts
remain in the workspace. The untouched original genealogy ACD is never opened.

Next: fresh sealed preparation under standing O3; fresh backup, guarded
Program/download/Run, unchanged 41 candidate cases, all E1–E9 read-only gates,
then genealogy copy rollback, five exact original documents, 31 baseline cases
and final checks. Fault/TASK clears, clocks, power/vendor-state operations and
Echo hard kills stay excluded. S4b/S5/S6 remain; physical S7 is deferred. V2 and
the Part III amendment remain inactive. No commit/push before stage exit.
