# Fraktal/AB

This tree is reserved for the Allen-Bradley Logix binding. The authoritative
implementation specification is
[`Specification/Fraktal_AB_Part_III.md`](../../../Specification/Fraktal_AB_Part_III.md).

Current status: **R0-R6 all PASS**. Every readiness gate in Part III now records
PASS, so production AB runtime and module-library implementation is authorized
to begin - against the bounds those gates record, not around them. **R6 passes
for the declared read-only claim only**: CIP Security, Security Level 2 and
write-enabled operation are explicitly not claimed, and enabling writes reopens
Core 14 in full. **S15 is narrowed**: Studio Verify is automated but needs a
logged-in desktop, and download is deliberately not automated. **S5's CI path**
is the named isolated bench with the download as an authorized manual step, not
zero-touch CI.

**Phase 4 has begun.** The runtime base exists in its generated form: one
committed Python declaration emits the contract UDTs, the module AOIs, the mode
owner, the routine and the full-project L5X, and the press demo emitted from it
imports at `0/0`, clears Studio v33 Verify at `0/0`, is a registered gate leg,
and runs on the bench with all fifteen matrix rows passing on three consecutive
runs. **Hand-authored L5X remains forbidden** - the declaration and the
generator are the committed sources and the L5X is output.

The press AUTO graph is declared once and **rendered in all three languages** -
ST, native SFC and ladder - each emitted from that one declaration, read back
and machine-checked for graph equality, and walked on the bench with identical
traces. MANUAL and HOME stay single-rendition ST, as the TwinCAT press keeps
them. **Hand-authored ladder is forbidden along with hand-authored L5X**: a
rendition is an emission, never a second maintained source. And the published
contract will describe that graph **once, rendition-agnostic** - the rendition
selector is a harness input, probe-only and never published, because which
language ran is a property of how the application is measured, not of the
machine it describes.

**This is still not a runtime library.** Module AOIs are generated *per
application*; the reusable library form is Phase 6. Recipes, changeover, part
traceability, release reports, the gateway/repository adapter, the generic HMI,
physical I/O and any control-power domain are all out of scope and recorded as
deferrals, not omissions.

The current Phase 0 workstation target is `192.168.100.89`, historically from
host adapter `192.168.100.99/24`. FactoryTalk Linx 6.50 browsed it through the
point-to-point alias `Fraktal_AB` on 2026-08-13; **neither still holds on the
2026-09-06 bench workstation**, where the host address is `192.168.100.123` and
`FTLinxCfgIETool.exe /Browse` fails with `status is 2` for every path tried,
including a driver Studio can see. Reachability is unaffected — Studio's Who
Active browses USB and every probe speaks EtherNet/IP directly — see the S16
execution record. Historically, direct CIP identity and symbolic reads also
pass. Studio 5000 v33 positively connected through
`Fraktal_AB\192.168.100.89`, but Studio and SDK read-only uploads over Ethernet
timed out. After USB was reconnected, Studio uploaded successfully through
`Backplane\16` with zero errors and warnings; the upload-derived v33 L5X also
passed a canonical SDK conversion round trip, and Studio's offline
**Verify Controller** completed with zero errors and warnings. The
Ethernet/SDK online issue remains open. With the user's explicit authorization
and all I/O disconnected, a generated memory-only v33 fixture was verified,
downloaded through USB to the serial-matched controller, returned to Remote Run,
and exercised over EtherNet/IP. Controller/program-scoped scalars, arrays
through a fragmented 4 KiB `DINT[1024]`, STRING, UDT, PLC-derived results,
External Access, liveness, and cleanup all passed. Bounded connection-size,
reconnect, timeout-recovery, and concurrent-reader tests also passed. One fixed,
authorized operation corrected the fixture wall clock from 1998 to host UTC;
the fixture reports PTP disabled/unsynchronized and Fraktal preserves that
quality explicitly. No firmware, fault-clear, network-configuration, or
physical-I/O operation occurred. S1 is PASS. S2 then imported, verified,
downloaded and executed a memory-only eight-level nested-AOI fixture: one UDT
`InOut`, STRING `InOut`, atomic Input/Output, private AOI storage, member
External Access, cleanup, and exact target binding all passed. Studio v33 fixed
the platform boundaries at 64 InOut parameters and 16 invocation levels;
Fraktal's generated nesting ceiling is eight. S2 is PASS. A separate
invalid-ST fixture was correctly rejected by Studio Verify with two errors.

S11 then replaced that fixture, under fresh explicit authorization and with all
I/O disconnected, with a memory-only fixture generating **both** AB §3.5
execution forms from one graph declaration: the ST reference-form sequence AOI
nested by an owner AOI, and a program-owned native SFC chart driven by the
generated JSR/SFR wrapper. The generated chart imported cleanly, passed Studio
v33 **Verify Controller** with zero errors and warnings, and round-tripped
canonically. On the controller the two forms walked the identical step trace in
an identical four scans; the root module AOI ran unconditionally and always
ahead of sequence intent; the command/result loop measured exactly one scan; the
simultaneous branch ran one numbered leg per Core branch; and `SFR` reset re-ran
the chain identically. **S11 is PASS and S4's native-SFC family is settled with
it.**

S12 then measured the type map on the same target. `TIME`, `TIME32` and
`LREAL` are unavailable on this controller — the first two abort the import,
the third is rejected by Studio Verify after the SDK had accepted it — and
`LINT` is transport-only, since it declares and round-trips but no arithmetic
form compiles. Duration therefore binds to a range-checked `DINT` of
milliseconds. The public UDT's CIP payload was measured member by member: 24
bytes with a 24-byte array stride, four of them trailing padding forced by the
`LINT`'s alignment. Integer overflow wraps two's-complement, and a NaN bit
pattern transports faithfully while Logix ST's `NaN <> NaN` evaluates false, so
generated code must test NaN by bit pattern. **S12 is PASS.** The S12 fixture
was later replaced: S9 downloaded its coherence fixture on 2026-08-14, and the
controller has held that clean S9 fixture in Remote Run ever since. Its identity
and Remote Run state were re-confirmed read-only on 2026-09-06
([`AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md) §7).

A later Studio-only v38 exploration on a disposable `5069-L310ER` revision
38.11 project imported all 28 declaration/use probes and ran Verify on each;
26 were clean, while the two duration cases correctly rejected an untyped
integer operand. It exposed family-specific differences, but the SDK licence,
unchanged v33 regression, and SDK-import evidence are still missing, so it is
explicitly not a second S12 baseline and does not change the frozen v33 contract.

S4 then closed offline with a representative construct matrix: two task types
with their schedules, ST, RLL and SFC routines side by side, nested and tabular
record shapes, a sized `StringFamily` type, a generated `Constant` tag, and an
AOI declaring all three scan flags with their routines. It imports `0/0`,
verifies `0/0`, round-trips canonically, and passes a **generated-vs-exported
construct census** — a check the canonical comparator structurally cannot make,
since it compares two documents that have both already been through Studio. Two
rules came out of it: every generated routine must be reached from its main
routine, or Studio warns about dead code; and every attribute must be stated,
because an omitted one comes back as Studio's default. **S4 is PASS, and with
it R2 closes.** S15 remains open on the unattended-gate and Ethernet questions.

**R3 then closed offline.** The six logical contracts — registry, manifest,
value envelope, mailbox, repository negotiation and the HostEvents ring — are
frozen at version 1 in
[`Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json`](../../../Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json),
the one artifact a generator, a gateway and a gate all read. Part III's prose
stays normative and `tools/check_ab_contracts.py` fails the build when the two
drift, when a field uses a type this controller does not have, or when a
capacity claims a number without evidence.

S7 then measured the manifest itself. A 43,728-byte manifest at candidate
capacities — 4 roots, 128 modules, 512 fields, 256 localization keys and the
rest — read completely and coherently in **293 ms** at S1's conservative
500-byte connection and **62 ms** at 4000 bytes, with a **~32 ms header-only
poll** in steady state. **One bounded manifest fits; no per-root split is
required.** Reading tables as arrays of UDT rows batches into far fewer round
trips than one monolithic tag, so S1's 4 KiB fragmented figure is a worst case
for that access pattern rather than the rate a manifest reader sees. Eight of
the nine `FRK_MAX_*` capacities are now resolved at the sizes actually
measured; `FRK_MAX_MAILBOX_ARGUMENTS` remains S9's.

The default controller communication path is EtherNet/IP explicit messaging
(CIP symbolic access) through the Fraktal gateway. OPC UA is an alternative
projection, not a prerequisite for base Fraktal/AB conformance. S1 selected
hash-pinned pylogix `1.1.5` as the initial private PLC-facing adapter; it shall
sit behind a versioned, allow-listed gateway boundary and shall not expose an
arbitrary CIP `Message()` surface to the HMI.

Start with:

- [`Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md`](../../../Specification/AllenBradley/AB_ENGINEERING_INTERFACE_AND_TOOL_CATALOG.md)
  for the complete status-marked inventory of every Studio 5000, FactoryTalk
  Linx, SDK, EtherNet/IP, Python, UI Automation, and repository tool interface
  used or discovered, plus the unfinished S11 checkpoint;
- [`Specification/AllenBradley/AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md`](../../../Specification/AllenBradley/AB_ENGINEERING_WORKSTATION_ACCESS_RUNBOOK.md)
  for the verified fresh-chat paths, tools, commands, and safety boundaries used
  to access Studio 5000, FactoryTalk Linx, and the isolated PLC;
- [`Specification/AllenBradley/AB_STUDIO5000_IMPLEMENTATION_HANDOVER_PROMPT.md`](../../../Specification/AllenBradley/AB_STUDIO5000_IMPLEMENTATION_HANDOVER_PROMPT.md)
  on the Windows 10 Studio 5000 workstation;
- [`Specification/AllenBradley/Evidence/AB_R0_CORE_AUTHORITY_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_R0_CORE_AUTHORITY_EVIDENCE.md)
  for the completed R0 decision record;
- [`Specification/AllenBradley/Evidence/AB_R1_PLATFORM_BASELINE_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_R1_PLATFORM_BASELINE_EVIDENCE.md)
  for the completed platform baseline;
- [`Specification/AllenBradley/Evidence/AB_S1_CIP_DATA_PATH_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S1_CIP_DATA_PATH_EVIDENCE.md)
  for the completed S1 CIP data/time/transport evidence and initial adapter
  decision;
- [`Specification/AllenBradley/Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S2_AOI_PARAMETER_EVIDENCE.md)
  for the completed nested-AOI, InOut/access, target-limit, and signature
  upgrade evidence;
- [`Specification/AllenBradley/Evidence/AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S11_SEQUENCE_EXECUTION_EVIDENCE.md)
  for the completed sequence-execution, scan-ordering, one-scan-latency,
  simultaneous-branch, `SFR` re-entry, and ST/SFC parity evidence, plus the
  native-SFC chart fidelity result;
- [`Specification/AllenBradley/Evidence/AB_S12_TYPE_MAP_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S12_TYPE_MAP_EVIDENCE.md)
  for the completed type-acceptance matrix, the measured CIP UDT layout and
  stride, and the overflow/NaN/string/array/duration rules that bind generated
  code;
- [`Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md`](../../../Specification/AllenBradley/Evidence/AB_S12_V38_STUDIO_EXPLORATORY_2026-08-29.md)
  for the explicitly provisional Studio-only 5380/v38 declaration/use matrix
  and the acceptance work still blocked by the SDK licence;
- [`Specification/AllenBradley/Evidence/AB_S7_MANIFEST_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S7_MANIFEST_EVIDENCE.md)
  for the measured manifest size, per-table read cost at two connection sizes,
  coherence and revision-change results, and the resolved capacities;
- [`Specification/AllenBradley/Evidence/AB_S9_COHERENCE_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S9_COHERENCE_EVIDENCE.md)
  for the snapshot-coherence result: the guard never accepted a torn read at any
  mutation rate, tearing was directly observed unguarded, and retry converges
  only when the mutation interval exceeds the guarded read window;
- [`Specification/AllenBradley/Evidence/AB_S8_SECURITY_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S8_SECURITY_EVIDENCE.md)
  for the measured absence of CIP Security on this controller and the allow-list
  audit;
- [`Specification/AllenBradley/Evidence/AB_S8_S9_DECISION_RECORD.md`](../../../Specification/AllenBradley/Evidence/AB_S8_S9_DECISION_RECORD.md)
  for the settled security and repository/mailbox decisions — read this before
  starting a new AB project, because it fixes the read-only default, the write
  switch, and the recommended v37+ baseline;
- [`Specification/AllenBradley/Evidence/AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md)
  for the two declarations those decisions deferred: the bench's zone/conduit
  layout with a declared **SL-T 1 / SL-C 0** (and why SL 2 is unreachable on this
  family rather than exceptable), and the reference station's tier poll periods,
  freshness thresholds, reader budget and manifest-mutation convergence limit;
- [`Specification/AllenBradley/Evidence/AB_S16_COMMAND_HANDSHAKE_DECLARATION_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S16_COMMAND_HANDSHAKE_DECLARATION_2026-09-06.md)
  for the S16 declaration: the Core §6.1 handshake and §6.2 mode chain fit one
  context UDT and two AOIs with no runtime base structure invented, which is the
  finding that lets the spike proceed. It carries the import package and the
  nine-phase execution matrix for the licensed v33 workstation, and it records
  the Core §6.1 ambiguity it had to resolve — whether a HELD command may time
  out — as something Phase 3 must settle rather than let each binding guess;
- [`Specification/AllenBradley/Evidence/AB_S16_EXECUTION_EVIDENCE_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S16_EXECUTION_EVIDENCE_2026-09-06.md)
  for that package executed on the licensed v33 bench: the real generated L5X
  hash the declaration deliberately withheld, SDK import `0/0`, Studio v33
  Verify `0/0`, an identical canonical round trip, and all nine matrix phases
  passing identically on three consecutive runs. It also records why the first
  runs were not evidence — the executor assembled each observation from 25
  separate reads of a fixture mutating every 10 ms, so phases passed on one run
  and failed on the next until the context was read in a single request — and
  that two automated download attempts crashed Studio v33 with two different
  faults and no root cause, leaving the successful download a manual one;
- [`Specification/AllenBradley/Evidence/AB_R4_REGENERATION_GATE_EVIDENCE_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R4_REGENERATION_GATE_EVIDENCE_2026-09-06.md)
  for **R4**: a fresh clone regenerating every fixture from an SDK seed and
  clearing import, canonical round trip, census and Studio v33 Verify at `0/0`
  on all nine legs — including the proof that canonical form is stable across
  seeds, which is what makes every hash in every earlier record checkable. It
  itemises what still cannot run unattended rather than rounding up;
- [`Specification/AllenBradley/Evidence/AB_R5_REFERENCE_SUITE_EVIDENCE_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R5_REFERENCE_SUITE_EVIDENCE_2026-09-06.md)
  for **R5**: the disposable reference suite — two reference types with the
  module type instantiated twice — executed on the named bench for nine
  machine-readable rows, all passing on three consecutive runs with the
  controller's own cross-talk counter at zero. It records why the CI path is
  named isolated hardware rather than Echo, and why the download step is an
  authorized manual operation;
- [`Specification/AllenBradley/Evidence/AB_R6_SECURITY_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_R6_SECURITY_EVIDENCE.md)
  for **R6**: the zone/conduit layout and declared Security Level, the External
  Access allow-list audit actually run against both downloaded fixtures, the
  three-state client identity model, secret handling, and the update lifecycle
  — with CIP Security, SL 2 and writes each named as **not** claimed;
- [`Specification/AllenBradley/Evidence/AB_LADDER_EXECUTION_PARITY_2026-09-07.md`](../../../Specification/AllenBradley/Evidence/AB_LADDER_EXECUTION_PARITY_2026-09-07.md)
  for the three-form press result and **the first executing ladder sequence on
  this bench** - S4 proved RLL round-trips, never that one runs. It carries the
  trace comparison, the two Logix constraints the graph was *not* bent to fit,
  and the defect only hardware could find: a chart whose JSR/SFR wrapper fired
  on a level its own first step kept true, so it reset itself every scan and
  never advanced. It also records three faults in the measurement itself, and
  why the trace window is now closed by the machine rather than by the observer;
- [`Specification/AllenBradley/Evidence/AB_PHASE4_RUNTIME_BASE_AND_PRESS_DEMO_2026-09-07.md`](../../../Specification/AllenBradley/Evidence/AB_PHASE4_RUNTIME_BASE_AND_PRESS_DEMO_2026-09-07.md)
  for **Phase 4**: what the generator emits, the step-graph comparison against
  the TwinCAT press demo with its two behavioural divergences named rather than
  absorbed, the fifteen-row bench matrix, and the four defects found on the way
  — including the one only hardware could find, where adopting a child's fault
  never released it and pinned the module in a state nothing could clear;
- [`Specification/AllenBradley/Evidence/AB_S9_RECONNECT_QUALITY_TIMESTAMP_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_S9_RECONNECT_QUALITY_TIMESTAMP_2026-09-06.md)
  for the measured reconnect budget, the two distinct bad-path quality codes and
  what each obliges a reader to do, and why a value's timestamp is the gateway's
  read time carrying `TimeSynchronized = FALSE`; it also records the wall-clock
  read the S1 fixture guard correctly refused rather than being widened;
- [`Specification/AllenBradley/Evidence/AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](../../../Specification/AllenBradley/Evidence/AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md)
  for the second engineering PC surveyed on 2026-09-06 — **read it before
  planning any v33 or SDK work on a new machine**, because that PC has Studio
  v37/v38 with no v33, SDK `2.01.974` rather than 2.02, no .NET SDK, and no
  issued `LDSDK.EXE` activation;
- [`Specification/AllenBradley/AB_R3_FROZEN_CONTRACTS.md`](../../../Specification/AllenBradley/AB_R3_FROZEN_CONTRACTS.md)
  and [`Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json`](../../../Specification/AllenBradley/AB_FROZEN_CONTRACTS_V1.json)
  for the frozen version-1 contracts, what is deliberately still a hole, and
  which spike owns each one;
- [`Specification/AllenBradley/Evidence/AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_S4_S15_OFFLINE_ROUNDTRIP_EVIDENCE.md)
  for the current disposable SDK Build and canonical L5X result;
- [`Specification/AllenBradley/Evidence/AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md`](../../../Specification/AllenBradley/Evidence/AB_PHASE0_PHYSICAL_EXECUTION_EVIDENCE.md)
  for the authorized v33 fixture generation, Studio Verify/download, physical
  EtherNet/IP execution matrix, access-control results, and rollback state; and
- [`Specification/AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md`](../../../Specification/AllenBradley/ALLEN_BRADLEY_PORT_PLAN.md)
  plus [`Specification/AllenBradley/AB_IMPLEMENTATION_PLAN.md`](../../../Specification/AllenBradley/AB_IMPLEMENTATION_PLAN.md)
  for spike and phase order.

Pre-gate tooling:

- [`tools/Fraktal.Ab.OfflineProbe`](tools/Fraktal.Ab.OfflineProbe/README.md)
  opens disposable projects through the installed Logix Designer SDK, reports
  the saved communication path, and can save a new disposable ACD or L5X while
  proving that the input was unchanged. Its `--create-seed` mode creates the
  empty v33 controller skeleton every generator consumes, so the whole chain
  regenerates from a clean checkout. It contains no controller-changing
  operation.
- [`tools/fraktal_ab_eip_probe.py`](tools/fraktal_ab_eip_probe.py) performs a
  targeted read-only EtherNet/IP identity and TCP/IP Interface Object probe. It
  exposes only `ListIdentity` and fixed `Get_Attribute_Single` reads for the
  TCP/IP Interface and Time Sync objects, can require the expected controller
  serial, and reports bounded identity latency.
- [`tools/fraktal_ab_symbolic_read_probe.py`](tools/fraktal_ab_symbolic_read_probe.py)
  performs explicitly named Logix symbolic reads and reports only status, value
  shape, and timing. Values are always redacted; the pinned temporary-client
  dependency is in [`tools/requirements-phase0.txt`](tools/requirements-phase0.txt).
- [`tools/fraktal_ab_phase0_fixture.py`](tools/fraktal_ab_phase0_fixture.py)
  transforms only a fresh empty v33 `1769-L24ER-QB1B` full-project L5X into the
  disposable memory-only execution fixture. It refuses overwrite, inhibits the
  embedded I/O module, disables task output updates, and rejects physical-I/O
  operands.
- [`tools/fraktal_ab_phase0_execute.py`](tools/fraktal_ab_phase0_execute.py)
  is the fixed physical execution vector. It requires the expected serial and an
  explicit arm flag, fingerprints the exact fixture, exposes no arbitrary tag or
  value input, and cleans every writable fixture input before returning.
- [`tools/fraktal_ab_transport_budget_probe.py`](tools/fraktal_ab_transport_budget_probe.py)
  is a fixed, read-only large-array/reconnect/timeout/concurrency probe. It caps
  every workload, requires the expected serial and fixture fingerprint, closes
  every client, and redacts values.
- [`tools/fraktal_ab_time_probe.py`](tools/fraktal_ab_time_probe.py) reads the
  controller wall clock by default. Its only state-changing path requires
  `--set-to-host`, exact serial and fixture checks, and can invoke only
  `SetPLCTime(dst=0)`. It recognizes only the exact Phase 0 data or S2 nested-AOI
  fixture fingerprints.
- [`tools/fraktal_ab_s2_fixture.py`](tools/fraktal_ab_s2_fixture.py) and
  [`tools/fraktal_ab_s2_execute.py`](tools/fraktal_ab_s2_execute.py) generate and
  execute the exact memory-only nested-AOI/access fixture. The execution tool
  exposes no arbitrary tag/value path and cleans its two writable inputs.
- [`tools/fraktal_ab_s2_signature_variant.py`](tools/fraktal_ab_s2_signature_variant.py)
  and [`tools/fraktal_ab_s2_inout_limit_fixture.py`](tools/fraktal_ab_s2_inout_limit_fixture.py)
  generate the offline-only AOI upgrade and 64/65 InOut compiler cases.
- [`tools/fraktal_ab_s11_fixture.py`](tools/fraktal_ab_s11_fixture.py) generates
  the memory-only sequence-execution fixture, emitting the ST reference form and
  the program-owned native SFC chart plus its JSR/SFR wrapper from one graph
  declaration, and declaring the three required controller SFC settings.
- [`tools/fraktal_ab_s11_execute.py`](tools/fraktal_ab_s11_execute.py) is the
  fixed S11 execution vector. It requires the exact serial, fixture fingerprint
  and arm flag, writes only `FRK_S11_Command` and `FRK_S11_ResetRequest`, drives
  one run plus one `SFR` re-entry run, and restores both inputs.
- [`tools/fraktal_ab_s16_fixture.py`](tools/fraktal_ab_s16_fixture.py) generates
  the memory-only command-handshake fixture: one `DINT`-only context UDT and two
  AOIs — a module carrying the Core §6.1 handshake over a simulated plant, and a
  mode owner running an AUTO step chain and a MANUAL behavior over it. A test
  fails the build if the fixture grows a recipe, manifest, registry, mailbox or
  any other runtime-base structure; fixtures stay disposable by construction.
- [`tools/fraktal_ab_s16_execute.py`](tools/fraktal_ab_s16_execute.py) is the
  fixed S16 nine-phase vector. It requires the exact serial, fixture fingerprint
  and arm flag, writes only the five named command tags, restores all five in a
  `finally` block, and fails closed — a held condition that raises `Error`, a
  broken call order, or a command/result latency other than one scan each fail
  the run rather than being reported as a pass. It reads the whole context in
  **one** request and unpacks it against the declared member layout: the fixture
  mutates every 10 ms, so a per-member sweep spans tens of scans and reports a
  state the controller never held — the tearing S9 measured, and the reason a
  phase could pass on one run and fail on the next with nothing changed.
- [`tools/fraktal_ab_declaration.py`](tools/fraktal_ab_declaration.py) is the
  declaration: the committed source an application is emitted from, and the
  rules that refuse a bad one. Each S16 finding is a rule here only because it
  can reject something - unnamed held reasons, timeouts that are not whole task
  scans, a ParCfg record that does not lead with `SchemaVersion`, a condition on
  an undeclared input, a transition to a step that does not exist.
- [`tools/fraktal_ab_generate.py`](tools/fraktal_ab_generate.py) turns a
  declaration into contract UDTs, one module AOI per declared type, the mode
  owner, the routine and the L5X. It asserts at emit time that the task it
  writes carries the declared period the millisecond timeouts were converted
  from, that no public UDT carries a `BOOL`, and that nothing it emitted names a
  physical I/O operand.
- [`tools/fraktal_ab_manifest.py`](tools/fraktal_ab_manifest.py) emits the
  controller-resident manifest from that same declaration, so a client can
  discover the station from the controller rather than from an L5X on disk. It
  describes the declared graph **once, rendition-agnostic**: the field list comes
  from `publishable_tags`, so the rendition selector and any tag that exists only
  because of how one rendition is implemented are absent by construction, and
  declaring AUTO in one language or three produces the identical manifest. Two
  things it learned the hard way are enforced rather than remembered: Logix
  stores an ASCII string only when it is quoted and `$`-escaped, and a key that
  does not fit the published string fails the build instead of being truncated
  into a name it shares with another path.
- [`tools/fraktal_ab_manifest_read.py`](tools/fraktal_ab_manifest_read.py) reads
  the manifest back off a controller and requires every published row to equal
  the declaration it was generated from. It is read-only by construction - there
  is no write path in the file - and its serial guard is required rather than
  optional. It reads array tags with an explicit element count, because an array
  read without one returns row zero and **succeeds**: the first bench run took
  the manifest apart in 526 requests and 1.5 seconds before that was noticed,
  and it was a defect here, not a controller limit. The run records which path
  each table took, so a fallback announces itself rather than costing 500 quiet
  requests.
- [`tools/fraktal_ab_projection.py`](tools/fraktal_ab_projection.py) projects a
  controller into the **transport-neutral snapshot document the HMI's mapper
  already consumes** - a flat `{browsePath: value}` map in which a module is
  anything publishing `Status/Name` and `Status/ModuleType`, with parentage from
  the dotted identity. The generic HMI therefore needs no AB screens and no AB
  repository. It is fail-closed on Core 3.10 grounds: an invalid, truncated or
  disagreeing manifest refuses the whole projection, because a half-drawn plant
  is a worse answer than a refusal. What this binding cannot publish is listed in
  `absent` with a reason rather than left out, since the mapper coerces a missing
  key into a default and silence would render as data.
- [`tools/fraktal_ab_press_demo.py`](tools/fraktal_ab_press_demo.py) is the press
  demo declaration - the first application, mirroring the TwinCAT oracle's
  observable behaviour with a simulated plant in tags and no control power.
- [`tools/fraktal_ab_press_execute.py`](tools/fraktal_ab_press_execute.py) is its
  fixed fifteen-row harness, reading each structure in one request.
- [`tools/fraktal_ab_rendition_gate.py`](tools/fraktal_ab_rendition_gate.py) reads
  every emitted rendition **back** out of the L5X and recovers its step set and
  transition set in that rendition's own language - a `CASE` for ST, `EQU`
  rung-ins and `MOV`s for ladder, steps and directed links for a chart - then
  requires all of them to equal the declaration. A rendition that cannot be
  parsed back fails the build: silence is not parity.
- [`tools/fraktal_ab_press_parity.py`](tools/fraktal_ab_press_parity.py) walks the
  AUTO graph on the bench in each rendition and requires identical traces. It
  closes its measurement window with the machine rather than the observer -
  withdrawing the start condition once the chain has passed the start step, so
  every rendition parks on the same declared step whatever its speed - because a
  window defined by an observer's reaction time would make a parity claim depend
  on which language happened to be faster.
- [`tools/fraktal_ab_reference_suite.py`](tools/fraktal_ab_reference_suite.py)
  generates the **disposable reference suite** for R5. It is gate tooling, not
  the production module library, and the same scope fence that keeps the S16
  fixture disposable guards it. It promotes the handshake module and the mode
  owner to the binding's first two reference types — importing the declaration
  machinery from the S16 generator rather than copying it — and instantiates the
  module type **twice** over independent contexts, with an on-controller
  cross-talk counter. That second instance is what AB §5.7's G-GENERATED
  argument needs: an extension argument never exercised on a second instance is
  an assertion.
- [`tools/fraktal_ab_reference_execute.py`](tools/fraktal_ab_reference_execute.py)
  is the R5 harness. Same guards as the S16 vector — exact serial, fixture
  fingerprint, explicit arm flag, six-tag write surface restored in a `finally`
  block — and it emits one row per test plus the five summary fields AB §5.7
  names, so the output converts to JUnit the way TC3's does. It reads each
  context in a single request.
- [`tools/fraktal_ab_s12_type_probe.py`](tools/fraktal_ab_s12_type_probe.py)
  emits one minimal project per candidate Logix type, twice — declaration alone
  and declaration plus one operation — so a failure names exactly one type and
  separates an unknown type from an uncompilable expression. Its default
  `v33-5370` profile is the accepted 28-case Phase 0 baseline. The explicit
  `v38-5380-exploratory` profile targets `5069-L310ER` revision 38, remains
  machine-labeled `exploratory-not-accepted`, and adds the four typed-literal and
  matched-operand duration discriminator cases from the Studio-only exploration:
  `python tools/fraktal_ab_s12_type_probe.py <v38-seed.L5X> <output-directory> --profile v38-5380-exploratory`.
- [`tools/fraktal_ab_s12_fixture.py`](tools/fraktal_ab_s12_fixture.py) and
  [`tools/fraktal_ab_s12_execute.py`](tools/fraktal_ab_s12_execute.py) generate
  and execute the memory-only type-map fixture. The controller copies its own
  public UDT, and two adjacent instances of it, into `SINT` arrays so member
  offsets and the padded stride are measured rather than assumed.
- [`tools/fraktal_ab_s9_coherence_fixture.py`](tools/fraktal_ab_s9_coherence_fixture.py)
  and [`tools/fraktal_ab_s9_execute.py`](tools/fraktal_ab_s9_execute.py) provoke
  snapshot tearing and measure whether the coherence guard catches it. The
  vector is ordered so a pass cannot be vacuous: it first shows the guard does
  not reject a frozen controller, then shows unguarded reads genuinely tear, and
  only then sweeps the mutation rate.
- [`tools/fraktal_ab_security_probe.py`](tools/fraktal_ab_security_probe.py)
  asks the controller whether it implements the three CIP Security object
  classes. Fixed classes, read-only, no write path. On the Phase 0 controller
  all three answered `0x05` — a positive absence, which is why that hardware
  runs the legacy zone-and-conduit posture.
- [`tools/fraktal_ab_access_audit.py`](tools/fraktal_ab_access_audit.py) audits
  a project's External Access allow-list offline: declared mailboxes
  `Read/Write`, declared public data `Read Only`, everything else `None`. It
  infers nothing from a tag name and does not treat an omitted attribute as
  `None`, so an incomplete invocation fails loudly instead of approving a
  project by default.
- [`tools/fraktal_ab_s7_manifest_fixture.py`](tools/fraktal_ab_s7_manifest_fixture.py)
  and [`tools/fraktal_ab_s7_execute.py`](tools/fraktal_ab_s7_execute.py)
  materialise the frozen manifest contract as real Logix types at parameterised
  capacities, then measure cold read cost, per-table cost, header-poll cost,
  snapshot coherence and revision-change detection. The generator refuses a
  manifest too large to download, since one that will not download measures
  nothing.
- [`tools/fraktal_ab_s4_matrix_fixture.py`](tools/fraktal_ab_s4_matrix_fixture.py)
  generates the representative construct matrix: both task types with their
  schedules, ST/RLL/SFC in one program, nested and tabular records, a sized
  string type, a generated constant, and the AOI scan routines.
- [`tools/fraktal_ab_l5x_inventory.py`](tools/fraktal_ab_l5x_inventory.py)
  censuses the constructs in a full-project L5X and compares two documents. It
  answers the question the canonical comparator cannot: whether a construct
  survived the *first* import, by comparing the generated declaration against
  the export it produced. An absent attribute is reported rather than treated
  as its default, because Studio writes the default and the difference would
  otherwise resurface later as apparent drift.
- [`tools/fraktal_ab_phase0_gate.py`](tools/fraktal_ab_phase0_gate.py) is the R4
  regeneration gate: it creates the empty v33 seed through the SDK, regenerates
  every fixture from it, and requires a clean import summary, a canonical round
  trip and a construct census for each, plus ID-independent chart equality where
  a chart exists. Studio Verify is opt-in with `--verify` because it needs a
  logged-in desktop session.
- [`tools/fraktal_ab_sfc_roundtrip_compare.py`](tools/fraktal_ab_sfc_roundtrip_compare.py)
  compares the executable SFC content of two L5X documents independently of
  element IDs and sibling order — steps, action qualifiers and bodies,
  transition conditions, branch type/flow, link topology and the controller SFC
  settings — so a generated declaration can be checked against the Studio
  export it produced. It fails closed rather than claiming an unmade comparison.
- [`tools/fraktal_ab_l5x_compare.py`](tools/fraktal_ab_l5x_compare.py) compares
  two full-project L5X exports after excluding only Rockwell's three known
  volatile project/export timestamps, then reports raw and canonical SHA-256
  hashes. Every executable and structural field remains in scope.
- [`tools/fraktal_ab_target_binding_compare.py`](tools/fraktal_ab_target_binding_compare.py)
  separately accepts only the exact serial/firmware-minor stamps introduced by
  a physical download and still requires every other canonical field to match.
- [`tools/fraktal_ab_sdk_log_gate.py`](tools/fraktal_ab_sdk_log_gate.py) turns
  SDK console events into a machine result. It can require named successful
  operations and rejects any SDK error event or non-zero import warning/error
  summary; an SDK process exit code alone is not an import gate.
- [`tools/fraktal_ab_studio_verify.ps1`](tools/fraktal_ab_studio_verify.ps1)
  opens one disposable ACD in the requested Studio revision, invokes offline
  **Verify Controller**, reads Error List counts/details through UI Automation,
  closes without saving, and proves the ACD hash stayed unchanged. It refuses
  repository-contained ACDs and any pre-existing Studio session.

Do not hand-author production L5X. Generated artifacts must be imported,
verified, exported, and compared through Studio 5000, with the exact software,
firmware, controller, and communication baseline recorded as evidence.
