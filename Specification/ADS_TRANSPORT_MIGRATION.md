# Plan — migrate the PLC transport to ADS, keep OPC UA as an HMI-side option

**Goal.** Make **native (TwinCAT) HMI ↔ PLC communication run over ADS** directly,
eliminating the TF6100 OPC UA server from the hot path. **Keep OPC UA available on
the HMI side** as a peer transport, so a future non-Beckhoff PLC (Siemens, Rockwell,
any OPC-UA-capable controller) integrates by pointing the *same* HMI at an OPC UA
endpoint. One HMI, two PLC-facing transports, one internal contract.

Status: **Phases 0–4 delivered and proven live (2026-07-23).** The ADS transport
is implemented and working end-to-end against the press demo on a real TwinCAT
4026 runtime — no TF6100. Measured: full-tree discovery renders the forest
through the **unchanged** mapper; steady-state snapshot **~15 ms** (sum-read);
mode-change round trip **~86 ms median** through the production repository path.
Reconnect handle-pool leak fixed 2026-07-23 (port-close bulk-release; ~330 ms
reconnects, no handle exhaustion). Remaining: Phase 5 (device notifications,
optional) and first-snapshot handle-creation batching. See "Delivered" below.

---

## 1. Why ADS (what it fixes)

The whole recent effort — TF6100 licensing, the mandatory TOFU init, the
`AdsIncreaseDynSymPool` / `0x00000710` handle-pool floods, the read-tier and
config-manifest work — was fighting **TF6100's cost**, not OPC UA the protocol.
TF6100 maps every OPC UA node read onto an ADS symbol handle; at ~17k nodes it
churns its handle pool and stalls. ADS removes that layer entirely:

| Pain (measured on the press demo) | ADS effect |
|---|---|
| TF6100 install + license + TOFU init before any data | **Gone** — ADS is the native runtime protocol; no server to license/initialize. |
| `0x710` handle-pool bursts, ~1 s command stalls | **Gone** — ADS reads by variable handle/symbol directly; no OPC-UA→ADS remap. |
| Publication obscuring (`OPC.UA.DA`) to shrink the tree | Still useful but less critical — ADS reads only the symbols requested. |
| Config manifest to keep the OPC UA surface small | Still valuable as a *read-batching* strategy; see §5. |

ADS also gives **sum-commands** (batched multi-symbol read/write in one call) and
**notifications** (server-pushed on-change), which map cleanly onto the tiers we
already designed.

## 2. The design principle — one internal contract, two transports

The HMI is already written against a transport-neutral seam
(`OpcUaSessionClient` → `snapshot()` / `write()` / capabilities), and the
repository/mapper consume a flat `fraktal.opcua.snapshot.v1` **browse-path
document**. **That contract stays.** ADS becomes a new implementation of it.

```
                 ┌─ AdsSessionClient  ──(TwinCAT.Ads)──▶  TC runtime  (native, default)
OpcUaRepository ─┤
   (unchanged)   └─ NativeOpcUaClient ──(open62541)────▶  any OPC UA PLC  (Beckhoff TF6100,
                                                            Siemens, Rockwell, …)
```

- **Rename intent, not code, later.** `OpcUaSessionClient` is really a
  *"FraktalSessionClient"*: browse-path snapshots + writes + optional
  bulk-read/tier/notify capabilities. Keep the concrete class names for now to
  avoid churn; a later cosmetic rename (`OpcUaSessionClient` → `PlcSessionClient`)
  is a pure refactor tracked as a separate low-priority item.
- **The browse-path is the wire identity for both.** ADS symbols in TwinCAT are
  addressable by name (`MAIN.PneumaticPress.Status.State`). The mapper's paths use
  `/` separators and the `PLC1/MAIN/...` prefix that TF6100 adds; the ADS client
  maps between the two with a deterministic rule (§4), so the **mapper and every
  view stay byte-for-byte unchanged**.

## 3. Transport selection (which client the HMI builds)

Extend the connection model so a native build can pick ADS or OPC UA:

- `ConnectionSettings.endpoint` already carries a scheme. Add `ads:` alongside
  `opc.tcp:`:
  - `ads://<AmsNetId>:<port>` (e.g. `ads://127.0.0.1.1.1:851`) → `AdsSessionClient`
  - `opc.tcp://host:4840` → `NativeOpcUaClient` (unchanged; the multi-brand path)
  - `ws(s)://…` → gateway (Web, unchanged)
- Native default flips to **ADS-local** (`ads://127.0.0.1.1.1:851`) for the
  TwinCAT case; OPC UA stays a first-class choice in the wizard for a remote or
  non-Beckhoff PLC. (This mirrors the existing `kDefaultEndpoint` platform switch.)
- **Web cannot do ADS** (no raw sockets, same reason it cannot do OPC UA TCP): Web
  keeps the gateway, and the gateway may itself speak ADS or OPC UA to the PLC —
  an implementation choice hidden behind the same gateway protocol.

## 4. `AdsSessionClient` — what it implements

A new client in the `fraktal_opcua_client` package (or a sibling
`fraktal_ads_client`) implementing the existing capabilities:

| Contract method | ADS realization (pin-and-verify each) |
|---|---|
| `snapshot()` | On first call: read the symbol upload table (`ADSIGRP_SYM_UPLOADINFO2` 0xF00F, then `ADSIGRP_SYM_UPLOAD` 0xF00B) to discover the Fraktal contract symbols; cache handles. Then **sum-read** the fast-tier symbols and emit the same `{protocol, paths, values, dataValues, namespaces?}` document. |
| `write()` / `writeBatch()` (`OpcUaBatchSessionClient`) | `ADSIGRP_SYM_VALBYHANDLE` (0xF005) write, or a **sum-write** for the mailbox commit-last transaction — one ADS sum-command replaces the 10 sequential OPC UA writes, so the mailbox is atomic and faster. |
| `readValues()` (`OpcUaBulkReadClient`) | One ADS **sum-read** of the given handles — this is the ack-poll / on-demand path; already the fast path in the repository. |
| `setSlowPaths()` / `setExcludedPaths()` (`OpcUaTieredReadClient`) | Same tier bookkeeping; excluded symbols simply are not in the cyclic sum-read. **Optionally upgrade** to ADS **device notifications** (on-change push) for the live tier, retiring polling entirely (§5). |
| `close()` | Release notification handles + symbol handles; close the ADS port. |

**Isolate boundary stays.** Like `NativeOpcUaClient`, ADS calls run in the worker
isolate; the UI isolate never blocks. The native library is `TwinCAT.Ads` (there
is a C ABI `TcAdsDll`, and a .NET `TwinCAT.Ads` — the FFI/interop choice is a
build decision, verify availability on the target).

**Path↔symbol mapping.** Establish one rule: ADS symbol
`MAIN.PneumaticPress.Status.State` ⇄ mapper path
`PLC1/MAIN/PneumaticPress/Status/State`. The `PLC1/` server prefix is
TF6100-specific; the ADS client either (a) prepends a synthetic `PLC1/` so the
mapper is unchanged, or (b) the mapper is taught the prefix is optional. Prefer
(a) — zero mapper change.

## 5. Read strategy on ADS (tiers → sum-commands / notifications)

The tiering we built maps onto ADS *better* than onto OPC UA:

- **Fast tier** → one **sum-read** per refresh (or, better, **device
  notifications** with an on-change server push + a max cycle time; the repository
  then updates on push instead of polling).
- **Slow tier** (Safety/ControlPower) → sum-read on the heartbeat, unchanged
  cadence.
- **On-demand** (fieldbus, module drill-downs) → sum-read only while the scope is
  active, unchanged.
- **Config manifest** → the `QUERY_CONFIG` mailbox still works verbatim over ADS
  (it is just symbol reads/writes); OR, since ADS reads only requested symbols,
  the obscured `OPC.UA.DA := '0'` members could simply be read by ADS directly on
  demand without the manifest. **Keep the manifest** initially (no PLC change) and
  revisit as an optimization.

The `0x710`/handle-pool problem does not exist on ADS, so the *reason* the tiers
were urgent is gone — but the tiers still reduce traffic and are worth keeping.

## 6. Fieldbus over ADS (bonus alignment)

`FIELDBUS_ADS_ADAPTER.md` Path A already reads the EtherCAT master via ADS on the
PLC and publishes `ST_BusNode[]`. With an ADS HMI transport, the fieldbus tree is
just more symbols in the same sum-read — no separate mechanism. The on-demand
fieldbus scope maps directly onto an ADS sum-read of the topology symbols.

## 7. What does NOT change

- The PLC contract (`ST_ModuleStatus`, `ST_HmiRequest/Response`, `ConfigRev`,
  `QUERY_CONFIG`) — ADS reads/writes the same symbols OPC UA did.
- `OpcUaRepository`, `OpcUaSnapshotMapper`, every widget, the read-tier classifier,
  the config-manifest hydration, `ScopedPlcRepository`.
- The OPC UA client — it remains, fully functional, as the multi-brand path.
- The gateway/Web transport.

## 8. Migration phases

| Phase | Deliverable | Risk / verify |
|---|---|---|
| **0. Spike** | Bare `AdsSessionClient.snapshot()` reading `Status/Name` + `State` for one root over `TwinCAT.Ads`; prove the same mapper renders it. | ADS lib availability + FFI/interop; symbol-name↔path rule. |
| **1. Read path** | Full fast-tier sum-read + discovery (symbol upload) + the `PLC1/` prefix rule; module tree renders live over ADS. | Sum-read size limits; handle caching + invalidation on download/online-change. |
| **2. Write path** | `write`/`writeBatch` as ADS sum-write; mailbox commands (mode/start/stop) ack over ADS. | Commit-last atomicity via sum-write; sequence/ack semantics identical. |
| **3. Capabilities** | `readValues` (ack/on-demand), tier bookkeeping; parity with the OPC UA client so the repository is transport-agnostic. | Reconnect/online-change recovery (ADS router loss); mirror the OPC UA session-loss handling. |
| **4. Transport select** | `ads://` scheme in the wizard + settings; native default = ADS-local; OPC UA still selectable. | Endpoint validation; AmsNetId/port entry UX. |
| **5. Notifications (opt.)** | Replace fast-tier polling with ADS device notifications (on-change push). | Notification handle limits; max-delay/cycle tuning; teardown on close. |
| **6. Retire TF6100 from the native default** | Docs + first-project guide updated: native uses ADS; TF6100/OPC UA becomes the *remote / multi-brand* option. | Keep TF6100 bring-up docs for the OPC UA path; do not delete. |

Phases 0–2 deliver the responsiveness win; 3–4 make it the default; 5 is the
"never poll again" upgrade; 6 is documentation.

## 9. Acceptance

- [x] Native HMI connects `ads://127.0.0.1.1.1:854` with **no TF6100 running** and
      renders the press demo module tree (root + 7 children via the unchanged mapper).
- [x] Mode change round-trip **< 100 ms** — measured **~86 ms median** through the
      production repository path (vs the ~5 s the OPC UA/TF6100 path first showed).
- [x] The **same build**, pointed at `opc.tcp://…` or `ws(s)://…`, still connects
      via OPC UA / the gateway — multi-brand path intact (factory branches on scheme).
- [x] On-demand exclusion works over ADS (excluded paths are off the snapshot,
      served by `readValues`); fieldbus/drill-down scopes reuse the same mechanism.
- [ ] Reconnect after an ADS router restart / PLC online-change recovers cleanly,
      queues no writes (§14), and re-discovers symbols. **(hardening — see below)**
- [x] Web (gateway) unaffected; full HMI suite green (108 tests).

## 10. Delivered (Phases 0–4)

- **C++ bridge** `native/ads/fraktal_ads_bridge.{h,cpp}` wraps `TcAdsDll`:
  connect by AmsNetId:port, **datatype-table walk** discovery (SYM_UPLOADINFO2
  `0xF00F` + SYM_UPLOAD `0xF00B` + SYM_DT_UPLOAD `0xF00E`, recursive member
  expansion), value handles (`0xF003`/`0xF005`), **sum-read** (`0xF080`) for the
  whole fast set in one round trip, typed writes, and the on-demand excluded set.
  Emits the identical `fraktal.opcua.snapshot.v1` document.
- **CMake** `native/ads/CMakeLists.txt` builds `fraktal_ads.dll`, installed next
  to the runner; **self-skips** when not Windows or `TcAdsDll` is absent (the HMI
  then uses OPC UA) — so non-TwinCAT native builds are unaffected.
- **Dart** `AdsSessionClient` (isolate worker, FFI to the bridge) implements the
  same `OpcUaSessionClient` + bulk-read + tier capabilities; the native factory
  branches on the `ads://` scheme; the wizard accepts `ads`; the Windows default
  endpoint is `ads://127.0.0.1.1.1:851` (OPC UA still selectable). Mapper,
  repository, and views are untouched.

## 11. Remaining / hardening

- **Handle-pool leak on reconnect — FIXED (2026-07-23).** The Dart worker reuses
  one bridge context and re-issues `connect` on reconnect; the bridge opened a new
  AMS port without closing the old, orphaning the entire prior value-handle set
  (~2.7k) on the PLC symbol server. A few cycles exhausted its pool —
  `CAdsWatchServerR0::AdsParseSymbol no more handles` flooding the log, plus a
  `MailboxFull` overrun. Fix: every teardown path (`reconnect`/`disconnect`/
  `destroy`) now **closes the AMS port, which bulk-releases all its handles in one
  operation** — not ~2.7k synchronous `SYM_RELEASEHND` round trips (which measured
  ~21 s/reconnect). `pruneFieldbus` still explicitly releases the handful of
  dropped-slot handles it created mid-discovery (port stays open there). Live:
  6 reconnects, **~330 ms each**, stable `nodeCount=14866`, zero handle errors
  (`live_ads_client_test.dart` reconnect-stress test). `AdsSessionClient.reconnect()`
  re-runs connect on the same worker for the repository-level session-recovery path.
- **First-snapshot cost** (~2.3 s): discovery creates ~1.6k value handles
  one-by-one. Batch via the sum handle-by-name service (`0xF082`) or defer
  non-fast-tier handle creation until first on-demand use.
- **Phase 5 (optional)**: replace fast-tier polling with **ADS device
  notifications** (server on-change push) to retire polling entirely.
- **Sum-command index groups** (`0xF080`/`0xF082`) are Beckhoff well-known but not
  in this SDK's `TcAdsDef.h`; verified working on the pinned 4026 runtime, but
  keep the per-symbol fallback (already in place) for other versions.

## 12. Honest boundaries

- ADS is Beckhoff-specific by design — it is the *native fast path*, while **OPC UA
  remains the portable, multi-brand path** kept first-class on the HMI so the
  standard's O8 (portable) and O5 (flexible connectivity) hold. A future
  Siemens/Rockwell PLC integrates by pointing the same HMI at `opc.tcp://…`.
- This work changes **transport only**. The module contract, the HMI widgets, and
  the reference PLC application are untouched — the same mapper renders both
  transports, proven by reusing every existing test.
