from pathlib import Path
W=Path(__file__).parent
source=(W/'finish_docs_01.py').read_text(encoding='utf-8')
old="matches=re.findall(r'Ran ([0-9]+) tests?',(W/(label+'.log')).read_text(encoding='utf-8'));assert matches,label"
new="matches=re.findall(rb'Ran ([0-9]+) tests?',(W/(label+'.log')).read_bytes());assert matches,label"
assert source.count(old)==1
source=source.replace(old,new).replace("W/'finish_docs_01.json'","W/'finish_docs_02.json'")
source=source.replace('with the retained control-script versions.',
 'with the retained control-script versions. The first report collector assumed\nUTF-8 for a raw Windows log; byte-based summary extraction corrects that\nwithout rewriting the log.')
with (W/'finish_docs_02.py').open('x',encoding='utf-8') as out:out.write(source)
print('Created append-only report collector 02')
