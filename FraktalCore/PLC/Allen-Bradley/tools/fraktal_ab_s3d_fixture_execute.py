"""Inherited 31 rows plus read-only alarm observations around existing resets."""
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mailbox
import fraktal_ab_press_execute as execute
import fraktal_ab_s3a_fixture_execute as capture
import fraktal_ab_s3b_fixture_execute as observer
import fraktal_ab_s3c_fixture_execute as previous
import fraktal_ab_s3d_equivalence as equivalence


def paired_run(destination,*,gate=None,prefix='s3d',base=None):
    selected=equivalence.run if gate is None else gate
    parent=previous.paired_run(destination,gate=selected,prefix=prefix,base=base)
    class AlarmRun(parent):
        def command(self,kind,**arguments):
            before=False
            if kind==mailbox.OPERATOR_RESET and not self.evidence.get('error'):
                blocking=execute.read_scalar(self.comm,gen.alarm_active_tag(self.app)+'.Blocking')
                self.check(blocking is not None,'pre-reset blocking read failed')
                before=bool(blocking)
                if before:self.alarm_pair('before')
            answer=super().command(kind,**arguments)
            if before:self.alarm_pair('after')
            return answer

        def alarm_pair(self,phase):
            language=execute.read_scalar(self.comm,gen.rendition_tag(self.app))
            self.check(type(language) is int and language in (0,1,2),'reset rendition unavailable')
            report=capture.capture_pair(self,destination,
                lambda writer:observer.capture_gate(writer,selected),key=prefix+'ResetPairs',kind='reset',
                metadata=dict(phase=phase,languageOrdinal=language))
            values=report['pair']['canonical']['values']
            self.check(values[self.app.name+'/AlarmLog/Blocking']==(phase=='before'),
                       'one operator reset must release the blocking latch')
            return report
    return AlarmRun


def main(argv=None):
    return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3d-genealogy-fixture')


if __name__=='__main__':raise SystemExit(main())
