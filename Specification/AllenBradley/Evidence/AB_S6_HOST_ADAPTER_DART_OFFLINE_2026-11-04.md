# S6 WP6.5 — The host adapter ported to Dart, offline

2026-11-04, America/Mexico_City. Entry commit `00e44264e` (branch
`s6/host-services`), with the uncommitted working tree. This follows the
[Python adapter record](AB_S6_HOST_ADAPTER_OFFLINE_2026-11-04.md), which stays
unchanged. The owner chose to port the adapter to Dart, so it ships and is
supervised like the gateway. That record's open distribution question is
therefore answered. No native claim is made: no controller or Echo session was
used, and no image was written to a file or downloaded. Nothing was committed
when the gates ran.

## What was built

| Source | Role |
|---|---|
| `packages/fraktal_opcua_client/lib/src/cip_host_service.dart` (exported by `lib/cip_host_service.dart`) | The protocol and the controller port. `CipHostLayout.negotiate` validates the request, chunk, commit and reply Templates of one binding row. `encode` returns the request payload and commit, and `decodeReply` reads the reply. `CipHostIngress` writes through an opened command connection, awaits the acknowledgement for a bounded time and never resends. `cipHostDiscover` discovers through the manifest, and `cipHostIngresses` builds one ingress per root from a discovered namespace and manifest. `CipHostFacts` holds what the port reads from the published capability, key and model tables. The library also exports the transport and manifest types the ingress takes |
| `gateway/lib/src/host_adapter/set_documents.dart` | The set-document format, `FileStore`, `Session` and the store folder. Its strict JSON reader refuses duplicate keys, NaN, non-integer numbers and control characters, as the Python reader does |
| `gateway/lib/src/host_adapter/live_medium.dart` | `FileMedium` and its failure kinds |
| `gateway/lib/src/host_adapter/root_service.dart` | `RootService`: every ConfigSets and ConfigProvider job, live-document keep and restore, and the rendering of documents from published facts |
| `gateway/lib/host_adapter.dart` | The library's exports |
| `gateway/bin/fraktal_host_adapter.dart` | The executable: discovery, one `RootService` per root, a health line on stdout whenever a root's health changes |
| `gateway/windows_tray/fraktal_gateway_tray.cpp` | Supervises the adapter from an instance's optional `host_adapter.args`, on its own restart backoff, logging to `logs\<name>\host_adapter.log` |
| `gateway/tool/build_gateway.dart`, `tool/build_windows_installer.dart`, `deploy/windows/install_gateway.ps1` | Package `fraktal_host_adapter.exe` and `host_adapter.args.example` beside the gateway |
| `gateway/DEPLOYMENT.md` | The host adapter section |
| `PLC/Allen-Bradley/tools/fraktal_ab_host_bench_server.py` | Serves the emitted controller code over stdio to the Dart tests, as plain values or as CIP tag bytes. It also renders the engineering documents and bytes the tests compare against |

The Python adapter and its port are retired:
- `fraktal_ab_host_adapter.py` and `fraktal_ab_host_cip.py`;
- their tests, `test_fraktal_ab_host_adapter.py` and `test_fraktal_ab_host_cip.py`.

`fraktal_ab_host_service_binding.complete` stays. The port's sparse-chunk test
(a chunk completed and never widened) moved into
`test_fraktal_ab_host_service_binding.py`. The modules that moved out of the
engineering code at the previous checkpoint stay too: the bench and
the engineering keeper still use them.

The tray never lets the adapter change the gateway's state. A failing adapter
only adds " - host adapter restarting" to the instance's status. Its backoff
doubles from 2 s to a 30 s cap. An operator Start, Restart or Start all clears
it, exactly as it clears the gateway's.

The executable does not resend any request. After an error it rediscovers
5 s later; a download in progress or a lost link both look like this. A
controller that serves no host services is looked at again only once a
minute, because each discovery walks the whole namespace. Between looks it
keeps no connection open.

`Gates/source_bindings_03.json` binds the 14 HMI sources, 2 tool sources and
the 3 documents. It checks each file keeps its HEAD line endings (LF for a
new file), and that the 4 retired files are absent, listed with their HEAD
hashes.

## Tests

`gateway/test/host_adapter_bench_test.dart` (20 tests) runs the Dart
`RootService` against the emitted controller routines on the Python bench.
Its store and medium are real temporary folders. It uses two ports:
- one that hands the bench plain values;
- the real `CipHostIngress`. Discovery builds it through
  `cipHostIngresses`, over a read and a command connection that the bench
  answers in CIP bytes. The bench serves each Read Tag from the emitted tags
  in a synthetic Template layout, which is not a measured Logix layout, with
  the type header. It decodes each Write Tag back into the emitted request
  tag, or stores the commit and scans. The manifest is the bench's own
  emitted header, normalized by the Python reader and accepted unchanged by
  the Dart `CipManifest`.

The tests are:
- **Configuration sets (5, run once through each port):**
  - save, list, load, export and delete through the adapter's store. The
    saved document equals the engineering rendering;
  - a current export rendered, then served line by line;
  - an import in 200-character pieces, stored on commit;
  - a stored value the controller cannot parse sent as invalid, never
    coerced, with the station unchanged and the key reported;
  - a missing set refused, and audited, by the transaction; a full store
    refused, while replacing an existing set is still accepted.
- **The CIP port (4):**
  - the reply and the facts it reads equal the controller's own values. The
    facts are the 30 capabilities with their keys, the model codes, the
    capacity and the revision. Nothing is written;
  - a request is written as its payload, then its commit, and the
    acknowledgement is returned. With no job open, the controller
    acknowledges the request and refuses it;
  - an unacknowledged request raises `CipHostUnanswered` after the bounded
    wait, with exactly one payload and one commit written and the reply
    unchanged;
  - a refused write is never resent. The connection is aborted, and the
    next request opens a new one.
- **Parity with the engineering code (3):**
  - one chunk encodes to the Python encoder's exact request and commit bytes.
    This holds for three sequences, including `0x7fffffff` and `0xfffffffe`;
  - the store and the medium write the Python code's exact files, both ways.
    The document carries every escape class the ASCII transport admits, and
    Python reads what Dart wrote and the reverse;
  - lines the format refuses are refused, and Python's `splitlines`
    behaviour is kept.
- **Live documents (3):**
  - a download restored from the medium, then every document kept, equal to
    the engineering keeper's rendering;
  - a lost document restored as a loss, with `RestoreLost` published;
  - an unreadable medium restoring nothing.

Each group skips only when Python or the AB tools are missing beside the HMI.
In this run none skipped.

## Mutations

`Investigation/mutate_dart_adapter_01.py` (`Gates/mutations_01.json`, run
before gate run 03 on the same sources). Dart cannot load a mutated library
in memory, so each mutant is written to its source file, its selected test
runs, and the original bytes are restored, with their SHA-256 asserted,
before the next mutant. A mutant counts as killed only when its test ran
and failed. A compile error or a run with no tests counts as invalid, never
as killed. The 10 selected tests pass unmutated, and each of the 12 mutants
is killed:
- **In `RootService`**, the eight the Python adapter's mutation run used:
  - a missing set answered as found;
  - a full store not refused;
  - an import commit not kept;
  - a restore that hides its losses;
  - a boolean rendered as a number;
  - invalid value text coerced;
  - the catalog never published;
  - a keep that never writes.
- **In `CipHostIngress`:**
  - the commit written before the payload;
  - any reply taken as the acknowledgement;
  - a refused write carried on;
  - a capability read with the wrong key column.

## Gate results

`Investigation/run_gates_03.py` (`Gates/gate_summary_03.json`): every gate
exits as expected. The usage request exits 64 by design; every other gate
exits 0.
- **Sources:** 19 files bound with their line endings, and the 4 retired
  files absent.
- **Dart:** `dart analyze` is clean for the client package and the gateway.
  The gateway's 24 tests pass (the 20 bench tests and its 4 others) in
  281 s, none skipped.
- **Builds:**
  - `fraktal_host_adapter.exe` compiles, and prints its usage;
  - the tray configures and builds. The build reports no compiler warning,
    only three MSBuild notices about building under the temporary folder
    (MSB8029 twice, MSB8012). That folder is the gate's own choice, so that
    no binary lands in the evidence.
- **Flutter:** `flutter analyze` is clean, and the full HMI suite passes 842
  tests with 12 skipped.
- **Python:**
  - the focused host-service suites pass 212 tests with ResourceWarnings
    raised as errors. That is 226 at the previous checkpoint, less the
    15 retired adapter and port tests, plus the sparse-chunk test that
    moved;
  - full AB discovery passes 2,499 tests in 1,225 s, which reconciles the
    same way from 2,513. All 399 Python module hashes are unchanged during
    the run: 402, less the 4 retired, plus the bench server.
- **Root and documents:** 85 root tests pass, and the AB specification,
  frozen-contract and strict consistency gates (0/0) are clean.

## Defects found during development

The parity test found one real divergence. The Dart JSON writer left DEL
(0x7f) unescaped, while Python's `ensure_ascii` writes it as `\u007f`. The
two adapters would then have written different bytes for the same set. Dart
now escapes every code unit below 0x20 or above 0x7e. The parity document
carries DEL.

Other development failures were caught before the gates:
- The analyzer caught two missing imports (`dart:convert`, `dart:io`). It
  also flagged `return` statements inside `try` blocks that did not await
  their future (`unawaited_return_in_try_block`): a refusal thrown
  asynchronously would have escaped its `catch`.
- The first version of the bench's wire decoded each Write Tag's data whole,
  including its type header, so every write through the real port failed
  with a length error. The bench now checks the header (`0x02A0`, the
  request's structure handle and one element; `0x00C4` and one element for
  the commit), refuses any other, and decodes what follows. On that same
  run the port's read test, unacknowledged test and refused-write test had
  already passed.
- `DEPLOYMENT.md` is mixed at HEAD (464 CRLF lines of 501). The Edit tool
  rewrote all of it as CRLF when the section was inserted, which would have
  committed 37 unrelated line changes. The source-binding dry run reported
  it, so the file was rebuilt from HEAD's bytes. The section was then
  inserted in the CRLF region it belongs to, as a 15-line insertion. The
  rebuild script's own line-count assertion was off by one after it had
  written the file. The diff (15 insertions, nothing else) and the binding
  check (zero defects) confirmed the file instead.
- Two other scratch scripts failed before writing anything: a heredoc
  mangled a backslash, and a label count stopped the first attempt to
  derive run 02's script from run 01's.

Two gate runs were stopped deliberately, because review found defects that
should be gated rather than argued. Their partial logs are kept unchanged and
have no summary.
- **Run 01** stopped during its Dart tests, with 9 passed and none failed.
  Two defects had been found:
  - the adapter's restart backoff was never cleared, not even by an operator
    Restart, so a few early crashes would have left every later restart
    waiting the full 30 s;
  - the executable did not range-check `--port`, and rediscovered a
    controller without host services every 5 s.
- **Run 02** stopped during its tray configure step. Its 15 gateway tests,
  the compile and the usage check had passed. Review then found:
  - no test reached the real port. The Dart tests used only the plain-value
    port, so retiring the Python port's tests had dropped coverage of reply
    decoding, the facts reader, the payload-then-commit order and the
    no-resend rule;
  - discovery left its read connection open when a controller served no
    host services, one leaked socket per minute.

  Discovery now delegates to `cipHostIngresses` and closes the connection
  when nothing is served. The port's tests and the second pass of the
  set scenarios were added.

Run 03 is the gated run.

## Boundary

The Dart adapter and its CIP port are proven against the emitted controller
code in the model, over synthetic Templates. The following are S6-Q gates:
- native Templates, the socket transport, timing and packet sizes;
- the live-document restore through the real port (its tests use the
  plain-value port, because a restore waits on controller scans);
- the closed connection of a discovery that finds nothing, which needs a
  socket;
- the tray's supervision at runtime.

Still open in WP6.5: HostEvents delivery over the canonical ring. Its batch
must be proven equal to the legacy one on a native capture.

Then:
- WP6.6 removes the legacy staged and provider endpoints, and the Python
  gateway path that still uses them;
- WP6.7 and WP6.8 follow;
- S6-Q is the native acceptance.
