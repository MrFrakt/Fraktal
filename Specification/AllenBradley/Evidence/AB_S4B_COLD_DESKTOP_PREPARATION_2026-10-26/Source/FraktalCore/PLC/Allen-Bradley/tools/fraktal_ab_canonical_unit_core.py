"""S3a engineering: Unit core publication, from the owning declarations/contexts."""
from functools import lru_cache
from pathlib import Path
import re

import fraktal_ab_declaration as decl
import fraktal_ab_canonical_publication as publication

PREFIX = publication.PREFIX


@lru_cache
def core_limit(name):
    """Engineering source for the Core capacities cited by the approved D2 map."""
    path = Path(__file__).resolve().parents[2]/'TwinCAT/Framework/Fraktal_Core/Params/PL_Fraktal.TcGVL'
    hits = re.findall(r'\b'+re.escape(name)+r'\s*:\s*INT\s*:=\s*(\d+)\s*;', path.read_text(encoding='utf-8'))
    if len(hits) != 1:
        raise ValueError('Core capacity is missing or ambiguous: '+name)
    return int(hits[0])


def validate(app):
    modes = decl.declared_modes(app)
    findings = []
    if any(not 0 <= mode < core_limit('MODE_COUNT') for mode in modes):
        findings.append('canonical mode ordinal exceeds the Core policy capacity')
    for decision in app.decisions:
        if len(decision.prompt_key.encode('utf-8')) > 255 or any(len(key.encode('utf-8')) > 64 for key in decision.option_keys):
            findings.append('canonical decision text exceeds its Core-declared width')
        if len(decision.option_keys) > core_limit('MAX_OPTIONS'):
            findings.append('canonical decision options exceed Core capacity')
    for module in app.modules:
        if len(module.commands) > core_limit('MAX_CMD_CATALOG'):
            findings.append('canonical command catalog exceeds Core capacity')
        if any(len(('std.command.'+c.name.lower()).encode('utf-8')) > 120 for c in module.commands):
            findings.append('canonical command label exceeds Core-declared width')
    return findings


def leaf_type(module):
    return PREFIX+f"Leaf{'Typed' if module.type_key else ''}Commands{len(module.commands)}V61"


def augment(app, definitions):
    M, string = publication.Member, publication.string_type
    decision = [M('Default','DINT')]
    if app.decisions:
        decision += [M('Prompt',string(255)),
                     M('Options',string(64),count=core_limit('MAX_OPTIONS'),lower=1,
                       extent=max(len(d.option_keys) for d in app.decisions))]
    definitions[PREFIX+'DecisionV61'] = tuple(decision)
    definitions[PREFIX+'ModePolicyV61'] = (M('Shield','DINT','ENUM'),M('Style','DINT','ENUM'))
    if any(m.commands for m in app.modules):
        definitions[PREFIX+'CommandInfoV61'] = (M('Value','DINT'),M('Label',string(120)),M('Style','DINT','ENUM'))
    for module in app.modules:
        fields = [M('Status',publication.status_type(bool(module.type_key))),M('CatalogCount','DINT')]
        if module.commands:
            fields.append(M('Catalog',PREFIX+'CommandInfoV61',count=len(module.commands),lower=1))
        definitions[leaf_type(module)] = tuple(fields)
    root = publication.root_type(app)
    definitions[root] = tuple(M(m.name,leaf_type(next(x for x in app.modules if x.name == m.name)))
                              if m.name in {x.name for x in app.modules} else m for m in definitions[root])
    for typed in {bool(app.type_key),*(bool(m.type_key) for m in app.modules)}:
        definitions.pop(publication.leaf_type(typed),None)
    modes = decl.declared_modes(app)
    definitions[root] += (
        M('Decision',PREFIX+'DecisionV61'),
        M('ModePolicy',PREFIX+'ModePolicyV61',count=core_limit('MODE_COUNT'),indices=modes),
        M('SupportedModesPublished','BOOL','BOOL',count=((core_limit('MODE_COUNT')+31)//32)*32,extent=core_limit('MODE_COUNT'),indices=modes),
        M('SupportedRunStylesPublished','BOOL','BOOL',count=((len(decl.RUN_STYLES)+31)//32)*32,extent=len(decl.RUN_STYLES)),
    )
    if app.models:
        definitions[root] += (M('AvailableModelCount','DINT'),M('ModelCapacity','DINT'),
                              M('AvailableModels',PREFIX+'ModelV6',count=app.model_capacity or len(app.models),lower=1,
                                count_path=app.name+'/AvailableModelCount'))


def initialize(app, values):
    values['Decision'] = {}
    count = core_limit('MODE_COUNT')
    values['ModePolicy'] = [dict(Shield=0,Style=1) for _ in range(count)]
    values['SupportedModesPublished'] = [i in decl.declared_modes(app) for i in range(((count+31)//32)*32)]
    values['SupportedRunStylesPublished'] = [i in app.run_styles for i in range(((len(decl.RUN_STYLES)+31)//32)*32)]
    if app.models:
        values.update(AvailableModelCount=len(app.models),ModelCapacity=app.model_capacity,
                      AvailableModels=[dict(ModelCode=app.models[i].code) if i < len(app.models) else {}
                                       for i in range(app.model_capacity or len(app.models))])
    for module in app.modules:
        values[module.name].update(CatalogCount=len(module.commands),
                                   Catalog=[dict(Value=c.ordinal,Label='std.command.'+c.name.lower(),Style=0)
                                            for c in module.commands])


def put_text(target, text, width):
    raw = text.encode('utf-8')
    if len(raw) > width:
        raise ValueError('canonical literal exceeds its declared byte width')
    return [f'{target}.LEN := {len(raw)};'] + [f'{target}.DATA[{i}] := {v if v < 128 else v-256};' for i,v in enumerate(raw)]


def cyclic(app):
    import fraktal_ab_models as models
    root, unit = app.name, f'FRK_{app.name}_Unit'
    lines = [f'{root}.Decision.Default := {unit}.DecisionAnswer;']
    if app.decisions:
        previous = f'FRK_{app.name}_CanonicalDecisionId'
        lines += [f'IF {previous} <> {unit}.DecisionId THEN',f'{root}.Decision.Prompt.LEN := 0;']
        for i in range(core_limit('MAX_OPTIONS')):
            lines += [f'{root}.Decision.Options[{i}].LEN := 0;']
        for decision in app.decisions:
            lines += [f'IF {unit}.DecisionId = {decision.identifier} THEN']
            lines += put_text(root+'.Decision.Prompt',decision.prompt_key,255)
            for i,key in enumerate(decision.option_keys):
                lines += put_text(f'{root}.Decision.Options[{i}]',key,64)
            lines += ['END_IF;']
        lines += [f'{previous} := {unit}.DecisionId;','END_IF;']
    if app.models and app.model_capacity:
        catalog, width = models.tag(app), models.CODE_MAX
        index, byte_index = f'FRK_{app.name}_CanonicalModelIndex', f'FRK_{app.name}_CanonicalIndex'
        previous = f'FRK_{app.name}_CanonicalModelCount'
        # The owning catalog is append-only: existing codes/ordinals never
        # change. Rebuild its publication when Count changes, not every scan.
        lines += [f'IF ({catalog}.Count >= 0) AND ({catalog}.Count <= {app.model_capacity}) THEN',
                  f'{root}.AvailableModelCount := {catalog}.Count;',
                  f'IF {previous} <> {catalog}.Count THEN',
                  f'FOR {index} := 0 TO {catalog}.Count-1 DO',
                  f'{root}.AvailableModels[{index}].ModelCode.LEN := 0;',
                  f'IF ({catalog}.CodeLength[{index}] >= 1) AND ({catalog}.CodeLength[{index}] <= {width}) THEN',
                  f'{root}.AvailableModels[{index}].ModelCode.LEN := {catalog}.CodeLength[{index}];',
                  f'FOR {byte_index} := 0 TO {catalog}.CodeLength[{index}]-1 DO',
                  f'{root}.AvailableModels[{index}].ModelCode.DATA[{byte_index}] := {catalog}.CodeBytes[{index}*{width}+{byte_index}];',
                  'END_FOR;','ELSE',f'{publication.header_tag(app)}.Valid := 0;','END_IF;','END_FOR;',
                  f'IF {publication.header_tag(app)}.Valid THEN',f'{previous} := {catalog}.Count;','END_IF;','END_IF;',
                  'ELSE',f'{root}.AvailableModelCount := 0;',f'{publication.header_tag(app)}.Valid := 0;','END_IF;']
    return lines
