"""Confirmed Core 11.6 resource events; no device control or remote command.

A MARK declares the actual confirmation boundary. Subject is bounded ASCII;
Value snapshots a signed DINT or bounded ASCII text, never a later live value.
Device/carrier protocols remain separate providers.
"""
import fraktal_ab_declaration as decl

KINDS = ('TOOL_CHANGED', 'MATERIAL_CHANGED')
TEXT_LIMIT = 80
TEXT_WORDS = (TEXT_LIMIT + 4) // 4  # 80 bytes plus zero terminator and padding


def enabled(app):
    return any(step.resource_kind for chain in app.chains for step in chain.steps)


def text_enabled(app):
    return any(step.resource_kind and isinstance(step.resource_value, decl.ResourceText)
               for chain in app.chains for step in chain.steps)


def operand_members(app):
    import fraktal_ab_generate as gen
    return {**{'Cfg.' + m.name: m for m in app.records[0].members},
            **{'Ctx.' + m.name: m for m in gen.unit_context_members(app)},
            **{module.name + '.' + m.name: m for module in app.modules
               for m in gen.module_members(module)}}


def scalar_operands(app):
    return {name for name, member in operand_members(app).items() if not member.dimension}


def text_operands(app):
    return {name: member.dimension for name, member in operand_members(app).items()
            if 1 <= member.dimension <= TEXT_LIMIT + 1}


def value_identity(value):
    from dataclasses import asdict
    return asdict(value) if isinstance(value, decl.ResourceText) else value


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
            value = step.resource_value
            if isinstance(value, decl.ResourceText):
                literal_ok = (type(value.literal) is str and type(value.source) is str and value.source == ''
                              and len(value.literal) <= TEXT_LIMIT
                              and all(32 <= ord(char) <= 126 for char in value.literal))
                source_ok = (value.literal is None and type(value.source) is str
                             and value.source in text_operands(app))
                if not (literal_ok or source_ok):
                    findings.append('Resource: text needs exactly one 0..80 printable ASCII literal '
                                    'or exact declared ASCII array of 1..81 DINT cells')
            elif not (type(value) is int and -2**31 <= value < 2**31
                      or type(value) is str and value in operands):
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


def without_text(app):
    """Exact prior declaration omitting only text-valued confirmations."""
    from dataclasses import replace
    return replace(app, chains=tuple(replace(chain, steps=tuple(
        replace(step, resource_kind='', resource_subject='', resource_value=0)
        if isinstance(step.resource_value, decl.ResourceText) else step
        for step in chain.steps)) for chain in app.chains))


def operand(value, names, app):
    for prefix, target in (('Cfg.', names.cfg + '.'), ('Ctx.', names.unit + '.')):
        if value.startswith(prefix):
            return target + value[len(prefix):]
    for module in app.modules:
        if value.startswith(module.name + '.'):
            return names.module(module.name) + value[len(module.name):]
    return value


def marks(app, step, names, *, ladder=False):
    """One generator for ST/SFC assignments and LD outputs; no project glue."""
    import fraktal_ab_host_events as host
    ring = 'HostEvents' if names.in_aoi else host.tag(app)
    data = step.resource_subject.encode('ascii').ljust(64, b'\0')
    def assign(destination, value):
        return f'MOV({value},{ring}.{destination})' if ladder else f'{ring}.{destination} := {value};'
    result = [assign(f'PendingUid[{index}]', value) for index, value in enumerate(data)]
    text = step.resource_value if isinstance(step.resource_value, decl.ResourceText) else None
    if text_enabled(app):
        result.append(assign('PendingTextEnabled', int(text is not None)))
    if text is not None:
        if text.literal is not None:
            cells = list(text.literal.encode('ascii').ljust(TEXT_LIMIT + 1, b'\0'))
        else:
            width = text_operands(app)[text.source]
            source = operand(text.source, names, app)
            cells = [f'{source}[{index}]' if index < width else 0
                     for index in range(TEXT_LIMIT + 1)]
        result += [assign(f'PendingText[{index}]', value) for index, value in enumerate(cells)]
        value = '0'
    else:
        value = operand(str(step.resource_value), names, app)
    call = host.call(app, step.resource_kind, in_aoi=names.in_aoi, value=value)
    return [*result, call if ladder else call + ';']
