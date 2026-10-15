# TIA selected Unit closed-event history - 2026-10-12

Generator 0.12 qualifies optional LOCAL_RETAIN closed history on the simulated
reference S7-1500. Selected Unit histories survive guarded STOP/RUN and power
cycles with full event records, order and overflow indication. Shared framework
services own storage and restore; the separately wired GRAPH/ST press compiles
offline. This is a closed-history prototype profile, not complete alarm lifecycle,
durable historian delivery or physical press acceptance.

## Images and ownership

Current simulator project:
`%LOCALAPPDATA%/Fraktal/TiaStations/Alarm_Persistence_Runtime_20261012/FrkS12/FrkS12.ap20`.
Offline wired press:
`%LOCALAPPDATA%/Fraktal/TiaStations/Alarm_Persistence_Press_Offline_20261012/FrkS12/FrkS12.ap20`.
The owner Fraktal stays CPU1516/TCPIP/RUN with169.254.212.49 and192.168.1.1, zero
physical adapter mappings, and keeper12728. Its keeper still uses the preceding
Access_Persistence work directory; it has no expiry/unregister cleanup. Physical
1214C and press I/O are untouched. No C# rebuild or owner whitelist change occurred:
candidate_structure_examples remains SHA256
ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74.

The composition declares alarm_history.scopes. Only selected deployed Units
allocate images; omission allocates no history store. The fixture selects StationA,
StationA.Satellite and StationB, out of six Units in the24-module forest. The press
selects its actual root PressDemo. Scope identity and bounds derive from that forest;
Core supplies ring capacity64, event fields, enum domains and CRC arithmetic.
Select histories against the actual controller's retained-memory budget rather
than its program/data memory. This CPU's available retained area is472KB, as specified
in the [Siemens CPU1516-3 PN/DP manual](https://support.industry.siemens.com/cs/attachments/109977238/s71500_cpu1516_3_pn_dp_manual_en-US_en-US.pdf).

The generated owning frame restores before access/mailbox events. The shared close
path retains the event before its sink callback. No extra project scan/wiring method
is scheduled. Active-table overflow commits its retained marker only on the first
Truncated transition; repeated failed raises do not advance the image generation.
Test-only routines and event sink are filed under Tests/ConfigBench/Fixtures in both
source layout and native TIA groups, independently of shared Core services.

## Image and restore rules

Private keyed images contain SchemaVersion first, identity, generation, ring cursor,
used count, Truncated, header CRC, closed records and per-record CRCs. A separate
retained commissioning marker distinguishes virgin storage from cleared headers.
Native export verifies Retain and all external exclusion flags. Live private reads
and writes return200; direct published-ring writes return205.

Canonical encoding derives every ST_AlarmEvent field, including UTF-16 characters,
64-bit timestamps, duration, I/O identity, shelving fields and all time-quality flags.
Shared checksum_services primitives derive from Core F_Crc32 and are also used by
the access consumer. Encoding is binding-local and independent of optimized-DB
padding. Per-record hashes are computed on close; idle scans do not rehash/rewrite
whole images. Header checksums cover all stored per-record checksums.

Restore validates the complete image before publishing any record. Bad schema,
identity, cursor/count, checksum, record text or duration, and cleared commissioned
headers reject the affected history whole. Truncated stays TRUE after rejection,
subsequent new events and further restarts, indicating incomplete history. Peer and
nested histories remain unchanged. Rejection invents no current machine fault and
does not block Start. Explicit test-only engineering clear removes the history and
its retained loss/overflow indication. Restore never replays event callbacks.

This profile stores closed events only. Active/WAIT_RESET alarm and control latches,
commands, sessions and monotonic clock storage retain the existing volatile startup
behavior. Current faults are recomputed by their owners. Active manual-reset recovery
across restart, external durable sinks, file/card media, full-download/changed-layout
loss boundaries and abrupt physical power loss remain separate gates. Timestamp
quality remains honestly unsynchronized; restart preserves the recorded quality.

## Qualification

| Gate | Result |
|---|---:|
| Final closed-history suite |174 passed |
| User/policy persistence regression |419 passed |
| Named config-set regression |198 passed |
| Final ordinary config regression |120 passed |
| Final access/session regression |122 passed |
| Final state/alarm regression |96 passed |
| Final root decision regression |36 passed |
| Successful assertions across qualification |1165 |
| Final runtime compile/download |0 errors,0 warnings |
| Offline press compile, initial two checkpoints and final update |0 errors,0 warnings |
| Native grouped runtime compile |0 errors,0 warnings |
| Siemens tool tests |155 passed |
| Cross-tree consistency tests |35 passed |
| TIA lint / consistency |0 findings /0 errors,0 warnings |

The final174 checks cover full-record equality across STOP/RUN and power cycles,
Unicode including a complete64-record ring of255-character descriptions, real
manual-reset duration/stamps, wrap/order/overflow, no callback replay, private/public
write boundaries, idle/full-active-table write rates, eight corruption forms,
whole-image rejection, isolation and explicit recovery. A retained counter after
the complete forest scan gates startup observation. Full Unicode restore leaves
the simulator in RUN; this is not a hard real-time worst-case execution-time claim.

The419/198 regressions preceded the final overflow write guard. The final change
updates one Core close/raise source and newly salted test provisioning constants;
76 native access/config/set/CRC sources are byte-identical before/after, recorded
in41_unchanged_services.json. History/config/access/state-alarm/decision checks run
after the final download. Tests restore the finite idle timeout left by the access
suite before the alarm suite. No HMI implementation/public contract changed in this
slice; new persistence is observed through the existing readonly ring surface.

The107-source press package replays exactly. Native GRAPH AUTO19/HOME4 and four LAD
examples match the generated object graphs,161 networks/155 calls. Main retains
three calls; GRAPH sequences and ST permissives remain wired at the owning Unit.
Optional ST/LAD twins remain uninstantiated. The press has not been downloaded.

## Findings and evidence

Initial native imports found invalid fixed-length String FC inputs. Detailed
KeepOnError compiler diagnostics identified the issue; changing those inputs to
bare String compiles cleanly. Initial non-ASCII fixture writes returned Web API
-32602. A test-only PLC stimulus creates the Unicode characters locally; retention
and readback are qualified without claiming a production transport workaround.
Private writes correctly return200 rather than the205 used by published readonly
leaves. The initial ordinary-config invocation used schema1; the combined fixture
owns schema2. The final wrapper derives schema and set capability from its generated
manifest. Every interrupted trial remains preserved.

[The immutable archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ALARM_HISTORY_2026-10-12/)
contains raw imports/compiles/downloads, native XML/SCL exports, trial/final fixtures,
regression logs/JUnit files, graph parity, storage readback and source snapshots.
[SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_ALARM_HISTORY_2026-10-12/SHA256SUMS)
binds every archived byte. Earlier archives and relocation payloads are unchanged.
Next work is active-alarm restart policy, durable sink/media adapters and remaining
sequence/frontier/config scope; physical press acceptance awaits the owner's bench.
