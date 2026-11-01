# S5 gateway — ATTEMPT; C12/qualified acceptance remains open

Recorded2026-10-30 under [sealed preparation](AB_S5_GATEWAY_C12_RETURN_PREPARATION_2026-10-30.md)
and standing O3. Echo601FC87B,1756-L81E v38.011,127.0.0.1 slot0,Remote.
Candidate95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012;
source979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162;
manifestBBA485936140CE9EE1C7693824BB06E935940A335D86A8EB2FBAD9AD35C847B6.
Fresh Capacity66%:2,077,924used/1,067,804available/3,145,728total Blocks.

## Exact results

```json
{
  "automaticCasesPassed": true,
  "qualifiedSessionPassed": false,
  "stageComplete": false,
  "ownerBrowserC12Pending": true,
  "ownerBrowser": {},
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
        "error": "FileNotFoundError: [Errno 2] No such file or directory: 'C:\\\\work\\\\fraktal-ab-s5-20261029\\\\session_08\\\\browser_C12_result.json'"
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
        "paths": 5264,
        "independentComparison": true
      },
      "generic_acquisition": {
        "passed": true,
        "values": 5264,
        "modules": 7,
        "rawCaptureReplay": true
      },
      "native_scan": {
        "passed": true,
        "monitorSamples": 12847,
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
  "artifacts": 236,
  "payloadManifestSha256": "05E647CB637C405B6CA55993666ED15C27148C89ECF8D8A2F0C1BDD91DD8D2EF"
}
```

The packaged Dart gateway and actual OpcUaRepository execute all12 automatic
C1–C11/C13 cases. The owner's separate C12 Chrome checklist is bound by its
fresh token, exact reply and native MANUAL/idle/logged-out boundaries plus
forward typed ACK progress. Only the results above establish acceptance.
Chrome is visibly opened in a private window for the owner; no clicks, login,
mode changes or checklist answers are automated. The local URL is explicitly
given as http://127.0.0.1:8080/ inside SoftIndVM.

C1 discovers seven LIVE modules. C2/C3 correlate provider authentication
success/refusal without logging input secrets. C4 acknowledges AUTO/MANUAL.
C5 observes both CM completion counts. C6 edits station.number1→2→1 with
exact restoration and live owner revision advancement; the publisher's fixed
WriteRevision works without client substitution. C7 independently compares
four configuration pages/1,100 scalars/types. C8/C9 refuse foreign-root and
stale/duplicate requests without ACK changes. C10 refuses all39 kinds on the
read-only instance. C11 proves STALE→DOWN→LIVE and no replay across the owned
gateway restart. C13 ends logged-out MANUAL/idle before C12.

All P5 read-only gates run even after a failed writer/browser stage: configuration,
path/value/type equivalence, independent raw capture replay and native TASK
scan. Occupied value counts follow published extents/live counts, without
omitted paths or type/value coercion. A fixed simulation air input is restored
to its exact original DINT value. The finally path restores pinned genealogy,
five original documents,31 baseline cases, MANUAL/idle/logout, final checks,
preflight and baseline timing. No fault/TASK clears, clocks, controller power/
vendor-state changes or Echo hard kills are authorized. C11 stops only its
own gateway. Unknown active sessions still stop rollback.

The prior [automated record](AB_S5_GATEWAY_AUTOMATED_RUNTIME_C12_PENDING_2026-10-30.md)
retains its missing-witness outcome. All earlier failed attempts remain sealed.
No prior record is rewritten by this follow-up. The same pristine image and
package are used;526 product/test inputs are independently hash-checked against
the previous accepted automatic sources. Both v38 targets/read-backs/SDK audits,
fresh Capacity,2,357AB,777HMI/12skips,74root,analyzer,locked dependencies,
spec/contracts/strict consistency and gateway/installer gates retain their
exact bound proofs. Fresh session SDK/profile builds and scope/handshake tests
pass. The PLC correction changes exactly two generated WriteRevision
assignments to the existing owner; types/initial Tags are unchanged.

Stage S5 exits only if all current automatic/browser/read/scan/restoration
gates pass. O1 permits the stage-exit commit/push afterward. S6 then classifies
legacy consumers and migrates harnesses before host services, persistence/
events, canonical storage collapse, retirement and V2 activation. Physical/
CIP SecurityS7 remains deferred under O2. Local time-bounded commissioning
results are not production security or physical acceptance.

Payload:236 artifacts; manifest SHA-256:05E647CB637C405B6CA55993666ED15C27148C89ECF8D8A2F0C1BDD91DD8D2EF. Credentials,
ACD/BAK/L5X, compiled binaries and caches are excluded. Exact outcomes and
failed outputs are preserved, including any missing owner witness.
