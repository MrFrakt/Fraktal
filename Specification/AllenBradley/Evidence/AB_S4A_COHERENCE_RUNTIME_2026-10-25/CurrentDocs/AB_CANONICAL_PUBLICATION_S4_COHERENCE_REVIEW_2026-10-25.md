# S4 coherence contract review — discoverable counters for bounded read groups

Non-normative review, 2026-10-25. **Option A owner-approved; S4a's initial
small-group scope qualified on Echo. S4b desktop/tier acceptance remains open.**
S3's recorded path/value equivalence and press ST/SFC/LD acceptance remain valid.
This review resolves a publication fact needed by the shipping S4 client.

## Finding

The [plan's S4](AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md) requires per-row/
group coherence through PLC-published metadata. Part III §3.13 explicitly says
coherence is per row; it does not require a scan-atomic whole document. A guarded
set must change less often than its read window or use PLC buffering, and bounded
failure must degrade quality.

Current code publishes an odd/even `CanonicalGeneration` counter around each
scan (`canonical_publication.begin_scan` and `cyclic`). However, the accepted
V6.6 manifest publishes no association between that counter and its protected
canonical tree/data products. The Python equivalence harness obtains the symbol
through its station declaration. The generic acquisition reader's manifest
pre/post check protects configuration shape, not live data coherence; its own
docstring states that limitation. S3's migration observation frame supplies the
independent native comparison proof, but cannot become the shipping protocol.

Therefore S4 cannot simply port the whole-root acquisition and mark its result
Good. Guessing a generation tag name or using the observation frame would put
unpublished station facts in the client. This is a correction to the S4 plan's
assumption that the needed association already exists.

## Approved option A — expose the existing guard in manifest V6.7

Add a hash-covered `ReadCoherenceBindings` table, with exact count/capacity, to
the physical V6 manifest. Normalized descriptors have exactly:

| Field | Published fact |
|---|---|
| `CanonicalPrefix` | Protected root or data-product path prefix, with segment boundaries |
| `RevisionSymbol` | Exact controller-scope DINT symbol; never derived by the client |
| `Protocol` | Versioned ordinal 1: a nonnegative 31-bit scan counter, odd during mutation, even when stable |
| `MutationPeriodUs` | Configured periodic publication interval, derived from the declaration/task period |

The publisher emits one binding per root/product prefix, reusing the existing
counter for every surface it actually protects. It verifies that all writes to
those published surfaces lie between the begin/end increments. A generation
counter is read-only, not a client mutation capability. Multiple non-overlapping
prefixes may share a counter; overlapping/duplicate prefixes, missing roots,
invalid symbols/types/protocol/period, and uncovered published data refuse.
Future forests describe their counters independently; no super-root is assumed.

The schema minor becomes **7**. The table participates in canonical content hash
and derived configuration revision. V6.6 and earlier source/image regeneration
stays unchanged behind an opt-in declaration choice. Existing clients that do
not understand V6.7 refuse it. No Core value path, scalar type, logical bound,
write endpoint, release condition or credential rule changes. V2 remains inactive.

The client builds small native row/groups from Templates and tier demand. It
reads the published counter before and after each group and accepts only equal,
even counters within both its bounded acquisition budget and the published
interval. It includes the first counter request in that window. No cross-group
same-scan promise is added. Group sizing/connection concurrency and deployment
freshness are measured; retry is not a substitute for a viable window.

Failed groups contain no stale/mixed payload: a bounded coherence conflict is
Uncertain; invalid metadata, lost transport or timeout is Bad. Cache ages are
monotonic and are not renewed by a failed read or reconnect. A session must also
establish counter progress before claiming fresh scanning data; a frozen even
counter does not prove liveness. No controller source timestamp is invented.

If measured windows cannot fit the configured interval, the stage does not
accept the deployment: adjust bounded group/tier acquisition or publish a proper
PLC buffer. The migration frame remains excluded. Capacity and scan are measured
on the exact prepared image, followed by guarded native acceptance and rollback.

## Alternative B — row-local revisions/publication buffering

Assign explicit revision sources to individual rows/groups, and update them at
their owning publication boundary, optionally skipping unchanged rows or using
PLC buffers where required. This can reduce contention for slower networks but
adds PLC counters/metadata and owner mutation logic; footprint and scan need
measurement. It must preserve the direct canonical tree, exact values, and
generic discovery. It is a different publication contract and is not implemented
by adding station conventions to the client.

**Recommendation: A first**, using the guard already present and measuring
bounded group windows. It adds discoverability without extra cyclic counter
work. B remains available if those measurements show A cannot satisfy a station's
declared freshness. Owner reply to `call_6bf53f81733f4bac8119326954e3b4d6:0`:
**“A — publish existing counter bindings (Recommended)”**. This approves the
wire contract and dependent offline work. It authorizes no download or controller
write. Earlier S3 evidence and V6.6 regeneration remain unchanged.

## Qualification boundary inside S4

S4a first qualifies the additive metadata and small guarded reads on Echo.
`fraktal_ab_genealogy_s4_demo` opts in; all previous declarations retain their
wire profile. The reference reader validates exact coverage and discovers each
counter's DINT type. The read-only `fraktal_ab_read_group_probe` plans module
Status records and one bounded structured row per data product from Templates.
It accepts only equal, positive even counters within the declared interval and
one bounded acquisition budget, requires counter progress across samples, and
stops on a Bad read. This is an initial feasibility gate, not full HMI read-tier
or freshness acceptance. Schema-discovery whole-record reads are not accepted
coherent samples. Probe rows do not include command/service inputs or the
migration frame.

S4b then completes transport, logical snapshot assembly, demand/read tiers,
worker isolate, read-only repository presentation, spike retirement and desktop
acceptance. Active-workload and all consumed row/group windows must pass there;
an idle Status-row qualification alone cannot accept the shipping client.

The prepared session uses a fresh backup, exact-image Program/download/Run,
five-document restore and the existing 31 genealogy regressions, read-only
equivalence/group/scan measurements, then pinned-copy genealogy rollback,
original host-document restoration and 31 baseline regressions/final checks.
The contract choice alone did not approve that scope; preparation required
separate current exact-image authorization under AGENTS §3a.

The subsequent exact-image grant, `call_0aa6207bba714a73bb1e80ee242d1981:0`,
was **“Approve guarded S4a qualification”**. That session is now complete and its
approval consumed. The [runtime record](Evidence/AB_S4A_COHERENCE_RUNTIME_2026-10-25.md)
qualifies the eight initial groups: 798 Good, two Uncertain with no payload,
all groups above the declared threshold and with counter progress. Accepted
window median/p95/max is 1,227.7 / 1,451.4 / 2,223.0 µs under 10,000 µs.
All 31 candidate and 31 restored-baseline checks, 4,428-path/type equivalence,
replays and final checks pass. Genealogy and original documents are restored.
This confirms feasibility for those groups; it does not accept full tiers or
active workloads, change the protocol, activate V2 or authorize another session.

## Independent S4 work already implemented

Two internal headless Dart components have no station/declaration dependencies:

- `CipTemplateDecoder`: exact attribute-5 sizes/array strides, full 12-bit
  handles, packed BOOLs, byte-counted UTF-8 strings, exact BigInt 64-bit/time
  values, bounded expansion, malformed-layout and non-finite-number refusal.
- `CipReadCoherenceGuard`: one bounded row/group acquisition, including odd/
  changed counters, interval/deadline failure, lost connections and strict
  revision validation. It returns no bytes for non-Good results. The binding
  object is supplied explicitly; it does not guess PLC symbols.

Physical decoder goldens contain eight records from hash-verified accepted
genealogy and press captures, compared with the independent Python decoder.
These are decoder/guard foundations, **not a completed CipSessionClient**.
Wire discovery, logical snapshot assembly, isolates, read tiers, repository
read-only presentation, spike retirement and live acceptance remain in S4.
