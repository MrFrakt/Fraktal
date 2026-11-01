from pathlib import Path
import hashlib,json
D=Path(__file__).parent;T=Path('C:/Users/SoftIndVM/Fraktal/FraktalCore/PLC/Allen-Bradley/tools')
pins=json.loads((D.parent/'session_09/source_bindings.json').read_bytes())['sha256']
current={str(p):hashlib.sha256(p.read_bytes()).hexdigest().upper() for p in T.rglob('*.py') if '__pycache__' not in p.parts}
bound={str(Path(name)):pin.upper() for name,pin in pins.items() if Path(name).is_relative_to(T)}
print(json.dumps(dict(current=len(current),bound=len(bound),missing=sorted(bound.keys()-current.keys()),added=sorted(current.keys()-bound.keys()),changed=[p for p in current.keys() & bound.keys() if current[p]!=bound[p]]),indent=2))
