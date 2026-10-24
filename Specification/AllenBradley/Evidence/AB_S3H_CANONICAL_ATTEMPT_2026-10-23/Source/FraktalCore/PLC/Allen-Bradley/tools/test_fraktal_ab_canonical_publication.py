"""S2 engineering and wire gates; synthetic data is never a runtime capture."""
from copy import deepcopy
from dataclasses import replace
import ast
from pathlib import Path
import struct
from types import SimpleNamespace
import unittest
import xml.etree.ElementTree as ET

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_publication as publisher
import fraktal_ab_canonical_reader as reader
import fraktal_ab_declaration as decl
import fraktal_ab_genealogy_demo as genealogy
import fraktal_ab_genealogy_canonical_demo as candidate
import fraktal_ab_generate as gen
import fraktal_ab_manifest as legacy
from fraktal_ab_canonical_equivalence import stable_scan_pair
from fraktal_ab_s2_equivalence import subset_paths
from test_fraktal_ab_canonical_reader import synthetic


def string(value, width=255):
    raw=value.encode('utf-8')
    return dict(string=True,width=width,LEN=len(raw),bytes=raw.hex())


def fixture():
    fields=[dict(CanonicalPath='Mixer/Flag',LogicalType='',EffectiveAccess='Read Only',LowerBound=0,ElementCount=0),
            dict(CanonicalPath='Mixer/Duration',LogicalType='DURATION',EffectiveAccess='Read Only',LowerBound=0,ElementCount=0)]
    old='0123456789ABCDEF'
    digest=wire.content_hash(fields,old)
    return dict(Magic=wire.MAGIC,SchemaMajor=6,SchemaMinor=0,PublicationStage=2,Valid=True,Truncated=False,
                ContentHash=string(digest,80),ConfigRevision=wire.revision(digest),LegacyContentHash=string(old,80),
                FieldsCount=len(fields),FieldsCapacity=len(fields),Fields=[{k:string(v,255 if k=='CanonicalPath' else 16) if isinstance(v,str) else v for k,v in row.items()} for row in fields])


def wire_fixture():
    """Independently assembled wire layout, with explicit padding and strides."""
    from test_fraktal_ab_canonical_reader import member
    record=fixture()
    templates=[]
    for handle,width in ((0x200,16),(0x201,80),(0x202,255)):
        templates.append(dict(handle=handle,name='Text'+str(width),byteSize=4+((width+3)//4)*4,
                              members=[member('LEN',0xC4,0),member('DATA',0x20C2,4,width)]))
    row_members=[member('CanonicalPath',0x8202,0),member('LogicalType',0x8200,260),member('EffectiveAccess',0x8200,280),member('LowerBound',0xC4,300),member('ElementCount',0xC4,304)]
    templates.append(dict(handle=0x210,name='Field',byteSize=308,members=row_members))
    header_members=[member(k,0xC4,i*4) for i,k in enumerate(('Magic','SchemaMajor','SchemaMinor','PublicationStage'))]
    header_members += [member('Valid',0xC1,16),member('Truncated',0xC1,17),member('ContentHash',0x8201,20),member('ConfigRevision',0xC4,104),member('LegacyContentHash',0x8201,108),member('FieldsCount',0xC4,192),member('FieldsCapacity',0xC4,196),member('Fields',0xA210,200,2)]
    templates.append(dict(handle=0x220,name='UnrelatedTypeName',byteSize=816,members=header_members))
    raw=bytearray(816)
    for i,key in enumerate(('Magic','SchemaMajor','SchemaMinor','PublicationStage')):struct.pack_into('<i',raw,i*4,record[key])
    raw[16]=1
    def put_text(offset,value):
        data=bytes.fromhex(value['bytes']);struct.pack_into('<i',raw,offset,len(data));raw[offset+4:offset+4+len(data)]=data
    put_text(20,record['ContentHash']);struct.pack_into('<i',raw,104,record['ConfigRevision']);put_text(108,record['LegacyContentHash'])
    struct.pack_into('<ii',raw,192,2,2)
    for i,row in enumerate(record['Fields']):
        at=200+i*308
        for key,offset in (('CanonicalPath',0),('LogicalType',260),('EffectiveAccess',280)):put_text(at+offset,row[key])
        struct.pack_into('<ii',raw,at+300,row['LowerBound'],row['ElementCount'])
    return templates,bytes(raw)


class ManifestTests(unittest.TestCase):
    def test_generic_runtime_modules_have_no_station_or_projection_dependencies(self):
        folder=Path(__file__).parent
        for name in ('fraktal_ab_canonical_reader.py','fraktal_ab_canonical_manifest.py','fraktal_ab_canonical_acquire.py'):
            tree=ast.parse((folder/name).read_text(encoding='utf-8'))
            imports=[node.module for node in ast.walk(tree) if isinstance(node,ast.ImportFrom)]
            imports += [alias.name for node in ast.walk(tree) if isinstance(node,ast.Import) for alias in node.names]
            self.assertFalse(set(imports)&{'fraktal_ab_station','fraktal_ab_declaration','fraktal_ab_generate','fraktal_ab_projection','fraktal_ab_genealogy_demo'})

    def test_paired_state_skips_active_scan_and_retries_generation_change(self):
        generations=iter((1,2,4,4,4))
        calls=[]
        result=stable_scan_pair(lambda:next(generations),lambda:(calls.append(1) or {'sample':'raw'}))
        self.assertEqual(len(calls),2)
        self.assertTrue(result['sameStateVerified'])
        self.assertEqual(result['stateEvidence']['generation'],4)
        self.assertEqual(len(result['stateEvidence']['attempts']),3)

    def test_paired_state_rejects_uninitialized_and_changing_generations(self):
        for generation in (0,True,None,-1):
            with self.subTest(generation=generation),self.assertRaises(ValueError):
                stable_scan_pair(lambda:generation,lambda:self.fail('must not acquire'))
        generations=iter((2,4))
        with self.assertRaises(ValueError) as error:
            stable_scan_pair(lambda:next(generations),lambda:{},attempts=1)
        self.assertEqual(error.exception.attempts,[dict(before=2,after=4)])

    def test_physical_loader_discovers_shape_with_arbitrary_symbol_and_type_names(self):
        templates,raw=wire_fixture()
        comm=SimpleNamespace(Read=lambda name:SimpleNamespace(Status='Success',Value=raw))
        symbols=[dict(name='UnexpectedSymbol',handle=0x220,arrayRank=0)]
        actual=wire.read_manifest(comm,symbols,templates)
        self.assertEqual(actual,wire.normalize(fixture()))
        self.assertEqual(actual['annotations']['Mixer/Duration']['logicalType'],'DURATION')
        with self.assertRaisesRegex(ValueError,'ambiguous'):
            wire.read_manifest(comm,symbols+[dict(symbols[0],name='Duplicate')],templates)

    def test_changed_row_hash_count_version_type_and_private_access_fail_closed(self):
        edits=[lambda r:r.update(Magic=0),lambda r:r.update(SchemaMajor=5),
               lambda r:r.update(SchemaMinor=1),lambda r:r.update(SchemaMinor=False),lambda r:r.update(Valid=1),
               lambda r:r.update(Truncated=True),lambda r:r.update(FieldsCount=1),
               lambda r:r.update(ConfigRevision=0),lambda r:r['Fields'][1].update(CanonicalPath=string('Mixer/Flag')),
               lambda r:r['Fields'][0].update(EffectiveAccess=string('None')),
               lambda r:r['Fields'][0].update(LogicalType=string('GUESS')),
               lambda r:r['Fields'][0].update(LowerBound=1),
               lambda r:r['Fields'][0].update(CanonicalPath=string('Mixer/Other'))]
        for edit in edits:
            r=deepcopy(fixture());edit(r)
            with self.subTest(edit=edit),self.assertRaises(ValueError):wire.normalize(r)

    def test_effective_access_is_validated_without_changing_value_types(self):
        capture=synthetic()
        capture['manifest']['annotations']['Mixer/Status/Name']=dict(effectiveAccess='Read Only')
        result=reader.snapshot(capture)
        self.assertEqual(result['values']['Mixer/Status/Name'],'Mixer')
        capture['manifest']['annotations']['Mixer/Status/Name']['effectiveAccess']='None'
        with self.assertRaisesRegex(ValueError,'effective access'):reader.snapshot(capture)


class PublicationTests(unittest.TestCase):
    def test_profile_is_opt_in_and_legacy_manifest_identity_is_preserved(self):
        base,new=genealogy.application(),candidate.application()
        self.assertFalse(publisher.enabled(base))
        self.assertTrue(publisher.enabled(new))
        self.assertEqual(legacy.content_hash(base),'6DEC4C1DC2F7F78A')
        self.assertEqual(legacy.content_hash(new),legacy.content_hash(base))
        self.assertEqual(legacy.content(new),legacy.content(base))
        self.assertEqual(publisher.validate(new),[])
        self.assertEqual(publisher.validate(replace(new,canonical_publication_stage=8)),[])
        self.assertEqual(publisher.validate(replace(new,canonical_publication_stage=9)),[])
        for app in (replace(new,major_revision=33),replace(new,canonical_publication_stage=11),
                    replace(new,canonical_publication_stage=True)):
            self.assertTrue(publisher.validate(app))

    def test_one_root_shared_leaf_types_readonly_tree_and_exact_field_coverage(self):
        app=candidate.application()
        root=ET.fromstring('<DataTypes>'+''.join(publisher.data_types(app))+'</DataTypes>')
        types={node.get('Name'):node for node in root}
        canonical=types[publisher.root_type(app)]
        self.assertEqual({m.get('Name') for m in canonical.findall('Members/Member')},
                         {'Status','ModeActivePublished','RunStyle','CurrentStep','Model',*(m.name for m in app.modules)})
        self.assertTrue(all(m.get('ExternalAccess')=='Read Only' for node in root for m in node.findall('Members/Member')))
        fields=publisher.field_rows(app)
        self.assertEqual(len(fields),46)
        self.assertEqual(len({r['CanonicalPath'] for r in fields}),46)
        self.assertEqual({r['CanonicalPath'] for r in fields},subset_paths(app))
        self.assertTrue(all(r['EffectiveAccess']=='Read Only' for r in fields))
        for module in app.modules:
            self.assertIn(app.name+'/'+module.name+'/Status/Name',{r['CanonicalPath'] for r in fields})
        # One shared leaf type for these six typed CMs, not six instance types.
        self.assertEqual(len([name for name in types if 'Leaf' in name]),1)
        self.assertEqual(types[publisher.status_type(True)].find("Members/Member[@Name='FaultActive']").get('DataType'),'BOOL')

    def test_initial_identity_uses_qualified_paths_and_utf8_bytes_without_truncation(self):
        app=candidate.application()
        tag=ET.fromstring(publisher.tags(app)[0])
        status=publisher.initial(app)
        self.assertEqual(status['Door']['Status']['Name'],'Press.Door')
        self.assertEqual(status['Status']['ModuleType'],1)
        self.assertEqual(status['Door']['Status']['ModuleType'],3)
        self.assertEqual(tag.get('Name'),'Press')
        too_long=replace(app,type_key='x'*161)
        with self.assertRaises(ValueError):publisher.tags(too_long)

    def test_publisher_follows_owners_and_adds_no_request_or_private_working_member(self):
        app=candidate.application()
        sections=gen.scan_sections(app)
        names=[name for name,body in sections if name]
        self.assertLess(names.index('FRK_Press_ScanDiagnostics'),names.index('FRK_Press_ScanCanonical'))
        self.assertEqual(names[0],'FRK_Press_ScanCanonicalBegin')
        self.assertEqual(names[-1],'FRK_Press_ScanCanonical')
        self.assertIn('2147483646','\n'.join(publisher.begin_scan(app)))
        lines='\n'.join(publisher.cyclic(app))
        self.assertIn('Press.Door.Status.State := FRK_Press_CtxDoor.OutImm_ExecState;',lines)
        self.assertIn('Press.CurrentStep.StepNo := FRK_Press_Unit.Step;',lines)
        self.assertIn('GSV(TASK,',lines)
        self.assertNotIn('SSV(',lines)
        self.assertNotIn('HmiRequest',lines)
        self.assertNotIn('Execute :=',lines)
        tags=ET.fromstring('<Tags>'+''.join(publisher.tags(app))+'</Tags>')
        self.assertEqual([t.get('Name') for t in tags if t.get('ExternalAccess')=='None'],['FRK_Press_CanonicalIndex'])

    def test_untyped_module_and_no_model_do_not_invent_optional_paths(self):
        app=replace(candidate.application(),type_key='',models=(),model_capacity=0,
                    modules=tuple(replace(m,type_key='') for m in candidate.application().modules))
        fields=publisher.field_rows(app)
        self.assertFalse(any(r['CanonicalPath'].endswith('/TypeKey') or '/Model/' in r['CanonicalPath'] for r in fields))
        self.assertNotIn('ModelCode','\n'.join(publisher.cyclic(app)))


if __name__=='__main__':unittest.main()
