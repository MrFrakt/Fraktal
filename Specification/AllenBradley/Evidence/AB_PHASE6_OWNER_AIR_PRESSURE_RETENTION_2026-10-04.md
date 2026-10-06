# Phase 6 — owner confirmation of minimum air-pressure retention

Date: 2026-10-04 (America/Bogota).
Result: **the owner confirms power-cycle retention of
station.airPressureMinKpa = 451 on press68.** The owner reports changing minimum
air pressure from 450 to 451 about nine hours earlier, then power-cycling the
PLC and observing that 451 persists. No exact edit/cycle timestamps or minimum
durability interval were supplied.

The previously recorded read-only preflight at
2026-10-04T15:46:08.351862+00:00 verifies the expected serial 7036B510 and press
fingerprint, and reads this parameter as 451. This corroborates the current
value; the physical cycle and retained-value history are owner observations.
The agent performed no controller I/O or changes in this record's turn. Earlier
admin credential retention remains owner-confirmed separately.

This supplies the representative parameter-retention observation sought by the
proposed Station number test. That proposal was not authorized or executed and
is no longer needed to obtain another owner observation of a retained editable
parameter. The old plan and evidence remain unchanged. Saved-set survival,
other configuration values/accounts, download/upgrade retention, the physical
medium and measured durability window remain unverified by this observation.
It does not establish full Core §3.8b conformance or a general retention matrix.

The owner also reports saving a Model parameter set, then receiving a refusal
when trying to load it. Source review verifies the current behavior: set names
are snapshot identities, separate from ModelCode; SAVE snapshots active model
values. Model save/export is supported, while LOAD_CONFIG_SET for PAR_CFG is
explicitly refused in both AB and the shipping TC3 framework until integration
with the atomic recipe/changeover transaction. No live set operation was issued
by the agent to investigate this report.

The current press declares models M-100, M-200 and M-050 in
`fraktal_ab_press_demo.py`'s MODELS tuple and derives Application.models from it.
Configuration → Model data edits those existing catalog entries. New catalog
models currently require an application declaration change, regenerated L5X and
owner import/Verify/completed download; the HMI has no runtime Add model action.
The [AB project guide](../../Guides/AB_NEW_PROJECT_GUIDE.md) now states that workflow
and distinguishes a new model from a named model snapshot. No model is added or
new controller deployment requested in this turn. A future deployment must
preserve/restore commissioning settings under its current schema/revision and
measure generated-size growth against loaded press68 before claiming native fit.

Full AB discovery 1,541 tests and root 33 tests pass; consistency has 0 errors /
0 warnings. No implementation source, PLC image, Web client, user count or
memory allocation changed. The historical S1 clock probe and TC3 native
segmented transport remain separate work.

The [machine-readable record](AB_PHASE6_OWNER_AIR_PRESSURE_RETENTION_2026-10-04.json)
preserves the owner's observation, binds the prior readback, source files and
gate logs, and limits the retention conclusion to the reported parameter.
