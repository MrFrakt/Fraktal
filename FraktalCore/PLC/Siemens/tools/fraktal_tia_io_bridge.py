"""Generate the small physical 1214C I/O bridge and matching press driver.

The I/O map is project-owned. One common endpoint owns TCP framing/liveness;
only the physical hardware driver accesses the raw tag table. No PUT/GET,
Fraktal command protocol, device lifecycle or process sequence is added here.
"""
import argparse
import binascii
from dataclasses import dataclass
import importlib.util
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import struct
import tempfile
import xml.etree.ElementTree as ET

from fraktal_tia_binding import PRIVATE, READONLY, type_source

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'Examples/PressIoBridge'
MAP = PROJECT / '00_System/io.json'
TEMPLATE = ROOT / 'Framework/IoBridge/bridge.scl.in'
INSTRUCTIONS = {'TSEND_C': '3.2', 'TRCV_C': '3.2', 'TCON_IP_v4': '1.0'}


def template_text():
    text = TEMPLATE.read_text(encoding='ascii')
    for instruction, version in INSTRUCTIONS.items():
        attributes = PRIVATE.replace('{', "{ InstructionName := '" + instruction + "'; LibVersion := '" + version + "';", 1)
        pattern = r'(@PRIVATE@)(\s*:\s*' + re.escape(instruction) + r';)'
        text, hits = re.subn(pattern, lambda m: attributes.strip() + m[2], text)
        if hits != (2 if instruction == 'TCON_IP_v4' else 1):
            raise ValueError('instruction declaration inventory changed: ' + instruction)
    return text.replace('@PRIVATE@', PRIVATE.strip())


@dataclass(frozen=True)
class Frame:
    """Independent PC peer for qualification of the PLC's byte protocol."""
    role: int
    epoch: int
    sequence: int
    echo_epoch: int = 0
    echo_sequence: int = 0
    signals: int = 0
    enabled: bool = False

    def encode(self):
        if self.role not in (1, 2) or not 1 <= self.epoch <= 0xffffffff or not 1 <= self.sequence <= 0xffffffff:
            raise ValueError('invalid frame identity')
        if not 0 <= self.signals <= (0x3fff if self.role == 1 else 0xff):
            raise ValueError('signals exceed this endpoint role')
        if type(self.enabled) is not bool:
            raise ValueError('enable must be Boolean')
        body = struct.pack('>4sBBBB5IBB', b'FRIO', 1, self.role, 0, 0,
                           self.epoch, self.sequence, self.echo_epoch, self.echo_sequence,
                           self.signals, int(self.enabled), 0)
        return body + struct.pack('>H', binascii.crc_hqx(body, 0xffff))

    @classmethod
    def decode(cls, data, expected_role):
        if len(data) != 32 or binascii.crc_hqx(data[:30], 0xffff) != int.from_bytes(data[30:], 'big'):
            raise ValueError('invalid frame length/checksum')
        magic, version, role, reserved1, reserved2, epoch, sequence, echo_epoch, echo_sequence, signals, enabled, reserved3 = struct.unpack('>4sBBBB5IBB', data[:30])
        if magic != b'FRIO' or version != 1 or role != expected_role or any((reserved1, reserved2, reserved3)) or enabled > 1:
            raise ValueError('invalid frame schema/role/flags')
        frame = cls(role, epoch, sequence, echo_epoch, echo_sequence, signals, bool(enabled))
        frame.encode()  # Apply the same public wire bounds to inbound frames.
        return frame


def read_map():
    value = json.loads(MAP.read_bytes())
    if value['schema_version'] != 1:
        raise ValueError('unsupported bridge I/O map')
    for name in ('physical_address', 'simulator_bench_address'):
        ipaddress.IPv4Address(value[name])
    if value['physical_address'] == value['simulator_bench_address']:
        raise ValueError('bridge endpoints require distinct addresses')
    if not 20 <= value['period_ms'] <= 100 or not 200 <= value['watchdog_ms'] <= 1000:
        raise ValueError('bridge timing outside qualified bounds')
    if not value['period_ms'] * 3 < value['watchdog_ms']:
        raise ValueError('watchdog must allow more than three transmissions')
    tags, addresses = set(), set()
    for name, count, address_pattern in [('inputs', 14, r'%I(?:0\.[0-7]|1\.[0-5])'), ('outputs', 8, r'%Q0\.[0-7]')]:
        if [row['bit'] for row in value[name]] != list(range(count)):
            raise ValueError('bridge signal bits must be contiguous and unique')
        for row in value[name]:
            if not re.fullmatch(r'_' + r'[A-Za-z0-9_]+', row['tag']):
                raise ValueError('invalid electrical tag')
            if not re.fullmatch(address_pattern, row['address']):
                raise ValueError('invalid onboard address')
            if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', row['signal']):
                raise ValueError('invalid logical I/O signal')
            if row['tag'] in tags or row['address'] in addresses:
                raise ValueError('duplicate raw I/O mapping')
            tags.add(row['tag']); addresses.add(row['address'])
    if len(value['inhibited_outputs']) != 2:
        raise ValueError('both Control On outputs must remain explicitly inhibited')
    for row in value['inhibited_outputs']:
        if row['address'] not in ('%Q1.0', '%Q1.1') or row['address'] in addresses or row['tag'] in tags:
            raise ValueError('invalid reserved Control On output')
        tags.add(row['tag']); addresses.add(row['address'])
    return value


def config_type():
    fields = [('SchemaVersion', 'UInt', '1'), ('InterfaceId', 'HW_ANY', '64'),
              ('SendId', 'CONN_OUC', '257'), ('ReceiveId', 'CONN_OUC', '258'),
              ('PeerAddress', 'Array[1..4] of Byte', ''), ('SendPort', 'UInt', ''),
              ('ReceivePort', 'UInt', ''), ('PeriodMs', 'UDInt', ''), ('WatchdogMs', 'UDInt', '')]
    return type_source('ST_IoBridgeConfig', [{'member': n, 'native_type': t, 'accessible': False, 'initial': v}
                                          for n, t, v in fields])


def config_lines(mapping, physical):
    peer = mapping['simulator_bench_address' if physical else 'physical_address']
    lines = ['    #Config.SchemaVersion := 1;', '    #Config.InterfaceId := 64;',
             '    #Config.SendId := 257;', '    #Config.ReceiveId := 258;']
    for slot, octet in enumerate(ipaddress.IPv4Address(peer).packed, 1):
        lines.append('    #Config.PeerAddress[%d] := %d;' % (slot, octet))
    lines += ['    #Config.%s := %d;' % (n, v) for n, v in (
        ('SendPort', mapping['simulator_receive_port' if physical else 'physical_receive_port']),
        ('ReceivePort', mapping['physical_receive_port' if physical else 'simulator_receive_port']),
        ('PeriodMs', mapping['period_ms']), ('WatchdogMs', mapping['watchdog_ms']))]
    return lines


def tags_xml(mapping):
    doc = ET.Element('Document')
    ET.SubElement(doc, 'Engineering', version='V20')
    table = ET.SubElement(doc, 'SW.Tags.PlcTagTable', ID='0')
    ET.SubElement(ET.SubElement(table, 'AttributeList'), 'Name').text = 'GVL_PressBridgeIO'
    objects = ET.SubElement(table, 'ObjectList')
    for index, row in enumerate(mapping['inputs'] + mapping['outputs'] + mapping['inhibited_outputs'], 1):
        attrs = ET.SubElement(ET.SubElement(objects, 'SW.Tags.PlcTag', ID=str(index), CompositionName='Tags'), 'AttributeList')
        for key, text in [('Name', row['tag']), ('DataTypeName', 'Bool'), ('LogicalAddress', row['address']),
                          ('ExternalAccessible', 'false'), ('ExternalVisible', 'false'), ('ExternalWritable', 'false')]:
            ET.SubElement(attrs, key).text = text
    ET.indent(doc)
    return ET.tostring(doc, encoding='unicode') + '\n'


def boot_store():
    return '\n'.join(['DATA_BLOCK "GDB_IoBridgeEpoch"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
                      'NON_RETAIN', 'VAR RETAIN', '    Epoch'+PRIVATE+' : UDInt;', 'END_VAR', 'BEGIN', 'END_DATA_BLOCK', ''])


def physical_driver(mapping):
    lines = ['FUNCTION_BLOCK "FB_PressIoBridgeHardwareDriver"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
             'VAR_INPUT', '    Startup'+PRIVATE+' : Bool;', 'END_VAR', 'VAR_OUTPUT',
             '    LinkHealthy'+READONLY+' : Bool;', '    OutputsEnabled'+READONLY+' : Bool;', 'END_VAR', 'VAR',
             '    Endpoint'+PRIVATE+' : "FB_IoBridgeEndpoint";', '    Config'+PRIVATE+' : "ST_IoBridgeConfig";',
             '    Inputs'+PRIVATE+' : DWord;', '    Demands'+PRIVATE+' : DWord;',
             '    Connected'+PRIVATE+' : Bool;', '    PeerEnabled'+PRIVATE+' : Bool;',
             '    PermitOutputs'+PRIVATE+' : Bool;', 'END_VAR', 'VAR CONSTANT',
             '    OUTPUT_MAPPING_CONFIRMED : Bool := FALSE;',
             '    EVALUATED_TWO_HAND_WIRED : Bool := FALSE;', 'END_VAR', 'BEGIN', *config_lines(mapping, True),
             '    #Inputs := DW#16#0;']
    for row in mapping['inputs']:
        expr = '"' + row['tag'] + '"'
        if row['signal'] == 'TwoHandSafeActive':
            expr += ' AND #EVALUATED_TWO_HAND_WIRED'
        lines.append('    #Inputs.%%X%d := %s;' % (row['bit'], expr))
    lines += ['    #Endpoint(Startup := #Startup, Enabled := TRUE, PhysicalRole := TRUE,',
              '        LocalSignals := #Inputs, LocalEnable := #OUTPUT_MAPPING_CONFIRMED,',
              '        BootEpoch := "GDB_IoBridgeEpoch".Epoch, Config := #Config,',
              '        LinkHealthy => #Connected, PeerEnable => #PeerEnabled, PeerSignals => #Demands);',
              '    #LinkHealthy := #Connected;',
              '    #PermitOutputs := #OUTPUT_MAPPING_CONFIRMED AND #Connected AND #PeerEnabled',
              '        AND #Inputs.%X11 AND #Inputs.%X12 AND #Inputs.%X9 AND NOT #Inputs.%X8;',
              '    #OutputsEnabled := #PermitOutputs;']
    for row in mapping['outputs']:
        expr = '#PermitOutputs AND #Demands.%X' + str(row['bit'])
        if 'opposite' in row:
            expr += ' AND NOT #Demands.%X' + str(row['opposite'])
        if row['signal'] == 'RamExtend':
            expr += ' AND #Inputs.%X2 AND #Inputs.%X13'
        lines.append('    "' + row['tag'] + '" := ' + expr + ';')
    for row in mapping['inhibited_outputs']:
        lines.append('    "' + row['tag'] + '" := FALSE;')
    lines += ['END_FUNCTION_BLOCK', '', 'DATA_BLOCK "GDB_PressIoBridgeHardwareDriver"',
              "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN',
              '"FB_PressIoBridgeHardwareDriver"', 'BEGIN', 'END_DATA_BLOCK', '',
              'ORGANIZATION_BLOCK "Main"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
              'VAR_INPUT', '    Initial_Call : Bool;', '    Remanence : Bool;',
              'END_VAR', 'BEGIN', '    "GDB_PressIoBridgeHardwareDriver"(Startup := #Initial_Call);',
              'END_ORGANIZATION_BLOCK', '']
    return '\n'.join(lines)


def client_driver(mapping):
    lines = ['FUNCTION_BLOCK "FB_PressIoBridgeClient"', "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1',
             'VAR', '    Endpoint'+PRIVATE+' : "FB_IoBridgeEndpoint";', '    Config'+PRIVATE+' : "ST_IoBridgeConfig";',
             '    Signals'+PRIVATE+' : DWord;', '    Demands'+PRIVATE+' : DWord;',
             '    Connected'+PRIVATE+' : Bool;', '    PeerEnabled'+PRIVATE+' : Bool;', 'END_VAR', 'BEGIN',
             *config_lines(mapping, False), '    #Demands := DW#16#0;']
    for row in mapping['outputs']:
        lines.append('    #Demands.%%X%d := "GDB_PressDemoIO".%s;' % (row['bit'], row['signal']))
    lines += ['    #Endpoint(Startup := FALSE, Enabled := TRUE, PhysicalRole := FALSE,',
              '        LocalSignals := #Demands, LocalEnable := TRUE,',
              '        BootEpoch := "GDB_IoBridgeEpoch".Epoch, Config := #Config,',
              '        LinkHealthy => #Connected, PeerEnable => #PeerEnabled, PeerSignals => #Signals);']
    for row in mapping['inputs']:
        if row['signal'] not in ('ControlOnFeedback', 'EStopReleasedMirror'):
            lines.append('    "GDB_PressDemoIO".%s := #Signals.%%X%d;' % (row['signal'], row['bit']))
    lines += ['    "GDB_PressDemoIO".StandardIoHealthy := #Connected AND #PeerEnabled;',
              '    "GDB_PressDemoIO".PartQuality := FALSE; // No quality sensor exists in the supplied I/O list.',
              'END_FUNCTION_BLOCK', '', 'DATA_BLOCK "GDB_PressIoBridgeClient"',
              "{ S7_Optimized_Access := 'TRUE' }", 'VERSION : 0.1', 'NON_RETAIN',
              '"FB_PressIoBridgeClient"', 'BEGIN', 'END_DATA_BLOCK', '']
    return '\n'.join(lines)


def build(physical=True):
    mapping = read_map()
    common = {'00_ST_IoBridgeConfig.udt': config_type(),
              '01_IoBridge.scl': template_text(),
              '02_GDB_IoBridgeEpoch.db': boot_store()}
    if physical:
        common['03_GVL_PressBridgeIO.xml'] = tags_xml(mapping)
        common['10_PressIoBridge.scl'] = physical_driver(mapping)
    else:
        from fraktal_tia_examples import build as press_build
        sources, _, _ = press_build()
        target = '38_PressDemoHardwareDriver.scl'
        original = sources[target]
        assert original.count('USE_SIMULATION : Bool := TRUE;') == 1
        anchor = '    "GDB_PressDemoHardwareDriver"(ReadInputs := TRUE);'
        assert original.count(anchor) == 1
        boundary = 'FUNCTION "F_PressDemoReadInputs" : Void'
        assert original.count(boundary) == 1
        # The logical I/O image is internal transport storage. Publishing raw
        # demands would create a command path outside the Unit mailbox.
        image_source=sources['38_GDB_PressDemoIO.db']
        image = re.search(r'(DATA_BLOCK "GDB_PressDemoIO".*?\nVAR\n)(.*?)(END_VAR)', image_source, re.S)
        if not image: raise ValueError('press logical I/O image not found')
        fields=re.findall(r'^\s+\w+\s*\{([^}]+)\}\s*:\s*Bool;',image[2],re.M)
        if not fields or len(fields)!=len(re.findall(r'\bBool;',image[2])) or any("ExternalAccessible := 'False'" not in flags for flags in fields):
            raise ValueError('logical I/O storage must be private in the owning press generator')
        original = original.replace(boundary, client_driver(mapping) + '\n' + boundary)
        sources[target] = original.replace('USE_SIMULATION : Bool := TRUE;', 'USE_SIMULATION : Bool := FALSE;').replace(
            anchor, '    "GDB_PressIoBridgeClient"();\n' + anchor)
        common = {**sources, **common}
    return common


def generate(out, physical=True):
    sources = build(physical)
    out.mkdir(parents=True, exist_ok=False)
    for name, text in sources.items():
        (out / name).write_bytes(text.encode('ascii'))
    manifest = {'schema': 'fraktal.tia.press-io-bridge.v1', 'physical': physical,
                'io_map_sha256': hashlib.sha256(MAP.read_bytes()).hexdigest(),
                'template_sha256': hashlib.sha256(TEMPLATE.read_bytes()).hexdigest(),
                'instruction_versions': INSTRUCTIONS,
                'generated': {n: hashlib.sha256(t.encode('ascii')).hexdigest() for n, t in sources.items()}}
    (out / 'bridge_manifest.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode('ascii'))
    return manifest


def verify(out, native=None):
    recorded = json.loads((out / 'bridge_manifest.json').read_bytes())
    sources = build(recorded['physical'])
    if recorded['schema'] != 'fraktal.tia.press-io-bridge.v1' or recorded['io_map_sha256'] != hashlib.sha256(MAP.read_bytes()).hexdigest():
        raise ValueError('bridge map/schema differs from authority')
    if recorded['template_sha256'] != hashlib.sha256(TEMPLATE.read_bytes()).hexdigest() or recorded['instruction_versions'] != INSTRUCTIONS:
        raise ValueError('bridge template/instruction versions changed')
    expected = {n: hashlib.sha256(t.encode('ascii')).hexdigest() for n, t in sources.items()}
    if recorded['generated'] != expected or any((out / n).read_bytes() != t.encode('ascii') for n, t in sources.items()):
        raise ValueError('bridge sources differ from deterministic replay')
    result = {'replayed_sources': len(sources), 'physical': recorded['physical']}
    if native is not None:
        spec = importlib.util.spec_from_file_location('tia_bridge_exports', ROOT / 'Tests/Generator/verify_exports.py')
        verifier = importlib.util.module_from_spec(spec); spec.loader.exec_module(verifier)
        with tempfile.TemporaryDirectory() as temporary:
            witness = Path(temporary)
            for name, text in sources.items():
                if not name.endswith(('.udt', '.scl')) or name.startswith(('23_', '28_')): continue
                # Initialized instance/global DB exports contain live/default
                # payloads; compare every code/type block, not those payloads.
                for match in re.finditer(r'^(TYPE|FUNCTION_BLOCK|FUNCTION|ORGANIZATION_BLOCK)\b.*?^END_\1\b[^\n]*', text, re.M | re.S):
                    block = re.match(r'\w+\s+"([^"]+)"', match[0])[1]
                    (witness / (block + ('.udt' if match[1] == 'TYPE' else '.scl'))).write_bytes((match[0] + '\n').encode('ascii'))
            proof = verifier.verify(witness, native)
            result.update({key: len(values) for key, values in proof.items()})
        epoch = ET.parse(native / 'xml/GDB_IoBridgeEpoch.xml').find('.//{*}Member[@Name="Epoch"]')
        if epoch is None or epoch.attrib.get('Remanence') != 'Retain': raise ValueError('native boot counter is not retained')
        if not recorded['physical']:
            members = ET.parse(native / 'xml/GDB_PressDemoIO.xml').findall('.//Interface/{*}Sections/{*}Section/{*}Member')
            if not members: raise ValueError('native logical I/O image missing')
            for member in members:
                flags = {a.attrib['Name']: a.text for a in member.findall('./{*}AttributeList/{*}BooleanAttribute')}
                if any(flags.get(key, 'true').lower() != 'false' for key in ('ExternalAccessible', 'ExternalVisible', 'ExternalWritable')):
                    raise ValueError('native logical I/O is externally published: ' + member.attrib['Name'])
            result['private_io_members'] = len(members)
        if not recorded['physical']:
            import fraktal_tia_graph as graph
            import fraktal_tia_ld as ladder
            result['graph'] = {}; result['ladder'] = {}
            for name, text in sources.items():
                if not name.endswith('.xml'): continue
                block = re.search(r'<Name>(\w+)</Name>', text)[1]
                target = native / 'xml' / (block + '.xml')
                if name.startswith('26_'):
                    result['ladder'][block] = ladder.parity(out / name, target)
                else:
                    if graph.dump(text) != graph.dump(target.read_text(encoding='utf-8-sig')): raise ValueError('native GRAPH differs: ' + block)
                    result['graph'][block] = len(graph.dump(text)['steps'])
    return result


def prepare_plan(sources, project, native, physical=True):
    """Prepare offline-only grouped import/compile plans; never download here."""
    if not project.is_file() or project.suffix.lower() != '.ap20':
        raise ValueError('supply the saved COPY of the station project (.ap20)')
    if physical:
        lines = ['open-project --path "' + str(project) + '"', 'delete-blocks --plc PLC_1']
        for name, group in [('00_ST_IoBridgeConfig.udt', 'Framework/IoBridge/DUTs'),
                            ('02_GDB_IoBridgeEpoch.db', 'Examples/PressIoBridge/00_System'),
                            ('01_IoBridge.scl', 'Framework/IoBridge')]:
            lines.append('import-sources --plc PLC_1 --dir "' + str(sources) + '" --only "' + name + '" --group ' + group)
        lines += ['import-xml --plc PLC_1 --file "' + str(sources / '03_GVL_PressBridgeIO.xml') + '" --kind tags',
                  'import-sources --plc PLC_1 --dir "' + str(sources) + '" --only "10_PressIoBridge.scl" --group Examples/PressIoBridge/00_System',
                  'save', 'compile --plc PLC_1', 'compile --plc PLC_1 --hw', 'save',
                  'export --plc PLC_1 --out "' + str(native) + '" --scl']
        target = sources / 'import.plan'
        with target.open('xb') as stream: stream.write(('\n'.join(lines) + '\n').encode('ascii'))
    else:
        from fraktal_tia_program_layout import organize
        organize(sources, sources / 'grouped', project, native)
        target = sources / 'grouped/import.plan'
        text = target.read_text(encoding='ascii')
        text = text.replace('delete-blocks --plc PLC_1\n', 'delete-blocks --plc PLC_1\nset-ip --plc PLC_1 --ip ' + read_map()['simulator_bench_address'] + ' --mask 255.255.255.0\n')
        target.write_bytes(text.encode('ascii'))
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--out', type=Path)
    mode.add_argument('--verify', type=Path)
    parser.add_argument('--client', action='store_true')
    parser.add_argument('--project', type=Path, help='saved offline project copy; prepares an import/compile plan')
    parser.add_argument('--native', type=Path, help='new native-export directory for the prepared plan')
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify(args.verify, args.native)))
        raise SystemExit(0)
    if args.project and not args.native: parser.error('--project requires --native')
    result = generate(args.out, not args.client)
    if args.project:
        prepare_plan(args.out, args.project, args.native, not args.client)
    print(json.dumps({'sources': len(result['generated']), 'physical': result['physical']}))
