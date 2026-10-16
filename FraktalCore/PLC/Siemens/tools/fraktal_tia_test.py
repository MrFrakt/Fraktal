"""Verify a native fixture, optionally download its guarded test CPU, emit JUnit.

Observation is the default. Downloads require the unchanged owner-approved
driver, clean compiler results, source/interface read-back and an explicit
reserved unmapped test identity. No uncertain mutation is retried.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

TIA=Path(__file__).resolve().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


def junit(path,name,assertions,result,error=''):
    failed=bool(error) or result.get('Done') is not True or result.get('Checks')!=len(assertions) or result.get('Failures')!=0 or result.get('FirstFailure')!=0
    suite=ET.Element('testsuite',name=name,tests='1',failures=str(int(failed)),errors='0')
    properties=ET.SubElement(suite,'properties')
    for key,value in {'native_assertions':result.get('Checks',0),'expected_assertions':len(assertions),
                      'native_failures':result.get('Failures',0),'first_failure':result.get('FirstFailure',0)}.items():
        ET.SubElement(properties,'property',name=key,value=str(value))
    case=ET.SubElement(suite,'testcase',classname='Fraktal.TIA.Native',name=name)
    if failed:
        label=assertions.get(str(result.get('FirstFailure',0)),'native execution/observation gate')
        ET.SubElement(case,'failure',message=label,type='NativeAssertion').text=error or json.dumps(result)
    tree=ET.ElementTree(suite);ET.indent(tree)
    with path.open('xb') as stream:tree.write(stream,encoding='utf-8',xml_declaration=True)
    return not failed


def run(profile,project,revision,download=False,report_dir=None):
    local=Path(os.environ['LOCALAPPDATA'])/'Fraktal'
    revision=revision.resolve();profile=profile.resolve();project=project.resolve()
    if not revision.is_relative_to(local/'TiaSpikes') or not project.is_relative_to(local/'TiaStations'):
        raise ValueError('native fixture and engineering copy must stay in their dedicated local roots')
    if not profile.is_relative_to(TIA/'Tests'):raise ValueError('select a versioned test profile')
    output=Path(report_dir).resolve() if report_dir else revision
    if output!=revision:
        if output.parent!=revision:raise ValueError('additional report directory must be an immediate child of this revision')
        output.mkdir(exist_ok=False)
    if any((output/name).exists() for name in ('native_test_observation.log','native_test_result.json','native_tests.junit.xml')):
        raise ValueError('test reports already exist; choose a new report directory before acting')
    assertions=json.loads((revision/'sources/assertions.json').read_bytes())
    if not assertions or list(assertions)!=[str(i) for i in range(1,len(assertions)+1)]:raise ValueError('nonempty contiguous assertion catalog required')
    from fraktal_tia_test_runtime import verify_signature
    image_hash=verify_signature(revision/'sources')
    sys.path.insert(0,str(TIA/'Tests/Line'))
    from owner_target import Target,original
    from run_bench import powershell
    verifier=load(TIA/'Tests/Line/verify_owner_exports.py','native_fixture_verifier')
    verified=verifier.verify(revision/'sources',revision/'native')
    witness=revision/'owner_verified_private.json'
    if witness.exists():
        if json.loads(witness.read_bytes())!=verified:raise ValueError('native verification witness differs')
    else:
        with witness.open('x',encoding='ascii',newline='\n') as stream:json.dump(verified,stream,indent=2);stream.write('\n')
    target=Target(profile,revision.parent,project)
    before=original();started=time.monotonic();result={};error=''
    try:
        if download:target.download(revision)
        target.guard()
        for attempt in range(3):
            observation,rows=powershell(TIA/'tools/Invoke-TiaIsolatedBench.ps1','-Profile',str(profile),'-Action','read','-ExpectedChecks',str(len(assertions)),'-ExpectedImageHash',image_hash)
            if not observation.returncode or 'AccessViolationException' not in observation.stdout:break
        with (output/'native_test_observation.log').open('x',encoding='utf-8',newline='\n') as stream:stream.write(observation.stdout)
        matches=[row for row in rows if row.get('event')=='results']
        if matches:result=matches[-1]
        if observation.returncode:error='Native test observation failed; see native_test_observation.log'
    except Exception as exc:error=str(exc)
    after=original()
    if after!=before:error+='; original Fraktal state changed'
    evidence=dict(before=before,after=after,result=result,error=error,download=download,elapsed_seconds=time.monotonic()-started)
    with (output/'native_test_result.json').open('x',encoding='ascii',newline='\n') as stream:json.dump(evidence,stream,indent=2);stream.write('\n')
    passed=junit(output/'native_tests.junit.xml',target.profile['name'],assertions,result,error)
    print(json.dumps(dict(result='PASS' if passed else 'FAIL',assertions=result.get('Checks',0),failures=result.get('Failures',0),first_failure=result.get('FirstFailure',0),error=error)))
    return 0 if passed else 1


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',type=Path,required=True);p.add_argument('--project',type=Path,required=True)
    p.add_argument('--revision',type=Path,required=True);p.add_argument('--download',action='store_true')
    p.add_argument('--report-dir',type=Path)
    a=p.parse_args();sys.exit(run(a.profile,a.project,a.revision,a.download,a.report_dir))
