from pathlib import Path
import hashlib,json,sys
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent;T=R/'FraktalCore/PLC/Allen-Bradley/tools'
inputs={
 'seed':Path('C:/work/echo38_5580_seed.L5X'),
 'python':Path(sys.executable),
 'sdkProbe':T/'Fraktal.Ab.OfflineProbe/bin/Debug/net8.0/win-x86/Fraktal.Ab.OfflineProbe.exe',
 'imagePrepare':Path('C:/work/fraktal-ab-s3j-20261024/s3j_01/prepare/bin/Debug/net8.0/win-x86/ImagePrepare.exe'),
 'storageDefaultsAudit':R/'Specification/AllenBradley/Evidence/AB_S6_COLLAPSE_C4C_OFFLINE_2026-11-06/Investigation/audit_storage_readback_01.py',
}
rows={name:dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest().upper(),bytes=p.stat().st_size) for name,p in inputs.items()}
with (W/'input_bindings_01.json').open('x',encoding='utf-8') as out:json.dump(dict(passed=True,inputs=rows,pythonVersion=sys.version,controllerAccess=False,credentialsRead=False),out,indent=2)
print(json.dumps(dict(passed=True,inputFiles=len(rows))))
