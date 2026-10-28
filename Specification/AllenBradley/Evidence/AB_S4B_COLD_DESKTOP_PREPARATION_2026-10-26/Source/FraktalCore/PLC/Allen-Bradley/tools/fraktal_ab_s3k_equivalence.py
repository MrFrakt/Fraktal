"""S3k reference: all inherited values plus the 133 approved read surfaces.

Only safe commit, response and release-owner records enter the paired frame.
No request arguments, native Frame, Secret or provider inputs are read here.
"""
from functools import partial
import fraktal_ab_s3j_equivalence as previous
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_projection as projection
import fraktal_ab_manifest as manifest
import fraktal_ab_mailbox as mailbox
import fraktal_ab_generate as gen
import fraktal_ab_canonical_mailbox as publication


def mailbox_paths(app,*,canonical):
    report='HmiResponse/Report/'
    reason=report+('Reasons' if canonical else 'Reasons/Reasons')
    return {app.name+'/'+p for p in (
        'GoodCount','NokCount','ReworkCount','Starved','Blocked','Features/CaptureEnabled',
        'Features/ExportCurrentConfig','HmiRequest/Sequence','HmiResponse/AckSequence',
        'HmiResponse/Accepted','HmiResponse/Diagnostic',report+'Released',report+'Count',
        *(f'{reason}[{i}]/{name}' for i in range(1,publication.CAPACITY+1)
          for name in ('Description','ReasonCode','SourcePath','Kind','Bypassable')))}


def additional_inputs(reader,app):
    import fraktal_ab_press_execute as execute
    import fraktal_ab_declaration as declaration
    result=previous.additional_inputs(reader,app)
    result.update(mailbox_input=execute.read_layout(reader,publication.input_tag(app),
            tuple(declaration.scalar(m.name) for m in __import__('fraktal_ab_canonical_publication').schema(app)[publication.INPUT])),
        mailbox_response=execute.read_layout(reader,mailbox.response_tag_name(app),
            tuple(declaration.scalar(n) for n,kind,width,note in mailbox.RESPONSE_MEMBERS)),
        release_report=execute.read_layout(reader,gen.release_report_tag(app),gen.release_report_members(app)))
    if any(result[n] is None for n in ('mailbox_input','mailbox_response','release_report')):
        raise ValueError('S3k safe mailbox/report owner unavailable')
    return result


def extra_values(app,unit,additional,*,page=0,model=0,provider_state=None):
    result=previous.extra_values(app,unit,additional,page=page,model=model,provider_state=provider_state)
    reply={n:additional['mailbox_input'][n] for n,kind,width,note in mailbox.RESPONSE_MEMBERS}
    source=projection.mailbox_values(manifest.content(app),reply,
        additional['mailbox_input']['Sequence'],additional['release_report'],app=app)
    source.update({name:unit[field]&0xffffffff for name,field in
        (('GoodCount','GoodCount'),('NokCount','ScrapCount'),('ReworkCount','ReworkCount'))})
    source['Starved'],source['Blocked']=projection.wait_attribution(app,unit)
    source.update({'Features/CaptureEnabled':any(r.get('CaptureSourceKey',0) for r in manifest.content(app)['WriteCapabilities']),
                   'Features/ExportCurrentConfig':bool(app.config_sets)})
    result.update({app.name+'/'+p:v for p,v in source.items()})
    return result


def subset_paths(app,codes,*,canonical,count,shift_count,page=0,model=0):
    return previous.subset_paths(app,codes,canonical=canonical,count=count,shift_count=shift_count,page=page,model=model)|mailbox_paths(app,canonical=canonical)


def logical_types(app,paths):
    result=previous.logical_types(app,paths)
    unsigned={app.name+'/'+p for p in ('GoodCount','NokCount','ReworkCount','HmiRequest/Sequence','HmiResponse/AckSequence')}
    for path in paths:
        if path in unsigned:result[path]='UInt32'
        elif path==app.name+'/HmiResponse/Report/Count':result[path]='Int16'
    return result


def run(comm,*,page=0,model=0,provider_state=None,candidate_factory=None,oracle_declaration='fraktal_ab_genealogy_demo'):
    if candidate_factory is None:
        import fraktal_ab_genealogy_s3k_demo as candidate
        candidate_factory=candidate.application
    app=candidate_factory();state={}
    def inputs(reader):
        value=additional_inputs(reader,app)
        state.update(count=value['host']['metadata']['Count'] if value['host'] is not None else 0,
                     shift_count=value['line_shift']['Count'] if app.line else 0)
        return value
    def paths(app,codes,*,canonical):return subset_paths(app,codes,canonical=canonical,**state,page=page,model=model)
    return shared.run(comm,application_factory=candidate_factory,path_contract=paths,
        extra_oracle=partial(extra_values,page=page,model=model,provider_state=provider_state),
        logical_types=logical_types,additional_inputs=inputs,oracle_declaration=oracle_declaration)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
