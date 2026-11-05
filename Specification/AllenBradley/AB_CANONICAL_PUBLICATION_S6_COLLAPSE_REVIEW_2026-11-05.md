# S6 WP6.6 — Generator collapse: inventory, gate and increments

Non-normative design review, 2026-11-05. It turns the plan's WP6.6 text
(R3, R5, R6, R8, O10, O11) into increments that can each be proven before the
next one starts. No generator output changes here. Evidence:
[`AB_S6_COLLAPSE_INVENTORY_OFFLINE_2026-11-05`](Evidence/AB_S6_COLLAPSE_INVENTORY_OFFLINE_2026-11-05.md).

## 1. What the contexts hold

`Investigation/context_dataflow_01.py` generated both S6-Q declarations
(genealogy S4b owner demo and the press) and followed each of the 320 legacy
context members through the emitted ST and ladder. The two declarations have
the same 320 members; one member is classed differently. Inside an AOI a
context is a parameter, so the type AOI's `Ctx` stands for every instance of
the type and the Unit AOI's `Ctx<Name>` for one instance. The owner is the
type AOI for a module context, and the Unit AOI for the Unit context and the
chart.

| Class | Genealogy | Press | Meaning |
|---|---:|---:|---|
| private | 108 | 109 | Only the owner touches it |
| input | 80 | 80 | Written only outside the owner (chains, driver, mailbox, Unit AOI) |
| output | 62 | 61 | Read outside the owner and its publication |
| shared | 30 | 30 | Written by the owner and outside it; all of them Unit or chart |
| published | 24 | 24 | Read outside the owner only by the canonical publication |
| unused | 16 | 16 | Touched by no routine |

- **Copies.** 94 members have an exact copy somewhere in the publication. Only
  28 of them fill a published canonical leaf, in 41 assignments: a module's
  `Status.State` and its `Timing.Rows[i]`, and for the Unit `ModeActivePublished`,
  `CurrentStep`, `RunStyle`, the part counts, `Decision.Default`, and the
  chart's elapsed and last-duration rows. The rest fill private caches, such as
  the diagnostic text cache's `Inputs`. Those caches are change detection, not
  duplication.
- **Harness facts.** 125 members carry a harness fact
  ([HX accounting](Evidence/AB_S6_HX_FACT_ACCOUNTING_OFFLINE_2026-11-03.md)).
- **Never written.** 19 members are read but never written by a routine. They
  are declared constants: `Par_TimeoutMs`, `Par_TaskPeriodMs`, `Par_Speed`, an
  unused `Abort`, and `StallTimeMs`.
- **Arrays.** Every module array is published: the eight-slot `Tim*` timing
  arrays. The chart's per-step arrays are all Unit-side. After R3 a module
  context is therefore all scalars.

## 2. What a client can reach

`fraktal_ab_schema_identity.py` records the image's external surface from the
generated L5X itself, not from the generator's description of it. That surface
is:

- every tag whose ExternalAccess is not `None`: its type, dimensions, access and
  decoded initial data;
- every UDT and AOI those tags reach, member by member.

| Declaration | Published tags | Types | Canonical tags | Legacy tags |
|---|---:|---:|---:|---:|
| `fraktal_ab_genealogy_s6_host_demo` (V6.11) | 94 | 155 | 31 | 63 |
| `fraktal_ab_press_canonical_echo38` | 78 | 128 | 17 | 61 |

A canonical tag is one with a canonical type, or one the canonical header
names. The legacy tags are:

- the six module contexts, `Unit` and `Chart`;
- the ten V5 manifest tables;
- the observation frame;
- the legacy views (alarm ring, OEE, profiler, health and others);
- the record tags.

**Three consequences the plan's wording does not show:**

1. **The canonical header still names legacy symbols.** Its V6.3 `Services`
   rows name `FRK_<Root>_HmiRequest`, the legacy staged request: its
   `ConfigProvider`, `Frame` and `ConfigSet` members. V6.11's
   `HostServiceBindings` supersede them, and removing the staged endpoints
   empties that table. The Dart reader already accepts zero `Services` rows
   (`table('Services', …, 0, 16)`). So the removal is a new additive minor
   (V6.12) with `ServicesCount = 0`, never an edit to V6.11.
2. **Two V5 tables are canonical in fact.** The V6.6 `CommandBindings` row names
   `FRK_<Root>_MfWriteCapabilities` and `FRK_<Root>_MfLocalization`. R8 keeps
   both tables, under their names and types, and removes the other eight.
3. **The configuration revision is a hash of legacy content.**
   - `ConfigRevision` and `LegacyContentHash` derive from the V5 tables, which
     are built from the context member declarations.
   - The host services take a set document's `configRev` from
     `LegacyContentHash[:6]` (`cipHostRevision`).
   - The HostEvents source key is `<serial>:<LegacyContentHash>`.
   - `fraktal_ab_sets.accepted_revisions` already lists nine families of
     predecessor variants. Every one is a declaration change that left the
     editable value schema untouched but moved the revision.

   Deleting the member declarations leaves no way to compute either the
   revision or the predecessors it must accept. **O12** (§5) proposes the fix.
   It is needed only by increment C6.

## 3. Where each member goes

The canonical structures become the working storage wherever a published fact
already has a canonical home. Everything else stays private, and becomes
private in fact.

| Member | After the collapse | Increment |
|---|---|---|
| Module `published` (State, Timing rows, FaultActive) | The type AOI writes the canonical leaf through an InOut `Leaf`; the copy line goes | C1 (R3) |
| Unit or chart member with an exact canonical counterpart | The canonical path is the storage; every writer writes it and the copy goes | C2 (R8) |
| Module `input` | AOI Input parameter, written as `Inst<Name>.<Member>` | C3 (R8) |
| Module `output` | AOI Output parameter, read as `Inst<Name>.<Member>` | C3 |
| Module `private` | AOI local tag, or an Output parameter if an O10 harness asserts it | C3 |
| Module or Unit `unused` | Deleted | C3 |
| Remaining Unit and chart members | Private Unit work tags (`ExternalAccess="None"`), unpublished | C6 |

Why AOI parameters and not an unpublished copy of today's context:

- **Encapsulation.** A local tag cannot be written from outside its AOI. That
  is the AB form of a TC3 protected member, and a context tag gives any routine
  write access to any private member.
- **One tag per instance.** Each module today has two tags,
  `FRK_<Root>_Inst<Name>` (almost empty) and `FRK_<Root>_Ctx<Name>`. After C3 it
  has one, its AOI instance.
- **Scan cost.** A parameter is direct access inside the AOI. Every `Ctx.`
  member access through an InOut is indirect, and the cumulative TASK maximum is
  already within about 1 ms of the 10 ms period.

The Unit AOI then takes each module instance as an AOI-typed InOut. Every
member it reads or writes is an Input or Output parameter, because a local tag
is not reachable through an InOut.

The Unit and chart contexts stay as unpublished work tags. Their 30 `shared`
members are written by the chains, the mailbox and the diagnostics as well as
by the Unit AOI. They are the Unit's working state, not a published duplicate,
and an AOI signature cannot express seven independent writers.

## 4. The increments

Each increment is one commit, or a few, and passes before the next starts:

- the schema-identity gate (`test_fraktal_ab_schema_identity`), with every
  intended difference added to the declaration's `.declared.json` beside the
  plan item that makes it;
- the executed-ST cases unchanged in meaning, their assertions moved to the
  storage that now holds each fact;
- full AB discovery;
- both v38 targets build and read back, and the access audit passes;
- Capacity and the ST token count recorded against the capacity plan's ranges.

| # | Step | Surface difference it declares |
|---|---|---|
| C0 | This inventory, the schema-identity gate, and fixtures recorded from `6898dfb87` | None |
| C1 | R3: type AOIs write their canonical leaf; ScanCanonical keeps only per-instance calls | Context type members `OutImm_ExecState`, `Tim*`, and module `Error` where only FaultActive read it, removed |
| C2 | R8, Unit: exact-counterpart members become canonical storage | Their Unit/Chart members removed |
| C3 | R8, modules: contexts become AOI parameters and locals; `unused` deleted | `FRK_<Root>_Ctx*` tags and `FRK_T_*Ctx` types removed |
| C4 | R6 + O10: fixture observation structure in acceptance declarations; the press harness and the 15 HX modules read it; frame removed | Observation frame removed; observation structure added (acceptance only) |
| C5 | O11 + O4: harnesses command through `writeBatch`; Frame ingress and staged services removed; header V6.12 | `FRK_<Root>_HmiRequest` removed; header minor and `Services` rows changed |
| C6 | R8, tables: legacy published tags to `None`; eight V5 tables removed (needs O12) | Those tags removed from the surface |
| C7 | R5: a production declaration selects one AUTO rendition | Production only; acceptance declarations keep all three |

Within these steps, C1 and C2 change no wire contract. C3 changes only private
storage. C4 to C6 change the published surface by declared removals, plus one
versioned header minor. A native S6-Q session after C7 closes WP6.6. Running
one earlier, after C3, is optional: it would catch a scan-time surprise
sooner.

## 5. Proposed owner decision O12: the configuration revision

**Proposal.**

- **The revision.** It becomes the first six hex digits of a hash over what
  gives a stored value its meaning, and nothing else:
  - for each editable value, its record, scope, key, and kind or type,
    including the unit;
  - the set schema, and the model and line layout.

  Three things stay out.
  - *Ranges and write levels.* The controller already checks each value's
    range and the session's permission at load, validate-before-load (§5.6).
    Hashing them would only refuse documents the controller could have checked
    itself.
  - *Ordinals.* Documents are addressed by key, and the key is resolved against
    the controller's current table.
- **`LegacyContentHash`.** It becomes that hash, all 16 hex digits.
  - Its path stays, so schema identity holds.
  - The rule `configRev = LegacyContentHash[:6]` (`cipHostRevision`, the bench
    server) stays, so neither the wire nor the Dart reader changes.
  - The name is historical from C6 on.
- **Predecessors.** The collapsed image also accepts everything its
  pre-collapse build accepts: the revision itself and the predecessors
  `accepted_revisions` derives today. The pre-collapse generator at
  `6898dfb87` records them once, as constants, for every declaration in the
  tree. This increment's fixtures already hold each gated declaration's own
  revision, as `LegacyContentHash`. So no set or live document saved before
  the collapse is refused.

This is the principled fix the nine predecessor-variant families point at. A
revision that moves whenever a status field is added forces every such
release to enumerate its predecessors, and one missed variant refuses a
customer's saved sets at the next download. The families multiply: the V6.11
genealogy already accepts 122 revisions, and its guard had to be nested to
pass the v38 operand limit. After C6, the revision moves only when a stored
value would mean something different, and the frozen list never grows.

**HostEvents consequence.** The adapter keys a root's event cursor on
`<serial>:<LegacyContentHash>`. When the hash changes, it refuses the existing
cursor file ("invalid acknowledged cursor") and delivers nothing for that root
until the cursor is retired. Today that happens at every download whose
legacy content changed. Under O12 it happens once at C6, so the C6 upgrade
procedure retires the cursor, and afterwards only on a real schema change.
Whether the adapter should start a new cursor by itself, with a data-loss
record, is a separate question outside O12.

**Alternative.** Keep the V5 content computation as an unemitted, frozen
identity function. The revision is then unchanged forever, but the member
declarations R8 deletes survive solely to feed a hash.

C1–C5 and C7 do not depend on O12. C6 waits for it.

## 6. Out of scope here

- WP6.7: deleting RT and MO, and the gate updates.
- WP6.8: the documentation and activation.
- S6-Q: the native run, including the HostEvents ring reader and the
  SessionPermits predicate that are still pending.
