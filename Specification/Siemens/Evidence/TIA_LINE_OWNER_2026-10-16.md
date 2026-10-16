# Shared line owner and LOAD_DB — 2026-10-16

P1 of the [remaining-features plan](../Reports/TIA_REMAINING_FEATURES_PLAN_2026-10-15.md)
now has a generated owner composition, ordinary root mailbox/manifest routing
and a shared LOAD_DB consumer. P1 and the optional Line profile remain open.
Core §1.5 requires line config and shifts together: ordinary generation refuses
a line declaration until the profile is complete. The isolated engineering
fixture explicitly selects `line_workbench=True`, recorded in its manifest.

## Implementation

One private owner is declared beside the two root Units, without another module,
parent, HAL or registry row. The first referencing root services the engine;
each root presents the same capabilities under its own scope and `Line/` items.
Writes use the existing typed config handler, access checks, readiness and audit
path. A shared readiness check includes every referencing root. Accepted edits
advance the owner revision and invalidate each referencing root's ConfigRev.
Station/model sets and exports continue to exclude line values.

The owner image is a new LOAD_DB document appended after existing documents, so
their keys and slots remain unchanged. Its key derives from LineId, independently
of which root hosts it. Boot installs typed defaults before the document restore
barrier; successful restore reapplies the image and revision. Both roots share
pending/failure/loss status and can acknowledge repair. Persistence reuses the
existing banked queue and read-back verification. Private storage and revision
cursors remain inaccessible through the external contract.

## Verification

| Gate | Result |
|---|---|
| Native software compile, native03 | 0 errors, 0 warnings |
| Canonical native code/type read-back | 402 blocks match |
| Native FB/type interfaces and access flags | 90 match |
| Native authored global DB interfaces and access flags | 75 match |
| Live guarded Web API/mailbox probe | 54 checks, 0 failures |
| Current workbench frame replay | 167 sources byte-identical to compiled frames |
| Siemens Python tools | 231 tests pass |
| Generic HMI config editor, live component test | passes; shared edit 2700, normalized 2500 |
| Changed HMI test/helper analysis | no issues |
| Source lint / cross-tree consistency / V1 candidate contracts | clean |
| Shipped press package | all 216 source files unchanged; metadata refreshed |

The live checks cover shared owner identity, both root scopes, capability kinds,
inactive-model exclusion, peer-root edits, shared revisions/ConfigRev, LREAL,
native/declared bounds, enum domains, malformed text, string width, capability
revision, model selectors and anonymous/operator access refusals. Starting the
peer Unit refuses a readiness-gated write from the idle root.

After verified LOAD_DB writes, the test deliberately changes only the working
TaktMs cache to 99999. Power-off/on of the same saved test CPU observes the typed
default 1000 before restore, then restores saved 2500 and revision 3 at both
roots. Application grants clear on restart. This distinguishes restoration from
accidentally retaining working memory. It does not qualify physical power loss,
full-download retention, media endurance or synchronized UTC.

The first full hardware compile and the test-user provisioning compile retain
two inherited warnings: no configured protection level and no display password.
These are isolated functional checks; R6 is open. The initial web login failed
until the disposable project's classic process-data user was assigned the
existing DPAPI credential. No secret appeared in a plan, argument or log.

The simulator SDK intermittently failed during status-process finalization.
The helper now disposes its interface explicitly. The HMI guard allows a bounded
retry of that read-only observation before sending a write; an unsuccessful
guard prevents the write. PLC writes are never retried after an uncertain result.

The generic `ConfigEditor`, production session, repository and mapper discover
eight line capabilities, authenticate each root, submit a rendered editor write,
observe 2700 at both roots, restore 2500 and log out. No production HMI component
was changed for this test. This qualifies the editor component; complete shell
navigation is not claimed here. Earlier test attempts found two test compilation
errors, a missed shell-tab tap and a missing peer read grant; the final test fixes
those setup issues. The captured image uses Flutter's test font and is not a
visual-acceptance record.

## Isolation and scope

Only `FrkLineOwnerTest`, CPU1516 at 169.254.212.53 / 172.31.254.53,
received this image. Physical adapter mappings stayed zero. The unchanged
approved `candidate_structure_examples` Openness executable was used. Original
`Fraktal` remained RUN/TCPIP at 169.254.212.49 and 192.168.1.1, with unchanged
mappings and certificate pin. The physical 1214C was not downloaded.
The test helper powered off/unregistered only its own registration at completion,
preserving its saved storage and the original Fraktal registration.

Named owner line sets/current-line export, mirror source binding and mirror
persistence, P2 shifts and complete press integration remain. The shipped press
publishes no partial Line profile. Cross-controller transport remains P12;
R3/R4/R5/R6 are not closed by this work.

## Evidence packaging

The [archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_LINE_OWNER_2026-10-16/)
holds compiler logs, native read-back, the guarded live records, public generated
frames and source snapshots. The private credential initializer and its native
exports are omitted, with hash-only witnesses. Engineering projects, simulator
storage, credentials, private KB backups and generated caches are excluded.
The current frame package replays separately from that private fixture overlay.
Public read-back replays 401 canonical blocks, all 90 FB/type interfaces and
all 75 global DB interfaces. The 402nd block is the private
`F_AccessBenchProvision` initializer; its successful measured comparison and
original file hashes remain as witnesses. The other FCs from its authored file
are preserved in a clearly named `.public.scl` derivative.
