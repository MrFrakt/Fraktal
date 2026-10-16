"""Declaration boundaries and generic mapping authority for the sequence view."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN
import fraktal_tia_examples as EX
import tia_lint

spec=importlib.util.spec_from_file_location('view_fixture',Path(__file__).resolve().parents[1]/'Tests/SequenceView/make_fixture.py')
FIXTURE=importlib.util.module_from_spec(spec);spec.loader.exec_module(FIXTURE)


class SequenceViewTests(unittest.TestCase):
    def value(self):
        value=FIXTURE.CONFIG.declaration()
        value['types'][0]['sequence_view']={'capacity':4,'branches':2,'annotations':2}
        return value

    def test_profile_bounds_and_owner_are_checked(self):
        for field,invalid in [('capacity',0),('capacity',129),('branches',-1),('branches',10),('annotations',0),('annotations',17),('capacity',True)]:
            value=self.value();value['types'][0]['sequence_view'][field]=invalid
            with self.subTest(field=field,invalid=invalid),self.assertRaises(DECL.DeclarationError):DECL.validate(value)
        value=self.value();value['types'][2]['sequence_view']=value['types'][0].pop('sequence_view')
        with self.assertRaises(DECL.DeclarationError):DECL.validate(value)

    def test_unselected_units_pay_no_view_storage(self):
        sources,_=GEN.build(DECL.validate(FIXTURE.CONFIG.declaration()),True)
        self.assertFalse(any('SequenceView' in n for n in sources))
        self.assertFalse(any('SequenceStepCount' in s for s in sources.values()))
        self.assertFalse(any('FRK_Diagnostics' in s for s in sources.values()))

    def test_diagnostic_samples_are_scoped_to_consumed_descendants(self):
        from fraktal_tia_diagnostics import consumers
        value=FIXTURE.CONFIG.declaration()
        value['types'][4]['sequence_view']={'capacity':4,'branches':2,'annotations':2}
        model=DECL.validate(value);nodes=consumers(model)
        self.assertTrue(nodes)
        self.assertTrue(all('.Satellite' in n.path for n in nodes))
        sources,_=GEN.build(model,True)
        self.assertIn('Array[1..'+str(len(nodes))+'] of "FRK_DiagSample"',sources['08_FRK_Diagnostics.db'])
        self.assertLess(len(nodes),model.registry_capacity)

    def test_pending_is_readonly_and_diagnostic_work_is_frame_owned(self):
        value=self.value();sources,_=GEN.build(DECL.validate(value),True)
        text=next(s for n,s in sources.items() if n.endswith(value['types'][0]['name']+'.scl'))
        frame=next(b for b in tia_lint.parse_blocks(text) if b.name==value['types'][0]['name'])
        self.assertIn('Pending',{d.name for d in frame.decls})
        self.assertLess(text.index('"FRK_SeqViewDiagnostic"'),text.index('"FRK_End"'))
        self.assertLess(text.index('"FRK_End"'),text.index('"FRK_DiagSync"'))
        self.assertIn('Pending := #Pending',text)

    def test_project_cannot_replace_pending_publication(self):
        value=self.value();value['types'][0]['logic']['cyclic']='#Pending.ReasonCode := 1;'
        with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)

    def test_snapshot_capture_does_not_borrow_readonly_config(self):
        sources,_,_=EX.build()
        text=sources['20_000_FB_CylinderCM.scl']
        helper=text.split('END_FUNCTION',1)[0]
        self.assertNotIn('"FRK_DiagSync"',helper)
        self.assertNotIn('ParCfg :',helper)
        frame=text.split('FUNCTION_BLOCK "FB_CylinderCM"',1)[1]
        self.assertIn('// ---- GENERATED: diagnostic snapshot',frame)
        self.assertIn('Held := #Core.Held',frame)
        self.assertLess(frame.index('"FRK_CyclicHook_CylinderCM"'),frame.index('"FRK_DiagSync"'))

    def test_consumed_arrays_readonly_and_defs_private(self):
        value=self.value();sources,manifest=GEN.build(DECL.validate(value),True)
        name=value['types'][0]['name']
        text=next(s for n,s in sources.items() if n.endswith(name+'.scl'))
        blocks=tia_lint.parse_blocks(text);frame=next(b for b in blocks if b.name==name)
        members={d.name:d for d in frame.decls}
        self.assertEqual(members['ActiveSteps'].type_text,'Array[0..2] of "ST_SequenceCursor"')
        self.assertIn('Array[1..4] of "ST_SequenceStep"',text)
        self.assertIn('SequenceStepDef',text)
        self.assertIn('ExternalAccessible',text)
        self.assertIn('ST_SequenceStepDef',manifest['types'])
        self.assertIn('SequenceSteps/SequenceSteps[',sources['17_SequenceView.scl'])
        self.assertNotIn('@',sources['17_SequenceView.scl'])
        self.assertEqual(tia_lint.check_ext(Path('view.scl'),frame,{t.name for t in DECL.validate(value).types}),[])

    def test_roundtrip_and_replay_cover_profile_and_template(self):
        value=self.value();model=DECL.validate(value)
        self.assertEqual(DECL.validate(GEN.definition(model)),model)
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'sources';GEN.generate(model,out,True);self.assertGreater(GEN.verify(out),0)
            p=out/'17_SequenceView.scl';p.write_bytes(p.read_bytes().replace(b'#Depth >=',b'#Depth >'))
            with self.assertRaises(DECL.DeclarationError):GEN.verify(out)

    def test_application_cannot_bypass_view_boundary(self):
        value=self.value();value['types'][0]['logic']['cyclic']='#SequenceStepCount := 0;'
        with self.assertRaises(DECL.DeclarationError):GEN.build(DECL.validate(value),True)
        value=self.value();value['types'][0]['children'][0]['name']='ActiveSteps'
        with self.assertRaises(DECL.DeclarationError):DECL.validate(value)

    def test_press_projection_is_declared_once_and_main_stays_three_calls(self):
        sources,definition,_=EX.build()
        load=definition['load_position']
        projected={s['no']+load['view_offset'] for s in load['steps']}
        main={s['no'] for s in definition['chains'][0]['steps']}|{s['no'] for s in definition['graph_auto']['auxiliary_steps']}
        self.assertFalse(projected & main)
        self.assertEqual(len(main|projected),definition['sequence_view']['capacity'])
        body=sources['40_PressDemoMain.scl'].split('BEGIN\n',1)[1]
        self.assertEqual(body.count('();'),2);self.assertEqual(body.count('Startup :='),1)
        self.assertIn('ViewOffset := '+str(load['view_offset']),sources['23_00_FB_PressDemoLoadPosition.scl'])


if __name__=='__main__':unittest.main()
