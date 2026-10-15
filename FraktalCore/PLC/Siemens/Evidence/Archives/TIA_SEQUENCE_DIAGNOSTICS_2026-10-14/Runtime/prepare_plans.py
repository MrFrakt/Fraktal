from pathlib import Path
import os,sys
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Siemens/tools'))
from fraktal_tia_program_layout import organize
import fraktal_tia_examples as EX
stations=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations'
runtime=stations/'Sequence_Diagnostics_Runtime_20261014/FrkS12/FrkS12.ap20'
press=stations/'Sequence_Diagnostics_Press_Offline_20261014/FrkS12/FrkS12.ap20'
organize(WORK/'candidate_02',WORK/'runtime_grouped_02',runtime,WORK/'runtime_export_02')
EX.generate(WORK/'press_01')
organize(WORK/'press_01',WORK/'press_grouped_01',press,WORK/'press_export_01')
(WORK/'download.plan').write_text('open-project --path "'+str(runtime)+'"\n${download}\nsave\n',encoding='ascii')
print('Prepared separate compile-only/runtime download plans')
