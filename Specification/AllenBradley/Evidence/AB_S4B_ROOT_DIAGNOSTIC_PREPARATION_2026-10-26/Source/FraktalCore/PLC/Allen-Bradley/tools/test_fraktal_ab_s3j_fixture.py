"""S3j word apparatus: exact arm, bounded writes, independent captures, cleanup."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_s3j_io_execute as fixture
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_manifest as manifest
import fraktal_ab_projection as projection
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_st_model as st


class RootReferenceTests(unittest.TestCase):
    def test_adopted_fault_uses_candidate_io_catalog_without_changing_global_app(self):
        # Native S3j condition capture 2: the old genealogy APP had no I/O,
        # while the adopted PartSlide fault names its retracted sensor.
        app=fixture.candidate.application();other=replace(app,io_modules=())
        unit=dict(st.structure(gen.unit_context_members(app)),Error=1,
                  ErrorSource=3,DiagReason=10101,DiagIoRoles=2)
        contexts={m.name:st.structure(gen.module_context_members(library.type_of(m)))
                  for m in app.modules}
        expected={'Press/Status/Diagnostic/IoTag':'_101B301A',
                  'Press/Status/Diagnostic/IoAddress':'Local:1:I.0'}
        with patch.object(projection,'APP',other):
            result=shared.oracle(app,manifest.content(app),unit,contexts,
                                 [m.code for m in app.models],expected=set(expected))
            self.assertEqual(result['values'],expected)
            self.assertIs(projection.APP,other)


class WordFixtureTests(unittest.TestCase):
    def test_current_exact_image_authorization_required_before_any_connection(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'approval.json';pin='A'*64
            base=dict(CurrentOwnerApproved=True,S3jIoVectorsAuthorized=True,Serial=fixture.SERIAL,
                      CanonicalSha256=pin,FaultClearAuthorized=False,ClockSetAuthorized=False)
            path.write_text(json.dumps(base));self.assertEqual(fixture.authorize(path,pin),base)
            for field,value in (('CurrentOwnerApproved',False),('S3jIoVectorsAuthorized',False),('Serial','00000000'),
                                ('CanonicalSha256','B'*64),('ClockSetAuthorized',True),('FaultClearAuthorized',True)):
                path.write_text(json.dumps(dict(base,**{field:value})))
                with self.subTest(field=field),self.assertRaisesRegex(Exception,'current exact-image'):fixture.authorize(path,pin)

    def run_fixture(self,*,failure=False):
        original=dict(InputWord=7,OutputWord=8,FaultWord=0,InputValid=1,OutputValid=1,FaultValid=1,ForcedWord=0,ForcePermitted=0)
        live=deepcopy(original);writes=[];guards=[];captures=[];failed=False
        class Comm:
            def guard(self):guards.append(1)
            def Write(self,tag,value):
                nonlocal failed
                writes.append((tag,value))
                if failure and not failed and len(writes)==4:
                    failed=True;return SimpleNamespace(Status='refused')
                live[tag.rsplit('.',1)[1]]=value;return SimpleNamespace(Status='Success')
            def Read(self,tag):return SimpleNamespace(Status='Success',Value=0)
        run=fixture.WordRun(Comm(),Path('unused.json'))
        run.guard=lambda:guards.append(1)
        run.observe=lambda phase:captures.append(phase)
        with patch.object(fixture.reader,'read_document',return_value=({},dict(manifest=dict(contentHash=fixture.publication.manifest_values(run.app)['ContentHash'])))), \
             patch.object(fixture.execute,'read_layout',side_effect=lambda *args:deepcopy(live)):
            evidence=run.execute()
        self.assertEqual(live,original);self.assertTrue(evidence['sourceRestored'])
        self.assertEqual({tag for tag,value in writes},run.allowed)
        self.assertTrue(all(type(v) is int for tag,v in writes))
        self.assertGreaterEqual(len(guards),len(writes))
        return evidence,writes,captures

    def test_all_nine_vectors_restore_all_words_and_use_ten_observations(self):
        e,w,c=self.run_fixture();self.assertTrue(e['passed']);self.assertEqual(len(e['rows']),9)
        self.assertEqual(len(w),80);self.assertEqual(len(c),10);self.assertEqual(c[-1],'source_restored')
        self.assertTrue(all(tag.startswith(fixture.SOURCE+'.') for tag,value in w))

    def test_partial_write_failure_restores_original_and_stops_vectors(self):
        e,w,c=self.run_fixture(failure=True);self.assertFalse(e['passed'])
        self.assertEqual(e['rows'],[]);self.assertEqual(len(w),12);self.assertEqual(c,['source_restored'])


if __name__=='__main__':unittest.main()
