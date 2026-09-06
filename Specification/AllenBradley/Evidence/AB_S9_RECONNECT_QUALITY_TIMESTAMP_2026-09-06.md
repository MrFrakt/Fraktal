# Fraktal/AB S9 — reconnect discovery, quality codes and timestamp mapping (2026-09-06)

**Spike:** S9 repository and mailbox conformance — reconnect/quality/timestamp leg

**Result:** **Three more S9 remainders are measured. Reconnect is cheap and
repeatable across fully independent sessions; the controller distinguishes two
different bad-path conditions and fails them faster than it serves a good read;
and the timestamp source is measured as unsynchronized with PTP disabled. The
wall-clock read is deferred, not widened. S9 remains OPEN.**

**Date:** 2026-09-06

**Repository revision at start:**
`92dd4fb`

## 1. Scope, and why this record is licence-free

Every measurement here was taken with the repository's own fixed-vector probes
running on CPython `3.14.7` plus hash-pinned `pylogix 1.1.5`, installed with
`pip --require-hashes` into a virtual environment **outside** the repository.
The raw EtherNet/IP probe uses only the Python standard library.

**No Rockwell licensed tooling was used, and none could have been.** The
workstation this ran from carries Studio 5000 and a Logix Designer SDK whose
entitlement could not be established — see
[`AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md`](AB_R1_WORKSTATION_BASELINE_ADDENDUM_2026-09-06.md)
and §6 below. That is precisely why this leg was chosen: it needs no Studio, no
SDK, no activation, and no controller change. Nothing in this record depends on
any licensed product, so nothing in it inherits that doubt.

**Controller-changing operations: none.** No download, mode change, tag write,
fault clear, clock set, firmware, network configuration, safety or SD-card
operation occurred. Every probe used is read-only by construction; the one tool
here that *can* change state refused to, and §5 records that refusal.

**Target, verified immediately before use:** `1769-L24ER-QB1B/A LOGIX5324ER`,
revision `33.014`, serial `7036B510`, at `192.168.100.89:44818`, state `3`,
device status `48`. Every probe below was run with its `--expect-serial`
guard and every run reported `serial_matches: true`.

## 2. Reconnect discovery

D2 leaves reconnect behaviour owed. Two independent measurements were taken.

### 2.1 Encapsulation session round trip

`fraktal_ab_eip_probe.py`, 15 samples. Each sample is a complete
ListIdentity plus RegisterSession/UnregisterSession cycle.

| Statistic | Value |
|---|---|
| minimum | **5.278 ms** |
| median | **14.470 ms** |
| maximum | **20.361 ms** |

### 2.2 Fully independent client sessions

`fraktal_ab_symbolic_read_probe.py` invoked as six separate operating-system
processes, so each run establishes a new TCP connection, registers a new CIP
session, reads one tag, and unregisters — no state is shared between runs.

| Run | First-read elapsed | Status |
|---:|---:|---|
| 1 | 7.523 ms | `Success` |
| 2 | 5.210 ms | `Success` |
| 3 | 4.422 ms | `Success` |
| 4 | 4.391 ms | `Success` |
| 5 | 4.619 ms | `Success` |
| 6 | 7.064 ms | `Success` |

**Six of six succeeded on first attempt**, spread 4.391–7.523 ms.

### 2.3 Declaration

**Reconnect requires no warm-up and no rediscovery negotiation.** A gateway that
loses its session re-establishes and serves a correct first read inside the
declared live/fast poll period of 100 ms
([`AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md`](AB_S8_S9_REFERENCE_STATION_DECLARATIONS_2026-09-06.md) §B.3)
with a worst observed cost of 20.361 ms — about a fifth of one period. The
reconnect budget is therefore declared as **one poll period**, and a reconnect
that has not produced a good read within **three** periods is declared a fault
rather than a slow start, matching the three-missed-poll freshness rule.

**Not claimed:** this measures reconnect after a *clean* session close. It does
not measure recovery from a severed cable, a controller reset, or a session
invalidated mid-read; those remain owed, and no number here should be cited for
them.

## 3. Quality codes

D2 leaves quality codes owed. `fraktal_ab_symbolic_read_probe.py` read four
scalars, one array, and two deliberately invalid paths in a single session. The
probe reports status, value shape and elapsed time, and **redacts every value**
(`values_redacted: true`).

| Case | Tag | `status` | `kind` | `size` | Elapsed |
|---|---|---|---|---:|---:|
| gen | `FRK_S9_Generation` | `Success` | int | 1 | 5.337 ms |
| rev | `FRK_S9_DataRevision` | `Success` | int | 1 | 4.065 ms |
| scan | `FRK_S9_ScanCount` | `Success` | int | 1 | 3.879 ms |
| done | `FRK_S9_Complete` | `Success` | bool | 1 | 3.665 ms |
| data | `FRK_S9_Data`, 16 elements | `Success` | list | 16 | 3.716 ms |
| absent | `FRK_S9_NoSuchTag` | **`Path segment error`** | none | 0 | 1.845 ms |
| wrongtype | `FRK_S9_Generation.BadMember` | **`Path destination unknown`** | none | 0 | 1.862 ms |

### 3.1 What this settles

**The controller distinguishes two different bad-path conditions**, and they are
not interchangeable:

- **`Path segment error`** — the tag *name* does not resolve in the controller's
  symbol table. The symbol is absent.
- **`Path destination unknown`** — the tag resolves but the *member path* beneath
  it does not. The symbol exists and the request was shaped wrongly for it.

That distinction matters to a gateway, because the two demand different
responses: the first means the manifest and the controller disagree about what
exists and discovery must re-run; the second means the reader's own path
construction is wrong and re-reading will never fix it.

**Bad paths fail faster than good reads succeed** — 1.845/1.862 ms against
3.665–5.337 ms. A wrong tag costs roughly half a good read, so a fail-closed
reader pays no latency penalty for being strict.

### 3.2 Declared quality mapping

| Observed CIP result | Declared Fraktal quality | Reader obligation |
|---|---|---|
| `Success` | **Good** | serve the value with the read timestamp of §4 |
| `Path segment error` | **Bad — symbol absent** | never serve a stale prior value; mark the point unavailable and trigger rediscovery |
| `Path destination unknown` | **Bad — path invalid** | mark unavailable; do **not** retry the same path, and raise a configuration fault |
| no response / timeout | **Bad — communication** | apply the §2.3 reconnect budget, then fault |
| value older than its tier threshold | **Uncertain — stale** | serve, but never silently as current |

Fail-closed throughout: no bad or uncertain result is ever presented as Good,
and the HMI renders Bad and Uncertain points as unavailable rather than
substituting a last-known value (Core §11.2, AB §3.13).

**Not claimed:** these are the statuses this controller produced for these two
fault shapes. Partial-read, privilege-denied and connection-size-exceeded
statuses were not provoked and are not mapped here.

## 4. Timestamp mapping

`fraktal_ab_eip_probe.py` read CIP Time Sync Object `0x43`, instance 1:

| Attribute | Value |
|---|---|
| `ptp_enabled` | **`false`** |
| `is_synchronized` | **`false`** |

Both were re-read across the 15-sample run and did not change.

### 4.1 Declaration

Logix carries **no per-tag timestamp**. A value read over CIP symbolic access
arrives with no time of its own, so the timestamp a Fraktal client sees is
manufactured by the gateway and must say so:

- The value's timestamp is the **gateway's read completion time**, not a
  controller-side acquisition time. Its accuracy is bounded by the read cost
  measured in §3 — single scalars 3.665–5.337 ms — plus the poll period of the
  tier the point belongs to.
- Because `is_synchronized` is `false` and `ptp_enabled` is `false`, every value
  from this station carries **`TimeSynchronized = FALSE`**, exactly as S1
  settled for AB §2.7. Fraktal preserves that quality explicitly rather than
  presenting an unsynchronized clock as authoritative.
- **Cross-controller ordering is therefore not claimed** for this station. Two
  values from two controllers cannot be ordered by their timestamps without
  separately proved CIP Sync, which this controller does not have enabled.

## 5. What was deferred rather than widened

`fraktal_ab_time_probe.py` reads the controller `WallClockTime`, which would
have given the third timestamp input directly. It **refused to run**:

```json
{ "error": "fixture fingerprint failed; clock was not set",
  "passed": false, "set_performed": false, "set_requested": false,
  "serial_matches": true }
```

The probe fingerprints the S1 Phase 0 fixture, and the controller holds the S9
coherence fixture instead — S9 replaced it on 2026-08-14. The refusal is the
tool working correctly: it is armed for one exact fixture and declines anything
else, and it confirmed `set_performed: false`.

**The fixture guard was not widened, and the probe was not modified.** The
guard is a safety property, not an obstacle. The `WallClockTime` reading stays
owed until either the S1 fixture is resident again or a probe is authorized for
the S9 fixture. The §4 declaration does not depend on it: PTP state and
synchronization flag came from the CIP Time Sync object, which needs no fixture.

## 6. Standing on the workstation's entitlement

This record was produced on the 2026-09-06 engineering PC after its Studio 5000,
Logix Designer SDK and Logix Echo entitlements were found unestablished, and
after the SDK was observed completing project operations while FactoryTalk
Activation logged `UNSUPPORTED: "LDSDK.EXE" ... No such feature exists (-5,346)`
at the exact timestamps of those operations. On the user's instruction, **no
gate evidence is being produced from any Rockwell licensed product on this
machine**, and the SDK-created artifacts from that fact-find were discarded.

Nothing in this document was produced by, or depends on, a Rockwell licensed
product. Its measurements come from the repository's own probes speaking
EtherNet/IP to a controller that is reachable regardless of workstation
licensing.

## 7. Status after this record

| Item | Before | After |
|---|---|---|
| S9 reconnect discovery | owed | **measured and declared** (§2) |
| S9 quality codes | owed | **measured and declared** (§3) |
| S9 timestamp mapping | owed | **declared**; `WallClockTime` read deferred (§4, §5) |
| S9 overall | OPEN | **OPEN** — the shared contract suite and the mailbox matrix remain owed |
| R4, R5, R6 | OPEN | OPEN — unchanged |

S9 does not close. The adapter-agnostic repository contract suite is
implementation work gated behind R0–R6, and the mailbox matrix is owed only when
writes are enabled. **The claim remains read-only.**

## 8. Commands

```
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_eip_probe.py 192.168.100.89 \
    --expect-serial 7036B510 --samples 15

python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_symbolic_read_probe.py 192.168.100.89 \
    --expect-serial 7036B510 \
    --tag gen=FRK_S9_Generation --tag rev=FRK_S9_DataRevision \
    --tag scan=FRK_S9_ScanCount --tag done=FRK_S9_Complete \
    --tag absent=FRK_S9_NoSuchTag --tag wrongtype=FRK_S9_Generation.BadMember \
    --array data=FRK_S9_Data,16

python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_time_probe.py 192.168.100.89 \
    --expect-serial 7036B510 --samples 7      # refused: fixture fingerprint
```

The reconnect series in §2.2 is the symbolic-read command above reduced to the
single `gen` tag and run as six separate processes.
