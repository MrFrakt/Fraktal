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
