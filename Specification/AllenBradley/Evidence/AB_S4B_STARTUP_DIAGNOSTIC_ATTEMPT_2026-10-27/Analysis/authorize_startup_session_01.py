from pathlib import Path
W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01/authorize_cold_session_01.py')
archived=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27/Analysis/authorize_cold_session_01.py')
assert original.read_bytes()==archived.read_bytes()
source=original.read_text(encoding='utf-8')
for before,after,count in (
    ('AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26','AB_S4B_STARTUP_DIAGNOSTIC_PREPARATION_2026-10-27',2),
    ('5c2833f6a8b45759c5417da9a11536e9926a883412cc8c60e4ddbcb80b4acf26','a2e966ee642f47052c35b144f58b3bb809aa8234ddf389592cb01d7843fbfd58',1),
    ('Approve guarded S4b cold-start/desktop session','Approve guarded S4b startup diagnostic session',1),
    ('call_297cd0f6497b4493909e0f524643c7c9:0','call_7d2226c74b974b268cf6aa63ab8aaae6:0',1),
):
    assert source.count(before)==count,before
    source=source.replace(before,after)
exec(compile(source,str(original),'exec'),{'__file__':__file__})
