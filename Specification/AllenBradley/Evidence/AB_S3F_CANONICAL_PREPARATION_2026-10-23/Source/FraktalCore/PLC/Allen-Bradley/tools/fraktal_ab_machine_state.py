"""One Core 8.11 classification, consumed by gateway and generated logic."""
STATES = dict(PRODUCING=0, IDLE=1, BLOCKED=2, STARVED=3, DOWN=4, CHANGEOVER=5, STOPPED=6)
CHANGEOVER = 3
PRIORITIES = (('DOWN', ('error', 'blocking')), ('CHANGEOVER', ('changeover',)),
              ('BLOCKED', ('blocked',)), ('STARVED', ('starved',)),
              ('PRODUCING', ('running',)), ('STOPPED', ('aborted',)))


def wait_steps(app, time_class):
    return tuple((c.mode_ordinal, s.number) for c in app.chains for s in c.steps
                 if s.time_class == time_class)


def waits(app, unit):
    position = (unit.get('Mode'), unit.get('Step', 0))
    busy = not unit.get('Error') and bool(unit.get('Running'))
    return tuple(busy and position in wait_steps(app, kind)
                 for kind in ('WAIT_UPSTREAM', 'WAIT_DOWNSTREAM'))


def classify(app, unit, blocking):
    starved, blocked = waits(app, unit)
    values = dict(error=bool(unit['Error']), blocking=bool(blocking),
                  changeover=unit['Mode'] == CHANGEOVER, blocked=blocked,
                  starved=starved, running=bool(unit['Running']), aborted=bool(unit['Aborted']))
    return next((STATES[state] for state, terms in PRIORITIES if any(values[t] for t in terms)), STATES['IDLE'])


def logic(app, target, unit, alarm):
    def wait(kind):
        positions = ' OR '.join(f'(({unit}.Mode = {m}) AND ({unit}.Step = {s}))'
                                for m, s in wait_steps(app, kind)) or '0 = 1'
        return f'(({unit}.Error = 0) AND ({unit}.Running <> 0) AND ({positions}))'
    terms = dict(error=f'{unit}.Error <> 0', blocking=f'{alarm}.Blocking <> 0',
                 changeover=f'{unit}.Mode = {CHANGEOVER}', blocked=wait('WAIT_DOWNSTREAM'),
                 starved=wait('WAIT_UPSTREAM'), running=f'{unit}.Running <> 0',
                 aborted=f'{unit}.Aborted <> 0')
    result = []
    for index, (state, names) in enumerate(PRIORITIES):
        condition = ' OR '.join('('+terms[n]+')' for n in names)
        result += [f'{"IF" if index == 0 else "ELSIF"} {condition} THEN', f'{target} := {STATES[state]};']
    return result + ['ELSE', f'{target} := {STATES["IDLE"]};', 'END_IF;']
