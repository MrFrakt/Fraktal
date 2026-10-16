# Shared operations, GRAPH pacing and native test gate (2026-10-16)

Generator0.22 continues the reference S7-1500 port. It adds V3 shifts, OEE/state
accounting/degradation, health/nameplates/build gates, shelving/tower/lamp test,
per-mode pacing, typed teach capture and fixed host rings. The normal generator
still refuses incomplete Line profiles; classes, runtime model creation, generic
I/O/modules/connectors, OUC replication, durable host delivery and full physical/
deployment acceptance remain open. P12 is owner-selected OUC TCP; P15 is reusable
connectors, with device-specific ports deferred. **[measured / owner decision]**

## Verified scope

- Shared operations native assertions:93 passed. Tests execute on the CPU and
  report an exact image fingerprint, assertion count and JUnit failure status.
  A fresh engineering project compile/read-back/download/test/cleanup gate also
  passes;248 Siemens tool tests pass. Neither gate establishes complete R3/R5/R6
  conformance. **[measured]**
- Two-root production/calendar probe:73 checks passed. Live health/gate/tower/
  capture probe:46 checks passed, including authorization, revision and actual
  out-of-range machine-value refusal. Calendar admission is whole-image and
  target edits apply at a finite boundary. **[measured]**
- Wired press native software compile is0/0 twice;254 generated sources replay
  and557 canonical sources/152 type-FB interfaces/62 DB interfaces match.
  GRAPH LoadPosition4/AUTO19/HOME4/CHANGEOVER6 and optional five LD examples
  (198 networks/192 calls) match independent native graph dumps. The final live
  press probe passes63 checks, including repeat jump880→810, pacing, static
  engineering metadata and inaccessible private owners. **[measured]**

## Engineering lessons

Native compile alone is insufficient. TIA drops external-access flags on
VAR_IN_OUT parameters, omits empty sections, and moves DB initializers into the
native DB representation. Emit separate DB sources; import an instance DB after
its FB. Hide sequence owners and expose their progress through the shared view.
Do not weaken canonical interface/source comparison to accept a source that TIA
did not store. Hardware sources belong in the composition's00_System/Hardware
group; generator refresh must remove old group locations as well as obsolete
filenames. **[measured]**

Native GRAPH needs separate parameter-instance DBs, not multi-instances. Its
transition reads the preceding scan's result; preserve that result until native
evaluation, but suppress it when hold-to-run is released. A decision consumed
while a paced step waits must remain owned by that step; otherwise a one-scan
answer disappears. Shared SeqDecisionAsk/Take retain the answer and avoid a
second prompt until mandatory step/lifecycle rearming. **[measured]**

Core health translation must distinguish formal argument names from variable
references. Prefixing a formal with# can compile but changes stored source;
read-back detected this. `RT_INFO(MODE:=25, OB:=0, ...)` compiled and measured
task execution; the attempted `OB_ANY#0` form was rejected. RD_SYS_T availability
does not qualify synchronization; controller/memory/IPC/PN metrics remain
unavailable until a corresponding native source is qualified. **[measured]**

## Simulator ownership and disk pressure

Use one extra unmapped test CPU at a time and wait for the host to exit after
signaling its stop file. Never unregister/recreate the saved Fraktal CPU, alter
its storage/certificate/IPs, or change physical output commissioning gates.
Original Fraktal remains RUN/TCPIP at169.254.212.49 +192.168.1.1. **[measured]**

SDK UpdateTagList on an entire large test FB caused excessive allocation. Use a
tiny separate result DB containing only status/count/fingerprint fields. Two
successive full downloads during initial web preparation also grew one disposable
simulator to about7.6GB private allocation and left about120MB on C:. Stopping
and unregistering that test CPU recovered over6GB without deleting files. A
single-download press session stayed around2.7GB. Configure web users on the
offline isolated project, then host and download once. **[measured]**

The isolated hardware project has two known protection warnings (no configured
PLC protection level; no CPU display password). Record both explicitly and
reject all other warnings. Software builds remain warning-clean. This does not
qualify production protection; the target is reserved and has no real-network
mapping. **[measured]**

Nested synthetic Units need their own finish stimuli before testing a READY-only
operation. A correct readiness refusal can mask the intended range check; drive
NestedFinish/InnerFinish, prove all descendants READY, then assert RECIPE_INVALID.
Never relax a PLC release gate to make a fixture pass. **[measured]**

## Evidence and tools

Report: `C:/Projects/Fraktal/Specification/Siemens/Evidence/TIA_OPERATIONS_GRAPH_2026-10-16.md`.
Immutable payload: `FraktalCore/PLC/Siemens/Evidence/Archives/TIA_OPERATIONS_GRAPH_2026-10-16`.
Tools: `fraktal_tia_gate.py`, `fraktal_tia_test.py`, `tia_isolated_session.py`;
fixtures: `Tests/Operations`, `Tests/PressTests_TIA`. DPAPI wrappers own credentials;
private initializers/exports, engineering projects, simulator storage and SQLite
backups are excluded from public evidence. **[measured]**
