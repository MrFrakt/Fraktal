# TIA candidate contracts

`TIA_FROZEN_CONTRACTS_V1.json` records the implemented S7-1500 subset, derived
from Core DUTs, the binding and the native HMI datatype adapter. Core remains
authoritative. This baseline is a compatibility check, not a copy for the
generator to consume and not a declaration that the entire TIA port is done.
The file's SHA-256 is bound in Part IV. Preserve V1 when adding a reviewed,
versioned successor; the checker has no rewrite/rebaseline mode.

From the repository root:

```powershell
python tools/check_tia_contracts.py
python -m unittest tools.test_check_tia_contracts
python tools/check_tia_contracts.py --generated FraktalCore/PLC/Siemens/Examples/PressDemo/generated --native <native-export-directory>
```

The ordinary check runs in pre-commit and hosted CI. It freezes ordered record
fields, logical/native types, declared widths, defaults and publication flags;
referenced Core enum ordinals and capacities; the sequence publication's
declaration-derived dimensions; and the HMI datatype map. Private runtime
storage and station-specific application types are outside this baseline.

The optional package/export checks require **all 31 frozen UDTs**, as consumed
by the full-profile press bench. They check all three external-access flags,
field order, types and bounds, rejecting missing or duplicate records. Point
them at the source package and native XML export directory, respectively, not
at evidence archives containing multiple copies. Native checks verify compiled
interfaces; behavioral qualification still requires the existing native probes.

**R3 remains OPEN.** This draft subset does not qualify S7-1200, OPC UA, clock
synchronization, coherent multi-read snapshots, physical hardware, unimplemented
facets, or persistence under destructive loss. Adding a frozen declaration
does not allocate it in a station; the generator retains consumed-size tables.
