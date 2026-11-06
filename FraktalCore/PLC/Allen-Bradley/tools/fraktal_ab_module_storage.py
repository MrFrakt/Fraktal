"""C4: derive module storage from the emitted owners, before final emission.

The temporary rendering has C3's full parameters. Code references, never V5
metadata or initialization bytes, decide storage. The final rendering uses one
immutable plan for AOI definitions, instance initializers and V5 fields. A
private derived Application subclass carries that plan only inside generation;
station declarations gain no configuration switch or duplicated field list.
"""
from dataclasses import dataclass, fields
import re
import hashlib,json
import xml.etree.ElementTree as ET

import fraktal_ab_declaration as decl


@dataclass(frozen=True)
class _Planned(decl.Application):
    _storage: tuple = ()


def planned(app):
    return isinstance(app, _Planned)


def roles(app, mtype):
    return dict(dict(app._storage)[mtype.type_key]) if planned(app) else {}


def public_members(app, mtype, members):
    layout = roles(app, mtype)
    return tuple(m for m in members if not layout or layout[m.name] in ('Input', 'Output'))


def code(element):
    text = '\n'.join(n.text or '' for n in element.iter() if n.tag in ('Line', 'Text'))
    # Generated IEC strings escape apostrophes with $, and comments have no
    # semantic operands. Preserve separators so neighboring tokens cannot join.
    return re.sub(r"\(\*.*?\*\)|'(?:\$[\s\S]|[^'])*'", ' ', text, flags=re.S)


def uses(text, prefix, member):
    token = re.escape(prefix + '.' if prefix else '') + re.escape(member)
    return re.search(r'(?<![\w.:])' + token + r'(?!\w)', text, re.I) is not None


def writes(text, prefix, member):
    token = re.escape(prefix + '.' if prefix else '') + re.escape(member)
    target = r'(?<![\w.:])' + token + r'(?!\w)(?:\[[^]\n]*\])?'
    return (re.search(target + r'\s*:=', text, re.I) is not None or
            re.search(r'\b(?:OTE|OTL|OTU|RES|CLR)\s*\(\s*' + target, text, re.I) is not None or
            re.search(r'\b(?:COP|CPS|MOV|MOVE)\s*\([^,;]*,\s*' + target, text, re.I) is not None)


def derive(app, text):
    """Analyze all generated AOIs and program languages. Unknown whole-instance
    consumers fail closed rather than incorrectly hiding their required fields.
    """
    import fraktal_ab_generate as gen
    import fraktal_ab_collapse as collapse
    import fraktal_ab_library as library
    root = ET.fromstring('<Image>' + text + '</Image>')
    aois = list(root.iter('AddOnInstructionDefinition'))
    programs = list(root.iter('Program'))
    by_type = {mtype.type_key: gen.module_aoi_name(app, next(m for m in app.modules
                 if library.type_of(m) == mtype)) for mtype in library.types_used(app)}
    by_aoi = {a.get('Name'): a for a in aois}
    result = []
    for mtype in library.types_used(app):
        aoi_name = by_type[mtype.type_key]
        body = code(by_aoi[aoi_name])
        consumers = []
        instances = [m for m in app.modules if library.type_of(m) == mtype]
        for program in programs:
            for module in instances:
                consumers.append((code(program), f'FRK_{app.name}_Inst{module.name}'))
        for aoi in aois:
            for param in aoi.findall('./Parameters/Parameter'):
                if param.get('DataType') == aoi_name:
                    if param.get('Usage') != 'InOut':
                        raise ValueError('module instance consumer must be InOut')
                    consumers.append((code(aoi), param.get('Name')))
        for external, prefix in consumers:
            # Whole-instance values may be passed only to a declared AOI input
            # of this exact type. Every other appearance must name a member.
            remainder = external
            for callee in aois:
                parameters = [p for p in callee.findall('./Parameters/Parameter')
                              if p.get('Required') == 'true']
                # The AOI instance itself is the first argument. Required
                # parameters follow it in the call (EnableIn/Out are implicit).
                positions = [0] if callee.get('Name') == aoi_name else []
                positions += [i + 1 for i, p in enumerate(parameters) if p.get('DataType') == aoi_name]
                if not positions:
                    continue
                pattern = r'\b' + re.escape(callee.get('Name')) + r'\s*\(([^;()]*?)\)'
                def remove(match):
                    args = match.group(1).split(',')
                    for i in positions:
                        if i < len(args) and args[i].strip().lower() == prefix.lower():
                            args[i] = 'C4_VALIDATED_INSTANCE'
                    return callee.get('Name') + '(' + ','.join(args) + ')'
                remainder = re.sub(pattern, remove, remainder, flags=re.I)
            if re.search(r'(?<![\w.])' + re.escape(prefix) + r'(?![\w.]|\s*\.)', remainder, re.I):
                raise ValueError('unclassified whole module instance use: ' + prefix)
        members = gen.module_context_members(mtype, True)
        per_instance = [{m.name: m.initial for m in gen.module_initial_members(app, instance)}
                        for instance in instances]
        layout = []
        for member in members:
            own = uses(body, '', member.name)
            external = any(uses(c, p, member.name) for c, p in consumers)
            if not own and not external:
                role = 'Unused'
            elif external:
                role = ('Input' if any(writes(c, p, member.name) for c, p in consumers)
                        or not writes(body, '', member.name) else 'Output')
            elif any(values[member.name] != member.initial for values in per_instance):
                # A type-local default cannot carry an instance-specific value.
                role = 'Input'
            else:
                role = 'Local'
            layout.append((member.name, role))
        result.append((mtype.type_key, tuple(layout)))
    return tuple(result)


def bind(app, text):
    return _Planned(**{f.name: getattr(app, f.name) for f in fields(decl.Application)},
                    _storage=derive(app, text))


def report(app):
    return {key: dict(layout) for key, layout in app._storage} if planned(app) else {}


def application(app):
    """Build the internal emission context; the station's declaration is untouched."""
    if planned(app):
        return app
    import fraktal_ab_generate as gen
    import fraktal_ab_collapse as collapse
    import fraktal_ab_part as part
    probe = gen.aoi_definitions(app) + gen.programs(app)
    scoped = {gen.unit_aoi_name(app), *((part.service_name(app),) if app.part_carrier is not None else ())}
    probe = collapse.rename_contexts(collapse.rename_storage(probe, app, scoped), app)
    return bind(app, probe)


def module_suffix(app, mtype):
    """Different application-owned storage/leaf signatures cannot reuse an AOI name."""
    import fraktal_ab_collapse as collapse
    import fraktal_ab_generate as gen
    signature = (roles(app,mtype), collapse.leaf_type(app,mtype), gen.type_aoi_logic(mtype,app))
    return 'C4' + hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()[:8].upper()


def unit_name(app, base):
    import fraktal_ab_generate as gen
    signature = (base, gen.unit_parameters(app))
    suffix = '_C4' + hashlib.sha256(json.dumps(signature).encode()).hexdigest()[:8].upper()
    return base[:40-len(suffix)] + suffix
