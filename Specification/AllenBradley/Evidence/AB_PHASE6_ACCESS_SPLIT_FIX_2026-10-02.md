# Fraktal/AB Phase 6 — split login correction

**Date:** 2026-10-02, America/Bogota. **Parent:** `123e89a`.
**Result:** press61 failed its scan budget; press62 is prepared offline.
Owner Studio Verify/download, end-to-end timing, the full access matrix,
physical retention and S9 remain owed. See the [companion JSON](AB_PHASE6_ACCESS_SPLIT_FIX_2026-10-02.json).
Earlier evidence is unchanged.

## Observed failure

The owner reported approximately 12 seconds to login, a credential failure
message during that wait, then a successful session while the message remained.
This turn issued read-only diagnostics with the exact serial guard on
192.168.100.89, serial 7036B510. The contract was `6A002B2FAA2E431D`, revision
6946859, 79,992 bytes, access schema 2 and result budget 12,570 ms, consistent
with prepared press61. ContentHash alone cannot identify generated logic.
The public session was `phase6_admin`, level 4, not busy or failed. Health
recorded a historical maximum scan of **32,136 µs**, **771 task overlaps**,
major fault bits **0**, and minor fault bits **64**, against the 10 ms task.
The previous offline one-block-per-scan estimate did not hold on hardware.
No login, plant, policy, download, mode, clock, network or counter/fault-clear
operation was issued during this correction.

## Prepared change

The gateway computes the penultimate digest: SHA-256(salt + PIN), then 255
hashes of digest + salt. The PLC hashes the resulting preimage plus its own
registration salt once, compares all 32 bytes with its private stored hash,
and assigns only its private registered level. All **257 hashes**, salts and
stored hashes are retained unchanged. A submitted stored hash is rejected;
this is not pass-the-hash authentication. The gateway grants no access role.
The existing LOGIN ordinal carries an additive profile through IntValue;
profile 0 remains the native PIN path, profile 1 carries the preimage as
64 lowercase hex characters in TextValue. The preimage is a password-equivalent
credential, subject to the same transport protection and immediate byte wiping
as the PIN. Neither transported nor private sampled credential bytes survive
sampling. No preimage or PIN is added to evidence or audit entries.

Each block is split into ten phases with at most eight compression rounds in
a scan. The accelerated path therefore has **100 ms of nominal controller
scheduling**; actual timing remains unproved. Native PIN clients retain their
full bounded path, nominal 25.7 seconds and 35.7-second client budget. State V3
preserves prior fields and adds the derivation count and completed-result
sequence. The gateway verifies the live schema/count before credential writes.
The generic HMI waits for its own completed sequence, ignores prior failures
and sessions, and does not call an unsettled empty session a bad PIN.

The observed HMI development server is on port 5555. Port 9100 is Flutter
DevTools, not the operator HMI. The owner's Chrome URL/version was not supplied,
so the browser's loaded source is not established. The source and release Web
build are updated; the running development HMI needs owner hot restart/relaunch.

## Verification

- AB suite: **1,417 passed**. Root consistency: **0 errors, 0 warnings**;
  consistency suite: **33 passed**.
- HMI: **438 passed, 6 skipped**, analysis clean, release Web build exit 0.
- Mutations: **13/13** PLC/derivation defects and **8/8** HMI defects killed,
  each after a passing baseline. Includes lost prefix rounds, ignored private
  level, skipped comparison, stale result sequence, retained credential bytes,
  unbounded scan work and premature HMI rejection.
- Emitted real SHA code authenticates the protected bench admin fixture with
  one block. Wrong PIN, unknown user, malformed proof and the stored hash as
  proof fail; a failed attempt preserves the prior session. All levels come
  from private registrations. A 257-block native PIN login also passes the
  actual ST subset model against independent SHA-256 intermediates.
- Press and empty-user station template regenerate byte-identically; modules,
  task, AOIs and private registration tags are unchanged from press61.
- SDK compilation was attempted on press62. `OpenLogixProjectAsync` refused
  **No valid license**. Studio Verify on the owner's licensed desktop is the
  remaining compiler gate, followed by owner download.

## Owner deployment

Import/Verify/download **C:\work\press62.L5X** and restart the gateway from
this checkout. Hot-restart/relaunch the running Flutter HMI and refresh Chrome;
the release equivalent is **C:\work\press62_hmi_web**. No gateway was started
by the agent. Replying done after this named download authorizes the standing
guarded follow-up, including a single login timing check through the actual
gateway writer. Its prepared harness has not executed any controller writes.

Press62 L5X SHA-256:
`708D29CE0E7BEC5700DCC947938D3B641C8D1D64F504010BBD2888334F898E16`.
ContentHash **10AEDC3FFD6B5DC1**, ConfigRevision **1093340**, manifest **79,992 B**,
Fields **547/768**, Localization **544/768**. The template SHA-256 is
`E89319CBE6D5C03BFE8E050BDA99FEC0B60FF3FFC7F47DA3A39F2BE11325F22B`.
The controller access and write-enabled claims remain pending until their
hardware gates pass; the bench posture remains the recorded legacy zone and
conduit, with S9 still owed.
