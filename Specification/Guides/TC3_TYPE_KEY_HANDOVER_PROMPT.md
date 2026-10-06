# Fraktal/TC3 — module type key handover prompt

Copy the fenced text below into a new coding-agent chat opened at the cloned
repository root **on a PC that has TwinCAT XAE installed**. Written 2026-09-27.

This is step 1 of `LOCALIZATION_AND_MODULE_CONTENT.md` §7 — faceplates authored
against a module **type**. It is blocked on the bench workstation only because
a Core DUT changes, and a DUT change needs the TwinCAT compiler plus a library
rebuild and install that no other host here can perform.

`Specification/Guides/TWINCAT_XAE_WORKFLOW.md` still governs every XAE
interaction; this prompt does not replace it.

## Why this is a separate host

| Needed | Where it is |
|---|---|
| TwinCAT XAE, to compile a changed `ST_ModuleStatus` and reinstall Core/Modules | **the new PC** |
| The AB declaration, manifest and projection changes | either host — pure Python, no licence |
| The HMI mapper read and faceplate resolution | either host — Dart |

Only the first row is blocked. Do the TC3 half there; the AB and HMI halves can
be done anywhere and are deliberately **out of scope** for this prompt, so the
two do not collide in the same files.

## What the decision already is

§7.1 is settled and written: a module publishes a **type key** in the catalog
vocabulary, because static text belongs to the front end's dictionaries rather
than to PLC values (§1), and a type is named the same way. Do not reopen it.

What this prompt adds is the observation that **TwinCAT already half does it**.
The reusable module types set a type-scoped display key today —
`FB_ClampEM` uses `std.moduleType.clamp.name`, `FB_CylinderCM` uses
`std.moduleType.cylinder.name` — while an application module uses
`project.module.clampStation.name`. The type/instance split already exists in
the key namespace. It is merely overloaded onto one field, so nothing can read
it as a type without guessing at the prefix.

The change is therefore small and follows an existing path rather than inventing
one: publish the type key as its own member, set through the same
`_M_SetPresentation` call every concrete type already makes.

## The trap that will bite

`_M_SetPresentation` has **11 call sites**, and the pinned 4024 compiler
requires every method input at every call — optional inputs are a 4026+
feature this binding does not use. Adding an input means updating all eleven in
the same change, or the build fails in ten places that each look like a
different problem.

```
FB_PressDemoUnit          project.module.pneumaticPress.name
FB_AirPressureMonitorCM   std.moduleType.airPressure.name
FB_AxisCM                 std.moduleType.axis.name
FB_ClampEM                std.moduleType.clamp.name
FB_ClampStationUnit       project.module.clampStation.name
FB_ConfigurableCylinderCM std.moduleType.configurableCylinder.name
FB_CylinderCM             std.moduleType.cylinder.name
FB_DigitalInputCM         (a variable — instance-configurable)
FB_PowerGroupCM           std.moduleType.powerGroup.name
FB_SeparatorCM            std.moduleType.separator.name
FB_TwoHandStartCM         std.moduleType.twoHand.name
```

`FB_DigitalInputCM` passes a variable rather than a literal. Its **display**
name is configurable per instance and its **type** key is not, which is the
distinction this whole change exists to make — so it takes a literal type key
like every other reusable type.

---

```
Read AGENTS.md first, then Specification/Guides/TWINCAT_XAE_WORKFLOW.md, then
Specification/LOCALIZATION_AND_MODULE_CONTENT.md §7 (especially §7.1).

TASK — publish a module type key from the TwinCAT binding.

This is step 1 of the §7 faceplate work: a layout is authored against a module
TYPE rather than a module path, and §7.1 says a type is identified by a key in
the catalog vocabulary. Nothing published today answers "what type is this?" —
Status/ModuleType separates a Unit from an EM from a CM and stops there, and
the press publishes Door, PartSlide and PressRam as three instances of one
declared cylinder under three different display-name keys.

WHAT TO CHANGE

1. Add `TypeKey : STRING(160)` to ST_ModuleStatus (Fraktal_Core DUTs), after
   DescriptionKey. This is an additive change to a released type, so Core takes
   a minor version step (0.5.0.0 -> 0.6.0.0) and every downstream placeholder
   is re-pinned. Record it in IMPLEMENTATION_NOTES.md with the reason.

2. Add a `TypeKey : STRING(160)` input to FB_ModuleBase._M_SetPresentation and
   assign it to Status.TypeKey beside the two existing assignments.

3. Update ALL ELEVEN call sites. The 4024 compiler requires every input at
   every call — this is not optional, and skipping one produces a wall of
   unrelated-looking errors. Reusable types in Fraktal_Modules take a literal
   `std.moduleType.<type>` (no `.name` suffix — that suffix belongs to the
   display key). Application modules take `project.moduleType.<type>`.
   FB_DigitalInputCM takes a literal type key even though its display name is
   an instance variable; that is precisely the distinction being drawn.

4. A module that sets no type key keeps publishing an empty string. §7.1 makes
   the empty case fall back to the coarse ModuleType scope, so do NOT invent a
   default or derive one from the FB name.

WHAT NOT TO CHANGE

Do not touch the Allen-Bradley tree or FraktalCore/HMI. The AB declaration,
manifest and projection and the HMI mapper are being done on the other host
and would collide. Do not add faceplate resolution, containers, bindings or
display classes — those are later steps and each ships on its own.

RULES THAT APPLY

* Never ship ST behind a disclaimer. "Build not run" in a commit message is not
  a caveat, it is skipping the gate that separates plausible ST from correct
  ST. Compile it.
* Naming: a `std.`/`project.` key is a literal, not an identifier; STRING(160)
  matches the existing key members and is not a guess.
* Changing a LIBRARY means installing it BEFORE the build gate. Core first,
  then Modules — consumers resolve an INSTALLED placeholder, never source, and
  a new member stays invisible to Tests/ until it is installed.

GATES, in the order they get cheaper to fix

  python FraktalCore/PLC/TwinCAT/tools/plc_lint.py            (both profiles)
  python -m unittest discover -s FraktalCore/PLC/TwinCAT/tools \
                              -t FraktalCore/PLC/TwinCAT/tools
  FraktalCore/PLC/TwinCAT/tools/Invoke-TwinCatLibraryInstall.ps1
  FraktalCore/PLC/TwinCAT/tools/Invoke-TwinCatBuild.ps1
  python tools/check_consistency.py
  python -m unittest tools.test_check_consistency

Then the two TcUnit gates on an isolated runtime, per the workflow document:
Tests/Fraktal_Tests.plcproj AND Examples/PressDemo/PressTests.plcproj. They are
separate because XAE rejects a `..` segment in a Compile Include, so a manifest
in Tests/ cannot reach Examples/. Run both.

Every new `std.moduleType.*` / `project.moduleType.*` key needs a catalogue
entry in FraktalCore/HMI/lib/localization/default_catalogs.dart, or
check_consistency reports it as unlocalized — it will render as a raw key at
the operator. That file is HMI, but the keys are yours; adding entries there is
in scope even though the mapper is not.

EVIDENCE

Record the archive revision, XAE/XAR/platform identity, the installed Core and
Modules versions, the build transcript and the TcUnit runner output with counts
and zero failures. A wrong-runner green summary is a failed gate-selection
check, not a pass.

WHEN DONE

Report: the DUT member added, the eleven call sites updated with the key each
now carries, the Core/Modules versions installed, and every gate's result. Then
stop — the AB and HMI halves are being done elsewhere and will be reconciled
against what you publish.
```

## After this lands

The other host adds the AB half (declaration `Module` -> manifest -> projection
publishes the same `project.moduleType.*` key) and the HMI half (mapper reads
`Status/TypeKey`, faceplate resolution keys on it with path override). Those are
mechanical once the contract member exists, and the read-surface gate will
refuse to let the HMI read a key the AB projection does not publish, which is
the cross-check that the two halves agree.
