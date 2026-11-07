from pathlib import Path
import json,re
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;NAME='AB_S6_COLLAPSE_C5B1_OFFLINE_2026-11-06'
assert json.loads((W/'ab_suite_01_exit.json').read_bytes())['exitCode']==0
log=(W/'ab_suite_01.log').read_bytes().decode('ascii','ignore');assert re.findall(r'Ran ([0-9]+) tests?',log)[-1]=='2629'
notes=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md';s=notes.read_text(encoding='utf-8');a='Offline qualification is in progress in';assert s.count(a)==1;s=s.replace(a,'C5b1 is complete offline, with 2,629 AB and 85 root tests passing. The final\n85-test focused run also passes. Qualification records are in');notes.write_bytes(s.encode())
plan=R/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md';s=plan.read_text(encoding='utf-8');a='C5 continues in two dependent increments without changing its exit gate:';assert s.count(a)==1
paragraph='''**C5b1 done offline, 2026-11-06** ([evidence](Evidence/AB_S6_COLLAPSE_C5B1_OFFLINE_2026-11-06.md)).
The capture/configuration slice uses typed Core requests, live revisions and
PLC-published refusal keys, with independent O10 value/audit checks. The
read-only viewer uses the existing Dart `readConfigurationPage` RPC and proves
START cannot commit. The S6-Q press gains the approved V6.8/V6.10 publications;
its fixture gains ten facts (40 total). All 2,629 AB and 85 root tests pass,
both v38 builds/read-backs/access/defaults pass, and schema/token proofs pass.
Press Capacity is 49% (1,554,428 used / 1,591,300 available / 3,145,728 Blocks).
Genealogy is byte-identical to C5a and retains its hash-bound 60% qualification.
No controller operations or scan measurement ran. The six native audit fields
are absent from old captures; their native acceptance remains S6-Q. The
remaining set/host lifecycle is C5b2; this does not qualify other HX consumers.

'''
s=s.replace(a,paragraph+a);a="press's configuration/set clients need the already approved read-view,\nowner-revision and host-service publications before they join.";b="press's capture client now has the read-view and owner-revision publications;\nits set clients still need the host-service publication and Dart adapter lifecycle.";assert s.count(a)==1;s=s.replace(a,b);plan.write_bytes(s.encode())
report=R/'Specification/AllenBradley/Evidence'/(NAME+'.md');assert not report.exists()
report.write_bytes(('''# S6 C5b1 - canonical capture and configuration browsing, offline

C5b1 is complete at its offline scope. C5 remains open. Parent commit
`df647e2f34b28e7c5f9962d4b93a2ea564755862`; owner authorization to commit and
push on main persists. No controller connection, download, tag write, mode
change, fault/TASK-counter clear, clock or power operation ran.

## Result

- **2,629 AB tests**, discovered from the tools directory; **85 root tests**;
  `check_ab_spec`, `check_ab_contracts`, and strict consistency pass.
- **85 focused tests** pass, including the new six hostile/native key-table
  tests and eleven capture/RPC/metadata tests. The old accepted press captures
  replay with their four newly consumed raw facts and unchanged press predicates.
- The press builds and reads back for **EchoController and PhysicalController**
  on v38. SDK log gates, native layouts/defaults and effective access pass.
- **Capacity:** 1,554,428 used / 1,591,300 available / 3,145,728 Blocks,
  displayed **49%**, measured by Studio on the review copy. The pinned ACD
  remained unchanged. Growth from C5a is 107,356 used Blocks.
- Genealogy's generated source is byte-identical to C5a; its two-target
  build/read-back/access/default and 60% Capacity evidence is reused only after
  exact artifact hashes are checked. Both frozen legacy declarations remain
  byte-identical under the full AB suite.
- Schema checks have zero uncovered differences and zero unused declarations.
  A frozen C5a source reference, with only the two approved feature flags
  enabled, has **62 identical routines**. The fixture routine differs only by
  the exact literal append for ten O10 facts. The 224 other `fraktal_ab` source files
  checked by that proof are unchanged.

Press source: `B96586AAB934145336B723022017723BE985E22938E0B2FC2669E738B3BB66D8`.
Press ACD: `D41054973FB4DC0E3B3541AA84C22934F9B9F1DDA5FA1A0C390967DC7B4D0457`.
Genealogy source: `5557604A02885ECE5C67392B552F41F15FDC9B747ED139E275D987064273A95A`.
These are offline prepared artifacts, not claims of a downloaded image.

## Change and preserved acceptance

Phase 6 capture sends typed Core arguments with dotted/root identity, the
portable key and live PLC configuration revision. It uses no Frame encoder.
The apparatus checks the stored native value and audit independently of the
gateway, including the ignored 999999 candidate, accepted-write audit,
refusal/no-change checks, setup/air gates, restoration and final disarm.
Restoration's WRITE_CONFIG also uses the live revision and typed value text.

Refusal/source-key expectations come from the command binding's published
key table. Native Templates determine names, widths and bytes; sparse IDs
are valid. Duplicate/malformed keys, invalid layouts and a changed root
revision refuse without caching partial metadata. The immutable cache lives
for one guarded connection; it supplies no cyclic value.

The separately owned, hash/target-pinned read-only Dart gateway browses with
`readConfigurationPage`, checks the key and unchanged controller sequence,
then refuses START before commit. The approved S4b/D9 API replaces the old
Python QUERY_CONFIG write exception. The approved S3k Core foreign-root
refusal is TARGET_KEY rather than the legacy CONFIG_KEY_UNKNOWN_KEY. These
protocol-specific adaptations are explicit; machine/restoration checks stay.

The press enables the approved V6.8 read view and V6.10 owner revisions. No
new contract choice or weakening of proofs/freshness is introduced. O10 grows
from 30 to 40 facts: configuration schema/baseline, six audit fields, last WORK
and air permissive. The audit retains all 16 native cells. Access masking and
configuration values are never reconstructed client-side.

## Scope, failures and pending work

The 86 old accepted press captures contain the four new configuration,
profiler and air facts. They contain **no ConfigAudit bytes**. Its six fields
have generated-writer/ST-model and exact-code proof, with native acceptance
still open at S6-Q after C7. Scan cannot be measured offline. There is no
new native acceptance or claim that the full Phase 5/6 or HX suite migrated.

The initial focused run loaded the old count/header expectations and lacked
mappings for the added raw replay surfaces. Its failures are retained; the
corrected 85-test focused run passes. The first frozen-reference generation
lacked its external Core constant file; the exact parent support files were
added and the fresh run passed. An inline schema helper's final display raised
`KeyError: differences` after writing the passing schema result; the full
gate validates the final declarations independently. These are tooling runs,
not controller failures. Logs keep the existing websockets deprecation warning.

Shipping HMI/gateway/client files are unchanged by hashes. Flutter and Dart
suites are not rerun for this increment; C5a's 44 gateway tests/package and
SDK result remain bound to those exact bytes. No live credentials were read or
archived. Owner changes in `.vscode/settings.json`, the Siemens Manifest
README and root `analysis_options.yaml` are excluded.

Next is **C5b2**: supervised Dart V6.11 set/document workflows with an isolated
store, explicit original restoration, and no Python broker/keeper interception.
Other HX consumers still need fact accounting and migration. Frame/staged
endpoints stay until C5c/V6.12; C6 exposure/tables, C7 production AUTO and
integrated S6-Q follow, then S7 physical CIP Security acceptance. Persistence,
site write posture, hardware and final retirement decisions remain as the plan
records; this increment does not settle them.

## Records

The append-only [payload manifest](AB_S6_COLLAPSE_C5B1_OFFLINE_2026-11-06/artifact_manifest.json)
contains hashes for the exact test receipts, raw logs, source freeze,
preparation, source/reference/code/schema proofs and fact/case accounting.
ACD/L5X/EXE/reference ZIPs remain private and are hash-bound in the payload.
Prior genealogy proof is [C5a](AB_S6_COLLAPSE_C5A_OFFLINE_2026-11-06.md).
The [working notes](../AB_CANONICAL_PUBLICATION_C5_NOTES_2026-11-06.md) and
[plan](../AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md) record the next gate.
''').encode())
print('Updated plan, C5 notes and C5b1 report')
