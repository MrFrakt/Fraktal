"""Disposable v38 compiler/model fixture, derived from the press, never deployed.

Enables the new host ring and a clearly fictitious digital nameplate. This is
not a commissioned asset declaration and is not registered as a hardware leg.
"""
from dataclasses import replace

import fraktal_ab_declaration as decl
import fraktal_ab_press_echo38 as echo


def application():
    base = echo.application()
    chains = tuple(replace(chain,
        renditions=(decl.ST, decl.SFC, decl.LD) if chain.name == 'AUTO' else chain.renditions,
        steps=tuple(
        replace(step, nok_reason='Ctx.ReportedReason')
        if any(mark.split(':=')[0].strip() == 'Ctx.ScrapCount' for mark in step.marks)
        else step for step in chain.steps)) for chain in base.chains)
    return replace(base, chains=chains, host_event_capacity=8,
        nameplate=decl.Nameplate('Fraktal', "Offline fixture's $identity ]]> record", 'OFFLINE-ONLY',
            product_uri='urn:fraktal:offline:host-events', year='2026',
            hardware_version='test', firmware_version='38.011', software_version='1',
            documentation_url='https://github.com/MrFrakt/Fraktal'))


def generate(source, output):
    import fraktal_ab_generate as gen
    return gen.generate(application(), source, output)
