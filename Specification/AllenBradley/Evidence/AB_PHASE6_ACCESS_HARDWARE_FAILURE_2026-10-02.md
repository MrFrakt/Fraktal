# Fraktal/AB Phase 6 access — failed press58 hardware gate

**Date:** 2026-10-02, America/Bogota. **Parent:** `850fcd0`.
**Authorization:** owner “done downloading build 58” authorizes the named
guarded verification fixtures on serial **7036B510**, **192.168.100.89**.
**Result:** manifest/read-only proof passes; access runtime gate **fails**.
The companion [JSON](AB_PHASE6_ACCESS_HARDWARE_FAILURE_2026-10-02.json)
preserves the manifest, both S3 samples, armed fixture failure and public audit.
Earlier build and limit records remain unchanged.

## Loaded contract and initial health

Controller identity is `1769-L24ER-QB1B/A LOGIX5324ER`, revision `33.14`.
The 79,992-byte manifest is coherent and every row matches the declaration:
ContentHash `D90151DAB7A1FC1B`, revision 14221649; Fields 544/768,
Localization 541/768, Rationalization 23/32 and WriteCapabilities 9/64.
The read took 175.597 ms. The owner-reported file is `C:\work\press58.L5X`,
SHA-256 `8BCFC3BE9C56544BCAD1AF5BDC6D41CD5824CEE6BDCCE07FDEFB80DDE3B7C4F4`.
Manifest agreement identifies the contract, not all executable logic; the
owner identifies the downloaded artifact. Gateway `/healthz` reports ready
and `plcReady=true`.

The initial S3 sample passes 6/6 at approximately 100 scans/second. Maximum
scan is 1,166 µs, overlap zero, major/minor bits zero. The access fixture's
three read-only rows pass, including the anonymous open policy and stopped
machine prerequisite, before it is armed.

## Access failure and subsequent observations

`fraktal_ab_phase6_execute.py 192.168.100.89 --expect-serial 7036B510
--access --execute-fixture` returns exit 1:

```text
controller login result did not settle
```

The first admin login exceeded the fixture's six-second result wait. Its
cleanup also attempted admin login while authentication was pending. The public
audit later records `std.audit.login` accepted for sequence 1 and a failed
second login attempt for sequence 2. Accepted authenticated policy/configuration
cleanup actions and logout follow. This proves that the original fixture
credential eventually authenticated; it does not turn the timed-out gate into
a pass. No exact total login duration was measured.

| Task observation | Before access | After access |
|---|---:|---:|
| Period | 10,000 µs | 10,000 µs |
| Maximum scan | 1,166 µs | **31,065 µs** |
| Overlap count | 0 | **606** |
| Major fault bits | 0 | 0 |
| Minor fault bits | 0 | **64** |

The next idle S3 sample still passes its six assertions: about 100 scans/second,
current last scans 581–787 µs and overlap steady at 606. Its overrun assertion
checks whether the counter changes during that sample, not whether it is zero.
Its current-time assertion does not reject a historical maximum above the
period. Thus “6/6” during idle is not evidence that hashing meets the task budget.
The measured whole-block hash workload exceeds this target's 10 ms scan period.
No controller fault or task counters were cleared.

## Cleanup and scope

The fixture records `access_cleanup_passed=false`: its admin-login and first
timeout-disable acknowledgement checks fail. All subsequent twelve gate
restorations, station.number, timeout and logout acknowledgements succeed.
Final readback is the original open policy, timeout 0, current level 0 and user
length 0, station.number 1. The parent restores baseline 950, mode 0 and run
style 0. All ten named fixture inputs are cleared. Application state ended
restored; historical timing/fault observations remain as shown above.

Other writing regressions stop at this failed runtime gate. No controller
download, mode/keyswitch administration, fault clear, clock/network/firmware
change or gateway startup was performed by the agent. Only the named fixture's
mailbox/policy/station-value writes and its restoration/disarm were exercised.
Local fixture credentials were consumed only by that harness and are absent
from this evidence.

The administrator is `phase6_admin`, level 4. No separate ENGINEER account
exists; ADMIN satisfies ENGINEER-level actions. The commissioning PIN is in
the local fixture file, with no shared default. The first chat response
incorrectly added the level number to the username; it was corrected against
the committed declaration before the hardware run.

The four-user limit remains committed; the press allocates only three rows
and its L5X remains byte-identical. The next implementation correction must
bound or optimize hash execution within the task budget and set a consistent
generic provider wait. It shall preserve the initial SHA plus all 256 further
hashes, immediate mailbox/private-request secret wipe, immutable pending
identity, cancellation and mailbox availability. Relaxing only the wait cannot
fix the measured scan overruns.

The v33 legacy zone-and-conduit bench remains write-enabled by the explicit
2026-09-29 decision. **Item 3 runtime acceptance, S9 and physical retention
remain owed.** No success claim is made for access, the remaining regressions
or the write-enabled security contract.
