# Seeing the HMI without a screen

Two `flutter test` entry points render the **real** generic HMI, headless and
with real fonts, against its integrated demo (`SimRepository`). They exist so a
person, a CI job or an AI agent can look at any state of the HMI with one
command — no display, browser, emulator or MCP server — and get back both a
PNG and the same screen as text.

| Entry point | What it does |
|---|---|
| `capture_test.dart` | Renders the screenshot catalog (`shots.dart`) into `doc/screenshots/`: one PNG per feature, a `.txt` twin of each, `manifest.json` and the catalog page `README.md`. |
| `script_test.dart` | Runs a JSON script you write — boot, wait for the plant, navigate, act, capture, describe — and prints what the screen says. |

Run both from `FraktalCore/HMI`. Neither is part of the normal suite:
`flutter test` with no path only runs `test/`.

## The catalog

```
flutter test tool/screenshots/capture_test.dart
```

| Variable | Effect |
|---|---|
| `FRAKTAL_SHOTS` | Comma list of shot ids; a trailing `*` matches a prefix (`overview,theme-*`). Default: all. A partial run merges into the existing `manifest.json`. |
| `FRAKTAL_SHOT_DIR` | Output folder. Default `doc/screenshots` (git-ignored: the pictures are generated, and the websites keep their own copies). |
| `FRAKTAL_SHOT_SCALE` | Device pixel ratio of the PNGs; `2` for retina/landing-page use. Default `1`. |

In PowerShell: `$env:FRAKTAL_SHOTS='overview'; flutter test tool/screenshots/capture_test.dart`.

Each shot is staged by a script that only does what an operator, an engineer or
the plant does: log in, navigate, press, or wait for the demo plant to get
there (`SimTour` in `lib/data/sim_repository.dart`). A shot whose moment never
arrives fails loudly instead of capturing the wrong screen. To add a feature,
add a `Shot` to `shots.dart`; the catalog page and manifest follow.

## Scripts (ad-hoc views)

```
FRAKTAL_HMI_SCRIPT=path/to/script.json flutter test tool/screenshots/script_test.dart
```

`FRAKTAL_HMI_SCRIPT` may also hold the JSON itself. Captures go to `out`
(default `build/hmi_script`); every `describe` prints the screen as text
between `==== HMI <name> ====` markers, so the result can be read without
opening an image.

```json
{
  "out": "build/hmi_script",
  "boot": {"theme": "processGrey", "user": "admin1", "size": [1440, 900]},
  "steps": [
    {"until": {"path": "StationA", "fault": true}, "within": 160},
    {"open": "StationA", "tab": "sequence"},
    {"describe": "jam"},
    {"reset": "StationA"},
    {"controlOn": "StationA"},
    {"advance": 2},
    {"why": "StationA"},
    {"capture": "after-reset"}
  ]
}
```

**`boot`** (all optional): `theme` (a `std.theme.*` name without the prefix:
`processGrey`, `likeABosch`, `neonCyan`, …), `language` (`en`, `es`, `de`, …),
`size` `[w, h]` in logical pixels, `scale` (pixel ratio), `controls`
(`compact`/`medium`/`large`), `user` (`op1`, `tech1`, `eng1`, `admin1`, or `""`
for nobody), `content` (seed the demo's authored tiles, views, guidance and
manuals; default `true`), `commissioning` (declare the commissioning gates and
offer output forcing; default `false`), `restoreLost`, `restoreLostPath`,
`persistFailed` (§3.8b durability), `epoch` (ISO time the plant clock starts
at; default a fixed Tuesday morning), `keyboard` (on-screen keyboard).

**Steps** — one key each:

| Step | Meaning |
|---|---|
| `{"advance": 12}` | Run the plant and the UI for 12 s of plant time. |
| `{"until": {"path": P, X: v}, "within": s}` | Run until module `P` has `step` = n, `fault`, `decision`, `blocking`, `running` or `event` (any active event) = v. Fails after `within` s. |
| `{"open": P, "tab": id}` | Open a module on a tab: `overview`, `hardware`, `statistics`, `events`, `description`, `configuration`, `sequence`, `motion`, `vision`, `code-reader`, `rfid`, `operator-guidance`, `cell-view`. |
| `{"overview": true}` / `{"fieldbus": true}` | Switch view. |
| `{"expand": P}` | Toggle a tree node. |
| `{"login": U}` / `{"logout": true}` | Session on every root (`"roots": [...]` to narrow). |
| `{"mode": {"path": P, "mode": "manual"}}` | Mode change (`auto`, `manual`, `home`, `changeover`). |
| `{"model": {"path": P, "model": "A200"}}` | Model selection. |
| `{"start": P}` `{"stop": P}` `{"reset": P}` | Start, graceful stop, operator reset. |
| `{"controlOn": P}` `{"controlOff": P}` | Control power of P's control domain. |
| `{"command": {"path": P, "value": n}}` | Manual command (§7.6.1). |
| `{"answer": {"path": P, "option": n}}` | Answer a pending decision (§6.11). |
| `{"force": {"channel": C, "value": true}}` | Force an output (`"release": true` clears). Needs `commissioning`. |
| `{"why": P}` | Open the §7.8 "why will it not start" report. |
| `{"tap": {"key"\|"text"\|"tooltip": …}}` | Tap a widget, scrolled into view first. |
| `{"enterText": "…", "field": 0}` | Type into the n-th text field. |
| `{"scrollTo": {"text"\|"key": …}}` | Scroll it to the top of its view. |
| `{"theme": name}` `{"language": code}` | Change theme or language. |
| `{"dismiss": true}` | Close the top dialog. |
| `{"capture": name}` | Write `name.png` and `name.txt`. |
| `{"describe": name}` | Print the screen as text. |

Machine actions go through the repository's gated write surface — the same
path the PLC re-checks — so a script that does something the station would
refuse fails with "the PLC refused …". The demo's users are `op1/1111`,
`tech1/4711`, `eng1/9999` and `admin1/2468`.

## What the plant does by itself

The demo repeats a 150 s tour (`SimTour`): muting of the infeed light curtain
(18–24 s), a conveyor air-pressure dip that starves Station A (36–50 s), a
tool-wear decision (58–88 s), a lost heartbeat on the conveyor (66–74 s), and
from 96 s a jam of cylinder B on the next clamp stroke, with the guard opened
and closed while it is freed. The jam latches until an operator reset, and the
station then waits for Control On and Start — it never resumes by itself. A
code-reader retry, a vision reject and an out-of-tolerance part recur at
production rate.

## How it works

`hmi_driver.dart` pumps the app in `flutter test`'s fake time, so minutes of
plant time render in seconds and every run is identical. It loads Roboto and the
Material icon font from the Flutter SDK, and Segoe UI, Cascadia Mono and
Segoe UI Symbol from Windows when present, so text renders as it does on a
panel. It sets `TargetPlatform.windows` (the desktop HMI's typography), points
the panel's clock seam `hmiNow` at the plant clock, and yields to the real event
loop before each capture so embedded pictures are decoded.
