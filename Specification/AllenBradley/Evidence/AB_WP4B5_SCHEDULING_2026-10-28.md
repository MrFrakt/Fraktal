# S4b WP4b.5 scheduling continuation — 2026-10-28

**The original-tier checkpoint's rehearsal prerequisite remains open. No native
session is prepared or run.** Echo stays on genealogy throughout, with passing
read-only preflights before and after each rehearsal. No download, mode/tag
write, fault/TASK-counter clear, clock/power/vendor-state operation or Echo
termination occurs. Nothing is committed or pushed.

This supersedes the implementation checkpoint in
[the earlier rehearsal record](AB_WP4B5_REHEARSAL_2026-10-28.md), which remains
immutable. The [payload manifest](AB_WP4B5_SCHEDULING_2026-10-28/artifact_manifest.json)
binds the raw logs, failed checks, source snapshots, screenshots and receipts.

## Retained implementation

- Logical native rows sharing a published counter can use one bounded body
  packet between separately completed counter reads. Count dependencies are
  deduplicated within that packet; every logical row retains its own reply
  cursor and count validation. Counts are discovered in drained dependency
  levels before descendant arrays expand.
- A phase's paths/layouts/packets are planned before opening wire proofs.
  Coalesced reply decoding waits until the phase's wire proofs finish. Planning
  and decoding CPU cannot consume a neighboring connection's proof window.
  Execution still refills at most four serial-pinned connections, one
  outstanding request per socket, and drains started work on failure.
- The small Core discovery header (Name, ModuleType, State and available
  ConfigRev/TypeKey) is acquired coherently near the end of a walk. It is not
  reread under a second retry budget. Large diagnostic/device rows retain
  their data and independent proof. A torn-header regression withdraws every
  affected identity payload instead of keeping old modules visible.
- A completed failed-attempt post read may be the next attempt's pre read.
  Its actual I/O start remains the window/source timestamp. The 10.1 ms
  counterexample still refuses. No attempt or total deadline is renewed.
- Slow acquisition is its own bounded worker operation. Fast envelopes can
  retain independently aged slow values; slow I/O does not extend the fast
  acquisition bracket. A fair serial operation queue alternates waiting cyclic
  and background work and preserves all control/profile/connection fences.
- Optional atomic tier installation avoids waiting behind a safe complete
  profile; legacy three-operation updates still block snapshots while unsafe.
  Duplicate tier updates are suppressed. Reconnect restores the latest complete
  profile before exposing the connection. The path vector is sent once per
  discovery rather than every third snapshot.
- Configuration rows are cached only under freshly validated owner-version
  headers at both ends of each query. Version/session changes discard cached
  values and policy; inactivity expires the lease. Partial coherent rows may
  survive a refused query, but an incomplete page is never returned. Unselected
  bank payloads never enter assembly. The exact four sealed pages and reconnect
  invalidation pass through real sockets. Small fetch batches let cyclic reads
  run between configuration operations.
- Trace delivery fields now apply **only to snapshot replies**. Adding them
  to a configuration descriptor made its later canonical equality comparison
  always refuse with `Read service changed during acquisition`. The trace-on
  sealed-page counterexample fails before the correction and passes afterward.
- The public-read acceptance panel uses the existing in-memory content API,
  remains logged out/read-only, waits for complete tab/tree inventory, and
  requires LIVE before and after screenshot encoding. The expected 31 views,
  seven modules and three bus nodes are never reduced.

No PLC schema, scalar type, array bound, projection/oracle value, write gate,
coherence acceptance rule, source-age calculation or freshness limit changes.
The original fast fallback for published configuration is active in the final
source. The temporary tier experiment below is not retained.

## Apparatus calibration

The peer serves the same pinned capture
`B0EBFBD06853FBAF1262C3B74549F88F99BD9AF37E1585844DC5B9A4291AFB4A`.
The piecewise latency quantiles stay 440/1,276.5/6,974/16,290 us at
0/50/95/100 percent; counters advance by two every 10 ms and are odd for the
first millisecond. No model draw or latency tail is shortened to pass.

Dart fractional timers could return before their requested delay or overshoot
by a timer tick. The peer now yields and rechecks a monotonic deadline. The
same-draw scalar control records median realized delay 2,962 →1,401 us,
median RTT 3,479.5 →2,134.5 us and minimum overshoot −981 →0 us. These are
CLI controls, not Flutter or native acceptance measurements. Requested/realized
samples and their truncation flags are retained in every later peer log.

Immutable native-tag/packet encodings are memoized in bounded peer caches.
Every request still incurs its delay draw. Counter-containing packets bypass
those caches; explicit counter advancement and byte-equivalence tests pass.
The post-cache packet control changes median scaled atomic-batch RTT only
1,936.5 →1,928 us; it does not resolve the full original-tier rehearsal.
Neither this cache nor the deadline correction makes a native timing claim.

## Rehearsal results and the rejected tier experiment

All labelled runs remain in `Runtime/`; `rehearsal_summary.json` identifies
their source, coverage, age and failure. Mapped maxima alone cannot qualify a
run: they omit the waiting interval in which the previous sample can expire.

| Run | Result |
|---|---|
| Profile 21, seed 7 | Provisional full coverage; 31 views, max 429.972 ms |
| Profile 22, seed 8 | Three child modules lost after a torn Status group; seven completed captures |
| Profiles 23/24/25, seeds 8/7/9 | Three provisional consecutive full passes; 31 views each; maxima 393.105/433.729/423.702 ms |
| Debug 02, seed 8 | Provisional comparison: STALE at `after-overview`; no completed capture |
| Profile 26, original tiers | STALE waiting for complete root tabs; 18 mapped samples, max 359.196 ms; one completed view |
| Profile 27, original tiers, peer cache | Same coverage failure; 13 mapped samples, max 382.676 ms; one completed view |
| Profile 28, overdue-poll experiment | Same coverage failure; three mapped samples, max 588.659 ms; one completed view; experiment reverted |
| Debug 03, final original-tier source | STALE at `after-overview`; one mapped sample, max 459.602 ms; no completed capture |

The provisional passes used a fallback that moved activation-static
configuration containers to the metadata heartbeat. Plan §3 prohibits changing
a tier rule to make a gate pass. That fallback was **reverted**. The old
`rehearsal_analysis_02.json` is explicitly superseded by
`rehearsal_analysis_02_superseded.json`; it does not authorize native preparation.
The valid consecutive profile count on the final original-tier source is
**zero**. Current source matches profile 27 and debug 03 by all bound HMI hashes.

The [230-path read-tier review](../AB_CANONICAL_PUBLICATION_S4B_METADATA_TIER_REVIEW_2026-10-28.md)
proposes a CIP-only capability rather than changing other transports. Its
inventory contains Meta 186, AvailableModels 8, Catalog 18, ModePolicy 8 and
Nameplate 10 leaves before exact manifest replacements. It explicitly changes
their delivery latency. After these checks, the owner approved O8 with
“Approve CIP configuration heartbeat (Recommended)”
(`call_a7b096025e8b4393802914b727457fab:0`). Its dependent implementation is next;
the source sealed here still has the original tiers. Provisional passes remain
historical and do not qualify that forthcoming source.

Other discarded experiments remain recorded: an advisory publisher-phase
predictor, a zero-timer/microtask polling change, single-row and larger
configuration batches, and intermediate packet/tier schedulers. Reversion
receipts bind restored source. Tool/test fixture failures are retained too,
including a callback counter, an invalid oversized batch fixture and an
append-only output collision; none is a new controller failure.

## Gates and measured scope

- **738 HMI tests pass /12 skipped**, analyzer clean,
  `pub get --enforce-lockfile` and Windows profile build pass. Toolchain:
  **Flutter 3.47.5 /Dart 3.13.4**, at
  `C:/work/fraktal-toolchains/flutter-3.47.5`. The AGENTS example SDK path is
  absent. Third-party CMake deprecation output is retained.
- **74 root tests**, AB spec/contracts, strict consistency and whitespace
  pass after the plan/status update. No new localization or PLC source exists.
- All **373 PLC/gate bindings** still match the sealed preparation, transferring
  **2,339 AB tests**, both v38 builds/read-backs and **65% Capacity**. Those
  PLC gates are not rerun here. Image remains
  `30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`.
- Native E1–E9, physical-controller performance and CIP Security are not
  claimed. O7 is not triggered by synthetic runs or cumulative process CPU.
  Every local peer closes gracefully; before/after genealogy preflights pass,
  and all model records show zero controller-changing operations.

## Next and remaining work

Implement and test approved O8, then require three fresh
consecutive final-source profile passes at ≤700 ms, plus the debug comparison.
No prior provisional result substitutes for that gate. Then prepare WP4b.6 /
S4b-Q: all five read-only stages run after the writer fixture even if one fails;
all E1–E9 must pass together, including native desktop/scan and genealogy
rollback with original documents and 31 baseline cases.

S5 gateway/Web/typed commands/installer and S6 legacy retirement,
FileMedium/events/capacity remain. C12 is a later owner-operated browser check.
S7 physical/CIP Security gates remain deferred under O2. O1–O8 are decided.
No stage exit, commit or push is claimed.
