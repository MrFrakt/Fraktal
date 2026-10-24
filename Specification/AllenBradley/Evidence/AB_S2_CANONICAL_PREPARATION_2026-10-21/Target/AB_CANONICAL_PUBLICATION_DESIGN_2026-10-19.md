# Fraktal/AB canonical publication — one architecture across bindings

Non-normative design note, 2026-10-19, continued 2026-10-20. Status:
**first S0 runtime measurement and restoration completed; D6/D7 selected;
V2 and the Part III amendment are owner-approved target drafts; the S1 oracle exit passes.** The
production generator and HMI have not migrated. Part III stays authoritative
until the stages below pass their gates and amend it. See
[S0 evidence](Evidence/AB_S0_CANONICAL_TYPES_2026-10-20.md).

## Owner decisions

- **Coherent architecture** (2026-10-19): *"having a coherent architecture
  along all implementations is important."* Fraktal/AB shall reach the HMI the
  way TC3 and TIA do. The PLC publishes the canonical Core module tree itself,
  and a **generic** session client discovers it through the controller's own
  symbolic services, with no station knowledge.
- **The L24ER is out** (2026-10-19). The 1769-L24ER/v33 is retired as a
  reference target. Its dated evidence stays as history.
- **Delegated:** the owner asked that the remaining choices be narrowed from
  the specification objectives and the other bindings. They are settled below,
  each with its reference.

Rejected this session, with the reason:

- **Finishing the Dart direct-CIP prototype** (`HMI/lib/data/cip/`) as a
  hand-written port of the Python projection. It keeps two copies of one
  contract (O9) and still needs the station declaration.
- **An HMI-owned gateway sidecar.** It keeps the off-PLC projection and its
  declaration, so station knowledge would live outside the PLC, next to the HMI.

## Where each binding keeps the canonical tree today

| | TC3 (Part II) | TIA (Part IV) | AB today (Part III) |
|---|---|---|---|
| Canonical module tree (`Status : ST_ModuleStatus` …) | Published by the PLC (TF6100 / ADS symbols) | Published by the PLC (instance DBs, Web API / OPC UA) | **Reconstructed off the PLC** by `fraktal_ab_projection.py` |
| Client | Generic (`opc.tcp`, `ads://`) | Generic `WebApiSessionClient` (`s7web://`) | Python gateway with the **station declaration** |
| Station knowledge off the PLC | None | None | The declaration module (steps, config pages, policy …) |
| Desktop HMI | Direct | Through the gateway; direct where OPC UA is licensed | Through the gateway; `cip://` is a 45-field spike |

The AB deviation answered the L24ER's 750 KB memory and the v33 type map.
With the L24ER retired, neither constraint remains.

## Measured facts (local Echo L81E v38, image `6DEC4C1DC2F7F78A`)

Captured read-only on 2026-10-19. The raw capture is
`C:/work/fraktal-ab-echo-20261019/projection_capture_01.json`, SHA-256
`5CA907E6076A02833A5670EF3741CD62ACA626F762F9DD557F1E4B9C2C3BBE0C`.

- **One gateway pass is 50 CIP reads, 126,076 bytes.** Ten are manifest
  reads (74 KB) and forty are state reads (51,524 bytes). An offline replay
  reproduces all **4,437** projected values exactly, so the capture is the
  golden vector for value equivalence.
- **The conversion runs about 4,500 lines of Python across 35 modules.**
- **The manifest describes the generated contexts.** It has 670 `Fields` rows,
  and only **36 of the 4,437 canonical paths** correspond to one of them.
- **Census of the canonical values:**

  | Type | Count |
  |---|---|
  | BOOL | 914 |
  | integer | 2,155 |
  | float | 83 |
  | string | 1,284 |

  Of the strings, 613 are empty, 212 are dictionary keys, 145 are names or
  paths and 314 are data. The longest is 54 characters and the mean is 11.6.
- **Echo serves generic symbolic discovery.** The Symbol object listed 61
  controller tags in 48 ms, and the Template object decoded 50 UDTs with member
  names and types. This is the CIP counterpart of TIA's `PlcProgram.Browse`.
- **Five arrays already differ from TC3.** AB publishes `ActiveSteps`,
  `ModePolicy`, `Required`, `SupportedModesPublished` and
  `SupportedRunStylesPublished` from index 1; TC3 declares them from 0. The
  other 22 published arrays match. The HMI mapper tolerates either base, but
  path identity, and with it layouts and customization bundles, differs.
- **CIP Security** objects `0x5D/0x5E/0x5F` are absent on Echo.
- **The 1756-L81E has 3 MB of user memory** (Rockwell 1756 selection guide).

## Target architecture

1. **The PLC publishes the canonical contract.** Each deployed root is one
   controller-scope tag named exactly as the root's browse name (`Press`). Its
   UDT carries the Core members under their canonical leaf names, with child
   modules as members named as the schematic names them.
   - Published values have effective External Access *Read Only*;
     `HmiRequest` alone is effectively *Read/Write*. Private storage is *None*.
     The supplementary probe confirms a Read Only parent blocks its writable
     child. Ancestors of HmiRequest must be Read/Write, other public branches
     Read Only. None storage stays outside whole-read canonical records.
     The manifest supplies effective member access absent from Template data.
     The R6 allow-list audit enforces the effective policy (Core §3.10(a)).
   - Static text stays a dictionary key resolved by the HMI (HMI_CONTRACT §1).
   - The **manifest remains the self-description service** (Core §3.10.2), now
     describing the canonical fields. It supplies only what Logix types cannot
     say themselves: logical type and logical array lower bound/element count
     (D2, D3, D6), plus effective member access absent from Template data.
     S0 found that native BOOL arrays are described as DWORD
     storage; physical word count is not the declared logical element count.
2. **One generic `CipSessionClient`** lives in `fraktal_opcua_client` beside
   `AdsSessionClient` and `WebApiSessionClient`, selected by `cip://`.
   - It discovers through Symbol + Template plus the manifest. A root is any
     controller tag whose type has a top-level `Status` member (TIA §3.10.1).
   - It reads whole structures, decodes them by template, emits
     `fraktal.opcua.snapshot.v1`, and caches discovery by manifest content hash
     and revision.
   - The **desktop HMI uses it directly**, and the **Dart gateway** uses it for
     Web clients, as with ADS and the Web API.
3. **No station declaration is needed at runtime.** The declaration stays the
   one source the generator turns into the L5X. The Python projection, the
   Python gateway and the Dart spike all retire at S6.

## Decisions

| # | Topic | Decision | Basis |
|---|---|---|---|
| D1 | Target family | A single **reference profile**: CIP Security-capable 5380/5580 class at **v37 or above**. Echo L81E v38 is the development bench. A future smaller family gets a declared reduced profile on **this same** architecture, never a second one. | Owner decision; AGENTS §3a baseline; TIA §1.1 family profiles |
| D2 | Array bounds | The canonical index is the **Core-declared index**, as TC3 and TIA publish it. Logix arrays are physically 0-based, so the manifest states each published array's logical lower bound and element count. The client expands packed BOOL storage before applying canonical index = physical element index + lower bound. The five deviations listed above are corrected. | TC3 Core (21 arrays from 1, 7 from 0); TIA mirrors bounds (`Policy : Array[0..MODE_LAST]`, `Catalog : Array[1..N]`); S0 DWORD storage finding; O9 |
| D3 | BOOL | **Native BOOL members.** The BOOL-free public UDT was a v33 contract rule. | TC3/TIA publish BOOL; v38 exploratory verify 0/0 |
| D4 | Strings | **Core-declared widths** (TC3 uses `STRING(2…255)`, keys 160, set lines 480). One Logix string type per width, `LEN : DINT` + `DATA : SINT[n]`, recognised by shape. UTF-8 bytes with a byte-counted `LEN`. A literal wider than its field is rejected at generation, never truncated at run time. | TIA §3.8.1 reference profile keeps Core widths; O10; S12 byte-counted LEN |
| D5 | Numbers and enums | Enums as `DINT` with generated constants. `INT`/`DINT`/`REAL`/`LREAL`/`LINT` native. 64-bit integers are delivered exactly as Int64, never through a float. LREAL generation retains declared precision: use the qualified `L` suffix in ST or typed Decorated LREAL initial data. Supplementary S0 preserves pi and 1.0000000000000002 exactly; the untyped REAL-rounded control remains a finding. | TIA type map; v38 native build/read-back and S0 runtime bytes |
| D6 | Durations (Core `TIME`) | **DINT milliseconds**, marked DURATION in the manifest; transport **Int32 ms**, wire ordinal 3. It matches Core's width and units directly. Measured TIME32 is 32-bit µs (insufficient range); TIME is 64-bit µs and would require normalization plus wider publication. Native time may remain internal to an owning provider, which converts and range-checks before publishing. | S0 native type codes/units; TC3 `TIME` and TIA `Time` are 32-bit ms; O4/O9 |
| D7 | Timestamps (Core `DT`) | **Native LDT**, 64-bit Unix ns, delivered as **DateTime UTC, zero = unset**. S0 preserved the nanosecond LINT-to-LDT vector exactly; its microsecond LINT-to-DT assignment divided by 1,000. A clock provider converts µs to ns once before assigning LDT. | S0 runtime bytes; TIA S7-1500 `LDT`; Rockwell's LINT-as-LDT conversion rule |
| D8 | Quality and source time | CIP carries no source timestamps; the client stamps read time. | Web API client and current gateway do the same |
| D9 | Writes | **Direct CIP writes only over a commissioned CIP Security policy.** Without it, the direct client is a read-only projection and says so in the HMI. Commands then go through the Dart gateway over `wss://` with an authenticated principal; gateway writes stay a per-deployment recorded decision (Part III §11.2.1). Echo has no CIP Security, so the desktop is read-only direct and commands through the gateway. | Core §11.2 (authenticated principals, integrity, confidentiality; read-only stated explicitly); Core §7.7(d); TC3 OPC UA secure channel; TIA HTTPS web user |

## Cost estimate (to be replaced by Studio Capacity measurements)

- **Published data:** numbers about 12.6 KB, plus strings. Strings take about
  21 KB at their actual maxima, and more at Core widths (D4) because every slot
  is sized. Some existing storage is replaced rather than duplicated: the
  51.5 KB state contexts and the 48.6 KB Localization table.
  - Net growth is estimated at **+20 KB to +150 KB**, against 3 MB.
- **Logic:** derivations move from Python into generated ST, notably OEE
  factors, machine state, condition records, release-report rows and alarm
  presentation. Code size and scan time are **unmeasured** and are gated
  per stage.

## Stages and gates

Each stage carries the same gates:

- generator tests and the AB suite;
- v38 build and read-back on both targets;
- the owner's Studio Capacity Estimate;
- the guarded Echo download;
- the 31 ST/SFC/LD regressions;
- **value equivalence**: the canonical publication read generically equals the
  Python projection for the same controller state, path by path and type by
  type. The only differences allowed are the D2 bound corrections, listed one
  by one.

| Stage | Content | Exit |
|---|---|---|
| S0 | Probe image measuring D2–D7 on Echo over CIP; supplementary size/naming/access questions before S2. First runtime/restore completed; type selections and frozen V2/Part III amendment drafts are recorded. | D6/D7 resolved by measurement and V2 draft approved by the owner |
| S1 | Python reference reader: generic Symbol/Template/manifest discovery into a snapshot (pylogix), compared with the projection | Equal on the published subset |
| S2 | Generator publishes the module tree (`Status` of every module, mode, step) canonically **alongside** the current contexts | Equivalence on Echo for that subset; memory and scan deltas recorded |
| S3 | Remaining surfaces one at a time: Sequence, AlarmLog, Part/HostEvents, Config, OEE/Profiler, Access, Line, Fieldbus | Full 4,437-path equivalence on Echo |
| S4 | Generic Dart `CipSessionClient`; desktop HMI `cip://` uses it, read-only per D9 | Same equivalence from Dart; HMI tests; desktop acceptance on Echo |
| S5 | Dart gateway gains `cip://` for Web clients and commanding | Web and write acceptance through the gateway |
| S6 | Retire the Python projection, the Python gateway and the Dart spike | Docs and gates updated; nothing reads the old contexts |
| S7 | CIP Security on a capable physical controller; direct writes enabled per D9 | Part III §11.2.1 evidence |

## Documents that change when the stages land

- **Part III:** §3.8 type map, §3.10 exposure and §11 transport, plus the
  L24ER retirement.
- **Frozen contracts:** `AB_FROZEN_CONTRACTS_V1.json` becomes V2; the manifest
  major version steps.
- **`OPCUA_TRANSPORT.md`:** a CIP transport section.
- **`AGENTS.md`:** §3a and §5.
- **The AB README and the new-station guide.**
- **`HMI_CONTRACT.md`:** unchanged apart from AB adopting TC3's bounds for
  the five D2 arrays.

## Next step

The owner approved [frozen contracts V2](AB_FROZEN_CONTRACTS_V2.json) and the
[Part III amendment draft](AB_CANONICAL_PUBLICATION_PART_III_AMENDMENT_DRAFT_2026-10-20.md).
The first probe was measured and genealogy restored with 31/31 regressions.
Approval recorded on 2026-10-20: “Approve drafts and proceed to S1”. The
target approval does not activate V2 in the shipping implementation. The S1
reference-oracle exit passes; see [S1 evidence](Evidence/AB_S1_CANONICAL_READER_2026-10-20.md)
for its scope and the S2 physical-manifest/paired-live boundary. The supplementary size/naming/access and full-precision
LREAL cases need a newly prepared/gated probe and separate current download
authorization; they are not covered by the completed first session.

2026-10-21 continuation: the owner authorized the guarded supplementary
session and supplied the exact-artifact Capacity screenshot (69%, in blocks).
The session completed; see [runtime evidence](Evidence/AB_S0_SUPPLEMENTARY_RUNTIME_2026-10-21.md).
A 2 MiB record reads exactly using fragmented reads at 500/4000-byte connection
settings; a root named Press is discoverable; both precise LREAL initializer
forms pass. The effective parent/member access vector passes and all writes
are restored. Symbol attribute 10 distinguishes top-level RO/RW on this Echo,
while the captured Template metadata does not distinguish member permissions.
This requires a PLC-manifest member-access annotation, without station facts
in a client. The target drafts now record these measured implementation rules.
Genealogy is restored with five documents, 31/31 regressions and passing final
checks. S2 is the next implementation stage; its image needs its own compiler,
equivalence, Capacity, scan and current controller-operation gates.
