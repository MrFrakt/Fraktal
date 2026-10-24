"""Collect the pinned offline Studio Capacity estimate without manual transcription."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

SCHEMA='fraktal.ab.studio-capacity-estimate'


def normalize(capture,expected_sha256):
    if capture.get('Schema')!='fraktal.ab.studio-capacity-capture' or capture.get('SchemaVersion')!=1:
        raise ValueError('unsupported Studio capture')
    if capture.get('Error') or capture.get('Offline') is not True or capture.get('ProcessClosed') is not True:
        raise ValueError('offline Studio measurement/cleanup did not complete')
    for key in ('SourceSha256','SourceSha256After','ReviewInitialSha256'):
        if capture[key].upper()!=expected_sha256.upper():raise ValueError('measurement does not bind the pinned source')
    if not re.fullmatch('[A-Fa-f0-9]{64}',expected_sha256):raise ValueError('invalid source pin')
    filename=Path(capture['ReviewCopy'].replace('\\','/')).name
    if not re.fullmatch(r'Logix Designer - .+ in '+re.escape(filename)+r' \[1756-L81E 38\.\d+\]',capture['FrameTitle']):
        raise ValueError('qualified L81E v38 review window required')
    snapshots=capture['Snapshots']
    if not isinstance(snapshots,list) or len(snapshots)!=2:raise ValueError('two complete UI samples required')
    values=[]
    for snapshot in snapshots:
        if snapshot['PageName']!='Capacity':raise ValueError('wrong controller Properties page')
        rows=snapshot['Controls']
        if any(row['Parent']!=snapshot['StandardParent'] or row['PasswordSkipped'] for row in rows):
            raise ValueError('controls are outside the Standard capacity panel')
        controls={row['Id']:row['Name'] for row in rows}
        if len(controls)!=len(rows):raise ValueError('ambiguous capacity control IDs')
        for key,label in ((1761,'Capacity (Blocks)'),(1762,'Available:'),(1763,'Used Standard:'),(1767,'Total:')):
            if controls.get(key)!=label:raise ValueError('unqualified capacity label/control pairing')
        def number(key):
            text=controls[key]
            if not re.fullmatch(r'(?:0|[1-9]\d*|[1-9]\d{0,2}(?:,\d{3})+)',text):raise ValueError('invalid capacity number')
            return int(text.replace(',',''))
        available,used,total=(number(key) for key in (1764,1765,1766))
        if not re.fullmatch(r'\d{1,3}%',controls[1759]):raise ValueError('invalid displayed capacity usage')
        percent=int(controls[1759][:-1])
        if total<=0 or used+available!=total or not 0<=used<=total or percent!=100*used//total:
            raise ValueError('Capacity arithmetic or displayed usage differs')
        values.append((available,used,total,percent))
    if values[0]!=values[1]:raise ValueError('Studio Capacity samples changed')
    available,used,total,percent=values[0]
    return dict(schema=SCHEMA,schemaVersion=1,Provider='StudioUIAutomation',
                MeasurementKind='Studio offline Capacity Estimate',Measured=True,VerifiedFit=True,
                CanonicalSha256=expected_sha256.upper(),CapacityUnit='Blocks',
                UsedStandardBlocks=used,AvailableBlocks=available,TotalBlocks=total,
                DisplayedUsagePercent=percent,CapturedUtc=snapshots[-1]['CapturedUtc'],
                SourceAcd=capture['SourceAcd'],ReviewCopy=capture['ReviewCopy'],
                StudioSha256=capture['StudioSha256'],MenuResourceSha256=capture['MenuResourceSha256'],
                Offline=True,SourceUnchanged=True,ReviewProcessClosed=True)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--acd',required=True,type=Path)
    parser.add_argument('--expect-sha256',required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--capture-output',required=True,type=Path)
    parser.add_argument('--studio-path',type=Path)
    args=parser.parse_args(argv)
    if args.output.exists() or args.capture_output.exists() or args.output==args.capture_output:
        parser.error('two different new output files required')
    command=['powershell','-NoProfile','-File',str(Path(__file__).with_name('Invoke-AbStudioCapacity.ps1')),
             '-AcdPath',str(args.acd),'-ExpectedSha256',args.expect_sha256,'-OutputPath',str(args.capture_output)]
    if args.studio_path:command+=['-StudioPath',str(args.studio_path)]
    result=subprocess.run(command,check=False)
    try:
        if result.returncode!=0:raise ValueError('Studio collector failed; retain its capture/log')
        raw=args.capture_output.read_bytes()
        report=normalize(json.loads(raw.decode('utf-8-sig')),args.expect_sha256)
        report.update(CapturePath=str(args.capture_output),CaptureSha256=hashlib.sha256(raw).hexdigest())
    except (ValueError,OSError,KeyError,TypeError) as error:
        report=dict(schema=SCHEMA,Provider='StudioUIAutomation',Measured=False,VerifiedFit=False,error=str(error))
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report))
    return 0 if report['VerifiedFit'] else 1


if __name__=='__main__':raise SystemExit(main())
