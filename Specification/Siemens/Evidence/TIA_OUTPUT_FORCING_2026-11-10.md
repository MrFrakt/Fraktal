# Output forcing on Fraktal/TIA (P8 slice, 2026-11-10)

Core §10.5.1 output forcing is implemented for the Siemens binding as an
engineering-image feature behind the framework `OUTPUT_FORCING` gate. Part IV
§10.5 records the realization; this note records what was measured.

## What is generated

| Image | Force surface |
|---|---|
| Production (gate inactive, the shipped press) | none: no force code, `Forceable` private, `FORCE_CHANNEL` refused as unsupported and audited |
| Engineering (`integration.output_forcing: true`) | `OUTPUT_FORCING` registered and annunciated; `Forceable` published TRUE on the declared outputs only; request, permit and apply generated |

- `Framework/Core/output_forcing.scl.in`: `FRK_ForceRequest` (§7.7 `MANUAL`,
  then the permit flag, then the table proves path, OUTPUT, `Forceable` and root
  ownership) and `FRK_ForceTick` (per-scan permit = Unit idle in `MANUAL`,
  falling edge withdraws every force with one audit record).
- `fraktal_tia_topology`: forcing-aware publication, refusal of a forceable
  input, an undriven output or two forceable tags on one image member, the
  per-project apply function, and the owning root's two frame lines.
- The press hardware driver calls `F_PressDemoApplyForces` at the end of its
  physical-output branch only; under `USE_SIMULATION` that branch is not
  reached, so the simulation gate still holds every terminal FALSE.
- Access audit: every `FORCE_CHANNEL` request is logged against the channel
  path as `std.audit.channelForced`/`channelForceCleared`/`channelForceRejected`,
  the forced value appended; withdrawal logs `std.audit.forcesWithdrawn`.

The press marks its six valve coils forceable. TC3 also marks the two start
lamps; here both lamp tags are driven from one image member (`StartLamp`), so a
per-tag force cannot be honoured and the generator refuses it. The control-power
coils `_000K951_A1`/`_000K911_A1` carry no application source and can never be
forceable (rule 4).

## Native results

| Run (`%LOCALAPPDATA%\Fraktal\TiaSpikes\…`) | Content | Result |
|---|---|---|
| `P8_PressForcing_20261110_01` | engineering-image press, 288 sources | compile 0 errors / 0 warnings in both stages; read-back 624 objects, 165 interfaces, 72 DB interfaces |
| `P8_PressShipped_20261110_01` | shipped press, 286 sources | compile 0/0 in both stages; read-back 621 objects, 165 interfaces, 72 DB interfaces; source inventory identical to the committed tree |
| `TiaGate_P8_20261110_01` | full gate: host gates, Operations fixture and reusable-module fixture compiled fresh, Operations downloaded to the isolated reserved CPU | PASS: 292 tool tests, lint/consistency/contracts clean, press replay 286; Operations fixture 0/0, read-back 297/85/22; module fixture 0/0, read-back 300/91/16; bench **108/108** assertions, image hash `a6571a787c91ee6cb98ac54a5435571cec01c885c6fe75ea36c427105b49b19e`; the saved `Fraktal` instance read RUN with unchanged addresses and zero mappings before and after |

The engineering image's own `tia_lint` run reports one `T-GEN` finding,
"changed authoritative inputs": lint replays the committed `press.json`, whose
gate is off, so an engineering image is not mistaken for the shipped press. It
has no structural finding.

The fifteen new Operations assertions run the generated services against a
generated four-channel topology: capability only on declared outputs; refusal
below MANUAL access and before the permit; arm, apply over the application
demand, `'TRUE'` (not exactly `true`) decodes FALSE; refusal of an input, an
unmarked output, another root's output and an unknown path; clear returns the
demand; leaving idle MANUAL withdraws and logs once; no force after withdrawal;
a permit edge with nothing forced logs nothing.

## Limits

- The real press mailbox path (login, MANUAL, `FORCE_CHANNEL` over the Web API,
  withdrawal on START) is compiled but not exercised live; that needs the
  authenticated press feature bench (`Tests/PressTests_TIA`).
- The CPU's own force jobs (TIA force tables) have no runtime API; annunciating
  a native force job is not implemented.
- Native PROFINET node health (`DeviceStates`/`ModuleStates`) is not
  implemented: the approved Openness driver cannot create an IO system, so no
  fresh fixture can contain a PROFINET device to test against.
- No HMI change beyond four catalogue strings; the HMI suite was not run because
  this host has no Flutter SDK.
- Physical output feedback and motion/SAT acceptance remain open.
