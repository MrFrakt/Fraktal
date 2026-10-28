"""Fixed S3j sampled-word vectors on local Echo; separate current approval required.

Only the named disposable source record is writable, never a real I/O address,
the force owner, a config record or a motion stimulus. Original source words
are restored. Every capture uses the independent 4,000-byte observer.
"""
import argparse
from pathlib import Path
import json
import re

import fraktal_ab_genealogy_s3j_demo as candidate
import fraktal_ab_canonical_publication as publication
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_fieldbus as fieldbus
import fraktal_ab_s3j_equivalence as equivalence
import fraktal_ab_s3a_fixture_execute as capture
import fraktal_ab_s3b_fixture_execute as observer
import fraktal_ab_part_execute as guarded
import fraktal_ab_press_execute as execute
import fraktal_ab_projection as projection
import fraktal_ab_declaration as declaration

SERIAL='601FC87B'
SOURCE='FRK_Press_SimIo'
FIELDS=fieldbus.SAMPLE_FIELDS
# First six words are raw values and their validity. Last two cannot grant
# authority: the controller's separate force owner overrides them.
VECTORS=(
 ('operational',(0x49,0x85,0,1,1,1,0,0)),
 ('channel_fault',(0x49,0x85,4,1,1,1,0,0)),
 ('inhibited',(0x49,0x85,65535,1,1,1,0,0)),
 ('offline',(0x49,0x85,0,0,0,0,0,0)),
 ('input_only',(0x49,0x85,0,1,0,1,0,0)),
 ('output_only',(0x49,0x85,0,0,1,1,0,0)),
 ('fault_unknown',(0x49,0x85,0,1,1,0,0,0)),
 ('signed_words',(-1,-2147483647,0,1,1,1,0,0)),
 ('unregistered_gate_claim',(0x49,0x85,0,1,1,1,0,1)),
)


def authorize(path,pin):
    value=json.loads(path.read_text(encoding='utf-8'))
    if not re.fullmatch(r'[A-F0-9]{64}',pin) or value.get('CurrentOwnerApproved') is not True \
            or value.get('S3jIoVectorsAuthorized') is not True or value.get('Serial')!=SERIAL \
            or value.get('CanonicalSha256')!=pin or value.get('FaultClearAuthorized') is not False \
            or value.get('ClockSetAuthorized') is not False:
        raise guarded.FixtureRefused('current exact-image S3j word-vector authorization required')
    return value


class WordRun:
    def __init__(self,comm,destination):
        self.comm,self.destination=comm,destination
        self.app=candidate.application();self.evidence=dict(schema='fraktal.ab.s3j-io-vectors',schemaVersion=1,serial=SERIAL,passed=False,rows=[])
        if len(self.app.io_modules)!=1 or self.app.io_modules[0].sample_tag!=SOURCE or not self.app.canonical_io_fixture:
            raise guarded.FixtureRefused('exact disposable I/O declaration required')
        self.layout=tuple(declaration.Member(name,'DINT') for name in FIELDS)
        self.allowed=frozenset(SOURCE+'.'+name for name in FIELDS)

    def check(self,condition,message):
        if not condition:raise guarded.FixtureRefused(message)

    def guard(self):
        self.comm.guard()
        u=execute.read_unit(self.comm);a=projection.read_access(self.comm)
        self.check(u is not None and u['Mode']==self.app.manual_mode and not any(u[k] for k in
            ('Running','Error','Aborted','RunRequest','AbortRequest','ResetRequest')),'MANUAL/idle Unit required')
        self.check(a is not None and a['CurrentLevel']==0,'active login blocks sampled-word writes')

    def write(self,values):
        self.guard()
        for name,value in zip(FIELDS,values):
            self.check(type(value) is int and -(1<<31)<=value<(1<<31),'fixed DINT source range required')
            self.comm.guard()
            reply=self.comm.Write(SOURCE+'.'+name,value)
            self.check(reply.Status=='Success','sampled-word write failed: '+name)

    def observe(self,phase):
        report=capture.capture_pair(self,self.destination,lambda writer:observer.capture_gate(writer,equivalence.run),
            key='s3jIoPairs',kind='io',metadata=dict(phase=phase))
        return report

    def execute(self):
        self.guard()
        unused,c=reader.read_document(self.comm,expect_serial=SERIAL)
        self.check(c['manifest']['contentHash']==publication.manifest_values(self.app)['ContentHash'],'exact S3j publication required')
        original=execute.read_layout(self.comm,SOURCE,self.layout)
        self.check(original is not None and original['ForcedWord']==0 and original['ForcePermitted']==0,'pristine fixture source required')
        self.evidence['originalSource']=original
        error=None
        try:
            for name,values in VECTORS:
                self.write(values);self.observe(name)
                actual=self.comm.Read('FRK_Press_ForcePermitted')
                self.check(actual.Status=='Success' and actual.Value==0,'unregistered force owner must remain closed')
                self.evidence['rows'].append(dict(case=name,passed=True))
        except Exception as caught:error=f'{type(caught).__name__}: {caught}'
        finally:
            try:
                self.write(tuple(original[n] for n in FIELDS))
                self.check(execute.read_layout(self.comm,SOURCE,self.layout)==original,'source restoration differs')
                self.observe('source_restored');self.evidence['sourceRestored']=True
            except Exception as caught:self.evidence['cleanupError']=f'{type(caught).__name__}: {caught}'
        if error:self.evidence['error']=error
        self.evidence['passed']=error is None and self.evidence.get('sourceRestored') is True and 'cleanupError' not in self.evidence
        return self.evidence


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-fixture',action='store_true');parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--expect-acd-sha256',required=True);parser.add_argument('--authorization-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if not args.execute_fixture or args.expect_serial!=SERIAL or args.output.exists():parser.error('explicit arm, exact local serial and new output required')
    authorize(args.authorization_file,args.expect_acd_sha256)
    from pylogix import PLC
    result=None
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot,native.ConnectionSize,native.SocketTimeout=0,4000,10
        comm=guarded.Guarded(native,0x601FC87B,candidate.application())
        run=WordRun(comm,args.output)
        comm.allowed=run.allowed
        try:result=run.execute()
        except Exception as caught:result=dict(run.evidence,passed=False,error=f'{type(caught).__name__}: {caught}')
    with args.output.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=result['passed'],rows=len(result['rows']),sourceRestored=result.get('sourceRestored'))))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
