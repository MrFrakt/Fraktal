from pathlib import Path
import hashlib

ROOT=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent

def replace(path,old,new):
    p=ROOT/path;raw=p.read_bytes();s=raw.decode();assert s.count(old)==1,(path,old)
    p.write_bytes(s.replace(old,new).encode())

replace('Specification/AllenBradley/AB_CANONICAL_PUBLICATION_PLAN_2026-10-20.md',
    '16 frozen gaps plus occupied eight-row Core V3 history; pending finite contract review; parameter keys stay `line.`-prefixed',
    'Owner-approved offline scope: 16 frozen gaps, two Core Line status members and occupied eight-row V3 history; S3i implementation/build/model gates in progress; native session separately gated; parameter keys stay `line.`-prefixed')

p=W/'prepare/Program.cs';s=p.read_text()
old=hashlib.sha256((W/'s3i_bench_02.L5X').read_bytes()).hexdigest().upper()
new=hashlib.sha256((W/'s3i_bench_03.L5X').read_bytes()).hexdigest().upper()
assert s.count(old)==1 and s.count('s3i_bench_02.L5X')==1
with p.open('w',encoding='utf-8',newline='\n') as f:f.write(s.replace(old,new).replace('s3i_bench_02.L5X','s3i_bench_03.L5X'))
print('Working plan status and unsealed offline helper updated for corrected source')
