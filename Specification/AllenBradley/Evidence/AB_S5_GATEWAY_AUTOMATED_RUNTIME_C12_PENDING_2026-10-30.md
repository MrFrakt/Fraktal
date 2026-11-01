# S5 Dart gateway — automated Echo checks PASS; owner C12 pending

Recorded2026-10-30 under the [sealed preparation](AB_S5_GATEWAY_MONITOR_READY_PREPARATION_2026-10-30.md)
and standing O3. Echo601FC87B,1756-L81E v38.011,127.0.0.1 slot0,Remote.
Candidate95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012;
source979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162;
manifestBBA485936140CE9EE1C7693824BB06E935940A335D86A8EB2FBAD9AD35C847B6.
Fresh Capacity66%:2,077,924used/1,067,804available/3,145,728total Blocks.

## Exact outcomes

```json
{
  "automaticCasesPassed": true,
  "qualifiedSessionPassed": false,
  "stageComplete": false,
  "ownerBrowserC12Pending": true,
  "genealogyRestored": true,
  "cases": 12,
  "baselineCases": 31,
  "candidateError": "RuntimeError: S5 automatic/read-only stages failed: gateway_qualification",
  "rollbackError": null,
  "nativeReadGates": {
    "passed": false,
    "readOnly": true,
    "gates": {
      "C1_C11_C13": {
        "passed": false,
        "error": "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\work\\\\fraktal-ab-s5-20261029\\\\session_07\\\\browser_C12_result.json'"
      },
      "simulation_setup_restore": {
        "passed": true,
        "exactRestoration": true,
        "tag": "FRK_Press_AirOk"
      },
      "configuration_readback": {
        "passed": true,
        "pages": 4,
        "scalars": 1100
      },
      "idle_equivalence": {
        "passed": true,
        "paths": 5238,
        "independentComparison": true
      },
      "generic_acquisition": {
        "passed": true,
        "values": 5238,
        "modules": 7,
        "rawCaptureReplay": true
      },
      "native_scan": {
        "passed": true,
        "monitorSamples": 12719,
        "finalSamples": 20,
        "cumulativeMaxUs": 7759,
        "overlaps": 0
      }
    },
    "rollbackGate": "E9 evaluated separately after guarded restore"
  },
  "scanMedianUs": 943.0,
  "scanCumulativeMaxUs": 7759,
  "overlaps": 0,
  "artifacts": 235,
  "payloadManifestSha256": "B7F14BB105D5B1443D0D791365DEB393D84E4D4EEEC7B61867E11D9E904DF0AE"
}
```

All12 automated cases C1–C11/C13 passed through the packaged gateway and actual
OpcUaRepository. C1 discovers seven LIVE modules; C2/C3 correlate native
authentication success/refusal and exclude input secrets from snapshots.
C4 acknowledges AUTO/MANUAL. C5 observes both CM completion counts. C6 edits
station.number1→2→1 with exact restoration and owner revision advancement;
the newly published WriteRevision is accepted without client substitution.
C7 compares four pages/1,100 scalars and types against the independent oracle.
C8/C9 refuse foreign-root and stale/duplicate requests without ACK progress.
C10 refuses all39 kinds on echo-view. C11 observes STALE→DOWN→LIVE across an
owned gateway restart with no replay. C13 ends logged-out MANUAL/idle.

## C12 was not witnessed

The owner confirmed availability before this session. After all automated
cases passed, both gateways remained up from07:22:45UTC for the sealed20-minute
Chrome window. The async checklist/link and VM-local address clarification
were presented. No owner result was received. The helper timed out, closed
its temporary gateways and continued the mandatory independent reads/rollback.
The grouped gate named C1_C11_C13 also requires browser_C12_result.json; its
FileNotFoundError reflects that missing owner witness, not an automatic case
failure. QualifiedSessionPassed and stageComplete therefore remain false.
No browser action, human observation or permission is inferred from elapsed time.

## Independent reads and restoration

Configuration comparison passes four pages/1,100 scalar+type comparisons.
Idle equivalence is exact on5,238 occupied paths; generic acquisition returns
the same number of values across seven modules and independently replays its
raw capture. Logical occupied counts are derived from PLC extents/counts, not
fixed at the5,407 values of the earlier41-case walk. Every value/type/path is
still required. Native TASK maximum is7,759µs with zero overlaps over12,719
monitor samples plus20 final samples; median is recorded above. Fixed simulated
air input restoration passed exactly.

Genealogy rollback, exact original five documents,31 baseline cases, final
checks, preflight and baseline timing passed. Echo ends Run, not faulted,
scanning, MANUAL/idle, logged out, not restoring, with saved/live documents
equal. No dumps, fault/TASK clears, clock changes, controller power/vendor-state
operations or Echo hard kills. C11 stopped only the owned Dart gateway.

The [publication correction](../AB_CANONICAL_PUBLICATION_S5_WRITE_REVISION_CORRECTION_2026-10-30.md)
changes exactly two generated WriteRevision assignments to the existing
configuration owner; data types/initial Tags are identical. Both v38 targets,
read-backs/SDK audits,2,357 AB tests,777 HMI/12 skips,74root tests, analyzer,
locked dependencies, spec/contracts/strict consistency,4gateway tests and17
installer vectors pass. Failed precheck/launch/interlock/revision/startup and
monitor-handshake attempts remain separately sealed. No values, validation,
freshness or row-proof rules were relaxed.

## Remaining and next step

S5 remains open solely for the owner Chrome C12 checklist and its guarded
native session. No stage-exit commit/push occurs before it. The standalone
typed gateway/client/installer work is implemented; direct unsecured CIP
remains read-only. These are local commissioning results, not physical or
CIP Security acceptance. After S5: S6 consumer classification/harness migration,
final oracle replay, declaration-free host services/persistence/events, working
storage collapse, legacy deletion and V2 activation. Physical/securityS7 is
deferred under O2. O1–O9 are already decided; do not re-ask them.

Payload:235 artifacts;manifest SHA-256:B7F14BB105D5B1443D0D791365DEB393D84E4D4EEEC7B61867E11D9E904DF0AE. Credentials,
ACD/BAK/L5X, compiled binaries and cache trees are excluded. Raw failed outputs
and the qualified-session refusal are retained, not rewritten as acceptance.
