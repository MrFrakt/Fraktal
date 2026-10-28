from pathlib import Path

W=Path(__file__).parent
source=(W/'inspect_lookup_runtime_01.py').read_text(encoding='utf-8')
before="D = W.parent / 'retry_lookup_01'"
assert source.count(before)==1
source=source.replace(before,"D = W.parent / 'desktop_scan_continue_01'")
before="pageKeys=list(page['page']), entries=len(page['page'].get('entries', []))"
assert source.count(before)==1
source=source.replace(before,"scalars=len(page['page']), entries=page['page']['EntryCount']")
exec(compile(source,str(W/'inspect_lookup_runtime_01.py'),'exec'),{'__file__':__file__})
