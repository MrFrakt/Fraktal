"""Shared guarded insertion for disposable offline L81E/v38 observers.

No deployment operations. Keep original code, initializers and task settings;
only new private storage and a final main-routine call may be added.
"""
import re
import xml.etree.ElementTree as ET

import fraktal_ab_generate as gen
from fraktal_ab_phase0_fixture import replace_once
import fraktal_ab_readback as readback


def augment(text, app, *, record, tags, routine, body):
    original = ET.fromstring(text)
    controller = original.find('Controller')
    if (controller.get('ProcessorType') != '1756-L81E'
            or controller.get('MajorRev') != '38' or app.io_modules):
        raise ValueError('observer requires the memory-only L81E/v38 fixture')
    additions = [ET.fromstring(record), *[ET.fromstring(tag) for tag in tags]]
    names = {routine, *(node.get('Name') for node in additions)}
    if len(names) != len(additions) + 1:
        raise ValueError('duplicate observer declaration')
    if any(element.get('Name') in names for element in original.iter()):
        raise ValueError('observer already present')
    tasks = controller.findall('Tasks/Task')
    if (len(tasks) != 1 or tasks[0].get('Name') != app.task_name
            or tasks[0].get('Type') != 'PERIODIC' or tasks[0].get('Rate') != '10'
            or tasks[0].get('InhibitTask') != 'false'
            or tasks[0].get('DisableUpdateOutputs') != 'true'):
        raise ValueError('observer requires the unchanged output-disabled 10 ms task')
    if [m.get('Name') for m in controller.findall('Modules/Module')] != ['Local']:
        raise ValueError('observer refuses configured external modules')
    programs = controller.findall('Programs/Program')
    if len(programs) != 1:
        raise ValueError('observer requires exactly one fixture Program')
    text = replace_once(text, '</DataTypes>', record + '\n</DataTypes>')
    index = text.index('</Tags>', text.index('</AddOnInstructionDefinitions>'))
    text = text[:index] + ''.join(tag + '\n' for tag in tags) + text[index:]
    program = programs[0]
    main = program.get('MainRoutineName')
    pattern = re.compile(rf'(<Routine Name="{re.escape(main)}" Type="ST">\s*<STContent>)(.*?)(</STContent>)', re.S)
    def append(match):
        lines = ET.fromstring('<STContent>' + match[2] + '</STContent>').findall('Line')
        return match[1] + match[2] + f'<Line Number="{len(lines)}"><![CDATA[JSR({routine},0);]]></Line>\n' + match[3]
    text, hits = pattern.subn(append, text)
    if hits != 1:
        raise ValueError('expected exactly one ST main routine')
    index = text.index('</Routines>', text.index('<Programs>'))
    text = text[:index] + gen.st_program_routine(routine, body) + '\n' + text[index:]
    updated = ET.fromstring(text)
    first, second = readback.executable(original), readback.executable(updated)
    key = (program.get('Name'), main)
    assert second.pop((program.get('Name'), routine)) == readback.normalized('\n'.join(body))
    assert second[key] == first[key] + readback.normalized(f'JSR({routine},0);')
    second[key] = first[key]
    assert second == first
    before, after = readback.initials(original), readback.initials(updated)
    assert all(after.get(key) == value for key, value in before.items())
    # Existing native alarm records are immutable too; only new tags may own new ones.
    old_alarms, new_alarms = readback.alarm_metadata(original), readback.alarm_metadata(updated)
    assert all(new_alarms.get(key) == value for key, value in old_alarms.items())
    return text


def sample(comm, tag, decode, attempts=20):
    """Read-only revision-bracketed acquisition shared by private observers."""
    for _ in range(attempts):
        before = comm.Read(tag + '.Revision')
        payload = comm.Read(tag)
        after = comm.Read(tag + '.Revision')
        if any(reply.Status != 'Success' for reply in (before, payload, after)):
            raise ValueError('native observer acquisition failed')
        try:
            record = decode(payload.Value)
        except ValueError as exc:
            if str(exc) != 'observer publication incomplete':
                raise
            continue
        if before.Value == record['Revision'] == after.Value:
            return record
    raise ValueError('native observer coherent snapshot unavailable')
