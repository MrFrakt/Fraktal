# Fraktal/AB Phase 6 access — login performance correction

**Date:** 2026-10-02, America/Bogota. **Parent:** `30b8bd8`.
**Result:** press59 admin login measured successfully; press61 optimized offline
and ready for owner Studio Verify/download. Full item 3 acceptance, scan-budget
proof for the new implementation, physical retention and S9 remain owed.
The companion [JSON](AB_PHASE6_ACCESS_PERFORMANCE_FIX_2026-10-02.json) contains
the guarded measurement, artifacts, source hashes, gates and mutation results.
Earlier evidence remains unchanged.

## Loaded controller and the reported failure

The owner reported an early HMI failure followed by eventual login after retries.
Serial-guarded reads at 192.168.100.89 confirmed serial 7036B510, press59's
published contract, access schema 2 and LoginTimeoutMs 35700. The PLC had a
successful admin LOGIN audit followed by busy refusals for later retries.

The previously explicit request to set the chosen admin PIN and try login
authorized this login-only test. The complete manifest matched the parent
declaration and the serial was checked again immediately before LOGIN.
The protected local fixture matched the unchanged private registration.
One native mailbox LOGIN was consumed in **112.940 ms** and authenticated
`phase6_admin` at level 4 in **25,776.784 ms**. Original and final public sessions
were the same admin; no policy, timeout, station value, mode or plant input was
written. Task overlaps stayed **0**, historical maximum scan stayed **6,388 us**,
and major/minor fault bits stayed **0**. No counters or faults were cleared.
This is a successful login measurement, not the full access regression matrix.

A separate read-only connection to the already running gateway, without a
token, confirmed that it publishes the 35,700 ms provider wait and the admin
session. Its snapshot took 287.602 ms and a correctly indexed/revisioned result
read took 0.869 ms. The running HMI URL/version was not available, so an old
client's fixed wait is an inference, not a verified deployment fact.

## Prepared runtime and generic HMI

Press61 replaces native bit-distribution and per-round rotate subroutine calls
with inline masked DINT arithmetic. High limbs are summed as signed 16-bit
values. Low-bit masks make every divide exact and every intermediate remains
within DINT; the execution model checks both properties, including every rotate
amount, single-bit/edge/random vectors and complete SHA/hash chaining.
[Rockwell division documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/37-00/contents-ditamap/instruction-set/compute-math-instructions/divide--div-.html)
supports the ST division operator; its
[conversion rules](https://www.rockwellautomation.com/en-be/docs/studio-5000-logix-designer/37-01/contents-ditamap/instruction-set/data-conversions.html)
distinguish integer operands from mixed REAL conversion. This implementation
uses only DINT operands and exact quotients.

Each task scan runs at most one complete block; all **257 hashes** and the
salted registrations remain unchanged. A private spent-block flag also refuses
a new LOGIN on the scan that finishes the previous one, preventing two blocks
in a scan under retries. The byte/word buffers are wiped within each block;
cancellation and Run entry wipe the private credential work. Corrupt remaining
counts fail closed. Private work is version 4; unused native bit scratch and
the rotate routine are removed. Declared access storage is **8,504 bytes** for
the press and **7,848** for the template, 20 fewer than press59, excluding
compiled code and native/type/symbol overhead. Modules, tasks and AOIs are
unchanged. Four users remain the ceiling, with three actual press rows.

The nominal scheduling bound is **257 task periods**, or **2.57 seconds** on
this 10 ms bench, with a **12.57-second** client budget. These are scheduling
values, not measured press61 CPU costs. The earlier press58 whole-block failure
is not overwritten: the arithmetic implementation has changed, and this new
block must still be measured below the task period without added overlaps.

The generic HMI uses a monotonic deadline, bounds stalled result reads, and
requires every requested access field before using the outcome. An unconsumed
login, timeout or lost link follows the existing localized unavailable branch;
only a completed negative provider result reports incorrect credentials.
No AB-specific screen or new operator-facing key was added.

## Artifacts and gates

| Artifact | ContentHash | Revision | SHA-256 |
|---|---|---:|---|
| `C:\work\press61.L5X` | `6A002B2FAA2E431D` | 6946859 | `7F5EF128319DA43DF9C0121B0FC614D13360EB0143A73B43EC29D9AFC61FAD27` |
| `C:\work\phase6_access_fast_final_template.L5X` | `A1B96FEDE7A52F3E` | 10598767 | `FCEBC8B23FFD08233ABA6F5C53F363C70714B276CA87EEDE8BD8EF94E8C66DAF` |

Both reproduce byte-for-byte. Manifest capacity remains 79,992 bytes; press
Fields 545/768, Localization 542/768. ContentHash remains identical to press59
because logic, private storage and initial provider values are outside that
hash. Identify this artifact by file SHA-256 and its 12,570 ms provider value.

- **1410 AB tests pass**, native process exit 0; root consistency zero errors
  and warnings and **33 tests pass**.
- **436 HMI tests pass, 6 skipped**; analysis clean. Release Web built with
  native exit 0 at `C:\work\press61_hmi_web`; deployment is pending.
- **18/18 PLC mutations killed**, **7/7 HMI mutations killed** in isolated
  memory/copies, without modifying tracked source for the probes.
- Real emitted compression authenticates the protected bench admin registration
  in the ST subset model, with every one of the 257 digests checked separately
  against the independent hashlib chain in the complete login test. This is
  not a Studio compile or controller result.
- SDK `OpenLogixProjectAsync(C:\work\press61.L5X)` refused
  **OperationFailedException: No valid license**, native exit **3762504530**.
  The compile gate is blocked, not passed. Licensed owner Studio Verify and
  download remain necessary, followed by gateway/HMI restart and guarded proof.

The v33 legacy zone-and-conduit posture and the existing write-enabled decision
remain unchanged. No gateway was started and no PLC was downloaded by the agent.
