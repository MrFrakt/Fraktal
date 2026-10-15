# TIA shared LOAD_DB document medium - 13 October 2026

Generator 0.15 connects station config, every offered model config, named sets,
private users and root policy to the native load-memory mechanism. The selected
reference fixture passes **903 native assertions**. Runtime and wired press
compile with zero errors and warnings. The unselected profile remains available;
no released Core enum or record layout changes in this slice.

## Images and ownership

Current simulator project is
`%LOCALAPPDATA%/Fraktal/TiaStations/Persist_Medium_Runtime_20261013/FrkS12/FrkS12.ap20`.
The separate press project is
`Persist_Medium_Press_Offline_20261013/FrkS12/FrkS12.ap20` in the same station tree.
Both preserve the engineering/security identity of their qualified predecessors.
The older S16 and event-delivery projects remain available.

The owner is Fraktal/CPU1516/TCPIP/RUN at 169.254.212.49 and 192.168.1.1,
with all physical interface mappings zero. Keeper PID12728 is preserved. The
approved candidate_structure_examples driver is unchanged, SHA-256
`ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74`.
Every mutation guards that owner; no physical PLC or press download occurred.

## Adapter and consumer behavior

The declaration selects LOAD_DB, a global minimum write interval and a bounded
queue. The fixture consumes 17 documents; the press consumes seven. Each document
has two private optimized UNLINKED banks, three private working buffers and a
private typed candidate. Keys, document geometry and schemas derive from existing
configuration owners and Core types. Header constants and CRC budget have one
policy authority. The adapter is identified by readonly metadata; the released
controller-local StoreKind ordinal is preserved, not extended.

The medium validates magic, schema, key CRC, generation, length and document CRC,
then its consumer validates the full deserialized candidate. Configuration
reserves every destination before applying any row. User shape/CRC validation
operates on private candidates before installation. Named sets and policies reuse
their owning validation. Confirmed load documents replace the typed caches, proven
by deliberately poisoning config text and the user checksum before restart.

A FIFO ticket owns its buffer lease through collection. Polling advances at most
one stage per scan; CRC work is bounded. Native REQ pulses once, write rate is
bounded globally and startup imposes a fresh delay. A write becomes durable after
native read-back validation and selector-committed confirmation. Live acceptance
precedes that point and Pending/Failed makes the distinction visible. Individual
writes and named-set apply share a dirty hook; an unchanged registered config
value does not advance its generation.

An unreadable boot keeps the restore barrier, drops sessions/commands, withdraws
derived device outputs through owning hooks and retries. Damaged documents are a
different result: defaults plus ENGINEER acknowledgement for config, restrictive
policy fallback, and fail-closed users with trusted provider repair. A corrupt
confirmation anchor cannot silently authorize a restore or replacement. Historical
RestoreLost remains set after acknowledgement in the existing contract; a new
unacknowledged loss is the regression criterion.

The availability stimulus is a test-only failure before native I/O. Its retained
flag survives STOP/RUN, and its observer runs before the barrier so availability
can be restored. These tests prove retry and control quiescence at that seam;
they do not claim physical instruction failure or arbitrary interruption during
a native transfer.

## Qualification

| Final native suite | Assertions | Raw log |
|---|---:|---|
| Shared medium and consumers | 340 | 45_native_consumers_final.jsonl |
| Access/session regression | 122 | 53_access_regression.jsonl |
| State/alarm regression | 100 | 63_state_alarm_final.jsonl |
| Manual alarm recovery regression | 341 | 65_recovery_final.jsonl |

All four final suites complete with zero failures. Native cases include active
and inactive model values, two roots, saved sets, policy/users, poisoned caches,
STOP/RUN, simulated power, write retry, unreadable boot while commanded, damaged
newest/both slots, damaged config/user anchors, repair privilege and confidentiality.
Prior config/set/user suites from the LOCAL_RETAIN image remain prior evidence;
they are not relabelled as LOAD_DB qualification.

The final runtime import (43_native_compile.jsonl) and final press import
(46_press_compile_final.jsonl, both compile stages) report zero errors/warnings.
There are 157 grouped press sources. Native read-back matches 19 AUTO and four
HOME GRAPH steps; optional LAD has 161 networks and 155 calls. Optional ST/LAD
renditions are uninstantiated, ST permissives and GRAPH are wired, and press MAIN
remains three calls. The press is compiled offline; physical acceptance awaits
an actual bench.

Siemens tool tests: **177 passed**. Cross-artifact tests: **35 passed**. Shipped
source lint and consistency pass, and whitespace checks are clean. Broad fixture
lint also records eight pre-existing missing-ELSE findings in older test-only
stimuli; it is retained as a failed diagnostic run, not presented as a passing
gate. HMI code was unchanged during this continuation; its earlier measured gate
is preserved rather than rerun without a relevant change.

Failed development attempts remain in the archive. They include the source VAR
match, warning-bearing OutImm borrowing, the named-set dirty-hook defect, the
nonretained fault-injection flag, press import dependency ordering and a generated
constant FOR 1 TO 0 rejected by TIA. The historical-loss assertion was corrected
to the existing acknowledgement semantics. Regression harnesses now wait for the
selected asynchronous restore barrier before asserting recovered state; expected
alarm and authentication outcomes are unchanged. Access-test timeout and
standalone publisher state are explicitly normalized between suites.

Final normalization returns the roots to MANUAL, logs out sessions and verifies
RUN/readiness/durability. The independent byte check and final owner facts are
bound by the machine-readable gate summary in the archive.

## Remaining boundaries

This is a measured draft Siemens adapter on the simulated S7-1500, with consumed
geometry and the Core document/key bounds; it introduces no 150KB reference cap.
It does not qualify physical flash endurance, arbitrary torn writes, changed
layout/full-download retention, CARD_FILE/external adapters or S7-1200 fit. It is
not a physical press acceptance result. Complete generic sequence frontier and
annotation publication, provider/line-config facets, module expansion and deployment
acceptance remain port work. New documents or layouts still need explicit
migration/commissioning evidence, rather than inferred preservation.

[Immutable archive](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_PERSIST_MEDIUM_2026-10-13/)
and [SHA256SUMS](../../../FraktalCore/PLC/Siemens/Evidence/Archives/TIA_PERSIST_MEDIUM_2026-10-13/SHA256SUMS)
bind raw attempts, final JUnit, native exports, import plans, generated packages,
source snapshots, replay/parity and gate summaries. Earlier archives and dated
reports are unchanged.
