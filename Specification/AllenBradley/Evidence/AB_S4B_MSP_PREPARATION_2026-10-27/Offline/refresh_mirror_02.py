from pathlib import Path
original=Path(__file__).with_name('refresh_mirror_01.py')
source=original.read_text(encoding='utf-8')
before="W/'isolated_hmi_sources_01.json'"
assert source.count(before)==1
source=source.replace(before,"W/'isolated_hmi_sources_02.json'")
exec(compile(source,str(original),'exec'),{'__file__':__file__})
