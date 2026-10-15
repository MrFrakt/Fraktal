"""Authentication generation boundaries and simulator bootstrap refusal tests."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from fraktal_tia_binding import Catalog, REPO
import fraktal_tia_access as ACCESS
import fraktal_tia_declaration as DECL
import fraktal_tia_generate as GEN

spec = importlib.util.spec_from_file_location('unit_fixture_access', REPO/'FraktalCore/PLC/Siemens/Tests/Unit/make_fixture.py')
FIXTURE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(FIXTURE)
spec = importlib.util.spec_from_file_location('guard_plan_access', REPO/'FraktalCore/PLC/Siemens/Spikes/S12_TypeMap/run_plan.py')
PLAN = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PLAN)


class AccessTests(unittest.TestCase):
    def test_hash_authorities_are_bound_and_hidden_worker_contains_no_secret(self):
        sources, manifest = GEN.build(DECL.validate(FIXTURE.declaration()),True)
        self.assertTrue(set(ACCESS.inputs()).issubset(manifest['runtime']['authority_inputs']))
        worker = sources['02_FRK_Access.udt']
        self.assertNotIn('Secret',worker)
        for field in ('ProviderEnabled','Digest','Expected','Salt','CandidateUser'):
            row = next(line for line in worker.splitlines() if '"'+field+'"' in line)
            self.assertIn("ExternalAccessible := 'False'",row)
        table = sources['05_FRK_LocalUsers.db']
        self.assertIn('Array[1..%d]'%Catalog.read().capacities['MAX_USERS'],table)
        self.assertIn("ExternalAccessible := 'False'",table)

    def test_authored_logic_cannot_write_the_authority_or_assemble_its_cyclic_call(self):
        for body in ('#Access.CurrentLevel := 4;', '#Access.Policy.Required[2] := 0;',
                     '"FRK_AccessCyclic"(Access := #Access);',
                     '"FRK_AccessPolicies".Rows[1].Policy.Required[2] := 0;',
                     '"FRK_LocalUsers".Count := 1;', '"FRK_AccessStorage".UsersReady := TRUE;',
                     '"FRK_AccessUsersCommit"();', '"FRK_AccessRegisterHash"(Record := #ParCfg);'):
            value = FIXTURE.declaration()
            value['types'][0]['logic']['Cyclic'] = body
            with self.assertRaises(DECL.DeclarationError):
                GEN.build(DECL.validate(value),True)

    def test_service_names_cannot_be_shadowed_by_project_types(self):
        for name in ('FRK_AccessLogin','FRK_LocalUsers','FRK_Sha256Pin','FRK_AccessPolicies','FRK_AccessPolicyBoot'):
            value = FIXTURE.declaration()
            value['types'][2]['name'] = name
            value['types'][1]['children'][0]['type'] = name
            with self.assertRaises(DECL.DeclarationError):
                GEN.build(DECL.validate(value),True)

    def test_persistence_globals_cannot_shadow_deployed_root_names(self):
        for name in ('FRK_AccessPolicies', 'FRK_AccessStorage', 'FRK_AccessPolicySave'):
            value = FIXTURE.declaration()
            value['roots'][0]['name'] = name
            with self.assertRaises(DECL.DeclarationError):
                GEN.build(DECL.validate(value), True)

    def test_retained_adapter_preserves_narrow_core_and_root_bounds(self):
        value = FIXTURE.declaration()
        sources, manifest = GEN.build(DECL.validate(value), True)
        images = sources['05_FRK_AccessPolicies.db']
        self.assertIn('Array[1..%d]' % len(value['roots']), images)
        self.assertIn('VAR RETAIN', images)
        self.assertIn('VAR RETAIN', sources['05_FRK_LocalUsers.db'])
        # Sessions and mutable login worker buffers are never retained.
        self.assertIn('NON_RETAIN', sources['25_StationA.db'])
        self.assertNotIn('Secret', sources['05_FRK_LocalUsers.db'])
        self.assertTrue(set(ACCESS.inputs()).issubset(manifest['runtime']['authority_inputs']))

    def guard(self, status, empty=False, name='Fraktal'):
        with tempfile.TemporaryDirectory() as tmp:
            plan = Path(tmp)/'download.plan'
            plan.write_bytes(b'${download}\n')
            command = 'download=download --plc PLC_1 --confirm-target 169.254.212.49 --pc-interface "Siemens PLCSIM Virtual Ethernet Adapter" --pc-number 1 --target "1 X1"'
            result = SimpleNamespace(returncode=0,stdout=json.dumps(status).encode('ascii'))
            with patch.dict(os.environ,{'FRAKTAL_TIA_SIM_INSTANCE':name}), patch.object(PLAN.subprocess,'run',return_value=result):
                PLAN.guard_downloads(plan,[command],io.BytesIO(),empty)

    def test_empty_owner_requires_the_explicit_bootstrap_and_exact_stopped_target(self):
        status = {'name':'Fraktal','cpu':'CPU1500_Unspecified','state':'Stop','comm':'TCPIP',
                  'addresses':['169.254.212.49'],'ie1':0,'ie2':0,'ie3':0}
        with self.assertRaises(ValueError):
            self.guard(status)
        self.guard(status,True)
        for field,value in (('state','Run'),('name','FrkS12'),('comm','Softbus'),('ie1',1),
                            ('addresses',['192.168.0.10'])):
            with self.assertRaises(ValueError):
                self.guard({**status,field:value},True)

    def test_verified_second_cpu_interface_is_virtual_but_unknown_addresses_are_refused(self):
        status = {'name':'Fraktal','cpu':'CPU1516','state':'Run','comm':'TCPIP',
                  'addresses':['169.254.212.49','192.168.1.1'],'ie1':0,'ie2':0,'ie3':0}
        self.guard(status)
        with self.assertRaises(ValueError):
            self.guard({**status,'addresses':['169.254.212.49','192.168.0.10']})

    def test_explicit_trust_reaches_the_download_step_only(self):
        self.assertNotIn('--trust-plc',PLAN.download_substitution())
        self.assertIn('--trust-plc PLC_1',PLAN.download_substitution('PLC_1'))


if __name__ == '__main__':
    unittest.main()
