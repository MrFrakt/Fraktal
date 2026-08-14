# Fraktal/AB

This tree is reserved for the Allen-Bradley Logix binding. The authoritative
implementation specification is
[`Specification/Fraktal_AB_Part_III.md`](../../../Specification/Fraktal_AB_Part_III.md).

Current status: **R0-R3 PASS; R4-R6 OPEN**. No production AB runtime or module
library is authorized until every readiness gate in Part III records PASS.
Before that point, this tree may contain only disposable Phase 0 fixtures and
the evidence, generator, lint, or host tooling needed to close the gates.

The current Phase 0 workstation target is `192.168.100.89` from host adapter
`192.168.100.99/24`. FactoryTalk Linx 6.50 successfully browses it through the
point-to-point alias `Fraktal_AB`; direct CIP identity and symbolic reads also
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
generated code must test NaN by bit pattern. **S12 is PASS.** The controller
retains the clean S12 fixture in Remote Run.

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
- [`tools/fraktal_ab_s12_type_probe.py`](tools/fraktal_ab_s12_type_probe.py)
  emits one minimal project per candidate Logix type, twice — declaration alone
  and declaration plus one operation — so a failure names exactly one type and
  separates an unknown type from an uncompilable expression.
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
