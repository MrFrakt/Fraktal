# S16 load-memory transfer

This gate qualifies native `READ_DBL` and `WRIT_DBL` on the owner Fraktal
simulated CPU1516, TIA V20 and PLCSIM Advanced V7. Config, named config sets,
local users and root policy continue using their existing LOCAL_RETAIN adapters.
The next layer connects those consumers to a selected keyed document medium.

| Variant | Native result | Storage |
|---|---|---|
| Optimized ordinary banks | 125 checks | Independent current RAM and load-memory values |
| Optimized UNLINKED banks | 118 checks | Bank payloads exist only in load memory |

The four private 64-byte buffers are a source, two independent banks and a
read destination. Test requests stage Kind/Seed and commit Sequence last; the
fixture samples once, keeps the native source stable while BUSY and acknowledges
only completion. Each native operation is polled with REQ FALSE after its initial
call. Invalid kinds do not issue a native operation. Diagnostics expose only
readonly mirrors. This request surface belongs to the test fixture.

WRIT_DBL leaves the ordinary bank's current RAM unchanged. Deliberately changing
that RAM and clearing the read destination still reads the saved load-memory
bytes. Both banks survive STOP/RUN and simulated PowerOff/PowerOn, including a
payload that wraps byte values. A complete 64-byte CRC agrees with Python zlib;
private payload reads refuse error 200 and diagnostic writes refuse 205.

The load-only property is readonly through the observed Openness attribute API.
A native XML import first proved `IsOnlyStoredInLoadMemory = true` while retaining
Optimized layout. Its native SCL export supplied the portable `UNLINKED` keyword.
`make_load_only.py` derives those source declarations from an ordinary native
export, asserts each edit, and removes RAM access from the test FC. Reimport,
compile, native property readback and runtime qualification all pass. Native
sources retain their exported bytes apart from the explicitly asserted edit.

Both variants compiled with zero errors and warnings. The unchanged approved
candidate_structure_examples driver preserves project security and performs
guarded downloads; every write/restart checks Fraktal, CPU1516, TCPIP,
169.254.212.49 and zero physical adapter mappings. No instance is unregistered.
Web/application credentials use the existing DPAPI environment wrapper.

Run `make_fixture.py <new-output> <qualified-authored-runtime>` to add the gate
to an isolated project copy. Import its five `06_*.db` files, then
`39f_LoadMemoryBench.scl`, then the updated `38_ConfigBenchRoutines.scl`.
Compile before downloading. For the second variant, run
`make_load_only.py <new-output> <ordinary-native-export>` and import its two DBs
and FC. The archived plans preserve the exact guarded engineering commands.
Run `probe_web.py <new-log>`, adding `--load-only` for the second variant, through
the existing credential mechanism. The probe expects fresh bank start values;
use a deliberate new fixture image rather than rewriting a previous evidence log.

Current test project:
`%LOCALAPPDATA%/Fraktal/TiaStations/Load_Memory_Only_Runtime_20261013/FrkS12/FrkS12.ap20`.
The original event-delivery project and compiled GRAPH/ST press remain available.
The registered owner and keeper PID12728 remain active.

The next adapter needs bounded tickets driven by consumer polling, keys and
whole-document validation, two-slot generations/CRC, confirmed-loss markers,
unreadable-storage retry and a bounded flash write rate. Live acceptance remains
separate from durable completion. Config restore and confidential user restore
must complete before writes, Start or login can proceed. Application code must
acquire the medium through its existing generated owner path, with no extra
cyclic scheduling call. Named sets should share the same chosen medium.

Physical flash endurance, arbitrary interrupted writes and changed-layout/full
download retention remain commissioning gates. This byte-transfer result does
not establish complete document or consumer durability. See
[the dated evidence](../../../../../Specification/Siemens/Evidence/TIA_LOAD_MEMORY_2026-10-13.md).

Instruction behavior follows the primary
[READ_DBL reference](https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/data-block-functions-s7-1200-s7-1500/read_dbl-read-from-data-block-in-the-load-memory-s7-1200-s7-1500)
and [WRIT_DBL reference](https://docs.tia.siemens.cloud/r/en-us/v20/extended-instructions-s7-1200-s7-1500/data-block-functions-s7-1200-s7-1500/writ_dbl-write-to-data-block-in-the-load-memory-s7-1200-s7-1500).
