from pathlib import Path

W=Path(__file__).parent
source=(W/'compare_reader_config_pages_01.py').read_text(encoding='utf-8')
before="D = W.parent / 'retry_reader_01'"
assert source.count(before)==1
source=source.replace(before,"D = W.parent / 'desktop_scan_continue_01'")
exec(compile(source,str(W/'compare_reader_config_pages_01.py'),'exec'),{'__file__':__file__})
