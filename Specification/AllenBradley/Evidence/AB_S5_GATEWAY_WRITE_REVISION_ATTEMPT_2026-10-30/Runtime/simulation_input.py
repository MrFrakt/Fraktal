"""Two fixed DINT writes at most: AirOk=1 and exact original restoration on Echo."""
from pathlib import Path
import json,os,subprocess,sys
from s5_session import authorize
D=Path(__file__).parent
TAG='FRK_Press_AirOk'

def change(comm,directory,operation):
    def read():
        answer=comm.Read(TAG)
        if answer.Status!='Success' or type(answer.Value) is not int or answer.Value not in (0,1):
            raise ValueError('Expected a successful fixed DINT simulation input')
        return answer.Value
    saved=directory/'simulation_original.json'
    if operation=='prepare':
        if saved.exists():raise ValueError('Single-use simulation preparation already exists')
        original=read()
        with saved.open('x',encoding='utf-8') as stream:
            json.dump(dict(serial='601FC87B',tag=TAG,original=original,temporary=1),stream,indent=2)
        comm.Write(TAG,1)
        if read()!=1:raise ValueError('Simulation input did not apply')
    elif operation=='restore':
        value=json.loads(saved.read_bytes())
        if value['serial']!='601FC87B' or value['tag']!=TAG or type(value['original']) is not int or value['original'] not in (0,1):
            raise ValueError('Unexpected simulation restoration scope')
        comm.Write(TAG,value['original'])
        if read()!=value['original']:raise ValueError('Simulation input restoration mismatch')
        with (directory/'simulation_restored.json').open('x',encoding='utf-8') as stream:
            json.dump(dict(passed=True,serial='601FC87B',tag=TAG,original=value['original'],restored=read()),stream)
    else:raise ValueError('Unsupported simulation operation')

def main():
    if sys.argv[1:] not in (['prepare'],['restore']):raise ValueError('Fixed prepare/restore operation required')
    authorize(json.loads((D/'authorization.json').read_bytes()))
    subprocess.run([sys.executable,str(D/'scripts/guard_echo.py')],check=True)
    os.environ['FRAKTAL_AB_DECLARATION']='fraktal_ab_genealogy_s4b_owner_demo'
    sys.path.insert(0,'C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
    from pylogix import PLC
    from fraktal_ab_part_execute import Guarded
    import fraktal_ab_station as station
    app=station.application()
    if TAG not in app.sim_inputs:raise ValueError('Fixed tag is not a declared simulation input')
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,5
        comm=Guarded(native,0x601FC87B,app);comm.guard()
        change(comm,D,sys.argv[1])
    print(json.dumps(dict(passed=True,tag=TAG,operation=sys.argv[1],fixedWrites=1)))
if __name__=='__main__':main()
