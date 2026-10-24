from pathlib import Path
import hashlib,json
ROOT=Path('C:/Users/SoftIndVM/Fraktal');BASE=ROOT/'Specification/AllenBradley'
v=BASE/'AB_FROZEN_CONTRACTS_V2.json';d=json.loads(v.read_text())
old='Same-scan acquisition, lifecycle/reset/flag coverage, runtime regressions, sizes and scan remain open.'
new='S3d runtime passes at 2,125 paths: 31 candidate/31 restored-baseline rows; 48 paired captures including idle; four decisions, 14 held/fault, 21 sequence and eight reset captures across ST/SFC/LD. Active/closed alarms, ring wrap, flag transitions and Blocking release are observed; WAIT_RESET remains model-only coverage. Two failed read-plan attempts retain 34 extra regression rows. The oracle now uses revision-cached metadata plus two guarded read-only connections inside the unchanged scan proof (1-8 attempts); the generic reader and approved image are unchanged. Native root/definition/alarm-metadata payloads are 77,304/7,308/16,616 bytes. Scan median/max is 437/3,111 us with zero overlaps. Genealogy and MANUAL=1 readiness are restored; see Evidence/AB_S3D_CANONICAL_RUNTIME_2026-10-22.md. Later surfaces and shipping activation remain open.'
assert d['publication']['physicalManifestLayout'].count(old)==1
d['publication']['physicalManifestLayout']=d['publication']['physicalManifestLayout'].replace(old,new)
assert d['active'] is False
v.write_text(json.dumps(d,indent=2)+'\n')
catalog=BASE/'AB_CAPACITY_OBSERVATIONS_2026-10-21.json';c=json.loads(catalog.read_text())
assert len(c['samples'])==5 and c['samples'][-1]['label']=='S3c'
prep=BASE/'Evidence/AB_S3D_CANONICAL_PREPARATION_2026-10-22'
source='Evidence/AB_S3D_CANONICAL_PREPARATION_2026-10-22/Preparation/genealogy_s3d_01.L5X.gz'
receipt='Evidence/AB_S3D_CANONICAL_PREPARATION_2026-10-22/Preparation/capacity_review.json'
c['samples'].append(dict(label='S3d',source=source,sourceSha256='03e0775edd8a1a22d88d198d4d3ce2b7c19a2f2029a40e3c428cb838fc2ee962',capacity=receipt,capacitySha256=hashlib.sha256((BASE/receipt).read_bytes()).hexdigest(),acdSha256='E5CA9AB3493AABF93E72A728EBDF5630E8056EEA2AC82254B38913B8C7CF7C9D'))
catalog.write_text(json.dumps(c,indent=2)+'\n')
print(json.dumps(dict(passed=True,capacitySamples=len(c['samples']),contractActive=d['active'])))
