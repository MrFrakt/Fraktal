"""Sources 11 and 12's preparation records into the C4a evidence, then fill the record's results."""
from pathlib import Path
import hashlib, json, re

S = Path('C:/work/fraktal-ab-s6-host-20261104/prepare')
E = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C4A_OFFLINE_2026-11-05')
G = E / 'Gates'
target = G / 'Prepare'
target.mkdir(parents=True)
archived, withheld = [], {}
for p in sorted(S.iterdir()):
    if not p.is_file() or not re.search(r'_1[12][._]', p.name):
        continue
    if p.suffix.lower() in ('.l5x', '.acd', '.bak') or p.name.lower().endswith('.acd.bak'):
        withheld[p.name] = hashlib.sha256(p.read_bytes()).hexdigest().upper()
        continue
    with (target / p.name).open('xb') as out:
        out.write(p.read_bytes())
    archived.append(p.name)
for helper in ('audit_access_06.py',):
    with (target / helper).open('xb') as out:
        out.write((S / helper).read_bytes())
    archived.append(helper)
with (target / 'withheld_artifacts.json').open('x', encoding='utf-8', newline='\n') as out:
    json.dump(dict(reason='No L5X, ACD or BAK is archived; each is recorded by SHA-256 only.', withheld=withheld),
              out, indent=2)
    out.write('\n')

summary = json.loads((G / 'gate_summary_02.json').read_text(encoding='utf-8'))
assert summary['passed'], summary
assert not (G / 'gate_summary_01.json').exists()
stopped = {p.stem[:-5]: json.loads(p.read_text(encoding='utf-8'))['exitCode']
           for p in sorted(G.glob('*_01_exit.json'))}
assert stopped == dict(bind_sources_01=0, dart_analyze_gateway_01=0, dart_test_gateway_01=0), stopped


def ran(label):
    text = (G / f'{label}.log').read_text(encoding='utf-8', errors='replace')
    m = re.findall(r'Ran (\d+) tests? in ([\d.]+)s', text)
    skipped = re.findall(r'OK \(skipped=(\d+)\)', text)
    return int(m[-1][0]), float(m[-1][1]), int(skipped[-1]) if skipped else 0


def dart(label):
    text = (G / f'{label}.log').read_text(encoding='utf-8', errors='replace')
    m = re.findall(r'\+(\d+)(?: ~(\d+))?: All tests passed', text)
    return int(m[-1][0]), int(m[-1][1] or 0)


focused, full, root = ran('focused_python_02'), ran('full_ab_02'), ran('root_02')
passed, skipped = dart('dart_test_gateway_02')
bindings = json.loads((G / 'source_bindings_02.json').read_text(encoding='utf-8'))
result = json.loads((G / 'full_ab_source_bindings_result_02.json').read_text(encoding='utf-8'))
p11 = json.loads((target / 'prepare_candidate_11.json').read_text(encoding='utf-8'))
prep = json.loads((target / 'prepare_candidate_12.json').read_text(encoding='utf-8'))
c11 = json.loads((target / 'capacity_auto_11.json').read_text(encoding='utf-8'))
cap = json.loads((target / 'capacity_auto_12.json').read_text(encoding='utf-8'))
t11 = json.loads((G / 'st_tokens_01.json').read_text(encoding='utf-8'))
tokens = json.loads((G / 'st_tokens_02.json').read_text(encoding='utf-8'))
skip = lambda n: f', {n} skipped' if n else ', none skipped'
h = lambda s: f'`{s[:8]}…{s[-4:]}`'
check11 = json.loads((G / 'c4a_routines_01.json').read_text(encoding='utf-8'))
check = json.loads((G / 'c4a_routines_02.json').read_text(encoding='utf-8'))
assert check11['passed'] and check['passed']
check = check['results']
cap10 = 2225812
text = f"""**Source 11, superseded.** Its preparation passed with all exits 0: genealogy
{h(p11['sourceSha256'])}, press {h(p11['pressSha256'])}, ACD {h(p11['acdSha256'])}, Capacity
{c11['UsedStandardBlocks']:,} blocks. Its code check (`Investigation/c4a_routines_01.py`,
`Gates/c4a_routines_01.json`) passed: against source 10, the only changes were the
frame block leaving `ScanCanonical` and, for the press, the fixture routine and its JSR
in the main routine. The check's first version assumed the frame was a routine of its
own; it failed on `ScanCanonical`, where the frame block lives, and was extended to
recognize exactly that block, and its first output was deleted. Its ST tokens are in
`Gates/st_tokens_01.json`. Gate run 01 (`Investigation/run_gates_01.py`) was stopped
after its first three gates had passed (the source binding, `dart analyze` and the
gateway's Dart tests) and while the focused Python suite was running, when the
placement defect above was found; `Gates/focused_python_01.log` is that partial log.
It wrote no summary.

**Source 12** (`Gates/Prepare/`, prepared in `C:/work/fraktal-ab-s6-host-20261104/prepare`), all exits 0:
- **Images:** genealogy collapse {h(prep['sourceSha256'])}, press collapse {h(prep['pressSha256'])}.
  The BOOL-operand gate is clean for both. The genealogy declares no fixture, so its
  image is source 11's {'unchanged' if prep['sourceSha256'] == p11['sourceSha256'] else 'CHANGED'}.
- **Legacy branch:** the V6.11 genealogy and the press candidate regenerate
  byte-identically to source 07 ({h(prep['legacy']['fraktal_ab_genealogy_s6_host_demo'])} and
  {h(prep['legacy']['fraktal_ab_press_canonical_echo38'])}).
- **Builds:** both collapsed images build, read back equivalent and pass the
  SDK log audit (the genealogy on both v38 targets, the press on Echo).
- **Access audit:** the genealogy's nested access audit passes on both targets
  (`audit_access_06`: `audit_access_05`, with its frame check guarded by
  whether the frame is enabled).
- **ACD and Capacity:** ACD {h(prep['acdSha256'])}, read-back equivalent. Capacity is
  {cap['UsedStandardBlocks']:,} of {cap['TotalBlocks']:,} blocks ({cap['DisplayedUsagePercent']}%), a verified fit:
  {cap10 - cap['UsedStandardBlocks']:,} blocks under source 10. That is the S3h frame and its copy block
  leaving, more than the capacity plan's 174-220 K estimate for the frame (a
  plus-or-minus 30% estimate, which this exceeds).
- **Scan-risk proxy** (`Gates/st_tokens_02.json`): the genealogy's ST tokens
  fall from {tokens['genealogy_10']['total']:,} to {tokens['genealogy_12']['total']:,}, and the press's from
  {tokens['press_10']['total']:,} to {tokens['press_12']['total']:,}. The press adds the fixture routine and
  loses the frame block.

**The code check** (`Investigation/c4a_routines_02.py`, `Gates/c4a_routines_02.json`)
compares every program routine and AOI of source 10 with source 12, token by token.
- **Genealogy:** {check[0]['routines'][0]} routines, only `ScanCanonical` changed: the frame block
  removed, and nothing gained.
- **Press:** one routine added, the fixture copy. `ScanCanonical` lost the frame
  block and gained one line, the copy's JSR, immediately before the generation's
  closing increment. The main routine is unchanged.
- **Both:** no other difference.

`Investigation/run_gates_02.py` (`Gates/gate_summary_02.json`), all exits 0:
- **Sources:** {len(bindings['files'])} files bound with their line endings.
- **Dart:** `dart analyze` is clean for the gateway, and its {passed} tests pass{skip(skipped)}.
- **Focused Python:** {focused[0]} tests with ResourceWarnings raised as errors{skip(focused[2])}.
  `test_fraktal_ab_fixture_observation` (8) covers:
  - validation;
  - the emitted copy, executed against random sources;
  - the structure being Read Only and outside the manifest;
  - the copy's place inside the generation window;
  - the frame's absence, and the genealogy's lack of a fixture.
- **Schema identity:** both collapse declarations hold their pre-collapse
  surfaces (34 declared changes for the genealogy, 36 for the press), every
  one used. The canonical tree is unchanged.
- **Full AB discovery:** {full[0]:,} tests in {full[1]:,.0f} s{skip(full[2])}. All {result['files']} tool
  sources are unchanged during the run.
- **Root and documents:** {root[0]} root tests pass, and the AB specification,
  frozen-contract and strict consistency gates are clean."""
record = E.with_suffix('.md')
t = record.read_bytes().decode('utf-8')
assert '\r' not in t and t.count('RESULTS') == 1
record.write_bytes(t.replace('RESULTS', text).encode('utf-8'))
print(len(archived), 'archived;', sorted(withheld))
print(text)
