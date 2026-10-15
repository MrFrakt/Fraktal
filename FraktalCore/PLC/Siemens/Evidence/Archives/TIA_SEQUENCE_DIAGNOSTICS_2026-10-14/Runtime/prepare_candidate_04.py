from pathlib import Path
import os,sys
ROOT=Path(r'C:\Projects\Fraktal');WORK=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'FraktalCore/PLC/Siemens/tools'))
from fraktal_tia_program_layout import organize
runtime=Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Sequence_Diagnostics_Runtime_20261014/FrkS12/FrkS12.ap20'
organize(WORK/'candidate_04',WORK/'runtime_grouped_04',runtime,WORK/'runtime_export_04')
