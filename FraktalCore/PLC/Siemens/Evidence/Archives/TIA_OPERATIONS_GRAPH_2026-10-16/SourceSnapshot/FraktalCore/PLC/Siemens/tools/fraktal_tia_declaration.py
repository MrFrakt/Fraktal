"""Validate a reference-1500 module forest and derive its registration inventory.

This is the structural declaration model for Phase 2, not a runtime generator.
Child members belong to reusable types; roots instantiate those types. Identity
widths and tier ordinals come from the authoritative Core DUTs.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from fraktal_tia_types import enum_values, struct_fields
from tia_lint import CONTRACT, RESERVED

REPO = Path(__file__).resolve().parents[4]
CORE = REPO / "FraktalCore/PLC/TwinCAT/Framework/Fraktal_Core/DUTs"


class DeclarationError(ValueError):
    def __init__(self, rule: str, location: str, message: str):
        self.rule = rule
        super().__init__(f"{location}: {rule} {message}")


@dataclass(frozen=True)
class CoreFacts:
    name_width: int
    key_width: int
    tiers: dict[str, int]
    inputs: tuple[tuple[str, str], ...]
    command_label_width: int

    @classmethod
    def read(cls) -> CoreFacts:
        inputs = []

        def declaration(name):
            path = CORE / (name + ".TcDUT")
            data = path.read_bytes()
            inputs.append((path.relative_to(REPO).as_posix(), hashlib.sha256(data).hexdigest()))
            text = ET.fromstring(data).findtext(".//Declaration")
            if text is None:
                raise ValueError("Core DUT has no declaration: " + str(path))
            return text

        fields = dict(struct_fields(declaration("ST_ModuleStatus")))

        def string_width(name):
            match = re.fullmatch(r"\s*STRING\((\d+)\)\s*", fields[name], re.I)
            if match is None:
                raise ValueError("Core status string width is unsupported: " + name)
            return int(match[1])

        tiers = enum_values(declaration("E_ModuleType"))
        if tiers.pop("NONE") != 0:
            raise ValueError("Core's NONE tier no longer reserves zero")
        if set(tiers) != {"UNIT", "EQUIPMENT_MODULE", "CONTROL_MODULE"}:
            raise ValueError("Core tier vocabulary changed; declaration semantics require review")
        timing = dict(struct_fields(declaration('ST_TimingRow')))
        label = re.fullmatch(r'\s*STRING\((\d+)\)\s*', timing['Label'], re.I)
        if label is None:
            raise ValueError('Core command label width is unsupported')
        return cls(string_width("Name"), string_width("TypeKey"), tiers, tuple(inputs), int(label[1]))


@dataclass(frozen=True)
class Member:
    name: str
    type_name: str


@dataclass(frozen=True)
class ModuleType:
    name: str
    tier: str
    type_key: str
    children: tuple[Member, ...]
    contract: tuple[tuple[str, str], ...] = ()
    hal: str = ""
    capabilities: int = 0
    logic: tuple[tuple[str, str], ...] = ()
    commands: tuple[tuple[int, str], ...] = ()
    timeout: str = ""
    storage: str = ""
    unit_modes: tuple[str, ...] = ()
    unit_initial: str = ""
    unit_run: int = 0
    station_config: str = ""
    config: tuple[dict, ...] = ()
    sequence_view: tuple[int, ...] = ()
    production: object = None
    health: object = None
    tower: object = None
    run_styles: tuple = ()


@dataclass(frozen=True)
class Instance:
    index: int
    parent_index: int
    path: str
    local_name: str
    type_name: str


@dataclass(frozen=True)
class Declaration:
    registry_capacity: int
    types: tuple[ModuleType, ...]
    roots: tuple[Member, ...]
    instances: tuple[Instance, ...]
    core: CoreFacts
    records: tuple[tuple[str, str], ...] = ()
    event_sink: str = ""
    model_config: tuple[str, ...] = ()
    initial_model: str = ""
    config_set_capacity: int = 0
    alarm_history_scopes: tuple[str, ...] = ()
    alarm_recovery_scopes: tuple[str, ...] = ()
    alarm_delivery_scopes: tuple[str, ...] = ()
    alarm_delivery_capacity: int = 0
    alarm_delivery_stream: str = ''
    persistence_min_write_ms: int = 0
    persistence_queue_capacity: int = 0
    # (model, 'ParCfg.Member', SCL literal): the value an absent model record
    # starts from, instead of the record default (the TC3 recipe seeds).
    model_seeds: tuple[tuple[str, str, str], ...] = ()
    line: object = None
    nameplates: tuple = ()
    engineering_gates: tuple = ()

    def inventory(self):
        types = {item.name: item for item in self.types}
        return {
            "schema_version": 1,
            "target_family": "S7-1500",
            "registry_capacity": self.registry_capacity,
            "core_inputs": dict(self.core.inputs),
            "identity_width": self.core.name_width,
            "type_key_width": self.core.key_width,
            "types": [{"name": item.name, "tier": item.tier, "type_key": item.type_key,
                       "children": [{"name": child.name, "type": child.type_name}
                                    for child in item.children]} for item in self.types],
            "instances": [{"index": item.index, "parent_index": item.parent_index,
                           "path": item.path, "local_name": item.local_name,
                           "type": item.type_name, "module_type": self.core.tiers[types[item.type_name].tier]}
                          for item in self.instances],
        }


def object_fields(value, required, optional, location):
    if not isinstance(value, dict):
        raise DeclarationError("T-GEN", location, "expected an object")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        raise DeclarationError("T-GEN", location,
                               f"missing fields {sorted(missing)}; unknown fields {sorted(extra)}")


def items(value, location):
    if not isinstance(value, list):
        raise DeclarationError("T-GEN", location, "expected an array")
    return value


def identifier(value, location, *, block=False):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise DeclarationError("T-COLLIDE", location, "expected an ASCII identifier without a path separator")
    if value.casefold() in RESERVED:
        raise DeclarationError("T-COLLIDE", location, "reserved SCL identifier: " + value)
    if block and not value.startswith("FB_"):
        raise DeclarationError("T-COLLIDE", location, "module type must use the FB_ prefix")
    return value


def unique_named(values, location):
    names = [item.name.casefold() for item in values]
    if len(names) != len(set(names)):
        raise DeclarationError("T-COLLIDE", location, "names collide ignoring case")


def member(value, location):
    object_fields(value, ("name", "type"), (), location)
    return Member(identifier(value["name"], location + ".name"),
                  identifier(value["type"], location + ".type", block=True))


def validate(value, core=None):
    core = core or CoreFacts.read()
    object_fields(value, ("schema_version", "target_family", "registry_capacity", "types", "roots"), ("records", "event_sink", "model_config", "config_sets", "alarm_history", "alarm_recovery", "alarm_delivery", "persistence", "line", "nameplates", "engineering_gates"), "declaration")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        raise DeclarationError("T-GEN", "schema_version", "only declaration version1 is supported")
    if value["target_family"] != "S7-1500":
        raise DeclarationError("T-GEN", "target_family", "this model currently supports the reference S7-1500 only")
    capacity = value["registry_capacity"]
    if type(capacity) is not int or not 1 <= capacity <= 2147483647:
        raise DeclarationError("T-GEN", "registry_capacity", "expected a positive DInt capacity, excluding reserved row0")
    types = []
    # These names are already owned by the generated module interface/frame.
    frame_members = CONTRACT | {"execute", "abort", "command", "busy", "done", "error",
                                "aborted", "errorid", "timing", "core", "hal", "parentindex",
                                "startup", "instancepath", "held", "lifecycleactive",
                                "exec_ready", "module_cm", "module_tier", "latchedparcmd", "device",
                                "unit", "modepolicy", "access", "part", "history", "historyhead",
                                "modeactivepublished", "runningpublished", "stoppendingpublished",
                                "supportedmodespublished", "goodcount", "nokcount", "reworkcount", "nokreason",
                                "manualowned", "manconditions", "routematched", "manualmatched", "configcursor", "statetouched",
                                "stationcfg", "configstageparcfg", "configstagestationcfg", "configdefaultparcfg", "configdefaultstationcfg",
                                "configstaged", "configpersist", "modelid", "availablemodelcount", "availablemodels", "configrootindex", "configsets", "configsetcount", "configsetdocument", "configsetdocumentline", "configsetdocumentlines"}
    frame_members |= {n.casefold() for n in ('SequenceViewEnabled', 'SequenceStepCount', 'SequenceAnnotationCount',
        'Profiler', 'Starved', 'Blocked', 'CurrentStep', 'CurrentStepElapsed', 'CurrentStepTimedOut', 'SequenceSteps', 'ActiveSteps',
        'SequenceAnnotations', 'SequenceStepDef', 'SequenceViewBook', 'SequenceViewTouched', 'SequenceViewDepths', 'SequenceViewVisits')}
    from fraktal_tia_operations import published_types
    frame_members |= {'productionbook','productionchanged',*(n.casefold() for n in published_types(1,1))}
    frame_members |= {'nameplate','engineeringslots','systemhealth','healthbook','healthconfig','signaltower','towerbook','towerconfig','runstyle','supportedrunstylespublished'}
    if value.get('line') is not None:
        frame_members |= {'line', 'linerevisionseen'}
    for index, data in enumerate(items(value["types"], "types")):
        location = f"types[{index}]"
        object_fields(data, ("name", "tier", "children"), ("type_key", "contract", "hal", "capabilities", "logic", "commands", "timeout", "storage", "unit", "station_config", "config", "sequence_view", "production", "health", "signal_tower"), location)
        name = identifier(data["name"], location + ".name", block=True)
        tier = data["tier"]
        if not isinstance(tier, str) or tier not in core.tiers:
            raise DeclarationError("T-TIER", location + ".tier", "unknown module tier")
        key = data.get("type_key", "")
        if not isinstance(key, str) or not key.isascii():
            raise DeclarationError("T-ASCII", location + ".type_key", "type key must be ASCII")
        if len(key) > core.key_width:
            raise DeclarationError("T-WIDTH", location + ".type_key", "type key exceeds Core status width")
        children = tuple(member(child, f"{location}.children[{position}]")
                         for position, child in enumerate(items(data["children"], location + ".children")))
        unique_named(children, location + ".children")
        if any(child.name.casefold() in frame_members for child in children):
            raise DeclarationError("T-COLLIDE", location + ".children", "child collides with the generated module frame")
        if tier == "CONTROL_MODULE" and children:
            raise DeclarationError("T-TIER", location, "a control module must be a leaf")
        contract = data.get("contract", {})
        if contract:
            object_fields(contract, ("ParCfg", "ParCmd", "OutCmd", "OutImm"), (), location + ".contract")
        elif not isinstance(contract, dict):
            raise DeclarationError("T-GEN", location, "contract must be an object")
        for role, record in contract.items():
            identifier(record, location + ".contract." + role)
            if not record.startswith("ST_"):
                raise DeclarationError("T-GEN", location, "contract records must use ST_ prefix")
        hal = data.get("hal", "")
        if hal:
            identifier(hal, location + ".hal")
            if tier != "CONTROL_MODULE" or not hal.startswith("ST_"):
                raise DeclarationError("T-IO", location, "only a CM declares a leaf HAL record")
        elif not isinstance(hal, str):
            raise DeclarationError("T-IO", location, "HAL must be a record name")
        capabilities = data.get("capabilities", 0)
        if type(capabilities) is not int or not 0 <= capabilities <= 4294967295:
            raise DeclarationError("T-GEN", location, "capabilities must fit DWord")
        logic = data.get("logic", {})
        object_fields(logic, (), ("cyclic", "Cyclic", "dispatch", "Init", "CommandStart", "Abort", "AbortInError", "ModeExit", "ModeChanged", "OperatorReset", "ManRelease", "Release", "Sequences"), location + ".logic")
        if tier == 'UNIT' and 'ManRelease' in logic:
            raise DeclarationError('T-TIER', location, 'function-specific manual release belongs to CM/EM commands')
        if tier != "UNIT" and any(n in logic for n in ('ModeExit', 'ModeChanged', 'OperatorReset', 'Release', 'Sequences')):
            raise DeclarationError("T-TIER", location, "mode reactions belong to Units")
        for region, body in logic.items():
            if not isinstance(body, str) or not body.isascii():
                raise DeclarationError("T-ASCII", location + ".logic." + region, "SCL regions must be ASCII")
        commands = []
        for row in items(data.get("commands", []), location + ".commands"):
            object_fields(row, ("id", "label"), (), location + ".commands")
            if type(row["id"]) is not int or not 1 <= row["id"] <= 2147483647:
                raise DeclarationError("T-GEN", location, "command id must be a positive DInt")
            if not isinstance(row["label"], str) or not row["label"].isascii() or not 1 <= len(row["label"]) <= core.command_label_width:
                raise DeclarationError("T-WIDTH", location, "command label must fit the Core timing-row width")
            commands.append((row["id"], row["label"]))
        if len({row[0] for row in commands}) != len(commands):
            raise DeclarationError("T-GEN", location, "duplicate command id")
        timeout = data.get("timeout", "")
        if bool(commands) != bool(timeout):
            raise DeclarationError("T-GEN", location, "commands and ParCfg timeout member must be declared together")
        if timeout:
            identifier(timeout, location + ".timeout")
        elif not isinstance(timeout, str):
            raise DeclarationError("T-GEN", location, "timeout must be a ParCfg member name")
        storage = data.get('storage', '')
        if storage:
            identifier(storage, location + '.storage')
            if not storage.startswith('ST_'):
                raise DeclarationError('T-GEN', location, 'private device storage must name an ST_ record')
        elif not isinstance(storage, str):
            raise DeclarationError('T-GEN', location, 'private storage must be a record name')
        unit = data.get('unit', {})
        object_fields(unit, (), ('modes', 'initial', 'run_command', 'run_styles'), location + '.unit')
        modes, initial, run = (), '', 0
        if unit:
            object_fields(unit, ('modes', 'initial', 'run_command'), ('run_styles',), location + '.unit')
            if tier != 'UNIT':
                raise DeclarationError('T-TIER', location, 'Unit runtime profile belongs only to Units')
            from fraktal_tia_binding import Catalog
            available = Catalog.read().enums['E_Mode']
            modes = tuple(items(unit['modes'], location + '.unit.modes'))
            if not modes or any(not isinstance(n, str) or n not in available for n in modes) or len(set(modes)) != len(modes):
                raise DeclarationError('T-GEN', location, 'Unit modes must be unique Core mode names')
            initial, run = unit['initial'], unit['run_command']
            if initial not in modes or type(run) is not int or run not in {n for n,label in commands}:
                raise DeclarationError('T-GEN', location, 'Unit initial mode/run command must be declared')
        station_config = data.get('station_config', '')
        if station_config:
            identifier(station_config, location + '.station_config')
            if not station_config.startswith('ST_'):
                raise DeclarationError('T-GEN', location, 'station config must name an ST_ record')
        elif not isinstance(station_config, str):
            raise DeclarationError('T-GEN', location, 'station config must name a record')
        config = tuple(items(data.get('config', []), location + '.config'))
        from fraktal_tia_config import validate_definition
        validate_definition(config, location)
        view = data.get('sequence_view', {})
        object_fields(view, (), ('capacity', 'branches', 'annotations'), location + '.sequence_view')
        view_sizes = ()
        if view:
            object_fields(view, ('capacity', 'branches', 'annotations'), (), location + '.sequence_view')
            from fraktal_tia_binding import Catalog
            bounds = Catalog.read().capacities
            limits = (bounds['MAX_SEQUENCE_STEPS'], bounds['MAX_PARALLEL_BRANCHES'], bounds['MAX_SEQUENCE_ANNOTATIONS'])
            view_sizes = tuple(view[n] for n in ('capacity', 'branches', 'annotations'))
            if not modes or any(type(n) is not int or not (0 if i == 1 else 1) <= n <= limits[i] for i, n in enumerate(view_sizes)):
                raise DeclarationError('T-GEN', location, 'sequence view requires a Unit profile and bounded Core capacities')
        production=None
        if 'production' in data:
            cfg=data['production']
            object_fields(cfg, ('ideal_cycle',), ('baseline','degradation_percent'), location+'.production')
            if not modes or not view_sizes or ('baseline' in cfg)!=('degradation_percent' in cfg):
                raise DeclarationError('T-GEN',location+'.production','production requires a profiled Unit and paired baseline/band members')
            if any(not isinstance(v,str) or not re.fullmatch(r'(?:ParCfg|StationCfg)\.[A-Za-z_][A-Za-z0-9_]*',v) for v in cfg.values()):
                raise DeclarationError('T-GEN',location+'.production','production settings bind scalar config members')
            production=tuple(cfg.items())
        health=None
        if 'health' in data:
            cfg=data['health']
            object_fields(cfg, (), ('max_task_cycle','max_task_jitter','require_time_sync'), location+'.health')
            if not modes or any(not isinstance(v,str) or not re.fullmatch(r'StationCfg\.[A-Za-z_][A-Za-z0-9_]*',v) for v in cfg.values()):
                raise DeclarationError('T-GEN',location+'.health','health thresholds require a Unit and registered station config members')
            health=tuple(cfg.items())
        tower=None
        if 'signal_tower' in data:
            cfg=data['signal_tower']
            object_fields(cfg, (), ('lamp_test_duration','operator_uses_white','horn_on_high'), location+'.signal_tower')
            if production is None or any(not isinstance(v,str) or not re.fullmatch(r'StationCfg\.[A-Za-z_][A-Za-z0-9_]*',v) for v in cfg.values()):
                raise DeclarationError('T-GEN',location+'.signal_tower','tower requires production summary and registered station config settings')
            tower=tuple(cfg.items())
        styles=unit.get('run_styles',{})
        if not isinstance(styles,dict) or set(styles)-set(modes):raise DeclarationError('T-GEN',location+'.unit.run_styles','run styles select declared modes')
        for mode,values in styles.items():
            if not isinstance(values,list) or not values or any(v not in ('CONTINUOUS','SINGLE_STEP','HOLD_TO_RUN') for v in values) or len(set(values))!=len(values) or 'CONTINUOUS' not in values or not view_sizes:
                raise DeclarationError('T-GEN',location+'.unit.run_styles','profiled modes select unique Core styles including CONTINUOUS')
        types.append(ModuleType(name, tier, key, children, tuple(contract.items()), hal, capabilities, tuple(logic.items()), tuple(commands), timeout, storage, modes, initial, run, station_config, config, view_sizes, production, health, tower,tuple((k,tuple(v)) for k,v in styles.items())))
    unique_named(types, "types")
    lookup = {item.name.casefold(): item for item in types}

    def referenced(item, location):
        found = lookup.get(item.type_name.casefold())
        if found is None:
            raise DeclarationError("T-TIER", location, "unknown child/root type: " + item.type_name)
        return found

    for item in types:
        for child in item.children:
            child_type = referenced(child, item.name + "." + child.name)
            if item.tier == "EQUIPMENT_MODULE" and child_type.tier == "UNIT":
                raise DeclarationError("T-TIER", item.name, "an equipment module cannot contain a Unit")
    roots = tuple(member(data, f"roots[{index}]") for index, data in enumerate(items(value["roots"], "roots")))
    if not roots:
        raise DeclarationError("T-TIER", "roots", "a forest needs at least one root Unit")
    unique_named(roots, "roots")
    if any(root.name.casefold() in lookup for root in roots):
        raise DeclarationError("T-COLLIDE", "roots", "instance DB name collides with a module FB block name")
    instances = []
    consumed = set()
    # Iterative traversal preserves parent-before-child registration and declared
    # call order; reject cycles before expanding another instance of that type.
    stack = [(root, 0, "", ()) for root in reversed(roots)]
    while stack:
        current, parent, prefix, ancestors = stack.pop()
        module = referenced(current, prefix or "roots")
        if parent == 0 and module.tier != "UNIT":
            raise DeclarationError("T-TIER", current.name, "each root must be a Unit")
        name = module.name.casefold()
        if name in ancestors:
            raise DeclarationError("T-TIER", current.name, "recursive multi-instance type cycle")
        path = prefix + "." + current.name if prefix else current.name
        if len(path) > core.name_width:
            raise DeclarationError("T-WIDTH", path, "qualified identity exceeds Core Status.Name width")
        if len(instances) >= capacity:
            raise DeclarationError("T-GEN", "registry_capacity", "module forest would overflow the registry")
        instance = Instance(len(instances) + 1, parent, path, current.name, module.name)
        instances.append(instance)
        consumed.add(name)
        stack.extend((child, instance.index, path, ancestors + (name,)) for child in reversed(module.children))
    unused = set(lookup) - consumed
    if unused:
        raise DeclarationError("T-GEN", "types", "unconsumed type declarations: " + ", ".join(sorted(unused)))
    records = value.get("records", {})
    if not isinstance(records, dict):
        raise DeclarationError("T-GEN", "records", "expected record declarations by name")
    names = set()
    for name, text in records.items():
        identifier(name, "records")
        if not name.startswith("ST_") or name.casefold() in names:
            raise DeclarationError("T-COLLIDE", "records", "record name/case collision")
        names.add(name.casefold())
        if not isinstance(text, str) or not text.isascii():
            raise DeclarationError("T-ASCII", name, "record declaration must be ASCII")
    event_sink = value.get('event_sink','')
    if event_sink:
        identifier(event_sink,'event_sink')
        if not event_sink.startswith('F_') or event_sink.casefold() in names | set(lookup) | {r.name.casefold() for r in roots}:
            raise DeclarationError('T-COLLIDE','event_sink','sink must name a separate F_ function with Ev : ST_AlarmEvent input')
    elif not isinstance(event_sink,str):
        raise DeclarationError('T-GEN','event_sink','sink must be a function name')
    model_config = value.get('model_config', {})
    object_fields(model_config, (), ('models', 'initial', 'seeds'), 'model_config')
    models, initial_model, seeds = (), '', ()
    if model_config:
        object_fields(model_config, ('models', 'initial'), ('seeds',), 'model_config')
        models = tuple(items(model_config['models'], 'model_config.models'))
        from fraktal_tia_config import width
        from fraktal_tia_binding import Catalog
        model_width = width(Catalog.read(), 'ST_ModelId', 'ModelCode')
        if not models or any(not isinstance(m, str) or not m.isascii() or not 1 <= len(m) <= model_width or any(ord(c) < 32 for c in m) for m in models) or len(set(models)) != len(models):
            raise DeclarationError('T-GEN', 'model_config', 'model codes must be unique bounded ASCII strings')
        initial_model = model_config['initial']
        if initial_model not in models:
            raise DeclarationError('T-GEN', 'model_config', 'initial model must be in the catalog')
        rows = []
        seeded = model_config.get('seeds', {})
        if not isinstance(seeded, dict):
            raise DeclarationError('T-GEN', 'model_config.seeds', 'seeds map a model to member values')
        for model, values in seeded.items():
            if model not in models or not isinstance(values, dict):
                raise DeclarationError('T-GEN', 'model_config.seeds', 'a seed names a catalog model and its member values')
            for seed_member, seed_value in values.items():
                if (not isinstance(seed_member, str) or not re.fullmatch(r'ParCfg\.[A-Za-z_]\w*', seed_member)
                        or not isinstance(seed_value, str) or not re.fullmatch(r'[A-Za-z0-9#_.+\-]{1,40}', seed_value)):
                    raise DeclarationError('T-GEN', 'model_config.seeds.' + model, 'a seed is ParCfg.<member> with an SCL literal')
                rows.append((model, seed_member, seed_value))
        seeds = tuple(rows)
    sets = value.get('config_sets', {})
    object_fields(sets, (), ('capacity',), 'config_sets')
    set_capacity = sets.get('capacity', 0)
    from fraktal_tia_binding import Catalog
    if type(set_capacity) is not int or not 0 <= set_capacity <= Catalog.read().capacities['MAX_CONFIG_SETS']:
        raise DeclarationError('T-WIDTH', 'config_sets', 'capacity must fit the Core named-set bound')
    history=value.get('alarm_history', {})
    object_fields(history, (), ('scopes',), 'alarm_history')
    scopes=history.get('scopes', [])
    units={i.path for i in instances if lookup[i.type_name.casefold()].unit_modes}
    if not isinstance(scopes,list) or any(not isinstance(n,str) or n not in units for n in scopes) or len(set(scopes)) != len(scopes):
        raise DeclarationError('T-GEN','alarm_history','scopes must name distinct deployed Units')
    recovery=value.get('alarm_recovery', {})
    object_fields(recovery, (), ('scopes',), 'alarm_recovery')
    recovery_scopes=recovery.get('scopes', [])
    if not isinstance(recovery_scopes,list) or any(not isinstance(n,str) or n not in scopes for n in recovery_scopes) or len(set(recovery_scopes)) != len(recovery_scopes):
        raise DeclarationError('T-GEN','alarm_recovery','scopes must name distinct history-selected Units')
    delivery=value.get('alarm_delivery', {})
    object_fields(delivery, (), ('scopes','capacity','stream_id'), 'alarm_delivery')
    delivery_scopes=delivery.get('scopes', [])
    delivery_capacity=delivery.get('capacity', 0)
    stream=delivery.get('stream_id', '')
    if delivery:
        object_fields(delivery, ('scopes','capacity','stream_id'), (), 'alarm_delivery')
        if not isinstance(delivery_scopes,list) or not delivery_scopes or any(not isinstance(n,str) or n not in scopes for n in delivery_scopes) or len(set(delivery_scopes)) != len(delivery_scopes):
            raise DeclarationError('T-GEN','alarm_delivery','scopes must name distinct history-selected Units')
        if type(delivery_capacity) is not int or not 1 <= delivery_capacity <= Catalog.read().capacities['MAX_ALARM_RING']:
            raise DeclarationError('T-WIDTH','alarm_delivery','capacity must fit the Core ring bound')
        import uuid
        try:
            if str(uuid.UUID(stream)) != stream: raise ValueError('noncanonical UUID')
        except (ValueError,TypeError,AttributeError):
            raise DeclarationError('T-GEN','alarm_delivery','stream_id must be a canonical deployment UUID')
    persistence=value.get('persistence', {})
    object_fields(persistence, (), ('medium','minimum_write_ms','queue_capacity'), 'persistence')
    minimum_write_ms=0; queue_capacity=0
    if persistence:
        object_fields(persistence, ('medium','minimum_write_ms'), ('queue_capacity',), 'persistence')
        minimum_write_ms=persistence['minimum_write_ms']
        queue_capacity=persistence.get('queue_capacity',Catalog.read().capacities['MAX_PERSIST_QUEUE'])
        if persistence['medium'] != 'LOAD_DB' or type(minimum_write_ms) is not int or not 1000 <= minimum_write_ms <= 86400000:
            raise DeclarationError('T-GEN','persistence','LOAD_DB requires a bounded write interval of at least 1000 ms')
        if type(queue_capacity) is not int or not 1 <= queue_capacity <= Catalog.read().capacities['MAX_PERSIST_QUEUE']:
            raise DeclarationError('T-WIDTH','persistence','queue capacity exceeds the Core bound')
        if not all(lookup[r.type_name.casefold()].unit_modes for r in roots) or not (any(t.config for t in types) or 'line' in value):
            raise DeclarationError('T-GEN','persistence','LOAD_DB requires runtime Units with registered config')
    line = None
    if 'line' in value:
        from fraktal_tia_line import Line
        line = Line.read(value['line'], [r.name for r in roots if lookup[r.type_name.casefold()].unit_modes])
        if not minimum_write_ms:
            raise DeclarationError('T-GEN', 'line', 'production line config requires LOAD_DB persistence')
        if line.role == 'MIRROR' and not line.source:
            raise DeclarationError('T-GEN', 'line', 'MIRROR needs a bound F_ image provider')
        if line.source and line.source.casefold() in {*(r.name.casefold() for r in roots), *lookup, *(n.casefold() for n in records), str(event_sink).casefold()}:
            raise DeclarationError('T-COLLIDE', 'line.source', 'provider collides with another project object')
    nameplates=value.get('nameplates',{})
    if not isinstance(nameplates,dict) or set(nameplates)-{i.path for i in instances}:
        raise DeclarationError('T-GEN','nameplates','identity metadata selects deployed canonical module paths')
    from fraktal_tia_binding import Catalog
    from fraktal_tia_config import width
    facts=Catalog.read();members={f['name'] for f in facts.records['ST_Nameplate']};uris=[]
    for path,data in nameplates.items():
        object_fields(data,(),members,'nameplates.'+path)
        for field_name,text in data.items():
            if not isinstance(text,str) or not text.isascii() or len(text)>width(facts,'ST_Nameplate',field_name) or any(ord(c)<32 for c in text):
                raise DeclarationError('T-WIDTH','nameplates.'+path,'identity field exceeds the Core physical bound')
        if data.get('ProductUri'):uris.append(data['ProductUri'])
    if len(uris)!=len(set(uris)):raise DeclarationError('T-GEN','nameplates','nonempty ProductUri identities must be unique')
    gates=items(value.get('engineering_gates',[]),'engineering_gates')
    if len(gates)>facts.capacities['MAX_ENGINEERING_GATES']:raise DeclarationError('T-WIDTH','engineering_gates','gate register exceeds Core capacity')
    names=[]
    for gate in gates:
        object_fields(gate,('name','description','active'),(),'engineering_gates')
        if type(gate['active']) is not bool:raise DeclarationError('T-GEN','engineering_gates','gate activity is a build Boolean, never a runtime operand')
        for key,field_name in [('name','Name'),('description','DescriptionKey')]:
            text=gate[key]
            if not isinstance(text,str) or not text.isascii() or not 1<=len(text)<=width(facts,'ST_EngineeringGate',field_name) or any(ord(c)<32 for c in text):
                raise DeclarationError('T-WIDTH','engineering_gates','gate identity exceeds its Core bound')
        names.append(gate['name'])
    if len(names)!=len(set(names)):raise DeclarationError('T-GEN','engineering_gates','gate names must be unique')
    return Declaration(capacity, tuple(types), roots, tuple(instances), core, tuple(records.items()),event_sink,models,initial_model,set_capacity,tuple(scopes),tuple(recovery_scopes),tuple(delivery_scopes),delivery_capacity,stream,minimum_write_ms,queue_capacity,seeds,line,
                       tuple((p,tuple(v.items())) for p,v in nameplates.items()),tuple(tuple(g.items()) for g in gates))


def unique_json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DeclarationError("T-GEN", "JSON", "duplicate object field: " + key)
        result[key] = value
    return result


def read(path):
    return validate(json.loads(Path(path).read_text(encoding="utf-8"), object_pairs_hook=unique_json_object))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("declaration", type=Path)
    parser.add_argument("--out", type=Path, help="write a new registration inventory; never overwrite")
    args = parser.parse_args()
    try:
        model = read(args.declaration)
        text = json.dumps(model.inventory(), indent=2, ensure_ascii=True) + "\n"
        if args.out:
            with args.out.open("x", encoding="ascii", newline="\n") as stream:
                stream.write(text)
        else:
            print(text, end="")
    except (DeclarationError, ValueError, OSError) as error:
        print(str(error))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
