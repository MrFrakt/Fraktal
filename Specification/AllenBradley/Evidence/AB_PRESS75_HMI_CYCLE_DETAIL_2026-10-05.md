# Press75 HMI cycle-detail and reconnect repair - 2026-10-05

The owner confirms that after loading the final polling update, Chrome stays
connected for two minutes with cycle history, Pareto and command timing
populated. The independent production repository check also passes for two
readers over two minutes. Earlier partial repairs and failed runs remain
recorded in the machine record; their results are not broadened into a PASS.

## Cause and resulting behavior

Large detail sweeps included closed-tab rings and sequence rows. Their earlier
batches aged out before renewal, so the mapper correctly withdrew chart data
while station samples and mailbox acknowledgements could remain current. Tab
scoping and shared timestamp-preserving targeted reads passed isolated checks
but did not resolve production expiry under concurrent load.

The shared HMI derives demand from the selected tab's visible, permitted cards
and authored tag bindings. Child timing belongs to its owning root. Budgeted
tiered transports promote only demanded detail to slow snapshots and exclude it
again on close. Native records refresh for shared viewers without repeated
leaf sweeps. Non-tiered transports retain bounded, independently aged detail
reads; parameter-set replies remain explicit request reads.

The remaining whole-app reconnect exposed two complete-sample timing costs.
The client's full RPC allowance counted server acquisition a second time. An
optional responseProcessingMs bracket now removes that processing from the
conservative transit allowance, with a one-millisecond resolution allowance,
strict bounds and legacy compatibility. Source age/timestamps do not change.
Also, a periodic timer skipped to a later tick when a complete read overran its
period. Budgeted polls now resume after completion with one acquisition in
flight; faster reads wait out the declared minimum period.

Good/expiry limits remain enforced. Old detail cannot become usable from a live
station sample. Bad quality, failed native reads and malformed timing metadata
remain unavailable. Partial ACK reads have their own acquisition quality and
cannot renew complete-station health. Native identity/manifest checks, PLC
permissions/releases and authenticated mutation gates are unchanged.

## Evidence and validation

- Machine record: [AB_PRESS75_HMI_CYCLE_DETAIL_2026-10-05.json](AB_PRESS75_HMI_CYCLE_DETAIL_2026-10-05.json), SHA-256 `0E33EC627C3D391EF6BD0929F0290B38E3B290AB0CADB5E3BC2573119E091742`.
- Full HMI: 521 pass, seven deployment-gated skips; analyzer clean.
- Full AB tools: 1,611 pass. No PLC source/generator edit or download occurred.
- JavaScript release build passes. Optional Wasm dry-run output is not a Wasm
  runtime support claim. Root consistency reports zero errors/warnings.
- Production: 480 forest samples across two readers over 120 seconds, with only
  LIVE link states. After initial warm-up, all four reader/stage groups contain
  110 samples each with 26 cycle-history entries and 20 Pareto rows. Door,
  PartSlide and PressRam each retain two command-timing rows. Configuration
  remains at 22 entries; Gantt retains 14 profile steps.
- Maximum complete-snapshot RPC: 661 ms and 675 ms; maximum reported source
  sample age: 648.3453 ms and 638.3465 ms. These are named-bench measurements,
  not guarantees for another station or a representative TC3 forest.
- Each reader issues two complete inert QUERY_CONFIG transactions during
  hydration. Anonymous post-ACK NONE cleanup is refused as required. No login,
  operator command, configuration mutation, mode change or clock write is issued.
- The final HTTPS assets match the staged release byte-for-byte at
  https://press.localhost/. Main JavaScript SHA-256:
  1478306110F01EB7B6BD69214A3C3CD1DD9D479CDE8697858CC902BC4DA8A2FF.
  The previous web root is retained at C:/work/press75_cycle_detail_web_backup_05.

The owner restarted the existing write-enabled gateway. The agent's separately
started QA gateways were read-only, serial-guarded and stopped after use. The
first QA launch command was automatically rejected as blocked by policy; the
safe foreground launch explicitly cleared the process token. Existing Chrome
surfaces were unavailable through browser tools. A standalone web-runner attempt
failed on its external path, and its temporary in-repository retry did not finish
loading and was cancelled. No automated visual browser PASS is claimed; final
visual acceptance is the owner's explicit confirmation.

The record retains the baseline batch expiry, an absent listener, a forty-second
check insufficient to cover the owner's later reconnect, and failed QA during
full test/build load with two native gateways. The final two-minute production
run and owner confirmation supersede those limited outcomes. Source/protocol
regressions cover visibility/access/root demand, disjoint tier updates, source
age/quality, malformed envelopes/brackets, cached record timestamps, expired
station plus fresh ACK, independent expiry and overrun polling without overlapping
acquisitions.

Press75 remains loaded: L5X SHA-256
82AB065C32BCD112D49DD00839B8047C1B5E957A5356FB9D61EF3C1C2F3172A5,
manifest 94E302F650BA1DB5 / 9757442, target 192.168.100.89 / serial 7036B510.
PLC code and memory are unchanged. This record does not complete the remaining
AB port, physical Line retention, other targets, or TC3 latency acceptance.
The AB guide and TC3 prompt carry the shared transport/consumption lessons.
