# Fraktal/TIA — first bench run: S15 automated gate, S2 module form, S5 harvest (2026-10-08)

**Scope:** the Phase 0 fixture `FraktalCore/PLC/Siemens/Spikes/S2_Shape` built,
compiled, downloaded and self-tested on the physical bench CPU through TIA Portal
Openness, headless, from this repository. Append-only: later results go in a new
record. Raw artifacts: [`TIA_S2_BENCH_2026-10-08/`](TIA_S2_BENCH_2026-10-08/).

**Verdicts (at this record's scope — S7-1200 bench only):**

| Spike | Verdict | Basis |
|---|---|---|
| S15 automated executable gate | **PASS (bench)** | headless create → import → compile (0/0 SW, 0/0 HW) → download → TLS online, all from plan files, every step logged |
| S2 module form | **PASS for the fixture's scope** | frame form, `FRK_Begin`/`FRK_End`, parameter instances, identity from `GetInstancePath`, registry, HELD; 17/17 assertions on hardware ×3 |
| S5 harvest | **PASS (bench, TCP path)** | test image serves its own result table over OUC TCP; host converts to JUnit; three consecutive green runs |
| S11 (SCL leg only) | **partial** | one SCL chain's step trace `0,100,110,120,100,110` and the 2-scan command/result loop exercised; GRAPH leg not started |
| S1/S7/S8/S9 (OPC UA, HMI) | **not started** | OPC UA server not enabled in this image |
| S3 memory | **not measured** | the image fits; no memory figures read yet |

## 1. Identity

| Item | Value |
|---|---|
| Controller | CPU 1214C DC/DC/DC `6ES7 214-1AG40-0XB0`, FW V4.7.3, 192.168.0.10, PROFINET name `s7-1200-plc`, MAC 8C-F3-19-B8-3F-4D |
| Engineering | TIA Portal V20 (STEP 7 setup package `20.00.0000`), Openness API 20.0.0.0, headless (`WithoutUserInterface`) |
| PG/PC interface | `Intel(R) 82574L Gigabit Network Connection` #2 (Windows adapter `Ethernet1`, 192.168.0.123/24) |
| Driver | `Fraktal.Tia.Cli` (net48 x64) — deployed runs used builds whitelisted as `APC3…`, `33NC…`, `w4PV…`, `gDmh…`, `QC8T…`; the current source builds `PdlSziKP…` (SHA-256 3dd952ce…5fe3) with the subscription fix of §3.9 and is not yet whitelisted |
| Station project | `%LOCALAPPDATA%\Fraktal\TiaStations\FrkSpikeS2\FrkSpikeS2.ap20` (engineering-workstation state, not committed — §3 item 8) |

Deployed sources: the 26 files imported by build run 7
(`07_build_deployed_sources.log`, `source-generated` events) are byte-identical to
the repository files at this record's commit (checked by SHA-256, 0 mismatches).

## 2. Results

Self-test rows (`FB_SpkHarness`, harvested by `s7_probe.py harvest --tcp 2000`):

| Run | When (UTC) | Image | Result |
|---|---|---|---|
| r1 | 06:19 | first image (interlock modelled as a fault) | 15/16 — case 8 failed (see §3.6) |
| r2 | 06:37 | HELD interlock | **17/17** |
| r3 | 06:39 | same image, CPU stopped and restarted by download | **17/17** |
| r4 | 06:41 | same | **17/17** |

The JUnit files of r2–r4 are byte-identical because the results are; the
download logs `12_…`/`13_…` show a separate `PLC_1 stopped`/`PLC_1 started` for
each run, and the result table is `NON_RETAIN`, so each table is a fresh run.

Cases (`CASES` in `tools/s7_probe.py`): T1 handshake (1, 2), T4 abort without
self-resume (3, 4), T2 first-out reason and `SourcePath` (5, 6), Execute-drop
reset (7), T3 HELD and self-resume (8, 17), identity from `GetInstancePath` (9),
registry rows and parentage (10), mailbox SET_MODE/START/STOP/OPERATOR_RESET
(11, 12, 14, 16), SCL chain trace (13), T6 verbatim roll-up (15).

## 3. Platform findings (each one changes Part IV or the tooling)

1. **Openness group and logon.** Without membership of `Siemens TIA Openness` every
   session fails (`00_openness_refused_no_group.log`); membership takes effect only in
   a new logon session.
2. **The Openness firewall covers new headless instances too, by exe hash.** A rebuilt
   driver fails with `EngineeringSecurityException: The operation has timed out`
   until the new hash is whitelisted (elevated). `Main` must not name a Siemens type,
   or the JIT loads the API before the resolver is registered.
3. **SCL external-source rules measured on V20:**
   - one `TYPE` per `.udt` file with no comment before `TYPE` generates; the original
     multi-type file with leading comments failed with no detail text
     (`DetailMessageData` was empty) — found by splitting files;
   - a member named `Name` is **silently dropped** from a source declaration
     (`NAME` is a block-header keyword): the type becomes "a structure without
     components". Declare it `"Name"`; code may still write `#Status.Name`;
   - FC `String` parameters take no length;
   - identifiers are case-insensitive: constants `BUSY`/`ERROR` collide with
     parameters `Busy`/`Error`; `dt` is reserved;
   - `GetInstancePath` is called as `#w := GetInstancePath(SIZE := 0);` and pulls
     the system blocks `GetSymbolPath` and `SymbolInformation*` into the image;
   - `TSEND_C.COM_RST` is `InOut` and needs a variable;
   - reading an FB's own output inside the FB, or writing its own input, draws
     warnings: `Status` and the mailbox request are therefore **statics**, published
     outputs are written only.
4. **Bench security posture applied** (station plan, bench only): confidential-data
   protection ("master secret") off — TIA refuses to compile V4.7 left in its default
   "enabled without password" state; access control `Disabled` (classic access
   levels) — UMAC otherwise requires a user with the Full-access runtime right.
   `ProtectionEnablePutGetCommunication` is **not** exposed for the S7-1200 through
   Openness (`EngineeringNotSupportedException`), hence the TCP result server.
5. **Secure PG/PC communication is the V4.7 default and is bound to the project's
   certificate.** The first download (legacy protocol, onto a CPU of unknown history)
   installed this project's certificate and secure-only mode. Recreating the project
   generated a new certificate and the next download could not connect by either
   protocol (`08_…`). Openness raises the trust question as
   `TlsVerificationConfiguration` on `ConnectionConfiguration.OnlineLegitimation`
   (`VerificationInfo` "certificate not matching"); answered `Trusted` once by
   `--trust-plc PLC_1` (`09_…`, `10_…`), after which TLS verifies with no override
   (`11_…`). Consequence: the TIA project is engineering state, kept per station
   (item 8 below and Part IV §2.5).
6. **Interlock semantics.** r1's case 8 exposed that the fixture faulted on an open
   interlock where the TC3 reference cylinder **holds** (Core §6.1: busy, outputs
   withdrawn by the same permit, reason at LOW, self-resume). The fixture was
   aligned (`FRK_Hold`) and the test extended (case 17); r2–r4 pass.
7. **Interface scan.** TIA lists the bench on both the physical adapter and the PLCSIM
   virtual adapter; the physical one (`#2`) was used.
8. **Station project location.** The project was moved from a session scratch folder to
   `%LOCALAPPDATA%\Fraktal\TiaStations` and verified (`TLS online, no trust`) there.
10. **Source round-trip (first look at S4).** `export --scl` regenerated all 41
    sources (27 blocks, 14 types), none skipped. Declarations, attributes and comments
    inside blocks survive; whitespace is normalized, a file-level comment above a block
    moves inside it after `VERSION`, a two-line trailing comment is joined, and TIA
    writes the member as `"Name"` itself. **TIA reads a BOM-less source as ANSI:** the
    UTF-8 `—` and `§` in comments came back as `â€”`/`Â§`, i.e. the text stored in the
    project is already wrong. Rule for the next iteration: Fraktal/TIA sources are
    ASCII-only (a UTF-8 BOM is untested). The deployed fixture is left unchanged so
    the identity claim of §1 stays true.
11. **Driver defect found and fixed in source:** subscribing to `OnlineLegitimation` a
   second time in one session throws; plans r3/r4 therefore ended with a `fatal` in
   their trailing `online-state` step after a successful download. The fix
   (unsubscribe per step) is in the current source, built but not yet whitelisted.

## 4. Lost artifacts (honest record)

The log of the first legacy download (06:17 UTC, the first `Success`) and of the
failed download after the project was recreated were overwritten by later runs that
reused their file names. Their outcome is stated in §3.5 from the session transcript;
the surviving files are listed in the folder. No result above depends on them.

## 5. Still owed

S1/S7/S8/S9 (OPC UA server, unchanged HMI), S3 memory figures (work-memory use of
this image and per type), S11 GRAPH leg on S7-PLCSIM V20 (S7-1500), S4 canonical
round-trip comparison (item 10 is a first look, not a gate), S12 type map (`DTL` over OPC UA), and the R1 items left open in
`TIA_R1_PLATFORM_BASELINE_2026-10-08.md` (licence inventory, OPC UA licence,
S7-1500 target).
