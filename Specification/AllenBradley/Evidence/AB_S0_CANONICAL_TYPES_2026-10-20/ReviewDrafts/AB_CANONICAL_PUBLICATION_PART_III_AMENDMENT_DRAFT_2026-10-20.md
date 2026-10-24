# Part III canonical publication amendment — owner review draft

2026-10-20. **Not effective.** This is proposed replacement text for the named
clauses, based on [S0 evidence](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md)
and [the V2 draft](AB_FROZEN_CONTRACTS_V2.json). Part III and frozen contracts
V1 remain authoritative for the shipping implementation. Approval settles the
target contract; it does not establish implementation or runtime conformance.
S1–S7 retain the implementation plan's gates.

## AB §1, §2.1 and §4.1 — reference profile

The reference profile is a CIP Security-capable CompactLogix 5380 or
ControlLogix 5580 at firmware v37 or above. Each different family/revision
requires the applicable compiler, type-map, transport and runtime qualification.
The development bench is FactoryTalk Logix Echo emulating a 1756-L81E at
38.011; simulation evidence is identified as such and grants no physical fit,
retention, I/O or CIP Security acceptance.

The 1769-L24ER-QB1B/v33 is retired as a reference target. Its dated evidence
and V1 contract remain history at their recorded scope. A future constrained
profile uses this same canonical architecture and declares its reductions;
it does not introduce a station-specific projection architecture.

## AB §3.8 — type map V2

The PLC publishes the logical Core contract itself. Type bindings are defined
by frozen contracts V2; the manifest supplies logical information absent from
the controller's native type system. A client never infers logical type or
array bounds from a member's name or a station declaration.

- BOOL members are native. A reader honors template offsets and bit metadata.
  Native BOOL arrays may be described as DWORD storage; the manifest supplies
  their logical Boolean type, lower bound and element count. Only that logical
  extent enters the canonical snapshot.
- SINT, INT, DINT, REAL, LINT and LREAL are native. Core enum ordinals remain
  generated DINT constants. Int64 transport uses exact integers/decimal
  strings and never passes through a float. Generation preserves the declared
  floating-point precision; an untyped REAL literal widened into LREAL is not
  a conforming full-precision initializer. The full-precision initializer form
  remains an explicit acceptance gate after S0's finding.
- **D6: Core TIME binds to DINT milliseconds**, with the manifest logical type
  DURATION and wire ordinal 3. Its signed 32-bit range and millisecond units
  match Core directly. Native TIME32 has microsecond units and insufficient
  range for this contract; native TIME has 64-bit microseconds. Neither is
  substituted for the published DINT representation. An internal native time
  value is converted and range-checked by its owning provider before publication.
- **D7: Core timestamps bind to native LDT**, 64-bit Unix nanoseconds, mapped
  to UTC DateTime; zero retains Core's unset meaning. Snapshot encoding is an
  ISO UTC string with up to nine fractional digits, or numeric zero for unset.
  Conversion from a microsecond clock is owned once by its provider. A LINT
  supplied to the time-type assignment is a nanosecond value: S0 measured a
  microsecond LINT assigned to DT being divided by 1,000, while nanoseconds
  assigned to LDT were preserved exactly.
- Strings retain the owning Core/application byte capacities. A StringFamily
  is recognized from its LEN DINT / DATA SINT[n] template shape. LEN counts
  UTF-8 bytes. Generation rejects an over-width literal; acquisition rejects
  invalid length or encoding rather than truncating it.

Canonical array indices equal the declared Core indices. Logix physical
storage starts at zero; the manifest supplies logical lower bound and element
count. Packed Boolean bits are expanded before that bound is applied.
The five V1 corrections are exactly ActiveSteps, ModePolicy,
SupportedModesPublished, SupportedRunStylesPublished and Access.Policy.Required,
all changing from lower bound 1 to 0. Other arrays keep their Core bounds.

The native units and LINT conversion rule agree with Rockwell's
[time and date type documentation](https://www.rockwellautomation.com/en-us/docs/studio-5000-logix-designer/37-01/contents-ditamap/instruction-set/time-and-date-data-types.html).
The D6/D7 selections above are binding decisions from the measurements, not a
claim that Rockwell prescribes those Fraktal representations.

## AB §3.10 — canonical exposure and self-description

Each deployed root is one controller-scope tag named exactly as its local
browse name. Its record declares the standard Status contract; children are
records named exactly as their local instance/schematic names. Status.Name
carries the qualified Fraktal identity. Infrastructure, private state and
reference aliases do not create additional roots.

Discovery uses the controller's Symbol object (0x6B), Template object (0x6C)
and validated PLC-resident manifest. A module is recognized through its Status
contract, as on TC3 and TIA. The structure flag and complete 12-bit template
handle govern references; a handle's low byte matching an atomic code does not
make the referenced record an atomic type.

The new physical manifest major is 6. It describes canonical paths and carries
logical types and logical array bounds/extents derived from the same
declarations as the UDTs. Physical word count cannot replace logical Boolean
element count. Static metadata is cached by the validated manifest content hash
and configuration revision; existing coherence, invalid-manifest and
incompatible-major refusals remain.

Published data is effectively Read Only, HmiRequest alone is effectively
Read/Write, and private storage has access None. The generated access audit
proves the effective leaf policy. The physical tag/member encoding and
discoverable access metadata remain the additional S0 probe's gate: this text
does not assume that a read-only tag can expose a writable descendant.

The client decodes the PLC-owned contract. There is no runtime station
declaration, client-owned derivation, hard-coded station tree, or station HMI
screen. During S2–S3, old contexts coexist only for migration/equivalence; S6
removes them after all harnesses and adapters have moved.

## AB §11.1 — desktop and gateway topology (D9)

One generic CipSessionClient in fraktal_opcua_client emits
fraktal.opcua.snapshot.v1. The desktop selects it through cip://. The Dart
gateway uses the same client for Web clients, as it does for ADS and S7 Web API.
The PLC's canonical tree and manifest are the sole runtime description.

Direct writes require a commissioned CIP Security session proved on capable
hardware. Without it, direct CIP is explicitly read-only in the HMI. Echo
implements no CIP Security, so direct desktop acceptance on Echo is read-only.

Commands on the Echo/isolated gateway path use the existing authenticated
wss:// gateway posture, recorded per-deployment write choice, root scope and
PLC mailbox gates. Browser clients do not open raw CIP sockets. Existing
§11.2.1 authenticated-principal, least-privilege and no-anonymous-write rules
remain in force for a write-enabled production deployment.

Every mailbox transaction is serialized. All argument writes must succeed
before a separate Sequence commit. Success requires the matching PLC
acknowledgement and acceptance; timeouts and reconnects never replay a request.
CIP sample receipt time is recorded without inventing device source time or
clock synchronization.

## Approval and implementation boundary

Owner approval is pending. The additional size/fragmentation, root-name and
access probe, full-precision LREAL initializer acceptance, per-surface Capacity
Estimate/native scan measurements, S1–S6 equivalence and S7 physical/security
acceptance remain open. No provisional physical size, access encoding or
manifest capacity is frozen by this draft.
