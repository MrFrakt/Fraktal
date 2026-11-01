# S5 gateway automatic runtime — ATTEMPT; acceptance open

Recorded 2026-10-30T06:30:38.851763+00:00 under the
[sealed retry preparation](AB_S5_GATEWAY_LAUNCH_RETRY_PREPARATION_2026-10-30.md)
and standing O3. Target Echo601FC87B, L81E v38.011,127.0.0.1 slot0.
Candidate84EC495F…516FBAC; source22DD1C2E…DAEE06; manifestBBA48593…C847B6.
Exact image Capacity66% transfers by hash; no PLC code change.

## Diagnosis

C1–C4 passed. C5 was acknowledged but its completion count stayed zero. The
raw independent capture reports PartSlide READY, FaultActive false, and
diagnostic reason2003 (project.interlock.pressRequiresAirPressure). The cold
fixture had not established its simulated air input. No PLC/client defect is
concluded. The next fresh preparation will bind one fixed simulated input
setup and exact original restoration, retaining the interlock unchanged.

## Results

```json
{
  "automaticSessionPassed": false,
  "stageComplete": false,
  "ownerBrowserC12Pending": true,
  "genealogyRestored": true,
  "cases": 4,
  "baselineCases": 31,
  "candidateError": "RuntimeError: S5 automatic/read-only stages failed: gateway_qualification",
  "rollbackError": null,
  "nativeReadGates": {
    "passed": false,
    "readOnly": true,
    "gates": {
      "C1_C11_C13": {
        "passed": false,
        "error": "AssertionError: "
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
        "monitorSamples": 977,
        "finalSamples": 20,
        "cumulativeMaxUs": 7759,
        "overlaps": 0
      }
    },
    "rollbackGate": "E9 evaluated separately after guarded restore"
  },
  "scanMedianUs": 944.0,
  "scanCumulativeMaxUs": 7759,
  "overlaps": 0,
  "artifacts": 200,
  "payloadManifestSha256": "6A1D21C27EF16A299764D02BDD79B38D09A70BC5580E5B9401BF74EEB034CB9E"
}
```

The profile application drives actual OpcUaRepository commands over the
packaged Dart gateway. C1–C11/C13 are the automatic cases; C12 is the owner's
Chrome checklist and is explicitly not claimed. Command completion is proved
by the PLC acknowledgement/provider outcome and the changed native state or
retained CM timing count. Four configuration pages compare independently,
scalar-by-scalar and type-by-type, while the same access session is held.

The native record distinguishes mailbox consumption from authentication and
manifest/root/capability revision domains. The gateway uses canonical Symbols,
Templates and manifest, without a station declaration. Direct unsecured CIP
remains read-only. Instances echo:8080 and echo-view:8081 preserve O3's write
postures. These are local time-bounded commissioning processes; production
authentication/CIP Security and physical acceptance are not transferred.

Independent P5 stages record after any writer failure. The finally path uses a
hash-checked genealogy copy, the five original documents and31 baseline cases,
followed by final checks, preflight and timing. See exact result/error fields;
absence of a passing result is not acceptance. Raw failed runs are retained.
No fault/TASK clears, clock/controller-power/vendor-state changes or Echo kills
are authorized. C11 stops only its own temporary gateway process.

S5 remains open until C12; no S5 commit/push. S6 retirement/host services and
inactive V2 activation follow the S5 exit. Physical/CIP Security S7 is deferred
under O2. No credentials, ACD/BAK/L5X, compiled binaries or cache trees are
archived. Payload manifest SHA-256 6A1D21C27EF16A299764D02BDD79B38D09A70BC5580E5B9401BF74EEB034CB9E.
