# S4b root-sample diagnostic attempt — 2026-10-26

**The refusal is diagnosed: the first snapshot's oldest fast row was 2,065.752 ms
old, above the unchanged 1,000 ms acceptance limit. Genealogy restoration and
31/31 baseline checks are verified after one unchanged baseline retry.**
S4b qualification failed; native and desktop acceptance remain open.

The owner answered “Approve guarded S4b root diagnostic session” to
`call_0c97c2f8c5c84620bbb108165c7177cd:0`, authorizing the
[sealed preparation](AB_S4B_ROOT_DIAGNOSTIC_PREPARATION_2026-10-26.md).
The original approval included rollback cleanup and the 31 baseline vectors.
The runner's first failure record is retained unchanged; its incomplete cleanup
was finished within that original scope, without another download or new write
vectors. That scope is now complete and the approval is consumed.

## Native finding

Fresh guards/backup, exact-image download/Run, SDK, L5X read-back and access
audits pass on Echo 601FC87B (1756-L81E v38.011, 127.0.0.1 slot 0).
ACD `7D75E86E9315E0383EDE0C4588A6D327848F54C8A6DBB26B987CCB36DEF056BF`;
source `C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F`;
offline Capacity remains 65% (2,066,100 /3,145,728 Blocks).

The corrected Template and manifest discovery pass. The retained rejected
snapshot has the correct Press root identity and **976 Good values, zero Bad
and zero Uncertain**. Snapshot processing took **2,495.609 ms**; the oldest
fast row, Press/Status, was **2,065.752 ms** old at delivery. That row's accepted
coherence window was 1,909 us; the largest returned window was 6,387 us, below
the declared 10,000 us period. This is an age failure after sequential
acquisition, not a missing root or an identity mismatch. These samples are not
accepted qualification samples. The initial 1,000 ms refusal is preserved.

Readiness was never set, **0/41 candidate cases** ran, and no configuration
pages were read. Candidate equivalence, generic acquisition, candidate scan
and desktop rendering were not reached.

## Rollback and failed baseline

Pinned genealogy was downloaded from a hash-checked copy; the original remains
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`.
The SDK and external-access audits and original five-document restoration pass.
The first baseline run passed **22 cases**, then SFC adopted-fault setup timed
out waiting for HOME readiness (`step=0, error=0`). Its finally path left
MANUAL/policy restoration incomplete, and the original runner correctly records
rollback verification as false. The initial final-state check also failed and
is preserved; that state was idle, logged out and scanning, with documents equal.

Residual cleanup restored only fixture policy gate 10 and MANUAL through the
already approved LOGIN/SET_ACCESS_LEVEL/SET_MODE/LOGOUT scope. Final checks and
preflight then pass. One unchanged repeat of the original 31 baseline cases
passed **31/31**, restored policy, and was followed by MANUAL normalization,
final checks, preflight equality and baseline timing. No readiness condition or
fixture assertion was weakened. The first baseline timeout's cause is not
established by this successful retry.

The final controller is Run, not faulted, scanning, MANUAL/idle, logged out,
not restoring, with the original policy and all five saved/live documents equal.
No dumps, fault clears, clock changes, power/vendor-state operations or Echo
hard kills. No further controller-changing session is authorized.

## Offline investigation and next step

An unchanged-source recorded-byte replay with an immediate fake transport took
1,697.892 ms for its first acquisition and 1,596.195 ms for its second:
1,986 requests, 596 groups across the two reads, and 976 sampled values. This
reproduces substantial client cost without network delay; it is a profiling
observation, not a native timing guarantee or proof of one specific hotspot.
Inspect repeated path/count lookups and scheduling, preserve exact values/types
and all coherence/freshness limits, then rerun offline gates before preparing
another approved native qualification. No production correction has been made
at this seal. The bound sources remain unchanged except the SDK-saved working
ACD. Preparation gates remain 2,336 AB /74 root /637 Flutter (12 skipped).

S4b desktop, S5-S7 and S3 physical I/O acceptance remain open. V2/Part III are
inactive. Nothing is committed or pushed; no credentials or ACD binaries are
archived.
