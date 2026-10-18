"""Guarded local Echo tower acceptance, with no electrical output writes.

Exact deployed fixture/serial and explicit arming are required. Reuses the
Part fixture's native mailbox, configuration keeper, guard and cleanup policy.
Credentials remain local; only decoded results enter the evidence.
"""
import argparse
import json
from pathlib import Path
import time

import fraktal_ab_access as access
import fraktal_ab_declaration as decl
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as manifest
import fraktal_ab_live as live
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_projection as projection
import fraktal_ab_reasons as reasons
import fraktal_ab_signal_tower as tower
import fraktal_ab_station as station


def snapshot(comm, app):
    raw = px.read_layout(comm,tower.tag(app),tower.members())
    return tower.project(raw)


def exercise(run):
    comm,app,evidence = run.comm,run.app,run.evidence
    def record(case, **values):
        evidence['rows'].append(dict(case=case,passed=True,**values))
    def refused(case, key):
        response = px.command(comm,mb.LAMP_TEST,settle=4)
        run.check(not response['accepted'] and response['diagnosticKey']==manifest.numeric_key(app,key),case)
        record(case,diagnosticKey=response['diagnosticKey'])
    before = projection.read_document(comm)['liveConfig']
    medium = live.FileMedium(live.live_directory(app,evidence['serial']))
    documents = {k:medium.read(k) for k in live.documents(app,before,0)}
    run.login()
    run.restore_configuration()
    after = projection.read_document(comm)['liveConfig']
    wanted = live.documents(app,after,0)
    def values(document):
        return [{key:value for key,value in row.items() if key!='rev'} for row in document[1:]]
    preserved = {k:documents[k] is not None and values(documents[k])==values(v) for k,v in wanted.items()}
    run.check(all(preserved.values()),'configuration values were not preserved')
    record('configuration_preserved',documents=preserved,
           previousRevisions={k:v[0]['configRev'] for k,v in documents.items()},
           currentRevision=manifest.config_revision(app))
    run.idle()
    run.command(mb.SET_ACCESS_LEVEL,IntValue=2,TextValue='1')
    run.command(mb.LOGOUT)
    refused('logged_out_manual_refusal',access.DENIED)
    run.login()
    run.command(mb.SET_ACCESS_LEVEL,IntValue=2,TextValue='0')
    run.command(mb.SET_ACCESS_LEVEL,IntValue=10,TextValue='4')
    run.command(mb.LOGOUT)
    # Request arguments cannot replace the configured bounded native timer.
    run.command(mb.LAMP_TEST,DurationMs=2147483647)
    record('manual_independent_of_power',currentLevel=0,manualRequired=0,powerRequired=4)
    active = run.wait(lambda:snapshot(comm,app) if snapshot(comm,app)['SignalTower/TestActive'] else None,'lamp test')
    run.check(all(active['SignalTower/'+n] for n in tower.OUTPUTS),'test must drive every semantic output')
    record('all_outputs_active',snapshot=active)
    refused('active_test_refusal',gen.UNIT_NOT_READY_KEY)
    run.command(mb.LOGOUT)
    started = time.monotonic()
    comm.Close()  # terminate the client connection while native TONR runs
    disconnected = 3.2  # no controller reads or writes during the complete configured interval
    time.sleep(disconnected)
    expired = snapshot(comm,app)
    elapsed = time.monotonic()-started
    run.check(not expired['SignalTower/TestActive'] and elapsed < 4.0,
              'test did not expire within configured duration and acquisition allowance')
    record('logout_disconnect_timeout',disconnectedSeconds=disconnected,observedSeconds=elapsed,snapshot=expired)
    run.login()
    run.home()
    run.set(px.HOLD['PressRam'],1)
    run.begin()
    run.wait(lambda:(px.read_module(comm,'PressRam') or {}).get('OutImm_Held'),'hold')
    producing = run.wait(lambda:snapshot(comm,app) if snapshot(comm,app)['SignalTower/Green'] else None,'producing indication')
    record('producing',snapshot=producing)
    refused('busy_test_refusal',gen.UNIT_NOT_READY_KEY)
    run.home()
    run.set(px.FAULT['PartSlide'],1)
    run.begin()
    run.wait(lambda:run.unit()['Error'],'adopted fault')
    fault = run.wait(lambda:snapshot(comm,app) if snapshot(comm,app)['SignalTower/Red'] else None,'fault indication')
    first_out = run.unit()['ErrorID']
    symbol = next(name for name,code in app.reasons.items() if code==first_out)
    severity = reasons.of(app,symbol).priority
    run.check(fault['MachineState']==4 and not fault['SignalTower/Green']
              and fault['SignalTower/Horn']==(severity==2 and app.signal_tower.horn_on_high),'fault arbitration')
    record('rationalized_fault',snapshot=fault,firstOut=first_out,severity=severity)
    run.home()
    baseline=run.unit()
    run.set(px.FAULT['PressRam'],1)
    run.begin()
    run.wait(lambda:run.unit()['DecisionId'],'handled fault decision')
    decision = run.wait(lambda:snapshot(comm,app) if snapshot(comm,app)['SignalTower/Blue'] else None,'operator indication')
    record('operator_decision',snapshot=decision)
    run.command(mb.DECISION_ANSWER,IntValue=1)
    run.set(px.FAULT['PressRam'],0)
    run.complete(baseline)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-fixture',action='store_true')
    parser.add_argument('--expect-serial',required=True)
    parser.add_argument('--credential-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--core-regressions',action='store_true',help='also run the existing Part ST/SFC/LD recovery matrix')
    args=parser.parse_args(argv)
    if not args.execute_fixture or station.module_name()!='fraktal_ab_tower_demo':
        parser.error('explicit arm and exactly FRAKTAL_AB_DECLARATION=fraktal_ab_tower_demo required')
    if args.output.exists():
        parser.error('refusing existing evidence output')
    app=station.application()
    account=next(a for a in json.loads(args.credential_file.read_text())['users'] if a['level']==4)
    if account['user'] not in {u.name for u in app.access_users}:
        parser.error('credential file does not name a fixture account')
    from pylogix import PLC
    evidence=dict(schema='fraktal.ab.tower-live-fixture',schemaVersion=1,
                  serial=args.expect_serial,manifestHash=manifest.content_hash(app),rows=[],restored=False)
    with PLC('127.0.0.1') as native:
        native.ProcessorSlot=0
        native.ConnectionSize=4000
        native.SocketTimeout=5
        comm=fixture.Guarded(native,int(args.expect_serial,16),app)
        comm.guard()
        projection.read_document(comm)
        original={tag:px.read_scalar(comm,tag) for tag in gen.externally_writable(app)}
        if any(v is None for v in original.values()):
            raise fixture.FixtureRefused('fixture input snapshot incomplete')
        mode=px.read_unit(comm)['Mode']
        initial_access=projection.read_access(comm)
        original_policy=initial_access['Required'][:]
        if initial_access['CurrentLevel']!=0:
            raise fixture.FixtureRefused('another controller session is active')
        run=fixture.Run(comm,app,account,evidence)
        try:
            exercise(run)
            if args.core_regressions:
                for language in decl.RENDITIONS:
                    run.idle()
                    run.set(gen.rendition_tag(app),gen.rendition_ordinal(language))
                    for operation in (run.happy,run.nok,run.held,
                                      lambda lang:run.held(lang,'abort'),
                                      lambda lang:run.held(lang,'mode'),run.adopted_fault):
                        first=len(run.rows)
                        operation(language)
                        for row in run.rows[first:]:
                            row['passed']=True
        except Exception as error:
            evidence['error']=str(error)
            raise
        finally:
            try:
                run.idle()
                run.command(mb.SET_MODE,IntValue=mode)
                for tag,value in original.items():
                    run.set(tag,value)
                if projection.read_access(comm)['CurrentLevel']!=account['level']:
                    run.login()
                for gate in (2,10):
                    run.command(mb.SET_ACCESS_LEVEL,IntValue=gate,TextValue=str(original_policy[gate]))
                run.command(mb.LOGOUT)
                run.wait(lambda:not snapshot(comm,app)['SignalTower/TestActive'],'test expiry during cleanup',timeout=35)
                final=snapshot(comm,app)
                u=run.unit()
                evidence['final']=dict(tower=final,unit={k:u[k] for k in ('Mode','Running','Error','ErrorID','Aborted')})
                evidence['restored']=(u['Running']==u['Error']==u['Aborted']==0
                    and not final['SignalTower/TestActive']
                    and all(px.read_scalar(comm,k)==v for k,v in original.items())
                    and projection.read_access(comm)['CurrentLevel']==0
                    and projection.read_access(comm)['Required']==original_policy)
                evidence['policyRestored']=projection.read_access(comm)['Required']==original_policy
            finally:
                args.output.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    return 0 if evidence['restored'] else 1


if __name__=='__main__':
    raise SystemExit(main())
