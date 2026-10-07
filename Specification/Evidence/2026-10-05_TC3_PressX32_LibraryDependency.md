# Press Demo x32 library dependency repair — 2026-10-05

The owner's 501 diagnostic rows report missing Core types/base classes inside
`Fraktal_Modules 0.11.0.0`, followed by missing inherited methods/properties and
interface-conversion failures in Press. The source Modules project had lost its
`Fraktal_Core` placeholder. Its installed `dependencies` file also omitted Core;
only the five Beckhoff dependencies remained. No license rejection occurs in
the supplied error list.

Restored Modules → Core 0.23.0.0, retained the owner's Press reference ordering
and namespace, and pinned the Press consumer to Core 0.23.0.0 / Modules 0.11.0.0.
Saved/reinstalled Core first, then Modules, after their native object checks.
The new installed dependency list contains `#Fraktal_Core`.

A fresh isolated XAE instance opened the owner's current `PressDemoX32.sln` and
system wrapper against the repaired installed libraries. **CheckAllObjects=True,
DteErrorListCount=0** for **Debug / TwinCAT RT (x86)** on XAE **3.1.4026.24**, DTE18.
The install and consumer compiler transcripts accompany this record. Modern
PLC lint and strict consistency also pass. This proves the 32-bit consumer
compile with the named compiler; it is not runtime or older-compiler acceptance.

No runtime configuration was activated or downloaded and no license was edited.
The owner's original source files and both overwritten installed library versions
were backed up under `artifacts/press-x32-repair` before repair. Other PLC/HMI
changes remain in the working tree. Reopen an already-loaded Press solution
before checking it again so its cached library graph reloads from the repository.
