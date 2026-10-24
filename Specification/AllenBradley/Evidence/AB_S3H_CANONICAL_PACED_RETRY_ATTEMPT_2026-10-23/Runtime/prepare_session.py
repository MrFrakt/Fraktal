from pathlib import Path
R=Path(__file__).parent;prior=R.parent/'runtime_fd53835fe9684f598bdd829da6d29c8d'
t=(prior/'prepare_runtime.py').read_text()
changes={
 'retry_9d1da9a04d564b03bc2b176f5b17ea42':'retry_fc306d330cc642499a52abbb53bae945',
 'AB_S3H_CANONICAL_RETRY_PREPARATION_2026-10-23':'AB_S3H_CANONICAL_PACED_RETRY_PREPARATION_2026-10-23',
 '1599086f1e840cfd1658674f9b91bd9b965a579f085463ae297c7b2c7229bb51':'e0def2de1f626503858c1bb6fbbee27a755153d4fd7abe307c5950e84f5fb437',
 'call_b3c6555953654068a83f787a8b82de5e:0':'call_9b203bdff24848999469abe17a76ee4f:0',
 'Approve this guarded S3h retry':'Approve this guarded paced S3h retry',
}
for old,new in changes.items():
 assert t.count(old)==1,(old,t.count(old));t=t.replace(old,new,1)
with (R/'prepare_runtime.py').open('x') as f:f.write(t)
