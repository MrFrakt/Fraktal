# Config sets, JSON lines and HMI mailbox transfers - measured 2026-10-12

Fraktal generator 0.10: optional root-owned LOCAL_RETAIN named station/model
config sets. Typed handlers share write definitions/scalar parsing; all owners
stage before commit. Per-root catalogs/work, no per-child set buffers. Current
bench: two roots/24 modules, four slots each, 24 records per set, nine station and
24 model records. ENGINEER gates CONFIG_SET; model loads also take CHANGEOVER.

Siemens gotchas measured with TIA V20/CPU1516 V3.0:
- FC IN_OUT WSTRING parameters are unsized; the actual DB declares WSTRING[480].
- WCHAR is not a valid CASE selector: use comparisons or a supported ordinal.
- Explicit narrow conversions avoid sign/accuracy warnings in parsed headers.
- Integer-to-string emits a leading '+': remove it for JSON numeric members.
- A station-only deployment must omit a literal FOR 1..0 model loop.
- Early shape refusals must copy the precise Scope/WriteKey into ConfigPersist.
- Core's 480-character line bound is derived from FB_ConfigSetJson. Real 382-char
  export lines read and import intact through 255-char mailbox pieces.
- Reject malformed/duplicate/unknown/missing/stale/foreign records before applying.
- Retained live config and named snapshots both survive guarded simulator power
  off/on; do not unregister the owner or stop its keeper.

Generic HMI: queue the entire import/export (all lines and pieces), not each
request separately. A background QUERY_CONFIG between export lines invalidated
Siemens' cursor; the repository fix applies to every binding. Dispose/link changes
invalidate continuation. Freshness reads continue; config queries wait. Tests
cover competing queries, piece ordering and interrupted exports. The live UI test
needs a rendered frame after editing and must select one of two set tooltips.

Evidence: Specification/Siemens/Evidence/TIA_CONFIG_SETS_2026-10-12.md and its separate
SHA-bound implementation archive. 198 set + 15 power + 120 config + 122 access +
96 state/alarm + 36 decision checks = 587 native checks. Press102 sources compile
0/0 at both checkpoints; AUTO19/HOME4 and LAD161 networks/155 calls match native.
HMI574 pass/8 opt-in skips plus passing production gateway/repository/widget live
gate. Siemens148 tools, consistency35, lint/consistency clean.

Current downloaded project: TiaStations/Config_Sets_Runtime_20261012/FrkS12/FrkS12.ap20.
Offline press: Config_Sets_Press_Offline_20261012/FrkS12/FrkS12.ap20, not downloaded.
Owner Fraktal RUN/TCPIP169.254.212.49+192.168.1.1, ie1/2/3=0, keeper1748 preserved.
Use the unchanged whitelisted candidate_structure_examples driver explicitly.
Its SHA256 ba24e6aaa0338b286accaf3d19c0d9dfaf2b394268b57a1a43ff1d330652fc74 is unchanged.

Next: user/policy and alarm retention; project-selected file/database medium;
line config replication; current-value export/runtime model creation; remaining
config forms. Physical press commissioning and full frontier/alias exclusion are
still separate gates. No conforming runtime release or full-download retention
claim follows from these simulator checks.
