# Core/Modules TcUnit evidence — 2026-08-01

Gate: `FraktalCore/PLC/TwinCAT/Tests/Fraktal_Tests.plcproj`

Observed XAE/TcUnit summary supplied from the isolated local test runtime:

| Field | Result |
|---|---:|
| Successful tests | 84 |
| Failed tests | 0 |
| Total tests | 84 |
| Test suites | 26 |
| Duration | 0.2722424 s |

`tools/tcunit_to_junit.py` accepted the raw log with expected counts 84/26 and
emitted a passing JUnit gate. The raw log is retained by the commissioning
session; its SHA-256 binds this record without copying noisy, time-sorted XAE
event output into the specification tree.

## Independent Windows 10 x64 VM repeat — 2026-08-02

The user downloaded a test application to the isolated Windows 10 x64 VM
runtime identified by the user as `192.168.1.11`. The captured output again
reports **84 successful, 0 failed, 84 total tests across 26 suites** in
0.2500116 s. Its suite paths are rooted at `PRG_TcUnitRunner`, so this is an
independent repeat of the Core/Modules gate, not the separate Press integration
gate. The fail-closed parser accepted the log with expected runner
`PRG_TcUnitRunner` and the expected 84/26 counts.

The event stream records that the restart was initiated from engineering
AMS Net ID `192.168.1.6.1.1`; the target IP comes from the operator's deployment
record and is not independently encoded in the TcUnit summary.

## SHA-256 snapshot

| Artifact | SHA-256 |
|---|---|
| Raw XAE/TcUnit text | `c338b5694c9c8b276d73dfc427f543cdb7e0d1b2003463d752647285250c51f4` |
| Windows 10 x64 VM repeat raw text | `02b1820ce402f0684825b2c7754231d38ca05ec620eb242bab0f009b17e653db` |
| `Tests/Fraktal_Tests.plcproj` | `447c4d79a665ea07bd0550065dd6362de523386e253a22b2b8003e6e7b65ff12` |
| `Tests/Fraktal_Tests/PRG_TcUnitRunner.TcPOU` | `1cff103f5703136bf3987b852515b5a088a51f49595015c9f87fd83da1e30d7f` |
| Generated `Tests/Fraktal_Tests.tmc` | `3d81f9df2c7f0044f29b42975a17227cdd4c4494df521c50f707327a6a0fb5b9` |
| Core `Fraktal_Core.plcproj` | `674bbfc0043d7114cd5b8eb9f9d32930808570e52baaa920d0a3750d8b953697` |
| Modules `Fraktal_Modules.plcproj` | `c0169b041d2b3a8bdf1a1a069599cf6a570ce82225e60aef613f79bc7298c015` |

This closes the Core/Modules runtime half of the split 92-test program. The
internal Press bench's separate 8-test/2-suite integration result is recorded in
`2026-08-02_Press_TcUnit.md`.
