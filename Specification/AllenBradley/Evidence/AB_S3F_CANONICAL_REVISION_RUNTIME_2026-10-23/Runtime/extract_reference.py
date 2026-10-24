from pathlib import Path
import gzip,hashlib,json
R=Path(__file__).parent
p=Path('C:/Users/SoftIndVM/Fraktal/Specification/AllenBradley/Evidence/AB_S3A_CANONICAL_RUNTIME_2026-10-21/Reference/genealogy_current.L5X.gz')
raw=gzip.decompress(p.read_bytes());pin=hashlib.sha256(raw).hexdigest()
assert pin=='91bf67c9101eae863cf29c1a9df6413d7256ab056d985394587f0183aa525714'
with (R/'genealogy_reference.L5X').open('xb') as f:f.write(raw)
print(json.dumps(dict(passed=True,sha256=pin,source=str(p),controllerAccess=False)))
