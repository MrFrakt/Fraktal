from pathlib import Path
p=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/HMI/lib/ui/custom_module_tabs.dart')
raw=p.read_bytes();assert b'\r\n' not in raw
p.write_bytes(raw.replace(b'\n',b'\r\n'))
print('Restored the tracked CRLF convention for custom_module_tabs.dart; owner facet_cards.dart untouched.')
