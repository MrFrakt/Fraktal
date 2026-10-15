# Shared LOAD_DB document consumers

[measured 2026-10-13] Fraktal generator 0.15, TIA V20, simulated CPU1516 on
PLCSIM Advanced V7. Shared medium consumers pass 340 native assertions; access122,
state/alarm100 and recovery341 also pass (903 total). Runtime and offline press
compile0/0, tools177/consistency35. No physical press or flash claim.

The declaration chooses LOAD_DB, minimum_write_ms1000 and queue_capacity4. Actual
keys/geometry derive from owners:17 fixture documents, seven press documents.
Each uses two private optimized UNLINKED banks and private typed/read/write buffers.
READ_DBL/WRIT_DBL polling is serialized; CRC work is bounded and confirmation
follows native read-back. Retained selector-committed anchor banks detect confirmed
newest-copy loss. Cache poisoning proves restoration reads the load documents.
The global minimum write interval also restarts after startup. Unchanged registered
config values do not advance generation; named-set apply must dirty its live document.

[measured] Quiesce before clearing the registry. FRK_End synchronizes its registry
entry; invoking it after clearing the registry produced a fault and empty names.
This was not demonstrated to be a GetInstancePath alias failure. The selected
profile's BoundPath derives from the declaration tree. Abort/cyclic hooks are
extracted once and reused for normal scanning and cold quiescence. Published
OutImm in FB static storage avoids warnings from passing uninitialized VAR_OUTPUT
storage as VAR_IN_OUT. All final native compiles are warning-clean.

[measured] TIA rejects a constant FOR1TO0 with 'The high limit is not higher than
the low limit'; omit the empty generated loop. Decimal bounds must be emitted as
native numbers, not by appending '.0' to a value already containing a decimal.
Python's substring VAR\n also matches END_VAR\n; anchor source-section transforms.
A typed quiesce FC needs its FB type declared first; defer press quiesce import
until after its Unit, before composition. Native graph read-back remains19AUTO/
4HOME; optional LAD161networks/155calls and MAIN3calls are unchanged.

[measured] Availability injection is test-only and precedes native I/O. Its retained
flag survives STOP/RUN and its observer precedes the restore barrier so recovery
is possible. Do not call it physical transfer-failure qualification. Root sessions,
commands and derived outputs withdraw while boot waits. Damaged users fail closed;
trusted user commit repairs an invalid medium anchor. Policies use restrictive
fallback, config replacement requires ENGINEER acknowledgement. RestoreLost is
historical; check RestoreAcknowledged before calling a repaired image newly lost.

[measured] Existing synchronous restart probes need the selected document barrier
before checking alarm restoration or sending login. Keep their expected outcomes.
The access test intentionally leaves an idle timeout; normalize bench policy and
standalone publisher state between suites. Raw failed attempts remain evidence.
The runner's require-clean-compile checks the completed log: if a plan also downloads,
a warning image can already have been downloaded. Use compile-only verification
then a separate guarded download-only plan.

Independent Python zlib verifies the confirmed station document's key/header/body
CRC (bankB generation11, length3894, extent4472 in final evidence). This exposes no
user hashes. Other medium names, physical endurance/torn writes, full-download or
changed-layout preservation, card/external adapters and1200fit remain unqualified.

Current projects: Persist_Medium_Runtime_20261013 and
Persist_Medium_Press_Offline_20261013, each FrkS12/FrkS12.ap20 under local station
storage. Owner Fraktal stays RUN, physical mappings0, keeper12728 preserved and
approved candidate_structure_examples hash unchanged. Final roots MANUAL/loggedout,
no pending/failed durability. Evidence and sealed SHA256SUMS:
C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_PERSIST_MEDIUM_2026-10-13.md.
