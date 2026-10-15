"""Generate the wired GRAPH/ST press demo and optional ST/LAD renditions."""
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
CONTROL_MODULES = ROOT / 'Framework/Modules/ControlModules'
TC3_MODULE_REASONS = 'FraktalCore/PLC/TwinCAT/Framework/Fraktal_Modules/Params/PL_ModuleReasons.TcGVL'
# Passive sensor CMs the press composes beside its cylinders: (folder, stem).
SENSOR_MODULES = (('TwoHand', 'two_hand'), ('DigitalInput', 'digital_input'), ('AirPressure', 'air_pressure'))
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
                for name, datatype in re.findall(r'\b(\w+)\s*:\s*([^;]+);', body):
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
    inputs=[('Run','Bool'),('Reset','Bool'),('OwnerIndex','DInt'),*([('ChainIndex','DInt')] if chain.get('shared') else []),('Delta','Time')]
    inputs += [(n,t) for n,t in [('PartPresent','Bool'),('AirPressureOk','Bool'),('TwoHandHeld','Bool'),('StartPulse','Bool'),
                               ('TransferSettleTime','Time'),('PressSettleTime','Time')] if n in consumed]
    if chain.get('process')=='auto':
        inputs += [('PartQuality','Bool'),('RequireTwoHandStart','Bool'),('SourcePath','String[80]')]
        for n,t in [('PartPresent','Bool'),('AirPressureOk','Bool'),('TwoHandHeld','Bool'),('StartPulse','Bool'),
                    ('TransferSettleTime','Time'),('PressSettleTime','Time')]:
            if n not in dict(inputs):inputs.append((n,t))
    inout=[(role,'"FB_CylinderCM"') for role in roles]
    changeover=chain.get('process')=='changeover'
    if changeover:
        inputs += [('ModelCode','String'),('SourcePath','String[80]')]
        inout += [('AlarmLog','"FRK_AlarmLog"')]
    if chain.get('process')=='auto':
        inout += [(n,'"'+t+'"') for n,t in [('Core','FRK_Core'),('Unit','FRK_Unit'),('Status','ST_ModuleStatus'),
                                           ('Part','ST_PartContext'),('AlarmLog','FRK_AlarmLog')]]
    return {'Input':inputs,
            'InOut':inout,
            'Output':[],
            'Static':[('Seq','"FRK_SequenceCtx"'),*[( 'Row'+str(i),'"FRK_SequenceRow"') for i,_ in enumerate(chain['steps'],1)]] +
                     [('At'+str(s['no']),'Bool') for s in chain['steps']] +
                     [('Ready'+str(i),'Bool') for i in range(1,6)] + [('Advance','Bool')] +
                     ([('Cycle','"ST_PressDemoCycle"')] if chain.get('process')=='auto' else []) +
                     ([('LoadPosition','"FB_PressDemoLoadPosition"'),('LoadDone','Bool'),('LoadActive','Bool')]
                      if chain.get('process')=='auto' or changeover else [])}


def header(name,intf):
    lines=['FUNCTION_BLOCK "'+name+'"',"{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1']
    for kind,members in intf.items():
        lines += [{'Input':'VAR_INPUT','InOut':'VAR_IN_OUT','Output':'VAR_OUTPUT','Static':'VAR'}[kind]]
        lines += ['    '+n+(READONLY if kind=='Output' or (kind=='Static' and
                  (n in ('Seq','Conditions','ModeStart','RamExtend') or n.startswith('Row'))) else PRIVATE
                  if kind in ('Static','InOut') else '')+' : '+t+';' for n,t in members]
        lines += ['END_VAR']
    return '\n'.join(lines)+'\nBEGIN\n'


def frame_ops(chain,roles,graph=False):
    begin=[call('FRK_SeqGraphBegin' if graph else 'FRK_SeqBegin',Run='#Run',Reset='#Reset',OwnerIndex='#OwnerIndex',
                ChainIndex='#ChainIndex' if chain.get('shared') else str(chain['chain_index']),BranchIndex=str(chain.get('branch_index',0)),
                ViewOffset=str(chain.get('view_offset',0)),ViewDepth=str(chain.get('view_depth',0)),Delta='#Delta',Seq='#Seq')]
    leases=[call('F_CylinderSequenceLease',Seq='#Seq',Target='#'+role) for role in roles]
    if chain.get('initial_step'):
        begin.append(call('FRK_SeqInitial',Seq='#Seq',InitialStep=str(chain['initial_step'])))
    if chain.get('process')=='auto' or any('StartLatched' in step.get('wait',[]) for step in chain['steps']):
        begin.append(call('FRK_SeqStart',Seq='#Seq',StartPulse='#StartPulse'))
    if chain.get('process')=='auto':
        begin += [call('F_PressDemoReset',Seq='#Seq',Cycle='#Cycle'),
                  call('FRK_SeqSubActive',Seq='#Seq',Run='#Run',StepNo='240',Ret_Val='#LoadActive'),
                  call('F_PressDemoLoadPosition',Target='#LoadPosition',Run='#LoadActive',Reset='#Seq.SubReset',
                       OwnerIndex='#OwnerIndex',ChainIndex=str(chain['load_chain_index']),Delta='#Delta',**{r:'#'+r for r in roles},Ret_Val='#LoadDone')]
        leases.append(call('FRK_SeqOwnerStatus',Seq='#Seq',Core='#Core',Status='#Status'))
        leases.append(call('FRK_SeqSubStatus',Seq='#Seq',Child='#LoadPosition.Seq'))
    elif chain.get('load_step'):
        # Same shared motion chain under this chain's own lease identity.
        begin += [call('FRK_SeqSubActive',Seq='#Seq',Run='#Run',StepNo=str(chain['load_step']),Ret_Val='#LoadActive'),
                  call('F_PressDemoLoadPosition',Target='#LoadPosition',Run='#LoadActive',Reset='#Seq.SubReset',
                       OwnerIndex='#OwnerIndex',ChainIndex=str(chain['load_chain_index']),Delta='#Delta',**{r:'#'+r for r in roles},Ret_Val='#LoadDone')]
        leases.append(call('FRK_SeqSubStatus',Seq='#Seq',Child='#LoadPosition.Seq'))
    return begin+leases,leases


def step_ops(step,index,module):
    command = next(iter(step.get('commands',[])), None)
    awaiting = command[0]+'.'+command[1] if command else ('project.condition.'+step['wait'][0] if step.get('wait') else '')
    # A typed, private zero avoids the native LAD importer's time-literal
    # ambiguity. All languages use the same operand for an unguarded step.
    expected = '#'+step['delay'] if step.get('delay') else '#Seq.NoTimeGuard'
    time_class = Catalog.read().enums['E_TimeClass']['WAIT_OPERATOR' if step.get('policy') in ('AwaitCycle','ConfirmScrap','ModelSelected','ChangeoverAnswer') or 'StartLatched' in step.get('wait',[]) else 'WORK']
    operations=[call('FRK_SeqStep',StepNo=str(step['no']),StepName=literal(step['label']),
        AwaitingLabel=literal(awaiting),AwaitsPath='#'+command[0]+'.Status.Name' if command else "''",
        TimeClass=str(time_class),ExpectedTime=expected,Seq='#Seq',Row='#Row'+str(index))]
    ready=[]
    for role,command in step.get('commands',[]):
        assert role in ('PressRam','Door','PartSlide')
        name='F_CylinderExtendHandled' if step.get('handled') else next(c['api'] for c in module['commands'] if c['label']==command)
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
    policy=step.get('policy')
    if policy:
        name='F_PressDemo'+policy
        params={'Seq':'#Seq'}
        shared={'Cycle':'#Cycle','Core':'#Core','Unit':'#Unit','Status':'#Status','Part':'#Part','AlarmLog':'#AlarmLog'}
        if policy=='AwaitCycle':params.update(shared,PartPresent='#PartPresent',PartQuality='#PartQuality',AirPressureOk='#AirPressureOk',RequireTwoHandStart='#RequireTwoHandStart')
        elif policy=='Started':params.update({n:v for n,v in shared.items() if n not in ('Core','Cycle')})
        elif policy=='DoorClose':params.update(Closed=ready[0],TwoHandHeld='#TwoHandHeld',RequireTwoHandStart='#RequireTwoHandStart',SourcePath='#SourcePath',AlarmLog='#AlarmLog')
        elif policy=='ClearStart':params.update(Complete=ready[0])
        elif policy=='RamResult':params.update(Reached=ready[0],Cycle='#Cycle',AlarmLog='#AlarmLog')
        elif policy=='ConfirmScrap':params.update(SourcePath='#SourcePath',AlarmLog='#AlarmLog')
        elif policy in ('Scrap','CycleEnd'):params.update(shared)
        elif policy=='Dwell':params.update(TwoHandHeld='#TwoHandHeld',RequireTwoHandStart='#RequireTwoHandStart',PT='#PressSettleTime',Delta='#Delta',PressRam='#PressRam')
        elif policy=='Record':params.update(Dwell='#PressSettleTime',Core='#Core',Status='#Status',Part='#Part')
        elif policy=='ModelSelected':params.update(ModelCode='#ModelCode')
        elif policy=='ChangeoverAsk':params.update(SourcePath='#SourcePath',AlarmLog='#AlarmLog')
        elif policy=='ChangeoverAnswer':params.update(AlarmLog='#AlarmLog')
        else:raise ValueError('Unknown project policy '+policy)
        if policy not in ('Started','DoorClose','ClearStart','RamResult','ChangeoverAnswer'):
            params['Ret_Val']='#Ready5';ready=['#Ready5']
        operations.append((name,params))
    if not step.get('selects') and not step.get('complete'):
        # Keep return values separate from call power flow in native LAD.
        operations.append(call('FRK_SeqReady',Seq='#Seq',**{'Ok'+str(i):ready[i-1] if i<=len(ready) else 'TRUE' for i in range(1,6)}))
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


def graph_sources(chain,roles,module,sources,definition):
    graph_name='FB_GRAPH_'+chain['name']
    old_interface=interface(chain,roles)
    graph_steps=copy.deepcopy(chain['steps'])
    parallel=chain.get('process')=='auto'
    results=Catalog.read().enums['E_StepResult']
    advance,jump1=results['ADVANCE'],results['JUMP1']
    branches=definition['graph_auto']['branch_steps'] if parallel else {}
    if parallel:
        graph_steps += copy.deepcopy(definition['graph_auto']['auxiliary_steps'])
        old_interface['Static'] += [('Branch1','"FRK_SequenceCtx"'),('Branch2','"FRK_SequenceCtx"')]
        old_interface['Static'] += [('Row'+str(i),'"FRK_SequenceRow"') for i in range(len(chain['steps'])+1,len(graph_steps)+1)]
        next(st for st in graph_steps if st['no']==240)['next']=250
    scalar={'Bool':'BOOL','Time':'TIME','DInt':'DINT'}
    inout=[(n,scalar.get(t,t.strip('"'))) for kind,members in old_interface.items() if kind!='Input'
           for n,t in members if not n.startswith('At') and n not in ('Advance','LoadPosition','LoadActive')]
    host_names={'Core','Unit','Status','Part','AlarmLog'}
    inout=[('Host'+n if n in host_names else n,t) for n,t in inout]
    chart={'name':graph_name,'number':100,'inout':inout,'steps':[],
           'graph_settings':{'skip_steps':False}}
    for i,step in enumerate(graph_steps,1):
        operations,ready=step_ops(step,i,module);actions=[]
        seq='#Branch'+str(branches[str(step['no'])]) if str(step['no']) in branches else '#Seq'
        for name,parameters in operations:
            parameters={n:seq if v=='#Seq' else '#Host'+v[1:] if v[1:] in host_names else v for n,v in parameters.items()}
            actions.append({'text':GRAPH.call_text(name,list(parameters.items()))})
        for role,_ in step.get('commands',[]):
            actions.append({'text':GRAPH.call_text('F_CylinderRelease',[('Seq',seq),('Target','#'+role)]),'event':'S0'})
        chart['steps'].append({'no':step['no'],'label':step['label'],'next':step.get('next',step['no']),
                               'actions':actions,'when':{'eq':[seq+'.RetVal',advance]} if 'next' in step else ['FALSE']})
    # Native alternative and simultaneous branches follow the TC3 chart.
    if parallel:
        top={'branches':[{'number':n,'type':t,'cardinality':2} for n,t in
             [(1,'AltBegin'),(2,'SimBegin'),(3,'AltBegin'),(4,'AltEnd'),(5,'SimEnd')]],'transitions':[],'connections':[]}
        def connect(a,b,link='Direct'):
            # Siemens branch connection ports are zero based.
            for node in (a,b):
                if node[0]=='branch':node[3]-=1
            top['connections'].append({'from':a,'to':b,'link':link})
        def trans(n,expr):top['transitions'].append({'number':n,'when':expr})
        def eq(seq,value):return {'eq':['#'+seq+'.RetVal',value]}
        for step in graph_steps:
            no=step['no'];seq='Branch'+str(branches[str(no)]) if str(no) in branches else 'Seq'
            if no in (250,310):continue
            if no in (180,200):
                branch=1 if no==180 else 3
                connect(['step',no],['branch',branch,'In',1])
                for port,key,value in [(1,'next',advance),(2,'jump1',jump1)]:
                    number=no if port==1 else no+1;trans(number,eq(seq,value))
                    connect(['branch',branch,'Out',port],['transition',number])
                    if no==180 and port==1:
                        connect(['transition',number],['branch',2,'In',1])
                        connect(['branch',2,'Out',1],['step',200]);connect(['branch',2,'Out',2],['step',300])
                    else:connect(['transition',number],['step',step[key]])
                continue
            number=no or 1
            trans(number,eq(seq,advance) if 'next' in step else ['FALSE'])
            connect(['step',no],['transition',number])
            if no in (215,230):connect(['transition',number],['branch',4,'In',2 if no==215 else 1])
            else:connect(['transition',number],['step',step.get('next',no)],'Jump' if step.get('next',no)<=no else 'Direct')
        connect(['branch',4,'Out',1],['step',240])
        connect(['step',250],['branch',5,'In',1]);connect(['step',310],['branch',5,'In',2])
        trans(998,{'all':[eq('Branch1',advance),eq('Branch2',advance)]})
        connect(['branch',5,'Out',1],['transition',998]);connect(['transition',998],['step',999])
        chart['topology']=top
    reference=(ROOT/'Spikes/S11_Graph/reference/FB_GraphSample.xml').read_text('utf-8-sig')
    xml=GRAPH.generate(chart,reference)
    def hide_value_parameters(match):
        attrs='<AttributeList>'+''.join('<BooleanAttribute Name="'+flag+'" SystemDefined="true">false</BooleanAttribute>'
              for flag in ('ExternalAccessible','ExternalVisible','ExternalWritable'))+'</AttributeList>'
        return match[1]+re.sub(r'(<Member\b[^>]*?) />',
            lambda hit:hit[0] if '&quot;' in hit[1] else hit[1]+'>'+attrs+'</Member>',match[2])+match[3]
    xml=GRAPH.once(xml,r'(\n  <Section Name="InOut">\n)(.*?)(  </Section>\n)',hide_value_parameters,re.S)
    members=''.join('    <Member Name="'+n+'" Datatype="'+scalar.get(t,t)+'" />\n'
                    for n,t in old_interface['Input'])
    xml=GRAPH.once(xml,r'(\n  <Section Name="Input">\n.*?)(  </Section>\n)',
                   lambda m:m[1]+members+m[2],re.S)
    sources['27_'+graph_name+'.xml']=xml
    owner_intf=copy.deepcopy(old_interface);owner_intf['InOut'].append(('Chart','"'+graph_name+'"'))
    before,after=frame_ops(chain,roles,graph=True)
    if parallel:
        before=[op for op in before if op[0] not in ('F_CylinderSequenceLease','FRK_SeqSubActive','F_PressDemoLoadPosition','FRK_SeqOwnerStatus','FRK_SeqSubStatus')]
        for branch in (1,2):before.append(call('FRK_SeqGraphBegin',Run='#Run',Reset='#Reset',OwnerIndex='#OwnerIndex',ChainIndex=str(chain['chain_index']),BranchIndex=str(branch),ViewOffset='0',ViewDepth='0',Delta='#Delta',Seq='#Branch'+str(branch)))
        before += [call('FRK_SeqSubActive',Seq='#Branch1',Run='#Run',StepNo='240',Ret_Val='#LoadActive'),
                   call('F_PressDemoLoadPosition',Target='#LoadPosition',Run='#LoadActive',Reset='#Seq.SubReset',OwnerIndex='#OwnerIndex',ChainIndex=str(chain['load_chain_index']),Delta='#Delta',**{r:'#'+r for r in roles},Ret_Val='#LoadDone')]
        before += [call('F_CylinderSequenceLease',Seq=seq,Target='#'+r) for seq in ('#Seq','#Branch1','#Branch2') for r in roles]
        after=[call('FRK_SeqSubStatus',Seq='#Branch1',Child='#LoadPosition.Seq')]
        after += [call('FRK_SeqOwnerStatus',Seq=seq,Core='#Core',Status='#Status') for seq in ('#Branch1','#Branch2','#Seq')]
        after += [call('F_CylinderSequenceLease',Seq=seq,Target='#'+r) for seq in ('#Seq','#Branch1','#Branch2') for r in roles]
    text=header('FB_'+chain['name']+'GraphOwner',owner_intf)
    text+='\n'.join('    '+scl_call(op) for op in before)+'\n'
    params=[(n,'#'+(n[4:] if n.startswith('Host') else n)) for n,t in old_interface['Input']+inout]
    params += [('INIT_SQ','#Seq.Restart AND #Seq.Running'),('OFF_SQ','NOT #Seq.Running')]
    text+='    IF NOT #Seq.Frozen OR #Seq.RestartPending THEN\n        #Chart('+', '.join(n+' := '+v for n,v in params)+');\n    END_IF;\n'
    text+='\n'.join('    '+scl_call(op) for op in after)+'\nEND_FUNCTION_BLOCK\n'
    sources['28_FB_'+chain['name']+'GraphOwner.scl']=text


def sensor_module(folder, stem, catalog):
    """One passive sensor CM: its declaration, records and bound logic regions."""
    module=json.loads((CONTROL_MODULES/folder/(stem+'.json')).read_bytes())
    reasons=(GEN.REPO/TC3_MODULE_REASONS).read_text('utf-8-sig')
    template=(CONTROL_MODULES/folder/(stem+'_logic.scl.in')).read_text('ascii')
    # Module band reasons have one source: the TC3 module reason list.
    tokens={name:int(re.search(name+r'\s*:\s*DINT\s*:=\s*(\d+)',reasons)[1])
            for name in set(re.findall(r'@([A-Z][A-Z_]+)@',template))}
    pieces=re.split(r'@REGION:(\w+)@\n',bind(template,catalog,tokens))[1:]
    records=module.pop('records')
    module['logic']=dict(zip(pieces[::2],pieces[1::2]));module['children']=[]
    return module,records


def unit_policy(catalog):
    busy=catalog.enums['E_ExecState']['BUSY'];auto=catalog.enums['E_Mode']['AUTO'];home=catalog.enums['E_Mode']['HOME']
    changeover=catalog.enums['E_Mode']['CHANGEOVER']
    return {
      'Release':'    "FRK_UnitSetPermit"(Unit := #Unit, Ok := #Hal.Process.AirPressureOk, Diag := #Hal.Process.PermitDiagnostic);',
      'Cyclic':'''    // The monitor CM owns air availability; the Unit's release function
    // receives only its HAL, so the Unit hands the derived fact across here.
    #Hal.Process.AirPressureOk := #AirPressureMonitor.OutImm.PressureOk;
    #Release(AirPressureOk := #Hal.Process.AirPressureOk, DoorClosed := #Hal.Door.FeedbackExtended AND NOT #Hal.Door.FeedbackRetracted,
        SlideInside := #Hal.PartSlide.FeedbackExtended AND NOT #Hal.PartSlide.FeedbackRetracted, RamHealthy := NOT #PressRam.Error AND NOT #PressRam.Aborted,
        DoorHealthy := NOT #Door.Error AND NOT #Door.Aborted, SlideHealthy := NOT #PartSlide.Error AND NOT #PartSlide.Aborted,
        TwoHandHeld := #TwoHand.OutImm.SafeActive OR NOT #StationCfg.RequireTwoHandStart);
    #Hal.Process.PermitDiagnostic := "FRK_UnitScratch".EmptyDiagnostic;
    #Hal.Process.PermitDiagnostic.Description := STRING_TO_WSTRING(#Release.ModeStart.Blocker);
    #Hal.Process.PermitDiagnostic.SourcePath := STRING_TO_WSTRING(#Status.Name);
    #Hal.PressRam.ExtendPermit := #Release.RamExtend.Permit;
    #Hal.PressRam.RetractPermit := #Hal.Process.AirPressureOk;
    #Hal.PressRam.PermitDiagnostic := "FRK_UnitScratch".EmptyDiagnostic;
    #Hal.PressRam.PermitDiagnostic.Description := STRING_TO_WSTRING(#Release.RamExtend.Blocker);
    #Hal.PressRam.PermitDiagnostic.SourcePath := STRING_TO_WSTRING(#Status.Name);
    #Hal.PressRam.RetractDiagnostic := #Hal.Process.PermitDiagnostic;
    #Hal.Door.PermitDiagnostic := #Hal.Process.PermitDiagnostic;
    #Hal.Door.RetractDiagnostic := #Hal.Process.PermitDiagnostic;
    #Hal.PartSlide.PermitDiagnostic := #Hal.Process.PermitDiagnostic;
    #Hal.PartSlide.RetractDiagnostic := #Hal.Process.PermitDiagnostic;
    #Hal.Door.ExtendPermit := #Hal.Process.AirPressureOk;
    #Hal.Door.RetractPermit := #Hal.Process.AirPressureOk;
    #Hal.PartSlide.ExtendPermit := #Hal.Process.AirPressureOk;
    #Hal.PartSlide.RetractPermit := #Hal.Process.AirPressureOk;''',
      'Sequences':'''    // Project policy: each accepted Start restarts the whole press chain.
    #SequenceReset := #Core.EvCommandStart;
    #Auto(Run := #Core.Exec = @BUSY@ AND #Unit.Mode = @AUTO@ AND NOT "FRK_Registry".Fault,
        Reset := #SequenceReset, OwnerIndex := #Core.RegIndex, Delta := DINT_TO_TIME(UDINT_TO_DINT(#Core.DeltaMs)),
        PartPresent := #PartPresentSensor.OutImm.Value AND #PartPresentSensor.OutImm.Quality,
        PartQuality := #Hal.Process.PartQuality,
        AirPressureOk := #AirPressureMonitor.OutImm.PressureOk, TwoHandHeld := #TwoHand.OutImm.SafeActive,
        StartPulse := #TwoHand.OutImm.StartPulse, RequireTwoHandStart := #StationCfg.RequireTwoHandStart,
        TransferSettleTime := #ParCfg.TransferSettleTime, PressSettleTime := #ParCfg.PressSettleTime,
        SourcePath := #Status.Name, PressRam := #PressRam, Door := #Door, PartSlide := #PartSlide,
        Core := #Core, Unit := #Unit, Status := #Status, Part := #Part, AlarmLog := #AlarmLog,
        Chart := "GDB_GRAPH_PressDemoAuto");
    #Home(Run := #Core.Exec = @BUSY@ AND #Unit.Mode = @HOME@ AND NOT "FRK_Registry".Fault,
        Reset := #SequenceReset, OwnerIndex := #Core.RegIndex, Delta := DINT_TO_TIME(UDINT_TO_DINT(#Core.DeltaMs)),
        PressRam := #PressRam, Door := #Door, PartSlide := #PartSlide, Chart := "GDB_GRAPH_PressDemoHome");
    "FRK_SeqOwnerStatus"(Seq := #Home.Seq, Core := #Core, Status := #Status);
    IF #Home.Seq.Done AND #Core.Exec = @BUSY@ AND #Unit.Mode = @HOME@ THEN
        "FRK_Complete"(Core := #Core, Status := #Status);
    END_IF;
    #Changeover(Run := #Core.Exec = @BUSY@ AND #Unit.Mode = @CHANGEOVER@ AND NOT "FRK_Registry".Fault,
        Reset := #SequenceReset, OwnerIndex := #Core.RegIndex, Delta := DINT_TO_TIME(UDINT_TO_DINT(#Core.DeltaMs)),
        ModelCode := #Model.ModelCode, SourcePath := #Status.Name,
        PressRam := #PressRam, Door := #Door, PartSlide := #PartSlide, AlarmLog := #AlarmLog);
    "FRK_SeqOwnerStatus"(Seq := #Changeover.Seq, Core := #Core, Status := #Status);
    IF #Changeover.Seq.Done AND #Core.Exec = @BUSY@ AND #Unit.Mode = @CHANGEOVER@ THEN
        // A command result: it stands until the next command replaces it.
        #OutCmd.ChangeoverCompleted := TRUE;
        "FRK_Complete"(Core := #Core, Status := #Status);
    END_IF;
    #OutCmd.CycleCompleted := #Auto.Cycle.CycleCompleted;'''.replace('@BUSY@',str(busy)).replace('@AUTO@',str(auto)).replace('@HOME@',str(home)).replace('@CHANGEOVER@',str(changeover)),
      'CommandStart':'    #OutCmd.ChangeoverCompleted := FALSE;'}


def wire_demo(sources,definition,catalog):
    name=next(n for n in sources if n.startswith('20_') and 'FB_PressDemoUnit' in n)
    text=sources.pop(name)
    anchor='    Unit'+PRIVATE+' : "FRK_Unit";'
    assert text.count(anchor)==1
    text=text.replace(anchor,anchor+'\n    Auto'+READONLY+' : "FB_PressDemoAutoGraphOwner";\n    Home'+READONLY+' : "FB_PressDemoHomeGraphOwner";\n    Changeover'+READONLY+' : "FB_PressDemoChangeover";\n    Release'+READONLY+' : "FB_PressDemoRelease";\n    SequenceReset'+PRIVATE+' : Bool;')
    sources['29_FB_PressDemoUnit.scl']=text
    if '23_PersistQuiesce.scl' in sources:
        sources['29_PersistQuiesce.scl']=sources.pop('23_PersistQuiesce.scl')
    for chain in definition['chains']:
        if chain.get('language','GRAPH')!='GRAPH':continue
        name='GDB_GRAPH_'+chain['name']
        sources['29_'+name+'.db']='\n'.join(['DATA_BLOCK "'+name+'"',"{ S7_Optimized_Access := 'TRUE' }",'VERSION : 0.1','NON_RETAIN','"FB_GRAPH_'+chain['name']+'"','BEGIN','END_DATA_BLOCK',''])
    for old in list(sources):
        if old.startswith('25_'):sources['29_'+old[3:].replace('GDB_FraktalHal','GDB_PressDemoHal')]=sources.pop(old)
    simulate=definition['integration']['simulate_feedback']
    sources['38_PressDemoHardwareDriver.scl']=bind((EXAMPLE/'hardware_driver.scl.in').read_text('ascii'),catalog,
        {'USE_SIMULATION':'TRUE' if simulate else 'FALSE'})
    main=sources['40_Main.scl'];anchor='    "GDB_FraktalMain"(Startup := #Initial_Call);'
    main=main.replace(anchor,'    "F_PressDemoReadInputs"();\n'+anchor+'\n    "F_PressDemoWriteOutputs"();')
    sources['40_Main.scl']=main
    sources['30_PressDemoComposition.scl']=sources.pop('30_FB_FraktalMain.scl')
    sources['35_GDB_PressDemoMain.db']=sources.pop('35_GDB_FraktalMain.db')
    sources['40_PressDemoMain.scl']=sources.pop('40_Main.scl')


def build():
    definition=json.loads((EXAMPLE/'press.json').read_bytes());module=json.loads((MODULES/'cylinder.json').read_bytes())
    catalog=Catalog.read();width=DECL.CoreFacts.read().key_width
    records=copy.deepcopy(module['records'])
    records['ST_SequenceCommandLease']='STRUCT OwnerIndex : DINT; ChainIndex : DINT; BranchIndex : DINT; Step : DINT; Raised : BOOL; AbortIssued : BOOL; ReleasedScan : UDINT; END_STRUCT'
    # model_fields declares the whole record, the Unit's mode-switch Timeout
    # included: a model change is migrate-or-fault over every member.
    records.update({'ST_PressDemoParCfg':'STRUCT SchemaVersion : UINT := 2; '+
                        ''.join(f['name']+' : '+f['type']+' := '+f['default']+'; ' for f in definition['model_fields'])+'END_STRUCT',
                    'ST_PressDemoParCmd':'STRUCT Reserved : BOOL; END_STRUCT',
                    'ST_PressDemoOutCmd':'STRUCT CycleCompleted : BOOL; ChangeoverCompleted : BOOL; END_STRUCT',
                    'ST_PressDemoOutImm':'STRUCT Homed : BOOL; TwoHandStartReady : BOOL; END_STRUCT'})
    cm={k:v for k,v in module.items() if k not in ('records',)}
    cm['commands']=[{k:v for k,v in c.items() if k!='api'} for c in cm['commands']]
    command_ids={c['label']:c['id'] for c in module['commands']}
    logic=bind((MODULES/'cylinder_logic.scl.in').read_text('ascii'),catalog,command_ids)
    pieces=re.split(r'@REGION:(\w+)@\n',logic)[1:]
    cm['logic']=dict(zip(pieces[::2],pieces[1::2]));cm['children']=[]
    sensors=[sensor_module(folder,stem,catalog) for folder,stem in SENSOR_MODULES]
    for _,sensor_records in sensors:records.update(sensor_records)
    assert {s['type'] for s in definition['sensors']}<={s['name'] for s,_ in sensors},'press sensor names an undeclared module type'
    owner={'name':'FB_PressDemoUnit','tier':'UNIT','type_key':'project.pressDemo','children':[{'name':r,'type':module['name']} for r in definition['roles']]+
           [{'name':s['name'],'type':s['type']} for s in definition['sensors']],
           'contract':{k:'ST_PressDemo'+k for k in ('ParCfg','ParCmd','OutCmd','OutImm')},
           'commands':[{'id':1,'label':'Run'}],'timeout':'Timeout',
           'unit':{'modes':['AUTO','MANUAL','HOME','CHANGEOVER'],'initial':'MANUAL','run_command':1}}
    records['ST_PressDemoStationCfg']='STRUCT SchemaVersion : UINT := 1; '+''.join(f["name"]+' : '+f["type"]+' := '+f["default"]+'; ' for f in definition['station_config'])+'END_STRUCT'
    owner['station_config']='ST_PressDemoStationCfg'
    owner['sequence_view']=definition['sequence_view']
    owner['logic']=unit_policy(catalog)
    owner['config']=[{'member':role+'.'+f['name'],'revision':1,**{k:v for k,v in f.items() if k in ('key','label','minimum','maximum')}}
                     for role,group in (('StationCfg','station_config'),('ParCfg','model_fields')) for f in definition[group]]
    owner['logic']['cyclic'] = """    #OutImm.Homed := "FRK_State"(Idx := 1, Key := 'project.state.pressAtLoadPosition',
        Ok := #PressRam.OutImm.Retracted AND #Door.OutImm.Retracted AND #PartSlide.OutImm.Retracted);
    // The start lamp's condition, derived where the facts live; the hardware
    // driver only maps it to the output.
    #OutImm.TwoHandStartReady := "FRK_State"(Idx := 2, Key := 'project.state.pressTwoHandStartReady',
        Ok := #TwoHand.OutImm.Armed AND #PartPresentSensor.OutImm.Value AND #PartPresentSensor.OutImm.Quality
            AND #AirPressureMonitor.OutImm.PressureOk);"""
    declaration={'schema_version':1,'target_family':'S7-1500','registry_capacity':4+len(definition['sensors']),'types':[owner,cm,*(s for s,_ in sensors)],
                 'roots':[{'name':'PressDemo','type':'FB_PressDemoUnit'}],'records':records}
    if definition.get('model_config'):
        declaration['model_config']=definition['model_config']
    if definition.get('config_sets'):
        declaration['config_sets']=definition['config_sets']
    if definition.get('alarm_history'):
        declaration['alarm_history']=definition['alarm_history']
    if definition.get('alarm_recovery'):
        declaration['alarm_recovery']=definition['alarm_recovery']
    if definition.get('alarm_delivery'):
        declaration['alarm_delivery']=definition['alarm_delivery']
    if definition.get('persistence'):
        declaration['persistence']=definition['persistence']
    sources,manifest=GEN.build(DECL.validate(declaration),True)
    # The complete package includes the composition root, chart DBs and one
    # hardware-driver boundary. Optional ST/LAD twins have no instances.
    signals=[('PartQuality','Bool'),('AirPressureOk','Bool'),('PermitDiagnostic','"ST_Diagnostic"')]
    sources['00_000a_ST_PressDemoSignals.udt']=udt('ST_PressDemoSignals',signals)
    for name in sources:
        if 'ST_PressDemoUnitHal' in name:
            sources[name]=sources[name].replace('END_STRUCT','    Process'+PRIVATE+' : "ST_PressDemoSignals";\nEND_STRUCT')
    fields=[('RunPrevious','Bool'),('Running','Bool'),('Restart','Bool'),('Done','Bool'),('Error','Bool'),
            ('Initialized','Bool'),('Frozen','Bool'),('ResumePending','Bool'),('RestartPending','Bool'),('Rearm','Bool'),('SubReset','Bool'),
            ('RestartEpoch','UDInt'),('ResumeEpoch','UDInt'),
            ('Pending','Bool'),('StartLatched','Bool'),('OwnerIndex','DInt'),('ChainIndex','DInt'),
            ('Step','DInt'),('ScanStep','DInt'),('RecordedStep','DInt'),('RetVal','DInt'),('Scan','UDInt'),
            ('Visit','UDInt'),('Elapsed','Time'),('DelayElapsed','Time'),
            ('StepName',next(f['native_type'] for f in catalog.resolve(['ST_StepRecord'])['ST_StepRecord'] if f['member']=='StepName')),
            ('Awaiting',next(f['native_type'] for f in catalog.resolve(['ST_StepRecord'])['ST_StepRecord'] if f['member']=='AwaitingLabel')),
            ('ErrorDiagnostic','"ST_Diagnostic"'),('BranchIndex','DInt'),('ViewOffset','DInt'),('ViewDepth','Int'),('NoTimeGuard','Time'),
            ('CommandFailed','Bool'),('CommandIssued','Bool'),('Warned','Bool'),('HandledDiagnostic','"ST_Diagnostic"'),
            ('EventVisit','UDInt'),('EventToken','DInt')]
    sources['06_FRK_SequenceCtx.udt']=udt('FRK_SequenceCtx',fields,
        ('Running','Done','Error','Pending','Step','Elapsed','StepName','Awaiting','ErrorDiagnostic'))
    sources['06_FRK_SequenceRow.udt']=udt('FRK_SequenceRow',[('StepNo','DInt'),('Visited','Bool'),('LastDuration','Time')],('StepNo','Visited','LastDuration'))
    record_fields={f['member']:f['native_type'] for f in catalog.resolve(['ST_MeasRecord'])['ST_MeasRecord']}
    record_widths={'RECORD_NAME_WIDTH':int(re.search(r'\[(\d+)\]',record_fields['Name'])[1]),
                   'RECORD_UNIT_WIDTH':int(re.search(r'\[(\d+)\]',record_fields['Unit'])[1])}
    sources['16_SequenceServices.scl']=bind((CORE/'sequence_services.scl.in').read_text('ascii')+'\n'+
        (CORE/'sequence_branches.scl.in').read_text('ascii'),catalog,{**catalog.capacities,**record_widths})
    sources['22_CylinderApi.scl']=bind((MODULES/'cylinder_api.scl.in').read_text('ascii'),catalog,
                                    {**command_ids,'READY':catalog.enums['E_ExecState']['READY']})
    release_sources(definition,sources,width)
    sources['06_ST_PressDemoCycle.udt']=udt('ST_PressDemoCycle',[(n,t) for n,t in
        [('PartInMachine','Bool'),('PartDispositioned','Bool'),('CycleCompleted','Bool'),('FailureReason','DInt')]])
    reason_path=GEN.REPO/'FraktalCore/PLC/TwinCAT/Examples/PressDemo/Fraktal_Press_Demo/01_PneumaticPress/PL_PressReasons.TcGVL'
    reason=int(re.search(r'PRESS_TWO_HAND_RELEASED\s*:\s*DINT\s*:=\s*(\d+)',reason_path.read_text('utf-8-sig'))[1])
    sources['22_PressDemoAutoServices.scl']=bind((EXAMPLE/'auto_services.scl.in').read_text('ascii'),catalog,{'PRESS_TWO_HAND_RELEASED':reason,'MAX_PRESS_DWELL_MS':next(f['maximum'] for f in definition['model_fields'] if f['name']=='PressSettleTime')})
    for chain in [definition['load_position'],*definition['chains']]:
        sigs=signatures(sources)
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
                text+='                "FRK_SeqRoute"(Seq := #Seq, OnAdvance := '+str(step['next'])+', OnJump1 := '+str(step.get('jump1',-1))+');\n'
            text+='            END_IF;\n'
            at='#At'+str(step['no']);ladder.call('FRK_SeqAt',{'Seq':'#Seq','StepNo':str(step['no']),'Ret_Val':at})
            for op in operations:ladder.call(*op,gate=at)
            if 'next' in step:
                ladder.call('FRK_SeqRoute',{'Seq':'#Seq','OnAdvance':str(step['next']),'OnJump1':str(step.get('jump1',-1))},gate=at)
        # The shared begin service parks an idle chain at step 0; a chain
        # without a step 0 (the load-position sub-chain) must not fault there.
        text+='        ELSE\n            IF #Seq.Running AND NOT #Seq.Error THEN\n                #Seq.Error := TRUE;\n'
        text+='                #Seq.ErrorDiagnostic.ReasonCode := '+str(definition['invalid_step_reason'])+';\n'
        text+="                #Seq.ErrorDiagnostic.Description := WSTRING#'project.sequence.invalidStep';\n            END_IF;\n"
        text+='    END_CASE;\n'+'\n'.join('    '+scl_call(op) for op in after)+'\nEND_FUNCTION_BLOCK\n'
        for op in after:ladder.call(*op)
        if chain is definition['load_position']:
            wrapper='''FUNCTION "F_PressDemoLoadPosition" : Bool
{ S7_Optimized_Access := 'TRUE' }
VERSION : 0.1
VAR_INPUT Run : Bool; Reset : Bool; OwnerIndex : DInt; ChainIndex : DInt; Delta : Time; END_VAR
VAR_IN_OUT Target : "FB_PressDemoLoadPosition"; PressRam : "FB_CylinderCM"; Door : "FB_CylinderCM"; PartSlide : "FB_CylinderCM"; END_VAR
BEGIN
    // Each embedding chain passes its own identity, so two owners of the one
    // motion chain never share a command lease.
    #Target(Run := #Run, Reset := #Reset, OwnerIndex := #OwnerIndex, ChainIndex := #ChainIndex, Delta := #Delta, PressRam := #PressRam, Door := #Door, PartSlide := #PartSlide);
    #F_PressDemoLoadPosition := #Target.Seq.Done;
END_FUNCTION
'''
            sources['23_00_'+name+'.scl']=text+wrapper
        else:
            sources['23_'+name+'.scl']=text
            if chain.get('language','GRAPH')=='GRAPH':
                graph_sources(chain,definition['roles'],module,sources,definition)
        sources['26_FB_LD_'+chain['name']+'.xml']=ladder.text()
    wire_demo(sources,definition,catalog)
    return sources,definition,manifest


def generate(out):
    sources,definition,manifest=build()
    out.mkdir(parents=True,exist_ok=False)
    for name,text in sources.items():(out/name).write_bytes(text.encode('ascii'))
    data={'kind':'fraktal.tia.press.examples.v1','wired':True,'definition':definition,
          'generator_version':manifest['generator_version'],'runtime':manifest['runtime'],
          'generated':{n:hashlib.sha256(t.encode('ascii')).hexdigest() for n,t in sources.items()},
          'core_inputs':manifest['core_inputs']}
    (out/'manifest.json').write_bytes((json.dumps(data,indent=2)+'\n').encode('ascii'))
    return len(sources)


def verify(out,native=None):
    import fraktal_tia_ld as LD
    sources,definition,manifest=build()
    recorded=json.loads((out/'manifest.json').read_bytes())
    assert recorded['definition']==definition and recorded['core_inputs']==manifest['core_inputs'],'Changed authoritative inputs'
    assert recorded['generator_version']==manifest['generator_version'] and recorded['runtime']==manifest['runtime'],'Changed runtime selection'
    assert recorded['generated']=={n:hashlib.sha256(t.encode('ascii')).hexdigest() for n,t in sources.items()},'Generated manifest differs from replay'
    located={}
    for name,text in sources.items():
        hits=list(out.rglob(name));assert len(hits)==1,(name,'missing or duplicate generated source')
        assert hits[0].read_bytes()==text.encode('ascii'),(name,'source differs from replay')
        located[name]=hits[0]
    result={'replayed_sources':len(sources),'wired':True,'ladder':{},'graph':{}}
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
