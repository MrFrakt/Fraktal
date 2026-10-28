"""Record only the completed offline option A slice; never authorize a session."""
from pathlib import Path
import hashlib, json, re
R = Path('C:/Users/SoftIndVM/Fraktal')
W = Path(__file__).parent
S = R/'Specification/AllenBradley'
sha = lambda b: hashlib.sha256(b).hexdigest()


def gate(label):
    exit_ = json.loads((W/(label+'_exit.json')).read_bytes())
    assert exit_['exitCode'] == 0, label
    # Child processes write the console code page; the gates only need ASCII lines.
    return (W/(label+'.log')).read_bytes().decode('utf-8', errors='replace')


tests = int(re.search(r'^Ran (\d+) tests', gate('ab_suite_01'), re.M).group(1))
roots = int(re.search(r'^Ran (\d+) tests', gate('root_tests_01'), re.M).group(1))
cap = json.loads((W/'capacity_auto_01.json').read_bytes())
assert cap['SourceUnchanged'] and cap['VerifiedFit'] and cap['Offline']
used, available, total, shown = (cap[k] for k in ('UsedStandardBlocks', 'AvailableBlocks', 'TotalBlocks', 'DisplayedUsagePercent'))
delta, s3k_delta = used-1807120, used-1743080
for target in ('EchoController', 'PhysicalController'):
    assert json.loads(gate('readback_'+target+'_01'))['Equivalent'], target
assert json.loads(gate('prepared_compare_01'))['Equivalent']
source = sha((W/'s3k_command_a_01.L5X').read_bytes()).upper()
acd = sha((W/'command_a_01.ACD').read_bytes()).upper()
assert acd == cap['CanonicalSha256']
replay = json.loads((W/'capture_replay_01.json').read_bytes())
images = json.loads((W/'accepted_images_01.json').read_bytes())
assert replay['passed'] and images['passed']
f = lambda n: f'{n:,}'
facts = dict(tests=f(tests), roots=roots, used=f(used), available=f(available), total=f(total), shown=shown,
             delta=f(delta), s3k=f(s3k_delta), source=source, acd=acd, captures=f(replay['captures']), images=images['images'])

paths = [S/'AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md', S/'AB_FROZEN_CONTRACTS_V2.json',
         S/'AB_CANONICAL_PUBLICATION_S3K_NOTES_2026-10-25.md', S/'AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md']
before = {p.relative_to(R).as_posix(): sha((W/('before_'+p.name)).read_bytes()) for p in paths}
for p in paths[:3]:
    assert sha(p.read_bytes()) == before[p.relative_to(R).as_posix()], p


def replace(text, old, new):
    assert text.count(old) == 1, old[:80]
    return text.replace(old, new)


# Notes: header, the decided ABI section, gates and next steps.
p = paths[2]; notes = p.read_text(encoding='utf-8')
notes = replace(notes, '''S3k is in progress: read surfaces, the versioned report owner and R4 compile
offline. Command binding awaits the [A/B owner choice](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md).
No S3k controller operation is authorized or performed.''', '''S3k is in progress: read surfaces, the versioned report owner, R4 and the
owner-chosen option A [command binding](AB_CANONICAL_PUBLICATION_S3K_COMMAND_BINDING_REVIEW_2026-10-25.md)
compile offline. No S3k controller operation is authorized or performed.''')
start = notes.index('## Command ABI decision remains open')
end = notes.index('## Completed offline gates')
notes = notes[:start]+(W/'notes_command_section.md').read_text(encoding='utf-8')+notes[end:]
notes = replace(notes, '''Work: `C:/work/fraktal-ab-s3k-20261025/`, especially `read_surface_01/`.
Evidence: [offline record](Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md).
''', '''Work: `C:/work/fraktal-ab-s3k-20261025/`, especially `read_surface_01/` and
`command_a_02/`. Evidence: [read surfaces](Evidence/AB_S3K_READ_SURFACES_OFFLINE_2026-10-25.md)
and [command binding](Evidence/AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25.md).

Option A, on the full image:

- **{tests} AB tests** and **{roots} root tests** pass; AB spec/contracts, strict
  consistency and whitespace gates pass. Executed model tests cover serial wrap,
  collisions, first-scan baselines, envelope/length refusal, every refusal arm,
  DINT parser bounds, PLC-side key/revision/model resolution, full-width wipes
  on every path and the set-service status conditions.
- Source `{source}` compiles on both v38 targets and reads back
  strictly equivalent; effective access passes, the typed payload and commit
  are the only new writable tags and no command storage is observed.
- Offline ACD `{acd}` prepares and reads back equivalently.
  Automatic Studio Capacity: **{used} used / {available} available / {total}
  Blocks**, **{shown}% displayed**: +{delta} versus the read-surface slice and
  +{s3k} for S3k over accepted S3j, inside the plan's +80 to +200 K band.
- All **{images} accepted image pins** regenerate byte-identically and all
  **{captures} archived captures** replay.

Read surfaces alone:
'''.format(**facts))
notes = replace(notes, '''Resolve the A/B ABI choice, freeze its detailed wire/state table, implement
command discovery/owner integration and prove secret exclusion and all service
bindings. Then run the complete S3k offline gates on the full image, measure
Capacity and prepare native report/request regressions with exact restoration.
Only after that can a current, exact-image authorization request be made for
the guarded native session, inherited regressions, value/type equivalence and
scan measurement. This partial image is not authorized for download.''', '''Prepare the native S3k session for this exact image: inherited regressions,
up-to-24 release reasons, accepted/refused/stale/colliding typed and legacy
requests, native Template size and one-packet encoding, secret wipe, exact
restoration, value/type equivalence and scan. A current exact-image owner
authorization is required first; this offline image is not authorized for
download and no authorization is requested by these notes.''')
p.write_bytes(notes.encode())

# Plan: one new latest paragraph; the previous latest becomes "Earlier".
p = paths[0]; plan = p.read_text(encoding='utf-8')
anchor = '**Latest, 2026-10-25: S3k read surfaces and R4 pass offline; command ABI choice pending.**'
plan = replace(plan, anchor, '''**Latest, 2026-10-25: S3k option A command binding passes offline.**
The owner chose A: a typed Core payload with native BOOL and Core string
widths, PLC-side routing, one owner and a temporary legacy Frame adapter.
CommandBindings/CommandOperations (V6.6) describe every endpoint and all 39
kinds. The full image compiles/reads back on both v38 targets; access passes.
All {tests} AB and {roots} root tests pass; {images} pins and {captures} captures still
hold. Capacity is {used} / {total} Blocks ({shown}% displayed),
+{s3k} for S3k over S3j, inside the planned band. No S3k download, native
regression or scan measurement has occurred; a native session needs a current
exact-image authorization. Read [offline evidence](Evidence/AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25.md)
and the [wire draft](AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md).

**Earlier, 2026-10-25: S3k read surfaces and R4 pass offline; command ABI choice pending.**'''.format(**facts))
p.write_bytes(plan.encode())

# V2 (inactive): status only, with the owner's choice recorded.
p = paths[1]; v = json.loads(p.read_bytes())
section = next(x for x in v.values() if isinstance(x, dict) and 'stageStatus' in x)
section['stageStatus']['S3k'] = 'read-surfaces-command-binding-a-offline-pass-native-pending'
section['s3kOfflineReadSurfaces'].update(commandBindingChoicePending=False, commandBindingChoice='A')
section['s3kOfflineCommandBinding'] = dict(
    evidence='Evidence/AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25.md',
    wireDraft='AB_CANONICAL_PUBLICATION_S3K_WIRE_DRAFT_2026-10-25.md',
    ownerChoice='A', ownerChoiceQuestion='call_f17f50e248404825813327f8477a84f4:0',
    schemaMinor=6, coreArguments=9, operationKinds=39, connectionBytes=4000, maximumPayloadBytes=1024,
    fullCommandBindingImplemented=True, legacyFrameAdapter=True, nativeAccepted=False,
    controllerChangesAuthorized=False, controllerChangesPerformed=False,
    sourceSha256=source, offlineAcdSha256=acd, abTests=tests, rootTests=roots,
    acceptedImagesByteIdentical=images['images'], priorCapturesReplayed=replay['captures'],
    usedStandardBlocks=used, availableBlocks=available, totalBlocks=total, displayedUsagePercent=shown,
    deltaUsedVsReadSurfacesBlocks=delta, deltaUsedVsS3jBlocks=s3k_delta, scanMeasured=False)
p.write_bytes((json.dumps(v, indent=2, ensure_ascii=False)+'\n').encode())

after = {p.relative_to(R).as_posix(): sha(p.read_bytes()) for p in paths}
for p in paths:assert b'\r\n' not in p.read_bytes(), p
with (W/'documentation_updates_01.json').open('x', encoding='utf-8') as out:
    json.dump({n: dict(beforeSha256=before[n], afterSha256=after[n]) for n in before}, out, indent=2)
print(json.dumps(dict(updated=len(paths), **facts)))
