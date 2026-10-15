# Shared command lifecycle tests

`make_fixture.py <new-package-directory> <new-frame-directory>` extends the shared
two-root declaration with test command catalogs, a timeout and test device logic.
Frames and the actual shared Framework/Core kernel come from the generator's
`--shared-runtime` path. The package adds PLC assertions and a test OB1; it does
not contain a replacement lifecycle implementation.

The test OB1 resets only fixture data on Initial_Call, then runs55 deterministic
scan cases with238 assertions. Test clock injection proves exact timeout and
rollover boundaries. After the cases it calls the normal generated composition,
including the production RUNTIME clock. STOP/RUN reruns the cases from fixture
defaults. This reset is test harness behavior, not production retention policy.

Fixture counters live in declared private Device storage and publish OutImm;
they never read the FB output parameters.

Cases cover parameter/command latching, initialization and management order,
terminal reset/pulses, early Execute release, abort level and error-abort edges,
HELD resume beyond timeout, first-out timeout and verbatim adoption, invalid
commands/timeouts, non-command faults and retry, command timing and rollover.

Use the existing Generator/build.plan and download.plan against a copied FrkS12
station, with explicit project/generated/export substitutions and --require-clean-compile
for build plans. It checks every compile event, not the driver exit alone. run_plan.py guards
the1516 TCPIP virtual target and all-zero physical mappings before download.
Read GDB_Lifecycle with the S12 simulator helper. probe_web.py reads native public
values and private refusals with the original pin; pass the generated
test_manifest.json path through FRAKTAL_LIFECYCLE_MANIFEST and use with_secret.ps1
to scope the DPAPI password environment. No API writes are needed.

Scope remains the shared command kernel, not complete Unit mode/mailbox, alarm,
recipe, retention, full sequence or press conformance.
