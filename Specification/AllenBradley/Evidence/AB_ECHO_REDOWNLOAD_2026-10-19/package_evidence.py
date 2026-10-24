"""Copy the small payload into the append-only evidence folder and bind every byte."""
import hashlib, json, re, shutil
from pathlib import Path
ROOT = Path('C:/Users/SoftIndVM/Fraktal')
WORK = Path('C:/work/fraktal-ab-echo-20261019')
NAME = 'AB_ECHO_REDOWNLOAD_2026-10-19'
DEST = ROOT/'Specification/AllenBradley/Evidence'/NAME
sha = lambda b: hashlib.sha256(b).hexdigest().upper()
read = lambda n: json.loads((WORK/n).read_text(encoding='utf-8'))

assert re.search(r'^Ran 1890 tests ', (WORK/'ab_tests.log').read_text(errors='replace'), re.M)
assert re.search(r'^OK\s*$', (WORK/'ab_tests.log').read_text(errors='replace'), re.M)
for n, count in (('root_consistency_tests.log', 35), ('root_tool_tests.log', 83)):
    assert re.search(rf'^Ran {count} tests ', (WORK/n).read_text(errors='replace'), re.M), n
assert all(r['buildClean'] and r['equivalent'] for r in read('compiled.json')['rows'])
assert all(read(n)['Equivalent'] for n in ('echo_compare.json', 'physical_compare.json',
                                           'prepared_compare.json', 'downloaded_compare.json'))
assert all(a['Clean'] for a in read('compiler_audit.json').values()) and read('download_audit.json')['Clean']
runtime = read('runtime_01.json')
assert runtime['restored'] and runtime['policyRestored'] and len(runtime['rows']) == 31
assert all(r['passed'] for r in runtime['rows'])
assert sum(r.get('genealogyChecksPassed', False) for r in runtime['rows']) == 21
assert read('final_checks.json')['passed'] and read('final_echo.json')['IsFaulted'] is False
source = (WORK/'genealogy_current.L5X').read_bytes()
assert sha(source) == '91BF67C9101EAE863CF29C1A9DF6413D7256AB056D985394587F0183AA525714'

files = ['scripts/compile.py', 'scripts/preflight.py', 'scripts/check_prepared.py', 'scripts/guard_echo.py',
         'scripts/package_evidence.py', 'session/Program.cs', 'session/Session.csproj',
         'genealogy_current_generation.json', 'compiled.json', 'echo_compare.json', 'physical_compare.json',
         'prepared_compare.json', 'downloaded_compare.json', 'compiler_audit.json', 'download_audit.json',
         'echo_build.log', 'physical_build.log', 'prepare.log', 'backup.log', 'deploy-authorized.log',
         'prepared.sha256', 'backup.sha256', 'preflight.json', 'runtime_01.json', 'runtime_01.log',
         'final_checks.json', 'final_echo.json', 'ab_tests.log', 'root_consistency_tests.log',
         'root_tool_tests.log', 'check_ab_spec.log', 'check_ab_contracts.log', 'check_consistency.log']
pin = next(u['pin'] for u in json.loads(Path('C:/work/fraktal_echo38_access_fixture.json').read_text())['users'])
for n in files:
    assert pin.encode() not in (WORK/n).read_bytes(), 'credential would be archived: ' + n
native = [dict(path=str(WORK/n), sha256=sha((WORK/n).read_bytes()), bytes=(WORK/n).stat().st_size)
          for n in ('genealogy_current.L5X', 'echo_readback.L5X', 'physical_readback.L5X',
                    'prepared_readback.L5X', 'genealogy_current.ACD', 'echo_before_redownload.ACD',
                    'echo_before_redownload.L5X', 'downloaded_current.L5X')]
DEST.mkdir(exist_ok=False)
for n in files:
    shutil.copy2(WORK/n, DEST/Path(n).name)
artifacts = [dict(path=p.name, sha256=sha(p.read_bytes()), bytes=p.stat().st_size)
             for p in sorted(DEST.iterdir()) if p.is_file()]
manifest = dict(schema='fraktal.ab.echo-redownload-evidence', version=1,
    sourceCommit='a1163c7c7bec21988167bc971145b1366206e9ce',
    authorization=dict(ownerRequest='can you check if the port is complete and then download it to the logix echo simulator?',
        acceptanceAnswer='Restore + 31 checks', target='local Echo 601FC87B', faultClearPerformed=False,
        physicalControllerAuthorized=False),
    declaration='fraktal_ab_genealogy_demo', manifestHash='6DEC4C1DC2F7F78A', configRevision=7203916,
    sourceL5xSha256=sha(source), preparedAcdSha256=(WORK/'prepared.sha256').read_text().strip(),
    backupAcdSha256=(WORK/'backup.sha256').read_text().strip(),
    validation=dict(abTests=1890, rootConsistencyTests=35, rootToolTests=83, compilerTargets=2,
        executableBodies=42, authoredInitialValues=21926, sfcSteps=21, liveRows=31, genealogyRows=21,
        configurationRestored=True, policyRestored=True, finalChecksPassed=True),
    nativeArtifactsArchived=False, nativeArtifactReferences=native, artifacts=artifacts)
(DEST/'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(dest=str(DEST), files=len(artifacts))))
