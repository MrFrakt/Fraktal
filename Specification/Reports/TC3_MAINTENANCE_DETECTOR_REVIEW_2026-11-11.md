# TC3 native maintenance detector — 2026-11-11

The owner approved the detector proposed in the preceding handover review.
Core **0.26.9.0** and the neutral Modules **0.18.0.1** rebuild implement it.
The existing platform probe samples both native PLC/System Manager force flags;
the existing health publisher owns one LOW/SYSTEM/AUTO_RESET, non-shelvable
reason-22 notice. Demand, availability or configuration clearing closes it.
Projects keep their existing probe/SetSystemHealth call path. Healthy and the
Start policy are unchanged. IMPLEMENTATION_NOTES §177 records the decision;
Part II §8.12 specifies the binding.

Beckhoff documents both flags from 3.1.4026.21 in
[PlcAppSystemInfo](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/714818699.html).
The implementation uses the documented
[conditional variable-declaration query](https://infosys.beckhoff.com/content/1033/tc3_plc_intro/2529795979.html)
for both members. Missing declarations produce explicit unavailability. An
isolated compile replaced both identifiers with nonexistent members and passed
CheckAllObjects with zero errors/warnings, then restored the original bytes.
This exercises the absent-member branch on 4026.24; it is not an installed
4024 compiler/runtime test. Both lint profiles pass.

The two new TcUnit rows cover unavailability, deduplication, registered metadata,
refused shelving, nonblocking health, come/gone history, re-raise and the native
probe mapping. Aggregate: **355/355 in 54 suites**; Press: **9/9 in 2 suites**.
All six solutions compile with zero errors/warnings, using installed libraries.
Both raw runtime logs have independent exact-inventory JUnit validation.
On the isolated 4026.24 runtime the installed probe read MaintenanceAvailable
TRUE and MaintenanceDemanded FALSE, matching both native force flags FALSE.
No live force job was created; active-force TRUE edges were not provoked in XAE.
The publisher's demand edges were exercised through its normal sample interface.

Shared-input/source hash changes regenerated seven Siemens package/test files;
the existing S7 maintenance source remains in place. Frozen V3 and AB code are
unchanged. The 304 Siemens tool tests, 49 cross-contract tests, AB/TIA contract
checks, generated replays and TIA lint pass. TC3 tools: 79 tests OK (one skip);
strict consistency: zero errors/warnings, 36 tests OK; reason catalog check clean.
The generated field census is 617. No HMI source or lockfile change.

The first aggregate object check caught Blocking called as a method in the new
test; it is a property. The assertion was corrected and the affected solution
recompiled cleanly. An initial generator/suite attempt used an inline alarm
expression outside the existing translator's accepted shape; the final publisher
uses its established named Boolean condition, with no generator code change.
Those initial failures remain in the raw evidence. A read-only ADS probe first
rejected the solution label FraktalTests; it was corrected to the verified PLC
ProjectName Fraktal_Tests before reading the sample. No target write resulted.

Only UmRT_Default **192.168.1.6.1.1:851** was activated, with boot autostart off.
The final gate leaves PressTests stopped in Run mode. No physical controller,
NC or robot acceptance was performed. Changes remain uncommitted and unpushed.
The prior accepted 513-source baseline is preserved in a ZIP, and every artifact
in its dated receipt was checked unchanged. The follow-up evidence and SHA-256
receipt bind the final source and retained logs.
