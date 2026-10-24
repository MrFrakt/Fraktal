"""S3f apparatus checks: bounded import, exact deployment and failure cleanup."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_s3f_fixture_execute as fixture


class FixtureTests(unittest.TestCase):
    def test_pieces_roundtrip_complete_station_document_with_one_final_commit(self):
        app=fixture.candidate.application()
        document=fixture.sets.values_document(app,fixture.IMPORT_NAME,1,lambda _o,_r,m:m.initial,'',1700000000,1)
        session=fixture.sets.Session();pieces=list(fixture.import_pieces(document));completed=[]
        for p in pieces:
            self.assertLessEqual(len(p['TextValue']),255)
            result=session.piece(p['TextValue'],p['IntValue']==1,p['BoolValue'])
            if result is not None:completed.append(result)
        self.assertEqual(completed,[document])
        self.assertEqual([i for i,p in enumerate(pieces) if p['BoolValue']],[len(pieces)-1])

    def test_provider_extension_only_permits_planned_public_chunks(self):
        app=fixture.candidate.application();targets=fixture.provider_targets(app)
        packet=fixture.wire.payload(sequence=1,request_sequence=2,login_sequence=3,
            build_revision=fixture.legacy.config_revision(app),operation=fixture.mb.LIST_CONFIG_SETS)
        plan=fixture.client.write_plan(fixture.provider.services(app)[0],packet)
        self.assertEqual(targets,{p for p,_ in plan})
        self.assertTrue(all(t.startswith(fixture.mb.request_tag_name(app)+'.ConfigProvider.') for t in targets))
        self.assertNotIn(fixture.provider.staged_tag(app),targets)

    def test_manifest_pin_rejects_other_publication_before_fixture_writes(self):
        class Parent:
            def __init__(self,*args):self.comm=SimpleNamespace(allowed=frozenset());self.evidence={'serial':'601FC87B'}
            def check(self,ok,message):
                if not ok:raise ValueError(message)
        with patch.object(fixture.previous,'paired_run',return_value=Parent), \
             patch.object(fixture.reader,'read_document',return_value=({},dict(manifest=dict(contentHash='wrong')))):
            with self.assertRaisesRegex(ValueError,'exact S3f publication'):fixture.paired_run(Path('unused.json'))()

    def runner(self):
        app=fixture.candidate.application();commands=[]
        class Parent:
            def command(self,kind,**arguments):commands.append((kind,arguments));return dict(sequence=1)
            def check(self,ok,message):
                if not ok:raise ValueError(message)
        with patch.object(fixture.previous,'paired_run',return_value=Parent):
            run=object.__new__(fixture.paired_run(Path('unused.json')))
        run.app=run.candidate=app;run.evidence={};run.comm=object()
        return run,commands

    def report(self,app,page=0,revision=10):
        values={app.name+'/Status/ConfigRev':revision}
        rows=fixture.gen.editable_values(app)[page*16:(page+1)*16]
        values.update({f'{app.name}/HmiResponse/ConfigPage/Entries[{i}]/WriteKey':m.write_key for i,(_,_,m) in enumerate(rows,1)})
        values[app.name+'/HmiResponse/ConfigPage/EntryCount']=len(rows)
        return dict(pair=dict(canonical=dict(values=values)))

    def test_edit_observation_failure_still_restores_exact_value(self):
        run,commands=self.runner();calls=0
        def query(page=0,model=0):
            nonlocal calls
            calls+=1
            if calls==6:raise RuntimeError('paired acquisition failed')
            return self.report(run.app,page)
        run.query_page=query
        with patch.object(fixture.execute,'read_scalar',return_value=20):
            with self.assertRaisesRegex(RuntimeError,'paired acquisition failed'):run.page_vectors()
        writes=[args for kind,args in commands if kind==fixture.mb.WRITE_CONFIG]
        self.assertEqual([w[fixture.mb.CONFIG_VALUE_MEMBER] for w in writes],[21,20])

    def test_store_failure_only_deletes_owned_names_and_leaves_evidence_directory(self):
        import tempfile
        run,commands=self.runner();run.evidence={'serial':'601FC87B'}
        calls=[]
        def store_command(kind,**args):
            calls.append((kind,args))
            if kind==fixture.mb.SAVE_CONFIG_SET:raise RuntimeError('save interrupted')
        run.store_command=store_command
        with tempfile.TemporaryDirectory() as temp, \
             patch.object(fixture.execute,'read_flat',return_value={'SchemaVersion':1}):
            # The closure owns this new path, not an arbitrary medium supplied by a caller.
            with patch.object(fixture.previous,'paired_run',return_value=type(run).__mro__[1]):
                selected=fixture.paired_run(Path(temp)/'fixture.json')
            run.__class__=selected
            with self.assertRaisesRegex(RuntimeError,'save interrupted'):run.store_vectors()
            self.assertTrue((Path(temp)/'fixture_isolated_sets').is_dir())
            self.assertTrue(run.evidence['s3fSetMediumEmpty'])
            self.assertEqual([k for k,_ in calls],[fixture.mb.LIST_CONFIG_SETS,fixture.mb.SAVE_CONFIG_SET,fixture.mb.LIST_CONFIG_SETS])


if __name__=='__main__':unittest.main()
