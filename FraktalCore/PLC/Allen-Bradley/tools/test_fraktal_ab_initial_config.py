"""Commissioned catalogs survive generated downloads without changing layout."""
import copy
import dataclasses
import re
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_generate as gen
import fraktal_ab_initial_config as image_module
import fraktal_ab_models as models
import fraktal_ab_press_demo as demo
from test_fraktal_ab_capture import initial
from test_fraktal_ab_sets import controller

APP = demo.application()


def image():
    result = {'records': {r.name: initial(r.members) for r in APP.records},
              'models': [initial(m) for m in gen.model_cfg_elements(APP)[:len(APP.models)]],
              'modelOrdinal': 1}
    for record in APP.records:
        result['records'][record.name]['SchemaVersion'] = record.schema_version
    for bank in result['models']:
        bank['SchemaVersion'] = gen.model_cfg_schema_version(APP)
    return result


def expanded_image():
    result = image()
    result['modelCodes'] = [m.code for m in APP.models] + ['M-101']
    result['models'].append(copy.deepcopy(result['models'][0]))
    result['models'][3]['PressDwellMs'] = 451
    return result


def decorated_value(node):
    if node.tag == 'Structure':
        return {child.attrib['Name']: decorated_value(child) for child in node}
    if node.tag == 'ArrayMember':
        return [int(child.attrib['Value']) for child in node]
    if node.tag == 'Array':
        return [decorated_value(child[0]) for child in node]
    return int(node.attrib['Value'])


class CommissionedCatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = gen.controller_tags(APP)

    def apply(self, proposal):
        return image_module.apply(APP, self.original, proposal)

    def test_fourth_recipe_and_code_survive_the_generated_boot_restore(self):
        applied = self.apply(expanded_image())
        c = controller()
        xml = ET.fromstring(applied)
        for name in (models.tag(APP), gen.model_cfg_tag(APP)):
            tag = xml.find(f'./Tag[@Name="{name}"]')
            c.tags[name] = decorated_value(tag.find('./Data')[0])
            self.assertEqual(tag.attrib['ExternalAccess'], 'Read Only')
        c.run('\n'.join(gen._model_restore_logic(APP, gen.config_persist_tag(APP))))
        self.assertEqual(models.decode(APP, c.tags[models.tag(APP)]),
                         ['M-100', 'M-200', 'M-050', 'M-101'])
        self.assertEqual(c.tags[gen.model_cfg_tag(APP)][3]['PressDwellMs'], 451)
        self.assertEqual(c.tags[gen.config_persist_tag(APP)]['RestoreLost'], 0)
        self.assertEqual(c.tags[models.tag(APP)]['CodeLength'][4:], [0] * 4)
        self.assertEqual(c.tags[models.tag(APP)]['CodeBytes'][4 * models.CODE_MAX:],
                         [0] * (4 * models.CODE_MAX))

    def test_expanded_active_model_keeps_its_ordinal_and_live_recipe(self):
        proposal = expanded_image()
        proposal['modelOrdinal'] = 4
        par_cfg = next(r for r in APP.records if r.par_cfg)
        proposal['records'][par_cfg.name]['PressDwellMs'] = 451
        applied = ET.fromstring(self.apply(proposal))
        unit = applied.find('./Tag[@Name="FRK_Press_Unit"]/Data/Structure')
        self.assertEqual(decorated_value(unit)['ModelOrdinal'], 4)
        cfg = applied.find(f'./Tag[@Name="{par_cfg.name}Tag"]/Data/Structure')
        self.assertEqual(decorated_value(cfg)['PressDwellMs'], 451)
        proposal['records'][par_cfg.name]['PressDwellMs'] = 450
        with self.assertRaisesRegex(ValueError, 'active recipe'):
            self.apply(proposal)

    def test_full_catalog_is_preserved_with_stable_indices(self):
        proposal = expanded_image()
        for index in range(4, APP.model_capacity):
            proposal['modelCodes'].append('MODEL-' + str(index))
            bank = copy.deepcopy(proposal['models'][0])
            bank['PressDwellMs'] = 500 + index
            proposal['models'].append(bank)
        xml = ET.fromstring(self.apply(proposal))
        catalog = decorated_value(xml.find(f'./Tag[@Name="{models.tag(APP)}"]/Data')[0])
        self.assertEqual(models.decode(APP, catalog), proposal['modelCodes'])
        banks = decorated_value(xml.find(f'./Tag[@Name="{gen.model_cfg_tag(APP)}"]/Data')[0])
        self.assertEqual(banks, proposal['models'])

    def test_invalid_last_bank_or_catalog_never_produces_a_download_image(self):
        mutations = {
            'duplicate': lambda d: d['modelCodes'].__setitem__(3, 'M-100'),
            'renumber': lambda d: d['modelCodes'].__setitem__(0, 'OTHER'),
            'blank': lambda d: d['modelCodes'].__setitem__(3, ''),
            'space': lambda d: d['modelCodes'].__setitem__(3, 'BAD CODE'),
            'non-ascii': lambda d: d['modelCodes'].__setitem__(3, 'M-\u00f1'),
            'too-long': lambda d: d['modelCodes'].__setitem__(3, 'X' * 81),
            'not-text': lambda d: d['modelCodes'].__setitem__(3, 123),
            'missing-bank': lambda d: d['models'].pop(),
            'missing-code': lambda d: d.pop('modelCodes'),
            'ordinal': lambda d: d.__setitem__('modelOrdinal', 5),
            'bool-ordinal': lambda d: d.__setitem__('modelOrdinal', True),
            'schema': lambda d: d['models'][3].__setitem__('SchemaVersion', 99),
            'value': lambda d: d['models'][3].__setitem__('PressDwellMs', 2147483647),
            'extra-member': lambda d: d['models'][3].__setitem__('Execute', 1),
            'credentials': lambda d: d.__setitem__('AccessProvider', {'PIN': 'invalid'}),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                proposal = expanded_image()
                mutate(proposal)
                with self.assertRaises(ValueError):
                    self.apply(proposal)
        proposal = expanded_image()
        proposal['modelCodes'] += ['X' + str(i) for i in range(APP.model_capacity)]
        proposal['models'] += [copy.deepcopy(proposal['models'][0]) for _ in range(APP.model_capacity)]
        with self.assertRaises(ValueError):
            self.apply(proposal)

    def test_no_layout_or_frozen_string_serialization_changes(self):
        applied = self.apply(expanded_image())
        original = ET.fromstring(self.original)
        updated = ET.fromstring(applied)
        self.assertEqual([(n.attrib, [x.attrib for x in n.findall('.//ArrayMember')])
                          for n in original],
                         [(n.attrib, [x.attrib for x in n.findall('.//ArrayMember')])
                          for n in updated])
        allowed = {r.name + 'Tag' for r in APP.records} | {
            models.tag(APP), gen.model_cfg_tag(APP), 'FRK_Press_Unit'}
        tag_pattern = r'<Tag Name="([^"]+)".*?</Tag>'
        before = {m.group(1): m.group() for m in re.finditer(tag_pattern, self.original, re.S)}
        after = {m.group(1): m.group() for m in re.finditer(tag_pattern, applied, re.S)}
        self.assertEqual(before.keys(), after.keys())
        for name in before.keys() - allowed:
            self.assertEqual(before[name], after[name], name)
        self.assertEqual(re.findall(r'<!\[CDATA\[.*?\]\]>', self.original, re.S),
                         re.findall(r'<!\[CDATA\[.*?\]\]>', applied, re.S))

    def test_old_three_bank_images_keep_the_existing_boot_initialization(self):
        old = self.apply(image())
        pattern = rf'<Tag Name="{models.tag(APP)}".*?</Tag>'
        self.assertEqual(re.search(pattern, old, re.S).group(),
                         re.search(pattern, self.original, re.S).group())
        # An explicit seed catalog differs only by initializing its already
        # declared catalog. Legacy images leave that to the existing boot path.
        seed = image()
        seed['modelCodes'] = [m.code for m in APP.models]
        explicit = self.apply(seed)
        self.assertNotEqual(old, explicit)
        static = dataclasses.replace(APP, model_capacity=0)
        self.assertEqual(image_module.apply(static, gen.controller_tags(static), image()),
                         image_module.apply(static, gen.controller_tags(static), seed))
        seed['modelCodes'].append('EXTRA')
        seed['models'].append(copy.deepcopy(seed['models'][0]))
        with self.assertRaises(ValueError):
            image_module.apply(static, gen.controller_tags(static), seed)


if __name__ == '__main__':
    unittest.main()
