"""Access vectors are bounded and always restore their temporary policy edit."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import fraktal_ab_s3e_fixture_execute as fixture


class AccessFixtureTests(unittest.TestCase):
    def runner(self):
        events=[];policy=dict(SchemaVersion=1,Count=1,ReadLevel=[0],WriteLevel=[0])
        class Parent:
            def command(self,kind,**arguments):
                events.append((kind,arguments))
                if kind==fixture.mailbox.SET_CLASS_LEVEL:policy['ReadLevel'][0]=arguments['IntValue']
                return dict(accepted=True)
            def login(self):self.command(fixture.mailbox.LOGIN,User='admin',Secret='fixture')
            def check(self,ok,message):
                if not ok:raise RuntimeError(message)
            def wait(self,predicate,label,timeout):return predicate()
        with patch.object(fixture.previous,'paired_run',return_value=Parent):
            run=object.__new__(fixture.paired_run(Path('unused.json')))
        run.app=SimpleNamespace(name='Press',access_users=[SimpleNamespace(name='admin')],data_classes=[SimpleNamespace(class_id='commissioning')])
        run.account=dict(user='admin',level=4);run.comm=object();run.evidence={}
        def pair(phase):
            values={'Press/Access/LoginBusy':phase=='login_busy','Press/Access/LoginFailed':phase=='login_failed',
                'Press/Access/CurrentUser':'' if phase in ('logged_out','login_failed','login_busy') else 'admin',
                'Press/Access/CurrentLevel':0 if phase in ('logged_out','login_failed','login_busy') else 4,
                'Press/Access/Classes[1]/ReadLevel':policy['ReadLevel'][0]}
            return dict(pair=dict(canonical=dict(values=values)))
        run.access_pair=pair
        return run,events,policy

    def test_only_one_negative_login_and_one_class_edit_restoration(self):
        run,events,policy=self.runner()
        with patch.object(fixture.projection,'read_access',return_value=dict(LoginBusy=0,LoginFailed=1,CurrentLevel=0,UserLength=0)), \
             patch.object(fixture.projection,'read_data_access',side_effect=lambda *a,**k:deepcopy(policy)):
            run.login();run.login()
        self.assertEqual([kind for kind,args in events],[fixture.mailbox.LOGIN,fixture.mailbox.LOGIN,fixture.mailbox.SET_CLASS_LEVEL,fixture.mailbox.SET_CLASS_LEVEL,fixture.mailbox.LOGIN])
        self.assertEqual(events[0][1]['User'],fixture.UNKNOWN_USER)
        self.assertEqual([args['IntValue'] for kind,args in events if kind==fixture.mailbox.SET_CLASS_LEVEL],[1,0])
        self.assertEqual(policy['ReadLevel'],[0])
        self.assertEqual(len(run.evidence['s3eAccessRows']),2)

    def test_failed_class_observation_cannot_bypass_policy_restoration(self):
        run,events,policy=self.runner()
        run.access_pair=lambda phase:(_ for _ in ()).throw(ValueError('comparison failed'))
        with patch.object(fixture.projection,'read_data_access',side_effect=lambda *a,**k:deepcopy(policy)):
            with self.assertRaisesRegex(ValueError,'comparison failed'):run.class_policy_vector()
        self.assertEqual(policy['ReadLevel'],[0])
        self.assertEqual([args['IntValue'] for kind,args in events],[1,0])

    def test_cleanup_skips_access_observations_and_additional_vectors(self):
        run,events,policy=self.runner();run.evidence['error']='prior observation failed'
        run.access_pair=lambda phase:(_ for _ in ()).throw(AssertionError('cleanup cannot observe'))
        run.login();run.command(fixture.mailbox.LOGOUT)
        self.assertEqual([kind for kind,args in events],[fixture.mailbox.LOGIN,fixture.mailbox.LOGOUT])
        self.assertNotIn('s3eAccessRows',run.evidence)

    def test_negative_identity_collision_is_refused_before_any_write(self):
        run,events,policy=self.runner();run.app.access_users.append(SimpleNamespace(name=fixture.UNKNOWN_USER))
        with self.assertRaisesRegex(RuntimeError,'unexpectedly registered'):run.login()
        self.assertFalse(events)
