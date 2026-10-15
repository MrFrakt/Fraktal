# Station config and model config bench

Generator0.8 registers editable config from one type declaration. The existing
24-module/two-root fixture adds typed station config, complete model config,
MODEL_A/MODEL_B, keyed local-retain records and prepare/commit/abort model changes.
It uses the existing DPAPI application provider and isolated owner Fraktal instance.
Line config keeps its own consistent name in the HMI/spec; its optional owner/mirror
runtime is not implemented by this slice.

```json
"station_config": "ST_UnitStationCfg",
"config": [
  {"member": "StationCfg.SiteLabel", "key": "siteLabel", "revision": 1,
   "label": "project.config.siteLabel", "requires_ready": false},
  {"member": "ParCfg.Preset", "key": "preset", "revision": 2,
   "label": "project.config.preset", "minimum": 0, "maximum": 1000}
]
```

Top-level `model_config: {"models": ["MODEL_A", "MODEL_B"], "initial": "MODEL_A"}`
declares the local catalog. Model config requires registration of the complete
ParCfg record except SchemaVersion. Model/station records begin with a nonzero
SchemaVersion UINT initializer. Supports BOOL, INT, DINT, UDINT, TIME and bounded
STRING. Scope/value/key/model-code widths derive from Core records. Wider text,
unsupported scalar/array/enum forms, duplicate targets/keys and invalid ranges
are refused before import. Float/capture/custom-class/collection support remains open.

Editable ParCfg is a module-owned static, externally read-only. Siemens warns
when a VAR_INPUT is passed to a mutating FC; the new profile owns the value where
it is used. Other profiles retain their existing interface. Generated own-frame
services take only the components they need; they do not require an FB self pointer
or a project-authored assembly call. Restore precedes FRK_Begin/Init. Generator
validation rejects project writes to config authority, staging and model identity.

The manifest and handler use the same per-type definition. WRITE_CONFIG rechecks
canonical owner/key/revision, effective DATA_WRITE/minimum level, readiness,
storage format and bounds. Direct native writes to config authority refuse205;
private staging/store reads refuse200. Another model's edit is root-model-scoped,
does not touch the running config, and can proceed while BUSY. Explicitly naming
the active catalog index still requires readiness. Child model config follows
the active model; station config does not accept a model index.

The local-retain pool stores ST_ConfigRecord by (Scope, WriteKey, ModelCode), with
schema metadata. Its capacity derives from consumed fields and offered models,
not a maximum table on every instance. No instance DB byte image is restored.
Station config and model config restore separately. Invalid/missing active records
default the affected owning record and publish CONFIG_RESTORE_LOST; valid station
config survives a rejected model record. ENGINEER-or-higher acknowledges loss.
The published ConfigPersist reports the Core window and store failure. Writes
publish only after the local-retain update succeeds; a failed store leaves live
values intact. Named-set StorePresent remains FALSE.

SET_MODEL uses the same CHANGEOVER release as its pure query. Every participant
validates into private typed staging; one late rejection leaves all live values
and ModelId intact, names the offending owner/key, and faults RECIPE_INVALID.
Commit is bounded memory publication without validation or I/O. Station config
is excluded. Session activity/audit use the existing shared access lifecycle.

Native candidate V5 passes120 config checks; V6 repeats120 after deterministic
source ordering. The separate retentivity probe passes7 checks including STOP/RUN,
power-cycle and private exclusion. Native export comparison:190 authored blocks,
52 interfaces, compile0/0; native reimport agrees. Production183/52 compiles0/0
without test fixtures and is not downloaded. Access122/state-alarm96 regressions,
23 blocking-restore checks and the live authenticated editor pass. The editor's
input/save button writes21, independently reads the PLC, verifies inactive-model
isolation and restores10. The live mapper correction preserves declared access
and bounds while using newer scalar readings.135 tools and571 HMI tests pass
(8 opt-in skips). No full Core conformance is implied.

Use the existing Access/with_credentials.ps1 with `-ScriptFile make_fixture.py`
for prepare or `probe_web.py` for probe. All writes and mode changes require exact
Fraktal CPU1516 TCPIP169.254.212.49 with zero physical mappings. cycle_simulator.ps1
is test-only and never unregisters the owner. Its keeper must remain alive.
Current project: TiaStations/Config_Runtime_20261011/FrkS12/FrkS12.ap20.

Named config sets, file/load-DB media, user/policy/alarm persistence, optional line
config replication, floating/enum/array/capture/custom-class forms, full sequence
integration and complete restore-loss detection across download remain open.
The current Python/simple JSON path rejects escaped Unicode before mailbox commit;
that measured transport refusal is not a PLC string-validation claim.
See [dated evidence](../../../../../Specification/Siemens/Evidence/TIA_CONFIG_TRANSACTIONS_2026-10-11.md).
