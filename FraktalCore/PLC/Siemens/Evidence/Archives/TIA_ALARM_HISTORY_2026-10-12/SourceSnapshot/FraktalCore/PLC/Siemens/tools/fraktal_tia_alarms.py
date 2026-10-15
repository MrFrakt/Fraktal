"""Emit Core-shaped event/state services, with an optional typed sink binding."""
from pathlib import Path
import re
from fraktal_tia_binding import PRIVATE, type_source

HERE = Path(__file__).resolve().parents[1]/'Framework/Core'
ALARM = HERE/'alarm_services.scl.in'
STATE = HERE/'state_services.scl.in'
HISTORY = HERE/'alarm_history.scl.in'


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


def build(catalog, event_sink='', history=False):
    fields = {'Active':'Array[1..%d] of "ST_AlarmEvent"'%catalog.capacities['MAX_ALARM_ACTIVE'],
              'NActive':'Int','Ring':'Array[1..%d] of "ST_AlarmEvent"'%catalog.capacities['MAX_ALARM_RING'],
              'RingHead':'Int','Blocking':'Bool','Truncated':'Bool'}
    public = set(fields)
    fields.update({'ComeMs':'Array[1..%d] of UDInt'%catalog.capacities['MAX_ALARM_ACTIVE'],
                   'Automatic':'Array[1..%d] of Bool'%catalog.capacities['MAX_ALARM_ACTIVE'],
                   'Touched':'Array[1..%d] of Bool'%catalog.capacities['MAX_ALARM_ACTIVE'], 'RingUsed':'Int'})
    if history:fields['HistorySlot']='Int'
    if event_sink:
        fields['SinkEnabled'] = 'Bool'
    text = expand(ALARM,catalog).replace('@EVENT_SINK@',
        '    IF #AlarmLog.SinkEnabled THEN "'+event_sink+'"(Ev := #Ev); END_IF;' if event_sink else '    RETURN; // No event sink supplied by the composition declaration.')
    for token,call in (
        ('@HISTORY_CLEAR@','IF #Startup AND #AlarmLog.HistorySlot > 0 THEN "FRK_AlarmHistoryClear"(AlarmLog := #AlarmLog); END_IF;'),
        ('@HISTORY_APPEND@','"FRK_AlarmHistoryAppend"(AlarmLog := #AlarmLog);'),
        ('@HISTORY_HEADER_SAVE@','"FRK_AlarmHistoryHeaderSave"(AlarmLog := #AlarmLog);')):
        text=text.replace(token,call if history else '')
    return type_source('FRK_AlarmLog',[{'member':n,'native_type':t,'accessible':n in public,'initial':''} for n,t in fields.items()]),text


def history_sources(catalog):
    """A private keyed closed-ring image; event checksums follow the Core record."""
    from fraktal_tia_generate import db
    fields = [('SchemaVersion','UInt'), ('Scope','String[@NAME_WIDTH@]'),
              ('Generation','UDInt'), ('RingHead','Int'), ('RingUsed','Int'),
              ('Truncated','Bool'), ('Checksum','DWord'),
              ('Ring','Array[1..%d] of "ST_AlarmEvent"' % catalog.capacities['MAX_ALARM_RING']),
              ('EventCrc','Array[1..%d] of DWord' % catalog.capacities['MAX_ALARM_RING'])]
    image = type_source('FRK_AlarmHistoryImage', [dict(member=n,native_type=t,accessible=False,initial='') for n,t in fields])
    storage = db('FRK_AlarmHistory', ['Rows'+PRIVATE+' : Array[1..@UNIT_COUNT@] of "FRK_AlarmHistoryImage";',
        'Commissioned'+PRIVATE+' : Array[1..@UNIT_COUNT@] of Bool;']).replace('VAR\n','VAR RETAIN\n',1)
    lines=[]
    for field in catalog.resolve(['ST_AlarmEvent'])['ST_AlarmEvent']:
        n,t=field['member'],field['native_type'];target='#Ev.'+n
        if t.startswith(('String[','WString[')):
            lines += ['    #Size := LEN('+target+');',
                      '    #Work := "FRK_CrcNumber"(Previous := #Work, Value := INT_TO_UDINT(#Size));',
                      '    FOR #Index := 1 TO #Size DO']
            if t.startswith('WString'):
                lines += ['        #Code := WCHAR_TO_WORD('+target+'[#Index]);',
                          '        #Work := "FRK_CrcByte"(Previous := #Work, Value := WORD_TO_BYTE(#Code));',
                          '        #Work := "FRK_CrcByte"(Previous := #Work, Value := WORD_TO_BYTE(SHR(IN := #Code, N := 8)));']
            else:lines += ['        #Work := "FRK_CrcByte"(Previous := #Work, Value := CHAR_TO_BYTE('+target+'[#Index]));']
            lines += ['    END_FOR;']
        elif t=='LDT':
            lines += ['    #Wide := LINT_TO_LWORD(LDT_TO_LINT('+target+'));',
                      '    #Work := "FRK_CrcNumber"(Previous := #Work, Value := DWORD_TO_UDINT(LWORD_TO_DWORD(#Wide)));',
                      '    #Work := "FRK_CrcNumber"(Previous := #Work, Value := DWORD_TO_UDINT(LWORD_TO_DWORD(SHR(IN := #Wide, N := 32))));']
        else:
            value={'DInt':'DINT_TO_UDINT('+target+')','Bool':'BOOL_TO_UDINT('+target+')','Time':'DINT_TO_UDINT(TIME_TO_DINT('+target+'))'}.get(t)
            if value is None:raise ValueError('Unmapped alarm checksum field '+n+': '+t)
            lines += ['    #Work := "FRK_CrcNumber"(Previous := #Work, Value := '+value+');']
    text=expand(HISTORY,catalog).replace('@EVENT_CRC_FIELDS@','\n'.join(lines))
    return {'02_FRK_AlarmHistoryImage.udt':image,'05_FRK_AlarmHistory.db':storage},text
