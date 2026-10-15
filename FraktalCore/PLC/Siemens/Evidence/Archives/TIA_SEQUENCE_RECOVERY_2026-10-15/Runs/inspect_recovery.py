import json, os, sys
from pathlib import Path
sys.path.insert(0, 'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/tools')
from tia_webapi import WebApi, leaf_var
api = WebApi('169.254.212.49', Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/FrkS12.webapi.pin', False)
paths = ['StationA.Status.State', 'StationA.Status.Diagnostic.ReasonCode', 'StationA.Status.Diagnostic.Description',
         'StationA.Cell.Clamp.Status.State', 'StationA.Cell.Clamp.Execute', 'StationA.Cell.Clamp.Abort',
         'GDB_RecoveryTest.Seq.Step', 'GDB_RecoveryTest.Seq.Error', 'GDB_RecoveryTest.Running',
         'GDB_RecoveryTest.EntryCount', 'GDB_RecoveryTest.IssueCount', 'GDB_RecoveryTest.Frozen',
         'GDB_RecoveryTest.ResumePending', 'GDB_RecoveryTest.Delay', 'GDB_RecoveryTest.AckSeq',
         'GDB_GRAPH_RecoveryTest.S_NO', 'GDB_GRAPH_RecoveryTest.ERR_FLT', 'GDB_GRAPH_RecoveryTest.OFF_SQ']
try:
    api.login('fraktal')
    values = dict(zip(paths, api.bulk([('PlcProgram.Read', {'var': leaf_var(p.split('.'))}) for p in paths])))
    text = json.dumps(values, indent=2)+'\n'
    Path(sys.argv[1]).write_text(text, encoding='ascii')
    print(text)
finally:
    api.conn.close()
