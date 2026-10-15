"""Emit Core-shaped event/state services, with an optional typed sink binding."""
from pathlib import Path
import re
from fraktal_tia_binding import PRIVATE, type_source

HERE = Path(__file__).resolve().parents[1]/'Framework/Core'
ALARM = HERE/'alarm_services.scl.in'
STATE = HERE/'state_services.scl.in'


def expand(path, catalog):
    text = path.read_text(encoding='ascii')
    for name, values in catalog.enums.items():
        for key, value in values.items():
            text = text.replace('@'+name+'.'+key+'@',str(value))
    for key, value in catalog.capacities.items():
        text = text.replace('@'+key+'@',str(value))
    if '@STATE_KEY_WIDTH@' in text:
        field=next(f for f in catalog.resolve(['ST_StateFlag'])['ST_StateFlag'] if f['member']=='Key')
        text=text.replace('@STATE_KEY_WIDTH@',re.search(r'\[(\d+)\]',field['native_type'])[1])
    return text


def build(catalog, event_sink=''):
    fields = {'Active':'Array[1..%d] of "ST_AlarmEvent"'%catalog.capacities['MAX_ALARM_ACTIVE'],
              'NActive':'Int','Ring':'Array[1..%d] of "ST_AlarmEvent"'%catalog.capacities['MAX_ALARM_RING'],
              'RingHead':'Int','Blocking':'Bool','Truncated':'Bool'}
    public = set(fields)
    fields.update({'ComeMs':'Array[1..%d] of UDInt'%catalog.capacities['MAX_ALARM_ACTIVE'],
                   'Automatic':'Array[1..%d] of Bool'%catalog.capacities['MAX_ALARM_ACTIVE'],
                   'Touched':'Array[1..%d] of Bool'%catalog.capacities['MAX_ALARM_ACTIVE'], 'RingUsed':'Int'})
    if event_sink:
        fields['SinkEnabled'] = 'Bool'
    text = expand(ALARM,catalog).replace('@EVENT_SINK@',
        '    IF #AlarmLog.SinkEnabled THEN "'+event_sink+'"(Ev := #Ev); END_IF;' if event_sink else '    RETURN; // No event sink supplied by the composition declaration.')
    return type_source('FRK_AlarmLog',[{'member':n,'native_type':t,'accessible':n in public,'initial':''} for n,t in fields.items()]),text
