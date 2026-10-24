# AB Capacity forecasting method — 2026-10-21

Non-normative engineering tool, requested by the owner to reduce repeated
manual Capacity reviews. The first implementation forecasts from the generated
L5X and hash-bound Studio measurements. A qualified automatic Studio collector
now obtains the actual offline Capacity Estimate as well. Both tools perform
no controller operations; forecasts and measured estimates remain distinct.

`fraktal_ab_capacity_estimate.py` counts allocated array capacity recursively,
including unused slots. It combines an unpacked data-storage model with four
units per ST token. BOOL scalars occupy four model units, and modeled records
round to eight units; these deliberately conservative modeling choices are
**not** a claim about exact Template offsets. Initial values and comments do
not contribute to the score. Shared types allocate storage for every instance.

For successive measured images, the tool derives:

```
score = modeled data units + 4 * ST tokens
slope = change in measured Used Standard blocks / change in score
estimate = latest measured usage + score growth * median observed slope
planning budget = latest usage + 1.5 * score growth * largest slope + reserve
reserve = max(65,536 blocks, 5% of total capacity)
```

The conversion to **Blocks** is empirical. No equality between Blocks and bytes
is assumed. The margin is a planning policy, not a proven upper bound.

The forecast currently accepts only the measured 1756-L81E v38 profile. It
refuses changed I/O, tasks, AOIs, native chart structures or opaque storage,
nonmonotonic calibration, smaller target scores, mismatched totals, corrupted
reference artifacts and Capacity records that do not bind the named ACD.
Such changes need a new model or direct measurement. This prevents an
apparently small score from hiding an unmodeled allocation.

## Independent S3a check

Only genealogy and S2 were used to fit the first slope. S3a was held out:

| Result | Blocks |
|---|---:|
| Forecast Used Standard | 826,044 |
| Owner Studio measurement | 817,476 |
| Forecast error | +8,568 (+1.0481% of measured usage) |
| Planning budget including reserve | 1,023,731 |
| Controller total | 3,145,728 |

The held-out measurement falls within the planning budget. One held-out
surface establishes neither a universal error bound nor acceptance near the
capacity limit. S3a is now available as an additional observation for future
forecasts; it was excluded from this validation calculation.

## Use in subsequent stages

Run the forecast automatically during offline preparation, using
[the hash-bound observations](AB_CAPACITY_OBSERVATIONS_2026-10-21.json):

```powershell
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_capacity_estimate.py `
  --observations Specification/AllenBradley/AB_CAPACITY_OBSERVATIONS_2026-10-21.json `
  --source <new-generated.L5X> --output <new-capacity-forecast.json>
```

Every result explicitly reports `measured=false` and
`acceptanceGateSatisfied=false`. The tool supplies an automatic budget and
early fit warning; it does not forge the existing session helper's exact
Capacity fields. The per-stage measured Capacity gate remains in effect and
can now use the qualified automatic measurement below. A forecast alone never
satisfies it.

The installed C# SDK 2.1.974 XML API documentation was inspected: its
`LogixProject` methods expose no Capacity/memory-estimation query. The
[Rockwell SDK guide](https://literature.rockwellautomation.com/idc/groups/literature/documents/gr/ldsdk-gr001_-en-p.pdf)
directs developers to the API documentation for supported functions. No Studio
window was visible during the initial S3a investigation. S3b preparation
subsequently opened a hash-checked offline review copy and qualified the UI
collector below; the earlier observation is not a continuing limitation.

## Automatic Studio measurement, qualified during S3b preparation

`fraktal_ab_studio_capacity.py` invokes `Invoke-AbStudioCapacity.ps1` against
the pinned ACD. The collector verifies its SHA-256, makes a unique review copy,
and opens only that copy in hidden Studio. It verifies the new process's exact
filename, L81E/v38 window identity and Offline state before opening Controller
Properties. The Properties command comes from the installed menu resource.
It selects the qualified Capacity page, records two stable samples from the
Standard panel, cancels Properties and closes its review process. It never
opens the source ACD or invokes controller operations, Apply or Save.

Normalization requires the source hashes before/after and review initial hash
to equal the expected pin, exact label/control pairings, Standard-panel
parentage, two equal samples, `used + available = total`, positive total, and
the displayed truncated usage percentage. Offline state and process closure
must both pass. A failed capture remains evidence and reports
`Measured=false`, `VerifiedFit=false`. Successful receipts report
`Measured=true`, `VerifiedFit=true`, `Provider=StudioUIAutomation` and bind the
raw capture hash plus Studio/resource hashes. Units remain **Blocks**.

The qualified profile is **1756-L81E, Studio v38, English UI**, on this host.
Studio executable SHA-256 is
`FA02C3DA1ED3777B779A28CA7BF84AFB3BD7EFBFB0795AE170F7374815EEB217`;
`LogixACENU.dll` SHA-256 is
`B9384996C78012443F7C51A216D833D74F942437476AF3646F03155DB5FCDB88`.
Other hardware, language or UI revisions need qualification before their
measurements replace an owner review. UI arithmetic/identity mismatches fail
instead of guessing. This is Studio's offline estimate, not measured online
controller memory or a substitute for completed download/native scan gates.

| Qualification | Used / Available / Total Blocks | Displayed |
|---|---|---:|
| Owner S3a screenshot, sealed | 817,476 / 2,328,252 / 3,145,728 | 25% |
| Automatic S3a reference, exact same original ACD pin | 817,476 / 2,328,252 / 3,145,728 | 25% |
| Automatic S3b candidate | 991,612 / 2,154,116 / 3,145,728 | 31% |

All reference fields match exactly; both source pins were unchanged and both
review processes closed. The S3b helper accepts this measured provider and
validates exact-artifact/baseline arithmetic before deployment. Routine
screenshots are no longer required on this qualified setup.

```powershell
python FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_studio_capacity.py `
  --acd <pinned.ACD> --expect-sha256 <64-hex-pin> `
  --output <new-capacity.json> --capture-output <new-ui-capture.json>
```

Use new output paths for every run. The tool leaves the unique review copy
outside the evidence archive; native ACDs and credentials are never archived.
Keep the source pinned through preparation and do not repin it after SDK saves.

The S3b holdout forecast used only genealogy/S2/S3a: 977,992 blocks versus
991,612 automatically measured, error -13,620 (-1.3735%). Its planning budget
1,229,016 contains the measurement, but this second holdout still establishes
no guaranteed error bound. S3b remains excluded from the current calibration
so the check is reproducible.

Raw validation, tests, measurements, the retained S3a capture failure and
source bindings are in
[S3a runtime evidence](Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21.md).
