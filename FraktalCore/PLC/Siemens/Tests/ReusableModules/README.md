# Reusable module bench

`make_fixture.py <out>` writes one package holding every reusable module type
that no shipped station instantiates: `FB_ClampEM` (with its two `FB_CylinderCM`
children), `FB_ConfigurableCylinderCM`, `FB_SeparatorCM`, their typed sequence
APIs, the shared sequence runtime and `FB_ConfigurableCylinderSim`. It also
writes `assertions.json` and `image_hash.json` for the native runner.

Types are bound by `fraktal_tia_examples.module_type`, the press's own binder,
so reason numbers come from the TC3 module reason list and nowhere else. The
root Unit declares a sequence view only because the APIs bind against the chain
runtime it brings in.

`Main` is a case driver, not the composition: one case per scan, an injected
`FRK_Clock.NowMs`, the root called exactly as the composition calls it, then
`FRK_TestAssert`. The 46 assertions mirror the TC3 suites for these types.
`bench.json` reserves the unmapped test CPU `FrkModulesTest` (`.57`).

`fraktal_tia_gate.py --native` compiles the package in a fresh project and
verifies the read-back; `--bench` downloads it to that test CPU after the
Operations suite and reads the result. See
[the native runs](../../../../../Specification/Siemens/Evidence/TIA_P9_MODULES_RUNTIME_2026-11-10.md).
