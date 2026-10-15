"""Complete root request commit/acknowledgement, with no write replay."""
import time
from tia_webapi import leaf_var
from fraktal_tia_binding import Catalog

class Mailbox:
    def __init__(self,api,guard,emit):self.api,self.guard,self.emit=api,guard,emit
    def read(self,path):return self.api.call('PlcProgram.Read',{'var':leaf_var(path.split('.'))})
    def request(self,kind,root='StationA',**fields):
        self.emit({'event':'mutation-guard','kind':kind,'root':root,'status':self.guard()})
        sequence=(int(self.read(root+'.HmiRequest.Sequence'))+1)&0xffffffff or 1
        value=Catalog.read().enums['E_HmiRequestKind'][kind] if isinstance(kind,str) else kind
        values=dict(Kind=value,TargetPath='',NameValue='',TextValue='',IntValue=0,BoolValue=False,DurationMs=0,User='',Secret='')
        if set(fields)-set(values):raise ValueError('Unknown mailbox argument')
        values.update(fields)
        results=self.api.bulk([('PlcProgram.Write',{'var':leaf_var((root+'.HmiRequest.'+n).split('.')),'value':v}) for n,v in values.items()])
        if any(error for value,error in results):raise RuntimeError('Mailbox argument write refused')
        self.emit({'event':'commit-guard','root':root,'sequence':sequence,'status':self.guard()})
        self.api.call('PlcProgram.Write',{'var':leaf_var([root,'HmiRequest','Sequence']),'value':sequence})
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if self.read(root+'.HmiResponse.AckSequence')==sequence:return self.read(root+'.HmiResponse.Accepted')
            time.sleep(.02)
        raise TimeoutError('Mailbox acknowledgement timeout; request not replayed')
