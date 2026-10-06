# Fraktal/AB Phase 6 access — four-user registration limit

**Date:** 2026-10-02, America/Bogota. **Parent:** `7d6de81`.
**Owner instruction:** “you can reduce users space to 4”.
**Stage:** offline limit change and regeneration; the owner subsequently
reports build 58 downloaded. Guarded controller verification follows.
No controller writes, download or gateway startup were performed for this
change. The companion [JSON](AB_PHASE6_ACCESS_FOUR_USER_LIMIT_2026-10-02.json)
records artifacts, source hashes, checks and mutations. Earlier evidence is
unchanged, including the [memory correction](AB_PHASE6_ACCESS_MEMORY_FIX_2026-10-02.md).

`MAX_USERS` is now **4**. The declaration rejects a fifth registration before
reading the seed or producing an L5X. Private storage still follows the actual
registration count, with one inert row for an empty provider. Tests authenticate
the last row at four users, refuse five otherwise valid registrations, and
confirm the refused generation leaves no output.

The press already declares three users and press58 already allocates three
rows. Reducing the ceiling therefore introduces **no further memory reduction
or controller-code change**. Both regenerated artifacts are byte-identical:

| | Press | Empty-user template |
|---|---|---|
| Existing owner artifact | `C:\work\press58.L5X` | `C:\work\phase6_access_memory_template.L5X` |
| New reproduction | `C:\work\press58_four_users_reproduce.L5X` | `C:\work\phase6_access_four_users_template.L5X` |
| SHA-256 | `8BCFC3BE9C56544BCAD1AF5BDC6D41CD5824CEE6BDCCE07FDEFB80DDE3B7C4F4` | `E224D2E3C159D0BBEDF26D76957CFBCA2C5B07EA17C71A28E6A44DC0A8E561FD` |
| Registered users / allocated rows | 3 / 3 | 0 / 1 |
| ContentHash | `D90151DAB7A1FC1B` | `5A2A0526DC0FAA84` |
| ConfigRevision | 14221649 | 5908997 |
| Manifest bytes | 79,992 | 79,992 |

The press's private user table remains 988 declared bytes, and total access
storage remains 8,504 bytes. The empty-user template remains 7,848 access
bytes. No replacement owner artifact is necessary. The SDK's prior refusal
**No valid license** concerns the same byte-identical project; this change
does not claim a new target compilation result.

AB **1,404 tests pass**; root consistency **33 tests pass**;
`check_consistency` reports **0 errors, 0 warnings**. Three focused mutations
are killed by assertions, with zero test errors: raising the ceiling back to
sixteen, reserving all four rows regardless of registrations, and skipping the
last registered user. The prior 33 access/security mutations remain historical
evidence for the unchanged emitted controller code.

The bench admin account is **`phase6_admin`**, level 4; no separate ENGINEER
account is registered. Its generated commissioning PIN is available only in
the local fixture file `C:\work\fraktal_phase6_access_fixture.json`, not in
this evidence. ADMIN satisfies actions requiring ENGINEER level 3. There is
no shared default PIN, and commissioning accounts shall not be copied into
a deployed station.

The v33 legacy zone-and-conduit posture and explicit 2026-09-29 bench
write-enabled decision remain. This ceiling change adds no write kind.
Guarded controller access/task-cost proof, physical retention and **S9** remain
owed; the owner's subsequent `done` authorizes the named verification fixtures
on serial **7036B510** at **192.168.100.89**.
