# S5 idle-connection correction: sealed preparation

Prepared 2026-10-31T03:02:25.923657+00:00 under standing
O3 (AGENTS §3a, plan §6.3). Echo 601FC87B, L81E v38.011, 127.0.0.1 slot 0.
Authorization remains unarmed until this seal. All guards and rollback apply.

The [owner attempt](AB_S5_GATEWAY_OWNER_CONNECTION_ATTEMPT_2026-10-30.md)
reported movement disconnects and an initial connect error. A read-only probe
reproduced an unused CIP connection closed by Echo during a 100-second idle
interval; a periodic-read connection stayed usable. The updated native pool
probe observed all four idle connections closed, then successfully renewed and
read all four against serial 601FC87B. Neither probe wrote a controller tag.

The writer validates all arguments before connection setup, opens a fresh
serial-pinned dedicated socket for each payload/commit pair, sends each at
most once, wipes the plan and closes the socket. Ambiguity still poisons the
writer and discards queued pairs. The read pool renews only a peer close
observed outside an exchange, before starting a whole guarded-row lease.
Timeouts, malformed replies, aborts and in-row failures are terminal; no row
or command is replayed. The original terminal error is retained for diagnostics.
Proof, freshness, retry, access and write-vector contracts are unchanged.

The exact PLC image/source remain 95E1C514A31B06AEF528BDDC07F7D64C2336DDA6910B43663F1C01EBBA586012 /
979DD73CDFC0C0CBCD3348915CB6D804FCF2736DC780AEA196963E2F2105A162.
The 385 PLC inputs, 2,357 AB tests, both v38 build/read-back proofs and exact-image
Capacity 66% (2,077,924 used / 1,067,804 available / 3,145,728 Blocks) transfer by
hash from the prior sealed preparation. No PLC generation or download has run
for this correction yet.

Fresh gates pass: 781 HMI tests / 12 existing skips, analyzer, locked dependencies,
74 root tests, AB spec/contracts, strict consistency, gateway/installer tests,
Web/Windows/gateway/installer package, fresh native profile and SDK builds,
read-back equivalence, workflow/authorization, launcher, readiness/window,
browser-witness, read-gate, simulation-restoration and artifact checks.
SDK 2.1.974; Flutter 3.47.5 / Dart 3.13.4 at C:/work/fraktal-toolchains/flutter-3.47.5.
This host lacks the TwinCAT ADS SDK; the package explicitly reports ADS unavailable.

The new session performs fresh guards/preflight/backup, MANUAL normalization
if required, Program/download/Run, five-document restore, the inherited 12
automatic C1–C11/C13 cases and independent read/equivalence/configuration/scan
gates. C1 first waits 100 seconds with no browser client, then connects without
retrying its first repository startup. C5 waits another 100 seconds without a
command, checks LIVE throughout, then extends/retracts the same PartSlide and
proves native completion counts. No extra command vector is introduced.

The owner then checks the packaged Chrome HMI at http://127.0.0.1:8080/:
LIVE, login, acknowledged AUTO→MANUAL, logout, and reports whether the two
connection symptoms recur. The existing two-hour availability window changes
no freshness/proof/acceptance limit. A fresh token, exact owner reply and native
MANUAL/idle/logged-out boundary are required. The finally path restores the
pinned genealogy copy, all five original documents, 31 baseline cases and final
checks/preflight/timing. No fault/TASK clears, clock changes, controller power/
vendor-state edits or Echo hard kills. Only owned gateway/test processes stop.

Failed development/early-input checks are retained. Current exact source,
private harness, package and SDK hashes are frozen in source_bindings.json.
No credentials, ACD/L5X, binaries or caches are archived. Payload manifest
SHA-256: CBA14106C3CD13D09327C553C47DBA5365649D645FC72CAAD87CB2BFB101F684. Native acceptance remains unproven.
