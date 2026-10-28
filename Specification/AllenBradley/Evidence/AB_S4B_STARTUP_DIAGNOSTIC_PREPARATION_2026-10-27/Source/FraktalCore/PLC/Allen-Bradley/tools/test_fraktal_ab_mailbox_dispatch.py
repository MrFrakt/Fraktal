"""Execute R4 against the released manual action/report behavior."""
from copy import deepcopy
from dataclasses import replace
import unittest

import fraktal_ab_genealogy_s3j_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_library as library
import fraktal_ab_mailbox as mailbox
import fraktal_ab_mailbox_dispatch as routes
import fraktal_ab_manifest as manifest
import fraktal_ab_st_model as st


class DispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old=replace(demo.application(),access_users=None)
        cls.app=replace(cls.old,canonical_publication_stage=13)
        cls.cache=st.parse('\n'.join(routes.cache(cls.app)))
        cls.routines={routes.find_routine(cls.app):routes.find(cls.app)}
        cls.keys={app.canonical_publication_stage:{r['NumericKey']:r['PortableKey']
                  for r in manifest.content(app)['Localization']} for app in (cls.old,cls.app)}
        cls.actions={app.canonical_publication_stage:st.parse('\n'.join([
            'CASE 11 OF',*mailbox.manual_command_dispatch(app),'ELSE','END_CASE;'])) for app in (cls.old,cls.app)}
        cls.reports={app.canonical_publication_stage:st.parse('\n'.join(mailbox.manual_report_lines(app)))
                     for app in (cls.old,cls.app)}
        cls.apply=st.parse('\n'.join(s for m in cls.app.modules for s in routes.apply(cls.app,m)))

    def controller(self,app,mode,target,command,busy):
        tags={gen.ctx_tag_for(app,m.name):st.structure(gen.module_context_members(library.type_of(m)))
              for m in app.modules}
        tags.update({f'{r.name}Tag':st.structure(r.members) for r in app.records})
        tags.update({name:0 for name in app.sim_inputs})
        tags[f'FRK_{app.name}_Unit']=st.structure(gen.unit_context_members(app))
        tags[f'FRK_{app.name}_Unit']['Mode']=mode
        tags[mailbox.request_tag_name(app)]={'DurationMs':target,'IntValue':command}
        tags[mailbox.response_tag_name(app)]={'Accepted':0,'DiagnosticKey':0}
        tags[gen.release_report_tag(app)]=st.structure(gen.release_report_members(app))
        for m in app.modules:
            ctx=tags[gen.ctx_tag_for(app,m.name)]
            ctx['Busy']=busy;ctx['Execute']=1;ctx['ManualCmd']=0
        if routes.enabled(app):
            modules,commands=routes.rows(app)
            tags[routes.modules_tag(app)]=deepcopy(modules)
            tags[routes.commands_tag(app)]=deepcopy(commands)
            tags[routes.work_tag(app)]=st.structure(routes.work_members())
        return st.Controller(tags,routines=self.routines if routes.enabled(app) else {})

    def test_manual_actions_match_for_every_target_command_mode_and_busy_state(self):
        targets=(-1,0,*range(1,len(self.app.modules)+2),2147483647)
        for mode in (0,self.app.manual_mode):
            for target in targets:
                for command in (-1,0,1,2,99):
                    for busy in (0,1):
                        with self.subTest(mode=mode,target=target,command=command,busy=busy):
                            old=self.controller(self.old,mode,target,command,busy)
                            new=self.controller(self.app,mode,target,command,busy)
                            old.run(self.actions[12]);new.run(self.cache);new.run(self.actions[13]);new.run(self.apply)
                            a=old.tags[mailbox.response_tag_name(self.old)];b=new.tags[mailbox.response_tag_name(self.app)]
                            self.assertEqual(a['Accepted'],b['Accepted'])
                            self.assertEqual(self.keys[12].get(a['DiagnosticKey'],''),self.keys[13].get(b['DiagnosticKey'],''))
                            for m in self.app.modules:
                                name=gen.ctx_tag_for(self.app,m.name)
                                self.assertEqual(old.tags[name],new.tags[name])
                            self.assertTrue(all(row['Pending']==0 for row in new.tags[routes.modules_tag(self.app)]))

    def test_manual_reports_match_the_existing_permit_and_busy_rules(self):
        for mode in (0,self.app.manual_mode):
            for target in (-1,0,*range(1,len(self.app.modules)+2)):
                for command in (-1,1,2,99):
                    for busy in (0,1):
                        with self.subTest(mode=mode,target=target,command=command,busy=busy):
                            old=self.controller(self.old,mode,target,command,busy)
                            new=self.controller(self.app,mode,target,command,busy)
                            old.run(self.reports[12]);new.run(self.cache);new.run(self.reports[13])
                            a=old.tags[gen.release_report_tag(self.old)];b=new.tags[gen.release_report_tag(self.app)]
                            self.assertEqual((a['Released'],a['Count']),(b['Released'],b['Count']))
                            for key in ('Key','Reason','Source','Kind'):
                                av=a[key][:a['Count']];bv=b[key][:b['Count']]
                                if key=='Key':
                                    av=[self.keys[12].get(x,'') for x in av]
                                    bv=[self.keys[13].get(x,'') for x in bv]
                                self.assertEqual(av,bv)
                            self.assertEqual(b['Overflow'],0)

    def test_corrupt_descriptor_refuses_without_an_out_of_range_read(self):
        target=next(i for i,m in enumerate(self.app.modules,1) if m.commands)
        for first,count in ((-1,1),(2147483647,1),(0,2147483647),(0,-1)):
            with self.subTest(first=first,count=count):
                c=self.controller(self.app,self.app.manual_mode,target,1,0)
                c.tags[routes.modules_tag(self.app)][target-1].update(FirstSlot=first,CommandCount=count)
                c.run(self.actions[13]);answer=c.tags[mailbox.response_tag_name(self.app)]
                self.assertEqual(answer['Accepted'],0)
                self.assertEqual(answer['DiagnosticKey'],manifest.numeric_key(self.app,mailbox.TARGET_KEY))

    def test_generation_wires_the_same_scan_queue_automatically(self):
        # Session/configuration cyclic work can change a permit's inputs. The
        # cache must follow that prologue, immediately before dispatch.
        handler=mailbox.handler_logic(self.app,use_routines=True)
        case=handler.index(f'CASE {mailbox._request(self.app,"Kind")} OF')
        self.assertEqual(handler[case-1],f'JSR({routes.cache_routine(self.app)},0);')
        modules='\n'.join(next(body for name,body in gen.scan_sections(self.app) if name and name.endswith('Modules')))
        for module in self.app.modules:
            if module.commands:
                self.assertIn('\n'.join(routes.apply(self.app,module)),modules)
        self.assertEqual(routes.records(self.old),[])
        self.assertEqual(routes.tags(self.old),[])


if __name__=='__main__':unittest.main()
