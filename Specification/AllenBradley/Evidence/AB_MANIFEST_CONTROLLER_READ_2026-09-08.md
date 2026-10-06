# Fraktal/AB — reading the manifest off the controller

**Spike:** S7 manifest — closing the discovery read the publication record left
owed

**Result:** **A client reads the whole manifest off the bench controller in ten
requests and 91 ms, and every published row equals the declaration it was
generated from.** The publication record
([`AB_MANIFEST_PUBLICATION_2026-09-07.md`](AB_MANIFEST_PUBLICATION_2026-09-07.md))
proved the manifest was correct *in the project* and explicitly did not claim it
had ever been read from a running controller. That is what this record closes.

**Date:** 2026-09-08

**Repository revision:** `6518d33`, plus the read-shape correction recorded in
§4

**Scope:** one authorized manual download to the isolated bench, and five
executions of a read-only harness. **No write of any kind was issued** — no tag
write, mode change, fault clear, clock set, firmware, controller-network, safety
or SD-card operation. The harness has no write path in it.

## 1. The target, checked immediately before the download

```
product name  1769-L24ER-QB1B/A LOGIX5324ER
revision      33.014
serial        7036B510           serial_matches: true
address       192.168.100.89:44818
```

The artifact downloaded:

```
source L5X   press13.L5X    510,630 bytes
             F7A5D752620F371821AE30168966FC6988438B8ECC7787F8F44E291AF0F4D61E
ACD          press_manifest.ACD   2,413,881 bytes
             7B284EA502939507DCB58B6498E791D3DD0699611911694C87C1E2CCD6E4DC0E
SDK import   Warnings 0, Errors 0
Studio v33   0 errors, 0 warnings, "0 of 12 Messages"
```

The download itself was **a manual operation performed by the authorized
operator**, over USB. That is not a convenience: automated download is recorded
as unavailable on this bench (3/3 failures across two mechanisms), and the
manual step is the declared narrowing in the S5 CI path.

## 2. What the controller returned

Every field of the header, read off the controller:

```
Magic               1179795787  ('FRAK')      SchemaMajor         1
ContentHash         42334AD69FD1A3AB          SchemaMinor         0
ConfigRevision      4338506                   CoreVersion         1
ControllerIdentity  1769-L24ER-QB1B/A 33.014  BindingVersion      1
KeyLength           48                        FrameworkVersion    1
Valid               1                         Truncated           0
```

| table | published count | capacity | declared rows | rows equal |
|---|---|---|---|---|
| Roots | 1 | 4 | 1 | yes |
| Modules | 4 | 16 | 4 | yes |
| Nameplates | 0 | 16 | 0 | yes |
| Fields | 142 | 192 | 142 | yes |
| Operations | 5 | 32 | 5 | yes |
| Localization | 206 | 224 | 206 | yes |
| Rationalization | 12 | 32 | 12 | yes |
| OptionalProfiles | 0 | 8 | 0 | yes |

**22,112 bytes, no findings.** Only the declared rows are compared: the slots
past a table's count are capacity, not content, and demanding they match would
be asserting that unused space has a value.

The strings survived the whole path — declaration to L5X to ACD to controller to
CIP — including the 44-character key `project.reason.two_hand_released.consequence`
that a 32-character string would have truncated into a collision.

## 3. Coherence, and the cost

The S7 protocol, unchanged: read `ConfigRevision`, read every table, read it
again, accept the snapshot only if it did not move. It did not move on any run.

| run | requests | header | tables | recheck | total |
|---|---|---|---|---|---|
| 1 | 10 | 30.0 ms | 58.1 ms | 2.8 ms | **90.9 ms** |
| 2 | 10 | 38.6 ms | 61.4 ms | 2.8 ms | **102.8 ms** |
| 3 | 10 | 38.4 ms | 62.2 ms | 2.7 ms | **103.3 ms** |

Per table, one request each:

```
Localization  12,544 bytes  16.9 ms      Operations   1,024 bytes   5.7 ms
Fields         6,144 bytes   9.3 ms      Rationaliz.    768 bytes   5.8 ms
Modules          640 bytes   5.8 ms      OptProfiles    128 bytes   4.5 ms
Nameplates       576 bytes   4.8 ms      Roots           80 bytes   4.5 ms
```

The connection negotiated at **4002 bytes** (pylogix's default forward open; the
size was not forced). So this compares against S7's 4000-byte figure — 43,728
bytes in 62 ms — and not its conservative 500-byte one. Half the data at a
comparable rate; nothing here contradicts the S7 budget.

## 4. The first measurement was the harness, not the controller

The first bench run passed every comparison and reported **526 requests and
1,465 ms**. Every table had fallen back to reading row by row — including
`Roots`, which is 80 bytes and could not plausibly need it.

That should not have been recorded as a controller cost, and it was not. The
cause:

```
Read("FRK_Press_MfRoots")      -> Success, 20 bytes    (row zero)
Read("FRK_Press_MfRoots", 4)   -> Success, 80 bytes    (the array)
```

An array read issued **without an element count returns element zero and
succeeds**. It does not look like the wrong question; it looks like a short
reply, which is exactly what the fallback was written to survive. So the harness
degraded silently into a 526-request read and reported it as a measurement.

Passing the element count takes the whole manifest in ten requests. The 90 ms
figure above is the corrected one; the 1,465 ms figure measured a defect in this
repository and is recorded here so it is not mistaken for a property of the
controller.

**What the fallback is worth keeping for.** It still guards a real case, and the
run now records which path each table took, so a future run that falls back says
so rather than quietly costing 500 requests.

## 5. The negative tests

A probe that cannot fail is not evidence.

* **The serial guard refuses.** Aimed at the same controller with
  `--expect-serial DEADBEEF`, the harness reads the identity, refuses, exits 2,
  and **issues no manifest read at all**: `serial 7036B510 is not the expected
  DEADBEEF; refusing to read a controller this vector was not aimed at`.
* **The comparison can report every difference it claims to check** — wrong
  content hash, wrong controller identity, `Valid = 0`, `Truncated = 1`, wrong
  key width, a count disagreeing with the declaration, a single changed row, and
  a table that read short. Ten offline tests, each pairing the check with the
  fault it must catch.
* **The decoder is tested against a byte image built independently**, the way
  Logix lays a structure out, rather than against its own packer — because
  checking a parser with its own packer proves only that it agrees with itself.

That last test earned its place: it found that the comparison **could not fail**
when a table read back empty. The mismatch loop walked zipped pairs, and an
empty read zips to nothing, so a wholly failed table read compared equal. A
short read is now reported as one.

## 6. What this does and does not settle

Settled: the manifest is generated from the declaration, survives import,
Verify, download and CIP read intact, and a client can take it off the
controller cheaply and coherently.

Not settled, and still owed: the registry, the event core, release/access
enforcement and the provider seam. The manifest publishes zero where those do
not exist rather than pretending otherwise. Nameplates stay empty because no
module declares one. And the gateway that will consume this — the adapter and
the generic HMI — is not written; this record only proves the surface it will
read is real.
