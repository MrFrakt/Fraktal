# Fraktal/AB Phase 6 access — press59 runtime correction

**Date:** 2026-10-02, America/Bogota. **Parent:** `14da3cc`.
**Result:** offline correction and account execution model pass; owner Studio
Verify/download and controller runtime proof remain pending. The companion
[JSON](AB_PHASE6_ACCESS_RUNTIME_FIX_2026-10-02.json) records artifacts, source
hashes, gates and mutation outcomes. Earlier evidence remains unchanged.

## Authorization and credential staging

The owner requested setting the admin PIN and trying login. The provisioning
command previously supplied generates a registration; it does not update the
running controller. The bench declaration now contains a fresh salt and hash
for the owner's chosen `phase6_admin` PIN, level 4. The protected local fixture
matches that registration. No PIN is included in committed source or evidence.
The real emitted SHA authenticates this account in the ST subset execution
model with all 257 hashes; that is not a Studio compile or controller result.

No controller write/download, gateway startup, mode administration, fault clear
or counter reset was performed during this correction. The last confirmed
loaded artifact remains press58; credential rotation is staged, not deployed.

## Bounded hash workload and matching client wait

Press58's whole-block-per-scan provider exceeded the 10 ms task period:
31,065 us maximum, 606 overlaps and a result outside the six-second wait. Its
[failed hardware record](AB_PHASE6_ACCESS_HARDWARE_FAILURE_2026-10-02.md) remains
the current runtime acceptance result.

Press59 uses a private phase/cursor. A block takes one input scan, eight
compression scans and one output scan. A compression chunk performs eight
rounds and expands at most the eight words it consumes. CASE phases do not
fall through; each mailbox scan invokes at most one chunk. All 257 blocks
remain mandatory; a digest is consumed only after its completion flag.
Cursor corruption fails closed without an array fault.

The sampling scan clears the transported/private-request secrets and packed
input byte buffer. Private word/compression state remains only as transient
work across the block; completion, logout cancellation and Run entry clear
the arrays, cursor and native bit scratch. Pending identity stays immutable,
other mailbox requests still run, and completion does not replace their ACK.

`FRK_T_AccessStateV2` appends read-only `LoginTimeoutMs`. Its declaration-derived
value is `257 * 10 * task_period_ms + 10000`. On this bench that means 25.70
seconds of nominal scheduling and a 35.70-second client wait. The generic HMI
uses a provider value in 1..600000 ms; older/synchronous providers retain the
six-second default. The AB declaration refuses a budget beyond this limit.
`FRK_T_AccessWorkV3` holds the four private phase fields. These scheduling
bounds are not measured controller execution costs; new hardware proof must
establish no added overlap, scan budget and actual login duration.

## Artifacts and validation

| Artifact | ContentHash | Revision | SHA-256 |
|---|---|---:|---|
| `C:\work\press59.L5X` | `6A002B2FAA2E431D` | 6946859 | `62AEDB124A4A2933684E61367C352869BB488B88FBCCD69F785FF079658AEE0E` |
| `C:\work\phase6_access_runtime_template.L5X` | `A1B96FEDE7A52F3E` | 10598767 | `BBA9846389237889AEEE1AE56E9ADFA5B4840086A8345531C768BB0A3A2FE6AC` |

Both reproduce byte-for-byte. Manifest capacity remains 79,992 bytes. The
press has Fields 545/768 and Localization 542/768; template 359/768 and
453/768. The four-user ceiling, three actual press rows and one inert template
row remain. Declared access storage is 8,524 bytes for the press and 7,868 for
the template, 20 bytes above press58's correction. This excludes native
instruction/type/symbol overhead and compiled code; Studio must establish fit.
Modules, tasks and AOIs are unchanged. Changed routines are Main startup,
HmiMailbox and AccessSha256; shared rotate/audit routines are unchanged.

- AB suite: **1408 tests pass**; root consistency **33 tests pass**, zero
  errors/warnings. Two older test callers were updated for the task-dependent
  state layout after an initial full-run signature failure.
- HMI: **433 pass, 6 skipped**; analysis clean; release Web built at
  `C:\work\press59_hmi_web`, not deployed. Long-provider and short-deadline
  tests check that the provider wait is actually consumed.
- PLC mutation probes: **42/42 killed**. HMI: **3/3 killed**. The real complete
  login test checks every scan's invocation count and all 2570 compression
  phase counts, alongside hashlib/FIPS vectors and signed overflow checks.
- SDK `OpenLogixProjectAsync(C:\work\press59.L5X)` refused
  **`OperationFailedException: No valid license`**, process exit 3762504530.
  This is a blocked compile gate, not a successful Verify. The owner must
  import and Verify in licensed Studio 5000 v33, then download and restart
  the gateway with the updated generic HMI before guarded controller proof.

Item 3 runtime acceptance, remaining regressions, physical retention and the
write-enabled S9 claim remain owed. The v33 legacy zone-and-conduit bench
posture and existing role/policy surface are unchanged.
