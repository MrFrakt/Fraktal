"""Disposable confirmed-component genealogy fixture, no device/carrier driver."""
from dataclasses import replace

import fraktal_ab_declaration as decl
import fraktal_ab_text_resource_demo as text

PARENTS = ('FIXTURE-BLANK-0001','FIXTURE-INSERT-0002')


def application():
    base = text.application()
    return replace(base,part_carrier=replace(base.part_carrier,genealogy_capacity=2),
        chains=tuple(replace(chain,steps=tuple(replace(step,
            part_parents=tuple(decl.AsciiSource(literal=value) for value in PARENTS))
            if step.number == 230 else step for step in chain.steps))
            if chain.name == 'AUTO' else chain for chain in base.chains))


def generate(source,output):
    import fraktal_ab_generate as gen
    return gen.generate(application(),source,output)
