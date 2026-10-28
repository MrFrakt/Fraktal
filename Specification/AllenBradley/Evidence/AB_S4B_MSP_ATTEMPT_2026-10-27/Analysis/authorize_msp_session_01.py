"""Record the owner's exact approved body-only packet session after sealed verification."""
from pathlib import Path
original=Path('C:/work/fraktal-ab-s4b-cold-20261026/offline_01/authorize_cold_session_01.py')
archived=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S4B_COLD_DESKTOP_ATTEMPT_2026-10-27/Analysis/authorize_cold_session_01.py')
assert original.read_bytes()==archived.read_bytes()
source=original.read_text(encoding='utf-8')
for before,after,count in (
    ('AB_S4B_COLD_DESKTOP_PREPARATION_2026-10-26','AB_S4B_MSP_PREPARATION_2026-10-27',2),
    ('5c2833f6a8b45759c5417da9a11536e9926a883412cc8c60e4ddbcb80b4acf26','35c78f809aecf1642e1ce32fcca7cfda6a5eeeb054eafc334c4cf94370365d3c',1),
    ('Approve guarded S4b cold-start/desktop session','Approve guarded S4b body-packet qualification',1),
    ('call_297cd0f6497b4493909e0f524643c7c9:0','call_2e3b8f619b2a46728c4e2e0627acc9c2:0',1)):
    assert source.count(before)==count,before
    source=source.replace(before,after)
exec(compile(source,str(original),'exec'),{'__file__':__file__})
