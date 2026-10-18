# Fraktal I/O architecture and code ownership

This document expands normative Core §10.2.1. If this guide conflicts with Part I, Part I wins.

## 1. The intended split

```text
approved I/O list ──> project I/O catalog ──> module role identity
          │                    │                        │
          │                    └──> Core topology <─────┘ diagnostics by exact tag
          │                           │
          v                           v
raw mapped GVL <──> hardware driver <──> semantic HAL <──> reusable CM
                              │
                              └──> live topology values ──> generic HMI
```

The split follows one rule: **project facts stay project-specific; reusable algorithms stay in the
framework; device behavior sees semantic HAL roles only.** A long catalog is acceptable because it is
the approved engineering list. Repeating generic loops and validation beside every catalog is not.

## 2. Ownership

### Framework

`FB_IoTopologyPublisher` and `ST_FieldbusTopology` own bounded storage, range checking, duplicate
tag/path detection, mapping status, health propagation, and exact-tag diagnostic correlation. They do
not contain Beckhoff terminal names or project tags. `I_FieldbusScanner` supplies detected topology and
master health behind the same table.

### Project I/O catalog

`FB_<Project>IoCatalog` is one-shot engineering data. It joins each approved tag to its physical
address, localization key, unique audit path, owning module path, direction, and semantic device role.
It may configure typed role records such as `ST_CylinderIoIdentity`. It does not run every scan and
never reads `%I/%Q`.

### Physical and simulation drivers

`FB_<Project>IoDriver` is the only POU allowed to access `GVL_<Project>IO` and evaluated safety aliases.
It converts physical polarity/scaling into typed HAL fields, writes final ordinary outputs, and updates
the live topology values. A simulation driver implements the same semantic boundary with plant models;
the Unit and CMs are unchanged.

### Modules

A CM knows `ExtendedFb`, not `_101B202A`; it knows “extended sensor timeout,” not “EL1809 Ch5.” The
project catalog injects that physical identity for diagnostics. EMs and Units sequence module commands
and never access the mapped GVL.

### Composition root

`MAIN` is deliberately boring: instantiate, call one-shot setup, choose physical or simulation driver,
publish the control domain, execute the Unit, apply the documented final output authority, and refresh
drivers. Individual tags, terminal addresses, duplicate loops, and domain-device construction do not
belong there.

## 3. Scan order

1. Read real or simulated inputs into HALs.
2. Update evaluated safety/control-domain data and process inputs.
3. Execute root Units.
4. Apply the project output-authority withdrawal layer.
5. Write physical outputs or advance the simulation plant.
6. Refresh fieldbus values, quality, and diagnostic correlation.

This order prevents a module scan from overwriting a final withdrawal and prevents stale output values
from being presented as the current fieldbus state.

## 4. Press example

The training press implements the pattern with:

- `GVL_PressIO` / `GVL_PressSafety`: mapped symbols only;
- `FB_PressIoCatalog`: the supplied workbook's approved metadata and cylinder-role identity;
- `FB_PressIoDriver`: physical HAL mapping, output mapping, and live topology refresh;
- `FB_PressSimulationDriver`: simulated input boundary and cylinder plant models;
- `FB_PressControlDomain`: cage/pneumatic-domain description and aggregation;
- `FB_PressOutputAuthority`: explicit ordinary-PLC final withdrawal policy;
- `MAIN`: composition and scan ordering;
- `FB_IoTopologyPublisher`: reusable Core mechanics shared by future projects.

## 5. CI checks

A project should fail CI when:

- a raw mapped GVL is referenced outside its declared Hardware Driver;
- `MAIN`, an EM, or a Unit references `%I/%Q` or the raw I/O GVL;
- an approved tag or unique channel path is duplicated;
- a catalog entry lacks address, localization key, or owning module path;
- a module embeds a project electrical tag instead of receiving identity;
- a project reimplements Core topology loops or diagnostic matching;
- detected terminal/channel addresses do not join exactly once to the approved catalog.

The eventual workbook importer should generate the project catalog and its parity test. Manual catalog
code is an interim transparent representation, not a second source of truth.
