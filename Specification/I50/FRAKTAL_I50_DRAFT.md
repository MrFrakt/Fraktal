# Fraktal I5.0 — the operations tier (working draft)

*Working draft v0.6, 2026-11-12 (four rounds of owner answers folded in, and two items
checked against the code; see §9 for what is decided and what is open).
**Non-normative.** This is the working set for a future
Part V. Nothing here is a `shall` until it moves to the root of `Specification/`. Proposals
are written in the present tense; decisions are tracked in §9 and open questions in §10.
Section references without a prefix (§3.16, §11.6 …) are to `Fraktal_Core_Part_I.md`.*

---

## 1. Intent

Fraktal Core standardises the controller (ISA-95 levels 0–2) and already projects it
north-bound (§11). This draft defines the tier above it: operations management (level 3 —
MES, traceability, routing, analytics) and the Industry 5.0 capabilities that sit on top.

The European Commission's Industry 5.0 adds three aims to Industry 4.0 connectivity:
**human-centric, sustainable, resilient** [R1]. Read against Fraktal:

| Aim | Already in Core | The operations tier adds |
|---|---|---|
| Human-centric | Every stall and refusal explains itself (§6.9, §7.8); exception-based display; guidance bound to the running step; localized text | Work instructions per route operation, qualification-gated manual work, operator call (andon), an assistant that answers with evidence and never commands |
| Sustainable | Optional utility metering and energy-per-part (§8.14); scrap attributed by reason (§8.11.2) | Energy and CO₂e attributed to the individual part, idle-consumption findings, product-passport export |
| Resilient | Bounded rings with explicit loss flags, no write replay, fail-closed faults, simulation (§2.6), mirrored line config that keeps running stale (§3.8e) | Store-and-forward, a declared MES-offline policy, capability-based alternate routing, configurable database redundancy, central backup of station config |

## 2. Principles carried up from Core

1. **Discovered, not engineered.** The operations tier builds its equipment tree, alarm
   catalogue, KPI sources and station contract from the Self-Description Service (§3.10).
   Adding a station makes it appear in MES and in the portal, as it already does in the HMI.
2. **The PLC stays authoritative for control.** Everything arriving from level 3 is
   untrusted input (§11.6.3). No operations or AI path commands motion, grants a release,
   or bypasses §7.6/§7.7.
3. **One fact, one source.** Raw host events are an immutable, append-only ledger; the
   relational model is a projection that can be rebuilt from it. One data dictionary
   generates the ORM model, migrations, indexes, the analytics semantic layer and the
   schema context given to an LLM.
4. **Production never depends on the cloud.** Local-first, store-and-forward, and an
   explicit per-line policy for an unreachable MES.
5. **Projection, not parallel logic.** A third-party MES, a UNS, AAS and product passports
   are projections of the same model, as PackML and MTP already are (§11.7, §11.8).
6. **Proportional surface (O4).** A small cell runs the whole tier on one box with
   PostgreSQL; nothing forces a cluster on it.
7. **A human decides.** AI output is advice with its evidence attached.

## 3. What the tier can consume today

| Need | Core source | Note |
|---|---|---|
| Part identity, verdict, measurements, genealogy | `ST_PartContext` / `ST_PartResult` (§3.16) | `Parents` carries consumed components |
| Part lifecycle + changeover/tool/material/mode/NOK events | Fixed host-event set, bounded `HostEvents` ring with sequence and `Wrapped` (§11.6) | Checked 2026-11-12: every binding publishes the ring. Only AB has a collector (the gateway host adapter: cursor, loss records, JSONL sink). None was found for TC3 or TIA, and TC3's `I_HostEventSink` has no shipped implementation |
| Carrier / host lookup | `I_PartCarrier`, `CarrierKind = HOST` (§3.16.2) | The right seat for an MES release check, but not as it stands: the read is single-scan and only local carriers were found (§5.1) |
| Model data down | `I_RecipeProvider`, `PrepareRecipe`/`CommitRecipe`, `(ModelCode, RecipeKey)` (§3.8) | Central model-config master is a provider, not new PLC code |
| OEE, counts, machine state, blocked/starved | §8.5.1, §8.11 | Factors carry validity flags |
| Shifts, targets, closed shift records | §8.5.2 (Line profile) | Closing is offered to `I_EventSink` |
| Step and command timing, work vs wait time | §8.11.4 | Same rows on every module of a type |
| Alarms with one reason vocabulary and rationalization | §8.3, §8.8, `reason_rationalization.json` | Alarm catalogue needs no per-site build |
| Health, condition and utility values | §8.12, §8.14 | |
| Process curves | `ST_CurveRecord` (TC3 Modules) | Read on demand |
| Line identity and line config | §3.8e | `I_LineSource` can be served centrally |
| Access levels, audit | §7.7, §8.3 | Local PIN tables today |
| Canonical address | §4.8 | One path for PLC, HMI, MES, UNS |

Three things fall out of the uniform contract at almost no cost and are worth naming as
features: **fleet benchmarking per module type** (every cylinder publishes the same timing
rows, so actuation-time drift is comparable across stations and plants); **config diff per
type** (why does station 3 behave differently from station 4); and **a reject Pareto that
uses the machine's own reason sentences** (§3.16, Annex E).

## 4. Gap analysis — Industry 4.0 features not yet covered

Cost is relative: **Low** = the data is already published and the work is a consumer or a
mapping; **Medium** = a new service or a small contract addition; **High** = a new
subsystem.

| # | Feature | Why it matters | Builds on | Cost |
|---|---|---|---|---|
| G1 | Host-event collector on every transport, with pluggable sinks (database, HTTP, MQTT) | Nothing above the PLC keeps the ring today except the AB JSONL sink. The work is lifting that collector's cursor, validation and sink off the CIP reader it is bound to, so the OPC UA, ADS and S7 transports feed the same code | §11.6.2, gateway host adapter | Low–Medium |
| G2 | UNS publish (MQTT Sparkplug B) from the gateway | §11.9 permits it; no implementation | Gateway snapshot | Low–Medium |
| G3 | ISO 22400 KPI names and the KPIs beyond OEE: first-pass yield, scrap and rework ratio, throughput rate, setup ratio, MTBF/MTTR | Comparable figures across plants; all derivable from published counts, state buckets and the alarm ring [R9] | §8.5, §8.11, §8.3 | Low |
| G4 | Alarm-performance profile owner | §8.10 asks for one named aggregator; the operations tier is its natural home | §8.10 | Low |
| G5 | Capability and SPC evaluation (Cmk/Cpk, control charts) from measurement records | `CAPABILITY` mode exists; nothing evaluates its output | §3.17, `ST_MeasRecord` | Low–Medium |
| G6 | Central backup and versioning of station config sets | Disaster recovery, and the config diff of §3 | §3.8b set documents | Low |
| G7 | Operator call: `OPERATOR_REQUESTED` / `OPERATOR_ARRIVED` host events and response-time KPI | Andon without station code; the decision and signal-tower state already exist | §6.11, §8.13 | Low |
| G8 | Energy and utility consumption attributed to the part | Input to product carbon footprint and passports | §8.14, §3.16 | Low on the PLC, Medium above |
| G9 | Software inventory and SBOM per station and for the gateway/HMI/operations tier | Cyber Resilience Act: reporting since 11 Sep 2026, main obligations 11 Dec 2027 [R10] | §14.2 version stamp | Low |
| G10 | Central model-config master with versioning, approval and audit | Today a recipe provider has no reference server | §3.8, §11.4 | Medium |
| G11 | Work orders into the station through OPC UA Machinery Job Management (ISA-95 Job Control: `Store`, `StoreAndStart`, job states) [R5] | Standard order hand-off; already named in the roadmap (Phase 6) | §11.11 | Medium |
| G12 | Contextual query API compatible with CESMII i3X 1.0 [R6] | A standard read surface for third-party tools and AI agents over the same tree | §3.10 | Medium |
| G13 | Product passport export: AAS submodels Digital Nameplate (IDTA 02006), Carbon Footprint (IDTA 02023), Digital Battery Passport series (IDTA 02035) [R7][R8] | Battery passport is mandatory from 18 Feb 2027; other ESPR product groups follow as delegated acts are adopted. First target (D22): nameplate and carbon footprint, product-neutral; the battery passport later | §11.8, Annex K | Medium |
| G14 | Central identity (OIDC/SSO) and qualification records | Local PIN tables do not scale to a plant. Named accounts for the tier itself are pulled into the first release by D21 (§7.5) | §7.7 | Medium |
| G15 | Maintenance work list from condition events, with service-interval counters | §8.12 raises the events; nothing schedules the work | §8.12 | Medium |
| G16 | Long-horizon historian for cyclic values | Core defers it to "the historian" (§8.5.1) | §11.5 | Medium |
| G17 | Energy-saving standby when starved or unscheduled | Sustainability; needs a Core change and careful restart semantics | §3.4, §8.14 | High — candidate only |

**The fixed host-event set is the one Core contract this tier must extend** (§11.6.1
forbids site-invented events). Compared with the station-side interface of a mature MES
(the reference studied here exposes work-process, work-part, material, tool, part-type,
data-set, operator, station-info, heartbeat and part-displaced profiles), Core lacks:

| Proposed event | Meaning |
|---|---|
| `PART_CREATED` | A new identity begins at this station (first operation, or a split) |
| `PART_DISPLACED` | An identity is replaced or re-married (carrier swap, relabel) |
| `PROCESSING_PAUSED` | Processing is suspended with the part in place |
| `MATERIAL_SETUP` / `MATERIAL_REPLACED` / `MATERIAL_REMOVED` | Finer than today's single `MATERIAL_CHANGED`: a lot or container is attached to, exchanged at, or taken from a consumption point |
| `TOOL_SETUP` / `TOOL_REPLACED` / `TOOL_REMOVED` | Same for durables |
| `OPERATOR_REQUESTED` / `OPERATOR_ARRIVED` | G7 |
| `SHIFT_CLOSED` | Already offered to `I_EventSink`; listing it makes it part of the host contract |

## 5. Station ↔ operations contract

### 5.1 Part release ("may this part be processed here?")

Core fixes what the cell *reports*. A routing-enforcing MES also needs the cell to *ask*,
and to wait for the answer. The carrier seam (§3.16.2) is the right place, but not as it
stands. Checked in the code on 2026-11-12:

- `I_PartCarrier.ReadContext` returns in one scan, and `FB_UnitBase._M_PartReceived`
  faults with `CARRIER_READ_FAILED` the moment it returns FALSE. An MES answer takes many
  scans.
- The shipped press sequence calls `M_PartReceived()` once and advances whatever it
  returns, because FALSE also means "no carrier configured" (§3.9).
- Only local carriers were found: TC3 ships `FB_LocalPartCarrier` alone, and the AB
  generator refuses every other provider. TIA was not checked.

So the release answer cannot simply be an MES-backed carrier, as v0.1 of this draft
claimed. What is proposed instead (D8, open):

- **A pending outcome on the read**, beside success and failure, offered as a second,
  optional capability so `I_PartCarrier` and every existing carrier stay unchanged
  (§1.5 — additive).
- **The base owns the wait.** While the answer is pending the Unit is *held* in the §6.1
  sense — `BUSY`, reason published at LOW, resuming by itself — and the time is classed
  `WAIT_EXTERNAL` (§8.11.4(f)), so waiting for the MES is never charged to the station's
  work time. How a chain stays on its entry step without the project writing a wait it
  could forget (O1, the trimming rule) is the design work still owed here.
- **Optional pre-delivery.** When a unit completes an operation the tier already knows
  which stations may see it next, and can place the answer at the edge ahead of the
  part, so the common case needs no round trip. A miss falls back to the pending read.
- **AB** already has a multi-scan request and reply mechanism with PLC-owned job
  identity (the host-service ingress that carries set documents); the part release would
  be one more service on it, not a new channel.

A station that does not claim the release profile is untouched. The answer itself:

```
ST_PartRelease
  Decision     PROCESS | PASS_THROUGH | HOLD | REJECT
  OperationId  the route operation this station is to perform
  ModelCode, RecipeKey   differing from the active model = changeover required (§3.8)
  WorkingCode  PRODUCTION | REWORK | MASTER | TEST | SETUP
  ReasonCode   why not PROCESS — the §8.8 vocabulary, operations band
  ChecksDue    master-part / SPC checks owed at this station
```

`PASS_THROUGH` and `HOLD` are **held** conditions in the §6.1 sense, not faults: the part
is not for this station, or waits for a human disposition. `REJECT` is the fault path. The
answer is advisory to the release gates, never a substitute for them.

Every PLC-side addition is paid for in controller memory (the AB binding has measured
limits), so the record is small, optional under §3.9, and absent on a station that does
not claim the profile.

### 5.2 Delivery and the offline policy

- **Up:** the collector reads the ring by sequence, spools durably at the edge, and
  delivers at-least-once; the operations tier de-duplicates on `(station, epoch, sequence)`.
  A `Wrapped` ring is recorded as a gap, never papered over.
- **Down:** a release request has a deadline. What a station does when it expires is a
  declared per-line policy, not station code:

| Policy | Behaviour when the operations tier is unreachable |
|---|---|
| `BLOCK` | Hold at part entry; reason published; resumes by itself when the answer arrives |
| `CONTINUE_BUFFERED` | Process on local carrier data; events spool; the unit is flagged *released offline* for later review |
| `MONITOR` | Routing is never enforced; violations are recorded only |

### 5.3 Other MES products behind the same contract

The contract of §5.1–5.2 is the product; Fraktal's own operations tier is its reference
implementation. An adapter maps the same events and release answer to another MES's
interface, and ISA-95/B2MML stays the neutral shape (§11.6.2).

## 6. Operations model

### 6.1 Entities (ISA-95 aligned)

Equipment (site / area / line / station — discovered from root Units and the Line
profile) · product, model, variant · order · **unit** (serialized) · lot / batch ·
carrier · **route** (versioned) · operation · operation execution · measurement ·
genealogy link · material lot and container · tool (durable) · host event (ledger) ·
alarm event · shift record · KPI aggregate · user and qualification · audit record.

### 6.2 The route is a graph, and it is recursive

A route is a directed graph of nodes, versioned and effective-dated. A unit is pinned to
the route revision it started on.

| Node | Semantics |
|---|---|
| `OPERATION` | One process step, performed by any station offering the required capability |
| `SEQUENCE` | Children in order |
| `PARALLEL` | All children, concurrently or in any interleaving; joins when all are complete |
| `ANY_ORDER` | All children, one at a time, order free |
| `ALTERNATIVE` | Exactly one child, chosen by guard |
| `OPTIONAL` | Child performed only when its guard holds |
| `SUBROUTE` | A reference to another route — a rework loop, a shared sub-assembly flow, a test sequence |
| `HOLD` | Wait for a human disposition |
| `END` / `SCRAP` | Terminal |

- **Self-similar on purpose.** A route is to a line what a mode chain is to a Unit: steps,
  jumps, parallel legs, sub-chains (§6.10, §6.12). A unit's position is a set of cursors,
  one per active leg — the `ActiveSteps` idea of §3.13 — so the existing flow-chart view
  can draw a route with live work-in-progress on it.
- **Capability, not station.** An operation names a required capability; stations declare
  what they offer. Alternate stations, load balancing and rerouting around a down station
  follow without editing the route.
- **Model dependence without copies.** Route selection is by product, variant, order type
  and effectivity. Inside a route, guards read unit attributes, earlier verdicts and
  measured values, so one route covers a family and a variant differs by a guard, not by a
  duplicated graph.
- **Guards are bounded predicates** — attribute, comparison, constant, combined with
  AND/OR to a fixed depth. No scripting language, for the reason
  `LOCALIZATION_AND_MODULE_CONTENT.md` gives when it excludes an expression language from
  bound HMI properties: nobody reviews it and nobody bounds its cost (D7). A case the
  predicates cannot express gets a new unit attribute, not code.
- **Time constraints** between operations (minimum cure, maximum open time) are edge
  attributes; a violation is a `HOLD` with a reason, never a silent pass.
- **Identity changes.** Merge — a component built into a parent, recorded as genealogy —
  is in the first release. Split (panel → boards), carriers with several nests, lots
  without serials and identity replacement are part of the model but follow later (D12);
  the graph and the unit record leave room for them so they arrive as additions.

### 6.3 Rework and disposition

A NOK verdict is resolved by a disposition table keyed on operation and reason — using the
§8.8 reason the station already attached, so there is no second reject taxonomy:

| Action | Return |
|---|---|
| `REWORK_AT(operation or subroute)` | to the same operation, the next, the previous, or a named one |
| `RETEST` | repeat the failing operation, bounded |
| `HOLD` | human decision (review board), then any of the others |
| `SCRAP` | terminal, with genealogy of the consumed components kept |

Loop counts are bounded per operation and per unit; exceeding one is a `HOLD`. A reworked
unit carries `WorkingCode = REWORK` into the release answer, so a station can select a
rework recipe through the ordinary changeover path.

### 6.4 Materials and tools at an operation

- **Material:** bill-of-material lines per operation — component, quantity per unit,
  tracking level (none / lot / serial), permitted alternates. Consumption is posted from
  the part's genealogy and the material events of §4; remaining quantity, expiry and
  floor-life limits are checked at release.
- **Tool:** required tool family per operation; usage counted per cycle; warning and
  blocking limits; a blocked tool refuses release with a reason naming it.
- **Data collection plan:** characteristics with limits per operation, checked against the
  measurement records the station sends — a cross-check on the station's own verdict, and
  the input to G5.
- **Qualification:** a manual operation may require one; the portal and the release
  answer explain a refusal, the PLC's access level still gates the action (§7.7).

### 6.5 Enforcement level

Per line: `ENFORCE` (the release answer is honoured), `MONITOR`, or `OFF` (traceability
only). A plant can start at `OFF` and tighten without touching station code.

The offline policy of §5.2 is declared with it (D6): a line at `ENFORCE` defaults to
`BLOCK`, a line at `MONITOR` or `OFF` to `CONTINUE_BUFFERED`. Either default may be
overridden per line.

### 6.6 Orders

Orders arrive from an ERP; the operations tier executes them (D13). It holds released
orders with their product, quantity and due date, binds units to an order when they are
created, counts progress from the verdicts it already receives, and reports completion
and scrap back. An order selects the route (§6.2) and the model the stations change over
to (§3.8). A plant without an ERP link enters orders in the portal — the same record,
a different source.

- **Interface (D14).** One documented REST endpoint whose payloads follow ISA-95 terms
  (order, product definition, quantity, schedule, production response). An ERP pushes to
  it or is polled through an adapter; product-specific connectors are built on top of it,
  never beside it.
- **The tier does not decide what is produced next (D16).** It executes and tracks a
  schedule that is given: imported from the ERP, or entered and ordered by a planner in
  the portal. It shows that schedule per line and reports progress against it. It
  contains no sequencing, dispatching or optimisation logic. Automated scheduling is a
  common reason MES projects stall; it is excluded from the first release by decision,
  not by omission.

### 6.7 Identities and labels

Each product declares where a part's identity comes from (D15):

| Source | Meaning |
|---|---|
| `MES_GENERATED` | Built by the tier from a declared pattern — counter, date, plant and line code, check digit — and handed to the first station |
| `STATION_ASSIGNED` | Created at a station (marking, laser) and reported with `PART_CREATED` |
| `PRE_MARKED` | Already on the part or carrier when it arrives (supplier code, customer serial) |

Whatever the source, the tier checks uniqueness and rejects a duplicate with a reason.
Label content is an optional template per product, filled from the same unit record.
A product with `MES_GENERATED` identities on a line that keeps producing offline (§6.5)
reserves a block of numbers at the edge, so the first station is not stopped by an
outage; the block size is declared, and unused numbers are accounted for rather than
silently reused.

### 6.8 First-release scope and build order

**In:** serialized parts with genealogy (D12) · a given schedule of orders from an ERP or
a planner, executed and tracked but never decided (D13, D16) · the route graph with
rework and disposition and bounded guards (D7) · identities per product (D15) · material
and tool checks at release · per-line enforcement and offline policy (D6) · the low-cost
features G1–G9 and G13 (D19) · audit trail, electronic signatures, retention and legal
hold, framed by IATF 16949, 21 CFR Part 11 and EU GMP Annex 11 (D18, D21) · named
accounts for the tier · a database per plant with a roll-up (D17) · on one box with
PostgreSQL (D4).

**Later:** lots, carriers with nests, split and identity replacement, scheduling and
dispatching, packaging, product-specific ERP connectors (D23), the battery passport
(D22), G10–G12, G15, G16, and the part of G14 that unifies station logins.

That is a large first release. It is built in stages (D20) that are each usable in a
plant on their own, so the release can stop being "first" at any stage boundary without
leaving half a feature:

| Stage | Content | Usable result |
|---|---|---|
| 1 Foundation | Collector on every transport (G1), ledger, discovered equipment tree, named accounts, audit trail, UNS publish (G2), ISO 22400 KPIs (G3) | Every station's events and KPIs are kept and comparable |
| 2 Traceability | Unit history and genealogy, identities (§6.7), portal, semantic layer, dashboards | A part can be looked up; a plant can build its own views |
| 3 Execution | Orders over REST (D14), route graph, release answer, material and tool checks, enforcement, electronic signatures | Routing is enforced and deviations are signed for |
| 4 Analytics and fleet | Capability and SPC (G5), alarm performance (G4), config backup and diff (G6), operator call (G7), software inventory (G9), assistant | Quality and fleet questions are answerable |
| 5 Sustainability and retention | Energy per part (G8), passport export (G13), retention periods and legal hold, plant roll-up | Records are exportable and defensible |

Two things are designed in stage 1 although they are delivered later: the time
partitioning that retention and legal hold rely on (§7.5), and the plant code in every
identity and key that the roll-up relies on (§7.4).

## 7. Platform

### 7.1 Persistence

- **Database is the deployment's choice.** PostgreSQL by default; Oracle and Microsoft SQL
  Server supported. Domain code talks to an ORM-backed repository layer and contains no
  vendor SQL; dialect-specific optimisation (partitioning, partial/filtered indexes) is
  isolated behind it.
- **What the chosen languages offer (checked 2026-11-12, D2).** The owner's direction is
  Rust or Go, and both have an ORM route to all three engines:

  | | PostgreSQL | SQL Server | Oracle | Schema sync found |
  |---|---|---|---|---|
  | Go — GORM [R14] | first-party | first-party | driver published by Oracle (on godror) | auto-migration on all three |
  | Go — Bun [R13] | yes | yes | yes | explicit migrations only |
  | Rust — RBatis [R16] | first-party `rbdc-pg` | first-party `rbdc-mssql` | third-party `rbdc-oracle`, one maintainer [R17] | `table_sync` creates tables and adds columns on PostgreSQL and SQL Server; no Oracle mapper and no index handling found |
  | Rust — SeaORM 2.0 [R15] | yes | proprietary SeaORM X only | none found | — |

  In both languages the Oracle path needs the Oracle client libraries at run time, so a
  single self-contained binary holds only for the other two engines. Two items to verify
  before relying on the Rust route: whether `rbdc-mssql` sits on `tiberius`, whose
  upstream is reported unmaintained with open 2026 advisories and a community fork
  [R18]; and the release cadence of `rbdc-oracle`.
- **The dictionary generator owns the DDL, not the ORM.** Tables, indexes and partitions
  are emitted per engine from the data dictionary; the ORM maps and queries. This follows
  from principle 3, and it removes schema sync — the column where the candidates above
  differ most — from the language decision.
- **Portable core schema.** Anything that is filtered, joined or aggregated is a typed
  relational column. JSON columns hold only opaque payloads that the server never filters
  on, because JSON indexing is where the three engines differ most.
- **Indexes are generated, in two layers.**
  1. *Derived* from the data dictionary at migration time: every foreign key, every
     attribute declared filterable or sortable, every declared access path (composite),
     and the time key of every partitioned table.
  2. *Advised* at run time: a background job reads the engine's own statistics and
     proposes indexes. Mode is configuration — `OFF` / `PROPOSE` / `AUTO` — every change
     is audited, and nothing is dropped without usage evidence.
- **The ledger is partitioned by time** with a declared retention and archive tier.
- **Cyclic values** (G16) sit behind a separate store interface so a time-series engine
  can be used where available and a plain partitioned table elsewhere.

### 7.2 Work-in-progress cache

Configurable on or off. When on, the state of every unfinished unit is held in memory:

- **Admission:** on first request for a unit, and predictively when it completes an
  operation (its next eligible stations will ask soon).
- **Eviction:** when the unit reaches `END`/`SCRAP`, or after a configurable idle time
  since the line last requested or reported it; bounded by size as a backstop.
- **Durability rule:** interlock-relevant facts are **write-through** — a result is
  durable before the station receives its acknowledgement, matching §3.16's
  write-before-event. Write-behind is permitted only for derived aggregates [R12].
- **Correctness never depends on the cache:** a miss is a database read; turning the cache
  off changes latency, not answers.
- **Several nodes:** either one owner per unit (partitioned) or an external shared cache;
  open (D5).

### 7.3 Redundancy

Declared per deployment, each level with a stated recovery point and recovery time:

| Level | Database | Application |
|---|---|---|
| `NONE` | single instance, scheduled backup | single node |
| `STANDBY` | asynchronous replica, manual or automatic promotion | cold or warm second node |
| `HA` | synchronous replica with automatic failover (the engine's native mechanism) | several stateless nodes behind a balancer |

The edge spool (§5.2) covers the failover window in every level, so redundancy changes
how long the tier is blind, never whether events survive.

### 7.4 Several plants

Each plant runs a complete instance with its own database and works alone (D17). A
central **roll-up** receives KPI aggregates and a search index (identity → plant,
order → plant) from every plant, one way. It answers cross-plant questions and directs a
drill-down to the owning plant; it is never a source of truth and never in a station's
path. Genealogy stays in the owning plant and is fetched on demand (D24). Identities
carry the plant code (§6.7), so two plants cannot issue the same one.

Proposed: master data that plants share — products, routes — is published from one place
as versioned documents and applied per plant whole or not at all, the line-config pattern
of §3.8e one tier up.

### 7.5 Records that must stand up to review

In the first release (D18):

- **Audit trail.** Every change to master data and every manual intervention records
  who, when, the old and new value and the stated reason, in the same append-only way as
  the ledger. Entries are chained by hash so removal or alteration is detectable. The
  trail can be filtered, reviewed, signed as reviewed, and exported.
- **Electronic signature.** A named person re-authenticates at the moment of signing. The
  signature records its meaning (authored, reviewed, approved), the time, and a hash of
  exactly what was signed. Which actions need one is declared, starting with: releasing a
  route or data-collection-plan revision, a disposition decision (§6.3), overriding a
  release answer, changing an identity pattern, and placing or lifting a legal hold. A
  signature in the operations tier authorises nothing on a controller; §7.7 access levels
  still gate every PLC action.
- **Retention and legal hold.** Each record type has a declared retention period and an
  archive tier. A legal hold freezes the records of named units, lots, orders or a time
  range against expiry and archiving until it is lifted. The retention job is hold-aware,
  so dropping a time partition can never remove a held record, and every deletion is
  itself recorded.

**Frame (D21).** All three: IATF 16949 (automotive), 21 CFR Part 11 (FDA) and EU GMP
Annex 11. The mechanisms are therefore designed to the strictest of them and the others
are configurations of the same mechanisms. What follows — to be checked against the
regulation texts before any of it becomes normative:

- **Named people, not shared levels.** A signature and an audit entry belong to one
  individual. The tier needs its own named accounts with a credential policy from stage
  1, so the identity part of G14 moves into the first release; unifying those accounts
  with the stations' local logins stays later.
- **Signing asks twice.** Signing re-authenticates with two components (identity and
  secret), and the signer's name, the time and the meaning are shown wherever the signed
  record is displayed or exported.
- **A change states its reason.** For master data that affects product quality, the
  reason for change is mandatory, and reviewing the audit trail is itself a recorded,
  signable activity.
- **Records leave the system intact.** A record can be exported in human-readable and
  electronic form together with its signatures and audit trail.
- **Nothing is hard-coded.** Retention periods and which actions need a signature are
  configuration per product and customer; automotive retention in particular follows the
  customer's contract.
- **Compliance is claimed by a deployment, not by software.** The tier supplies the
  technical controls. A site's claim also needs its validated installation and its own
  procedures, so each release ships what a site needs to validate it: versioned
  requirements, the tests that cover them, and installation and operation checks.

## 8. Portal, dashboards and the assistant

### 8.1 Portal

A web application (React, D3) over the operations API: the discovered equipment tree, unit history
and genealogy, route and live work-in-progress, orders, materials and tools, alarms,
shifts and KPIs. Filtering by time, line, station, model, order, shift, verdict and
reason; saved views; export. Scope is enforced server-side per user — the plant-level
counterpart of the HMI's root scope — and every KPI drills through to its events, to the
unit, and by canonical path (§4.8) into the station's own HMI.

### 8.2 Semantic layer

Measures (OEE and its factors, first-pass yield, cycle time, energy per part …) and
dimensions (time, shift, equipment, model, reason, operator …) are defined **once** and
generated from the data dictionary. The portal, the API and the assistant all query
through it, so a figure means the same thing wherever it appears.

### 8.3 Dashboards

A dashboard is a **declarative document**: data bindings expressed in semantic-layer
terms plus a chart grammar. A user builds one by placing dimensions and measures; the
document is versioned, shareable, and published with the draft/publish/rollback discipline
the HMI layouts already use.

### 8.4 Assistant

- The model **selects measures, dimensions and filters; a deterministic engine writes the
  query.** Free text-to-SQL is not the default path: a query that runs and is wrong is the
  failure nobody notices [R11].
- A generated dashboard is the same declarative document a person would author — so it
  can be read, corrected, saved and reviewed, not just looked at.
- Every answer shows its query, its filters and the freshness of its data.
- Read-only database role, the asking user's scope, bounded cost per question.
- **No tool reaches a controller.** The assistant has no command, release, acknowledge or
  config-write capability, by construction.
- Text originating in a PLC or a user field is data, never instruction.
- The model provider is pluggable — a hosted API or a local model for a site that may not
  send data out — and the same tools are offered as an MCP server so other agents can use
  them.
- Diagnostic questions ("why was line 3 down last night") are answerable from data that
  is already sentences: first-out reasons, stall walks, release reports.

## 9. Decision ledger

| # | Decision | Recommendation | Status |
|---|---|---|---|
| D1 | Scope: own MES of record, an integration layer for other MES, or one contract serving both | One contract; own tier as reference implementation; adapters for other MES | **Decided 2026-11-12** |
| D2 | Backend technology (must carry an ORM for PostgreSQL, Oracle and SQL Server) | Owner's direction: **Rust or Go**, chosen for low latency, open to change. Both have an ORM route to the three engines (§7.1: GORM or Bun; RBatis). Settle by a spike on the three engines: the same repository operations and the part-release path in each language, compared on Oracle and SQL Server driver health, latency at the 99th percentile under station load, and deployment footprint | **Open — Rust kept open by the owner 2026-11-12** |
| D3 | Portal and dashboard technology | Own web portal rendering declarative dashboard documents, in **React**; Dart is not used for this front end | **Decided 2026-11-12** |
| D4 | Deployment topology | On-premises first (one box), cloud and multi-site as a scale-out of the same services | **Decided 2026-11-12** |
| D5 | Cache topology with several nodes | Partitioned ownership first; external shared cache optional | Open |
| D6 | Default offline policy | Declared per line: `BLOCK` where routing is enforced, `CONTINUE_BUFFERED` for traceability-only lines (§6.5) | **Decided 2026-11-12** |
| D7 | Route guards: bounded predicates or a scripting hook | Bounded predicates only; no script hook | **Decided 2026-11-12** |
| D8 | Where the release answer enters the PLC | At the carrier seam, as an additive pending-capable read with the wait owned by the Unit base (§5.1). The first proposal — a plain MES-backed carrier — does not work: the read is single-scan and faults on FALSE | Open — corrected after code check 2026-11-12 |
| D9 | Assistant provider | Pluggable; hosted default, local for air-gapped sites | **Decided 2026-11-12** |
| D10 | Name and filing of the result | Part V at the root once normative; working set stays in `I50/` | Open |
| D11 | How far Dart is dropped | Portal only. The Flutter operator HMI and the Dart gateway and host adapter stay; replacing them is a separate decision | **Decided 2026-11-12** |
| D12 | What the first release tracks | Serialized parts with genealogy — what `ST_PartContext` already carries, so no new PLC contract. Lots, multi-nest carriers, split and identity replacement follow | **Decided 2026-11-12** |
| D13 | Where orders come from | An ERP sends, the tier executes and reports back; manual entry in the portal where there is no ERP link (§6.6) | **Decided 2026-11-12** |
| D14 | ERP interface in the first release | One REST endpoint with ISA-95 shaped payloads; product-specific connectors are built on top of it later | **Decided 2026-11-12** |
| D15 | Who creates a part's identity and label content | Declared per product: generated by the tier, assigned by a station, or pre-marked; the generator and label templates are optional (§6.7) | **Decided 2026-11-12** |
| D16 | Scheduling and dispatching | None. The tier executes and tracks a schedule imported from the ERP or entered by a planner; it never decides what is produced next (owner's ruling, §6.6) | **Decided 2026-11-12** |
| D17 | Several plants | A complete instance and database per plant; a one-way roll-up for KPIs and cross-plant search (§7.4) | **Decided 2026-11-12** |
| D18 | Regulated-industry capabilities in the first release | Electronic signatures, audit-trail review, retention and legal hold (§7.5) | **Decided 2026-11-12** |
| D19 | Low-cost features in the first release | All four groups: data foundation (G1–G3), quality analytics (G4, G5), sustainability (G8, G13), fleet and compliance (G6, G7, G9) | **Decided 2026-11-12** |
| D20 | Build order inside the first release | Five stages, each usable alone (§6.8) | **Decided 2026-11-12** |
| D21 | Regulation framing the compliance features | IATF 16949, 21 CFR Part 11 and EU GMP Annex 11 together; designed to the strictest, the rest configured (§7.5) | **Decided 2026-11-12** |
| D22 | First product-passport target | Product-neutral: digital nameplate and carbon footprint as AAS submodels; battery passport later | **Decided 2026-11-12** |
| D23 | First ERP product connector | None yet: the REST interface and a file-import helper only, until a real plant and ERP are in hand | **Decided 2026-11-12** |
| D24 | What the plant roll-up answers | KPIs plus part and order lookup; genealogy fetched from the owning plant on demand | Defaulted 2026-11-12 — the owner stated no preference |

## 10. Open questions for the next rounds

Needing the owner's facts:

1. *(answered — D21)*
2. *(answered — D22)*
3. *(answered — D23)*
4. Which stations have utility metering today? Energy per part (G8) is delivered where
   §8.14 metering exists and shown as "not measured" elsewhere, never estimated.
5. *(defaulted — D24)*
6. Are manual interventions at a station attributable to a named person today, at the
   level D21 expects, or only to an access level? If only to a level, unifying station
   logins with the tier's accounts cannot stay "later" for a regulated site.

Design questions:

7. After the first release, which follows first: lots, multi-nest carriers, or split and
   identity replacement (D12)?
8. Packaging and shipping units: when?
9. Is G17 (energy standby) wanted as a Core change?
10. Is one backend language preferred throughout, or may the tier split — for example
    one language for the edge collector and release service, another for the portal API?

To verify in the code or by a spike:

11. *(answered — see G1: only AB has a collector)*
12. Rust versus Go on the three engines (D2), and the cache topology with several nodes
    (D5).
13. How a chain waits on its entry step for a pending release answer without project
    code (D8, §5.1), and what the pending read costs in controller memory on each
    binding.

## 11. References

- [R1] European Commission, *Industry 5.0 — towards a sustainable, human-centric and resilient European industry* (2021): https://research-and-innovation.ec.europa.eu/knowledge-publications-tools-and-data/publications/all-publications/industry-50_en
- [R2] Station-side MES interface of the reference studied: *MES over PublicInterface — Technical Manual* (2021) and the `NxMesBase` access objects, read from the local knowledge base at `C:\Projects\NexeedAgent`.
- [R3] SAP Manufacturing Execution — routing group types, loop limits, return types, rework and disposition routings: https://help.sap.com/saphelp_me60/helpdata/EN/66/fa5f0e9e244efc9096ef6eb06bc0ba/content.htm
- [R4] Critical Manufacturing — flow modeling (flows containing steps and flows, alternate and optional steps) and line material tracking: https://help.criticalmanufacturing.com/tutorials/modules/routing-and-dispatching/flow-modeling/flowmodeling/
- [R5] OPC 40001-3 Machinery Job Management (on OPC 10031-4 ISA-95 Job Control): https://reference.opcfoundation.org/specs/OPC-40001-3/6
- [R6] CESMII i3X 1.0 (June 2026): https://github.com/cesmii/i3X
- [R7] IDTA submodel templates — Digital Nameplate 02006, Carbon Footprint 02023, Time Series Data 02008, Production Calendar 02067, Digital Battery Passport 02035: https://industrialdigitaltwin.org/en/content-hub/submodels
- [R8] EU battery passport (18 Feb 2027) and ESPR status — secondary sources, to be re-checked against the Commission's pages before any normative use: https://en.wikipedia.org/wiki/Battery_passport , https://espratlas.com/timeline/
- [R9] ISO 22400 KPI set — secondary summaries; check ISO 22400-2 for definitions: https://www.fabrico.io/blog/iso-22400-kpi-selection-guide/
- [R10] Cyber Resilience Act timeline: https://natlawreview.com/article/cyber-resilience-act-11-september-2026-key-starting-point-reporting-obligations
- [R11] Semantic layer versus text-to-SQL (vendor benchmark, 2026): https://docs.getdbt.com/blog/semantic-layer-vs-text-to-sql-2026
- [R12] Write-behind durability trade-off: https://oneuptime.com/blog/post/2026-01-30-write-behind-pattern/view
- [R13] Bun (Go) — drivers and dialects: https://bun.uptrace.dev/guide/drivers.html , https://github.com/uptrace/bun
- [R14] Oracle-published GORM driver: https://github.com/oracle-samples/gorm-oracle
- [R15] SeaORM 2.0 and SeaORM X (Rust): https://www.sea-ql.org/blog/2026-07-27-sea-orm-2.0/ , https://www.sea-ql.org/SeaORM-X/
- [R16] RBatis (Rust) — supported databases and the table-sync plugin: https://docs.rs/crate/rbatis/latest
- [R17] `rbdc-oracle`, the third-party Oracle driver for RBatis (on the ODPI-C based `oracle` crate): https://docs.rs/crate/rbdc-oracle/0.10.0 , https://docs.rs/crate/oracle/latest/source/README.md
- [R18] `tiberius` maintenance status and the `tiberius-ng` fork: https://users.rust-lang.org/t/tiberius-ng-a-maintained-continuation-of-the-tiberius-sql-server-driver/142157
