"""Confirmed Core 11.6 resource events; no device control or remote command.

A MARK declares the actual confirmation boundary. Subject is bounded ASCII;
Value snapshots a signed DINT (e.g. tool/lot number), never a later live value.
Arbitrary textual values and device/carrier protocols are separate providers.
"""
import fraktal_ab_declaration as decl

KINDS = ('TOOL_CHANGED', 'MATERIAL_CHANGED')


def enabled(app):
    return any(step.resource_kind for chain in app.chains for step in chain.steps)


def scalar_operands(app):
    import fraktal_ab_generate as gen
    return ({'Cfg.' + m.name for m in app.records[0].members if not m.dimension}
            | {'Ctx.' + m.name for m in gen.unit_context_members(app) if not m.dimension}
            | {module.name + '.' + m.name for module in app.modules
               for m in gen.module_members(module) if not m.dimension})


def validate(app):
    findings = []
    operands = None
    for chain in app.chains:
        for step in chain.steps:
            if not step.resource_kind:
                if step.resource_subject or step.resource_value:
                    findings.append('Resource: subject/value require resource_kind')
                continue
            if not app.host_event_capacity:
                findings.append('Resource: confirmed events require an opted-in host ring')
            if step.action != decl.MARK or step.resource_kind not in KINDS:
                findings.append('Resource: use a MARK with a canonical resource kind')
            if (type(step.resource_subject) is not str or not 1 <= len(step.resource_subject) <= 63
                    or not step.resource_subject.isascii() or not step.resource_subject.isprintable()):
                findings.append('Resource: subject must be 1..63 printable ASCII bytes')
            if operands is None:
                operands = scalar_operands(app)
            if not (type(step.resource_value) is int and -2**31 <= step.resource_value < 2**31
                    or type(step.resource_value) is str and step.resource_value in operands):
                findings.append('Resource: value must be a signed DINT literal or exact declared scalar')
    return findings


def without(app):
    """Exact prior declaration with resource annotations omitted.

    Used for configuration revision compatibility, never execution. No wildcard
    revision is accepted and no editable value/schema is changed.
    """
    from dataclasses import replace
    return replace(app, chains=tuple(replace(chain, steps=tuple(
        replace(step, resource_kind='', resource_subject='', resource_value=0)
        if step.resource_kind else step for step in chain.steps)) for chain in app.chains))


def marks(app, step, names, *, ladder=False):
    """One generator for ST/SFC assignments and LD outputs; no project glue."""
    import fraktal_ab_host_events as host
    ring = 'HostEvents' if names.in_aoi else host.tag(app)
    data = step.resource_subject.encode('ascii').ljust(64, b'\0')
    result = [f'MOV({value},{ring}.PendingUid[{index}])' if ladder else
              f'{ring}.PendingUid[{index}] := {value};' for index, value in enumerate(data)]
    value = str(step.resource_value)
    for prefix, target in (('Cfg.', names.cfg + '.'), ('Ctx.', names.unit + '.')):
        if value.startswith(prefix):
            value = target + value[len(prefix):]
            break
    else:
        for module in app.modules:
            if value.startswith(module.name + '.'):
                value = names.module(module.name) + value[len(module.name):]
                break
    call = host.call(app, step.resource_kind, in_aoi=names.in_aoi, value=value)
    return [*result, call if ladder else call + ';']
