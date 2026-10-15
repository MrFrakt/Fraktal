# Named station/model config sets - 2026-10-12

Generator 0.10 implements an optional bounded LOCAL_RETAIN set store over the
existing typed config owners. Save/list/load/delete and JSON-lines export/import
use the generic HMI contract. The two-root simulator bench passes 587 native
checks. The wired press application compiles offline with zero errors/warnings
and retains its GRAPH/ST composition. This is prototype evidence, not a release
or a physical process qualification.

## Qualified images and boundaries

Owner: Fraktal, CPU1516 V3.0, PLCSIM Advanced7, RUN/TCPIP, virtual addresses
169.254.212.49 and 192.168.1.1. All three physical interface mappings are zero.
The owner registration and persistent keeper PID1748 remain intact.

Current simulator project is
%LOCALAPPDATA%\Fraktal\TiaStations\Config_Sets_Runtime_20261012\FrkS12\FrkS12.ap20.
The press is a separate compiled offline project:
Config_Sets_Press_Offline_20261012/FrkS12/FrkS12.ap20. It was not downloaded.
The exact previously owner-whitelisted grouped driver was reused, with no rebuild:
TiaCli/bin/candidate_structure_examples/Fraktal.Tia.Cli.exe,
SHA256 ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.
Every download and native mutation checked the isolated virtual target. TLS trust
and the existing certificate pin were preserved. Credentials came from DPAPI
through environment variables and do not appear in commands or evidence.

## Implementation and sizing

Named sets are opt-in. Capacity is bounded by Core MAX_CONFIG_SETS; record windows
use the largest consumed config kind in an actual root, bounded by
MAX_SET_RECORDS. The bench has two roots, four slots per root and 24 record slots
per set. Its station projection has nine records and its model projection 24.
Children own typed staging and no set catalogs or transfer buffers. The press
has four station slots and no model catalog or line config provider.

The same config definitions own capability identity, revision, type, bounds and
read/write/readiness gates. FRK_ConfigDecode parses ordinary writes and set values.
Every owner prepares before any owner commits. Commit publishes typed staging
and replaces existing keyed retained records, with no validation or allocation.
Model loads use the shared CHANGEOVER release and publish ModelId after commit.
Invalid sets leave live values, identity and ConfigRev unchanged and publish the
offending Scope/WriteKey. Applied/refused loads produce the Core configuration
events; untrusted input is not adopted as a device fault.

Exports use a private immutable snapshot. JSON matches Core FB_ConfigSetJson;
its authoritative LINE_MAX supplies the 480-character bound. IntValue=1 holds a
255-character mailbox piece, zero completes its line, and BoolValue finalizes the
document. A strict whole-object scanner checks fields/types/integers and decodes
string escapes. An incomplete import never allocates/replaces a saved set. The
largest measured exported line is 382 characters. Session generation, startup
and intervening requests invalidate private transfer state. CPU timestamps are
explicitly unsynchronized. Saved-set exports use successive line ordinals.

The generic HMI repository now queues a complete import/export, so background
config queries cannot interrupt a PLC cursor. Link changes/disposal invalidate
continuations. This fixes the live failure where QUERY_CONFIG ran between export
lines 0 and 1. All single requests keep the existing queue and refresh behavior.
The consistency gate follows the actual export-reader helper after that refactor.

## Native and host validation

| Gate | Result |
|---|---:|
| Named-set operation, rejection, access, isolation, capacity, JSON, privacy and startup checks | 198/198 |
| Named set and live config through owner-preserving power off/on | 15/15 |
| Ordinary config/model/retention regression | 120/120 |
| Authentication/access/session regression | 122/122 |
| State/alarm regression | 96/96 |
| Root decision regression | 36/36 |
| Simulator compilation | 0 errors, 0 warnings |
| Press compilation, two checkpoints | 0 errors, 0 warnings each |
| Siemens tool tests | 148/148 |
| Cross-artifact consistency tests | 35/35 |
| HMI full suite | 574 passed, 8 opt-in tests skipped |
| Flutter analysis | no issues |
| SCL lint / cross-artifact gate | 0 findings / 0 errors, 0 warnings |

The compiled press package has 102 replayed sources. Native readback preserves
AUTO19/HOME4 GRAPH steps and all four LAD examples: 161 networks, 155 calls.
Main remains input read, forest scan, output write. Optional ST/LAD twins remain
uninstantiated. No TC3 implementation or historical evidence was changed.

The opt-in live HMI test passes through the production Web API gateway,
repository, snapshot mapper and widgets. It clicks the native Instant command,
handles an alarm/reset, writes model config, and saves/lists/exports/imports/loads/
deletes station sets. The rendered dialog displays the nine-value station sets
and their unsynchronized timestamps. The artifact includes the actual exported
JSON lines, dialog/config/alarm/manual PNGs, forest snapshot and complete test log.
Shutdown-only canceled reads after disposal are logged and do not affect the
passing assertions. The full HMI suite has three new transfer/concurrency tests.

## Defects identified before qualification

Earlier trials are preserved and do not qualify the final image. TIA rejected
WSTRING/STRING mismatches, WCHAR CASE selectors, narrowing conversions and a
1..0 model loop in a station-only deployment. Late corruption tests found the
missing rejection key on an early shape failure. A standard JSON parser caught
the leading '+' emitted by Siemens integer conversions. Long-key/escaped-value
round trips exercise real lines beyond 255 characters. The UI test now waits for
edited/rendered frames and selects one of the configuration cards' set buttons.

## Evidence and remaining scope

The [immutable archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CONFIG_SETS_2026-10-12/)
contains 5,878 SHA-bound files, 105,504,907 bytes. SHA256SUMS uses repository-relative
paths, and every binding was verified after copying. Runtime/ preserves original
candidate trials, native exports/logs, final runtime/press packages, regressions,
HMI screenshots/JSON/logs and gate results. SourceSnapshot/ records the owning
Core/generator/test/example/HMI sources and transport contract. Earlier archives
remain byte-identical. The archive excludes binary build/cache directories and
DPAPI secrets. The old generated press directory was preserved before replacing
its 95-source package with the compiled 102-source package.

File/database media, line config sets/replication, user/policy/alarm retention,
runtime model creation/current-value export and remaining scalar/array forms are
subsequent work. Full sequence frontier conformance and GRAPH alias exclusion
remain separate qualification. No physical press operation, safety function or
retained-data survival across a full download is claimed.
