import sys
from pathlib import Path
sys.path.insert(0,'C:/Projects/Fraktal/FraktalCore/PLC/Siemens/Spikes/S16_Persistence')
from probe_web import probe
probe(Path(sys.argv[1]),load_only=True)
