# S5 gateway automatic runtime — ATTEMPT; acceptance open

Recorded 2026-10-30T07:16:43.214770+00:00 under the
[sealed retry preparation](AB_S5_GATEWAY_LIVE_ACTION_PREPARATION_2026-10-30.md)
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
  "genealogyRestored": false,
  "cases": 0,
  "baselineCases": 0,
  "candidateError": "PermissionError: [Errno 13] Permission denied: 'C:\\\\work\\\\fraktal-ab-s5-20261029\\\\session_06\\\\host_cpu_ready.json'",
  "rollbackError": null,
  "nativeReadGates": {},
  "scanMedianUs": null,
  "scanCumulativeMaxUs": null,
  "overlaps": null,
  "artifacts": 117,
  "payloadManifestSha256": "4E580F47CDA401AE7C333F4D33736F561C08F8BB62FEEEB36AD06AE7545EFC90"
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
archived. Payload manifest SHA-256 4E580F47CDA401AE7C333F4D33736F561C08F8BB62FEEEB36AD06AE7545EFC90.
