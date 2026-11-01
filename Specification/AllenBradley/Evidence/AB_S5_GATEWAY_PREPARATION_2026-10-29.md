# S5 preparation seal attempt — stopped before authorization

The first archive attempt refused the legitimate Dart source path
`HMI/gateway/bin/fraktal_gateway.dart`: its directory deny-list treated every
`bin` folder as compiled output. The existing extension deny-list already
excludes EXE/DLL/PDB/ACD/BAK/L5X/PYC. The correction permits source `bin`
directories while retaining those exclusions and cache/build exclusions.

The partial source overlay in the matching payload folder is retained as
created. No payload manifest, source binding or preparation seal was produced;
authorization remained false. No controller operation occurred. Raw failure:
`C:/work/fraktal-ab-s5-20261029/preparation_seal_01.log` and its exit record.
The completed seal will use a new retry record. No S5 native claim or commit.
