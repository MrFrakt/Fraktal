"""Emit Core-shaped event/state services, with an optional typed sink binding."""
from pathlib import Path
import re
import json
from fraktal_tia_binding import PRIVATE, type_source

HERE = Path(__file__).resolve().parents[1]/'Framework/Core'
ALARM = HERE/'alarm_services.scl.in'
STATE = HERE/'state_services.scl.in'
HISTORY = HERE/'alarm_history.scl.in'
RECOVERY = HERE/'alarm_recovery.scl.in'
RECOVERY_POLICY = HERE/'alarm_recovery.json'


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


def build(catalog, event_sink='', history=False, recovery=False, delivery=False):
    fields = {'Active':'Array[1..%d] of "ST_AlarmEvent"'%catalog.capacities['MAX_ALARM_ACTIVE'],
              'NActive':'Int','Ring':'Array[1..%d] of "ST_AlarmEvent"'%catalog.capacities['MAX_ALARM_RING'],
              'RingHead':'Int','Blocking':'Bool','Truncated':'Bool'}
    public = set(fields)
    fields.update({'ComeMs':'Array[1..%d] of UDInt'%catalog.capacities['MAX_ALARM_ACTIVE'],
                   'Automatic':'Array[1..%d] of Bool'%catalog.capacities['MAX_ALARM_ACTIVE'],
                   'Touched':'Array[1..%d] of Bool'%catalog.capacities['MAX_ALARM_ACTIVE'], 'RingUsed':'Int'})
    if history:fields['HistorySlot']='Int'
    if recovery:fields.update({'RecoverySlot':'Int','ElapsedBefore':'Array[1..%d] of UDInt'%catalog.capacities['MAX_ALARM_ACTIVE'],
                               'Recovering':'Array[1..%d] of Bool'%catalog.capacities['MAX_ALARM_ACTIVE']})
    if event_sink:
        fields['SinkEnabled'] = 'Bool'
    if delivery:fields.update({'DeliverySlot':'Int','DeliveryMuted':'Bool','DeliveryLossSlot':'Int'})
    text = expand(ALARM,catalog).replace('@EVENT_SINK@',
        '    IF #AlarmLog.SinkEnabled THEN "'+event_sink+'"(Ev := #Ev); END_IF;' if event_sink else '    RETURN; // No event sink supplied by the composition declaration.')
    for token,call in (
        ('@HISTORY_CLEAR@','IF #Startup AND #AlarmLog.HistorySlot > 0 THEN "FRK_AlarmHistoryClear"(AlarmLog := #AlarmLog); END_IF;'),
        ('@HISTORY_APPEND@','"FRK_AlarmHistoryAppend"(AlarmLog := #AlarmLog);'),
        ('@HISTORY_HEADER_SAVE@','"FRK_AlarmHistoryHeaderSave"(AlarmLog := #AlarmLog);')):
        text=text.replace(token,call if history else '')
    recovery_hooks={
        '@RECOVERY_REFRESH@':'"FRK_AlarmRecoveryRefresh"(AlarmLog := #AlarmLog);',
        '@RECOVERY_CLEAR@':'IF #Startup THEN "FRK_AlarmRecoveryClear"(AlarmLog := #AlarmLog); END_IF;',
        '@RECOVERY_CLAIM@':'#Slot := "FRK_AlarmRecoveryClaim"(AlarmLog := #AlarmLog, Diag := #Diag, ResetClass := #ResetClass); IF #Slot > 0 THEN #FRK_AlarmRaise := #Slot; RETURN; END_IF;',
        '@RECOVERY_NEW@':'#AlarmLog.ElapsedBefore[#Slot] := 0; #AlarmLog.Recovering[#Slot] := FALSE;',
        '@RECOVERY_STORE@':'"FRK_AlarmRecoveryStore"(AlarmLog := #AlarmLog, EventSlot := #Slot);',
        '@RECOVERY_CLOSE_PREPARE@':'"FRK_AlarmRecoveryClosePrepare"(AlarmLog := #AlarmLog, EventSlot := #Slot);',
        '@RECOVERY_CAPTURE@':'IF NOT #AlarmLog.Automatic[#Slot] THEN #AlarmLog.Automatic[#Slot] := TRUE; "FRK_AlarmRecoveryStore"(AlarmLog := #AlarmLog, EventSlot := #Slot); END_IF; #AlarmLog.Recovering[#Slot] := FALSE;'
    }
    for token,call in recovery_hooks.items():text=text.replace(token,call if recovery else '')
    text=text.replace('@DELIVERY_CAPTURE@','"FRK_DeliveryCapture"(AlarmLog := #AlarmLog, Ev := #AlarmLog.Active[#Slot]);' if delivery else '')
    text=text.replace('@ALARM_SPAN@','#Span := "FRK_AlarmRecoveryElapsed"(AlarmLog := #AlarmLog, EventSlot := #Slot);' if recovery else
        '#Span := "FRK_Elapsed"(NewMs := "FRK_Clock".NowMs, OldMs := #AlarmLog.ComeMs[#Slot]);\n    IF #Span > 2147483647 THEN #Span := 2147483647; END_IF;')
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


def recovery_sources(catalog):
    from fraktal_tia_generate import db
    active=catalog.capacities['MAX_ALARM_ACTIVE']
    fields=[('SchemaVersion','UInt'),('Scope','String[@NAME_WIDTH@]'),('Generation','UDInt'),('Checksum','DWord'),
            ('Active','Array[1..%d] of "ST_AlarmEvent"'%active),('EventCrc','Array[1..%d] of DWord'%active),
            ('Automatic','Array[1..%d] of Bool'%active),('Elapsed','Array[1..%d] of UDInt'%active),
            ('TimeCrc','Array[1..%d] of DWord'%active),('ElapsedAlt','Array[1..%d] of UDInt'%active),('TimeCrcAlt','Array[1..%d] of DWord'%active),('TimeBank','Array[1..%d] of Bool'%active),('PendingSlot','Int'),('PendingClosed','"ST_AlarmEvent"'),
            ('PendingCrc','DWord'),('PendingHead','Int'),('PendingHistoryGeneration','UDInt')]
    image=type_source('FRK_AlarmRecoveryImage',[dict(member=n,native_type=t,accessible=False,initial='') for n,t in fields])
    store=db('FRK_AlarmRecovery',['Rows'+PRIVATE+' : Array[1..@RECOVERY_COUNT@] of "FRK_AlarmRecoveryImage";',
            'Commissioned'+PRIVATE+' : Array[1..@RECOVERY_COUNT@] of Bool;']).replace('VAR\n','VAR RETAIN\n',1)
    runtime=db('FRK_AlarmRecoveryRuntime',['Ready'+PRIVATE+' : Array[1..@RECOVERY_COUNT@] of Bool;',
        'Blocked'+PRIVATE+' : Array[1..@RECOVERY_COUNT@] of Bool;'])
    text=expand(RECOVERY,catalog);policy=json.loads(RECOVERY_POLICY.read_bytes())
    for k,v in policy['reason'].items():
        if k in ('severity','category','reset_class'):v=catalog.enums[{'severity':'E_Severity','category':'E_Category','reset_class':'E_ResetClass'}[k]][v]
        text=text.replace('@RECOVERY_LOST_'+k.upper()+'@',str(v))
    return {'02_FRK_AlarmRecoveryImage.udt':image,'05_FRK_AlarmRecovery.db':store,'05_FRK_AlarmRecoveryRuntime.db':runtime},text
