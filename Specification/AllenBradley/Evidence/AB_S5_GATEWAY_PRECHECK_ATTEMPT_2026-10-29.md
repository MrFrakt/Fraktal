# S5 native preparation attempt — backup only; genealogy unchanged

Captured 2026-10-30T05:21:58.250650+00:00 under the
standing O3 authorization, bound to the [sealed preparation](AB_S5_GATEWAY_PREPARATION_RETRY_2026-10-29.md).

Initial identity/service/listener, MANUAL/idle/logout, preflight, fresh backup,
SDK Save As log audit and backup access audit passed. The deploy command then
stopped on missing `canonical_prepared_compare.json` at Program.cs:106.
That check precedes `deploy_attempt.json`, project open, Program, download and
Run. No download marker exists and no candidate case ran. The approved image
84EC495F…516FBAC was never opened by the deployment SDK.

The missing read-back gate was not weakened. The correction copies/compares the
actual accepted readback and derives static SDK input requirements before the
first controller call; it uses a new workspace/backup/seal under O3.

Post-attempt final checks and preflight verify-only pass: genealogy manifest
6DEC4C1DC2F7F78A, Run/not faulted/scanning, MANUAL/idle/logged out, not restoring,
the five saved documents equal live and original policy unchanged. Rollback was
not required; the session result's genealogyRestored=false means no restore
download occurred. The pinned original genealogy ACD retains D67561C4…ED4084.
No fault/TASK clears, clock/power/vendor operations, Echo kills or dumps.

S5 C1–C13 remain unproved. No commit/push. 107 artifacts,
payload_hashes.json SHA-256 57C89ED28D7F305A4787386974A46CD4CDA3C107C0A238A7FFDE67200B0FE14D. No credentials, ACD/BAK/L5X, compiled
binaries or cache directories are archived.
