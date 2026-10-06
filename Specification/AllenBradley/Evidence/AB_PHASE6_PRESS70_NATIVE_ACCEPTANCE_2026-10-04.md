# Press70 native acceptance - 2026-10-04

The owner confirms: "Yes, press70 downloaded successfully." This advances the
successful controller-fit baseline to press70, SHA-256
`A8CE4B44DA9F09BEE1DCDA1AAC2886F70954C9FA896562D4F3F14D510B9BCF04`.
Serial 7036B510, manifest 66C4A00ABDB4FCC3 / 6735008, firmware 33.014. The agent
performed no PLC download, clock write, gateway restart or disposable model creation.
The [machine record](AB_PHASE6_PRESS70_NATIVE_ACCEPTANCE_2026-10-04.json) retains
the failed run, superseding passes, guards and source hashes.

## Native checks and restoration

Eleven maintained native suites pass 159 rows: shelving 15, data 18, access 16,
capture 10, parity 25, Phase 1 7, Phase 2 6, Phase 3 8, corrected Phase 4 12,
Phase 5 25 and sets 17. Exact serial is checked immediately before every write;
fingerprint, native header and the four-code catalog are checked at fixture entry.
Both runs independently restore mode/style, policy/classes, session/timeout,
fixture inputs, station values, all four model banks and the M-101 catalog.
No major/minor fault or task overlap is observed. Maximum observed scan is
7,544 us against a 10,000 us task; this is not a CPU/free-memory measurement.

The first Phase 4 run fails 10/11 because its legacy fixture expected the air
Start report in MANUAL. The declaration intentionally scopes it to AUTO/HOME.
The fixture now derives conditions from the declaration and checks MANUAL,
HOME, AUTO and CHANGEOVER. No PLC logic changes. Two assertion mutants are
killed and the superseding 12/12 run passes; the failure is retained.
An initially stale gateway health snapshot is followed by a fresh subscription
and ready/plcReady proof, without relaxing freshness or restarting the gateway.
S3 read-only probe passes 6/6, with time synchronization observed false.

## Model and export proof

M-101 was created by the owner, is inactive, and has a schema-4 bank. Native
current-model export returns its four typed records through one immutable
snapshot and consumes no saved slots. Duplicate M-101 creation is refused
without changing catalog/configuration. The harness creates no new model.
A first private export helper failed before any write on a missing document
key; the corrected guarded helper passes 126 checks/writes, zero blocked.

The production OpcUaRepository reads M-101 through the running gateway and
returns BaselineWorkMs/IdealCycleMs 950, PressDwellMs 300, TransferSettleMs 200.
The running model remains M-100. This proves the shared selected-page repair
against the live binding; Chrome dialog acceptance remains a separate pending
owner check. No login or configuration mutation is used for this read.

## Offline and remaining scope

Full AB 1,571 tests pass; root 33 and consistency zero errors/warnings pass.
The unchanged deployed HMI previously passes 492 tests (seven expected skips),
analyzer/release and HTTPS exact-byte checks. Expanded-catalog boot/image tests
are recorded separately in [catalog preservation](AB_PHASE6_CATALOG_IMAGE_2026-10-04.md).
Capture all commissioned codes/banks again before a replacement download;
never seed a three-model image over M-101. Physical created-model retention,
credential/download migration, the new profile's full S9 live closure and
browser acceptance are not inferred. The earlier qualified S9 stays scoped to
press68. Line data and remaining port stages are still implementation work.
