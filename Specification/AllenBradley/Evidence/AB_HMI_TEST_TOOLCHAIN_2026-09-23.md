# Fraktal/AB — the two HMI test failures were not a toolchain delta

**Result:** **Two HMI tests were recorded as failing because of a Flutter
version delta, and they were not. Both were stale assertions, and both are now
fixed.** `flutter test` is green — 270 passing, 6 intentional live-environment
skips — and `flutter analyze` reports no issues.

The recorded explanation was tested rather than believed, which is what
falsified it: the prescribed fix was "run the suite on the pinned Flutter", and
running it on the pinned Flutter changed nothing.

**Date:** 2026-09-23

**Repository revision:** `a8f3c41`

**Scope:** the HMI test suite and the workstation toolchain only. **Nothing here
touched a controller.** The bench holds `press_closed.ACD` throughout.

## 1. What was recorded

[`AB_HMI_GATEWAY_2026-09-21.md`](AB_HMI_GATEWAY_2026-09-21.md) §"HMI offline
suite" records `cycle_gantt_test.dart §8.11.4(c)` and
`opcua_snapshot_mapper_test.dart` failing, and explains them:

> the local toolchain is Flutter **3.44.5**, CI pins **3.44.6**, and both
> failures track that delta (a `Color.colorSpace` framework addition and an
> alarm-meta count). Recorded honestly rather than worked around; the fix is to
> run the suite on the pinned Flutter.

That record was right to write the failures down rather than hide them, and
right that they were not caused by the gateway work. The *diagnosis* was wrong.

## 2. What three versions actually do

| Flutter | satisfies `pubspec.lock`? | result |
|---|---|---|
| 3.44.5 (the 09-21 host) | — | the two failures |
| **3.44.6** (recorded as "the CI pin") | **no** — `Unable to satisfy pubspec.yaml using pubspec.lock` | the two failures |
| **3.47.5** (satisfies the lock exactly) | **yes** — `Got dependencies!`, lockfile untouched | **the two failures** |

Running the prescribed fix did not fix it, and neither did running the version
the repository's own lockfile demands. The version hypothesis is falsified in
both directions.

**A second finding fell out of it: the pin itself was wrong.** `pubspec.lock`
pins `vector_math 2.4.2`, `matcher 0.12.20`, `leak_tracker 2.4.2`, `meta 1.19.0`
and `test_api 0.7.12` — packages Flutter ships *by SDK version*. 3.44.6 cannot
supply them, so a plain `flutter pub get` on it silently **downgraded all five
and rewrote the lockfile**. That rewrite was reverted, not committed.
`flutter pub get --enforce-lockfile` is what makes the mismatch loud; `AGENTS.md`
now says so and names 3.47.5.

## 3. The failures, read rather than attributed

**`opcua_snapshot_mapper_test.dart:228` — a hand-counted literal.**

```
Expected: an object with length of <61>
  Actual: has length of <77>
```

The mapper builds `alarmMeta` from `generatedReasonSymbolByCode.keys`, generated
from `Specification/reason_rationalization.json` (§8.9). The catalogue grew to 77
reasons; the test still said 61. Nothing about Flutter.

*Fixed by deriving it* — `hasLength(generatedReasonSymbolByCode.length)` — so
adding a reason cannot make it stale again. Editing 61 to 77 would have made the
symptom disappear and left the next reason to re-break it.

**`cycle_gantt_test.dart:96` — an assertion that could not hold.**

```dart
expect(tester.widget<Text>(find.text('1.6s')).style?.color, isNull);
```

The widget sets:

```dart
color: overrun ? Theme.of(ctx).colorScheme.error : null
```

inside a `copyWith`. **`copyWith` ignores a null argument**, so the in-guard
label cannot come back null — it keeps `bodyMedium`'s own colour, which under
Material 3 is `onSurface` (`#1D1B20`, exactly what the failure reported). The
test used "no colour" as a proxy for "default ink", and that proxy stopped being
true once the base text style carried a colour.

**The rendering was correct the whole time**: overrun in error ink, in-guard in
default ink, which is what §8.11.4(c) asks for. Only the test was wrong.

*Fixed by asserting the inks themselves* against the live theme — the overrun
label equals `colorScheme.error`, the in-guard label equals
`textTheme.bodyMedium.color` and is `isNot` the error ink. That states the
contract the section actually makes instead of a proxy for it.

## 4. Why this is worth a record

Both tests fail identically on three consecutive Flutter versions, which is
weak evidence for a version delta and was available at the time. The cost of the
mis-attribution was small here — two days and one wasted 1.8 GB SDK install —
but the shape is the one this programme keeps catching: **a failure explained by
something external, rather than read.** The same discipline that says
"acceptance is not publication" applies to a red test: a failing assertion is
evidence about the assertion until someone opens it.

`AB_HMI_GATEWAY_2026-09-21.md` stands as written, with a pointer to this record
added beneath the claim. Its other results are unaffected: the gateway work it
describes did not cause these failures, which is the one thing it checked
directly, on a clean HEAD worktree, and got right.

## 5. Verification

```
flutter --version   3.47.5 (stable, Dart 3.13.4)
flutter pub get --enforce-lockfile   Got dependencies!   (lockfile unchanged)
flutter analyze                      No issues found!
flutter test                         270 passing, 6 skipped, 0 failing
```

The 6 skips are the live-environment tests, unchanged and still intentional.
