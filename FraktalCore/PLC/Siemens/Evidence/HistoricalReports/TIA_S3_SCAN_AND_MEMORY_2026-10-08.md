# Fraktal/TIA — S3 first measurements: memory and per-module scan cost, bench 1214C (2026-10-08)

**What this records.** The first S3 (scale & memory) numbers on the physical CPU, and
one frame-design change they forced: the **quiescent fast path** for idle modules.
Raw material: [`TIA_S3_SCAN_AND_MEMORY_2026-10-08/`](TIA_S3_SCAN_AND_MEMORY_2026-10-08/)
(numbered in order, failures included).

| Item | Value |
|---|---|
| Target | CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0` FW V4.7.3 @ 192.168.0.10, serial `S V-P9FT7791`, identified by `s7_probe.py ident` before **each** of the six downloads |
| Authorization | owner: bench free to use (2026-10-08); "go on" after S3 was named as the next step |
| Toolchain | TIA Portal V20 / Openness V20, `Fraktal.Tia.Cli` build `h2hnPuq1…` (whitelisted) |
| Images | S2 (`Spikes/S2_Shape`) and scale variants built from copies by `make_scale.py`: the S2 sources plus `FB_SpkScale` holding N extra cylinder CMs, called every scan after the composition root (`"SpkScale"()` in OB1) |

## 1. Where the CPU's memory use can be read

- Openness: **no** per-block load/work-memory attribute (`01`: every attribute of an
  FB, an instance DB and an FC listed — sizes absent).
- S7comm: SZL `0x0013`, `0x0113`, `0x0B13` **refused** by the 1214C V4.7.
- Web API V1.473: no memory method.
- **System web page `Diagnostics > Memory`** (`/Portal/Portal.mwsl?PriNav=Online&SecNav=Memory`)
  reports load, work and retentive memory for a user with the `WebAllowDiagnostics`
  right. A separate UMAC user `fraktal-diag` (role `FraktalDiagnostics`, that right
  only) was added (`diagnostics_user_1214c.plan`, `02`) and downloaded with `um=reset`
  (`03`); the gateway user `fraktal` stays at read/write process data. Login is a form
  `POST /FormLogin` with the page's own `Origin`/`Referer` (without them: HTTP 400).

## 2. Results

**Memory of the S2 image** (`04`, `05`): load **327.7 KB** of 4096 KB (7.9 %), work
**19.62 KB** of 150 KB (13.1 %), retentive 0 of 14 KB — framework FCs, two cylinder
CMs, one Unit, the SCL chain, the self-test harness, the TCP result server, the
registry and the clock.

**Cycle time** — the PLC's own `FRK_Clock` (`Scans` over 10 s, `CycleMs` samples) read
over the Web API; all modules idle after the harness finished:

| Image | Mean cycle | Δ per extra CM | Harness |
|---|---|---|---|
| S2 | 2.115 ms | — | 17/17 |
| S2 + 10 CMs, array of multi-instances called by loop index | 4.391 ms | +0.228 ms | 16/17 ¹ |
| S2 + 10 CMs, named statics called by name (generated form) | 4.128 ms | +0.201 ms | 16/17 ¹ |
| S2 + 10 **empty-body** CMs (same interface and data), named | 2.506 ms | +0.039 ms | 17/17 |
| S2, CM with **quiescent fast path** | **1.875 ms** | — | **17/17** |
| S2 + 10 CMs with quiescent fast path, named | **2.406 ms** | **+0.053 ms** | 16/17 ¹ |

¹ Expected and only this: harness case 10 asserts exactly three registered modules;
the extra CMs register (actual 13). Every other row passed. Empty-body CMs do not
register, so that image passes 17/17.

Reading:
- An idle CM cost **≈ 0.20 ms per scan** on the 1214C: ≈ 0.04 ms is the FB call with
  its parameters, ≈ 0.16 ms the lifecycle frame (`FRK_Begin`/`FRK_End`) re-deriving an
  unchanged READY state. A loop-indexed array of modules adds ≈ 0.03 ms per call.
- **Quiescent fast path** (`30_CylinderCM.scl`): the generated frame skips the
  lifecycle while the module is initialised, READY, `Execute`/`Abort` low and no
  edge, hold or one-shot is pending; identity setup and derived `OutImm` still run
  every scan. It is semantically identical — the hardware harness passes 17/17
  including abort and no self-resume (T4), timeout fault and first-out (T2),
  HELD and resume (T3), the Unit's verbatim rollup (T6) and operator reset — and
  brings an idle CM to **≈ 0.053 ms**, close to the 0.039 ms call floor.
- Projection for a press-sized S7-1200 load (30–60 mostly idle modules): ≈ 1.6–3.2 ms
  of module overhead per scan with the fast path, against ≈ 6–12 ms without it.

## 3. Not yet measured — and why

- **Memory per CM.** After the first scale download every `POST /FormLogin` (both
  users) returned 302 to the start page with no session cookie, while the Web API
  login of the same users kept working. The likeliest cause is the CPU's session limit
  filled by this session's own legacy-page logins, which were never logged out (the
  page's "Logout" only clears the browser cookie); CPU restarts by download did not
  clear it. Attempts were stopped rather than repeated, so as not to prolong a possible
  brute-force lockout. `s3_measure.py` now closes its session when the page offers a
  logout. Owed: work memory of S2 + N CMs (N = 10, 30) for the per-instance cost.
- The Unit FB does not yet use the fast path (one per root; CMs are the multiplier).
- Memory and scan cost of the real generated types (registry capacity, step table,
  alarm ring, configuration) — the fixture types are minimal.

The bench was left running an S2 + 10 CM scale image at the time of this record; it is
restored to the plain S2 image afterwards (see the plan's §11 for the record of that).

## 4. Later the same session — memory per CM, and the bench restored

Appended; §1–§3 were not changed. Logs `22`–`31`.

- **The web-page lockout** (§3) was not a user-data effect: a download with
  `um=reset` did not clear it (`22`). It ended ≈ 33 minutes after the last good
  login (`23`), consistent with a ~30-minute session timeout on a web server that
  keeps running while the PLC program stops and starts for a download. The page's
  logout is `GET /FormLogin?LOGOUT`; the CPU closes the TCP connection right after
  it (`23`: `RemoteDisconnected`), which `s3_measure.py` now expects. Every later
  measurement logged out (`27`, `31`: `web_logout`).
- **Work memory, quiet frame, named CMs** (`24`, `27`, `31`):

| Image | Work memory | Load memory | Mean cycle | Harness |
|---|---|---|---|---|
| S2 (quiet frame), restored from the repository sources | **19.68 KB** (13.1 %) | 327.7 KB | **1.872 ms** | **17/17** (`30`) |
| S2 + 10 named CMs | 31.66 KB (21.1 %) | 348.2 KB | 2.406 ms | 16/17 ¹ |
| S2 + 30 named CMs | 54.90 KB (36.6 %) | 378.9 KB | 3.182 ms | 16/17 ¹ (registry full at 15 → overflow flag, fails closed) |

  Per CM (N = 10 → 30): **≈ 1.16 KB work memory** (instance data incl. its strings,
  its HAL struct and the call) and **≈ 0.039 ms cycle**; N = 0 → 10 gives ≈ 0.053 ms
  including the scale block's own call. The quiet guard itself costs ≈ 60 bytes of
  code (19.62 → 19.68 KB).
- **Reading for the S7-1200 profile** (a hypothesis until the real generated types
  are measured — the fixture CM carries no alarm ring, step table or configuration):
  a fixed framework of ≈ 20 KB leaves ≈ 130 KB, i.e. on the order of 100 minimal CMs,
  or a press of ~15–30 real modules if a real type is several times larger. Cycle:
  ≈ 2 ms + 0.04–0.05 ms per idle module.
- **Bench state at the end of this record:** the plain S2 image from
  `Spikes/S2_Shape` (quiet frame) is running, 17/17; web users `fraktal` and
  `fraktal-diag`; the station project holds the same image.

## 5. Source identity of the committed fixture

The `Spikes/S2_Shape` sources committed with this record (with the quiescent fast path in
`30_CylinderCM.scl`) are the bytes of the image restored in §4 (17/17): `sha256sum *.udt *.db *.scl | sha256sum`
= `9589d492633670c851c7e188487fc67efd16e90cbe15f5cd87dcd83ad4222d65`. The S1W record's `ffa03293…` identifies the image before the fast path.
