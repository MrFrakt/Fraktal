# S4b-Q observer-policy retry preparation — 2026-10-29

This fresh retry is prepared under standing Echo authorization O3 for identity
`601FC87B`, 127.0.0.1 slot 0, 1756-L81E v38.011. No controller changes occur
during preparation. The false approval template is sealed before applying O3.

The image is unchanged: ACD
`30315E6D6D88B1B3133C253D41775A94CD6C26C18F29B07F548CBAA5FA3049A5`,
L5X `60C0AB6C7A40F0A5286B231E2BEF8889CA2FD96E1E2EBD8992D57C76638EBA4E`.
Working copies come from the untouched cold-start preparation. Equivalent SDK
read-back and exact-image Capacity transfer: 2,066,212 used / 1,079,516 available /
3,145,728 Blocks (65%). All 373 PLC/gate inputs remain unchanged, retaining
2,339 AB tests and both v38 build/read-back gates.

[The correction record](AB_S4B_OBSERVER_POLICY_2026-10-29.md) seals the only new
HMI changes: approved O8 tiers in the independent observer and their tests.
The desktop's 27 inputs exactly match the O8 three-profile/debug qualification;
that proof transfers by hashes. The changed observer separately passes 100
loopback samples, zero Bad samples and four configuration pages without writes.
Adaptive packing is reverted and excluded from this session. Final gates:
743 HMI passed/12 skipped, clean analyzer, locked dependencies, Windows profile
build, 74 root tests and root gates. Flutter 3.47.5 / Dart 3.13.4.

The SDK helper builds with zero warnings/errors. Missing authorization refuses
all tested entry points before controller I/O; malformed scope/target/image
records are refused. Five helper tests and eight orchestration scenarios pass.
The corrected CPU sampler survives injected invalid process-counter samples
and passes a live read-only host/emulator probe. The strict LIVE native desktop
test is prebuilt, with all 16 files hashed; no compiler runs during measurement.

Session scope: fresh guards, dump check, MANUAL normalization when needed,
preflight and backup; guarded Program/download/Run, SDK/read-back/access audits;
the unchanged 41-case fixture with corrected read-only observer; independent
87-pair replay; configuration comparison against a fresh Python oracle, idle
equivalence, generic acquisition, strict 31-view profile desktop and final
20-sample TASK timing in that order. After a writer/observer failure, a healthy
candidate still yields every independent read-only outcome under P5. Writer
operations stop at their first failure. No proof, expiry or retry limit changes.

TASK monitoring starts before download; the append-only post-download/pre-Run
host marker scopes candidate counters. Overall host/emulator CPU is recorded.
E8 requires cumulative TASK maximum below 10,000 µs and zero overlaps through
desktop completion plus the final timing samples. No counter is cleared.

The finally path restores a verified copy of genealogy
`D67561C4A30002E89B7D3F2973633D794239C5890221FF02319C5CFB93ED4084`,
the five exact original host documents, 31 baseline cases, MANUAL/idle/logout,
final checks, preflight verification and baseline timing. The original ACD is
never opened. Fault/dump/target guards remain in force. Fault/TASK-counter clears,
clock changes, power/vendor-state operations and Echo hard kills are excluded.

Workspace: `C:/work/fraktal-ab-s4b-q-20261029/session_01`. The payload binds
all runtime inputs, helpers, binary hashes and offline gates while excluding
credentials, binaries and ACD/BAK. Native improvement remains unproven. S4b exit
still requires E1–E9 together. Nothing is committed or pushed.
