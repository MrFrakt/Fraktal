# Fraktal/TIA line sets and bound mirrors (2026-10-16)

Measured continuation of the [shared owner milestone](TIA_LINE_OWNER_2026-10-16.md).
P1 remains in progress. These are isolated S7-1500 workbenches; normal generation
still refuses a partial Line profile under Core 1.5. The shipped press does not
publish a line until shifts, classes/capture and the complete profile are ready.

## Implementation

Owner LINE_CFG sets use the existing root catalog, workspace, typed validators,
JSON exchange and LOAD_DB set documents. The referencing root identifies a saved
snapshot; applying it changes the shared owner seen by all referencing roots.
The whole record is staged before commit. One framework helper advances the
revision once, regardless of record count, for both individual edits and set
loads. No new project call, line-set catalog or persistence document is needed.
Current-line export uses the existing immutable token/session cursor and consumes
no catalog slot. Station/model sets continue to exclude line records.

The complete line capacity is Core's 32 records, independently of the 12-field
per-module bound. The runtime fixture uses eight native types; a generator test
checks the 32-record shape. Read/write levels, capability revisions, enums,
native/declared bounds, root identity and shared readiness are enforced through
the existing validators. Stored imports may be validated while a peer is busy;
applying them still requires the shared readiness permit.

A MIRROR declaration binds a separate F_ image provider. The framework calls it
once per scan on the first referencing root after the restore barrier. The
provider offers an image, source error, timestamp and explicit clock quality;
it never receives live working storage. Only an available image with no provider
error enters whole-image validation. Mirror edits and line-set operations are
refused with the owner identified in LastRejectScope. Ordinary station/model
operations retain their existing path.

A successful mirror image is saved by the existing line LOAD_DB document. Virgin
mirrors wait for an observed image without reporting a media failure. Boot
installs defaults, then restores the last valid typed image/revision before the
roots run. Restore does not invent a source observation or synchronized time.
Freshness expiry raises one LOW/SYSTEM AUTO_RESET event, does not block Start and
closes automatically after a valid source heartbeat.

## Verification

| Gate | Result |
|---|---|
| Owner native04 software compile | 0 errors, 0 warnings |
| Owner canonical / FB-type / global DB read-back | 404 / 90 / 76 match |
| Owner live sets/current-export probe | 165 checks, 0 failures |
| Mirror native01 software compile | 0 errors, 0 warnings |
| Mirror canonical / FB-type / global DB read-back | 406 / 90 / 77 match |
| Mirror live source/restart probe, probe03 | 64 checks, 0 failures |
| Current owner / mirror frame replay | 169 / 170 sources byte-identical to compiled frames |
| Siemens engineering tools | 235 tests pass |
| Live generic HMI editor/repository, hmi05 | pass: save/edit/export/load/delete; both roots normalize to 2500 |
| Changed HMI test analysis | no issues |
| Cross-tree consistency and its tests | clean; 35 tests pass |
| Candidate V1 contracts and shipped press package | clean; 31 records, 22 enums |
| Shipped press source and native compile | 216 sources unchanged; 0 errors, 0 warnings |

The owner checks exercise catalog overflow, immutable current export during a
peer edit, whole-record revision increment, malformed/partial/last-field import
refusal, root isolation, per-value access and shared readiness. After verified
writes, working-only TaktMs is poisoned to 99999. A simulated power cycle observes
default 1000 before LOAD_DB restores 2600, its revision, four StationA line sets
and the peer's independent snapshot. Test sets are removed and the owner is
normalized to 2500 after verified persistence.

The mirror checks cover wrong identity, partial/invalid-last-record images,
changed values with the same revision, provider error/recovery, stale-event
deduplication and nonblocking behavior, read-only manifests, owner-directed
refusals, and a second offline simulated power cycle. LOAD_DB restores TaktMs3500
and revision24 after the same working-only poison; default1000 is observed first.
A same-revision heartbeat then renews freshness and closes the event.
The earlier cold run proves that no-image manifests conceal values and do not
report persistence failure. Its last assertion counted retained descriptions in
closed alarm slots; the final probe correctly checks non-CLOSED event state.

The HMI uses the existing production session/repository and ConfigEditor. It
saves an eight-record line snapshot, submits a rendered edit to2600, observes
the same value at both authenticated roots, exports nine JSON lines (header plus
eight records), reloads the snapshot, verifies2500 at both roots, deletes the
test snapshot and logs out. No production HMI component was changed for this
slice. The capture loads Segoe UI and Material Icons for readable test output;
this remains a component test, not complete shell navigation or visual acceptance.

Disk exhaustion interrupted an earlier mirror probe before any source-image
writes and seven temporary-copy tool tests. Test instances were stopped, space
recovered, the interrupted test file restored, and the complete tool/probe runs
repeated successfully. No saved engineering project or simulator storage was
deleted. The helper now tolerates an already-off test CPU on restart and can
release only a guarded test identity while preserving its saved storage.

## Scope and isolation

The source provider is synthetic and local to the fixture. P12 cross-controller
transport is not implemented or qualified. Timestamps/clock quality are explicit
test inputs; synchronized UTC, physical abrupt loss, download retention and
media endurance are not qualified. R3/R4/R5/R6 remain open.

Only FrkLineOwnerTest (.53) and FrkLineMirrorTest (.54), CPU1516 with all physical
adapter mappings zero, received these images. Their saved storage is preserved.
Both test registrations were powered off and released after final checks. The
owner's writes are durable, its test catalogs empty and both sessions logged out.
Original Fraktal stays RUN/TCPIP at .49 and 192.168.1.1 with unchanged mappings,
storage and certificate pin. No physical 1214C download or commissioning-output
gate change was made. The existing owner-whitelisted driver binary was reused.

## Evidence

The [archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_LINE_SETS_MIRROR_2026-10-16/)
contains public sources, native exports/read-back, compiler logs, live probes,
frame replays and source snapshots. Private F_AccessBenchProvision initializers
and their native exports are omitted with hash witnesses. Remaining FCs from
that source are preserved in explicit public derivatives. Engineering projects,
simulator storage, credentials, private database backups and generated caches
are excluded. Earlier sealed archives remain unchanged.

The archive seals 3119 payloads (71,121,571 bytes). SHA256SUMS.txt SHA-256 is
`066c5c01bdab48a537c3eaf370dc96432dbc046d6986a9cb80164fe8dbef1531`.
Public read-back replays owner403/90/76 and mirror405/90/77; each omits only its
private initializer from the full canonical block count. SiemensAgent's curated
notes/search index are updated with measured results and the remaining scope.
