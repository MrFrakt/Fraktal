"""Migration oracle for the approved V6.8 configuration view.

The shipping reader knows no declaration. This acceptance side independently
joins legacy capabilities, records, model banks and access decisions; it never
uses the new view's values to choose or calculate its expected paths.
"""
from functools import partial
import fraktal_ab_s3k_equivalence as previous
import fraktal_ab_s3f_equivalence as configuration
import fraktal_ab_s2_equivalence as shared
import fraktal_ab_config_read_view as view
import fraktal_ab_canonical_config as layout
import fraktal_ab_manifest as manifest
import fraktal_ab_models as models
import fraktal_ab_projection as projection


def view_paths(app,codes):
    root=view.canonical_root(app)+'/'
    definitions=layout.def_rows(app)
    count=len(definitions)+len(codes)*sum(row['ModelScoped'] for row in definitions)
    return {root+n for n in ('SchemaVersion','RootIdentity','Revision','DefinitionCount','DefinitionCapacity','ValueCount','ValueCapacity')} | {
        root+f'Definitions[{i}]/'+n for i in range(len(definitions))
        for n in ('DefinitionIndex',*(n for n in configuration.ENTRY_FIELDS if n not in ('ValueText','Readable')))} | {
        root+f'Values[{i}]/'+n for i in range(count)
        for n in ('DefinitionIndex','ModelOrdinal','ModelCode','ValueText','Readable','Revision')}


def reference(app,additional):
    codes=additional['read_view_codes'];revision=additional['query']['Revision']
    def entries(model):
        page=projection.config_page(app,manifest.content(app),additional['records'],additional['models'],model,additional['levels'])
        result=[]
        for i in range(1,page['HmiResponse/ConfigPage/EntryCount']+1):
            prefix=f'HmiResponse/ConfigPage/Entries[{i}]/'
            row={p[len(prefix):]:v for p,v in page.items() if p.startswith(prefix)}
            for n in ('Minimum','Maximum'):row[n]=float(row[n])
            result.append(row)
        return result
    live=entries(0);definitions=[dict(DefinitionIndex=i,**{k:v for k,v in row.items() if k not in ('ValueText','Readable')}) for i,row in enumerate(live)]
    values=[dict(DefinitionIndex=i,ModelOrdinal=0,ModelCode='',ValueText=row['ValueText'],Readable=row['Readable'],Revision=revision) for i,row in enumerate(live)]
    for ordinal,code in enumerate(codes,1):
        values += [dict(DefinitionIndex=i,ModelOrdinal=ordinal,ModelCode=code,ValueText=row['ValueText'],Readable=row['Readable'],Revision=revision)
                   for i,row in enumerate(entries(ordinal)) if row['ModelScoped']]
    root=view.canonical_root(app)+'/'
    return {root+n:v for n,v in dict(SchemaVersion=1,RootIdentity=app.name,Revision=revision,
        DefinitionCount=len(definitions),DefinitionCapacity=view.capacities(app)[0],ValueCount=len(values),ValueCapacity=view.capacities(app)[1]).items()} | {
        root+f'{group}[{i}]/'+n:v for group,rows in (('Definitions',definitions),('Values',values))
        for i,row in enumerate(rows) for n,v in row.items()}


def logical_types(app,paths):
    result=previous.logical_types(app,paths);root=view.canonical_root(app)+'/'
    for p in paths:
        if not p.startswith(root):continue
        leaf=p.rsplit('/',1)[-1]
        if leaf=='SchemaVersion':result[p]='UInt16'
        elif leaf in ('Revision','WriteRevision'):result[p]='UInt32'
        elif leaf in ('Minimum','Maximum'):result[p]='Double'
    return result


def run(comm,*,page=0,model=0,provider_state=None):
    import fraktal_ab_genealogy_s4b_demo as candidate
    app=candidate.application();state={}
    def inputs(reader):
        value=previous.additional_inputs(reader,app);value['read_view_codes']=models.read(reader,app)
        state.update(count=value['host']['metadata']['Count'] if value['host'] is not None else 0,
                     shift_count=value['line_shift']['Count'] if app.line else 0)
        return value
    def paths(app,codes,*,canonical):
        return previous.subset_paths(app,codes,canonical=canonical,**state,page=page,model=model)|view_paths(app,codes)
    def extra(app,unit,additional):
        return previous.extra_values(app,unit,additional,page=page,model=model,provider_state=provider_state)|reference(app,additional)
    return shared.run(comm,application_factory=candidate.application,path_contract=paths,
        extra_oracle=extra,logical_types=logical_types,additional_inputs=inputs)


if __name__=='__main__':raise SystemExit(shared.main(run,description=__doc__))
