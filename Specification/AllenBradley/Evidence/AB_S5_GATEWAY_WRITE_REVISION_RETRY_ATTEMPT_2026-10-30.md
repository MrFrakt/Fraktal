# S5 gateway automatic runtime — ATTEMPT; acceptance open

Recorded 2026-10-30T07:08:39.358323+00:00 under the
[sealed retry preparation](AB_S5_GATEWAY_WRITE_REVISION_PREPARATION_2026-10-30.md)
and standing O3. Target Echo601FC87B, L81E v38.011,127.0.0.1 slot0.
Candidate95E1C514…A586012; source979DD73C…105A162; manifestBBA48593…C847B6.
Fresh exact-image Capacity66%:2,077,924 used /1,067,804 available /3,145,728 Blocks. Two generated WriteRevision assignments now use the existing configuration owner; layouts and initial Tags are identical to S4b. Both v38 targets/read-backs and SDK audits pass.

## Results

```json
{
  "automaticSessionPassed": false,
  "stageComplete": false,
  "ownerBrowserC12Pending": true,
  "ownerBrowser": {},
  "genealogyRestored": true,
  "cases": 1,
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
        "paths": 5212,
        "independentComparison": true
      },
      "generic_acquisition": {
        "passed": true,
        "values": 5212,
        "modules": 7,
        "rawCaptureReplay": true
      },
      "native_scan": {
        "passed": true,
        "monitorSamples": 597,
        "finalSamples": 20,
        "cumulativeMaxUs": 7760,
        "overlaps": 0
      }
    },
    "rollbackGate": "E9 evaluated separately after guarded restore"
  },
  "scanMedianUs": 943.0,
  "scanCumulativeMaxUs": 7760,
  "overlaps": 0,
  "artifacts": 209,
  "payloadManifestSha256": "B9ECC990B436B91DF69E947E38AA66D72C6541D287BCEA8E40A0B48961E9C727"
}
```

The profile application drives actual OpcUaRepository commands over the
packaged Dart gateway. C1–C11/C13 are the automatic cases. C12 is the owner's
Chrome checklist, separately bound by the fresh witness token and native
MANUAL/idle/logged-out boundaries plus forward acknowledgement evidence.
Its actual pass or absence is recorded above. Command completion is proved
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

S5 exits only if all automatic, owner C12, native read/scan and rollback gates pass together. O1 permits the stage-exit commit/push after that condition; this record itself performs neither. S6 retirement/host services and
inactive V2 activation follow the S5 exit. Physical/CIP Security S7 is deferred
under O2. No credentials, ACD/BAK/L5X, compiled binaries or cache trees are
archived. Payload manifest SHA-256 B9ECC990B436B91DF69E947E38AA66D72C6541D287BCEA8E40A0B48961E9C727.
