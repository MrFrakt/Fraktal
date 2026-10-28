"""Fill the evidence record from the measured gate outputs; never overwrite."""
from pathlib import Path
import json
W=Path(__file__).parent;E=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence')
facts=json.loads((W/'finalize_docs_02.log').read_text(encoding='utf-8').strip().splitlines()[-1])
back=json.loads((W/'readback_PhysicalController_01.log').read_text(encoding='utf-8'))
facts.update(bodies=back['SFC'] and None or None)
