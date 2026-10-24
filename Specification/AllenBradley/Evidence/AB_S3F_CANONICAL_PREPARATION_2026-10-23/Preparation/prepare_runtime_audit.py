"""Extend the accepted inherited audit with explicit S3f page/vector checks."""
from pathlib import Path
import shutil
W=Path(__file__).parent;E=Path('C:/work/fraktal-ab-s3e-20261022/prepare_768bb43d842d4b008ab1dfb322741aea')
assert not (W/'verify_runtime_acceptance.py').exists()
shutil.copyfile(E/'audit_baseline_access.py',W/'audit_baseline_access.py')
text=(E/'verify_runtime_acceptance.py').read_text().replace("['s3e","['s3f")
anchor=" for kind,items in [('decision',decisions),('condition',conditions),('sequence',sequences),('reset',resets),('access',access)]:"
assert text.count(anchor)==1
text=text.replace(anchor,""" config=fixture['s3fConfigPairs'];config_rows=fixture['s3fConfigRows']
 expected_config={'page_walk_and_model_bank','edit_revision_and_exact_restoration','hidden_values_and_policy_restoration',
  'store_save_list_export_import_load_delete','provider_stale_parent_refused','provider_stale_login_refused',
  'provider_catalog_overflow_refused','provider_invalid_utf8_refused'}
 assert len(config_rows)==8 and {r['case'] for r in config_rows}==expected_config and all(r['passed'] for r in config_rows)
 assert fixture['s3fSetMediumEmpty'],'isolated set medium not cleaned'
 assert len(config)>0 and {r['page'] for r in config}>={0,1,2} and any(r['model']==2 for r in config)
 for kind,items in [('decision',decisions),('condition',conditions),('sequence',sequences),('reset',resets),('access',access),('configuration',config)]:""")
anchor="   assert result['comparedPaths']==result['typedPaths']==2154"
assert text.count(anchor)==1
text=text.replace(anchor,"""   values=state['canonical']['values'];page=values['Press/HmiResponse/ConfigPage/PageIndex']
   expected_count={0:2617,1:2567,2:2217}[page]
   if kind=='configuration':assert page==item['page']
   assert result['comparedPaths']==result['typedPaths']==expected_count
   assert values['Press/HmiResponse/ConfigPage/Revision']==values['Press/Status/ConfigRev']
   from fraktal_ab_canonical_reader import snapshot
   assert snapshot(state['capture'])==state['canonical'],'generic capture replay changed'
   assert state['canonical']['types']['Press/ConfigSets[1]/SetSchema']=='UInt16'
   assert state['canonical']['types']['Press/ConfigPersist/PendingSince']=='DateTime'""")
anchor=" assert class_values=={extra[1]['originalReadLevel'],extra[1]['temporaryReadLevel']},'class policy transition missing'"
assert text.count(anchor)==1
text=text.replace(anchor," assert class_values=={extra[1]['originalReadLevel'],extra[1]['temporaryReadLevel'],4},'class policy/hiding transition missing'")
text=text.replace('paths=2154','paths=expected_count')
text=text.replace('report=dict(manualPolicyPath=',"report=dict(configurationRows=len(config_rows),configurationPairs=len(config),plannedCandidateRows=41,manualPolicyPath=")
# The first logout is the hidden-value vector. Its class must actually be hidden.
anchor="    if phase=='logged_out':assert values[base+'CurrentLevel']==0 and values[base+'CurrentUser']==''"
assert text.count(anchor)==1
text=text.replace(anchor,anchor+"\n    if phase=='logged_out':assert values[base+'Classes[2]/ReadLevel']==4")
with (W/'verify_runtime_acceptance.py').open('x') as f:f.write(text)
compile(text,str(W/'verify_runtime_acceptance.py'),'exec')
print('S3f audit prepared; no runtime data or controller operations')
