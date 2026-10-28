"""S3a engineering and independent acceptance-surface gates."""
from dataclasses import replace
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_canonical_publication as publisher
import fraktal_ab_canonical_unit_core as core
import fraktal_ab_genealogy_s3a_demo as candidate
import fraktal_ab_manifest as legacy
from fraktal_ab_s3a_equivalence import subset_paths


class UnitCoreTests(unittest.TestCase):
    def test_stage_preserves_legacy_identity_and_matches_independent_94_path_inventory(self):
        app=candidate.application();self.assertEqual(publisher.validate(app),[])
        self.assertEqual(legacy.content_hash(app),'6DEC4C1DC2F7F78A')
        root=Path(__file__).resolve().parents[4]
        inventory=json.loads((root/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3A_INVENTORY_2026-10-21.json').read_text())
        expected=set(inventory['paths'])
        self.assertEqual(subset_paths(app,[m.code for m in app.models],canonical=True),expected)
        self.assertEqual(len(subset_paths(app,['A','B','C','D'],canonical=True)),95)

    def test_physical_capacity_and_published_selection_are_separate_and_explicit(self):
        app=candidate.application();definitions=publisher.schema(app)
        root={m.name:m for m in definitions[publisher.root_type(app)]}
        self.assertEqual((root['ModePolicy'].count,root['ModePolicy'].indices),(7,(0,1,2,3)))
        self.assertEqual((root['SupportedModesPublished'].count,root['SupportedModesPublished'].extent),(32,7))
        self.assertEqual((root['AvailableModels'].count,root['AvailableModels'].lower,root['AvailableModels'].count_path),(8,1,'Press/AvailableModelCount'))
        self.assertEqual(definitions[core.PREFIX+'DecisionV61'][-1].extent,2)
        self.assertEqual(definitions[core.PREFIX+'DecisionV61'][-1].count,6)
        fields={r['CanonicalPath']:r for r in publisher.field_rows(app)}
        self.assertEqual(fields['Press/ModePolicy']['Indices'],'[0,1,2,3]')
        self.assertEqual(fields['Press/AvailableModels']['CountPath'],'Press/AvailableModelCount')
        self.assertIn('Press/AvailableModels[*]/ModelCode',fields)

    def test_sparse_modes_and_command_types_are_not_expanded_per_station_instance(self):
        app=candidate.application()
        app=replace(app,manual_mode=0,chains=tuple(replace(c,mode_ordinal=(1,3,6)[i]) for i,c in enumerate(app.chains)))
        fields={r['CanonicalPath']:r for r in publisher.field_rows(app)}
        self.assertEqual(fields['Press/SupportedModesPublished']['Indices'],'[0,1,3,6]')
        definitions=publisher.schema(app)
        leaves=[kind for kind in definitions if 'Leaf' in kind]
        self.assertEqual(len(leaves),2)
        self.assertEqual(core.leaf_type(app.modules[0]),core.leaf_type(app.modules[1]))
        empty=replace(app,manual_mode=None,chains=())
        fields={r['CanonicalPath']:r for r in publisher.field_rows(empty)}
        self.assertEqual(fields['Press/SupportedModesPublished']['Indices'],'[]')

    def test_native_bool_initial_values_and_core_widths_survive_generation(self):
        app=candidate.application();tag=ET.fromstring(publisher.tags(app)[0])
        flags=tag.find("Data/Structure/ArrayMember[@Name='SupportedModesPublished']")
        self.assertEqual([int(e.get('Value')) for e in flags][:7],[1,1,1,1,0,0,0])
        types=ET.fromstring('<Types>'+''.join(publisher.data_types(app))+'</Types>')
        self.assertIsNotNone(types.find("DataType[@Name='FRK_T_CanonicalString120V6']"))
        self.assertIsNotNone(types.find("DataType[@Name='FRK_T_CanonicalString64V6']"))
        too_wide=replace(app,decisions=(replace(app.decisions[0],option_keys=('X'*65,)),))
        self.assertTrue(core.validate(too_wide))

    def test_live_model_count_is_published_from_provider_and_private_indices_stay_outside_root(self):
        app=candidate.application();lines='\n'.join(publisher.cyclic(app))
        self.assertIn('Press.AvailableModelCount := FRK_Press_ModelCatalog.Count;',lines)
        self.assertIn('FRK_Press_ModelCatalog.CodeBytes[',lines)
        self.assertIn('Press.Decision.Default := FRK_Press_Unit.DecisionAnswer;',lines)
        self.assertIn('FRK_Press_Unit.DecisionId = 1',lines)
        self.assertNotIn('SSV(',lines)
        tags=ET.fromstring('<Tags>'+''.join(publisher.tags(app))+'</Tags>')
        private=[t.get('Name') for t in tags if t.get('ExternalAccess')=='None']
        self.assertEqual(private,['FRK_Press_CanonicalIndex','FRK_Press_CanonicalModelIndex',
                                  'FRK_Press_CanonicalModelCount','FRK_Press_CanonicalDecisionId'])


if __name__=='__main__':unittest.main()
