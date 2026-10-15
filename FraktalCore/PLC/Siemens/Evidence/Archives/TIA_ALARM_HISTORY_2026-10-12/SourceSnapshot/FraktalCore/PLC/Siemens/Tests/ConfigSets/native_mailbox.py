"""Shared native mailbox harness for additional set acceptance checks."""
import time
from tia_webapi import leaf_var
from fraktal_tia_binding import Catalog
class Mailbox:
    def __init__(self,api,guard,emit):self.api,self.guard,self.emit=api,guard,emit
    def read(self,path):return self.api.call('PlcProgram.Read',{'var':leaf_var(path.split('.'))})
    def request(self,kind,root='StationA',**fields):
        self.emit({'event':'mutation-guard','kind':kind,'root':root,'status':self.guard()})
        sequence=(int(self.read(root+'.HmiRequest.Sequence'))+1)&0xffffffff or 1
        values=dict(Kind=Catalog.read().enums['E_HmiRequestKind'][kind],TargetPath='',NameValue='',TextValue='',IntValue=0,BoolValue=False,DurationMs=0,User='',Secret='');values.update(fields)
        results=self.api.bulk([('PlcProgram.Write',{'var':leaf_var((root+'.HmiRequest.'+n).split('.')),'value':v}) for n,v in values.items()])
        assert not any(error for value,error in results)
        self.api.call('PlcProgram.Write',{'var':leaf_var([root,'HmiRequest','Sequence']),'value':sequence})
        deadline=time.monotonic()+8
        while time.monotonic()<deadline:
            if self.read(root+'.HmiResponse.AckSequence')==sequence:return self.read(root+'.HmiResponse.Accepted')
            time.sleep(.02)
        raise AssertionError('native mailbox timeout')
