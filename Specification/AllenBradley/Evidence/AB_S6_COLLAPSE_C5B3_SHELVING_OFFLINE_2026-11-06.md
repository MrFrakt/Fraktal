# S6 C5b3 shelving acceptance profile - offline qualification

Work started on 2026-11-06; final gates completed on 2026-11-07
(America/Mexico_City). UTC process times are retained in the receipts.

The dedicated shelving acceptance profile passes offline. It resolves the
source-level eligibility gap recorded by the policy migration; positive native
shelving remains S6-Q after C7. Parent `8f87f0ab5f4e1c9fb007a23e1b0f51847d2ae3a0`. The owner authorizes
commit and push on main. No controller connection, download, tag write, mode
change, fault/TASK clear, clock, power or vendor-state operation ran.

## Results

- **2,689 AB tests** by discovery from tools, **85 root tests**, **52 focused
  health/shelving/profile checks** (including the eight new profile checks),
  and all root gates pass.
- Both **v38 compiler targets build/read back** and pass SDK, native access
  and default audits. Studio offline Capacity is **54%**:
  **1,713,240 used / 1,432,488 available / 3,145,728 Blocks**,
  **+36 used** versus the qualified normal press. The canonical ACD
  is unchanged by measurement of its review copy.
- Public schema, access, initial values and all three derived manifest hashes
  are identical to the normal press. The same exact schema-difference list
  gates both profiles against the pre-collapse press; there is no new
  allowlist. There are zero uncovered differences or unused declarations.
- **65 routines are identical.** The only executable delta is the existing
  `SystemHealth.Bad[2] := 1` assignment inside its guarded evaluation block:
  ST tokens **116,007 to 116,016 (+9)**. The 102-field O10 vector, equipment,
  documents, all three AUTO renditions and command/policy owners are inherited.
- The existing harness modules load the profile through
  `FRAKTAL_AB_DECLARATION=fraktal_ab_press_s6_shelving_echo38` and agree on
  the application and reason 21, without controller access or credentials.

Prepared source SHA-256: `088D02BF7E83C587C3A9311C65C733972E7E5A4CF5140C210E0BD3ED03405275`.
Prepared ACD SHA-256: `0976205ACD482AC7093CF503A89FB7381A08C93703DEDE913062B384AD3903EF`.
These artifacts have not been downloaded and must be regenerated and
requalified after the remaining collapse increments.

## Ownership and scope

`fraktal_ab_press_s6_shelving_echo38` replaces only
`SystemHealth.require_controller_metrics` with true. Part III §8 already
permits that declaration. It is explicitly acceptance-only; the normal press
and production defaults keep unavailable metrics excluded. No warning slot,
second producer or altered rationalization is introduced. The unchanged
health owner first waits for a real prior sample, then the existing alarm
owner holds one LOW AUTO_RESET warning with no blocking effect.

Executed-ST service checks use the actual declaration before storage-name
lowering. They raise no event by direct slot injection. They exercise the
first-sample refusal, the second-sample event and unchanged original fixture
preflight, repeated scans without duplicate events, the base exclusion and
refusal, active-shelf and unknown-session refusal, manual unshelving, expiry
while logged out, and the generated access owner's refusal of a claimed
administrator. These are isolated service/eligibility checks; the typed wire
ingress, O11 gateway path, full fixture writes/restoration and live coherence
are not newly qualified by them. The full-image token/schema and compiler
gates separately cover the emitted collapsed image.

The plan now includes three S6-Q candidate images under standing O3:
genealogy, this dedicated shelving profile, then the normal press. Each keeps
fresh identity/session guards, backup, Capacity, scan and rollback gates.
The session ends on the qualified collapsed genealogy baseline per O6.

Shipping HMI/Dart sources (84 hashes) and both prepared runtime executables
match the committed C5b2 package qualification. Its 44 Dart tests, analyzer,
locked dependencies and host compilation are reused by hashes; no fresh
Flutter/UI build is claimed. The normal press and genealogy declarations and
generator are unchanged. Their prior Capacity qualifications remain separate
from this profile's measurement. No scan or retention measurement ran.

## Failed runs and remaining work

The first two focused runs exposed unsuitable historical test setup: its
release-report layout predates the current application, and toggling collapse
also changes derived localization IDs. The corrected service bench allocates
the actual declaration's native structures and executes its unchanged owners.
The first image-proof helper used `Health` instead of the emitted `ScanHealth`
routine name. The first runtime-pin invocation tried to create its receipt in
the previous work folder; create-only protection refused it, preserving that
record. Corrected fresh runs pass. All failed logs remain archived, along
with the retained control-script versions. The first report collector assumed
UTF-8 for a raw Windows log; byte-based summary extraction corrects that
without rewriting the log.

The next source-only inventory records 18 direct legacy calls and 21 row sites
in Phase 5, three legacy calls in Part, and no direct projection calls in the
genealogy wrapper. It is a starting inventory, not complete HX accounting or
acceptance: inherited calls and private/public fact mapping still need review.
Phase 5's health assertions also require reason 21, so its migration must
account for that precondition explicitly.

Next: migrate the remaining Phase 5 metrics/reports and Part/genealogy/
inherited runners, then the standalone canonical press launcher. Frame/staged
retirement and V6.12 remain C5c; C6/C7, native S6-Q, deletion/import census,
final gates and specification activation follow. O5 already selects the host
FileMedium. Under O2 there is no S7 hardware purchase: hardware-only acceptance
is a declared exclusion and deferred without a date; the software CIP Security
scope is revisited only after S4b-S6 exit.

Owner edits in `.vscode/settings.json`, the Siemens Manifest README and root
`analysis_options.yaml` are preserved and excluded. No credentials are archived.

[Payload and hashes](AB_S6_COLLAPSE_C5B3_SHELVING_OFFLINE_2026-11-06/artifact_manifest.json) bind source inputs,
outputs and failures. ACD/L5X/EXE artifacts remain private and hash-bound.
See the [working notes](../AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md)
and [plan](../AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md).
