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
import fraktal_ab_fixture_reads as views
import fraktal_ab_generate as gen
import fraktal_ab_harness_documents as host_docs
import fraktal_ab_mailbox as mb
import fraktal_ab_manifest as manifest
import fraktal_ab_live as live
import fraktal_ab_part_execute as fixture
import fraktal_ab_press_execute as px
import fraktal_ab_reasons as reasons
import fraktal_ab_signal_tower as tower
import fraktal_ab_station as station


def snapshot(comm, app):
    return views.signal_tower(comm, app=app)


def exercise_common(run):
    """Rows every declaration has: configuration restore/preservation and the logged-out refusal.

    LAMP_TEST is the probe because its gate is checked before dispatch; a
    declaration without a tower refuses it for access first, like any other.
    Returns the row recorder and the refusal probe for the declaration's own rows.
    """
    comm,app,evidence = run.comm,run.app,run.evidence
    def record(case, **values):
        evidence['rows'].append(dict(case=case,passed=True,**values))
    def refused(case, key):
        response = (views.command(comm,mb.LAMP_TEST,app=app,settle=4)
                    if app.canonical_collapse else px.command(comm,mb.LAMP_TEST,settle=4))
        expected_key = views.numeric_key(comm, key, app=app)
        run.check(not response['accepted'] and response['diagnosticKey']==expected_key,case)
        record(case,diagnosticKey=response['diagnosticKey'])
    if app.canonical_collapse:
        seed_docs = host_docs.seed_documents(evidence['serial'], app.name)
        run.login()
        run.restore_configuration()
        session = views._session(comm, app)
        lease = views.connection_state(comm)._fraktal_host_lease
        expected, epoch = host_docs.expected_documents(session.reader, session.root)
        run.check(views.revision(comm, app=app) == epoch
                  and host_docs.medium_matches(lease.store, expected)
                  and lease.originals_unchanged(),
                  'isolated host medium or original seed verification failed')
        preserved, previous_revs, current_rev = host_docs.compare_seed_documents(seed_docs, expected)
        run.check(all(preserved.values()), 'configuration values were not preserved')
        record('configuration_preserved', documents=preserved,
               previousRevisions=previous_revs, currentRevision=current_rev)
    else:
        raise fixture.FixtureRefused('canonical collapsed profile required')
    run.idle()
    run.command(mb.SET_ACCESS_LEVEL,IntValue=2,TextValue='1')
    run.command(mb.LOGOUT)
    refused('logged_out_manual_refusal',access.DENIED)
    run.login()
    run.command(mb.SET_ACCESS_LEVEL,IntValue=2,TextValue='0')
    return record, refused


def exercise(run):
    comm,app = run.comm,run.app
    record, refused = exercise_common(run)
    observer = comm.open_observer() if app.canonical_collapse else None
    try:
        if observer is not None:
            snapshot(observer, app)
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
        comm.close_phase()  # terminate the client connection while native TONR runs
        disconnected = 3.2  # no controller reads or writes during the complete configured interval
        time.sleep(disconnected)
        expired = snapshot(observer if observer is not None else comm,app)
        elapsed = time.monotonic()-started
        run.check(not expired['SignalTower/TestActive'] and elapsed < 4.0,
                  'test did not expire within configured duration and acquisition allowance')
        record('logout_disconnect_timeout',disconnectedSeconds=disconnected,observedSeconds=elapsed,snapshot=expired)
    finally:
        if observer is not None:
            observer.Close()
    if app.canonical_collapse:
        comm.open_new_phase()
    run.login()
    run.home()
    run.set(px.HOLD['PressRam'],1)
    run.begin()
    run.wait(lambda:(run.module('PressRam') or {}).get('OutImm_Held'),'hold')
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
    return execute_fixture(args, app, account)


def execute_fixture(args, app, account, *, run_type=fixture.Run,
                    schema='fraktal.ab.tower-live-fixture', exercise_rows=exercise, plc_factory=None):
    """Shared exact-target deployment regressions and restoration owner."""
    if not args.execute_fixture or args.output.exists():
        raise fixture.FixtureRefused('explicit arm and new evidence output required')
    if plc_factory is None:
        from pylogix import PLC
        plc_factory = lambda: PLC('127.0.0.1')
    evidence=dict(schema=schema,schemaVersion=1,
                  serial=args.expect_serial,manifestHash=views.manifest_hash(app),rows=[],restored=False)
    native = plc_factory()
    comm = None
    try:
        native.ProcessorSlot=0
        native.ConnectionSize=4000
        native.SocketTimeout=5
        comm=fixture.Guarded(native,int(args.expect_serial,16),app,plc_factory=plc_factory)
        comm.guard()
        original={tag:px.read_scalar(comm,tag) for tag in gen.externally_writable(app)}
        if any(v is None for v in original.values()):
            raise fixture.FixtureRefused('fixture input snapshot incomplete')
        mode=views.unit_surface(comm, app=app)['Mode']
        initial_access=views.read_access(comm, app=app)
        original_policy=list(initial_access['Required'])
        if initial_access['CurrentLevel']!=0:
            raise fixture.FixtureRefused('another controller session is active')
        run=run_type(comm,app,account,evidence)
        try:
            exercise_rows(run)
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
                if app.canonical_collapse:
                    if getattr(comm, '_phase_closed', False) is True:
                        comm.open_new_phase()
                    else:
                        comm.check_owned_leases()
                run.idle()
                run.command(mb.SET_MODE,IntValue=mode)
                for tag,value in original.items():
                    run.set(tag,value)
                if views.read_access(comm, app=app)['CurrentLevel']!=account['level']:
                    run.login()
                for gate in (2,10):
                    run.command(mb.SET_ACCESS_LEVEL,IntValue=gate,TextValue=str(original_policy[gate]))
                run.command(mb.LOGOUT)
                final=None
                if app.signal_tower is not None:
                    run.wait(lambda:not snapshot(comm,app)['SignalTower/TestActive'],'test expiry during cleanup',timeout=35)
                    final=snapshot(comm,app)
                u=run.unit()
                after_access=views.read_access(comm, app=app)
                final_record=dict(tower=final,unit={k:u[k] for k in ('Mode','Running','Error','ErrorID','Aborted')})
                restored_ok=(u['Running']==u['Error']==u['Aborted']==0
                    and (final is None or not final['SignalTower/TestActive'])
                    and all(px.read_scalar(comm,k)==v for k,v in original.items())
                    and after_access['CurrentLevel']==0
                    and list(after_access['Required'])==original_policy)
                if app.canonical_collapse:
                    comm.check_owned_leases()
                    originals_ok = comm.originals_unchanged()
                    active_host = getattr(views.connection_state(comm), '_fraktal_host_lease', None)
                    docs_ok = True
                    if active_host is not None:
                        host_docs.ready(comm, app, active_host)
                        docs_ok = active_host.originals_unchanged()
                    final_record['originalMediumUnchanged'] = originals_ok and docs_ok
                    final_record['liveDocumentsVerified'] = active_host is not None and docs_ok
                    restored_ok = restored_ok and originals_ok and docs_ok
                evidence['final']=final_record
                evidence['restored']=restored_ok
                evidence['policyRestored']=list(after_access['Required'])==original_policy
            finally:
                args.output.write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf-8')
    finally:
        try:
            if comm is not None:
                comm.Close()
        finally:
            native.Close()
    return 0 if evidence['restored'] else 1


if __name__=='__main__':
    raise SystemExit(main())
