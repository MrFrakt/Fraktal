# Phase 6 — configuration dialog and model selector regressions

Date: 2026-10-04 (America/Bogota).
Result: **software regression checks passed; corrected Web client deployed;
AB gateway activation and owner browser acceptance pending.**

The owner reports that Parameter sets opens for about one second, then the HMI
returns to its root, and that the model selector has disappeared. Offline
fixtures reproduce two faults against source baseline `8a879a4`:

- A held native set command blocks subsequent snapshot RPCs on the same socket.
  Its previous complete sample can expire while queued reads wait. The generic
  connection gate then removes the operator shell and its dialog; recovery
  mounts a fresh shell. The fixture also catches a queued command executing after
  disconnect. Original failing log: `C:/work/press68_config_gateway_repro_01.log`.
- Static tiering excludes AvailableModels paths by container name, although the
  binding publishes them outside its configuration pages. Subsequent snapshots
  lose both model names. Original failing log:
  `C:/work/press68_config_model_repro_01.log`. The companion manifest-provided
  model case passed on that baseline.

The AB gateway now dispatches a bounded number of requests concurrently on each
viewer connection. Reply IDs match requests; the existing Station lock still
serializes its native reader and the shared mailbox lock still serializes whole
command transactions. At most 16 pending requests are admitted per viewer;
overflow closes the connection with code 1013. Disconnect and overload cancel
queued work exactly once, and active native work drains before releasing its
lock. No command is automatically replayed. This does not shorten native set
delivery, change serial/authentication/scope checks or weaken freshness limits.

The generic repository excludes published static paths only once their exact
replacement keys exist in its hydrated manifest. Its tier cache also watches
that key set. A binding that does not re-serve model names therefore retains
their published values. Implementation-only SequenceStepDef storage remains
excluded because its consumed definitions live under SequenceSteps instead.
No station-specific selector or parallel configuration contract was added.

Validation:

- Final focused concurrency suite: 4 tests pass. It proves same-socket reads
  while a set write is held, ordered serialized commands, disconnect cancellation
  and bounded overflow with active native draining.
- Full AB discovery: 1,541 tests pass in 229.727 seconds.
- Full HMI: 478 tests pass, with 7 expected live/fixture skips. Both manifest
  model cases retain the model selector, query model 2 and preserve the running
  model. Existing editor controls cover dropdown selection and model writes.
- Shared TC3/AB repository, freshness, reconnect and gateway contract: 79 tests
  pass with the production AB projected snapshot.
- Four in-memory AB mutants killed by assertions: serial receive loop, retaining
  queued disconnect commands, canceling a native drain twice, and interleaving
  mailbox transactions. No repository source was mutated by that run.
- Flutter analyzer has no issues; release Web compile and Wasm dry run pass.
- Root consistency has zero errors/warnings; root suite passes 33 tests.

The corrected client is served at `https://press.localhost/`. Trusted HTTPS
requests return 200 and exact release bytes for main script, bootstrap and index.
Served main script SHA-256:
`A566AE9D54B271C48351751B357C7865C1DC86A27C39A6C25196AB1971B1BF4C`.
The previous Web release is retained at `C:/work/press68_config_fix_web_backup_01`.
The [JSON record](AB_PHASE6_CONFIGURATION_REGRESSIONS_2026-10-04.json) binds the
sources, original failing logs, final gates, mutation report and deployment by
SHA-256. Browser interaction itself was not exercised by this agent run.

The handover assigns write-enabled gateway restart to the owner. Restart the
existing approved AB gateway once, hard-refresh Chrome, then open Parameter
sets and check the model-data dropdown. The same restart activates the earlier
D6 health-policy implementation; read all three health endpoints afterward.
Live acceptance remains pending until those observations succeed.

All current tests use fake native data, except the read-only HTTPS asset checks.
No controller tag write, fault clear, mode change, power cycle, download or
gateway restart occurred. No PLC source/declaration was changed or generated.
PLC memory growth is zero, the four-user ceiling is retained, and
`C:/work/press68.L5X` remains SHA-256
`E2C20374F8FC7364672E425EBC3E55CC5F6D9F81ED4894BB32366E737BA586F7`.
Configuration power-cycle retention, the historical S1 clock probe, TC3 native
segmented transport and owner-deferred mode-latency work remain separate.
