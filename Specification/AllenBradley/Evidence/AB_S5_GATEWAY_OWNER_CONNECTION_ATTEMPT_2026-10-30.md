# S5 owner browser attempt: connection defects; genealogy restored

Recorded 2026-10-31T02:56:29.346526+00:00 under
[sealed preparation](AB_S5_GATEWAY_LONG_WINDOW_PREPARATION_2026-10-30.md)
and standing O3. Echo 601FC87B, L81E v38.011, 127.0.0.1 slot 0.
Candidate ACD 95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012;
unchanged image Capacity 66%.

The owner reported LIVE/login/mode/logout checks passed, then reported a
one-to-two-second disconnect on manual movement and an initial connection
error followed by successful connection. The original words are retained.
The gateway log contains real upstream `CIP connection closed` errors, so
these observations are unresolved defects, not a qualified S5 pass.

The browser witness rejected its final native boundary because the PLC still
reported an active operator login. Ownership cleanup and rollback also refused
that login. No active-session guard was bypassed. The original session result
and failed logs remain unchanged. After reopening only the owned gateway, the
owner replied **"MANUAL and logged out now"**. Fresh guards confirmed level 0,
MANUAL and idle. Only then did the continuation restore the pinned genealogy
copy, the five original documents, 31 baseline cases, final checks, preflight
and timing. The controller finished Run, not faulted, scanning, MANUAL/idle,
logged out, not restoring, with saved documents equal to live.

The first continuation precheck incorrectly included the candidate ACD that
the prior SDK Download/Save had modified. It stopped before controller access.
The second continuation excludes that unused candidate ACD; restoration still
hash-checks the protected original genealogy image and uses a copy. Its failed
precheck record and both continuation sources are retained separately.

```json
{
  "qualifiedSessionPassed": false,
  "automaticCasesPassed": true,
  "automaticCases": 12,
  "ownerBasicChecksReported": {
    "liveOverview": true,
    "login": true,
    "modeAcknowledged": true,
    "logout": true
  },
  "browserNativeBoundaryPassed": false,
  "reportedIssues": [
    "Manual movement briefly disconnects for 1\u20132 seconds, then reconnects.",
    "Connect displays an error for a few seconds before succeeding."
  ],
  "initialRollbackBlockedByActiveLogin": true,
  "genealogyRestoredAfterOwnerLogout": true,
  "baselineCases": 31,
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
    "utc": "2026-10-31T02:54:12.069715+00:00"
  },
  "originalFailureRetained": true,
  "payloadManifestSha256": "EF0D3994706DCF9A6E20DE3573151D5BC67F9FA78F86A5ECE964F1A63516B57C"
}
```

The 12 automated cases and independent read/scan results are retained at their
recorded scope. The failed browser/session result is not promoted by later
cleanup. S5 remains open for connection fixes and fresh exact-source native/
browser qualification. No fault/TASK clears, clock changes, controller power/
vendor-state edits or Echo hard kills occurred. Only owned gateways stopped.
No credentials, ACD/L5X, binaries or caches are archived.
