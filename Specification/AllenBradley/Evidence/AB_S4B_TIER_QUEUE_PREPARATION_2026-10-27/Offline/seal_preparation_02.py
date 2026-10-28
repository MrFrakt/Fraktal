"""Match the exact retained negative-test reporter text; keep the failed gate."""
from pathlib import Path
W=Path(__file__).parent
source=(W/'seal_preparation_01.py').read_text(encoding='utf-8')
for before,after in (
 ("b'+1 -4: Some tests failed!'","b'+1 -4: Some tests failed.'"),
 ("p.name!='seal_preparation_01.log'","p.name!='seal_preparation_02.log'")):
    assert source.count(before)==1,before
    source=source.replace(before,after)
exec(compile(source,str(W/'seal_preparation_01.py'),'exec'),{'__file__':__file__})
