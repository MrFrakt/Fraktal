# Fraktal/AB Phase 6 item 4 — data classes on hardware

**Date:** 2026-10-02, America/Bogota. **Source:** `9b07e47`.
**Result:** press64's guarded data-class fixture passes **18/18**, all hardware
regressions pass, and final restoration/readback passes. The owner replied
“done” after the requested Verify/download and gateway restart. This authorizes
the named verification fixtures on serial **7036B510**; it does not authorize
other controller administration. The companion
[JSON](AB_PHASE6_DATA_CLASSES_ON_HARDWARE_2026-10-02.json) retains the raw suites,
preflight, session preparation/restoration, timings and source hashes.
The [offline build record](AB_PHASE6_DATA_CLASSES_BUILD_2026-10-02.md) remains
historical and unchanged.

## Loaded build and prerequisites

Target is `192.168.100.89`, `1769-L24ER-QB1B/A`, firmware `33.014`, with a
10 ms periodic task. Each harness checks the exact serial and declaration
fingerprint before its fixture writes. The entire major-4 manifest is coherent
and equal to the declaration: **80,760 bytes**, ContentHash
`7E0EC4F58C126852`, ConfigRevision **8261316**, Fields **563/768** and
Localization **565/768**. Initial read took 170.905 ms; final and repeat reads
took 172.241 and 171.458 ms. The owner artifact `C:\work\press64.L5X` has SHA-256
`A07AC994DAA8EC27F181FB52333364F9BBABAD7B2E0896ADFE5DB8A42830A339`.
The gateway reports `status=ready`, `plcReady=true` before and after verification.

The first unarmed preflight refused its anonymous-start prerequisite because
the owner had already logged in as `phase6_admin`, level 4. It performed no
writes. A fresh serial/fingerprint/stopped-state check preceded a mailbox
LOGOUT to prepare the role-test baseline. The original admin session is restored
after all suites. The positive set regression authenticates admin because its
calibration record now requires ENGINEER; no class or action policy is lowered
to make that fixture pass.

## Data-class hardware proof

The fixture passes all four prerequisites and fourteen behavior rows:

- With DATA_READ/DATA_WRITE raised to ENGINEER, OPERATOR still sees and changes
  the `public` station number. Its actual controller value changes from 1 to 2.
  Built-in values retain their metadata with Readable=FALSE and blank ValueText.
- A native WRITE_CONFIG claiming the admin name remains denied under the
  operator's actual session. Capture also checks the effective value write level.
  An operator cannot lower class policy through SET_CLASS_LEVEL.
- TECHNICIAN cannot write pressure calibration. Lowering its class write level
  to OPERATOR leaves the immutable effective minimum at ENGINEER. ADMIN changes
  the actual pressure calibration from 450 to 451.
- OPERATOR saves a set with CONFIG_SET open while DATA_READ is higher. A later
  TECHNICIAN load refuses at `station.airPressureMinKpa` before any value changes;
  the changed public station number remains unchanged by that refusal.
- TECHNICIAN export refuses before even the header returns, leaving the returned
  document blank and naming `station.ramExtendLimitMs`. ADMIN load restores the
  saved public value and ADMIN export returns the document.
- The calibration denial audit identifies the actual technician, value and
  required level: `std.audit.dataAccessDenied: phase6_tech [kind=19, gate=1]
  [value=station.airPressureMinKpa, required=3]`, sequence 22. The native request's
  claimed admin identity grants no role and does not replace the audit actor.

Eight successful data-fixture authentications settle in **550.139–590.057 ms**,
including the in-process gateway, CIP staging/acknowledgement and correlated
controller result read. These timings do not measure Chrome rendering or the
full native-PIN fallback. Maximum task scan is 5,129 microseconds before and
after this fixture, then **5,259 microseconds** after the access regression,
against a **10,000-microsecond** period. Overlap count and major/minor fault bits
remain **zero** throughout. No timing counters or fault bits were cleared.

## Regressions and final restoration

| Suite | Result |
|---|---|
| Data classes | 18/18 |
| Controller access | 16/16 |
| Capture / read-only configuration query | 10/10 |
| Parameter sets | 17/17 |
| S3 health/timing, before and after | 6/6 each |
| Principles parity across ST/SFC/LD | 25/25 |
| Phases 1, 2, 3, 4, 5 | 7/7, 6/6, 8/8, 11/11, 25/25 |

Every fixture restores its settings and disarms its inputs. Final independent
readback confirms station number 1, pressure calibration 450, baseline 950,
AUTO mode and CONTINUOUS style, all twelve action thresholds NONE, both class
read/write policies NONE, timeout zero and all ten fixture inputs zero. The
owner's prior `phase6_admin` session is restored at level 4, with LoginBusy and
LoginFailed both zero. The Unit is stopped without Error. The positive set
fixture restores every station value and leaves its isolated store empty;
existing station documents are untouched.

The offline AB suite passes **1,448 tests**; consistency reports **0 errors,
0 warnings**, and its suite passes **33 tests**. PLC and HMI source are unchanged
from `9b07e47`, so the build's eleven killed mutations, 439 passing HMI tests,
six skips and verified HTTPS release deployment remain its offline evidence.
No agent download, gateway start/restart, firmware/network change, clock set or
fault/counter clear was performed during this verification.

Item 4's data-class runtime gate is accepted. **Item 5, alarm shelving, is next.**
The v33 legacy zone-and-conduit bench remains write-enabled by the 2026-09-29
decision. This gate covers its class edits and per-value checks; it does not
mark the full **write-enabled S9 claim** met. Physical retention across power
cycle, download and upgrade also remains owed.
