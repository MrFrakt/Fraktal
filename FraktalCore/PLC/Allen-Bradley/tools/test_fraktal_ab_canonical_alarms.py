"""Execute generated S3d publication against the independent legacy oracle."""
from dataclasses import replace
from pathlib import Path
import json
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_alarms as alarms
import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_status as diagnostic
import fraktal_ab_canonical_reader as reader
import fraktal_ab_genealogy_s3d_demo as demo
import fraktal_ab_generate as gen
import fraktal_ab_manifest as manifest
import fraktal_ab_library as library

TIME_SYNCHRONIZED = False

def _controller_time(date: int, time: int):
    if date <= 0:
        return 0
    year, month, day = date // 10000, (date // 100) % 100, date % 100
    hour, minute = time // 10_000_000, (time // 100_000) % 100
    second, millis = (time // 1000) % 100, time % 1000
    if not (1 <= month <= 12 and 1 <= day <= 31 and hour < 24 and minute < 60 and second < 60):
        return 0
    return f"{year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}.{millis:03d}Z"

def _module_path(app, ordinal: int) -> str:
    if ordinal <= 0:
        return ""
    if ordinal == 1:
        return app.name
    index = ordinal - 2
    return f"{app.name}.{app.modules[index].name}" if 0 <= index < len(app.modules) else ""

def reason_description(app, code: int) -> str:
    name = next((n for n, c in app.reasons.items() if c == code), None)
    return manifest.reason_key(app, name) if name and code else ''

def _alarm_event(app, columns: dict, prefix: str, index: int) -> dict:
    def col(name: str):
        return columns[f"{prefix}{name}"][index]
    reason = col("ReasonCode")
    source = _module_path(app, col("SourceModuleId"))
    io_tag, io_address = library.io_join(app, source.rsplit(".", 1)[-1], col("IoRoles") if f"{prefix}IoRoles" in columns else 0)
    return {
        "State": col("State"),
        "ReasonCode": reason,
        "Description": reason_description(app, reason),
        "Severity": col("Severity"),
        "ResetClass": col("ResetClass"),
        "SourcePath": source,
        "ComeAt": _controller_time(col("ComeDate"), col("ComeTime")),
        "GoneAt": _controller_time(col("GoneDate"), col("GoneTime")),
        "Duration": col("DurationMs"),
        "Shelved": bool(col('Shelved')),
        "IoTag": io_tag,
        "IoAddress": io_address,
        "ComeTimeSynchronized": TIME_SYNCHRONIZED,
        "GoneTimeSynchronized": TIME_SYNCHRONIZED,
        "ResetTimeSynchronized": TIME_SYNCHRONIZED,
        "ShelfTimeSynchronized": TIME_SYNCHRONIZED,
    }

def alarm_log_status(app, active: dict | None, ring: dict | None) -> dict:
    if active is None:
        return {}
    out = {
        "AlarmLog/RingHead": active.get("RingHead", 0),
        "AlarmLog/Blocking": bool(active.get("Blocking", 0)),
    }
    for index in range(gen.ALARM_ACTIVE):
        for key, value in _alarm_event(app, active, "Act", index).items():
            out[f"AlarmLog/Active[{index + 1}]/{key}"] = value
    if ring is not None:
        for index in range(gen.ALARM_RING):
            for key, value in _alarm_event(app, ring, "Ring", index).items():
                out[f"AlarmLog/Ring[{index + 1}]/{key}"] = value
    return out

def alarm_meta_status(rows: dict) -> dict:
    catalogue = {row["NumericKey"]: row["PortableKey"] for row in rows["Localization"]}
    meta = rows.get("Rationalization") or []
    out = {"AlarmLog/MetaCount": len(meta)}
    for index, row in enumerate(meta, start=1):
        base = f"AlarmLog/Meta[{index}]"
        out[f"{base}/ReasonCode"] = row["ReasonCode"]
        out[f"{base}/OperatorAction"] = catalogue.get(row["ActionKey"], "")
        out[f"{base}/Consequence"] = catalogue.get(row["ConsequenceKey"], "")
        out[f"{base}/Priority"] = row["Priority"]
        out[f"{base}/Category"] = row["Category"]
        out[f"{base}/Shelvable"] = bool(row["Shelvable"])
    return out

def state_flags_status(app, flags: dict | None) -> dict:
    if not app.state_flags or flags is None:
        return {}
    values = {"StateFlagCount": len(app.state_flags)}
    for i, flag in enumerate(app.state_flags):
        base = f"StateFlags[{i + 1}]"
        values[f"{base}/Key"] = flag.key
        values[f"{base}/Value"] = bool(flags["Value"][i])
        values[f"{base}/Since"] = _controller_time(flags["SinceDate"][i], flags["SinceTime"][i])
        values[f"{base}/Stale"] = False
    return values
import fraktal_ab_st_model as st


class AlarmTests(unittest.TestCase):
    def setup_model(self):
        self.app=app=demo.application();self.schema=pub.schema(app)
        def value(kind,initial=None):
            if kind.startswith(pub.PREFIX+'String'):
                raw=(initial or '').encode('utf-8');return dict(LEN=len(raw),DATA=list(raw)+[0]*(pub.string_width(kind)-len(raw)))
            if kind not in self.schema:return initial or 0
            supplied=initial or {}
            return {m.name:([value(m.kind,item) for item in supplied.get(m.name,[None]*m.count)] if m.count
                else value(m.kind,supplied.get(m.name))) for m in self.schema[kind]}
        tags={app.name:value(pub.root_type(app),pub.initial(app)),pub.header_tag(app):dict(Valid=1,FragmentRevision=0)}
        def serialize(name,kind,initial,**options):
            tags[name]=[value(kind,item) for item in initial] if options.get('array') else value(kind,initial)
            return ''
        alarms.tags(app,serialize);diagnostic.private_tags(app,serialize)
        self.active=st.structure(gen.alarm_active_members());self.ring=st.structure(gen.alarm_ring_members())
        self.flags=st.structure(gen.state_flags_members(app))
        tags.update({gen.alarm_active_tag(app):self.active,gen.alarm_ring_tag(app):self.ring,gen.state_flags_tag(app):self.flags})
        self.controller=st.Controller(tags,calls={'CPS':st.cps_structure},routines=dict(gen.canonical_routines(app)))
        self.make_value=value
        self.logic='\n'.join(alarms.cyclic(app))

    def scan(self):
        # The model defaults to DINT; the shared calendar ends in native LINT.
        # Native compilation/read-back remains a separate acceptance gate.
        with patch.object(st,'_wrap',lambda value:(value+(1<<63))%(1<<64)-(1<<63)):
            self.controller.run(self.logic)
        work=self.controller.tags[diagnostic.work_tag(self.app)]
        for member in self.schema[diagnostic.WORK]:
            if member.kind=='DINT':self.assertTrue(-(1<<31)<=work[member.name]<(1<<31))

    def actual(self):
        result={}
        def walk(kind,value,path):
            if kind.startswith(pub.PREFIX+'String'):
                result[path]=bytes(x&255 for x in value['DATA'][:value['LEN']]).decode('utf-8')
            elif kind not in self.schema:
                result[path]=bool(value) if kind=='BOOL' else reader.timestamp_ns(value) if kind=='LDT' else value
            else:
                for m in self.schema[kind]:
                    child=path+'/'+m.name if path else m.name
                    if m.count:
                        for i,item in enumerate(value[m.name]):walk(m.kind,item,child+f'[{i+m.lower}]')
                    else:walk(m.kind,value[m.name],child)
        root=self.controller.tags[self.app.name]
        walk(alarms.LOG,root['AlarmLog'],'AlarmLog')
        walk(alarms.METADATA,self.controller.tags[alarms.metadata_tag(self.app)],'')
        result['StateFlagCount']=root['StateFlagCount']
        for i,flag in enumerate(root['StateFlags'],1):walk(alarms.FLAG,flag,f'StateFlags[{i}]')
        return result

    def assert_oracle(self):
        expected=alarm_log_status(self.app,self.active,self.ring)
        expected.update(alarm_meta_status(manifest.content(self.app)))
        expected.update(state_flags_status(self.app,self.flags))
        self.assertEqual(self.actual(),expected)

    def event(self,index=0,*,ring=False,**values):
        columns,prefix=(self.ring,'Ring') if ring else (self.active,'Act')
        for key,value in values.items():columns[prefix+key][index]=value

    def test_independent_2125_path_inventory_and_timestamp_types(self):
        root=Path(__file__).resolve().parents[4]
        inventory=json.loads((root/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3D_INVENTORY_2026-10-22.json').read_text())
        self.assertEqual(len(inventory['paths']),2125)

    def test_empty_slots_and_static_metadata_match_the_oracle(self):
        self.setup_model();self.scan();self.assert_oracle()

    def test_active_wait_reset_close_and_ring_wrap_preserve_lifecycle(self):
        self.setup_model();reason=next(v for v in self.app.reasons.values() if v)
        self.event(State=1,ReasonCode=reason,Severity=2,ResetClass=1,SourceModuleId=3,ComeDate=19980101,ComeTime=10203004,IoRoles=1)
        self.active['Blocking']=1;self.scan();self.assert_oracle()
        self.event(State=2,GoneDate=19980101,GoneTime=10204125,DurationMs=1121,Shelved=1)
        self.scan();self.assert_oracle()
        for slot in (63,0):
            self.active['RingHead']=slot+1
            for key,_ in gen.ALARM_COLUMNS:self.ring['Ring'+key][slot]=self.active['Act'+key][0]
            self.ring['RingState'][slot]=0;self.scan();self.assert_oracle()
        self.active['Blocking']=0
        for key,_ in gen.ALARM_COLUMNS:self.active['Act'+key][0]=0
        self.scan();self.assert_oracle()

    def test_reason_zero_still_preserves_valid_timestamps_and_source(self):
        self.setup_model();self.event(ReasonCode=0,SourceModuleId=1,ComeDate=20000229,ComeTime=235959999)
        self.scan();self.assert_oracle()
        self.assertEqual(self.actual()['AlarmLog/Active[1]/ComeAt'],'2000-02-29T23:59:59.999Z')

    def test_source_ordinals_io_and_slot_reuse_follow_the_oracle(self):
        self.setup_model();reason=next(v for v in self.app.reasons.values() if v)
        for source in (0,1,2,len(self.app.modules)+1,99,-1):
            self.event(ReasonCode=reason,SourceModuleId=source,IoRoles=7,State=1)
            self.scan();self.assert_oracle()
        self.event(ReasonCode=0,SourceModuleId=0,IoRoles=0);self.scan();self.assert_oracle()
        self.assertEqual(self.actual()['AlarmLog/Active[1]/Description'],'')

    def test_state_flags_change_without_client_accumulation(self):
        self.setup_model();self.scan();self.assert_oracle()
        self.flags['Value'][0]=1;self.flags['SinceDate'][0]=20261022;self.flags['SinceTime'][0]=120000123
        self.scan();self.assert_oracle()
        self.flags['Value'][0]=0;self.flags['SinceTime'][0]+=500
        self.scan();self.assert_oracle();self.assertFalse(self.actual()['StateFlags[1]/Stale'])

    def test_unchanged_timestamps_do_not_reconvert_on_scalar_updates(self):
        self.setup_model();self.scan()
        work=self.controller.tags[diagnostic.work_tag(self.app)];work['EpochNs']=123456789
        self.active['ActDurationMs'][0]=777;self.active['ActShelved'][0]=1
        self.scan();self.assert_oracle();self.assertEqual(work['EpochNs'],123456789)

    def test_invalid_calendar_refuses_and_shared_algorithm_is_emitted_once(self):
        self.setup_model();self.event(ComeDate=19000229,ComeTime=0)
        self.scan();self.assertEqual(self.controller.tags[pub.header_tag(self.app)]['Valid'],0)
        routines=dict(gen.canonical_routines(self.app))
        self.assertIn(diagnostic.timestamp_routine_name(self.app),routines)
        self.assertEqual(sum('719468' in line for lines in routines.values() for line in lines),1)
        self.assertEqual(len(pub.publication_bindings(self.app)),2)
        self.assertTrue(any('collides' in finding for finding in pub.validate(replace(self.app,
            modules=(replace(self.app.modules[0],name='AlarmLog'),*self.app.modules[1:])))))


if __name__=='__main__':unittest.main()
