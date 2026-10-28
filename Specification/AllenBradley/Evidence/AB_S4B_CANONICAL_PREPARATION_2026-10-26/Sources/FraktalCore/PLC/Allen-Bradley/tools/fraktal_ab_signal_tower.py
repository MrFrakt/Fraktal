"""Core 8.13 semantic outputs; native TONR owns elapsed time and timeout.

Startup site convention is declared once. No electrical channel, arbitrary
lamp write or parallel alarm/machine-state owner is introduced.
"""
from dataclasses import dataclass

import fraktal_ab_declaration as decl
import fraktal_ab_machine_state as machine

OUTPUTS = ('Red', 'Amber', 'Green', 'Blue', 'White', 'Horn', 'TestActive')


@dataclass(frozen=True)
class SignalTower:
    lamp_test_duration_ms: int = 3000
    operator_uses_white: bool = False
    horn_on_high: bool = True


def validate(app):
    cfg = app.signal_tower
    if cfg is None:
        return []
    if not isinstance(cfg, SignalTower):
        return ['signal tower requires a typed SignalTower convention']
    if (type(cfg.lamp_test_duration_ms) is not int or not -2**31 <= cfg.lamp_test_duration_ms < 2**31
            or type(cfg.operator_uses_white) is not bool or type(cfg.horn_on_high) is not bool):
        return ['signal tower requires DINT duration and Boolean site choices']
    if app.access_users is None:
        return ['signal tower requires the controller MANUAL access gate']
    return []


def tag(app, suffix=''):
    return f'FRK_{app.name}_SignalTower{suffix}'


def type_name():
    return 'FRK_T_SignalTowerV1'


def members():
    return (decl.scalar('SchemaVersion', initial=1), decl.scalar('MachineState', initial=machine.STATES['IDLE']),
            *(decl.boolean(n) for n in OUTPUTS))


def records(app):
    cfg = app.signal_tower
    return [decl.Record(type_name(), members()),
        decl.Record('FRK_T_SignalTowerCfgV1', (decl.scalar('SchemaVersion', initial=1),
            decl.scalar('LampTestDuration', initial=cfg.lamp_test_duration_ms),
            decl.boolean('OperatorUsesWhite', initial=int(cfg.operator_uses_white)),
            decl.boolean('HornOnHigh', initial=int(cfg.horn_on_high)))),
        decl.Record('FRK_T_SignalTowerBookV1', (decl.scalar('SchemaVersion', initial=1),
            *(decl.scalar(n) for n in ('Request', 'Index', 'AlarmActive', 'Highest', 'Duration'))))]


def tags(app):
    import fraktal_ab_generate as gen
    records_ = records(app)
    return [gen._structure_tag(tag(app, suffix), rec.name, rec.members,
                              external_access='Read Only' if suffix == '' else 'None')
            for suffix, rec in zip(('', 'Cfg', 'Book'), records_)] + [
        f'<Tag Name="{tag(app,"Timer")}" TagType="Base" DataType="FBD_TIMER" Constant="false" ExternalAccess="None"/>']


def dispatch(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_mailbox as mb
    return [f'{mb.LAMP_TEST}: (* LAMP_TEST: MANUAL gate has already run *)',
            f'IF (FRK_{app.name}_Unit.Running <> 0) OR ({tag(app)}.TestActive <> 0) THEN',
            *mb._refuse(app, gen.UNIT_NOT_READY_KEY), 'ELSE',
            *mb._accept(app, tag(app,'Book')+'.Request := 1;'), 'END_IF;']


def logic(app):
    import fraktal_ab_generate as gen
    status, book, cfg, timer = (tag(app,s) for s in ('','Book','Cfg','Timer'))
    unit, alarm = f'FRK_{app.name}_Unit', gen.alarm_active_tag(app)
    i = book+'.Index'
    result = machine.logic(app, status+'.MachineState', unit, alarm)
    result += [f'{book}.AlarmActive := 0;', f'{book}.Highest := 0;',
        f'FOR {i} := 0 TO {gen.ALARM_ACTIVE-1} DO',
        f'IF ({alarm}.ActState[{i}] <> 0) AND ({alarm}.ActShelved[{i}] = 0) THEN',
        f'{book}.AlarmActive := 1;', f'IF {alarm}.ActSeverity[{i}] > {book}.Highest THEN',
        f'{book}.Highest := {alarm}.ActSeverity[{i}];', 'END_IF;', 'END_IF;', 'END_FOR;',
        f'IF {book}.Request <> 0 THEN', f'{book}.Duration := {cfg}.LampTestDuration;',
        f'IF ({cfg}.SchemaVersion <> 1) OR ({book}.Duration <= 0) THEN', f'{book}.Duration := 3000;',
        f'ELSIF {book}.Duration > 30000 THEN', f'{book}.Duration := 30000;', 'END_IF;',
        f'{timer}.PRE := {book}.Duration;', f'{status}.TestActive := 1;', 'END_IF;',
        f'{timer}.Reset := ({book}.Request <> 0) OR ({status}.TestActive = 0);',
        f'{timer}.TimerEnable := {status}.TestActive <> 0;', f'TONR({timer});',
        f'{book}.Request := 0;', f'IF {timer}.DN THEN', f'{status}.TestActive := 0;', 'END_IF;']
    result += [f'{status}.{n} := 0;' for n in OUTPUTS if n != 'TestActive']
    result += [f'IF {status}.TestActive <> 0 THEN']
    result += [f'{status}.{n} := 1;' for n in OUTPUTS if n != 'TestActive']
    result += ['ELSE', f'CASE {status}.MachineState OF',
        f'{machine.STATES["DOWN"]}: {status}.Red := 1;',
        f'{machine.STATES["BLOCKED"]},{machine.STATES["STARVED"]},{machine.STATES["CHANGEOVER"]}: {status}.Amber := 1;',
        f'{machine.STATES["PRODUCING"]}: {status}.Green := 1;',
        f'{machine.STATES["IDLE"]},{machine.STATES["STOPPED"]}: ;',
        f'ELSE {status}.Red := 1;', 'END_CASE;', f'IF {book}.AlarmActive <> 0 THEN',
        f'CASE {book}.Highest OF', '2:', f'{status}.Red := 1;', f'{status}.Green := 0;',
        f'IF {cfg}.HornOnHigh <> 0 THEN {status}.Horn := 1; END_IF;',
        f'0,1: IF {status}.Red = 0 THEN {status}.Amber := 1; END_IF;',
        f'ELSE {status}.Red := 1; {status}.Green := 0;', 'END_CASE;', 'END_IF;',
        f'IF {unit}.DecisionId <> 0 THEN',
        f'IF {cfg}.OperatorUsesWhite <> 0 THEN {status}.White := 1; ELSE {status}.Blue := 1; END_IF;',
        'END_IF;', 'END_IF;']
    return result


def project(raw):
    if (not isinstance(raw,dict) or raw.get('SchemaVersion') != 1
            or type(raw.get('MachineState')) is not int or raw['MachineState'] not in machine.STATES.values()
            or any(type(raw.get(n)) is not int or raw[n] not in (0,1) for n in OUTPUTS)):
        raise ValueError('invalid or unavailable signal tower snapshot')
    return {'MachineState':raw['MachineState'],
            **{'SignalTower/'+n:bool(raw[n]) for n in OUTPUTS}}
