"""The scan-risk proxy WP6.6 records: ST tokens per image, and where they run.

Counts the lexical tokens (comments and whitespace excluded) of every ST line
in each image, split into program routines and AOI bodies, with the tokenizer
the executed-ST model uses. That tokenizer also yields one end marker per
routine, which is counted: the same constant per ST routine in every image.
Ladder and SFC are not ST and are not counted.
Usage: st_tokens_01.py <output.json> <label=image.L5X>...
"""
import json, sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[5] / 'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_st_model as st


def count(path):
    root = ET.parse(path).getroot()
    out = dict(programs=0, aois=0)
    for kind, containers in (('programs', root.iter('Program')), ('aois', root.iter('AddOnInstructionDefinition'))):
        for container in containers:
            for routine in container.iter('Routine'):
                if routine.get('Type') == 'ST':
                    text = '\n'.join(l.text or '' for l in routine.iter('Line'))
                    out[kind] += len([t for t in st.tokenize(text) if t.kind not in ('comment', 'ws', 'end')])
    out['total'] = out['programs'] + out['aois']
    return out


output, images = Path(sys.argv[1]), dict(a.split('=', 1) for a in sys.argv[2:])
result = {label: count(path) for label, path in images.items()}
with output.open('x', encoding='utf-8', newline='\n') as f:
    json.dump(result, f, indent=2)
print(json.dumps(result))
