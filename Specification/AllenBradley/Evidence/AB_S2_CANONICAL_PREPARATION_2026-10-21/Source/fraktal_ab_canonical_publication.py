"""Opt-in S2 publication emitted from the existing application declaration.

Canonical records coexist with the legacy working contexts only during
migration. Identity is initialized in the PLC; cyclic state is published once
after the owning scan services. This module is engineering code, never a client.
"""
from __future__ import annotations

from dataclasses import dataclass
import xml.etree.ElementTree as ET

import fraktal_ab_canonical_manifest as wire

PREFIX = "FRK_T_Canonical"


@dataclass(frozen=True)
class Member:
    name: str
    kind: str
    logical: str = ""
    count: int = 0


def enabled(app):
    return app.canonical_publication_stage == wire.STAGE


def validate(app):
    stage = app.canonical_publication_stage
    if type(stage) is not int or stage not in (0, wire.STAGE):
        return ["canonical publication supports only disabled or the gated S2 slice"]
    if not stage:
        return []
    findings = []
    if app.major_revision < 37 or not app.controller.startswith(("1756-L8", "5069-L")):
        findings.append("canonical publication requires its v37+ 5380/5580 baseline")
    if app.name in app.sim_inputs or any(m.name in ("Status", "ModeActivePublished", "RunStyle", "Model", "CurrentStep") for m in app.modules):
        findings.append("canonical root/member collides with an existing symbol")
    return findings


def root_type(app):
    return f"FRK_T_{app.name}CanonicalRootV6"


def header_type(app):
    return f"FRK_T_{app.name}CanonicalManifestV6"


def header_tag(app):
    return f"FRK_{app.name}_CanonicalManifest"


def generation_tag(app):
    return f"FRK_{app.name}_CanonicalGeneration"


def begin_scan(app):
    tag = generation_tag(app)
    return [f'IF {tag} >= 2147483646 THEN {tag} := 0; END_IF;', f'{tag} := {tag} + 1;']


def string_type(width):
    return f"{PREFIX}String{width}V6"


def status_type(has_type):
    return f"{PREFIX}Status{'Typed' if has_type else ''}V6"


def leaf_type(has_type):
    return f"{PREFIX}Leaf{'Typed' if has_type else ''}V6"


def schema(app):
    """One member declaration owns UDT layout, initial values and field rows."""
    import fraktal_ab_models as models
    result = {}
    for typed in sorted({bool(app.type_key), *(bool(m.type_key) for m in app.modules)}):
        result[status_type(typed)] = (
            Member("Name", string_type(80)), Member("DisplayNameKey", string_type(160)),
            *((Member("TypeKey", string_type(160)),) if typed else ()),
            Member("ModuleType", "DINT", "ENUM"), Member("State", "DINT", "ENUM"),
            Member("FaultActive", "BOOL"),
        )
        result[leaf_type(typed)] = (Member("Status", status_type(typed)),)
    result[PREFIX+"CurrentStepV6"] = (Member("StepNo", "DINT"),)
    if app.models:
        # The existing application's model-catalog declaration owns this bound.
        # Preserve all accepted codes; never truncate a live catalog value.
        result[PREFIX+"ModelV6"] = (Member("ModelCode", string_type(models.CODE_MAX)),)
    result[root_type(app)] = (
        Member("Status", status_type(bool(app.type_key))),
        Member("ModeActivePublished", "DINT", "ENUM"), Member("RunStyle", "DINT", "ENUM"),
        Member("CurrentStep", PREFIX+"CurrentStepV6"),
        *((Member("Model", PREFIX+"ModelV6"),) if app.models else ()),
        *(Member(m.name, leaf_type(bool(m.type_key))) for m in app.modules),
    )
    result[PREFIX+"FieldV6"] = (
        Member("CanonicalPath", string_type(wire.PATH_WIDTH)),
        Member("LogicalType", string_type(16)), Member("EffectiveAccess", string_type(16)),
        Member("LowerBound", "DINT"), Member("ElementCount", "DINT"),
    )
    fields = field_rows(app, result)
    result[header_type(app)] = (
        *(Member(name, "DINT") for name in ("Magic", "SchemaMajor", "SchemaMinor", "PublicationStage")),
        Member("Valid", "BOOL"), Member("Truncated", "BOOL"),
        Member("ContentHash", string_type(80)), Member("ConfigRevision", "DINT"),
        Member("LegacyContentHash", string_type(80)),
        Member("FieldsCount", "DINT"), Member("FieldsCapacity", "DINT"),
        Member("Fields", PREFIX+"FieldV6", count=len(fields)),
    )
    result[PREFIX+"TimingV6"] = tuple(Member(name, "DINT") for name in
                                      ("Scan", "LastScanUs", "MaxScanUs", "OverlapCount"))
    return result


def field_rows(app, definitions=None):
    if definitions is None:
        definitions = schema(app)
    rows = []
    def walk(kind, path):
        for member in definitions[kind]:
            target = path+"/"+member.name
            if member.kind in definitions:
                walk(member.kind, target)
            else:
                rows.append(dict(CanonicalPath=target, LogicalType=member.logical,
                                 EffectiveAccess="Read Only", LowerBound=0, ElementCount=0))
    walk(root_type(app), app.name)
    return rows


def string_width(kind):
    return int(kind.removeprefix(PREFIX+"String").removesuffix("V6"))


def data_types(app):
    definitions = schema(app)
    widths = sorted({string_width(m.kind) for members in definitions.values() for m in members
                     if m.kind.startswith(PREFIX+"String")})
    out = []
    for width in widths:
        node = ET.Element("DataType", Name=string_type(width), Family="StringFamily", Class="User")
        members = ET.SubElement(node,"Members")
        for name, kind, count, radix in (("LEN","DINT",0,"Decimal"),("DATA","SINT",width,"ASCII")):
            ET.SubElement(members,"Member",Name=name,DataType=kind,Dimension=str(count),
                          Radix=radix,Hidden="false",ExternalAccess="Read Only")
        out.append(ET.tostring(node,encoding="unicode"))
    for kind, fields in definitions.items():
        node = ET.Element("DataType", Name=kind, Family="NoFamily", Class="User")
        members = ET.SubElement(node,"Members")
        for member in fields:
            ET.SubElement(members,"Member",Name=member.name,DataType=member.kind,
                          Dimension=str(member.count),Radix="Decimal" if member.kind in ("DINT","BOOL") else "NullType",
                          Hidden="false",ExternalAccess="Read Only")
        out.append(ET.tostring(node,encoding="unicode"))
    return out


def initial(app):
    import fraktal_ab_manifest as legacy
    rows = legacy.content(app)
    keys = {row["NumericKey"]:row["PortableKey"] for row in rows["Localization"]}
    result = {}
    for row, module in zip(rows["Modules"], [None,*app.modules], strict=True):
        identity = keys[row["CanonicalPathKey"]]
        values = dict(Name=identity,DisplayNameKey=keys[row["LocalNameKey"]],
                      ModuleType=1 if module is None else 3,State=0,FaultActive=False)
        type_key = app.type_key if module is None else module.type_key
        if type_key:
            values["TypeKey"] = type_key
        if module is None:
            result["Status"] = values
        else:
            result[module.name] = dict(Status=values)
    return result


def tags(app):
    import fraktal_ab_manifest as legacy
    definitions = schema(app)
    def members(kind, values):
        out = []
        for m in definitions[kind]:
            v = values.get(m.name, [] if m.count else {} if m.kind in definitions else "" if m.kind.startswith(PREFIX+"String") else 0)
            if m.count:
                if len(v) != m.count:
                    raise ValueError("canonical array initializer extent mismatch")
                elements = ''.join(f'<Element Index="[{i}]"><Structure DataType="{m.kind}">{members(m.kind,item)}</Structure></Element>' for i,item in enumerate(v))
                out.append(f'<ArrayMember Name="{m.name}" DataType="{m.kind}" Dimensions="{m.count}">{elements}</ArrayMember>')
            elif m.kind in definitions:
                out.append(f'<StructureMember Name="{m.name}" DataType="{m.kind}">{members(m.kind,v)}</StructureMember>')
            elif m.kind.startswith(PREFIX+"String"):
                # Native ASCII hex encodes UTF-8 bytes without CDATA splitting.
                out.append(legacy._string_member(m.name,m.kind,v.encode('utf-8').decode('latin-1'),string_width(m.kind)))
            else:
                out.append(f'<DataValueMember Name="{m.name}" DataType="{m.kind}" Radix="Decimal" Value="{int(v)}"/>')
        return ''.join(out)
    def tag(name,kind,values):
        return f'<Tag Name="{name}" TagType="Base" DataType="{kind}" Constant="false" ExternalAccess="Read Only"><Data Format="Decorated"><Structure DataType="{kind}">{members(kind,values)}</Structure></Data></Tag>'
    fields, old_hash = field_rows(app,definitions), legacy.content_hash(app)
    digest = wire.content_hash(fields,old_hash)
    header = dict(Magic=wire.MAGIC,SchemaMajor=wire.MAJOR,SchemaMinor=wire.MINOR,
                  PublicationStage=wire.STAGE,Valid=True,Truncated=False,ContentHash=digest,
                  ConfigRevision=wire.revision(digest),LegacyContentHash=old_hash,
                  FieldsCount=len(fields),FieldsCapacity=len(fields),Fields=fields)
    return [tag(app.name,root_type(app),initial(app)),tag(header_tag(app),header_type(app),header),
            f'<Tag Name="FRK_{app.name}_CanonicalIndex" TagType="Base" DataType="DINT" Radix="Decimal" ExternalAccess="None"/>',
            f'<Tag Name="{generation_tag(app)}" TagType="Base" DataType="DINT" Radix="Decimal" ExternalAccess="Read Only"/>',
            tag(f'FRK_{app.name}_CanonicalTiming',PREFIX+"TimingV6",{})]


def cyclic(app):
    import fraktal_ab_generate as gen
    import fraktal_ab_models as models
    root, unit = app.name, f'FRK_{app.name}_Unit'
    lines = [f'{header_tag(app)}.Valid := 1;',
             f'IF {unit}.Error <> 0 THEN',f'{root}.Status.State := {gen.STATE_ERROR};',
             f'ELSIF {unit}.Running <> 0 THEN',f'{root}.Status.State := {gen.STATE_BUSY};',
             f'ELSIF {unit}.Complete <> 0 THEN',f'{root}.Status.State := {gen.STATE_DONE};',
             'ELSE',f'{root}.Status.State := {gen.STATE_READY};','END_IF;',
             f'{root}.Status.FaultActive := {unit}.Error <> 0;',
             f'{root}.ModeActivePublished := {unit}.Mode;',
             f'{root}.RunStyle := '+(f'{unit}.RunStyle;' if gen.pacing(app) else '0;'),
             f'{root}.CurrentStep.StepNo := {unit}.Step;']
    for module in app.modules:
        ctx = gen.ctx_tag_for(app,module.name)
        lines += [f'{root}.{module.name}.Status.State := {ctx}.OutImm_ExecState;',
                  f'{root}.{module.name}.Status.FaultActive := {ctx}.Error <> 0;']
    if app.models:
        target, ordinal = f'{root}.Model.ModelCode',f'{unit}.ModelOrdinal'
        lines += [f'{target}.LEN := 0;']
        if app.model_capacity:
            catalog, width, index = models.tag(app), models.CODE_MAX, f'FRK_{app.name}_CanonicalIndex'
            source = f'{catalog}.CodeLength[{ordinal}-1]'
            lines += [f'IF {models.ordinal_guard(app,ordinal)} THEN',
                      f'IF ({source} >= 1) AND ({source} <= {width}) THEN',
                      f'{target}.LEN := {source};',f'FOR {index} := 0 TO {target}.LEN - 1 DO',
                      f'{target}.DATA[{index}] := {catalog}.CodeBytes[({ordinal}-1)*{width}+{index}];',
                      'END_FOR;','ELSE',f'{header_tag(app)}.Valid := 0;','END_IF;','END_IF;']
        else:
            for number, model in enumerate(app.models,1):
                raw = model.code.encode('utf-8')
                if len(raw)>models.CODE_MAX:
                    raise ValueError('canonical model code exceeds its declared byte capacity')
                lines += [f'IF {ordinal} = {number} THEN',f'{target}.LEN := {len(raw)};']
                lines += [f'{target}.DATA[{i}] := {v if v<128 else v-256};' for i,v in enumerate(raw)]
                lines += ['END_IF;']
    timing = f'FRK_{app.name}_CanonicalTiming'
    lines += [f'{timing}.Scan := FRK_{app.name}_ScanCount;',
              f'GSV(TASK,{app.task_name},LastScanTime,{timing}.LastScanUs);',
              f'GSV(TASK,{app.task_name},MaxScanTime,{timing}.MaxScanUs);',
              f'GSV(TASK,{app.task_name},OverlapCount,{timing}.OverlapCount);']
    lines += [f'{generation_tag(app)} := {generation_tag(app)} + 1;']
    return lines
