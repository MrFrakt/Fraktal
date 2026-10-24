"""Inherited 31-row fixture plus read-only decision, held and fault captures."""
import fraktal_ab_genealogy_execute as genealogy
import fraktal_ab_s3a_fixture_execute as shared
import fraktal_ab_s3b_equivalence as equivalence
import fraktal_ab_press_execute as execute
import fraktal_ab_generate as gen


def capture_gate(writer):
    """Keep observation reads independent of the mailbox's 500-byte framing."""
    if writer.IPAddress!='127.0.0.1' or writer.ProcessorSlot!=0:
        raise ValueError('fixed local Echo observer required')
    from pylogix import PLC
    with PLC(writer.IPAddress) as observer:
        observer.ProcessorSlot,observer.ConnectionSize,observer.SocketTimeout=0,4000,5
        report=equivalence.run(observer)
        report['fixtureObserver']=dict(independent=True,writerConnectionBytes=writer.ConnectionSize,
                                       readConnectionBytes=observer.ConnectionSize)
        return report


def paired_run(destination):
    parent=shared.paired_run(destination,gate=capture_gate,key='s3bDecisionPairs')
    class PairedRun(parent):
        def set(self,tag,value):
            observed={execute.HOLD['PressRam']:('held','PressRam'),
                      execute.FAULT['PartSlide']:('fault','PartSlide')}
            # The parent's exception handler marks error before cleanup. A
            # failed observation must never prevent its existing cleanup writes.
            if value==0 and tag in observed and not self.evidence.get('error'):
                response=self.comm.Read(tag)
                self.check(response.Status=='Success','condition stimulus read failed')
                if response.Value:
                    kind,module=observed[tag]
                    # Adoption drops the child's Execute and clears its local
                    # diagnostic. The Unit owns the latched first-out fault.
                    context=(execute.read_module(self.comm,module) if kind=='held'
                             else execute.read_unit(self.comm))
                    self.check(context is not None,'condition context read failed')
                    active=(context['OutImm_Reason'] and context['OutImm_Held'] if kind=='held'
                            else context['Error'] and context['DiagReason'])
                    if active:
                        language=execute.read_scalar(self.comm,gen.rendition_tag(self.app))
                        self.check(type(language) is int and language in (0,1,2),'condition rendition unavailable')
                        base=self.app.name+('/'+module if kind=='held' else '')+'/Status/Diagnostic/'
                        report=shared.capture_pair(self,destination,capture_gate,key='s3bConditionPairs',kind='condition',
                            metadata=dict(kind=kind,module=module,diagnosticPath=base,languageOrdinal=language))
                        values=report['pair']['canonical']['values']
                        self.check(values[base+'ReasonCode']!=0 and values[base+'Since']!=0,
                                   'active condition must preserve its reason and onset')
            return super().set(tag,value)
    return PairedRun


def main(argv=None):
    return genealogy.main(argv,run_type_factory=paired_run,schema='fraktal.ab.s3b-genealogy-fixture')


if __name__=='__main__':raise SystemExit(main())
