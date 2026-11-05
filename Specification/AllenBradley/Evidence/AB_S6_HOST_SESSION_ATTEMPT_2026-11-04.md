# S6 — First V6.11 host-services session on Echo: stopped at the native restore

2026-11-04, America/Mexico_City (04:21–04:32 UTC on 2026-11-05). Repository
head `b30dc7e3b`, which regenerates the pinned candidate source byte for byte.
One guarded session on Echo `601FC87B` under the standing owner decision O3,
following plan §4, on the candidate the
[offline preparation](AB_S6_HOST_CANDIDATE_OFFLINE_2026-11-04.md) pinned: ACD
`A4B4FC78…17D3`, source `847C4289…2059`. **The session failed** at its first
candidate writer stage. The genealogy baseline was restored and verified.

## Plan

The session was planned in five steps:
1. download the candidate;
2. let the Dart host adapter restore its live documents from a byte-exact
   session copy of the five baseline documents;
3. run the fixture's core rows to produce host events;
4. capture both host-event rings on one quiet state, for the WP6.5
   equivalence;
5. roll back.

## What happened

| Stage | Result |
|---|---|
| Guard, dump check, MANUAL, preflight | Pass. The preflight equals the re-baseline's record |
| Backup upload | Pass, with SDK and access audits |
| Candidate download | Pass: Program, Download, Run. SDK audit, read-back equivalent, access audit passing |
| Candidate guard | Pass |
| Adapter restore | **Fail** (below) |
| Events, capture | Not run: writer stages stop at their first failure |
| Rollback | Pass: candidate MANUAL, genealogy pin downloaded with SDK and access audits, the original documents unchanged by hash, 31/31 baseline cases, MANUAL, final preflight equal to the session start, final checks, timing |

The Dart adapter (`fraktal_host_adapter.exe`, compiled at the session head)
behaved as follows:
- It discovered the host services natively and reported `serving`, root
  `Press`. This is the first time the V6.11 discovery and the layout
  negotiation against real Templates ran on a controller, and both passed.
- Its first host request, the restore of the first document, was refused by
  the controller with CIP general status 0x0F (privilege violation):
  `host-service write refused (15)`. The adapter aborted its command
  connection. It then retried on its own backoff and never resent an
  unanswered request.
- The candidate stayed restoring, and the restore check timed out after 180 s.

## The defect

The request tag `FRK_Press_HostRequest` is Read/Write, and so is every member
of its two types. But each text member of the chunk (`Scope`, `Name`,
`Model`, `Line`, `Keys`) uses a published canonical string type
(`FRK_T_CanonicalString{80,64,480,160}V6`), whose own `LEN` and `DATA`
members are Read Only. So the request is not writable as a whole. The typed
command ingress avoids this with its own Read/Write string family
(`FRK_T_String{w}CmdV66`).

No offline gate saw it:
- the executed-ST bench has no external-access model;
- the access audit checked each ingress type's own members, not the types
  nested inside them.

## Measured on the candidate

TASK telemetry every 100 ms, from before the download until the rollback:
2,488 samples, 2,398 of them readable (the rest fall within the download).
Maximum scan was 7,767 µs with 0 overlaps, with the candidate in Run and
restoring.

## Artifacts

`AB_S6_HOST_SESSION_ATTEMPT_2026-11-04/Session/` holds the session's logs,
JSON records, scripts, SDK program source, the adapter's log and the session's
document copy (108 files). `withheld_artifacts.json` records the ACDs, L5Xs
and binaries by SHA-256 only. The fixture credential's secret appears in no
archived file. There were no fault or TASK-counter clears, clock changes,
power or vendor-state operations, or Echo hard kills.

## Next

- The host chunk's strings move to a Read/Write string family emitted only
  with host services.
- The access audit, and a standing offline test, check every member reachable
  from a writable ingress.
- Then a fresh candidate and a fresh session.
