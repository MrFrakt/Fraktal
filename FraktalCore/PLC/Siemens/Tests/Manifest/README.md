# Static manifest and native HMI bench

`make_fixture.py <new-package> <new-frames>` extends the nested Unit fixture with
one test-only data-read gate. Production generation contains neither stimulus DB
nor test observations. The generator derives typed child walks from the forest;
shared services count all entries and store only the requested Core page window.

QUERY_CONFIG takes IntValue=page index, DurationMs=0 (active context). ConfigRev
seeds from the CPU clock on activation/Initial_Call. Pages carry the same revision.
Every reused slot is cleared before the walk. Out-of-range nonnegative pages are
empty; negative/oversized indices and unavailable models are refused. Static
command catalogs are private and manifest items reproduce the existing HMI paths.
Mode policies and empty model counts are also served. There are no editable
capabilities in this slice; Writable, WriteKey and WriteRevision remain closed.

Run probe_web.py through S12_TypeMap/with_secret.ps1 -Action script. It uses the
original pin and process-data-only user, guards each mutation against the exact
isolated1516 target and produces JSON-lines, captured entries and JUnit. It checks
16-entry page bounds, root isolation, stable order, stale-slot clearing, metadata
without values below DATA_READ, query purity and restart revision changes.

run_gateway.dart uses the production gateway and Web API client. Its test-only
transport checks FrkS12/CPU1516/TCPIP169.254.212.49 and zero physical mappings
before every native write. Run with the gateway package configuration and the
existing DPAPI wrapper; credentials never enter arguments. Arguments are the
captured certificate DER, simulator.ps1 path and a stop-file path. It listens on
loopback8107 and exits when the stop file appears.

The opt-in HMI test is test/live_tia_manifest_test.dart. Set
FRAKTAL_TIA_MANIFEST_LIVE=1 and FRAKTAL_TIA_HMI_OUTPUT to a fresh evidence work
directory, then run Flutter with --run-skipped -t live and --concurrency=1. It uses
the production repository, snapshot mapper and widgets, saves a PNG/forest record,
clicks the rendered Instant command and independently checks the native counter.
The prototype has no login provider: the test sets only its in-memory operations
display preference to NONE to match the current PLC MANUAL gate. PLC authorization
still applies. This is not an authenticated production commissioning gate.

The generic repository excludes acknowledged ConfigPage/Report payloads from
cyclic reads. Queries read their exact discovered subtree after acknowledgement;
release consumers retain that reply instead of reading a later shared snapshot.
Complete authentication, data-write capabilities, alarms, retention and sequences
remain subsequent Core work.
