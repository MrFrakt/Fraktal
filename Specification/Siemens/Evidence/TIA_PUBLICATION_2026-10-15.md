# TIA publication scope, 2026-10-15

The owner requested commit and push to main after validation. The publication
includes the Siemens port, shared HMI support, specification/reference updates,
workspace selection and dated engineering evidence through generator0.20.
The unrelated deletion of LICENSES/MIT-legacy.txt is left outside this commit.

The October14 cycle-profile archive contains a local SiemensAgent knowledge
database before-image with unrelated engineering-project tables. That one file
stays local and is explicitly ignored for publication:
`FraktalCore/PLC/Siemens/Evidence/Archives/TIA_CYCLE_PROFILE_2026-10-14/Runs/knowledge_before.sqlite3`.
Its bytes and original checksum record remain unchanged. A public checkout
therefore omits that local-only payload; the authored knowledge notes and
index/integrity/table-count reports remain available. Native PLC source,
readbacks and test evidence are unaffected. The new recovery archive likewise
keeps its private knowledge before-image outside the archive.

Saved engineering-project storage under archive `projects/` directories also
stays local, matching Part IV's build-output boundary for `.ap20` projects.
GitHub rejected the first unpublished commit because the October13 project
copies contained PEData.plf databases of394754733 and132972233 bytes, above its
100 MB per-file limit. The unpublished commit was amended to omit those local
build-output directories. Their original files and checksum records remain
unchanged; public checkouts use the recorded sources, native exports and logs.

Immutable native exports retain Siemens' formatting, including trailing spaces.
Byte-bound generator output/templates retain their existing formatting as well;
normalizing frozen exports would invalidate their hashes. The repository's
`* -text` attribute preserves byte fidelity through Git checkout.

The new recovery archive binds21389 payload files /336656588 bytes. Its
SHA256SUMS digest is
`5498a2dec0e9f8ac98a627c8e226a4ffc92040cafd3e34be95971031201fee82`.
All payload bindings were verified before staging. The selected gate is
[415 native checks plus final normalization and tooling/HMI checks](TIA_SEQUENCE_RECOVERY_2026-10-15.md).
