"""Emit the shared reference-1500 command kernel; no project lifecycle copies."""
import hashlib
import json
from pathlib import Path

from fraktal_tia_binding import Catalog, PRIVATE, REPO, type_source
from fraktal_tia_generate import db

TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/command_kernel.scl.in'


def build(unit_runtime=False, event_sink='', states=False, history=False, recovery=False):
    catalog = Catalog.read()
    fields = {
        'Named': 'Bool', 'Initialized': 'Bool', 'RegIndex': 'DInt', 'ParentIndex': 'DInt',
        'ModuleType': 'DInt', 'Exec': 'DInt', 'ExecPrev': 'Bool', 'AbortPrev': 'Bool',
        'Armed': 'Bool', 'Command': 'DInt',
        'CommandLabel': next(f['native_type'] for f in catalog.resolve(['ST_TimingRow'])['ST_TimingRow'] if f['member'] == 'Label'),
        'Dispatch': 'Bool', 'EvInit': 'Bool', 'EvCommandStart': 'Bool',
        'ReleasePending': 'Bool',
        'EvAbort': 'Bool', 'EvAbortInError': 'Bool', 'EvModeExit': 'Bool', 'EvModeChanged': 'Bool',
        'Step': 'DInt', 'HookResult': 'DInt', 'Held': 'Bool', 'HoldReq': 'Bool',
        'HoldReason': 'DInt', 'DiagTouched': 'Bool', 'TimingOpen': 'Bool',
        'StartMs': 'UDInt', 'LastNowMs': 'UDInt', 'DeltaMs': 'UDInt',
        'ActiveMs': 'UDInt', 'TimeoutMs': 'UDInt', 'Timing': '"ST_ModuleTiming"',
    }
    if unit_runtime:
        fields['FaultSlot'] = 'Int'
        fields['FaultHandled'] = 'Bool'
    sources = {'02_FRK_Core.udt': type_source('FRK_Core', [
        {'member': n, 'native_type': t, 'accessible': False, 'initial': ''} for n, t in fields.items()])}
    sources['03_FRK_Clock.db'] = db('FRK_Clock', [
        n + PRIVATE + ' : ' + t + ';' for n, t in
        [('Mem', 'LReal'), ('AccMs', 'LReal'), ('NowMs', 'UDInt')]])
    text = TEMPLATE.read_text(encoding='ascii')
    for enum in ('E_ExecState', 'E_Severity', 'E_Category', 'E_Reason'):
        for name, number in catalog.enums[enum].items():
            text = text.replace('@' + enum + '.' + name + '@', str(number))
    text = text.replace('@MAX_CMD_STATS@', str(catalog.capacities['MAX_CMD_STATS']))
    text = text.replace('@FAULT_HANDLED_RESET@', '    #Core.FaultHandled := FALSE;' if unit_runtime else '')
    rational = REPO / 'Specification/reason_rationalization.json'
    rules = json.loads(rational.read_text(encoding='utf-8'))['reasons']
    rows = []
    for name, rule in rules.items():
        if name in catalog.enums['E_Reason']:
            rows.append('        %d: #Diag.Severity := %d; #Diag.Category := %d;' % (
                catalog.enums['E_Reason'][name], catalog.enums['E_Severity'][rule['priority']],
                catalog.enums['E_Category'][rule['category']]))
    text = text.replace('@RATIONALIZATION@', '\n'.join(rows))
    if '@' in text:
        raise ValueError('unresolved command-kernel template token')
    sources['12_CommandKernel.scl'] = text
    if unit_runtime:
        from fraktal_tia_unit import build as build_unit
        unit_sources = build_unit(catalog,event_sink,history,recovery)
        sources.update(unit_sources)
    if states:
        from fraktal_tia_alarms import STATE, expand
        sources['12a_StateServices.scl'] = expand(STATE,catalog)
    inputs = {**catalog.inputs,
              rational.relative_to(REPO).as_posix(): hashlib.sha256(rational.read_bytes()).hexdigest(),
              TEMPLATE.relative_to(REPO).as_posix(): hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()}
    if unit_runtime:
        from fraktal_tia_unit import TEMPLATE as unit_template, ROUTING, CONFIG, DECISION
        inputs[unit_template.relative_to(REPO).as_posix()] = hashlib.sha256(unit_template.read_bytes()).hexdigest()
        inputs[ROUTING.relative_to(REPO).as_posix()] = hashlib.sha256(ROUTING.read_bytes()).hexdigest()
        inputs[CONFIG.relative_to(REPO).as_posix()] = hashlib.sha256(CONFIG.read_bytes()).hexdigest()
        inputs[DECISION.relative_to(REPO).as_posix()] = hashlib.sha256(DECISION.read_bytes()).hexdigest()
        from fraktal_tia_access import inputs as access_inputs
        inputs.update(access_inputs())
        from fraktal_tia_alarms import ALARM, HISTORY
        inputs[ALARM.relative_to(REPO).as_posix()] = hashlib.sha256(ALARM.read_bytes()).hexdigest()
        if history:inputs[HISTORY.relative_to(REPO).as_posix()] = hashlib.sha256(HISTORY.read_bytes()).hexdigest()
        if recovery:
            from fraktal_tia_alarms import RECOVERY, RECOVERY_POLICY
            for path in (RECOVERY,RECOVERY_POLICY):inputs[path.relative_to(REPO).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    if states:
        inputs[STATE.relative_to(REPO).as_posix()] = hashlib.sha256(STATE.read_bytes()).hexdigest()
    return sources, {'version': '0.1', 'authority_inputs': inputs}
