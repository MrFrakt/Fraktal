# R1/R2 canonical preparation — offline gates pass; native session pending

Client date: 2026-10-24, America/Mexico_City. The owner approved R1 offline
implementation and R2 native acceptance **in principle**, in the handover's
recorded “all of them approved” decision. This record grants no controller
changes. The combined exact image and guarded apparatus are now prepared.
**Current explicit confirmation is required before backup/download, mode or tag
writes.** Authorization is false. No commit or push.

## Result

R1 adds the declaration opt-in `canonical_type_manifest` and the generic V6.4
reader. It replaces instance-path Fields with sparse TypeAnnotations and
PathExceptions. R2's existing `canonical_table_driven` form remains enabled
only in this candidate. All accepted declarations keep both opt-ins off.

| Image | Used / available / total Capacity Blocks | Displayed usage |
|---|---|---|
| Accepted S3i | 2,763,512 / 382,216 / 3,145,728 | 87% (about 88% rounded) |
| R2 alone, prior offline measurement | 2,014,032 / 1,131,696 / 3,145,728 | 64% |
| Prepared R1 + R2 | **1,653,432 / 1,492,296 / 3,145,728** | **52%** |

R1 saves 360,600 Blocks beyond R2; together they free **1,110,080 Blocks**
from accepted S3i. These are measured offline Studio estimates for the exact
ACDs, not native scan or runtime acceptance. Native TASK timing remains open.

The S3i manifest has **137 type annotations and two exceptions**. The review's
136 estimate deduplicated the logical SequenceSteps path before counting
owning UDTs: the live root and its definition fragment both need a row.
An added cylinder module of an existing type adds **zero manifest rows**.
Every physical array needs an extent, including those below empty views.
A count sibling can be supplied by a disjoint bound record at the same logical
parent; the reader validates the joined schema before resolving it.
Non-sibling counts or conflicting type facts are refused. The reviewed
exception columns represent explicit index selections only.

## Exact image and gates

- Source L5X SHA-256:
  `C3E1FA7EEACB927B98AC0177E51D44A2E132BC1C1677ACC07583A46C02021333`.
- Prepared/pristine ACD SHA-256:
  `D170F1E3BA9CCBF4FB00CF265FB43E43FC40FFB82CDF95322C48570D33FF906C`.
- V6.4 ContentHash:
  `89A5B02938107D4152C00AB736EC575333252ADFD3878E9246AF10A0CC63A49C`.
- Legacy genealogy identity remains `6DEC4C1DC2F7F78A`.

| Gate | Result / exact output |
|---|---|
| AB discovery suite, final | **2,227 pass**, 347.686 s reported by unittest; driver 349.280 s; `Offline/ab_suite_03.log` |
| Root test suites | **74 pass**; `Offline/root_tests_03.log` |
| AB spec / contracts / strict consistency | Pass; final logs under Offline and Preparation |
| v38 EchoController and PhysicalController | Import **0 warnings / 0 errors**, accepted build; clean SDK audit, both targets |
| Strict read-back, both targets | **Equivalent=true**; 59 executable bodies, 42,930 authored initial values, no differences; SFC 21 steps equivalent |
| Effective access, both targets | Pass; 154 controller tags; published Read Only, existing mailbox write surface, new tables private as appropriate |
| Prepared ACD read-back | Equivalent=true |
| Automatic Studio Capacity | Measured=true, VerifiedFit=true, source unchanged, review process closed; 52% |
| Old accepted images | **10 / 10 byte-identical** with opt-ins off, S2 through S3i |
| Sealed capture replay | **1,147 / 1,147** across V6.0–V6.3 and all ten stages; same path values/types/dataValues/counts under V6.4 |
| Replay configuration identity | Actual V6.4 tables rehashed; only snapshot ContentHash/ConfigRevision differ, as required by the new wire format; no canonical value/type exclusion |
| Prior seals | **50 records / 11,085 artifacts** and their reports verify unchanged, including expanded compressed hashes |
| Fresh workspace | Sealed predecessor copies as bytes; byte-level path rebinding recorded, explicit profile changes enumerated; pristine deployment/review/retained-control copies all match the ACD pin |
| Session helper | Build succeeds, **0 warnings / 0 errors** |
| Download-gate dry check | Every file-bound helper comparison passes; fresh runtime backup and live preflight are deliberately still required |
| Negative authorization | **6 / 6** refuse before SDK/controller/credential access; retained cycle contains no download/save |
| Profile dry check | Both opt-ins, stage 11, exact manifest and ACD pin agree; legacy identity unchanged |
| Read-only Echo guard | 601FC87B, v38.011, expected local service/listener, remote keyswitch, Run, not faulted |
| Read-only baseline state | MANUAL/idle, logged out, five saved/live documents equal |
| Native R1/R2 download, regressions, scan and rollback | **Not run — current exact-image confirmation pending** |
| HMI / physical / CIP Security gates | Not run; no HMI change or physical acceptance claim |

## Proposed guarded native session

Target: local Echo **601FC87B**, 1756-L81E v38.011, 127.0.0.1 slot 0.
This folds R1 into the same R2 acceptance image. No new write vector is added
to the accepted S3i lifetime apparatus:

1. Current identity/service/listener/fault/keyswitch and no-driver/dump guards;
   guarded MANUAL normalization only when needed; fresh preflight and backup.
2. Guarded Program/download/Run of the exact ACD above. Download saves into
   its deployment copy; the pristine review/control copies remain pinned.
3. Five-document restoration and **41 candidate cases**, with read-only paired
   value/type equivalence and the eight first-scan Line publication vectors.
4. The same fixed calendar/target vectors: at most **64 public Line commits**
   (38 normally), natural closure, 40→99 target deferral, exact original-value
   restoration and independent 4,000-byte capture sockets.
5. **One retained Program/Run without download or save during that cycle**,
   eight first-scan vectors again, exact retained value/type equality, full
   idle equivalence, generic acquisition and twenty native TASK samples.
6. Hash-checked genealogy rollback copy, five-document restoration,
   **31 baseline regressions**, MANUAL cleanup and final state/scan checks.

Fault clears, clock changes, firmware/network changes, power operations,
hard kills and vendor-state edits remain excluded. An active login or failed
guard stops the workflow. Failed candidate steps still enter the inherited
rollback path. Independent byte/reference replays are required after the run.

## Development failures retained

The first focused refactor run lost a conditional sequence import; it was
restored and regeneration then matched the compiled source byte for byte.
The intermediate full suite ran 2,227 tests with one error because an existing
fixture test uses the module's legacy import; that import was restored and
the final full suite passes. Early replay development exposed fragment/native
sibling count resolution, now covered by tests and all sealed replays.

The archive scanner first encountered a non-object JSON root, and three initial
SDK audit CLI calls used a variadic flag incorrectly; corrected runs pass.
A read-only invocation of final_checks stopped because the fresh session
preflight did not yet exist; the separate baseline-state probe then passed
without creating the session preflight. These attempts remain in the payload;
none performed a controller-changing operation. See development_attempts_01.json.

## Work locations and boundary

Offline: `C:/work/fraktal-ab-s3j-20261024/r1_01/`.
Session: `C:/work/fraktal-ab-r1-r2-20261024/prepare_8f74e954758141dd81821a0c1316c2ef/`.
Append-only payload: [manifest](AB_R1_R2_CANONICAL_PREPARATION_2026-10-24/manifest.json).
No credential file or ACD binary is archived. Owner Siemens archive changes
are untouched. V2 remains inactive. S3j, S3k, press renditions and S4–S7 remain
open; the next action is exact-image native session confirmation, then its
measured acceptance, before the dependent implementation stages.
