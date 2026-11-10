# Reusable module compile fixture

`make_fixture.py <out>` writes one compilable package holding every reusable
module type that no shipped station instantiates: `FB_ClampEM` (with its two
`FB_CylinderCM` children), `FB_ConfigurableCylinderCM`, `FB_SeparatorCM`, their
typed sequence APIs, the shared sequence runtime and `FB_ConfigurableCylinderSim`.

Types are bound by `fraktal_tia_examples.module_type`, the press's own binder,
so reason numbers come from the TC3 module reason list and nowhere else. The
root Unit declares a sequence view only because the APIs bind against the chain
runtime it brings in.

`fraktal_tia_gate.py --native` compiles this package in a fresh reserved project
and verifies the native read-back; it is never downloaded. See
[the first native run](../../../../../Specification/Siemens/Evidence/TIA_P9_MODULES_NATIVE_2026-11-10.md).
