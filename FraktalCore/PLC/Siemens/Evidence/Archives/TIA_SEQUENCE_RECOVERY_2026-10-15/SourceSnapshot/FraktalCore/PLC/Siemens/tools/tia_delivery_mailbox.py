"""Metadata-only receipt capability; independent of the operator command mailbox."""
import time
from tia_webapi import leaf_var
from fraktal_tia_event_delivery import POLICY
import json
KINDS=json.loads(POLICY.read_bytes())['request_kinds']

class ReceiptMailbox:
    def __init__(self,api,guard,emit):self.api,self.guard,self.emit=api,guard,emit
    def read(self,path):return self.api.call('PlcProgram.Read',dict(var=leaf_var(path.split('.'))))
    def request(self,kind,root='StationA',**fields):
        if kind not in KINDS.values():raise ValueError('Only event delivery receipts are supported')
        count=int(self.read('FRK_EventDeliveryReceipt.Count'))
        slot=next((i for i in range(1,count+1) if self.read('FRK_EventDeliveryReceipt.Roots['+str(i)+']')==root),0)
        if not slot:raise ValueError('Root has no event delivery capability')
        prefix='FRK_EventDeliveryReceipt.Request['+str(slot)+']'
        sequence=(int(self.read(prefix+'.Sequence'))+1)&0xffffffff or 1
        values=dict(SchemaVersion=1,TargetPath=fields.get('TargetPath',''),Token=fields.get('NameValue',''),Checksum=fields.get('DurationMs',0),DiscardLost=fields.get('BoolValue',False),Epoch=0,StreamId='')
        if kind==KINDS['DISCARD_LOST_EVENT_DELIVERY']:
            values.update(Token='',Epoch=int(fields.get('NameValue','0')),StreamId=fields.get('TextValue',''))
        self.emit(dict(event='receipt-argument-guard',root=root,status=self.guard()))
        replies=self.api.bulk([('PlcProgram.Write',dict(var=leaf_var((prefix+'.'+name).split('.')),value=value)) for name,value in values.items()])
        if any(error for value,error in replies):raise RuntimeError('Receipt argument write refused')
        self.emit(dict(event='receipt-commit-guard',root=root,sequence=sequence,status=self.guard()))
        self.api.call('PlcProgram.Write',dict(var=leaf_var((prefix+'.Sequence').split('.')),value=sequence))
        response='FRK_EventDeliveryReceipt.Response['+str(slot)+']'
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if self.read(response+'.AckSequence')==sequence:return self.read(response+'.Accepted')
            time.sleep(.02)
        raise TimeoutError('Delivery receipt not acknowledged; no replay')
