# Siemens reusable modules

[cylinder.json](ControlModules/Cylinder/cylinder.json) owns the cylinder's contract, storage and command
catalog. [cylinder_logic.scl.in](ControlModules/Cylinder/cylinder_logic.scl.in) adds device reactions to
the generated common frame. [cylinder_api.scl.in](ControlModules/Cylinder/cylinder_api.scl.in) exposes
typed `F_CylinderExtend` / `F_CylinderRetract` operations to every sequence language.
The command identifiers are bound from the catalog, never repeated in a chain.

The frame owns lifecycle, command timing, terminal reset and derived states.
The CM owns feedback interpretation, direction and HAL coils. Both live permits
and a sequence's withdrawal apply to outputs after completion as well as BUSY.
Private Device storage is externally excluded. Parameter-instance alias flags
are stripped by TIA; verify the native browse surface when instantiating chains.
Sequences use the semantic API; raw Execute/Done handling stays in shared code.

Generate the module and its unwired consumers through
[the press example generator](../../tools/fraktal_tia_examples.py). Native groups
place the FB, contract types and API under
`Framework/Modules/ControlModules/Cylinder`; no module instance is created there.
