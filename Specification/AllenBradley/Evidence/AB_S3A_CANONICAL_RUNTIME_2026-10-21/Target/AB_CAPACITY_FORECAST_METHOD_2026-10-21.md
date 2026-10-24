# AB Capacity forecasting method — 2026-10-21

Non-normative engineering tool, requested by the owner to reduce repeated
manual Capacity reviews. The first implementation forecasts from the generated
L5X and hash-bound Studio measurements. It performs no controller operations.

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
Capacity fields. The per-stage measured Capacity gate remains in effect until
an automatic measurement path is qualified or a replacement acceptance rule
is explicitly agreed. That limitation is recorded here so a later agent does
not mistake a forecast for the screenshot it replaces.

The installed C# SDK 2.1.974 XML API documentation was inspected: its
`LogixProject` methods expose no Capacity/memory-estimation query. The
[Rockwell SDK guide](https://literature.rockwellautomation.com/idc/groups/literature/documents/gr/ldsdk-gr001_-en-p.pdf)
directs developers to the API documentation for supported functions. No Studio
window was visible to this session for an automatic UI read. Neither fact
proves that every Rockwell tool lacks such an interface; qualifying one is
the next route to removing routine manual requests.

Raw validation, tests, measurements, the retained S3a capture failure and
source bindings are in
[S3a runtime evidence](Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21.md).
