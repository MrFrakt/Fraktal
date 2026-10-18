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
  Input quality follows the validated link. Output values are local demands;
  their quality stays FALSE until an applied-output feedback profile exists.

The Core marks identity members OPC.UA.DA := 0, i.e. excluded from the cyclic
tree. The S7 Web API has no cyclic tree: the HMI classifies every Topology
leaf as on-demand (read only while the fieldbus view is open), so the Siemens
binding publishes identity read-only instead of re-serving it through the
configuration manifest. The commissioning force set-points and the force
capability stay private: forcing has no runtime path on this binding, and an
absent Forceable reads as FALSE, which renders no force affordance (10.5.1).
"""
from __future__ import annotations

import dataclasses
import re

from fraktal_tia_binding import Catalog, READONLY, literal, type_source

# Members that stay private on this binding (see the module docstring).
PRIVATE_MEMBERS = {'Forceable', 'ForceBool', 'ForceAnalog', 'ForcesEnabled'}
TYPES = ('ST_IoChannel', 'ST_BusNode', 'ST_FieldbusTopology')
DIRECTIONS = ('INPUT', 'OUTPUT')
IDENT = re.compile(r'[A-Za-z_]\w*')


def resolve_types(catalog: Catalog, nodes: int, channels: int) -> dict:
    """The three Core types with arrays sized to this station."""
    sized = dataclasses.replace(catalog, capacities={
        **catalog.capacities, 'MAX_BUS_NODES': nodes, 'MAX_NODE_CHANNELS': channels})
    resolved = sized.resolve(['ST_FieldbusTopology'])
    for fields in resolved.values():
        for field in fields:
            field['accessible'] = field['member'] not in PRIVATE_MEMBERS
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
    if spec['healthy'] not in image_members:
        raise ValueError('health bit is not a member of the I/O image: ' + spec['healthy'])
    if not spec['nodes']:
        raise ValueError('fieldbus declares no node')
    node_fields, channel_fields = types['ST_BusNode'], types['ST_IoChannel']
    paths = set()
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
            module = channel.get('module', root)
            if module != root and module not in modules:
                raise ValueError('channel %s: unknown owning module %s' % (channel['tag'], module))
            path = node['name'] + '/' + channel['tag']
            if path in paths:
                raise ValueError('duplicate channel path ' + path)
            paths.add(path)


def sources(catalog: Catalog, spec: dict, image_members: set, root: str, modules: set) -> dict:
    """Source files keyed by import-ordered file name."""
    nodes = spec['nodes']
    channels = max(1, max(len(n.get('channels', [])) for n in nodes))
    types = resolve_types(catalog, len(nodes), channels)
    validate(spec, image_members, root, modules, types)
    enums = catalog.enums
    files = {'06_0_ST_IoChannel.udt': type_source('ST_IoChannel', types['ST_IoChannel']),
             '06_1_ST_BusNode.udt': type_source('ST_BusNode', types['ST_BusNode']),
             '06_2_ST_FieldbusTopology.udt': type_source('ST_FieldbusTopology', types['ST_FieldbusTopology'])}

    start = ['    Topology.NodeCount := %d;' % len(nodes),
             '    Topology.MappingValid := TRUE;']
    publish = []
    for n, node in enumerate(nodes, 1):
        prefix = 'Topology.Nodes[%d].' % n
        start += ['    %sName := %s;' % (prefix, literal(node['name'])),
                  '    %sDescriptionKey := %s;' % (prefix, literal(node.get('description_key', ''))),
                  '    %sTypeId := %s;' % (prefix, literal(node.get('type_id', ''))),
                  '    %sAddress := %s;' % (prefix, literal(node.get('address', ''))),
                  '    %sParentIdx := %d;' % (prefix, node.get('parent', 0)),
                  '    %sChannelCount := %d;' % (prefix, len(node.get('channels', [])))]
        live = '"%s".%s' % (spec['block'], prefix)
        publish += ['    %sLinkOk := #Healthy;' % live, '    %sState := #State;' % live]
        for c, channel in enumerate(node.get('channels', []), 1):
            item = prefix + 'Channels[%d].' % c
            start += ['    %sName := %s;' % (item, literal(channel['tag'])),
                      '    %sDescriptionKey := %s;' % (item, literal(channel['description_key'])),
                      '    %sAddress := %s;' % (item, literal(channel['address'])),
                      "    %sPath := WSTRING#%s;" % (item, literal(node['name'] + '/' + channel['tag'])),
                      "    %sModulePath := WSTRING#%s;" % (item, literal(channel.get('module', root))),
                      '    %sDir := %d;' % (item, enums['E_ChannelDir'][channel['dir']]),
                      '    %sKind := %d;' % (item, enums['E_ChannelKind']['DIGITAL'])]
            live_item = '"%s".%s' % (spec['block'], item)
            if channel.get('source'):
                publish.append('    %sBoolValue := "%s".%s;' % (live_item, spec['image'], channel['source']))
            # This map observes the local command image for DQ, not the
            # physical endpoint's final applied outputs. The bridge protocol
            # returns DI only. Never present a demand as confirmed output I/O.
            quality = '#Healthy' if channel['dir'] == 'INPUT' else 'FALSE'
            publish.append('    %sQuality := %s;' % (live_item, quality))

    files['38_%s.db' % spec['block']] = '\n'.join([
        '// Core 10.5.1: identity is fixed at generation; the publisher writes live state.',
        'DATA_BLOCK "%s"' % spec['block'], "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN',
        'VAR', '    Topology%s : "ST_FieldbusTopology";' % READONLY, 'END_VAR', 'BEGIN',
        *start, 'END_DATA_BLOCK', ''])
    files['38_%s.scl' % spec['publisher']] = '\n'.join([
        'FUNCTION "%s" : Void' % spec['publisher'], "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
        'VAR_TEMP', '    Healthy : Bool;', '    State : DInt;', 'END_VAR', 'BEGIN',
        '    // Core 10.5.1: live values and link health only. An input without a',
        '    // healthy link is not a claim, so its quality follows the link.',
        '    #Healthy := "%s".%s;' % (spec['image'], spec['healthy']),
        '    #State := %d;' % enums['E_NodeState']['OFFLINE'],
        '    IF #Healthy THEN #State := %d; END_IF;' % enums['E_NodeState']['OPERATIONAL'],
        *publish, 'END_FUNCTION', ''])
    return files
