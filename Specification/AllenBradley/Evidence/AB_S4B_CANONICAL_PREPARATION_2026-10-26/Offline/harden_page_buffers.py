"""With the new view only, zero full page/formatter buffers before rendering."""
from pathlib import Path
p=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools/fraktal_ab_canonical_config.py')
raw=p.read_bytes();text=raw.decode().replace('\r\n','\n')
old="    lines += [f'IF {w}.PageBuilt = 0 THEN',f'JSR({page_routine(app)},0);','END_IF;']\n"
new="""    if app.canonical_config_read_view:
        from fraktal_ab_config_read_view import work_tag as read_work
        clean=read_work(app)+'.CleanText';slot=w+'.Slot'
        lines += [f'IF {w}.PageBuilt = 0 THEN',f'FOR {slot} := 0 TO {PAGE_SIZE-1} DO',
                  f'CPS({clean},{root}.HmiResponse.ConfigPage.Entries[{slot}].ValueText,1);',
                  f'{root}.HmiResponse.ConfigPage.Entries[{slot}].Readable := 0;','END_FOR;',
                  f'JSR({page_routine(app)},0);','END_IF;']
    else:
        lines += [f'IF {w}.PageBuilt = 0 THEN',f'JSR({page_routine(app)},0);','END_IF;']
"""
assert text.count(old)==1;text=text.replace(old,new)
old="    status=query_status_tag(app)\n"
new="""    if app.canonical_config_read_view:
        from fraktal_ab_config_read_view import work_tag as read_work
        # Old formatter scratch can contain a longer, previously readable value.
        lines=[f'CPS({read_work(app)}.CleanText,{w}.Render,1);' if line==f'{w}.Render.LEN := 0;' else line for line in lines]
    status=query_status_tag(app)
"""
assert text.count(old)==2;text=text.replace(old,new,1)
p.write_bytes(text.replace('\n','\r\n').encode() if b'\r\n' in raw else text.encode())
print('New-profile page buffers wiped without changing earlier generated images.')
