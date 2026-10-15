# TIA local users and root-policy retention - 2026-10-12

Generator 0.11 qualifies private LOCAL_RETAIN user records and root access policy
on the reference simulated S7-1500. User credentials and policy survive guarded
STOP/RUN and a power cycle; active and pending sessions do not. The existing
acknowledged mailbox remains the only remote mutation path. The separately wired
GRAPH/ST press compiles offline. This is a measured prototype continuation, not
release of the complete Core binding or physical press acceptance.

## Images and guards

Current downloaded project:
`%LOCALAPPDATA%/Fraktal/TiaStations/Access_Persistence_Runtime_20261012/FrkS12/FrkS12.ap20`.
Offline press:
`%LOCALAPPDATA%/Fraktal/TiaStations/Access_Persistence_Press_Offline_20261012/FrkS12/FrkS12.ap20`.
Both clone the preceding saved engineering projects, preserving certificates and
hardware identity. The runtime is the two-root, 24-module config/set/decision bench.
The physical1214C and press I/O were untouched.

Native target guards require owner Fraktal, CPU1516, TCPIP,169.254.212.49, and zero
physical adapter mappings. The additional192.168.1.1 virtual CPU interface remains
unchanged. The driver is the existing owner-whitelisted candidate_structure_examples,
SHA256 ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
No C# rebuild or whitelist change was needed. DPAPI credentials were read into
process environment and cleared by the existing wrapper; secrets were not logged.

## Ownership and behavior

One private root-policy image is allocated per deployed root, keyed by its identity;
nested Units have no policy images. The local table keeps Core MAX_USERS records of
username, salt, iterated PIN hash and level. Root sessions and worker caches remain
NonRetain. Images have schema and CRC protection; field encoding is binding-local
and independent of optimized-DB padding. Core supplies hash arithmetic, work factor,
record dimensions, enum domains and CRC arithmetic. Public Core types are unchanged.

The composition scan services storage and generated Unit frames restore policy,
enforce sessions and commit accepted policy edits before publishing their mailbox
acknowledgement. Session timeout edits also advance ConfigRev. Projects schedule
no extra persistence scan. FRK_AccessRegisterHash is a trusted hashed-record seam,
not a remote user editor. A committed table generation invalidates old grants and
fails pending attempts from the prior table. NONE remains a valid disabled account,
matching Core registration, and grants no authenticated session.

Restore accepts a complete valid image or reports loss. Bad schema/count/level,
duplicate names, hash/checksum damage and cleared commissioned headers reject the
user table whole. A historical commissioning marker prevents automatic reseeding.
Invalid user restore grants no login and emits std.error.accessRestoreLost.
Trusted engineering repair is explicit. A damaged root policy uses ADMIN thresholds
and blocks Start. ENGINEER acknowledgement persists that restrictive fallback;
later edits still require ADMIN. A peer root's policy remains unchanged. Users and
credentials never enter recipe documents or config sets.

ConfigPersist reports <root>.Access or <root>.AccessPolicy. The owning status
service combines typed-config and access loss before publication. Access owns its
precise loss alarms, so typed-config reporting neither replaces nor duplicates them.

## Qualification

| Gate | Result |
|---|---:|
| New user/policy persistence checks |419 passed |
| Existing named config sets |198 passed |
| Existing ordinary config |120 passed |
| Existing access/session checks |122 passed |
| Existing state/alarm checks |96 passed |
| Existing root decisions |36 passed |
| Total successful native assertions |991 |
| Runtime native compile |0 errors,0 warnings |
| Offline press native compile, two checkpoints |0 errors,0 warnings |
| Siemens Python tools |150 passed |
| Cross-tree consistency tests |35 passed |
| TIA lint / consistency |0 findings /0 errors,0 warnings |
| Live production gateway/repository/HMI workflow |1 passed |

Native storage readback verifies retained private table/image members, retained
commissioning/startup witnesses and NonRetain root session storage. Live reads of
private images and worker members return200; direct published policy writes return205.
The native CRC check vector123456789 produces CBF43926. Power and STOP/RUN restore
changed roles, distinct policies and distinct idle timeouts without provisioning
again. Corruption tests check precise alarms, unchanged peers, complete refusal and
explicit recovery. Repeated24-read batches prove loss publication stays stable.

The press has105 replayed sources. Native GRAPH AUTO19/HOME4 steps match the
source graph; the four LAD examples match161 networks/155 calls. MAIN keeps its
three composition calls, and GRAPH/ST integration remains at the owning Unit.
Optional ST/LAD twins are uninstantiated.

The unchanged generic HMI passes its live authenticated manual, fault/reset, typed
config and named-set workflow against the restored simulator through the production
gateway. Rendered screenshots, forest data and set JSON lines are retained in hmi_01.
The test logs both roots out; the temporary gateway is stopped without touching the
owner keeper. No HMI implementation change was required in this continuation.

## Findings and preserved interrupted runs

All trial logs are retained. The first final Start assertion ran in MANUAL mode,
where Start is intentionally refused; qualification now selects AUTO before asking
for Start release. A read-only simulator identity query failed once before a write;
the write was not sent and a fresh read found the same instance/keeper. Retries are
bounded to identity reads and never replay an uncertain mutation.

The simulator Run result can precede completion of the first scan. A nonretained
startup witness also resets on restart. The final fixture uses a retained monotonic
startup count after the complete forest scan and waits for its increment.

A real publication defect was found: typed-config status temporarily cleared loss
before a later access writer restored it every scan. Native reads caught the empty
LostPath. The final owning status service combines both sources instead of applying
an access patch afterward.

The access regression leaves a finite idle timeout. Previously startup reseeding
reset that stimulus; with real retention, the alarm suite's session expired during
read-only checks. normalize_bench.py explicitly restores timeout/mode/sessions and
restarts the test scratch before the next suite. A stale standalone state table in
an interrupted alarm run was also reset explicitly. The final96/36 checks pass.

The owner's VM rebooted after native qualification and before HMI connection.
The saved Fraktal image was restored without download by the guarded owner-image
script; addresses and physical mappings remain unchanged. The old keeper1748 ended
with that VM session. New keeper12728 uses the current work directory's stop file,
with no expiry or unregister cleanup; it is not a disposable test process.

## Scope and evidence

LOCAL_RETAIN is the qualified adapter. Load-memory/card-file and external media,
provider dispatch alternatives, data-class policy forms, changed-layout/full-download
retention and durable alarm storage remain separate gates. No physical motion or
process sequencing acceptance is claimed. CPU UTC synchronization remains unproven.

[Raw logs, native exports and source snapshots](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ACCESS_PERSISTENCE_2026-10-12/)
are frozen with repository-relative SHA256SUMS. Original relocation, GRAPH and
config-set archives remain unchanged. The source snapshot includes the exact Core
hash/provider/CRC authorities and generated applications used for this run.

The archive contains7,431 SHA-bound files,142,317,590 bytes. Every hash was verified
after freezing. The gateway had stopped before its log was copied; the owner keeper
remains active. Relocation verification still preserves11,166 original files and
the specification Siemens tree contains Markdown only.
