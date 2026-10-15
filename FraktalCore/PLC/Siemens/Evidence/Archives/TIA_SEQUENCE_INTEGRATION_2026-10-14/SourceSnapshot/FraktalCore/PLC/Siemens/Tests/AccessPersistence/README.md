# Retained local users and root access policy

Generator 0.11 services private LOCAL_RETAIN storage from the existing forest scan.
Projects add no cyclic persistence call. Each actual root has one keyed policy
image; nested Units allocate no policy images. The shared local provider retains
the Core MAX_USERS table of usernames, salts and iterated SHA-256 hashes. Neither
sessions, pending authentication work nor transported plaintext secrets survive
restart. Published policy remains readonly; edits use the existing root mailbox
and ACCESS_POLICY gate. Session timeout edits also advance ConfigRev.

The binding-local images are versioned and checksummed. Commissioning markers
distinguish virgin stores from commissioned images with cleared headers. CRC-32 arithmetic derives
from Core F_Crc32; canonical field encoding avoids optimized-DB padding and native
pointer layouts. Restore validates the complete user table and each complete root
policy, including counts, duplicate names, levels, timeout bounds and owner key.
Salt/hash compatibility and work factor still derive from the Core authorities.
The images are not TwinCAT ST_AccessImageV1 byte documents.

An invalid user image makes the provider unavailable to every root and announces
std.error.accessRestoreLost. It is not automatically overwritten or reseeded.
Recovery needs trusted engineering provisioning. FRK_AccessRegisterHash accepts
an already hashed ST_UserRecord at the composition/provider seam, never through
the HMI. A successful replacement or addition commits a new generation; managers
revoke existing sessions and refuse an in-flight attempt from the previous table.
Invalid registration changes neither table nor generation. NONE is a valid stored
level, matching Core registration, and grants no authenticated session.

A damaged policy never restores the open default. Its root uses ADMIN thresholds
and blocks Start, while another root retains its independent policy. An explicit
ENGINEER-or-higher ACK_CONFIG_RESTORE accepts and persists that restrictive
fallback, after which ordinary gated edits can restore the intended thresholds.
Acknowledgement does not reopen actions. Loss reaches the existing alarm surface
and ConfigPersist when the root declares typed config: LostPath distinguishes
<root>.Access from <root>.AccessPolicy. Neither source adds credential fields to
recipes or config sets. A virgin image uses the deliberate composition policy or
the shipped fully open default.

The fixture wraps the existing two-root, 24-module config/set/decision bench. Its
startup provisioner runs only for a virgin image. A retained ProvisionCount proves
that STOP/RUN and power cycles do not reseed it. Engineering-only test controls
change an operator role, inject invalid images and explicitly repair the known
hashed table. Those controls and their private scratch record are absent from
production generation. Main continues to call setup, the forest, and observation.

Use Tests/Access/with_credentials.ps1 with make_fixture.py and probe_web.py.
normalize_bench.py explicitly restores the shared bench timeout, mode and sessions
between regressions. The access test leaves its finite timeout retained; a restart
no longer resets that test stimulus. The probe guards every mutation and restart against the exact Fraktal CPU1516
TCPIP instance at 169.254.212.49 with zero physical adapter mappings. It preserves
the registration and keeper, and restores the bench policy and logged-out sessions.

Current simulator project:
%LOCALAPPDATA%\Fraktal\TiaStations\Access_Persistence_Runtime_20261012\FrkS12\FrkS12.ap20.
The wired GRAPH/ST press remains in a separate offline compiled project.
This LOCAL_RETAIN qualification does not claim load-memory/card-file media,
full-download or changed-layout retention, external access providers, durable
alarm storage, or physical press acceptance. The production adapter's protected
symbols are checked through native export and live read/write refusal probes.

See [dated evidence](../../../../../Specification/Siemens/Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md).
