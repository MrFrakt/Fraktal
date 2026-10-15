# Reference declaration fixtures

`two_root_forest.json` declares three reusable module types and two root Units.
Each Unit owns an EM with two instances of the same CM type. Child names and
types are written once in the owning type; roots carry only their local name
and type. The explicit registry capacity includes headroom and excludes row0.

Validate and derive a new registration inventory:

```powershell
python FraktalCore/PLC/Siemens/tools/fraktal_tia_declaration.py FraktalCore/PLC/Siemens/Tests/Declaration/two_root_forest.json --out "$env:TEMP/Fraktal-declaration-inventory.json"
```

The output records eight module instances in parent-before-child call order,
root/parent indices, exact browse paths, tier ordinals and source hashes.
Widths and ordinals are read from Core's ST_ModuleStatus and E_ModuleType DUTs.
The model rejects CM children, EM-to-Unit containment, recursive multi-instance
types, non-Unit roots, case collisions, unknown/unused types, qualified names
that exceed the Core width, registry overflow and unrecognized JSON fields.

The same declaration now includes typed contract records, a CM HAL and test
reactions for the [frame/registry generator](../Generator/README.md). There is
one authored forest; inventory and PLC assembly derive from it. Source replay
checks apply to generated manifests. Full lifecycle, Unit facets, sequence
integration, capability behavior and retention remain later work; the broader
source linter rules retain their explicit pending scope.
Only the S7-1500 reference family is currently accepted; this fixture adds no
1200 capacity or width policy.
