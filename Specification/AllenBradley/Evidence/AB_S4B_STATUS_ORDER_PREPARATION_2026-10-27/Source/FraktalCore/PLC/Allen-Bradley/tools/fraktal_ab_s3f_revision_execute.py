"""S3f follow-up: fixed model CHANGEOVER round trip, with exact live restore.

Separate current authorization must include both simulated CHANGEOVER runs and
their existing tooling confirmation. The public mailbox owns model selection;
private ModelRequest is never written. This is bench apparatus, not a client.
"""
from copy import deepcopy
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_s3f_fixture_execute as previous
import fraktal_ab_part_execute as base
import fraktal_ab_press_execute as execute
import fraktal_ab_press_demo as press
import fraktal_ab_projection as projection
import fraktal_ab_generate as gen
import fraktal_ab_mailbox as mb
import fraktal_ab_models as models


def paired_run(destination):
    parent=previous.paired_run(destination)
    class RevisionRun(parent):
        def command(self,kind,**args):
            if getattr(self,'_revision_cleaning',False):return self.native_command(kind,**args)
            return super().command(kind,**args)

        def set(self,tag,value):
            if getattr(self,'_revision_cleaning',False):return base.Run.set(self,tag,value)
            return super().set(tag,value)

        def native_command(self,kind,**args):return base.Run.command(self,kind,**args)

        def revision_snapshot(self):
            codes=models.read(self.comm,self.app)
            records=projection.read_records(self.comm)
            banks=projection.read_models(self.comm,len(codes)) if codes else None
            inputs={tag:execute.read_scalar(self.comm,tag) for tag in gen.externally_writable(self.app)}
            self.check(bool(records) and all(v is not None for v in records.values()) and banks is not None
                       and all(v is not None for v in inputs.values()),'model snapshot incomplete')
            return dict(records=deepcopy(records),banks=deepcopy(banks),codes=codes,
                        inputs=inputs,mode=self.unit()['Mode'],active=self.unit()['ModelOrdinal'])

        def restore_configuration(self):
            super().restore_configuration()
            if not self.evidence.get('error') and not getattr(self,'_revision_vector_started',False):
                self._revision_vector_started=True
                self.active_model_vector()

        def changeover(self,target,*,observe=True):
            self.idle()
            self.native_command(mb.SET_MODE,IntValue=press.MODE_CHANGEOVER)
            self.native_command(mb.SET_MODEL,IntValue=target)
            self.native_command(mb.START)
            def prompt():
                unit=self.unit()
                self.check(not unit['Error'],'model CHANGEOVER faulted')
                return unit if unit['DecisionId']==press.DECISION_CHANGEOVER_CONFIRM else None
            self.wait(prompt,'fixed CHANGEOVER tooling confirmation')
            if observe:self.config_pair('active_model_confirmation')
            # This is the same public decision answer as the fixture's AUTO
            # decisions; avoid classifying it as one of the four AUTO pairs.
            self.native_command(mb.DECISION_ANSWER,IntValue=1)
            self.wait(lambda:self.unit()['Complete'] and self.unit()['ModelOrdinal']==target,'model commit')
            self.idle()
            self.native_command(mb.SET_MODE,IntValue=self.app.manual_mode)

        def active_model_vector(self):
            saved=self.revision_snapshot();original=saved['active']
            self.check(1<=original<=len(saved['codes']) and len(saved['codes'])>=2,'two valid model banks required')
            target=next(i for i in range(1,len(saved['codes'])+1) if i!=original)
            before=self.config_pair('active_model_before')['pair']['canonical']['values'][self.app.name+'/Status/ConfigRev']
            try:
                self.home()
                self.changeover(target)
                changed=self.config_pair('active_model_changed')['pair']['canonical']['values']
                self.check(changed[self.app.name+'/Model/ModelCode']==saved['codes'][target-1], 'active model not published')
                self.check(changed[self.app.name+'/Status/ConfigRev']!=before,'active model commit must change revision')
                self.changeover(original)
            finally:
                # Observation failure cannot prevent the existing public
                # cleanup/recipe writes or re-enter a failed observation.
                self._revision_cleaning=True
                try:
                    self.idle()
                    if self.unit()['ModelOrdinal']!=original:self.changeover(original,observe=False)
                    for ordinal,record,member in gen.editable_values(self.app):
                        if gen.is_model_scoped(self.app,record,member.name):
                            self.native_command(mb.WRITE_CONFIG,**{mb.CONFIG_ORDINAL_MEMBER:ordinal,
                                mb.CONFIG_VALUE_MEMBER:saved['records'][record.name][member.name]})
                    self.native_command(mb.SET_MODE,IntValue=saved['mode'])
                    for tag,value in saved['inputs'].items():self.set(tag,value)
                finally:self._revision_cleaning=False
                restored=self.revision_snapshot()
                self.check(restored==saved,'model vector did not restore live configuration/banks/inputs/mode')
            self.config_pair('active_model_restored')
            self.evidence.setdefault('s3fRevisionRows',[]).append(dict(case='active_model_revision_and_exact_restore',
                passed=True,originalModel=original,temporaryModel=target))
    return RevisionRun


def main(argv=None):return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3f-revision-fixture')
if __name__=='__main__':raise SystemExit(main())
