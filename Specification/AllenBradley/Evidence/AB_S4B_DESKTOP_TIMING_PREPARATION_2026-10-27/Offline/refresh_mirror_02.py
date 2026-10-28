from pathlib import Path
W=Path(__file__).parent
source=(W/'refresh_mirror_01.py').read_text(encoding='utf-8')
before="W/'isolated_hmi_sources_01.json'";assert source.count(before)==1
source=source.replace(before,"W/'isolated_hmi_sources_02.json'")
exec(compile(source,str(W/'refresh_mirror_01.py'),'exec'),{'__file__':__file__})
