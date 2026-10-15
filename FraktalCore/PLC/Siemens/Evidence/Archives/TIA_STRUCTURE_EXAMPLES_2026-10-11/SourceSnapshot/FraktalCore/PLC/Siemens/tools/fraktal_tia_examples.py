"""Generate unwired ST/LAD/GRAPH press examples from one process definition."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import fraktal_tia_graph as GRAPH
from fraktal_tia_binding import Catalog, PRIVATE, READONLY, literal, type_source

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'Examples/PressDemo/01_PneumaticPress'
MODULES = ROOT / 'Framework/Modules/ControlModules/Cylinder'
CORE = ROOT / 'Framework/Core'
FN = 'http://www.siemens.com/automation/Openness/SW/NetworkSource/FlgNet/v4'
IFACE = 'http://www.siemens.com/automation/Openness/SW/Interface/v5'


def udt(name, fields, visible=()):
    return type_source(name, [{'member': n, 'native_type': t, 'accessible': n in visible, 'initial': ''}
                             for n, t in fields])


def bind(text, catalog, extra=None):
    for enum, members in catalog.enums.items():
        for name, value in members.items():
            text = text.replace('@'+enum+'.'+name+'@', str(value))
    for name, value in (extra or {}).items():
        text = text.replace('@'+name+'@', str(value))
    assert not re.search(r'@[A-Z_a-z][\w.]*@', text), 'Unbound template token'
    return text


def signatures(sources):
    result = {}
    for text in sources.values():
        for hit in re.finditer(r'FUNCTION "(\w+)" : (\w+)(.*?)\nBEGIN', text, re.S):
            rows = []
            for section, body in re.findall(r'VAR_(INPUT|OUTPUT|IN_OUT)(.*?)END_VAR', hit[3], re.S):
                for name, datatype in re.findall(r'^\s*(\w+)\s*:\s*([^;]+);', body, re.M):
                    rows.append((name, {'INPUT':'Input','OUTPUT':'Output','IN_OUT':'InOut'}[section], datatype.strip()))
            if hit[2].lower() != 'void': rows.append(('Ret_Val', 'Return', hit[2]))
            result[hit[1]] = rows
    return result


class Ladder:
    """Declare rails, contacts and typed calls; never concatenate graph fragments."""
    def __init__(self, name, interface, sigs):
        self.root = ET.Element('Document')
        ET.SubElement(self.root, 'Engineering', version='V20')
        self.block = ET.SubElement(self.root, 'SW.Blocks.FB', ID='0')
        attributes = ET.SubElement(self.block, 'AttributeList')
        for key, value in [('AutoNumber','true'),('MemoryLayout','Optimized'),('Name',name),('Namespace',''),('ProgrammingLanguage','LAD')]:
            ET.SubElement(attributes, key).text = value
        intf = ET.SubElement(attributes,'Interface')
        sections = ET.SubElement(intf,'Sections', xmlns=IFACE)
        for kind, members in interface.items():
            sec = ET.SubElement(sections,'Section',Name=kind)
            for member, datatype in members:
                node=ET.SubElement(sec,'Member',Name=member,Datatype=datatype)
                attributes=ET.SubElement(node,'AttributeList')
                visible=kind=='Static' and (member in ('Seq','Conditions','ModeStart','RamExtend') or member.startswith('Row'))
                for flag,value in [('ExternalAccessible',kind!='InOut' and (kind!='Static' or visible)),
                                   ('ExternalVisible',kind!='InOut' and (kind!='Static' or visible)),('ExternalWritable',False)]:
                    ET.SubElement(attributes,'BooleanAttribute',Name=flag,SystemDefined='true').text=str(value).lower()
        self.objects = ET.SubElement(self.block,'ObjectList')
        self.sigs = sigs; self.networks=[]

    def net(self):
        unit=ET.SubElement(self.objects,'SW.Blocks.CompileUnit',ID=str(len(self.networks)+1),CompositionName='CompileUnits')
        attr=ET.SubElement(unit,'AttributeList'); src=ET.SubElement(attr,'NetworkSource')
        net=ET.SubElement(src,'FlgNet',xmlns=FN)
        ET.SubElement(attr,'ProgrammingLanguage').text='LAD'
        self.parts=ET.SubElement(net,'Parts');self.wires=ET.SubElement(net,'Wires');self.uid=20
        self.networks.append(net)

    def fresh(self):
        self.uid+=1;return str(self.uid)

    def access(self, operand, datatype='Bool'):
        uid=self.fresh()
        access=ET.SubElement(self.parts,'Access',Scope='LocalVariable' if operand.startswith('#') else 'LiteralConstant',UId=uid)
        if operand.startswith('#'):
            symbol=ET.SubElement(access,'Symbol')
            for component in operand[1:].split('.'):
                ET.SubElement(symbol,'Component',Name=component)
        else:
            constant=ET.SubElement(access,'Constant')
            ET.SubElement(constant,'ConstantType').text=datatype
            ET.SubElement(constant,'ConstantValue').text=operand
        return ('IdentCon',{'UId':uid})

    def wire(self, *connections):
        wire=ET.SubElement(self.wires,'Wire',UId=self.fresh())
        for tag,attrs in connections: ET.SubElement(wire,tag,**attrs)

    def contact(self, variable):
        uid=self.fresh();ET.SubElement(self.parts,'Part',Name='Contact',UId=uid)
        self.wire(self.access(variable),('NameCon',{'UId':uid,'Name':'operand'}))
        return uid

    def call(self, name, parameters, gate=None):
        self.net();uid=self.fresh();node=ET.SubElement(self.parts,'Call',UId=uid)
        info=ET.SubElement(node,'CallInfo',Name=name,BlockType='FC')
        for pin, section, datatype in self.sigs[name]:
            ET.SubElement(info,'Parameter',Name=pin,Section=section,Type=datatype)
        if gate:
            contact=self.contact(gate);self.wire(('Powerrail',{}),('NameCon',{'UId':contact,'Name':'in'}))
            self.wire(('NameCon',{'UId':contact,'Name':'out'}),('NameCon',{'UId':uid,'Name':'en'}))
        else:self.wire(('Powerrail',{}),('NameCon',{'UId':uid,'Name':'en'}))
        for pin,section,datatype in self.sigs[name]:
            assert pin in parameters,(name,pin)
            self.wire(self.access(parameters[pin],datatype),('NameCon',{'UId':uid,'Name':pin}))

    def conjunction(self, inputs, output):
        self.net();previous=('Powerrail',{})
        for variable in inputs:
            uid=self.contact(variable);self.wire(previous,('NameCon',{'UId':uid,'Name':'in'}))
            previous=('NameCon',{'UId':uid,'Name':'out'})
        uid=self.fresh();ET.SubElement(self.parts,'Part',Name='Coil',UId=uid)
        self.wire(previous,('NameCon',{'UId':uid,'Name':'in'}))
        self.wire(self.access(output),('NameCon',{'UId':uid,'Name':'operand'}))

    def text(self):
        ET.indent(self.root,space='  ')
        return '<?xml version="1.0" encoding="utf-8"?>\n'+ET.tostring(self.root,encoding='unicode')+'\n'


def call(name, **params):
    return name,params


def scl_call(operation):
    name,parameters=operation
    args=', '.join(key+' := '+value for key,value in parameters.items() if key!='Ret_Val')
    expression='"'+name+'"('+args+')'
    return (parameters['Ret_Val']+' := ' if 'Ret_Val' in parameters else '')+expression+';'


def interface(chain,roles):
    consumed={c for step in chain['steps'] for c in step.get('wait',[])}
    consumed.update(step['delay'] for step in chain['steps'] if step.get('delay'))
    if 'StartLatched' in consumed:consumed.add('StartPulse')
    if any(step.get('hold_force') for step in chain['steps']):consumed.add('TwoHandHeld')
    inputs=[('Run','Bool'),('Reset','Bool'),('OwnerIndex','DInt'),('Delta','Time')]
    inputs += [(n,t) for n,t in [('PartPresent','Bool'),('AirPressureOk','Bool'),('TwoHandHeld','Bool'),('StartPulse','Bool'),
                               ('TransferSettleTime','Time'),('PressSettleTime','Time')] if n in consumed]
    return {'Input':inputs,
            'InOut':[(role,'"FB_CylinderCM"') for role in roles],
            'Output':[],
            'Static':[('Seq','"FRK_SequenceCtx"'),*[( 'Row'+str(i),'"FRK_SequenceRow"') for i,_ in enumerate(chain['steps'],1)]] +
                     [('At'+str(s['no']),'Bool') for s in chain['steps']] +
                     [('Ready'+str(i),'Bool') for i in range(1,6)] + [('Advance','Bool')]}


def header(name,intf):
    lines=['FUNCTION_BLOCK "'+name+'"',"{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1']
    for kind,members in intf.items():
        lines += [{'Input':'VAR_INPUT','InOut':'VAR_IN_OUT','Output':'VAR_OUTPUT','Static':'VAR'}[kind]]
        lines += ['    '+n+(READONLY if kind=='Output' or (kind=='Static' and
                  (n in ('Seq','Conditions','ModeStart','RamExtend') or n.startswith('Row'))) else PRIVATE
                  if kind in ('Static','InOut') else '')+' : '+t+';' for n,t in members]
        lines += ['END_VAR']
    return '\n'.join(lines)+'\nBEGIN\n'


def frame_ops(chain,roles):
    begin=[call('FRK_SeqBegin',Run='#Run',Reset='#Reset',OwnerIndex='#OwnerIndex',
                ChainIndex=str(chain['chain_index']),Delta='#Delta',Seq='#Seq')]
    leases=[call('F_CylinderSequenceLease',Seq='#Seq',Target='#'+role) for role in roles]
    if any('StartLatched' in step.get('wait',[]) for step in chain['steps']):
        begin.append(call('FRK_SeqStart',Seq='#Seq',StartPulse='#StartPulse'))
    return begin+leases,leases


def step_ops(step,index,module):
    operations=[call('FRK_SeqStep',StepNo=str(step['no']),StepName=literal(step['label']),Seq='#Seq',Row='#Row'+str(index))]
    ready=[]
    for role,command in step.get('commands',[]):
        assert role in ('PressRam','Door','PartSlide')
        name=next(c['api'] for c in module['commands'] if c['label']==command)
        result='#Ready'+str(len(ready)+1);ready.append(result)
        operations.append(call(name,Seq='#Seq',Target='#'+role,Ret_Val=result))
    for condition in step.get('wait',[]):
        result='#Ready'+str(len(ready)+1);ready.append(result)
        source='#Seq.StartLatched' if condition=='StartLatched' else '#'+condition
        operations.append(call('FRK_SeqAwait',Seq='#Seq',Label=literal('project.condition.'+condition),Ok=source,Ret_Val=result))
    if step.get('hold_force'):
        operations.append(call('F_CylinderForcePermit',Target='#'+step['hold_force'],Permit='#TwoHandHeld'))
    if step.get('delay'):
        result='#Ready'+str(len(ready)+1);ready.append(result)
        operations.append(call('FRK_SeqDelay',Seq='#Seq',PT='#'+step['delay'],Delta='#Delta',
                               Permit='#TwoHandHeld' if step.get('hold_force') else 'TRUE',Ret_Val=result))
    if step.get('cycle_end'):
        operations.append(call('FRK_SeqCycleEnd',Seq='#Seq'))
    if step.get('complete'):
        operations.append(call('FRK_SeqComplete',Seq='#Seq'))
    return operations,ready


def release_sources(definition,sources,width):
    conditions=definition['release']
    names=[c['name'] for c in conditions]
    sources['06_ST_PressDemoReleaseConditions.udt']=udt('ST_PressDemoReleaseConditions',[(n,'Bool') for n in names],names)
    sources['06_FRK_PermCtx.udt']=udt('FRK_PermCtx',[('Permit','Bool'),('Count','Int'),('Blocker','String['+str(width)+']')],('Permit','Count','Blocker'))
    sources['16_PermissiveServices.scl']=(CORE/'permissive_services.scl.in').read_text('ascii')
    signals=sorted({s for condition in conditions for s in condition['all']})
    intf={'Input':[(n,'Bool') for n in signals],
          'Static':[('Conditions','"ST_PressDemoReleaseConditions"'),('ModeStart','"FRK_PermCtx"'),('RamExtend','"FRK_PermCtx"')]}
    text=header('FB_PressDemoRelease',intf)
    ladder=Ladder('FB_LD_PressDemoRelease',intf,signatures(sources))
    for row in conditions:
        target='#Conditions.'+row['name'];inputs=['#'+s for s in row['all']]
        text+='    '+target+' := '+' AND '.join(inputs)+';\n'
        ladder.conjunction(inputs,target)
    for group in ('ModeStart','RamExtend'):
        op=call('FRK_PermBegin',Perm='#'+group);text+='    '+scl_call(op)+'\n';ladder.call(*op)
        selected=conditions[:1] if group=='ModeStart' else conditions[1:]
        for row in selected:
            op=call('FRK_PermCondition',Perm='#'+group,Label=literal('project.condition.'+row['name']),Ok='#Conditions.'+row['name'])
            text+='    '+scl_call(op)+'\n';ladder.call(*op)
    sources['23_FB_PressDemoRelease.scl']=text+'END_FUNCTION_BLOCK\n'
    sources['26_FB_LD_PressDemoRelease.xml']=ladder.text()


def graph_sources(chain,roles,module,sources):
    graph_name='FB_SFC_'+chain['name']
    old_interface=interface(chain,roles)
    scalar={'Bool':'BOOL','Time':'TIME','DInt':'DINT'}
    inout=[(n,scalar.get(t,t.strip('"'))) for kind,members in old_interface.items() if kind!='Input'
           for n,t in members if not n.startswith('At') and n!='Advance']
    # Private owner storage provides the chart's parameter instances. GRAPH FBs
    # remain single-instance DBs selected by the user; no example DB is created.
    chart={'name':graph_name,'number':100,'inout':inout,'steps':[],
           'graph_settings':{'skip_steps':False}}
    for i,step in enumerate(chain['steps'],1):
        operations,ready=step_ops(step,i,module);actions=[]
        for name,parameters in operations:
            if 'Ret_Val' in parameters:
                parameters={**parameters,'Ret_Val':parameters['Ret_Val']}
            actions.append({'text':GRAPH.call_text(name,list(parameters.items()))})
        for role,_ in step.get('commands',[]):
            actions.append({'text':GRAPH.call_text('F_CylinderRelease',[('Seq','#Seq'),('Target','#'+role)]),'event':'S0'})
        chart['steps'].append({'no':step['no'],'label':step['label'],'next':step.get('next',step['no']),
                               'actions':actions,'when':['#Seq.Running',*ready] if 'next' in step else ['FALSE']})
    reference=(ROOT/'Spikes/S11_Graph/reference/FB_GraphSample.xml').read_text('utf-8-sig')
    xml=GRAPH.generate(chart,reference)
    # TIA retains flags on scalar InOut parameters, but strips them from FB
    # parameter instances and structured InOut parameters. Do not claim those
    # aliases have a verified runtime exclusion.
    def hide_value_parameters(match):
        attrs='<AttributeList>'+''.join('<BooleanAttribute Name="'+flag+'" SystemDefined="true">false</BooleanAttribute>'
              for flag in ('ExternalAccessible','ExternalVisible','ExternalWritable'))+'</AttributeList>'
        return match[1]+re.sub(r'(<Member\b[^>]*?) />',
            lambda hit:hit[0] if '&quot;' in hit[1] else hit[1]+'>'+attrs+'</Member>',match[2])+match[3]
    xml=GRAPH.once(xml,r'(\n  <Section Name="InOut">\n)(.*?)(  </Section>\n)',hide_value_parameters,re.S)
    # Input values remain input values: passing them as VAR_IN_OUT would let a
    # chart modify its owner's inputs and is rejected by the clean warning gate.
    members=''.join('    <Member Name="'+n+'" Datatype="'+scalar.get(t,t)+'" />\n'
                    for n,t in old_interface['Input'])
    xml=GRAPH.once(xml,r'(\n  <Section Name="Input">\n.*?)(  </Section>\n)',
                   lambda m:m[1]+members+m[2],re.S)
    sources['27_'+graph_name+'.xml']=xml
    owner_intf=copy.deepcopy(old_interface)
    owner_intf['InOut'].append(('Chart','"'+graph_name+'"'))
    before,after=frame_ops(chain,roles)
    text=header('FB_'+chain['name']+'GraphOwner',owner_intf)
    text+='\n'.join('    '+scl_call(op) for op in before)+'\n'
    params=[(n,'#'+n) for n,t in old_interface['Input']+inout]
    params.append(('INIT_SQ','#Seq.Restart'))
    text+='    #Chart('+', '.join(n+' := '+v for n,v in params)+');\n'
    text+='\n'.join('    '+scl_call(op) for op in after)+'\nEND_FUNCTION_BLOCK\n'
    sources['28_FB_'+chain['name']+'GraphOwner.scl']=text


def build():
    definition=json.loads((EXAMPLE/'press.json').read_bytes());module=json.loads((MODULES/'cylinder.json').read_bytes())
    catalog=Catalog.read();width=DECL.CoreFacts.read().key_width
    records=copy.deepcopy(module['records'])
    records['ST_SequenceCommandLease']='STRUCT OwnerIndex : DINT; ChainIndex : DINT; Step : DINT; Raised : BOOL; AbortIssued : BOOL; ReleasedScan : UDINT; END_STRUCT'
    records.update({'ST_PressDemoParCfg':'STRUCT SchemaVersion : UINT := 1; Timeout : TIME := T#0ms; END_STRUCT',
                    'ST_PressDemoParCmd':'STRUCT Reserved : BOOL; END_STRUCT',
                    'ST_PressDemoOutCmd':'STRUCT CycleCompleted : BOOL; END_STRUCT',
                    'ST_PressDemoOutImm':'STRUCT Reserved : BOOL; END_STRUCT'})
    cm={k:v for k,v in module.items() if k not in ('records',)}
    cm['commands']=[{k:v for k,v in c.items() if k!='api'} for c in cm['commands']]
    command_ids={c['label']:c['id'] for c in module['commands']}
    logic=bind((MODULES/'cylinder_logic.scl.in').read_text('ascii'),catalog,command_ids)
    pieces=re.split(r'@REGION:(\w+)@\n',logic)[1:]
    cm['logic']=dict(zip(pieces[::2],pieces[1::2]));cm['children']=[]
    owner={'name':'FB_PressDemoUnit','tier':'UNIT','type_key':'project.pressDemo','children':[{'name':r,'type':module['name']} for r in definition['roles']],
           'contract':{k:'ST_PressDemo'+k for k in ('ParCfg','ParCmd','OutCmd','OutImm')},
           'commands':[{'id':1,'label':'Run'}],'timeout':'Timeout',
           'unit':{'modes':['AUTO','MANUAL','HOME'],'initial':'MANUAL','run_command':1}}
    declaration={'schema_version':1,'target_family':'S7-1500','registry_capacity':4,'types':[owner,cm],
                 'roots':[{'name':'PressDemo','type':'FB_PressDemoUnit'}],'records':records}
    sources,manifest=GEN.build(DECL.validate(declaration),True)
    sources={name:text for name,text in sources.items() if not name.startswith(('25_','30_','35_','40_'))}
    fields=[('RunPrevious','Bool'),('Running','Bool'),('Restart','Bool'),('Done','Bool'),('Error','Bool'),
            ('Pending','Bool'),('StartLatched','Bool'),('OwnerIndex','DInt'),('ChainIndex','DInt'),
            ('Step','DInt'),('ScanStep','DInt'),('RecordedStep','DInt'),('RetVal','DInt'),('Scan','UDInt'),
            ('Visit','UDInt'),('Elapsed','Time'),('DelayElapsed','Time'),('StepName','String['+str(width)+']'),
            ('Awaiting','String['+str(width)+']'),('ErrorDiagnostic','"ST_Diagnostic"')]
    sources['06_FRK_SequenceCtx.udt']=udt('FRK_SequenceCtx',fields,
        ('Running','Done','Error','Pending','Step','Elapsed','StepName','Awaiting','ErrorDiagnostic'))
    sources['06_FRK_SequenceRow.udt']=udt('FRK_SequenceRow',[('StepNo','DInt'),('Visited','Bool'),('LastDuration','Time')],('StepNo','Visited','LastDuration'))
    sources['16_SequenceServices.scl']=bind((CORE/'sequence_services.scl.in').read_text('ascii'),catalog)
    sources['22_CylinderApi.scl']=bind((MODULES/'cylinder_api.scl.in').read_text('ascii'),catalog,
                                    {**command_ids,'READY':catalog.enums['E_ExecState']['READY']})
    release_sources(definition,sources,width)
    sigs=signatures(sources)
    for chain in definition['chains']:
        name='FB_'+chain['name'];intf=interface(chain,definition['roles']);before,after=frame_ops(chain,definition['roles'])
        text=header(name,intf)+'\n'.join('    '+scl_call(op) for op in before)+'\n'
        text+='    CASE #Seq.ScanStep OF\n'
        ladder=Ladder('FB_LD_'+chain['name'],intf,sigs)
        for op in before:ladder.call(*op)
        # Fresh start is latched by a shared service in both forms.
        for i,step in enumerate(chain['steps'],1):
            text+='        '+str(step['no'])+':\n            IF #Seq.Running AND NOT #Seq.Error THEN\n'
            operations,ready=step_ops(step,i,module)
            for op in operations:text+='                '+scl_call(op)+'\n'
            if 'next' in step:
                text+='                "FRK_SeqAdvance"(Seq := #Seq, Ok := '+(' AND '.join(ready) or 'TRUE')+', OnAdvance := '+str(step['next'])+');\n'
            text+='            END_IF;\n'
            at='#At'+str(step['no']);ladder.call('FRK_SeqAt',{'Seq':'#Seq','StepNo':str(step['no']),'Ret_Val':at})
            for op in operations:ladder.call(*op,gate=at)
            if 'next' in step:
                ladder.conjunction([at,*ready],'#Advance')
                ladder.call('FRK_SeqAdvance',{'Seq':'#Seq','Ok':'#Advance','OnAdvance':str(step['next'])},gate=at)
        text+='        ELSE\n            #Seq.Error := TRUE;\n'
        text+='            #Seq.ErrorDiagnostic.ReasonCode := '+str(definition['invalid_step_reason'])+';\n'
        text+="            #Seq.ErrorDiagnostic.Description := WSTRING#'project.sequence.invalidStep';\n"
        text+='    END_CASE;\n'+'\n'.join('    '+scl_call(op) for op in after)+'\nEND_FUNCTION_BLOCK\n'
        for op in after:ladder.call(*op)
        sources['23_'+name+'.scl']=text;sources['26_FB_LD_'+chain['name']+'.xml']=ladder.text()
        graph_sources(chain,definition['roles'],module,sources)
    return sources,definition,manifest


def generate(out):
    sources,definition,manifest=build()
    out.mkdir(parents=True,exist_ok=False)
    for name,text in sources.items():(out/name).write_bytes(text.encode('ascii'))
    data={'kind':'fraktal.tia.press.examples.v1','wired':False,'definition':definition,
          'generated':{n:hashlib.sha256(t.encode('ascii')).hexdigest() for n,t in sources.items()},
          'core_inputs':manifest['core_inputs']}
    (out/'manifest.json').write_bytes((json.dumps(data,indent=2)+'\n').encode('ascii'))
    return len(sources)


def verify(out,native=None):
    import fraktal_tia_ld as LD
    sources,definition,manifest=build()
    recorded=json.loads((out/'manifest.json').read_bytes())
    assert recorded['definition']==definition and recorded['core_inputs']==manifest['core_inputs'],'Changed authoritative inputs'
    assert recorded['generated']=={n:hashlib.sha256(t.encode('ascii')).hexdigest() for n,t in sources.items()},'Generated manifest differs from replay'
    located={}
    for name,text in sources.items():
        hits=list(out.rglob(name));assert len(hits)==1,(name,'missing or duplicate generated source')
        assert hits[0].read_bytes()==text.encode('ascii'),(name,'source differs from replay')
        located[name]=hits[0]
    result={'replayed_sources':len(sources),'wired':False,'ladder':{},'graph':{}}
    for name,path in located.items():
        if not name.endswith('.xml'):continue
        block=re.search(r'<Name>(\w+)</Name>',sources[name])[1]
        exported=Path(native)/'xml'/ (block+'.xml') if native else path
        if name.startswith('26_'):
            result['ladder'][block]=LD.parity(path,exported)
        else:
            expected=GRAPH.dump(sources[name]);actual=GRAPH.dump(exported.read_text('utf-8-sig'))
            assert expected==actual,(block,'native chart differs from generated graph')
            result['graph'][block]={'steps':len(actual['steps'])}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--out',type=Path);group.add_argument('--verify',type=Path)
    parser.add_argument('--native',type=Path)
    args=parser.parse_args()
    print(json.dumps(verify(args.verify,args.native) if args.verify else {'generated':generate(args.out)},indent=2))
