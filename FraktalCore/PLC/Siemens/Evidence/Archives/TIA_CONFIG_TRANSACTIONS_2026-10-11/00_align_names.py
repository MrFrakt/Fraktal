"""Use station config, line config and model config in current presentation."""
from pathlib import Path
import json
import re

repo = Path('C:/Projects/Fraktal')
files = [repo / p for p in (
    'Specification/Fraktal_Core_Part_I.md', 'Specification/HMI_CONTRACT.md',
    'Specification/Fraktal_TIA_Part_IV.md',
    'FraktalCore/HMI/lib/localization/default_catalogs.dart',
    'FraktalCore/HMI/lib/ui/config_and_history.dart',
    'FraktalCore/HMI/lib/content/module_layout.dart',
    'FraktalCore/HMI/test/widget_test.dart',
    'FraktalCore/HMI/test/config_editor_controls_test.dart',
)]
terms = [('station configuration', 'station config'), ('line configuration', 'line config'),
         ('model configuration', 'model config'), ('station data', 'station config'),
         ('line data', 'line config'), ('model data', 'model config'),
         ('model parameters', 'model config'), ('model params', 'model config')]
rows = []
for path in files:
    original = path.read_bytes().decode('utf-8')
    text = original
    for old, new in terms:
        text = re.sub(re.escape(old), lambda m: new.capitalize() if m[0][0].isupper() else new, text, flags=re.I)
    if path.name == 'default_catalogs.dart':
        for key, old, new in (
            ('std.config.group.model', 'Datos del modelo', 'Configuración del modelo'),
            ('std.config.group.line', 'Datos de línea', 'Configuración de línea'),
            ('std.module.card.modelData', 'Datos del modelo', 'Configuración del modelo'),
            ('std.module.card.lineData', 'Datos de línea', 'Configuración de línea'),
        ):
            text = text.replace("'%s': '%s'" % (key, old), "'%s': '%s'" % (key, new))
    if text != original:
        path.write_bytes(text.replace('\r\n', '\n').encode('utf-8'))
        rows.append(path.relative_to(repo).as_posix())
Path(__file__).with_suffix('.json').write_bytes((json.dumps(rows, indent=2) + '\n').encode('ascii'))
print(json.dumps(rows))
