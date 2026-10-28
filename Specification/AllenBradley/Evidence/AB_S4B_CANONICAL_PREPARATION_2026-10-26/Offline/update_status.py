from pathlib import Path
import json
R=Path('C:/Users/SoftIndVM/Fraktal');W=Path(__file__).parent
p=R/'Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json'
d=json.loads(p.read_bytes());capacity=json.loads((W/'capacity_auto_01.json').read_bytes())
d['manifestV68']=dict(schemaMajor=6,schemaMinor=8,publicationStage=13,
    approvedBy='AB_CANONICAL_PUBLICATION_S4B_READONLY_CONFIG_REVIEW_2026-10-25.md',
    approvalQuestion='call_519504369cbc4895aca3f61ae5696848:0',
    approvalAnswer='A — publish a read-only configuration view (Recommended)',
    approvedScope='Wire contract and dependent offline work only',nativeAccepted=False,currentSessionAuthorized=False,
    preparation='Evidence/AB_S4B_CANONICAL_PREPARATION_2026-10-26.md',
    preparedAcdSha256=capacity['CanonicalSha256'],sourceSha256='C4D0E14475AADB651A6C7DA23F63ABD6A10F2A11698E629A828CDD67F38C1C6F',
    readServiceColumns=dict(Kind='DINT',Version='DINT',RootSymbol='STRING(40)',CanonicalRoot='STRING(255)'),
    protocol='Kind=1 / Version=1; canonical product resolved from ReadServices and DataProducts, never inferred from names',
    viewMembers=['SchemaVersion','RootIdentity','Revision','DefinitionCount','DefinitionCapacity','Definitions','ValueCount','ValueCapacity','Values'],
    valueMembers=['DefinitionIndex','ModelOrdinal','ModelCode','ValueText','Readable','Revision'],
    definitionContract='Existing configuration-entry metadata minus ValueText/Readable, plus DefinitionIndex; generated from its owning schema',
    authority='Existing R2 configuration owner; change-driven PLC formatting, revisions and access masking; private raw cache remains unexposed',
    directClientPolicy='Unsecured CIP is read-only, including login, page and model-bank selection; no mailbox or provider writes',
    readScheduling='Bounded worker RPC batches yield to cyclic station reads; only selected-bank value payloads are fetched',
    fullBufferMasking=True,independentAdditionalFixturePaths=979,existingFixturePaths=4428,
    measuredCapacityBlocks={k:capacity[v] for k,v in [('used','UsedStandardBlocks'),('available','AvailableBlocks'),('total','TotalBlocks'),('displayedPercent','DisplayedUsagePercent')]},
    offlineGates=dict(abTests=2336,rootTests=74,flutterTests=631,flutterSkipped=12,flutterAnalyze=True,
        flutterLockfileEnforced=True,windowsDebugBuild=True,v38TargetsBuiltAndReadBack=2,accessAudits=4,priorImagesByteIdentical=15),
    desktopImplementation='Generic session, discovery/templates/manifest, logical projection, row guard, worker isolate, tiers, freshness, reconnect, read-only presentation and factory implemented offline; old HMI spike archived and removed',
    acceptancePending=['Exact-image approved Echo session','Concurrent Dart/41-case active-workload qualification','Native all-bank view/access/revision checks',
        'Native acquisition and scan','Verified genealogy rollback and 31 baseline cases','Desktop rendering/connection acceptance'],
    activation='V2/Part III remain inactive; S5-S7 and S3 physical I/O proof remain open; no commit/push')
p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(dict(updated=True,active=False,nativeAccepted=False)))
