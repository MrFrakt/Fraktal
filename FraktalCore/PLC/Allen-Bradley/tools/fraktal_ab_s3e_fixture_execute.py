"""31 inherited rows plus two explicit Access vectors and read-only captures.

Requires current authorization for this exact S3e fixture, including a fixed
unknown-user login and one data-class edit/restoration. No arbitrary writes.
"""
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_mailbox as mailbox
import fraktal_ab_projection as projection
import fraktal_ab_access as access
import fraktal_ab_s3a_fixture_execute as capture
import fraktal_ab_s3b_fixture_execute as observer
import fraktal_ab_s3d_fixture_execute as previous
import fraktal_ab_s3e_equivalence as equivalence

UNKNOWN_USER='fraktal_s3e_no_user'
NEGATIVE_SECRET='denied_fixture'


def paired_run(destination,*,gate=None,prefix='s3e',base=None):
    selected=equivalence.run if gate is None else gate
    parent=previous.paired_run(destination,gate=selected,prefix=prefix,base=base)
    class AccessRun(parent):
        def access_pair(self,phase):
            return capture.capture_pair(self,destination,
                lambda writer:observer.capture_gate(writer,selected),
                key=prefix+'AccessPairs',kind='access',metadata=dict(phase=phase))

        def command(self,kind,**arguments):
            answer=super().command(kind,**arguments)
            # Never record arguments: LOGIN includes a transported secret.
            if not self.evidence.get('error'):
                if kind==mailbox.LOGIN and not getattr(self,'_s3e_busy_captured',False):
                    self._s3e_busy_captured=True
                    report=self.access_pair('login_busy')
                    self.check(report['pair']['canonical']['values'][self.app.name+'/Access/LoginBusy'],
                               'bounded login must be observed busy')
                elif kind==mailbox.LOGOUT and not getattr(self,'_s3e_logout_captured',False):
                    self._s3e_logout_captured=True
                    report=self.access_pair('logged_out')
                    values=report['pair']['canonical']['values']
                    self.check(values[self.app.name+'/Access/CurrentLevel']==0 and
                               values[self.app.name+'/Access/CurrentUser']=='','logout must remove authority')
            return answer

        def login(self):
            normal=not self.evidence.get('error')
            if normal and not getattr(self,'_s3e_negative_done',False):
                self._s3e_negative_done=True
                self.check(UNKNOWN_USER not in {u.name for u in self.app.access_users},'negative fixture identity unexpectedly registered')
                self.command(mailbox.LOGIN,User=UNKNOWN_USER,Secret=NEGATIVE_SECRET)
                def failed():
                    state=projection.read_access(self.comm)
                    return state if state and not state['LoginBusy'] and state['LoginFailed'] else None
                state=self.wait(failed,'unknown-user login refusal',timeout=15)
                self.check(state['CurrentLevel']==0 and state['UserLength']==0,'unknown user must never acquire authority')
                report=self.access_pair('login_failed')
                self.check(report['pair']['canonical']['values'][self.app.name+'/Access/LoginFailed'],'failed login must be published')
                self.evidence.setdefault(prefix+'AccessRows',[]).append(dict(case='unknown_user_login_refused',passed=True))
            super().login()
            if normal and not getattr(self,'_s3e_authenticated_captured',False):
                self._s3e_authenticated_captured=True
                report=self.access_pair('authenticated')
                values=report['pair']['canonical']['values'];base=self.app.name+'/Access/'
                self.check(not values[base+'LoginBusy'] and not values[base+'LoginFailed'] and
                    values[base+'CurrentUser']==self.account['user'] and values[base+'CurrentLevel']==self.account['level'],
                    'published authentication result must match controller authority')
                self.class_policy_vector()

        def class_policy_vector(self):
            # One declared class, one read-level field, then its exact original.
            # A failure cannot bypass restoration; cleanup has no observations.
            self.check(bool(self.app.data_classes),'class-policy fixture requires one class')
            index=len(self.app.data_classes)-1;identity=self.app.data_classes[index].class_id
            before=projection.read_data_access(self.comm,policy=True)
            self.check(before is not None and before['Count']>index,'class policy is unavailable')
            original=before['ReadLevel'][index];changed=(original+1)%5
            attempted=False
            try:
                attempted=True
                self.command(mailbox.SET_CLASS_LEVEL,NameValue=identity,IntValue=changed,BoolValue=False)
                report=self.access_pair('class_policy_changed')
                self.check(report['pair']['canonical']['values'][f'{self.app.name}/Access/Classes[{index+1}]/ReadLevel']==changed,
                           'changed class policy must be published')
            finally:
                if attempted:
                    # Use the parent command, so an observation failure cannot
                    # re-enter this test or block its restoration write.
                    super().command(mailbox.SET_CLASS_LEVEL,NameValue=identity,IntValue=original,BoolValue=False)
                    restored=projection.read_data_access(self.comm,policy=True)
                    self.check(restored==before,'class-policy vector did not restore exact policy')
            report=self.access_pair('class_policy_restored')
            self.check(report['pair']['canonical']['values'][f'{self.app.name}/Access/Classes[{index+1}]/ReadLevel']==original,
                       'restored class policy must be published')
            self.evidence.setdefault(prefix+'AccessRows',[]).append(dict(case='class_policy_change_restore',passed=True,classIndex=index+1,
                originalReadLevel=original,temporaryReadLevel=changed))
    return AccessRun


def main(argv=None):return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3e-genealogy-fixture')
if __name__=='__main__':raise SystemExit(main())
