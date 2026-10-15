"""Build the separate test-only frame boundary and independent runtime assertions."""
import argparse
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN


def prepare(out, frame_out):
    model = DECL.read(HERE.parent / 'Declaration/two_root_forest.json')
    manifest = GEN.generate(model, frame_out)
    out.mkdir(parents=True, exist_ok=False)
    for directory in (frame_out, HERE / 'Boundary'):
        for path in directory.iterdir():
            if path.suffix in ('.scl', '.udt', '.db'):
                if (out / path.name).exists() and path.name != '40_Main.scl':
                    raise ValueError('test boundary collides with a generated source: ' + path.name)
                shutil.copyfile(path, out / path.name)
    checks = []

    def check(expression):
        checks.append('    "FRK_FrameProbeAssert"(Passed := ' + expression + ');')

    check('"FRK_Registry".Count = %d' % len(model.instances))
    check('NOT "FRK_Registry".Fault')
    check('NOT "FRK_Registry".Rows[0].Valid')
    type_ids = manifest['type_ids']
    lookup = {t.name: t for t in model.types}
    for item in model.instances:
        parts = item.path.split('.')
        path = '"' + parts[0] + '"' + ''.join('.' + p for p in parts[1:])
        row = '"FRK_Registry".Rows[%d]' % item.index
        probe = '"GDB_FrameProbe".Rows[%d]' % item.index
        t = lookup[item.type_name]
        check(path + '.Status.Name = ' + GEN.literal(item.path))
        check(path + '.Status.ModuleType = %d' % model.core.tiers[t.tier])
        check(path + '.Core.RegIndex = %d' % item.index)
        check(row + '.Valid')
        check(row + '.Parent = %d' % item.parent_index)
        check(row + '.TypeId = %d' % type_ids[t.name])
        check(probe + '.InitCalls = 1')
        check(probe + '.InitOrder > ' + probe + '.BeginOrder')
        check(probe + '.BeginCalls = ' + probe + '.EndCalls')
        check(probe + '.CyclicCalls = "GDB_FrameProbe".Scans')
        check(probe + '.BeginCalls = ' + ('1' if t.tier == 'CONTROL_MODULE' else '"GDB_FrameProbe".Scans'))
        if item.parent_index:
            check(probe + '.BeginOrder > "GDB_FrameProbe".Rows[%d].InitOrder' % item.parent_index)
    for path, value in [('StationA.Cell.Clamp',42), ('StationA.Cell.Gate',43), ('StationB.Cell.Clamp',84), ('StationB.Cell.Gate',85)]:
        parts = path.split('.')
        native = '"' + parts[0] + '"' + ''.join('.' + p for p in parts[1:])
        check(native + '.OutImm.Sample = %d' % value)
    check('"GDB_FrameProbe".OverflowPassed')
    check('"GDB_FrameProbe".BadParentPassed')
    body = ['FUNCTION "FRK_FrameProbeVerify" : Void', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
            'BEGIN', '    IF "GDB_FrameProbe".Scans = 5 THEN', '        "FRK_FrameProbeInvalidRegistry"();', '    END_IF;',
            '    "GDB_FrameProbe".Checks := 0;', '    "GDB_FrameProbe".FailedChecks := 0;', *checks,
            '    "GDB_FrameProbe".Passed := "GDB_FrameProbe".FailedChecks = 0 AND "GDB_FrameProbe".Scans >= 5;',
            'END_FUNCTION', '']
    (out / '38_Assertions.scl').write_bytes('\n'.join(body).encode('ascii'))
    (out / 'probe_manifest.json').write_bytes((json.dumps({'checks':len(checks), 'test_entrypoint':'Boundary/40_Main.scl replaces generated entrypoint for input/verification only', 'scoped_to':'frame/registration integration; no lifecycle or Unit-mode acceptance'},indent=2)+'\n').encode('ascii'))
    print(json.dumps({'sources':len(list(out.glob('*.scl')))+len(list(out.glob('*.db')))+len(list(out.glob('*.udt'))),'checks':len(checks)}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path);p.add_argument('frames',type=Path)
    args=p.parse_args();prepare(args.out,args.frames)
