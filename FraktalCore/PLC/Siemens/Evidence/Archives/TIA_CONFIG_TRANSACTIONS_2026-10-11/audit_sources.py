from pathlib import Path
import subprocess,hashlib,json,sys
repo=Path('C:/Projects/Fraktal'); work=Path(__file__).resolve().parent
changed=subprocess.check_output(['git','diff','--name-only'],cwd=repo).decode().splitlines()
changed+=subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=repo).decode().splitlines()
rows=[]; converted=[]
for relative in sorted(set(changed)):
 if not relative.startswith(('FraktalCore/HMI/','FraktalCore/PLC/Siemens/')): continue
 p=repo/relative
 if not p.is_file(): continue
 data=p.read_bytes()
 if b'\r\n' in data:
  data=data.replace(b'\r\n',b'\n');p.write_bytes(data);converted.append(relative)
 if p.suffix in ('.scl','.udt','.db','.plan') or p.name.endswith('.scl.in'): assert data.isascii(),relative
 assert b'\r\n' not in data,relative
 rows.append({'path':relative,'sha256':hashlib.sha256(data).hexdigest(),'lf':True})
sys.path.insert(0,str(repo/'FraktalCore/PLC/Siemens/tools'))
import fraktal_tia_generate as GEN
verified=GEN.verify(work/'frames_v6')
value={'checked_authored_files':len(rows),'converted_to_lf':converted,'verified_v6_generated_sources':verified,'rows':rows}
with (work/'75_final_source_checks.json').open('x',encoding='ascii',newline='\n') as f: json.dump(value,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in value.items() if k!='rows'}))