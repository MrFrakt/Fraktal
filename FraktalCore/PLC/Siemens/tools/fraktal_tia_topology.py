"""Core 10.5.1 fieldbus topology for a Fraktal/TIA station.

One declaration joins the station's approved I/O list (tag, terminal address,
description key) with the module that owns each signal. From it this module
emits, sized to the declared hardware rather than to the Core's TwinCAT
maxima (64 nodes x 16 channels would cost ~1.2 MB and ~20,000 Web API leaves):

* ST_IoChannel / ST_BusNode / ST_FieldbusTopology, derived from the TwinCAT
  Core DUTs through the shared catalog;
* one read-only block whose start values carry the activation-static identity
  (names, addresses, paths, owning modules, parent links, counts);
* one publish function that copies only live state each scan: channel values
  from the station's logical I/O image and link health from its health bit.
  Input quality follows the validated link: the station's health bit, or for
  a node bound to a PROFINET device, that device's state as the CPU reports it
  (DeviceStates, sampled per IO system). An output is its local demand with
  quality FALSE, unless the station declares applied-output feedback: then,
  while that feedback is valid, it is the state the I/O owner reports applied.

The Core marks identity members OPC.UA.DA := 0, i.e. excluded from the cyclic
tree. The S7 Web API has no cyclic tree: the HMI classifies every Topology
leaf as on-demand (read only while the fieldbus view is open), so the Siemens
binding publishes identity read-only instead of re-serving it through the
configuration manifest.

Output forcing (10.5.1) exists only when the declaration's OUTPUT_FORCING
engineering gate is active (Part IV 7). Otherwise no force code is generated,
the force capability and set-points stay private, and an absent Forceable reads
as FALSE, which renders no force affordance. When the gate is active, Forceable
is published TRUE on exactly the declared outputs, the owning root runs the
request and the per-scan permit, and the hardware driver applies held
set-points through one generated function where it writes physical outputs.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
import re

from fraktal_tia_binding import Catalog, PRIVATE, READONLY, literal, type_source

FORCING_TEMPLATE = Path(__file__).resolve().parents[1] / 'Framework/Core/output_forcing.scl.in'

# Members that stay private on this binding (see the module docstring).
PRIVATE_MEMBERS = {'Forceable', 'ForceBool', 'ForceAnalog', 'ForcesEnabled'}
TYPES = ('ST_IoChannel', 'ST_BusNode', 'ST_FieldbusTopology')
DIRECTIONS = ('INPUT', 'OUTPUT')
IDENT = re.compile(r'[A-Za-z_]\w*')
# A hardware system constant ("Local~PROFINET_IO-System", "IM_1~IODevice").
SYSTEM_CONSTANT = re.compile(r'[A-Za-z_][\w~\-]{0,124}')
# Part IV 10.5: device state is sampled per IO system, never per scan per device.
PN_SAMPLE_MS = 250
# DeviceStates modes (S7-1500): devices that are disabled, that exist, that report a problem.
PN_DISABLED, PN_EXISTING, PN_PROBLEM = 3, 4, 5


def resolve_types(catalog: Catalog, nodes: int, channels: int, forcing: bool = False) -> dict:
    """The three Core types with arrays sized to this station."""
    sized = dataclasses.replace(catalog, capacities={
        **catalog.capacities, 'MAX_BUS_NODES': nodes, 'MAX_NODE_CHANNELS': channels})
    resolved = sized.resolve(['ST_FieldbusTopology'])
    # The HMI reads only the capability; set-points and the permit stay private.
    private = PRIVATE_MEMBERS - {'Forceable'} if forcing else PRIVATE_MEMBERS
    for fields in resolved.values():
        for field in fields:
            field['accessible'] = field['member'] not in private
    return resolved


def _width(fields, member):
    native = next(f['native_type'] for f in fields if f['member'] == member)
    return int(re.search(r'\[(\d+)\]', native)[1])


def validate(spec: dict, image_members: set, root: str, modules: set, types: dict) -> None:
    """Refuse at generation time what would otherwise be a runtime mapping fault."""
    for key in ('block', 'publisher', 'image', 'healthy', 'nodes'):
        if key not in spec:
            raise ValueError('fieldbus declaration needs ' + key)
    for key in ('block', 'publisher', 'image', 'healthy'):
        if not IDENT.fullmatch(spec[key]):
            raise ValueError('fieldbus %s must be an identifier' % key)
    if type(spec.get('forcing', False)) is not bool:
        raise ValueError('fieldbus forcing is a build Boolean (the OUTPUT_FORCING gate)')
    if spec.get('forcing') and not IDENT.fullmatch(spec.get('apply', '')):
        raise ValueError('fieldbus forcing needs the apply function identifier')
    if spec['healthy'] not in image_members:
        raise ValueError('health bit is not a member of the I/O image: ' + spec['healthy'])
    feedback_healthy = spec.get('feedback_healthy')
    if feedback_healthy is not None and feedback_healthy not in image_members:
        raise ValueError('feedback health bit is not a member of the I/O image: %s' % feedback_healthy)
    if not spec['nodes']:
        raise ValueError('fieldbus declares no node')
    node_fields, channel_fields = types['ST_BusNode'], types['ST_IoChannel']
    paths = set()
    forced_sources = set()
    for index, node in enumerate(spec['nodes'], 1):
        parent = node.get('parent', 0)
        if not (type(parent) is int and 0 <= parent < index):
            raise ValueError('node %d: parent must be an earlier node or 0' % index)
        for member, key in (('Name', 'name'), ('DescriptionKey', 'description_key'),
                            ('TypeId', 'type_id'), ('Address', 'address')):
            value = node.get(key, '')
            if not value.isascii() or len(value) > _width(node_fields, member):
                raise ValueError('node %d: %s too long or not ASCII' % (index, key))
        if not node.get('name'):
            raise ValueError('node %d needs a name' % index)
        profinet = node.get('profinet')
        if profinet is not None and (not {'io_system', 'device'} <= set(profinet) <= {'io_system', 'device', 'module'} or not all(
                type(profinet[key]) is str and SYSTEM_CONSTANT.fullmatch(profinet[key]) for key in profinet)):
            raise ValueError('node %d: profinet names its io_system, device and optional module system constants' % index)
        for channel in node.get('channels', []):
            for member, key in (('Name', 'tag'), ('DescriptionKey', 'description_key'),
                                ('Address', 'address')):
                value = channel.get(key, '')
                if not value or not value.isascii() or len(value) > _width(channel_fields, member):
                    raise ValueError('channel %r: %s missing, too long or not ASCII' % (channel.get('tag'), key))
            if channel.get('dir') not in DIRECTIONS:
                raise ValueError('channel %s: dir must be INPUT or OUTPUT' % channel['tag'])
            source = channel.get('source')
            if source is not None and source not in image_members:
                raise ValueError('channel %s: %s is not a member of the I/O image' % (channel['tag'], source))
            if source is None and channel['dir'] == 'INPUT':
                raise ValueError('channel %s: an input needs its image member' % channel['tag'])
            forceable = channel.get('forceable', False)
            if type(forceable) is not bool:
                raise ValueError('channel %s: forceable is a Boolean' % channel['tag'])
            # Rule 2: outputs only, and only one the application actually drives.
            if forceable and (channel['dir'] != 'OUTPUT' or source is None):
                raise ValueError('channel %s: only a driven OUTPUT may be forceable' % channel['tag'])
            feedback = channel.get('feedback')
            if feedback is not None and (channel['dir'] != 'OUTPUT' or source is None
                                         or feedback_healthy is None or feedback not in image_members):
                raise ValueError('channel %s: feedback needs a driven OUTPUT, an image member and the feedback health bit' % channel['tag'])
            module = channel.get('module', root)
            if module != root and module not in modules:
                raise ValueError('channel %s: unknown owning module %s' % (channel['tag'], module))
            path = node['name'] + '/' + channel['tag']
            if path in paths:
                raise ValueError('duplicate channel path ' + path)
            paths.add(path)
            if forceable:
                # A force writes the image member; two forceable tags on one member
                # would force a terminal the operator did not name.
                if source in forced_sources:
                    raise ValueError('channel %s: forceable output shares image member %s' % (channel['tag'], source))
                forced_sources.add(source)


def sources(catalog: Catalog, spec: dict, image_members: set, root: str, modules: set) -> dict:
    """Source files keyed by import-ordered file name."""
    nodes = spec['nodes']
    channels = max(1, max(len(n.get('channels', [])) for n in nodes))
    forcing = spec.get('forcing', False)
    types = resolve_types(catalog, len(nodes), channels, forcing)
    validate(spec, image_members, root, modules, types)
    enums = catalog.enums
    files = {'06_0_ST_IoChannel.udt': type_source('ST_IoChannel', types['ST_IoChannel']),
             '06_1_ST_BusNode.udt': type_source('ST_BusNode', types['ST_BusNode']),
             '06_2_ST_FieldbusTopology.udt': type_source('ST_FieldbusTopology', types['ST_FieldbusTopology'])}

    start = ['    Topology.NodeCount := %d;' % len(nodes),
             '    Topology.MappingValid := TRUE;']
    publish = []
    applied = []
    for n, node in enumerate(nodes, 1):
        prefix = 'Topology.Nodes[%d].' % n
        start += ['    %sName := %s;' % (prefix, literal(node['name'])),
                  '    %sDescriptionKey := %s;' % (prefix, literal(node.get('description_key', ''))),
                  '    %sTypeId := %s;' % (prefix, literal(node.get('type_id', ''))),
                  '    %sAddress := %s;' % (prefix, literal(node.get('address', ''))),
                  '    %sParentIdx := %d;' % (prefix, node.get('parent', 0)),
                  '    %sChannelCount := %d;' % (prefix, len(node.get('channels', [])))]
        live = '"%s".%s' % (spec['block'], prefix)
        if node.get('profinet'):
            # The sampled device state owns this node's link; its inputs follow it.
            link = live + 'LinkOk'
        else:
            publish += ['    %sLinkOk := #Healthy;' % live, '    %sState := #State;' % live]
            link = '#Healthy'
        for c, channel in enumerate(node.get('channels', []), 1):
            item = prefix + 'Channels[%d].' % c
            start += ['    %sName := %s;' % (item, literal(channel['tag'])),
                      '    %sDescriptionKey := %s;' % (item, literal(channel['description_key'])),
                      '    %sAddress := %s;' % (item, literal(channel['address'])),
                      "    %sPath := WSTRING#%s;" % (item, literal(node['name'] + '/' + channel['tag'])),
                      "    %sModulePath := WSTRING#%s;" % (item, literal(channel.get('module', root))),
                      '    %sDir := %d;' % (item, enums['E_ChannelDir'][channel['dir']]),
                      '    %sKind := %d;' % (item, enums['E_ChannelKind']['DIGITAL'])]
            if forcing and channel.get('forceable'):
                start.append('    %sForceable := TRUE;' % item)
                applied.append(('"%s".%s' % (spec['block'], item), channel['source']))
            live_item = '"%s".%s' % (spec['block'], item)
            if channel.get('feedback'):
                # Applied state while the owner's report is valid; otherwise the
                # local demand, unconfirmed. A demand is never presented as applied.
                confirmed = '"%s".%s' % (spec['image'], spec['feedback_healthy'])
                publish += ['    IF %s THEN %sBoolValue := "%s".%s;' % (confirmed, live_item, spec['image'], channel['feedback']),
                            '    ELSE %sBoolValue := "%s".%s; END_IF;' % (live_item, spec['image'], channel['source']),
                            '    %sQuality := %s;' % (live_item, confirmed)]
                continue
            if channel.get('source'):
                publish.append('    %sBoolValue := "%s".%s;' % (live_item, spec['image'], channel['source']))
            # Without declared feedback a DQ is the local command image, not the
            # physical endpoint's applied output. Never present a demand as confirmed.
            quality = link if channel['dir'] == 'INPUT' else 'FALSE'
            publish.append('    %sQuality := %s;' % (live_item, quality))

    sample, temps, members = profinet_sample(spec['block'], nodes, enums['E_NodeState'])
    files['38_%s.db' % spec['block']] = '\n'.join([
        '// Core 10.5.1: identity is fixed at generation; the publisher writes live state.',
        'DATA_BLOCK "%s"' % spec['block'], "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN',
        'VAR', '    Topology%s : "ST_FieldbusTopology";' % READONLY, *members, 'END_VAR', 'BEGIN',
        *start, 'END_DATA_BLOCK', ''])
    files['38_%s.scl' % spec['publisher']] = '\n'.join([
        'FUNCTION "%s" : Void' % spec['publisher'], "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
        'VAR_TEMP', '    Healthy : Bool;', '    State : DInt;', *temps, 'END_VAR', 'BEGIN',
        '    // Core 10.5.1: live values and link health only. An input without a',
        '    // healthy link is not a claim, so its quality follows the link.',
        '    #Healthy := "%s".%s;' % (spec['image'], spec['healthy']),
        '    #State := %d;' % enums['E_NodeState']['OFFLINE'],
        '    IF #Healthy THEN #State := %d; END_IF;' % enums['E_NodeState']['OPERATIONAL'],
        *sample, *publish, 'END_FUNCTION', ''])
    if forcing:
        text = FORCING_TEMPLATE.read_text('ascii')
        for name, values in enums.items():
            for member, value in values.items():
                text = text.replace('@%s.%s@' % (name, member), str(value))
        files['16e_OutputForcing.scl'] = text.replace('@NODES@', str(len(nodes))).replace('@CHANNELS@', str(channels))
        lines = ['    IF NOT "%s".Topology.ForcesEnabled THEN RETURN; END_IF;' % spec['block']]
        lines += ['    IF %sForced THEN "%s".%s := %sForceBool; END_IF;' % (live, spec['image'], source, live)
                  for live, source in applied]
        files['38_%s.scl' % spec['apply']] = '\n'.join([
            'FUNCTION "%s" : Void' % spec['apply'], "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'BEGIN',
            '    // Core 10.5.1: the hardware driver calls this where it writes physical',
            '    // outputs. A held set-point replaces the application demand only while',
            '    // forcing is permitted, so the demand returns the moment the Unit can act.',
            *lines, 'END_FUNCTION', ''])
    return files


def profinet_sample(block: str, nodes: list, states: dict) -> tuple:
    """Node link and state from the CPU's own PROFINET view (Part IV 10.5).

    One DeviceStates read per mode per IO system, and one ModuleStates read per
    mode per device that has bound modules, at most every PN_SAMPLE_MS. Device
    numbers and slots come from the hardware identifiers (LOG2GEO), so the
    declaration names the hardware, never a number to keep in step with it. A
    module node is up only while its device is; its FAULT is its own problem.
    A read that fails is not a claim: the node is OFFLINE with no link."""
    bound = [(n, node['profinet']) for n, node in enumerate(nodes, 1) if node.get('profinet')]
    if not bound:
        return [], [], []
    modules = any('module' in p for _, p in bound)
    # The system type carries its instruction identity, as the native export writes it.
    temps = ['    PnOk : Bool;', '    PnRet : Int;', '    PnStation : Int;', '    PnUp : Bool;', '    PnFault : Bool;',
             "    PnGeo {InstructionName := 'GEOADDR'; LibVersion := '1.0'} : GEOADDR;",
             *['    Pn%s : Array[0..1023] of Bool;' % name for name in ('Existing', 'Disabled', 'Problem')]]
    if modules:
        temps += ['    PnModOk : Bool;', '    PnSlot : Int;',
                  *['    PnMod%s : Array[0..127] of Bool;' % name for name in ('Existing', 'Disabled', 'Problem')]]
    members = ['    PnSampled%s : Bool;' % PRIVATE, '    PnSampleMs%s : UDInt;' % PRIVATE]
    lines = ['    // Part IV 10.5: PROFINET device state, sampled per IO system - never per scan per device.',
             '    IF NOT "%s".PnSampled OR "FRK_Elapsed"(NewMs := "FRK_Clock".NowMs, OldMs := "%s".PnSampleMs) >= %d THEN' % (block, block, PN_SAMPLE_MS),
             '        "%s".PnSampled := TRUE;' % block, '        "%s".PnSampleMs := "FRK_Clock".NowMs;' % block]
    for system in dict.fromkeys(p['io_system'] for _, p in bound):
        lines += ['        #PnRet := DeviceStates(LADDR := "%s", MODE := %d, STATE := #PnExisting); #PnOk := #PnRet = 0;' % (system, PN_EXISTING),
                  '        #PnRet := DeviceStates(LADDR := "%s", MODE := %d, STATE := #PnDisabled); #PnOk := #PnOk AND #PnRet = 0;' % (system, PN_DISABLED),
                  '        #PnRet := DeviceStates(LADDR := "%s", MODE := %d, STATE := #PnProblem); #PnOk := #PnOk AND #PnRet = 0;' % (system, PN_PROBLEM)]
        for device in dict.fromkeys(p['device'] for _, p in bound if p['io_system'] == system):
            nodes_here = [(n, p) for n, p in bound if p['io_system'] == system and p['device'] == device]
            if any('module' in p for _, p in nodes_here):
                lines += ['        #PnRet := ModuleStates(LADDR := "%s", MODE := %d, STATE := #PnModExisting); #PnModOk := #PnRet = 0;' % (device, PN_EXISTING),
                          '        #PnRet := ModuleStates(LADDR := "%s", MODE := %d, STATE := #PnModDisabled); #PnModOk := #PnModOk AND #PnRet = 0;' % (device, PN_DISABLED),
                          '        #PnRet := ModuleStates(LADDR := "%s", MODE := %d, STATE := #PnModProblem); #PnModOk := #PnModOk AND #PnRet = 0;' % (device, PN_PROBLEM)]
            for n, profinet in nodes_here:
                live = '"%s".Topology.Nodes[%d].' % (block, n)
                lines += ['        #PnStation := 0;',
                          '        #PnRet := LOG2GEO(LADDR := "%s", GEOADDR := #PnGeo);' % device,
                          '        IF #PnRet = 0 AND #PnGeo.STATION >= 1 AND #PnGeo.STATION <= 1023 THEN #PnStation := UINT_TO_INT(#PnGeo.STATION); END_IF;',
                          '        #PnUp := #PnOk AND #PnStation > 0;',
                          '        IF #PnUp THEN #PnUp := #PnExisting[#PnStation] AND NOT #PnDisabled[#PnStation]; END_IF;',
                          '        #PnFault := #PnUp AND #PnProblem[#PnStation];']
                if 'module' in profinet:
                    lines += ['        #PnSlot := 0;',
                              '        #PnRet := LOG2GEO(LADDR := "%s", GEOADDR := #PnGeo);' % profinet['module'],
                              '        IF #PnRet = 0 AND #PnGeo.SLOT >= 1 AND #PnGeo.SLOT <= 127 THEN #PnSlot := UINT_TO_INT(#PnGeo.SLOT); END_IF;',
                              '        IF #PnUp THEN #PnUp := #PnModOk AND #PnSlot > 0; END_IF;',
                              '        IF #PnUp THEN #PnUp := #PnModExisting[#PnSlot] AND NOT #PnModDisabled[#PnSlot]; END_IF;',
                              '        #PnFault := #PnUp AND #PnModProblem[#PnSlot];']
                lines += ['        %sLinkOk := #PnUp;' % live,
                          '        IF NOT #PnUp THEN %sState := %d;' % (live, states['OFFLINE']),
                          '        ELSIF #PnFault THEN %sState := %d;' % (live, states['FAULT']),
                          '        ELSE %sState := %d; END_IF;' % (live, states['OPERATIONAL'])]
    lines.append('    END_IF;')
    return lines, temps, members


def unit_calls(spec: dict, catalog: Catalog) -> dict:
    """The owning root's two force lines: the mailbox request and the per-scan
    permit. Both act on the one flag the driver applies by (ForcesEnabled)."""
    if not spec.get('forcing'):
        return {}
    topology = '"%s".Topology' % spec['block']
    idle_manual = '#Unit.Mode = %d AND #Core.Exec = %d' % (catalog.enums['E_Mode']['MANUAL'], catalog.enums['E_ExecState']['READY'])
    return {'request': '    "FRK_ForceRequest"(Scope := #Status.Name, Unit := #Unit, Access := #Access, Response := #HmiResponse, Topology := %s);' % topology,
            'tick': '    "FRK_ForceTick"(Permit := %s, Scope := #Status.Name, Topology := %s, AlarmLog := #AlarmLog);' % (idle_manual, topology)}
