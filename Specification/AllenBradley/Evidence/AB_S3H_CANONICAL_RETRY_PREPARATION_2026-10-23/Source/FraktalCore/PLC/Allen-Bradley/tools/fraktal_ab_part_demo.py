"""Disposable v38 local-carrier fixture; not a commissioned asset or bench leg."""
from dataclasses import replace

import fraktal_ab_declaration as decl
import fraktal_ab_host_demo as host
import fraktal_ab_part as part


def application():
    base = host.application()
    chains = []
    for chain in base.chains:
        if chain.name != 'AUTO':
            chains.append(chain)
            continue
        steps = []
        for step in chain.steps:
            if step.number == 100:
                step = replace(step, on_advance=105)
            elif step.number == 130:
                step = replace(step, on_advance=145)
            elif step.number == 215:
                step = replace(step, marks=(), nok_reason=0, part_action='processed',
                               part_verdict=2, part_reason='Ctx.ReportedReason')
            elif step.number == 230:
                step = replace(step, part_action='record', part_record=1, part_value='Cfg.PressDwellMs', on_advance=231)
            elif step.number == 999:
                step = replace(step, part_action='processed', part_verdict=1,
                    marks=tuple(m for m in step.marks if not m.startswith('Ctx.GoodCount')))
            steps.append(step)
        steps += [decl.Step(105, 'receivePart', decl.MARK, part_action='receive', on_advance=110),
                  decl.Step(145, 'startPart', decl.MARK, part_action='start', on_advance=150),
                  decl.Step(231, 'recordPosition', decl.MARK, part_action='record', part_record=2,
                            part_value='PressRam.OutImm_Pos', on_advance=240)]
        chains.append(replace(chain, steps=tuple(sorted(steps, key=lambda s: s.number))))
    return replace(base, chains=tuple(chains), host_event_capacity=16,
        part_carrier=part.LocalCarrier('OFFLINE-PRESS', (
            part.Measurement('PressDwell', 's', 50, 10000, 300, scale=1000),
            part.Measurement('RamPosition', '%', 0, 100, 100)), result_capacity=4),
        reasons={**base.reasons, **part.REASONS})


def generate(source, output):
    import fraktal_ab_generate as gen
    return gen.generate(application(), source, output)
