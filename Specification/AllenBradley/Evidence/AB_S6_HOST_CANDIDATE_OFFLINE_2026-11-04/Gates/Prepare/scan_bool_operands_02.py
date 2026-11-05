"""Whole-image BOOL-operand scan, to decide whether the rule can become a standing gate.

Runs the resolver of find_bool_operands_01 over every ST line (programs and
AOIs) of each image given and writes {image: [findings]} to the output. An
image the v38 compiler accepted must report none for the rule to be sound.
"""
import json, sys, time
from pathlib import Path

W = Path(__file__).parent
source = (W / 'find_bool_operands_01.py').read_text(encoding='utf-8').split('old_types, old_tags')[0]
ns = {'__name__': 'finder'}
sys.argv = ['finder', 'unused', 'unused']
exec(compile(source, 'find_bool_operands_01.py', 'exec'), ns)
output = Path(sys.argv_out) if False else W / 'bool_operand_scan_02.json'
images = ['v610_owner_01.L5X', 's6_host_02.L5X', 's6_host_01.L5X']
report = {}
for image in images:
    started = time.perf_counter()
    types, tags, routines, aois = ns['load'](str(W / image))
    hits, lines_seen = [], 0
    for name, lines in routines.items():
        for line in lines:
            lines_seen += 1
            found = ns['suspicious'](line, tags, types)
            if found:
                hits.append(dict(routine=name, line=line.strip()[:200], operands=found))
    for name, (scope, bodies) in aois.items():
        for rname, lines in bodies.items():
            merged = {**tags, **scope}
            for line in lines:
                lines_seen += 1
                found = ns['suspicious'](line, merged, types)
                if found:
                    hits.append(dict(routine=name + '/' + rname, line=line.strip()[:200], operands=found))
    report[image] = dict(lines=lines_seen, findings=hits, seconds=round(time.perf_counter() - started, 1))
    print(json.dumps({image: dict(lines=lines_seen, findings=len(hits))}), flush=True)
with output.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=1)
