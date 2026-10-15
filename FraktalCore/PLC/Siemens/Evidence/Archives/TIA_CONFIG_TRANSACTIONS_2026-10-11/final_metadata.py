from pathlib import Path
import os,json,subprocess,hashlib
work=Path(__file__).resolve().parent;repo=Path('C:/Projects/Fraktal')
value={
 'runtime_project':str(Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Config_Runtime_20261011/FrkS12/FrkS12.ap20'),
 'compiler_project':str(Path(os.environ['LOCALAPPDATA'])/'Fraktal/TiaStations/Config_Verify_20261011/FrkS12/FrkS12.ap20'),
 'native_config':120,'native_restore_policy':23,'native_access':122,'native_state_alarm':96,'retain_probe':7,
 'native_blocks_interfaces':[190,52],'production_blocks_interfaces':[183,52],
 'hmi_passed':571,'hmi_opt_in_skipped':8,'live_hmi':'PASS','live_config_visible_ms':6058,'focused_mapper_repository':32,
 'tools_passed':135,'consistency_tests_passed':35,'generated_v6_verified':70,
 'keeper_pid':1748,'keeper_must_remain_alive':True,'gateway_stopped':True,
 'new_driver_build':False,'physical_target_mutation':False,'staged_committed_pushed':False,
 'prior_verified':{'access':3360,'state_alarm':3179,'older_available':134,'older_absent_manifests':18,'older_absent_reports':12},
 'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo).decode().strip(),
 'configuration_names':['station config','line config','model config'],
}
assert (work/'gateway_verified.stop').is_file()
assert 'No issues found!' in (work/'79_hmi_analysis.log').read_text('utf-16')
with (work/'83_final_metadata.json').open('x',encoding='ascii',newline='\n') as f:json.dump(value,f,indent=2);f.write('\n')
print(json.dumps(value))