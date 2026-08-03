# Internal Press feature-bench TcUnit evidence — 2026-08-02

Gate: `FraktalCore/PLC/TwinCAT/Examples/PressDemo/PressTests.plcproj`

Scope: framework integration testing only. Press Demo is an internal simulated
test bench, not a real machine project or production acceptance target.

Runtime: isolated Windows 10 x64 VM identified by the operator as
`192.168.1.11`, PLC ADS port 851. The event stream identifies the initiating
engineering AMS Net ID as `192.168.1.6.1.1`; it does not independently encode
the target IP.

| Field | Result |
|---|---:|
| Runner | `PRG_PressTestRunner` |
| Successful tests | 8 |
| Failed tests | 0 |
| Total tests | 8 |
| Test suites | 2 |
| Duration | 0.0103145 s |

Both intended suites ran: `PressDemoTests` and `FaultRecoveryTests`, four tests
each. `tools/tcunit_to_junit.py` accepted the archived raw output with expected
runner `PRG_PressTestRunner`, 8 tests, and 2 suites and emitted a passing JUnit
gate.

Immediately after capture, only the runner's XML declaration comment was
reworded to state that this is an internal integration bench rather than a
conformance or production project; its IEC declaration/body did not change. The
table therefore binds the current comment-corrected source and the independently
generated runtime TMC separately.

The warning that ten `PRG_TcUnitRunner.*` persistent symbols were not restored
is expected after replacing the preceding Core/Modules test application on ADS
port 851. Those old symbols do not exist in PressTests, restoration was skipped,
and the correct Press runner subsequently completed cleanly. The VM's USB-support
message is also non-blocking: the log explicitly says system start continued,
and the Press simulation gate does not require USB hardware.

## SHA-256 snapshot

| Artifact | SHA-256 |
|---|---|
| Archived raw XAE/TcUnit output | `235b3324f6d79f37aa694974d827170ea0ee4f575649d50a09f4dca1109f524a` |
| `PressTests.plcproj` | `928a521b011831fa735a0e04d444f48f4f45e42ffd377f91e37165019426ed95` |
| `PressTests/PRG_PressTestRunner.TcPOU` | `24468d01887538547794dc71eaad00b223282fe1887dafe03900af21d977d3fd` |
| `PressTests/PlcTask.TcTTO` | `e64078b3f0f7c36c1ae765ebbf2754068ae1edb0c0899c940124007753a1236d` |
| Generated `PressTests.tmc` | `8a8cdd7549ae583297e8d2813295821d4cb727f65f40fe352284f96fe80cae56` |

Together with the separately archived Core/Modules 84-test/26-suite result,
this closes the complete split runtime program: **92 successful tests across 28
suites, 0 failures**.
