# Named station/model config sets

Generator 0.10 adds an optional deployment declaration:

```json
"config_sets": {"capacity": 4}
```

Omit it or use capacity zero to omit all named-set storage and capabilities.
Capacity is bounded by Core MAX_CONFIG_SETS. Storage and working buffers belong
only to actual roots. The record window derives from the largest consumed config
kind in a root, bounded by Core MAX_SET_RECORDS. A larger projection is refused
whole. Child modules have typed staging records and no set catalogs or documents.

Save/list/load/delete and JSON-lines export/import use the existing generic HMI
request kinds. List and export mirrors are readonly and fetched on demand.
CONFIG_SET governs every operation. Capture/export also recheck each field's read
level; import/load recheck its write level. A station load checks each field's
RequiresReady; a model load also takes the shared CHANGEOVER release. Every record
is checked against its owning definition, parsed by FRK_ConfigDecode and staged
before commit. Missing, duplicate, unknown, foreign or stale capabilities reject
the complete operation and name the offending Scope/WriteKey. Model identity is
published after the complete recursive commit. Credentials never enter a set.

LOCAL_RETAIN is the current adapter. The store moves keyed ST_ConfigRecord values;
the typed owner remains the authority. Accepted live writes and saved snapshots
are separate retained data. The generic ConfigPersist status reports availability
and failures. File/database media, line config sets, runtime model creation and
current-value export remain subsequent slices. A station-only deployment refuses
model sets; its compiled zero-model path contains no invalid 1..0 loop.

The wire format matches Core FB_ConfigSetJson: one header and one record per line.
The Core authority supplies the 480-character line bound. TextValue pieces fit
255 characters; IntValue=1 holds a piece, the final piece uses zero, and BoolValue
marks the last document line. The PLC refuses overflow rather than truncating.
The strict scanner validates the entire object, unique fields, types and integer
grammar, with JSON string escapes including representable Unicode escapes.
An interrupted operation, logout/session generation or restart discards private
import/export state. A partial import never allocates or replaces a saved set.
Export uses an immutable private snapshot and exact successive line ordinals;
permission checks repeat for each line. Optional current-value export is absent.

make_fixture.py extends the existing two-root, 24-module decision/config bench.
Each root has three Unit station config records and 24 model config values. The
station record schema is 2: its additional LongText field has a 140-character key
so real exported lines exceed one mailbox request. Test-only set_bench.scl.in can
corrupt a saved record; production set storage stays inaccessible. The fixture
requires ENGINEER for CONFIG_SET. Main calls bench setup, the forest scan and
observation; decision acceptance keeps its existing separate hook.

probe_web.py exercises operations, late rejection atomicity, root isolation,
capacity, long-line round trips, malformed imports, availability, access and
readonly/private boundaries. retain_probe.py separately checks named and live
values through a guarded power cycle, preserving the owner registration/keeper.
config_regression.py repeats ordinary config acceptance with this deployment.
run_gateway.py runs the production gateway under the DPAPI credential wrapper;
set FRAKTAL_TIA_CONFIG_SETS_LIVE=1 for the existing generic HMI live test.

Current simulator project:
%LOCALAPPDATA%\Fraktal\TiaStations\Config_Sets_Runtime_20261012\FrkS12\FrkS12.ap20.
The press example remains in a separate compiled offline project. No physical
press acceptance or retained-data survival across full download is claimed.

See [dated evidence](../../../../../Specification/Siemens/Evidence/TIA_CONFIG_SETS_2026-10-12.md).


Native qualification: 198 set checks, 15 power-retention checks, and the existing
120 config / 122 access / 96 state-alarm / 36 decision checks pass. The largest
measured exported line is 382 characters. The compiled press has 102 replayed
sources, 19 AUTO / 4 HOME GRAPH steps, and native parity for all four LAD examples.
The generic HMI queues a complete document transfer so its background manifest
queries cannot interrupt a PLC cursor; interruption invalidates remaining lines.

The current owner image is now Access_Persistence_Runtime_20261012, qualified in
[access-retention evidence](../../../../../Specification/Siemens/Evidence/TIA_ACCESS_PERSISTENCE_2026-10-12.md).
The config-set behavior and original dated archive above remain unchanged.
