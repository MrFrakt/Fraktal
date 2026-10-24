"""Execute the shared diagnostic resolver and compare independent legacy values."""
from datetime import datetime,timezone
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import fraktal_ab_canonical_publication as pub
import fraktal_ab_canonical_reader as reader
import fraktal_ab_canonical_status as status
import fraktal_ab_genealogy_s3b_demo as candidate
import fraktal_ab_projection as projection
import fraktal_ab_s3b_equivalence as equivalence
import fraktal_ab_st_model as st


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.app=candidate.application()
        self.definitions=pub.schema(self.app)

    def value(self,kind):
        if kind.startswith(pub.PREFIX+'String'):
            return dict(LEN=0,DATA=[0]*pub.string_width(kind))
        if kind not in self.definitions:return 0
        return {m.name:([self.value(m.kind) for _ in range(m.count)] if m.count else self.value(m.kind))
                for m in self.definitions[kind]}

    def text(self,value,width):
        raw=value.encode('utf-8')
        return dict(LEN=len(raw),DATA=list(raw)+[0]*(width-len(raw)))

    def resolver(self,**inputs):
        app=self.app;work=self.value(status.WORK)
        work['Inputs'].update(inputs)
        tags={status.work_tag(app):work,pub.header_tag(app):dict(Valid=1),
              status.area_tag(app):[self.text(m.area_safe_key,255) for m in app.modules],
              status.io_tag(app):[{**r,**{k:self.text(r[k],80) for k in ('ElectricalTag','Address')}} for r in status.bindings(app)]}
        controller=st.Controller(tags,calls={'CPS':st.cps_structure})
        # The existing model defaults to DINT. Here the arithmetic's final
        # operations are LINT; all calendar DINT intermediates are also checked.
        with patch.object(st,'_wrap',lambda value:(value+(1<<63))%(1<<64)-(1<<63)):
            controller.run('\n'.join(status.resolver(app)))
        for member in self.definitions[status.WORK]:
            if member.kind=='DINT':self.assertTrue(-(1<<31)<=work[member.name]<(1<<31))
        return work,tags[pub.header_tag(app)]['Valid']

    def test_exact_304_path_inventory_and_native_timestamp_contract(self):
        root=Path(__file__).resolve().parents[4]
        expected=json.loads((root/'Specification/AllenBradley/AB_CANONICAL_PUBLICATION_S3B_INVENTORY_2026-10-21.json').read_text())
        paths=equivalence.subset_paths(self.app,[m.code for m in self.app.models],canonical=True)
        self.assertEqual(paths,set(expected['paths']))
        self.assertEqual(len(paths),304)
        since=next(m for m in self.definitions[status.DIAGNOSTIC] if m.name=='Since')
        self.assertEqual((since.kind,since.logical),('LDT','TIMESTAMP'))

    def test_calendar_values_match_independent_datetime_at_ms_precision(self):
        for stamp in ('1998-01-01T01:02:03.000','2000-02-29T23:59:59.999',
                      '1900-03-01T00:00:00.100','1969-12-31T23:59:59.999','2026-10-21T09:08:07.120'):
            moment=datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc)
            date=moment.year*10000+moment.month*100+moment.day
            clock=moment.hour*10000000+moment.minute*100000+moment.second*1000+moment.microsecond//1000
            delta=moment-datetime(1970,1,1,tzinfo=timezone.utc)
            expected=(delta.days*86400+delta.seconds)*1000000000+delta.microseconds*1000
            with self.subTest(stamp=stamp):
                work,valid=self.resolver(Reason=1,Stamped=1,DateCode=date,ClockCode=clock)
                self.assertEqual(valid,1)
                self.assertEqual(work['Diagnostic']['Since'],expected)
                self.assertEqual(reader.timestamp_ns(expected),stamp+'Z')

    def test_invalid_calendar_and_nanosecond_overflow_refuse(self):
        for date,clock in ((19000229,0),(20001301,0),(19980101,240000000),
                           (16770921,1243145),(22620411,234716855)):
            with self.subTest(date=date,clock=clock):
                work,valid=self.resolver(Reason=1,Stamped=1,DateCode=date,ClockCode=clock)
                self.assertEqual((work['Diagnostic']['Since'],valid),(0,0))
        for date,clock in ((16770921,1243146),(22620411,234716854)):
            with self.subTest(date=date,clock=clock):
                _,valid=self.resolver(Reason=1,Stamped=1,DateCode=date,ClockCode=clock)
                self.assertEqual(valid,1)

    def test_unset_and_unstamped_reasons_do_not_invent_onset(self):
        for reason,stamped,date in ((0,0,19980101),(1,2,19980101),(1,1,0)):
            work,valid=self.resolver(Reason=reason,Stamped=stamped,DateCode=date)
            self.assertEqual((work['Diagnostic']['Since'],valid),(0,1))

    def test_electrical_join_matches_owning_library_role_order(self):
        import fraktal_ab_library as library
        for index,module in enumerate(self.app.modules,1):
            for roles in range(1<<len(library.type_of(module).io_roles)):
                work,valid=self.resolver(Owner=index,IoSource=index,IoRoles=roles)
                actual=tuple(bytes(work['Diagnostic'][name]['DATA'][:work['Diagnostic'][name]['LEN']]).decode()
                             for name in ('IoTag','IoAddress'))
                self.assertEqual(actual,projection.io_join(self.app,module.name,roles))
                self.assertEqual(valid,1)

    def test_held_description_precedes_reason_text(self):
        for index,module in enumerate(self.app.modules,1):
            if not module.area_safe_key:continue
            work,_=self.resolver(Owner=index,Reason=next(iter(self.app.reasons.values())),Held=1,AreaSafe=0,Permit=0)
            text=work['Diagnostic']['Description']
            self.assertEqual(bytes(text['DATA'][:text['LEN']]).decode(),module.area_safe_key)

    def test_one_resolver_and_private_caches_are_outside_public_root(self):
        tags=pub.tags(self.app)
        self.assertEqual(sum('ExternalAccess="None"' in t and 'CanonicalDiagnosticCache' in t for t in tags),7)
        root_fields={m.name for m in self.definitions[pub.root_type(self.app)]}
        self.assertNotIn('CanonicalDiagnosticWork',root_fields)
        for kind,members in self.definitions.items():
            self.assertLessEqual(len(kind),40,kind)
            self.assertEqual(len({m.name for m in members}),len(members),kind)
        self.assertEqual(len(__import__('fraktal_ab_generate').canonical_routines(self.app)),1)


if __name__=='__main__':unittest.main()
