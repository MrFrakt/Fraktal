# Fraktal/AB Phase 6 access — controller memory correction

**Date:** 2026-10-02, America/Bogota. **Parent:** `a90c6cc`.
**Stage:** regenerated and tested offline; owner Studio v33 memory-fit Verify,
download and guarded hardware verification pending. No controller writes,
download, gateway startup or mode changes were performed.
The [press56 build](AB_PHASE6_ACCESS_BUILD_2026-10-02.md) and
[press57 Boolean correction](AB_PHASE6_ACCESS_BOOLEAN_FIX_2026-10-02.md)
remain unchanged. The companion [JSON](AB_PHASE6_ACCESS_MEMORY_FIX_2026-10-02.json)
records generated artifacts, storage counts, scope checks, source hashes,
offline gates and mutations.

## Owner result and reduction

The owner reported this result after the press57 handoff:

```text
Error: Out of memory in the controller.
Complete - 1 error(s), 0 warning(s)
```

The initial provider allocated sixteen private user rows even though the press
declares three, represented every audit actor byte with a full DINT, and emitted
the same rotate/audit implementation repeatedly. The generator now pays that
work once, following Core §1.1 O4/O9:

- Private user arrays and lookup bounds derive from the registration count.
  An empty template has one inert row; the declaration still permits sixteen
  users. A corrupt Count exceeding the allocated rows fails authentication.
- `FRK_T_AccessAuditV2`, schema 2, replaces the byte-per-DINT actor array with
  eight packed DINTs per slot, four bytes per word in little-endian order.
  All 64 slots and all 32 actor bytes remain. Shorter names zero the unused
  bytes. The generic projection decodes V2 and refuses an unknown version.
- `AccessRotate32` owns native BTDT rotation; `AccessRecordAudit` owns ring
  writes and packing. Call arguments have private scratch storage separate
  from the pending login identity. Private layouts are versioned V2; public
  session/policy remains V1.
- SHA finalization loops over eight state words and their four bytes. Its
  64 round constants are one private, constant DINT table rather than CASE
  branches. Modulo addition still avoids signed overflow through 16-bit limbs.

| Declared access storage | press57 | press58 |
|---|---:|---:|
| Session/policy | 200 B | 200 B |
| Audit metadata and names | 9,740 B | 3,596 B |
| Private users | 5,252 B | 988 B |
| Private hash/audit scratch | 996 B | 1,036 B |
| Immutable sampled mailbox request | 2,428 B | 2,428 B |
| Private round constants | 0 B | 256 B |
| **Total** | **18,616 B** | **8,504 B** |

The press saves **10,112 bytes**. The empty-user template saves **10,768
bytes**, from 18,616 to 7,848 bytes. These figures count declared member
storage with four-byte UDT alignment; they exclude native instruction records,
symbol/type bookkeeping and compiled code. They are not a controller free-memory
measurement or proof of fit.

SHA plus rotate ST drops from **724 to 222 emitted lines** (209 SHA, 13 rotate).
The shared audit routine has 46 lines; mailbox ST drops from 1,594 to 1,426.
Source line counts are not compiled-code bytes. SDK opening of press58 again
fails at `OpenLogixProjectAsync` with **No valid license**, exit 1. The owner's
licensed Studio Verify remains the arbiter for fit and target compilation.

## Generated artifacts and contract

| | Press | Empty-user template |
|---|---|---|
| File | `C:\work\press58.L5X` | `C:\work\phase6_access_memory_template.L5X` |
| SHA-256 | `8BCFC3BE9C56544BCAD1AF5BDC6D41CD5824CEE6BDCCE07FDEFB80DDE3B7C4F4` | `E224D2E3C159D0BBEDF26D76957CFBCA2C5B07EA17C71A28E6A44DC0A8E561FD` |
| ContentHash | `D90151DAB7A1FC1B` | `5A2A0526DC0FAA84` |
| ConfigRevision | 14221649 | 5908997 |
| Fields | 544/768 | 358/768 |
| Localization | 541/768 | 452/768 |
| Manifest | 79,992 B | 79,992 B |

Both outputs reproduce byte-for-byte, including after the final source cleanup.
The packed actor field changes the contract hash; table capacities, row counts
and the 102,400-byte manifest budget remain. All AOIs, I/O modules, task settings
and other program routines compare equal to press57. Only mailbox/SHA routines
change and the two shared routines are added. ST/SFC/LD sequence graphs remain
equal. Access secrets/hashes, work, sampled request, native bit instruction and
round constants remain excluded from external access; public access data is
read-only. Fixture PINs are absent from generated artifacts and Python sources.

## Offline verification and remaining gates

- AB suite: **1,404 tests pass**. Root consistency suite: **33 tests pass**.
  `check_consistency`: **0 errors, 0 warnings**.
- All **33/33 mutations** are killed by test assertions, with zero mutant
  test errors. These retain the original credential, policy, native bypass,
  idle, actor and restore probes and add allocation bounds, final user row,
  packed high bytes, schema rejection, digest byte order, shared rotation,
  private constants and the Boolean-literal regression.
- Independent digest vectors, signed-intermediate arithmetic checks and one
  complete login execute the actual emitted SHA plus shared rotate routine.
  Full-width failed-attempt names, all 256 native byte values and shorter
  ring overwrites exercise the actual packed audit routine. Zero/one/three/
  sixteen registrations exercise allocation and final-row authentication.
- Authentication remains the TC3 salted initial hash plus 256 further hashes,
  one block per scan, constant full-digest comparison, immediate transported
  secret wipe, immutable pending identity, mailbox availability, logout
  cancellation and controller-authoritative mutation gates. No plaintext
  fixture credential is included in this evidence.

Import **`C:\work\press58.L5X`** in Studio 5000 v33 and Verify Controller. On a
clean Verify, download to serial **7036B510** at **192.168.100.89**, restart the
gateway and reply `done` for the guarded hardware loop. The final hash workload,
maximum scan time, overlap/faults and restored baseline still require hardware
proof. HMI source is unchanged; its prior 431-pass, six-skip, clean analysis and
successful Web build remain historical offline evidence.

The v33 legacy zone-and-conduit bench remains write-enabled by the explicit
2026-09-29 decision. This correction adds no new write kind to item 3's login
and policy surface. **S9 remains owed**; physical retention, model-set load,
data classes and shelving retain their existing pending gates.
