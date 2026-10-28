"""Prepare a new unapproved same-image session; fixture write vectors unchanged."""
from pathlib import Path

W=Path(__file__).parent
original=Path('C:/work/fraktal-ab-s4b-refill-20261027/offline_01/prepare_session_01.py')
source=original.read_text(encoding='utf-8')
old="OLD=Path('C:/work/fraktal-ab-s4b-busy-witness-20261027/session_01')"
assert source.count(old)==1
source=source.replace(old,"OLD=Path('C:/work/fraktal-ab-s4b-refill-20261027/session_01')")
source=source.replace("('authorization_checks_02.py','authorization_checks_01.py')","('authorization_checks_01.py','authorization_checks_01.py')")
start=source.index("approval['Scope']+=")
end=source.index("(S/'authorization.template.json')",start)
source=source[:start]+'''approval['Scope']+=' Fitting rows combine only count/body reads in a bounded read-only CIP Multiple Service Packet between separately completed counter reads; packet execution order is irrelevant. Every embedded service is a symbolic Read Tag Fragmented request. Oversized or data-dependent variable-length primitive rows keep the original reader; unsupported/partial transfers fall back within the same attempt/window/deadline. Malformed/type/extent mismatches refuse. Source ages, equality/even/window proofs, attempts/deadlines, freshness limits and all fixture writes are unchanged. Native full-row/desktop acceptance remains unproven.'
approval['ReadOnlyMultipleServiceRows']=True
'''+source[end:]
exec(compile(source,str(original),'exec'),{'__file__':__file__})
