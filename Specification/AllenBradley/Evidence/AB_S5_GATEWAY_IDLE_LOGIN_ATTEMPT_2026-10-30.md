# S5 idle-connection attempt: C2 client freshness failure

Recorded 2026-10-31T03:21:03.459872+00:00 under standing
O3 and [sealed preparation](AB_S5_GATEWAY_IDLE_CONNECTION_PREPARATION_2026-10-30.md),
with its [pre-execution seal correction](AB_S5_GATEWAY_IDLE_CONNECTION_SEAL_CORRECTION_2026-10-30.md).
Echo 601FC87B, L81E v38.011, 127.0.0.1 slot 0; unchanged ACD 95E1C514…A586012,
source 979DD73C…105A162, Capacity 66%.

Fresh backup, download, SDK audits, access checks, read-back and five-document
bootstrap passed. C1 connected and discovered all seven LIVE modules. Its
100-second pre-connect delay ran, but an old browser tab also reconnected;
therefore this run does not prove a continuously idle gateway during that delay.

C2 sent one LOGIN, received accepted acknowledgement 11, then the client lost
LIVE while awaiting the provider result. The fixture stopped there; C3–C11/C13,
the delayed movement and owner C12 did not run. No upstream CIP disconnect is
present in this gateway log. This is a failed qualification. The original
session result and failed outputs remain unchanged.

Cleanup initially refused because C2 failed before writing its normal
authentication proof. A separate read-only recovery matched the single logged,
accepted LOGIN sequence 11 to the native provider's completed result, exact
fixture user/level and sequence. Only then did the existing ownership guard
issue its one authorized legacy LOGOUT. No unknown operator session was cleared.
The owner also confirmed old HMI tabs closed before the next planned repeat.

Independent P5 gates passed: four pages / 1,100 scalar comparisons, exact
5,212-path equivalence at the current published counts, seven-module generic
acquisition and raw capture replay, exact AirOk restoration, cumulative TASK
maximum 7,759 microseconds and zero overlaps. Later rollback downloaded the
pinned genealogy copy, restored the five exact original documents, passed all
31 baseline cases, final checks, preflight and timing. Echo finished Run,
not faulted, scanning, MANUAL/idle, logged out and not restoring; saved/live
documents and original policy matched.

A bounded read-only follow-up on an isolated read-only gateway compared one
client with two clients plus targeted access reads. All 80 snapshots stayed
within the declared fast Good limit, with no read errors. This does not reproduce
the login transition and does not establish its cause.

```json
{
  "profile": {
    "passed": false,
    "failedCase": "C2",
    "error": "Bad state: Connection lost while waiting for the login result",
    "cases": [
      {
        "case": "C1",
        "passed": true,
        "live": true,
        "modules": [
          "Press",
          "Press.AirPressureMonitor",
          "Press.Door",
          "Press.PartPresentSensor",
          "Press.PartSlide",
          "Press.PressRam",
          "Press.TwoHand"
        ],
        "writeEnabled": true,
        "gatewayIdleBeforeConnectSeconds": 100
      }
    ],
    "ownerBrowserPending": true,
    "credentialValuesRecorded": false
  },
  "nativeGates": {
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
        "monitorSamples": 1628,
        "finalSamples": 20,
        "cumulativeMaxUs": 7759,
        "overlaps": 0
      }
    },
    "rollbackGate": "E9 evaluated separately after guarded restore"
  },
  "overlap": {
    "single": {
      "snapshots": 20,
      "errors": [],
      "maxRpcMs": 171.993,
      "maxEffectiveAgeMs": 136.106,
      "overFastGood": 0
    },
    "dual-with-targeted-access-reads": {
      "snapshots": 60,
      "errors": [],
      "maxRpcMs": 347.931,
      "maxEffectiveAgeMs": 157.58100000000002,
      "overFastGood": 0
    }
  },
  "restoration": {
    "passed": true,
    "genealogyRestored": true,
    "candidateAccepted": false,
    "originalFailedSessionPreserved": true,
    "ownerConnectionIssuesRemainUnderInvestigation": true,
    "faultClears": 0,
    "clockChanges": 0,
    "powerOperations": 0,
    "echoHardKills": 0,
    "utc": "2026-10-31T03:17:12.398357+00:00"
  }
}
```

The idle-socket correction retains its focused/full tests and earlier native
four-socket renewal proof; this run establishes no S5 exit. Next is an unchanged
write-scope repeat with existing opt-in frontend freshness/poll tracing. No
proof/freshness/retry limit is relaxed. No fault/TASK clears, clocks, controller
power/vendor-state edits or Echo hard kills. Only owned gateways stopped.
No credentials, ACD/L5X, compiled binaries or caches are archived. Payload
manifest SHA-256: 3106354DA636FDF1EB6C8E1C7FF2D4971A9548421DAB2889E7FFCB170396BFF9.
