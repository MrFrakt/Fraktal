# Native access/session bench

`make_fixture.py` extends the measured nested forest with private salted hashes
and two test principals. `with_credentials.ps1 -Action prepare -Output <new-package>
-Frames <new-frames>` creates separate random operator/admin PINs in DPAPI files
and provides them only through process environment variables. Generated sources
contain salt and hash bytes. The process-data Web API account remains separate.

The generated shared services perform the Core local-provider hash: SHA-256 of
16 salt bytes followed by the PIN, then the Core work factor of SHA-256 of the
previous digest followed by the salt. SHA constants, work factor, capacities and
user-record fields derive from the TwinCAT Core authorities. Four native hash
witnesses compare with Python hashlib. One compression runs per active PLC scan.
Private candidate storage contains no PIN and clears on completion/cancellation.

LOGIN acknowledges consumption before completion. Clients wait for LoginBusy to
clear and LoginResultSequence to match the committed sequence, then use
CurrentUser/CurrentLevel/LoginFailed. Failed credentials preserve an existing
valid session. Each Unit has independent session state; only the test roots have
the local provider enabled. Explicit logout and startup cancel pending work.
Expiry drops the old session without discarding a new credential attempt.

Run `with_credentials.ps1 -Action probe -Output <fresh-log>` after the guarded
download. The probe requires owner instance Fraktal, CPU1516, TCP/IP on
169.254.212.49 and zero physical mappings before every write/mode change. It
tests denial/acceptance, root isolation, policy bounds/self-lockout, query-neutral
idle expiry, accepted-mutation activity, cancellation/supersession, secret
clearing, native privacy and STOP/RUN. Extra stimulus DBs and deterministic
interrupts are test-only; production generation contains neither.

The opt-in HMI gate reuses Tests/Manifest/run_gateway.dart and
test/live_tia_manifest_test.dart. Run the gateway with the existing DPAPI web
wrapper, then `with_credentials.ps1 -Action hmi -Output <new-artifact-directory>`
from FraktalCore/HMI. It uses a real application login, the normal OPERATOR
operations display policy, the rendered Instant button and an independent
native counter. The wrapper supplies PINs without arguments or logs.

This is an unreleased reference1500 prototype. Production defaults remain fully
open with the provider disabled until composition provisioning. User-table and
policy persistence, CRUD/provider substitution, data classes, concurrent mailbox
writers and the complete alarm/audit contract remain open. Generator0.7 now emits
access records as AlarmLog AUTO_RESET occurrences with action/user/path and no
secret; the [state/alarm bench](../StateAlarm/README.md) proves their lifecycle and
optional callback seam. Shelving, retention and durable sink adapters remain open. No1200
deployment or physical-controller authentication is claimed.

Generator 0.11 adds a separate [retention qualification](../AccessPersistence/README.md).
It provisions the same private salted records only for a virgin image and proves
that an edited role and root policies survive restart without startup reseeding.
The older fixture's deliberate startup assignments remain regression stimuli.
