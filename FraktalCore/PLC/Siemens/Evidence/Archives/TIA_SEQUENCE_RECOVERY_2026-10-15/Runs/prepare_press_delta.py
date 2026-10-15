from pathlib import Path
work = Path(__file__).resolve().parent
prior, current = work/'press04', work/'press05'
old = {p.name: p.read_bytes() for p in (prior/'sources').iterdir() if p.suffix in ('.scl', '.udt', '.db', '.xml')}
new = {p.name: p.read_bytes() for p in (current/'sources').iterdir() if p.suffix in ('.scl', '.udt', '.db', '.xml')}
assert old.keys() == new.keys()
changed = {n for n in new if new[n] != old[n]}
assert changed == {'16_SequenceServices.scl', '28_FB_PressDemoAutoGraphOwner.scl', '28_FB_PressDemoHomeGraphOwner.scl'}
full = (current/'grouped/import.plan').read_text('ascii').splitlines()
lines = [full[0]]+[line for line in full if any('--only "'+name+'"' in line for name in changed)]
lines += ['compile --plc PLC_1', 'export --plc PLC_1 --out "'+str(current/'native')+'" --scl true', 'save']
(current/'grouped/refresh.plan').write_bytes(('\n'.join(lines)+'\n').encode('ascii'))
