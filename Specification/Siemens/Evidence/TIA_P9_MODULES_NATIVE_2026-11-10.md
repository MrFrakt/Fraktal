# First native compile of the P9 module types (2026-11-10)

The P9 commit `e52acff6a` reported "TIA Portal V20 native compilation (286
replayed sources, 0 errors, 0 warnings)" and "93/93 assertions". Neither run
contained the P9 types: 286 is the press source replay, and the native gate
compiled only the fixed Operations fixture. `FB_ClampEM`,
`FB_ConfigurableCylinderCM`, `FB_SeparatorCM`, their typed APIs and the
configurable-cylinder simulation block had never been through the TIA compiler.

## What was run

[`Tests/ReusableModules/make_fixture.py`](../../../FraktalCore/PLC/Siemens/Tests/ReusableModules/make_fixture.py)
composes the three types (and the cylinder the clamp owns) under one root Unit
with a sequence view, plus the four typed APIs, the shared sequence runtime and
the simulation block. Each type is bound by `fraktal_tia_examples.module_type`,
the same function the press uses: command labels from the type's own catalog,
band reasons from the TC3 `PL_ModuleReasons` list. The P9 unit test previously
typed those reason numbers in by hand; it now reads the fixture's declaration.

`fraktal_tia_gate.compile_fresh` imported the revision into a new reserved
project (CPU 1516-3 PN/DP V3.0, approved driver unchanged), compiled it and
compared the native export with the generated sources.

| Run | Outcome |
|---|---|
| `P9_Modules_20261110_01` | import refused `16_SequenceServices.scl`: `FRK_SequenceLifecycle` and `FRK_DiagSummary` unknown. The typed APIs bind against the chain runtime, which a Unit's `sequence_view` brings in; the fixture now declares one. Not a module defect. |
| `P9_Modules_20261110_02` | every source imported; compile 2 errors, both in `FB_ConfigurableCylinderCM`: "Parameters of the function or the function block do not match the transferred formal parameters". |
| `P9_Modules_20261110_03` | 123 sources, compile **0 errors / 0 warnings**; read-back matches 300 canonical objects, 91 type interfaces and 16 DB interfaces. |

Run directories are under `%LOCALAPPDATA%\Fraktal\TiaSpikes`; projects under
`%LOCALAPPDATA%\Fraktal\TiaStations` with the same names. Run 03's sorted
source-set digest is `95b304d374e2c2219b87e09e20cdbf385df56b87405302ecdfebd2404a90f453`;
its `build.log` SHA-256 is `447f45c7e939c158c4af92015c2ca9128b36f389a9a6f50128c1cba8980861d4`.

## The defect

`configurable_cylinder_logic.scl.in` set `OutCmd.ReachedPosition` with
`SEL(#Device.TargetWork, 1, 2)` in both completion branches. STEP 7 V20 refuses a
positional `SEL`. Both calls now use `SEL(G := …, IN0 := DINT#1, IN1 := DINT#2)`;
the values are `E_CylinderPosition.HOME`/`WORK` of the TC3 module enum, so the
behaviour is unchanged. A new `tia_lint` rule, **T-FORMAL**, rejects a
positional `SEL`; it reports both lines of run 02's sources and passes run 03.

## Gate change

The native stage of `fraktal_tia_gate.py` now compiles and reads back this
fixture in a second fresh project on every run, beside the Operations fixture.
The reusable modules are compiled, never downloaded.

## Limits

This is a compile and read-back gate only. No P9 type has run on a controller:
T2 (first-out reason and `SourcePath`), T3 (interlock withholds the output) and
the clamp's child-rollup behaviour remain untested natively. Host gates at this
change: 286 tool tests, `tia_lint` 0 findings, `check_consistency --strict`
0/0, candidate contracts clean.
