from pathlib import Path
B=Path('C:/work/fraktal-ab-s4b-scheduling-20261028/offline_01')
C=Path(__file__).parent
s=(B/'verify_rehearsals_02.py').read_text()
s=s.replace("['profile_23','profile_24','profile_25']", "['profile_01','profile_02','profile_03']")
s=s.replace('debug_02','debug_01').replace('rehearsal_analysis_02.json','rehearsal_analysis_01.json')
with (C/'verify_rehearsals_01.py').open('x',encoding='utf-8') as f:f.write(s)
s=(B/'validate_hmi_final_02.py').read_text()
for old,new in [('locked_dependencies_02','locked_dependencies_01'),('analyze_final_02','analyze_01'),
                ('full_hmi_03','full_hmi_01'),('profile_build_02','profile_build_01')]:s=s.replace(old,new)
with (C/'validate_hmi_final_01.py').open('x',encoding='utf-8') as f:f.write(s)
