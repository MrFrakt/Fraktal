"""Disposable text-resource confirmation fixture, derived from the numeric one."""
from dataclasses import replace

import fraktal_ab_declaration as decl
import fraktal_ab_resource_demo as resource
import fraktal_ab_document_revision as document_revision

SUBJECT = 'Fixture.ConfirmedLotLabel'
VALUE = 'LOT-2026-10-18.A / press "A" / $ / ]]> / end'


def application():
    base = resource.application()
    return replace(base, chains=tuple(replace(chain, steps=tuple(
        replace(step, resource_kind='MATERIAL_CHANGED', resource_subject=SUBJECT,
                resource_value=decl.ResourceText(literal=VALUE))
        if step.number == 230 else step for step in chain.steps))
        if chain.name == 'AUTO' else chain for chain in base.chains), config_predecessors=document_revision.recorded('fraktal_ab_text_resource_demo', '6F3F8CDA9A8F6B59'))


def generate(source, output):
    import fraktal_ab_generate as gen
    return gen.generate(application(), source, output)
