"""Compare accepted publication with the desktop's paging requirements."""
from pathlib import Path
import gzip,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
sys.path.insert(0,str(R/'FraktalCore/PLC/Allen-Bradley/tools'))
import fraktal_ab_genealogy_s4_demo as profile
import fraktal_ab_canonical_config as config
v=json.loads(gzip.decompress((R/'FraktalCore/HMI/test/fixtures/cip_publication_goldens.json.gz').read_bytes()))['vectors'][-1]
values=v['expected']['values'];root=profile.application().name
symbols={s['name'] for s in v['capture']['symbols']}
report=dict(schema='fraktal.ab.s4b-readonly-configuration-inventory',controllerAccess=False,
    source=v['source'],sourceSha256=v['sourceSha256'],
    pageState={k:values[root+'/HmiResponse/ConfigPage/'+k] for k in ('PageIndex','PageCount','EntryCount')},
    editableDefinitions=len(config.values(profile.application())),
    configuredModelBanks=len(profile.application().models),
    descriptorPublished=config.defs_tag(profile.application()) in symbols,
    valueCachePublished=config.state_tag(profile.application()) in symbols,
    pageService=[row for row in v['capture']['manifest']['services'] if row['Kind']==2],
    decision='D9 prohibits unsecured direct mailbox writes; existing repository requests each page/model through QUERY_CONFIG')
with (W/'readonly_config_inventory_01.json').open('x') as stream:json.dump(report,stream,indent=2)
print(json.dumps(report))
