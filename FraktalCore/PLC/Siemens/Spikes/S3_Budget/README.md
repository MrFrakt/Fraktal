# S3 — Unit idle path and contract-storage budget

Phase 0 measurements on the disconnected 1214C V4.7.3 bench. The generator
copies S2 + S11_Scl and generates memory-only UDTs from the authoritative
TwinCAT Core DUT declarations. The manifest records every source hash, field,
physical mapping, string width, capacity and storage array. It adds no runtime
library, recipe implementation or alarm algorithm.

`wide` keeps Core widths up to Siemens' 254-character limit and Core capacities.
`compact` tests candidate reductions from `make_fixture.py`; these are **not a
released family profile**. All fields remain present. Enums map to DInt, DT to
DTL and the two config-write pointers to logical UDInt indices. Initial values
are omitted for the storage experiment. Groups are measured independently:

- `module`: 16 full status records plus derived-state storage.
- `alarm`: active events, closed ring and rationalization metadata.
- `sequence`: live rows, static definitions, active cursors, sparse annotations
  and the current step with its condition records.
- `config`: manifest page, value-keyed snapshot, set headers and write metadata.
- `writes`: configuration-write metadata alone, to check per-module cost.
- `all`: all four contract-storage groups in one image, with shared UDTs.

Separate DBs prevent a per-block ceiling from being confused with total work
memory. Their arrays are private to the experiment. Memory comes from the
authenticated native Diagnostics > Memory page; cycle means come from PLC scan
counters over three five-second windows under the same read workload.

```powershell
python FraktalCore/PLC/Siemens/Spikes/S3_Budget/make_fixture.py <new-folder> --group alarm --profile compact
python FraktalCore/PLC/Siemens/Spikes/S3_Budget/verify_export.py <source-folder> <export-folder>/xml
```

`--units 4` adds four named idle Units and their two children each, reaching
15 registry rows. The harness expectation changes to that exact count; every
other case remains unchanged. `--unit-quiet` derives the minimum guard from the
CM fixture, uses RunReq/AbortReq and fences only lifecycle begin/hooks/end.
Mailbox, child calls, per-scan chain clear and published mirrors remain active.
The linter rejects a changed guard, conditional child tick or conditional mirror.
S2 now carries the measured quiet frame. The builder strictly removes its known
fences for the full comparison variant, so both variants remain reproducible.

Identify the bench before each controller-changing plan and keep the existing
station/certificates. `build_download.plan` rebuilds and downloads in one
Openness session; `update_unit.plan` changes only the Unit source; the
`update_memory.plan` optimization is for changing widths/capacities **within
the same memory group**. A different group requires the full rebuild to remove
the previous group's storage. Compile software and hardware 0/0, read back
generated fields/types, harvest exactly cases 1–17,29,30 and restore the base
image after the experiment. Approved drivers are never rebuilt or overwritten.

`measure.py` needs both password environment variables used by S11/S9 and the
existing TLS pin. It never logs passwords/cookies/tokens. A caller may pass one
authenticated `NativePage` as `native_page` across a series; that caller owns its
logout. A dead socket on the memory GET gets one pinned reconnect with the same
cookie. API sessions log out per measurement; standalone native sessions attempt
logout in `finally`. Repeated standalone form logins still exhausted the native
session pool on 2026-10-10 despite those attempts. A corrected live probe still
read protected memory with the old cookie after both measured GET logout forms.
`NativePage.close` now drops local cookies and closes the socket even on failure;
server-side revocation is not proven. Use one session for a series. Do not repeat downloads for a failed
read-only measurement. Aggregate deltas include small DB/compiled-type overheads;
they are not exact per-field byte counts or proof that complete press logic fits.
