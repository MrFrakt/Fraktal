from pathlib import Path

W=Path(__file__).parent
original=W/'seal_reader_runtime_01.py'
archived=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_READER_RUNTIME_2026-10-26/Continuation/seal_reader_runtime_01.py')
assert original.read_bytes()==archived.read_bytes()
source=original.read_text(encoding='utf-8')
def replace(before,after,count=1):
    global source
    assert source.count(before)==count,(before,source.count(before))
    source=source.replace(before,after)
replace("D = W.parent / 'retry_reader_01'","D = W.parent / 'desktop_scan_continue_01'")
replace("assert all(code == 0 for code in stages.values()), stages","assert all(code==(1 if name=='desktop_acceptance_review_01' else 0) for name,code in stages.items()), stages")
replace('accepted = functional and scan_passed',"""desktop=load(D/'desktop_acceptance_review_01.json')
assert desktop['helperReportedPassed'] and desktop['actualModules']==0 and desktop['actualViews']==2
desktop_passed=desktop['desktopLiveAccepted']
trace=load(D/'task_trace_analysis_01.json')
accepted = functional and scan_passed and desktop_passed""")
replace('desktopAccepted=False','desktopAccepted=desktop_passed',4)
replace("scanCauseConfirmed=False, desktopAccepted=desktop_passed, serial='601FC87B',","scanCauseConfirmed=False, desktopAccepted=desktop_passed, serial='601FC87B',\n    desktopCoverageReview=desktop, taskTrace=trace,")
replace('call_abc4d640a85f42539728d5b6b697dbb4:0','call_6c35ecad4ba84714a17ec9b7b68f5ad4:0')
replace('Approve guarded S4b reader retry','Approve guarded S4b desktop/scan session')
replace("name = 'AB_S4B_READER_RUNTIME_2026-10-26' if functional else 'AB_S4B_READER_RETRY_ATTEMPT_2026-10-26'","name = 'AB_S4B_DESKTOP_SCAN_RUNTIME_2026-10-26'")
replace("report = (W / ('reader_runtime_report.txt' if functional else 'reader_attempt_report.txt')).read_text(encoding='utf-8')","report = (W/'desktop_scan_runtime_report.txt').read_text(encoding='utf-8')")
replace("'.l5x','.cs','.csproj')","'.l5x','.cs','.csproj','.png','.dart')")
start=source.index("for name in ('authorize_reader_retry_01.py'")
end=source.index("\nfor name in ('authorize_reader_retry_01.log'",start)
source=source[:start]+"""for name in ('authorize_desktop_continuation_01.py','inspect_desktop_runtime_01.py',
    'replay_desktop_pairs_01.py','compare_desktop_config_pages_01.py','analyze_desktop_task_trace_01.py',
    'review_desktop_coverage_01.py','seal_desktop_scan_runtime_01.py','desktop_scan_runtime_report.txt'):
    archive(W/name,'Continuation/'+name)
"""+source[end:]
replace("for name in ('authorize_reader_retry_01.log','authorize_reader_retry_01_exit.json'):\n    archive(W.parent / 'session_01' / name,'Continuation/'+name)","for name in ('authorize_continuation_01.log','authorize_continuation_01_exit.json'):\n    archive(W.parent/'desktop_scan_01'/name,'Continuation/'+name)")
replace('AB_S4B_READER_RETRY_PREPARATION_2026-10-26/manifest.json','AB_S4B_DESKTOP_SCAN_CONTINUATION_2026-10-26/manifest.json')
replace("W / 'sealed_reader_runtime_01.json'","W / 'sealed_desktop_scan_runtime_01.json'")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
