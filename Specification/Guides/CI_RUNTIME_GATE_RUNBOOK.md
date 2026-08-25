# Finishing the PLC CI gate — runbook

Companion to `TWINCAT_XAE_WORKFLOW.md`. That guide records what the gates do and
what was measured; this one is the ordered set of actions that takes the PLC
half of CI from where it stands to the §5.7 bar.

**Where it stands (2026-08-16).** `PLC object check` ran green on commit
`0e16d51` — five steps, all five solutions, 2 m 44 s, from a clean clone. That is
the first licensed PLC compilation this repository has had in a hosted gate.
`PLC TcUnit` is skipped by design. The runner then de-registered itself.

Read §A and §B before doing anything: §B contains two decisions that change what
§C and §D are worth doing.

---

## Decisions taken (2026-08-16)

Recorded here because §C and §D branch on them, and because a decision that only
lives in a conversation gets re-litigated.

| | Decision | Consequence |
|---|---|---|
| **Autostart rule** | **§5.7 stands unchanged.** Not narrowed | C-1 is not implemented |
| **Runtime gate** | **Stays manual**, by the §6.2 operator procedure | §C and §D are out of scope; §E item 2 is not pursued |
| **Licensing** | Stay on **trial**; may change if the project warrants it | Checks run **advisory**, never *required*; §E item 4 out of scope |
| **Isolated runtime** | **Hold.** Not standing up the isolated VM yet | Evidence stays qualified as development-runtime |
| **Runner** | **On-demand, never left listening** | Registration persists; `run.cmd` started deliberately, see §A5 |

**What this means, stated plainly.** The compile gate is closed and running. The
runtime gate is not being automated: §5.7 keeps its blanket autostart
prohibition, and the only mechanisms that would start a PLC unattended either
require narrowing that rule (C-1) or a separate toolchain (C-2). Neither is being
taken.

The honest consequence is that **§5.7's "green in CI" stays unreachable for every
module type**, so conformance claims remain per-release and hand-run rather than
continuous. That is a deliberate position, not an oversight: a §6.2 operator run
produces genuine results, and `Read-TcUnitResults.ps1` removes the transcription
step once a PLC is running by any route.

§C and §D below are retained as the record of what was investigated and what the
options cost, should the position change. **Do not implement them without
revisiting the decisions above.**

---

## A. Restore the compile gate

The runner was registered `--ephemeral`, which accepts exactly one job and then
removes itself. The repository currently reports **zero runners**, so the next
push has nothing to run on.

### A1. Re-register without `--ephemeral`

From the runner directory (currently `C:\Projects\Fraktal\actions-runner`, which
is inside the working tree — see A3):

```powershell
.\config.cmd remove --token <REMOVAL_TOKEN>
.\config.cmd --url https://github.com/MrFrakt/Fraktal --token <REG_TOKEN> --labels twincat,twincat-test
.\run.cmd
```

Get both tokens from **Settings → Actions → Runners**. Add `twincat-test` now
even though the TcUnit job stays off — it costs nothing and saves a
re-registration in §D.

`self-hosted`, `Windows` and `X64` are added automatically; label matching is
case-insensitive, so the workflow's lowercase `windows` matches.

### A2. Do not install it as a service

`Invoke-TwinCatBuild.ps1` drives XAE through out-of-process COM
(`VisualStudio.DTE.18.0`). Under LocalSystem it runs in Session 0 with no user
profile or desktop, where DTE automation is unreliable. Run it interactively. For
unattended operation, autologon a dedicated account and start `run.cmd` there.

### A3. Move the runner out of the working tree

It keeps a full second checkout under `_work/`. `.gitignore` covers
`actions-runner/` so a stray `git add -A` cannot commit it, but the nested clone
still sits inside the project. Move the folder to `C:\actions-runner` and re-run
`run.cmd` from there; it is not a service, so moving the directory is sufficient.

### A4. Confirm

Push anything, or use **Actions → CI → Run workflow**. Expect
`PLC object check (self-hosted TwinCAT)` to complete in roughly three minutes
with `PLC TcUnit (isolated runtime)` skipped.

**Exit:** two consecutive green object-check runs on `main`. **Met** —
`0e16d51` and `313c317`.

### A5. Operating model: on-demand, never left listening

The repository is public and the runner reaches a machine with a licensed XAE and
a PLC runtime. GitHub advises self-hosted runners only on private repositories.
Rather than leave a listener up unattended, the runner **stays registered but is
started deliberately**.

Because a runner with matching labels exists, `plc-object-check` **queues**
instead of skipping when nothing is listening — GitHub holds it for roughly 24
hours. `ci.yml` sets `cancel-in-progress: true` on a per-ref concurrency group,
so consecutive pushes cancel the older queued run and only the newest survives.
Work therefore accumulates as a single pending compile of the latest commit.

To collect it:

```powershell
cd C:\Projects\actions-runner
./run.cmd          # takes the queued job, ~3 minutes
# Ctrl+C when it returns to "Listening for Jobs"
```

Do this before a release, and after any change to `Fraktal_Core` or
`Fraktal_Modules` — a library change that breaks a consumer is the regression
class this gate exists to catch, and it is the one that actually occurred here on
2026-08-14.

**Keep `HAS_TWINCAT_RUNNER` set to `true`.** Deleting it makes the job skip rather
than queue, which looks tidier but discards the pending-compile behaviour that
makes this model work. The cost of the model is that a run shows *in progress*
until the runner is started; that is the intended trade, not a fault.

Two standing conditions, since the runner is registered rather than removed:

- **Fork-approval must stay at "Require approval for all outside collaborators."**
  It is the control that prevents an unapproved fork PR queueing work that would
  execute the moment `run.cmd` starts.
- The runner lives at `C:\Projects\actions-runner`, outside the repository tree.
  Keep it there; installed in-tree its `_work/` accumulates a second clone of
  this repository inside itself.

---

## B. Two decisions that are not engineering

### B1. Licensing — do not mark these checks *required* yet

The host carries trial licences. Renewal is an interactive captcha, so a required
check fails every seventh day, and a required check that fails predictably is one
people learn to bypass.

Run the compile job **advisory** until a permanent licence exists. It already
earns its keep: it catches "a library changed and a consumer no longer builds",
which is the exact regression this repository hit locally on 2026-08-16.

Branch protection is the last step of §E, not a step here.

### B2. Does §5.7's autostart prohibition mean what it says?

This decides whether §C is a small change or a project. AGENTS.md §5.7:

> `Fraktal_Tests` and `PressTests` run only on an isolated test runtime/ADS port
> with Autostart Boot Project disabled; **never deploy either as the machine boot
> application**.

The clauses differ in scope. The second names the hazard — a test application
auto-starting on **equipment**. The first is written as a blanket prohibition and
is what the gates assert.

It matters because **the boot project is the only known way to start a PLC with
no person and no IDE prompt**, and closing G9 through it costs far less than any
alternative. A dedicated CI runtime that controls no I/O is not "the machine".

Against narrowing it: we already hit the failure mode. A stale
`Port_851.autostart` marker dated 2026-08-06 survived on the development runtime
and had to be deleted by hand, precisely because boot state outlives the run that
created it.

**Decide one:**

- **Narrow the rule** to "never on a runtime with I/O; the gate must clear the
  boot project afterwards" → take path C-1. Update AGENTS.md §5.7 and
  `TWINCAT_XAE_WORKFLOW.md` §6.1 together with the code, in the same commit.
- **Keep it as written** → take path C-2.

Do not take C-1 without editing the rule. A gate that violates a documented
assertion is worse than either option.

---

## C. Close G9 — start a PLC without a person

`ITcPlcOnline.Login()` returns without error, writes nothing to any of the ten
DTE output panes, and leaves `IsLoggedIn` false with `OnlineOperationState` 0
indefinitely. Everything up to activation is verified. The eliminated hypotheses
are listed in `TWINCAT_XAE_WORKFLOW.md` §9.1 — do not re-test them.

### Path C-1 — boot project + autostart (requires B2 narrowed)

**C-1.0 — verified 2026-08-16. The premise holds.**

Activation writes the boot application, with no login and no download involved.
Measured on the local development runtime: the gate run started 14:33:56, failed
at the login assertion (`IsLoggedIn` false, `OnlineOperationState` 0), and
`Port_851.app` and `Port_851_boot.tizip` were nevertheless written at
14:34:13–14. Nothing else was driving that runtime.

`Invoke-TwinCatTcUnitGate.ps1`'s header asserted the opposite — "It never
generates a boot project" — and has been corrected. **C-1 is therefore a live
option, gated only on B2.**

Repeat the check below on the isolated runtime before relying on it there, since
the measurement above is from the development runtime:

On the isolated runtime:

```powershell
# 1. Note the current boot state
$boot = 'C:\ProgramData\Beckhoff\TwinCAT\3.1\Runtimes\<Instance>\3.1\Boot\Plc'
Get-ChildItem $boot -Filter 'Port_851.*' | Select-Object Name,Length,LastWriteTime

# 2. Activate through the gate (it will still fail at login - expected)
.\FraktalCore\PLC\TwinCAT\tools\Invoke-TwinCatTcUnitGate.ps1 `
  -Solution FraktalCore\PLC\TwinCAT\Tests\FraktalTests.slnx `
  -TargetNetId <ISOLATED_NETID> -ExpectedNetId <ISOLATED_NETID> `
  -ExpectedRunner PRG_TcUnitRunner -ExpectedTests 106 -ExpectedSuites 31

# 3. Did Port_851.app and Port_851_boot.tizip update?
Get-ChildItem $boot -Filter 'Port_851.*' | Select-Object Name,Length,LastWriteTime
```

If their timestamps advanced, activation writes the boot application and the
premise holds. If not, C-1 is dead — go to C-2.

**C-1.1 Prove it starts unattended**

Still by hand, once, before touching the gate:

1. In XAE on the isolated target, enable **Autostart Boot Project** on the PLC
   project and activate.
2. Restart TwinCAT (`TwinCAT → Restart TwinCAT System`).
3. Without logging in, run the reader:

```powershell
.\FraktalCore\PLC\TwinCAT\tools\Read-TcUnitResults.ps1 `
  -NetId <ISOLATED_NETID> -OutputLog artifacts\tcunit\probe.log
```

A summary here means the whole problem is solved: the application ran on its own
and the reader read it. This is also the first end-to-end proof of
`Read-TcUnitResults.ps1`, which has never read a live run.

**C-1.2 Fold it into the gate**

Replace the login/start block in `Invoke-TwinCatTcUnitGate.ps1` with:

1. set `BootProjectAutostart` **true** on the PLC project;
2. activate, restart, wait for `IsTwinCATStarted()`;
3. call `Read-TcUnitResults.ps1`;
4. **in `finally`**: set autostart false, re-activate, and delete
   `Port_851.autostart` from the runtime's Boot folder.

Step 4 is not optional and is the whole reason B2 needs deciding rather than
assuming. A run that aborts between 1 and 4 leaves a test application armed to
start on the next reboot. Assert in step 4 that the marker is gone, and fail the
gate if it is not — a cleanup that fails silently recreates the Aug-6 marker
problem.

Keep both existing safeguards intact; §9 permits automation only with them:
the `-ExpectedNetId` refusal, and a hard failure if the target has any I/O
configured.

### Path C-1.3 — load the boot project on demand — **investigated, does not exist**

This was proposed as a way to avoid the §5.7 decision entirely: if the runtime
could be told to load a boot project *as an action*, the gate would get a running
application with no login and no prompt while Autostart stayed disabled. The
premise was `PLC_OPSTATE_LOADBOOTPROJECT` (8192).

**It was a misreading, resolved 2026-08-16. Do not re-open it.**

`PLC_OPSTATE` appears in `TCatSysManagerLib` *only* as the return type of
`get_OnlineOperationState`. It is never a parameter to anything. It is a status
readout: `LOADBOOTPROJECT` reports that the runtime **is** loading a boot project,
and cannot be used to ask for one.

A full sweep of the library for members matching Boot / Load / Download /
Activate / Restart gives the complete boot surface, and there is no load action in
it:

| Member | Effect |
|---|---|
| `GenerateBootProject(Boolean)` | creates a boot project |
| `get/set_BootProjectAutostart(Boolean)` | reads/sets the persistent flag |
| `CreateOfflineBootPrj(String)` | offline creation |
| `ActivateConfiguration()`, `StartRestartTwinCAT()` | already called by the gate |
| `BeforeDownload` / `AfterDownload` | notification hooks, not commands |

`TcXaeMgmt` is not installed, and would not change the conclusion: loading an
application requires either a download or a boot-load. There is no third
mechanism.

**One useful result.** `set_BootProjectAutostart(Boolean)` is settable at runtime
through automation, so C-1's *transient* variant — arm, activate, restart, run,
read, disarm, re-activate within a single run — is mechanically clean and needs no
file manipulation. The implementation is small. What blocks C-1 is therefore
entirely the rule, and always was.

### Path C-2 — drive the runtime without the IDE (no rule change)

TcUnit-Runner is the known tool for this. Budget real time: it is a separate
toolchain to install, license-check and wire, and it must still satisfy the §9
constraints on target identity and destructive state.

Whichever path is taken, `Read-TcUnitResults.ps1` is unaffected — it only needs a
running PLC.

---

## D. Wire the TcUnit job

Only after §C produces a result without a person.

### D1. The isolated runtime

`ci.yml` requires the hook never target a machine runtime. The committed target
`192.168.132.128.1.1` is unreachable; everything to date ran on the development
runtime. Stand that VM up, or designate another runtime that drives no I/O, and
put its NetId in the test wrappers.

### D2. The hook

`TCUNIT_RUNNER_SCRIPT` must point at a runner-local `.ps1` — deliberately not in
the repository, because it encodes machine-specific NetId and ports, and because
a repo-resident script that drives a runtime is one a pull request can edit.

Contract, fixed by `ci.yml`:

```
& $runner -Gate <CoreModules|Press> -Solution <abs .slnx> -OutputLog <abs path>
```

Exit 0 on success, and write to `-OutputLog` a file containing **exactly one**
TcUnit summary. `tcunit_to_junit.py` then validates it and rejects a log holding
two summaries, so a capture window that catches a green run followed by a red one
cannot be graded green.

A minimal hook is a wrapper: call `Invoke-TwinCatTcUnitGate.ps1` with the
runner's own NetId and the expected counts, and copy its raw log to `-OutputLog`.

### D3. Switch it on

Settings → Secrets and variables → Actions → Variables:

```
HAS_TWINCAT_TEST_RUNTIME = true
TCUNIT_RUNNER_SCRIPT     = <absolute runner-local path to the .ps1>
```

The editor hints on `ci.yml` lines 190 and 196 ("Context access might be
invalid") are the extension resolving these against variables that do not exist
yet. They disappear on their own here — they are an accurate status indicator,
not a defect.

### D4. Evidence

Per `TWINCAT_XAE_WORKFLOW.md` §8, retain repository revision,
`.plcproj`/runner/TMC hashes, XAE/XAR build, platform, target identity and ADS
port, autostart state, runner identity, all five TcUnit summary fields, the raw
log and the generated JUnit. A result without those identities is diagnostic
information, not release evidence.

Note the expected counts are **146 tests / 37 suites** (Core+Modules) and
**8 / 2** (Press). Derive them from source rather than trusting any table: the
suite count is the runner POU's `VAR` block, the test count is the `TEST('…')`
calls in the suites it instantiates. A suite that exists but is not instantiated
does not run, and would make the log self-consistent while silently under-testing.

---

## E. Exit criteria

Phase 2 as originally scoped is finished when all of these hold:

1. `PLC object check` green on `main` from a clean clone, on a runner that
   survives more than one job. — **met** (`0e16d51`, `313c317`, `e9af27f`).
2. `PLC TcUnit` green on an isolated runtime, **started and read without a
   person**, reporting 106/31 and 8/2 with matching runner identities. — **not
   pursued**, per the decisions above.
3. JUnit and log hashes archived under `Specification/Evidence/`. — follows 2.
4. Both checks required on `main`. — **out of scope** while licences are trial.

**Only item 1 is being pursued, and it is done.** Recording the rest as *not
pursued* rather than *pending* is the point: an exit criterion nobody intends to
meet is not a plan, and a status page that lists it as outstanding work
misrepresents where the project actually stands.

What replaces item 2 in practice: run the §6.2 operator procedure when a runtime
result is wanted — before a release, or after a change to a reusable type — and
read the outcome with `Read-TcUnitResults.ps1` rather than transcribing the log
window. Retain the §8 evidence set for any run that is meant to support a claim.

---

## F. The manual runtime run

Proven 2026-08-16 and recorded in
`Specification/Evidence/2026-08-17_Core_Modules_TcUnit.md`. **This is now the only
thing standing between a change and a regression**, because CI compiles but does
not execute. Ten module types ship with suites today and nothing forces them to
run; treat this as a discipline, not a convenience.

### F1. When to run it

- before a release;
- after any change to `Fraktal_Core` or `Fraktal_Modules`;
- after adding a module type — which is every step of phase 4.

### F2. How

1. Open the gate solution in XAE, select the local target, **Activate
   Configuration**, then **PLC → Login → Yes → Start** (§6.2).
2. While it is still running, read the result:

```powershell
.\FraktalCore\PLC\TwinCAT\tools\Read-TcUnitResults.ps1 `
  -NetId <TARGET_NETID> -OutputLog artifacts\tcunit\manual.log

python FraktalCore\PLC\TwinCAT\tools\tcunit_to_junit.py `
  artifacts\tcunit\manual.log artifacts\tcunit\manual.junit.xml `
  --gate-name CoreModules --expected-tests <N> --expected-suites <M> `
  --expected-runner PRG_TcUnitRunner
```

3. For a run meant to support a claim, copy both files into
   `Specification/Evidence/` under a dated name and write the record with the §8
   identity set. `2026-08-17_Core_Modules_TcUnit.md` is the template.

`Invoke-TwinCatTcUnitGate.ps1 -Interactive` automates steps 1 and 2 apart from the
download prompt, which it puts on the operator's desktop. Useful, but it is not
the documented path and it activates — read §6.1 before pointing it anywhere.

### F3. The counts are pinned in three places

`ci.yml`, guide §6.3, and every evidence record. **Every new module type changes
all three.** Derive them from source rather than trusting any table: the suite
count is the runner POU's `VAR` block, the test count is the `TEST('…')` calls in
the suites it instantiates. A suite that exists but is not instantiated does not
run, and would leave the log's own totals self-consistent while silently
under-testing.

Current: **146 tests / 37 suites** (Core+Modules), **8 / 2** (Press).

### F4. Housekeeping that bites

XAE strips `BootProjectAutostart="false"` and `TargetNetId` from the `.tsproj`
whenever it opens or activates the solution. Both gates snapshot and restore
them, but an abort between snapshot and restore leaves the stripped file in the
tree — this happened three times on 2026-08-16. **Check `git status` after a
manual session**, and `git checkout --` the wrapper if it shows modified.
