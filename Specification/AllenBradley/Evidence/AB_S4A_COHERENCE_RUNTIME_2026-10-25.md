# S4a Echo coherence qualification — runtime acceptance

2026-10-25, America/Mexico_City. **S4a passes at its declared initial scope.
Genealogy and all five original host documents are restored.** All 31 candidate
and 31 baseline cases, idle value/type equivalence, small-group qualification,
offline replays and final/preflight checks pass. This is not full S4 desktop,
read-tier, active-workload, retention or physical/CIP Security acceptance. V2 is
inactive. No commit or push.

## Exact session and current authorization

Owner reply to `call_0aa6207bba714a73bb1e80ee242d1981:0`:
**“Approve guarded S4a qualification”**. The exact scope is sealed in the
[preparation](AB_S4A_COHERENCE_PREPARATION_2026-10-25.md) and recorded in
`Runtime/authorization.json`. It includes fresh backup, MANUAL normalization if
needed, Program/download/Run, five-document restoration and 31 candidate cases,
read-only qualification/equivalence/scan, then pinned genealogy rollback,
original-document restoration, 31 baseline cases and final checks. That grant
is now **consumed**; it authorizes no further controller changes.

Target: local FactoryTalk Logix Echo, **1756-L81E v38.011**, serial **601FC87B**,
127.0.0.1 slot 0, Remote keyswitch, GUID
`91dec7d6-8ac3-45c9-ab2e-0d039c7006fd`. Service, emulator listener, identity,
fault, idle and logout guards pass. The initial Unit was already MANUAL; the
normalization helper performed **zero writes**. The original preflight was
recorded once and verified before deployment and after restoration.

- Pristine prepared ACD SHA-256:
  `07C54E8DCE8D70A1EC487684B65F3596922D615448881AA05470304821CC2FF3`.
- Generated L5X SHA-256:
  `20F27F80CF9D0AEFEFA72EB64848927AE6076CF05CB544073575A55728825996`.
- Fresh backup SHA-256:
  `56E7F7F9E38FBAF89005DFC4145DCBE4832BEAB5D1E21F378C558C9B81445CCC`.
- Immutable genealogy rollback SHA-256:
  `D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.

SDK Save changes only the session's private ACD copy. The pristine preparation
ACD remains hash-matched; deployment read-back is equivalent. **431 other bound
files** match their prepared hashes after execution, before current status docs
are updated. SDK event and effective-access audits pass for backup, deployment
and rollback. Only a hash-checked copy of the immutable rollback original was
opened. No credential fixture, PIN or ACD/BAK binary is archived.

## Candidate and generic discovery results

The unchanged genealogy fixture passes **31/31** cases across its ST/SFC/LD
scope, with input/policy/idle/logout restoration. V6.7's two hash-covered
`ReadCoherenceBindings` rows are recovered from the PLC's own manifest. Their
counter symbols are discovered DINT scalars. No runtime declaration supplies
station facts to the generic reader or small-group probe.

Idle migration equivalence matches **4,428/4,428 paths and types**, with zero
unapproved differences or numeric tolerance, under the existing finite S3
contract corrections. Generic acquisition recovers **4,428 values / seven
modules**. Both raw captures replay afterwards: one to the exact stored
canonical result and oracle comparison, one to the exact generic snapshot.
The migration frame is used only by the separate value-equivalence fixture;
neither the probe nor future shipping client depends on it.

Whole-record generic discovery/acquisition does not establish shipping live
coherence. That evidence is separate from the bounded row measurements below.

## Bounded small-group qualification

The probe discovers **eight groups** and takes **100 acquisitions per group**.
Its declaration-free plan uses Templates, attribute-5 byte sizes, canonical root
discovery and published data-product/counter bindings. It reads seven module
Status records and one fieldbus channel row. Cold/discovery values are excluded
from accepted samples. The manifest is unchanged at the end.

**798 Good / 800 acquisitions; two Uncertain; zero Bad.** Each group passes its
predeclared minimum 95 Good / 100 and shows accepted-counter progress. Both
Uncertain results exhaust the unchanged three-attempt coherence budget and
contain **no raw payload or revision**; they are retained in evidence and never
counted as Good. No retry, time or quality gate was relaxed.

Every Good sample has equal positive even pre/post tokens and an acquisition
window, including the first counter request, below the PLC-published **10,000
µs** interval and the one-second deadline. Accepted-window median/p95/max:
**1227.7 / 1451.4 / 2223.0 µs**.
These statistics describe accepted attempt windows, not full tier or retry cost.
Human-readable timing is rounded to 0.1 µs; raw timing/attempts remain archived.

| Discovered native group | Bytes | Good | Window median / p95 / max, µs |
|---|---:|---:|---:|
| Press.Status | 880 | 100 / 100 | 1215.6 / 1421.8 / 2096.7 |
| Press.PressRam.Status | 872 | 100 / 100 | 1240.8 / 1397.8 / 2223.0 |
| Press.Door.Status | 872 | 100 / 100 | 1218.5 / 1445.7 / 1668.2 |
| Press.PartSlide.Status | 872 | 100 / 100 | 1218.9 / 1487.3 / 1879.2 |
| Press.PartPresentSensor.Status | 872 | 100 / 100 | 1237.2 / 1421.4 / 1727.1 |
| Press.TwoHand.Status | 872 | 100 / 100 | 1223.6 / 1397.3 / 1568.6 |
| Press.AirPressureMonitor.Status | 872 | 99 / 100 | 1223.7 / 1490.9 / 1622.8 |
| FRK_Press_Topology_58beeb34a53312b5.Nodes[0].Channels[0] | 1156 | 99 / 100 | 1244.0 / 1461.7 / 1673.2 |

All **798 Good raw rows** decode again after rollback using the recorded
Templates and exact byte extents. Metadata, per-attempt quality, payloads and
counter observations are retained. These are offline replays from raw bytes,
not 798 separate full-oracle comparisons.

This proves the initial small-group feasibility of contract A on this Echo
fixture. Full client demand/read tiers, liveness/stale-cache rules, every
consumed row, active workloads, connection recovery and desktop rendering
remain S4b gates. Module arrays and arbitrary product plans are not accepted by
this initial measurement tool. No whole-document same-scan claim is made.

## Capacity and native scan

The exact-image automatic Studio offline Capacity from preparation remains
**1,904,400 used / 1,241,328 available / 3,145,728 total Blocks (60%)**.
This is +1,056 Blocks over accepted genealogy S3k; canonical root layout and
cyclic publisher remain unchanged. No physical-controller Capacity claim is
transferred from Echo.

Native TASK GSV measurements (20 samples each, µs):

| Image | LastScan median | Cumulative MaxScan | Overlaps | Task period |
|---|---:|---:|---:|---:|
| V6.7 candidate | 965 | 8990 | 0 | 10,000 |
| Restored genealogy | 99 | 1167 | 0 | 10,000 |

MaxScan is cumulative since task reset; it is not a percentile. It remains below
the 10 ms period in the candidate run. Different-image historical measurements
are not treated as causal estimates of this metadata's scan cost.

## Rollback, final checks and gates

Genealogy downloads back to Run, with clean SDK/access audits. The post-candidate
host medium is backed up, original row values are checked, and the **exact five
preflight host documents** are restored before baseline regression restoration.
All **31/31 baseline cases** pass. Final checks prove Run, not faulted, advancing
scan, MANUAL/idle, logged out, not restoring, original policy, and saved/live
document equality. The session's original preflight verification passes.

**Zero dumps, fault clears, clock changes, power operations or hard kills.**
No failed native session precedes this S4a acceptance; the two bounded Uncertain
read samples are preserved within this successful qualification.

| Gate | Result / runtime payload |
|---|---|
| Approved session | Pass; `session_execution_01.log`, `session_result.json` |
| Backup / download / rollback SDK audits | Clean; `backup_audit.log`, `deploy_audit.log`, `restore_genealogy_audit.log` |
| Native read-back / effective access | Pass; `deploy_readback.log`, `*_access.json` |
| Candidate / baseline | 31 / 31 each; `candidate_regressions.json`, `baseline_regressions.json` |
| Idle path/type equivalence | 4,428 exact; `idle_equivalence.json.gz` |
| Generic V6.7 discovery | 4,428 values, seven modules, two bindings; `generic_capture.json.gz`, `generic_snapshot.json.gz` |
| Small-group qualification | 798 Good, two payload-free Uncertain; `read_group_qualification.json.gz` |
| Offline replays / native result assertions | Pass; `runtime_summary_01.json`, `summarize_runtime_01.log` |
| Native scan | Pass at declared scope; `candidate_timing.json`, `baseline_timing.json` |
| Original host documents / final checks / preflight | Pass; `medium_restored_01.json`, `final_checks.json`, `preflight_final.log` |
| Bound native sources | 431 unchanged, pristine ACD retained; `native_source_verified_01.json` |
| AB suite, compiler/access/Capacity, HMI suite | Reuse exact prepared source/image bindings: **2,320 AB**, both v38 builds/read-backs, **608 Flutter / 12 existing skips**, pinned Flutter 3.47.5/Dart 3.13.4; preparation links exact logs |
| Root suites / AB spec / contracts / strict consistency / whitespace | Pass after status-doc updates; `post_runtime_*_01.log` |
| Full S4 desktop/tier/active-workload / physical security | Not run; open gates, not accepted by this record |

Only status documentation changes after the native source verification. No PLC,
probe or HMI implementation changes invalidate the prepared suite/build results.
Earlier failed offline runs remain in the immutable preparation payload. Owner
Siemens archive edits are untouched.

## Remaining work and next step

**Next is S4b:** implement the headless generic CIP transport/session, port
manifest and logical snapshot mapping with complete goldens, add a worker isolate
and bounded demand/read tiers, qualify active-workload row/liveness behavior,
expose read-only state through the repository/UI, route the factory, remove the
spike and perform Echo desktop acceptance. The current Dart physical decoder
and group guard are foundations, not a completed `CipSessionClient`.

S3 physical I/O proof and the refreshed legacy-consumer census before S6 remain.
S5 adds the Dart gateway/installer/tray and typed commanding behind its existing
write gate; each station needs the owner's write-posture choice. S6 migrates
harnesses, collapses contexts/copies/frame, relocates persistence/events, removes
Python projection/gateway and completes capacity/documentation work. S7 needs
physical v37+ hardware, commissioned CIP Security/TLS and physical acceptance.

Owner decisions pending: persistence medium after its probe, gateway write
posture per station, S7 hardware and commit/push policy. No new permission is
needed to continue authorized offline S4 work; any later controller-changing
session retains its exact-image/current-authorization gate.

Payload: [manifest](AB_S4A_COHERENCE_RUNTIME_2026-10-25/manifest.json).
All prior seals are checked unchanged. Credentials and native ACD/BAK files are
excluded from the archive.
