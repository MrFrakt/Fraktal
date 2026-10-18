# Native Unit control bench

`make_fixture.py <new-test-package> --test-frames <new-frame-directory>` builds
the existing two-root/eight-instance forest with actual shared Unit services.
The generated source is independently reviewable. The test package replaces
OB1 and adds GDB_UnitTest for virtual permits, cycle boundaries, fault/carrier
conditions and observation. This stimulus surface is excluded from production
generation; only Unit HmiRequest is writable within module roots.

Use Generator/build.plan with explicit project/generated/export paths and
run_plan.py --require-clean-compile. Use download.plan with the isolated FrkS12
guard. probe_web.py runs through with_secret.ps1 -Action script; it keeps the
original pin and never logs the DPAPI web password. Every mutation and mode act
checks the1516 TCPIP target and zero physical mappings. Failed mutations are not
replayed. JSON-lines and JUnit preserve each check.

The native sequence exercises live access/permit checks, supported/unsupported
modes and requests, same/zero commits, secret clearing, continuous run, Stop at
a cycle boundary, graceful/immediate/deferred/bounded exits, one-reset child
release, live faults, carrier read/write/identity failures, invalid NOK results,
canonical part events/counters, STOP/RUN and post-restart operation. Root B is
the independent carrier-disabled peer. Private paths and non-mailbox writes
are checked through the native API.

The simulator reinitializes this fixture's non-retained data at STOP/RUN;
BootStamp proves a new Initial_Call. Tests compare acknowledgement to the current
post-restart request sequence rather than assuming the old sequence survived.
Production retention classes and HMI rendering are separate gates.
