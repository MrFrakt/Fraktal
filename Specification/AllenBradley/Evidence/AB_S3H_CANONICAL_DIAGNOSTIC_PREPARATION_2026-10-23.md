# S3h active-workload diagnostic preparation — 2026-10-23

**S3h is incomplete. No new controller-changing operation is authorized or
performed.** The [paced native retry](AB_S3H_CANONICAL_PACED_RETRY_ATTEMPT_2026-10-23.md)
has 39 exact independently replayed comparisons, then a failed first HELD
capture: all 17 complete windows cross a scan boundary. Genealogy rollback,
strict read-back, 31 regressions and final readiness pass. Its approval is
consumed. Baseline timing proxies do not establish active-workload timing.

This preparation adds only a separate timing wrapper around the unchanged
fixture/observer. It records monotonic start/end times for each acquisition
and generation read, retains the last attempted frames labelled unaccepted,
and reads eight existing TASK mirror scalars immediately after a failed proof,
before inherited fixture cleanup. The exact original exception and attempt
history propagate unchanged. No extra attempt, comparison tolerance, cache,
packet omission, task-period change or fixture vector is introduced. Four
sockets retain one pending read each; 47 packets and 100 polls/five seconds
remain. Timing calls and bounded in-memory rows add observer overhead inside
the proof; all frame serialization/compression/file I/O follow its completion.
Instrumentation can affect timing, so results are diagnostic observations.

Read-only post-failure scalars are FRK_Press_CanonicalTiming.Scan,
LastScanUs, MaxScanUs, OverlapCount and FRK_Press_HealthProbe.Samples,
TaskLastScanUs, TaskMaxScanUs, TaskOverlapCount. They exist in this exact image
and are the same mirrors used by the stage's existing timing tool. A failed
diagnostic read cannot mask or replace the original proof failure. The wrapper
requires current exact-image approval plus ReadTimingDiagnosticsAuthorized.
It delegates every tag write to the inherited fixed-vector fixture.

| Gate | Result |
|---|---|
| Wrapper tests | Four pass: current authority required; successful proof unchanged/no added TASK reads; original failure/100 polls preserved; diagnostic read error does not mask failure |
| Existing AB/root suites | 2,149 / 74 pass, reused by all 159 unchanged source hashes |
| Source/image | Native source E83B9A2C…567315 and ACD C6B42327…5D7D9DC remain byte-identical; no production source changes |
| Both v38 build/read-back/access | Exact-image sealed proofs reused; current prepared read-back/access pass |
| Capacity | Exact-image automatic 79%: 2,501,720 used / 644,008 available / 3,145,728 total Blocks; no accepted S3h calibration entry |
| Helper | Fresh one-shot workspace and untouched C6 copy; .NET helper build passes |
| Baseline | Fresh read-only preflight/final checks pass: Run/not faulted/Remote/scanning, MANUAL/idle/logout, five saved/live documents and policy equal |
| Current native diagnostic | Not executed; approval template false |

Read-only transport experiments are retained. At 4,000/4,002-byte negotiated
sizes the first fragment is 3,988/3,990 bytes. Echo refuses 8,000, 16,000 and
60,000-byte requests. A prototype that sends the next read immediately after
the preceding response passes framing/ownership tests and exact immutable
payload checks, but its 100-sample median is 8,161.95 µs (maximum 17,016.90),
so no reliable gain is established and it is not adopted. None of these
experiments writes a tag, changes mode, clears a fault or changes a clock.

Prepared ACD SHA-256:
`C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC`.
Generated source SHA-256:
`e83b9a2cd9593718026528ccdbd83a1ead6c8a52948fc6616006daffb0567315`.
The immutable genealogy original is never opened. ACD binaries and credentials
are not archived. Work folder: `C:/work/fraktal-ab-s3h-20261023/diagnostic_0b74f072e0d74c7c97531e07dec70898`.

Proposed current session: local Echo 601FC87B, 127.0.0.1 slot 0, v38.011;
guarded MANUAL normalization when needed, fresh backup, Program/download/Run
of the exact C6 image, five-document restore and the unchanged inherited 41
candidate checks with this read-only instrumentation. At the first failure
the fixture stops and rolls back, retaining timing/TASK/raw-frame diagnostics.
If all checks pass, existing idle/generic/sizes/scan steps still run. Then
hash-checked genealogy rollback, five-document restore, 31 baseline regressions,
MANUAL cleanup and final readiness/preflight checks. No new tag-write vector,
fault clear or clock change. AGENTS.md §3a requires current explicit approval
for this new session. It is a diagnostic run, not a promised acceptance retry.

Payload: [manifest](AB_S3H_CANONICAL_DIAGNOSTIC_PREPARATION_2026-10-23/manifest.json). The 33 earlier canonical seals and
8,072 artifacts remain unchanged. V2 remains inactive; no commit or push.

The first preparation audit stopped because it assumed every older manifest
had a report field. Older schemas make that field optional. The corrected
audit retains all artifact/hash checks, checks report hashes when present,
and verifies all 33 records. Both audit versions and exact logs are archived.
