"""Fill the evidence record from the measured gate outputs; never overwrite."""
from pathlib import Path
import json
W = Path(__file__).parent
E = Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence')
facts = json.loads((W/'finalize_docs_02.log').read_text(encoding='utf-8').strip().splitlines()[-1])
backs = [json.loads((W/f'readback_{t}_01.log').read_text(encoding='utf-8')) for t in ('EchoController', 'PhysicalController')]
assert all(b['Equivalent'] for b in backs)
assert len({(b['ExecutableBodies'], b['AuthoredInitialValues']) for b in backs}) == 1
facts.update(bodies=backs[0]['ExecutableBodies'], values=f"{backs[0]['AuthoredInitialValues']:,}")
text = (W/'report_template.md').read_text(encoding='utf-8').format(**facts)
with (E/'AB_S3K_COMMAND_BINDING_OFFLINE_2026-10-25.md').open('xb') as out:
    out.write(text.encode())
print(json.dumps(dict(written=True, bodies=facts['bodies'], values=facts['values'])))
