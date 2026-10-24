"""Disposable confirmed-resource fixture; fictitious tool/lot, no device driver."""
from dataclasses import replace
import fraktal_ab_tower_demo as tower


def application():
    base = tower.application()
    chains = []
    for chain in base.chains:
        if chain.name != 'AUTO':
            chains.append(chain)
            continue
        # Fictitious resource confirmations at existing successful boundaries;
        # no added chart rows, config fields, hardware action or per-scan glue.
        steps = tuple(replace(step, resource_kind='MATERIAL_CHANGED',
            resource_subject='Fixture.BlankLot', resource_value=20261018) if step.number == 105 else
            replace(step, resource_kind='TOOL_CHANGED', resource_subject='Fixture.UpperDie',
                    resource_value=314) if step.number == 145 else step for step in chain.steps)
        chains.append(replace(chain, steps=steps))
    return replace(base, chains=tuple(chains))


def generate(source, output):
    import fraktal_ab_generate as gen
    return gen.generate(application(), source, output)
