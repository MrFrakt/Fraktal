# How to work on Siemens controllers from this workstation — lessons (2026-10-08/09)

How to work, not what the products do; the product facts are in `verified-gotchas.md`,
`graph-simaticml-and-plcsim.md` and `plc-communication-options.md`. Each rule names the
incident that taught it. Read this before the first controller or Openness action of a
session.

## 1. Controller-changing acts

- **Authorization is per act, and the target is checked right before it.** Run
  `s7_probe.py ident` immediately before every download or mode change. Pass the exact
  address (`--confirm-target`, `-ConfirmTarget`). Read what you are about to change,
  then change it. This holds for the simulator too: PLCSIM mode/power actions accept
  only a Softbus instance whose ControllerIP matches.
- **The station project is the controller's identity.** After the first download the
  CPU trusts only that project's certificate. A recreated project was locked out
  ("Connect to module failed" / "Changing to online mode failed"). Keep one project per
  station in `%LOCALAPPDATA%\Fraktal\TiaStations\` and regenerate only the program
  inside it. Trust on first use (`--trust-plc`) is a logged recovery on the command
  line, never a plan default. A *newly registered* PLCSIM instance is a new identity
  and needs that step once.
- **Security questions are never blanket-accepted.** Every download question is logged
  with its offered choices. The driver answers protection, user-management and
  unencrypted-data questions only when an explicit flag says so; plans give
  `um=`/`protection=` no default, so a missing answer stops the plan before TIA starts.
- **Restore what you granted.** A right added for one test (for example
  `WebChangeOperatingMode` on the diagnostics user) is removed afterwards. Verify the
  removal by listing the users, not by trusting the plan's exit code.

## 2. The Openness driver and its whitelist

- The Openness firewall keys on the **exe's SHA-256**, headless sessions included. An
  unknown build fails with "Security error. The operation has timed out". Only the
  owner can whitelist, in an elevated shell (`Enable-TiaOpenness.ps1`). VS Code's shell
  is not elevated, and the classifier rightly refuses privilege changes.
- **Never rebuild over an approved exe.** An in-place rebuild once discarded a build
  that had just been approved. Build candidates into a separate folder
  (`bin\candidate…`), keep `bin\Release\net48` untouched, and hand the owner the exact
  path and hash. Check approval against
  `HKLM\SOFTWARE\Siemens\Automation\Openness\20.0\Whitelist\Fraktal.Tia.Cli.exe\Entry`
  → `FileHash` (Base64 SHA-256).
- **Batch driver changes; prefer generic commands.** `service-get/set/call`,
  `hw-attributes --probe`, `block-attribute` and `project-get/set` reach most settings
  by reflection without a rebuild. A new command costs a whitelist round.
- One TIA session at a time. A killed agent session can leave a headless
  `Siemens.Automation.Portal.exe` (its command line contains
  `-bootstrapper=…Openness…`) and a waiting `Fraktal.Tia.Cli`. They hold memory and can
  make the next run fail with "Connection to TiaPortal failed". Stop only processes
  you have confirmed as your own orphans.

## 3. Secrets

- Passwords exist only in DPAPI files (`TiaStations\*.secret`), are decrypted into an
  environment variable for the one command, and are named to tools by **variable name**
  (`--password-env`, `--plc-password-env`). Never put them in an argument, a plan, a log
  or evidence. Grep the evidence folder for `password|secret` before committing.
- `ConvertTo-SecureString` on a DPAPI hex file needs the text `.Trim()`-ed first.

## 4. Evidence and claims

- **Numbered raw logs, failures included, append-only.** Each spike gets a dated record
  plus a folder `NN_what.log`. Failed attempts stay in, because they are often the
  finding (the multi-instance refusal, the classic STOP refusal).
- **Hash what ran.** Record the SHA-256 of every deployed source and compare it with
  the hash the import logged. A later doc-only edit to a tool is stated, not hidden.
- **An inference is not a fact until a probe says so.** "A GRAPH action cannot hold an
  IF" was first written as a design rule from memory. A one-minute probe measured it
  ("Tag IF not defined") before it went into the spec. Probe before you specify.
- **Record the precondition your conclusion depends on.** "INIT_SQ runs S0" first
  rested on a run where the commanded input was already low. A field captured just
  before the event (`ExecBBeforeInit`) made the result unambiguous.
- **A clean compile does not prove a generated artifact is right.** Read it back (the
  canonical dump of TIA's re-export) and run the gate on a negative control. The
  reference chart must *fail* parity.
- Add test cases without touching measured fixtures. A second program-cycle OB (from an
  SCL source, auto-numbered 123, runs after OB1) carried the S11 rig while the S2
  sources kept their deployed bytes. A per-scan code log
  (`Step·100 + flags`) showed GRAPH's execution order directly.
- `compile --hw` and the software compile are separate gates. A download followed by
  a TIA crash is a failed plan even when an independent harvest is green.

## 5. Workstation limits

- About 4 GB RAM and a 12 GB page file. TIA plus a running virtual CPU plus the help
  service exhausted commit memory and killed an import. Power the PLCSIM instance off
  (`-Action off`, which keeps registration) for offline builds.
- The first `PowerOn` after the PLCSIM Runtime Manager cold-starts can return
  `InstanceNotRunning`. Retry with a bound.
- PLCSIM's `host` action ends after `-MaxMinutes` (default 120) and **unregisters**, so
  the next registration needs the trust step again.
- Long waits: run the job in the background and poll a condition (an until-loop on a
  log line). Never sleep blindly.

## 6. Text, encodings, shells

- SCL sources must be **ASCII**: TIA reads BOM-less files as ANSI and double-encodes
  UTF-8. TIA exports are UTF-8 **with BOM** and CRLF; keep them byte-exact as evidence
  and templates.
- The Fraktal repo is byte-exact (`* -text`) and LF by convention. On Windows, Python
  `write_text` writes CRLF, so write bytes. PowerShell `Out-File -Encoding utf8` adds a
  BOM. `Get-Content -Raw` → `WriteAllText` double-encodes UTF-8. Before editing a file,
  count its line endings from bytes (Python), not with `grep -c $'\r'`, which miscounted.
- PowerShell 5.1: no `&&`/`||`; `Remove-Item Env:X` can be blocked, so use
  `$env:X = $null`; native-exe arguments lose embedded quotes, so put complex input in
  a script file. Complex `python -c` one-liners are fragile; write a heredoc or a file.
- Legacy CPU web pages: always log out (`GET /FormLogin?LOGOUT`). Abandoned sessions
  locked every form login for about 33 minutes.
- Web API on S7-1200: one persistent, warm HTTPS connection (the handshake takes about
  2.75 s) and small batches. The server serves one request at a time across all
  clients.

## 7. Spec hygiene (Fraktal Part IV)

- A measured fact goes into the spec with its scope (family, firmware, simulator or
  hardware). Anything unmeasured stays `[PROVISIONAL Sx]`. Update the spike register
  status, the port plan's next steps, this KB and the agent memory in the same change.
- Commit or push only when the owner asks, and only your own files. A pre-existing
  unrelated change, such as `FraktalCore/HMI/native/opcua/CMakeLists.txt`, stays out.

## 8. Resumed Siemens workspace, 2026-10-14

- Historical HMI snapshot trees are evidence, not standalone Dart packages.
  Exclude them from analyzer/project discovery. The supplied15,811 Problems
  entries were dominated by15,809 archived-snapshot errors. **[measured]**
- Select the actual Siemens solution for this workspace. The auto-generated
  root solution also restores an AB probe whose local Rockwell SDK feed is absent.
  Fraktal.TIA.sln restores/builds0/0 without altering AB dependencies. **[measured]**
- Native path discovery must precede read-tier configuration and the first
  sample on a large station. Manifest metadata must join discovered array
  containers, including compact Siemens paths; a compile or static-only chart
  does not prove history hydration keeps step numbers. **[measured]**
- After a host restart, verify keeper process identity and persisted simulator
  storage. Historical PIDs can belong to unrelated processes. Current restored
  Fraktal keeper5380 has no expiry; do not terminate/unregister it. **[measured]**
