"""Strict initial-value decoding when Studio omits large Decorated records.

The native UDT declaration owns member order and array extents. Unsupported
atoms, nonzero string padding and unexpected shape refuse the read-back gate.
"""
import math
import re
import struct


def native_value(kind,text):
    """Canonical exact native value, including signed zero and IEEE width."""
    if kind in ('REAL','LREAL'):
        if not re.fullmatch(r'-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?',text):raise ValueError('unsupported native floating atom')
        number=float(text)
        if not math.isfinite(number):raise ValueError('nonfinite native floating initializer')
        try:raw=struct.pack('<f' if kind=='REAL' else '<d',number)
        except (OverflowError,struct.error) as error:raise ValueError('native floating initializer overflows') from error
        return kind+':'+raw.hex()
    if text.startswith('2#'):
        if kind!='BOOL' or text not in ('2#0','2#1'):raise ValueError('binary initializer is not a scalar BOOL')
        return text[2:]
    return text


def parse(text):
    position=0
    def value():
        nonlocal position
        while position<len(text) and text[position].isspace():position+=1
        if position>=len(text):raise ValueError('truncated L5K initializer')
        char=text[position]
        if char=='[':
            position+=1;result=[]
            while True:
                while position<len(text) and text[position].isspace():position+=1
                if position<len(text) and text[position]==']':
                    if result:raise ValueError('trailing L5K array delimiter')
                    position+=1;return result
                result.append(value())
                while position<len(text) and text[position].isspace():position+=1
                if position>=len(text):raise ValueError('unterminated L5K array')
                if text[position]==']':position+=1;return result
                if text[position]!=',':raise ValueError('invalid L5K array delimiter')
                position+=1
        if char=="'":
            start=position;position+=1
            while position<len(text):
                if text[position]=='$':position+=2;continue
                if text[position]=="'":position+=1;return text[start:position]
                position+=1
            raise ValueError('unterminated L5K ASCII initializer')
        match=re.match(r'2#[01](?![01])|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?',text[position:])
        if not match:raise ValueError('unsupported L5K atom')
        position+=len(match[0])
        return match[0]
    result=value()
    if text[position:].strip():raise ValueError('trailing L5K initializer data')
    return result


def decode(root,tag,path,ascii_payload):
    types={t.get('Name'):t for t in root.findall('Controller/DataTypes/DataType')}
    data=tag.find("Data[@Format='L5K']")
    if data is None:raise ValueError('authored initial values missing in native read-back: '+path)
    result={}
    def count(text):
        if text in (None,'','0'):return 0
        if not re.fullmatch(r'[1-9][0-9]*(?:[, ][1-9][0-9]*){0,2}',text):raise ValueError('unsupported L5K dimensions')
        return math.prod(map(int,re.split('[, ]',text)))
    def walk(kind,value,current,extent=0):
        if extent:
            if not isinstance(value,list) or len(value)!=extent:raise ValueError('L5K array extent differs: '+current)
            for index,item in enumerate(value):walk(kind,item,current+f'/[{index}]')
            return
        declaration=types.get(kind)
        if declaration is not None:
            members=[m for m in declaration.findall('Members/Member') if m.get('Hidden')!='true']
            if not isinstance(value,list) or len(value)!=len(members):raise ValueError('L5K structure shape differs: '+current)
            if declaration.get('Family')=='StringFamily':
                if [m.get('Name') for m in members]!=['LEN','DATA']:raise ValueError('unsupported L5K StringFamily shape')
                length=int(value[0]);width=count(members[1].get('Dimension'))
                payload=ascii_payload(value[1])
                if not 0<=length<=width or len(payload)!=width or any(payload[length:]):
                    raise ValueError('invalid L5K string extent/padding: '+current)
                result[current+'/LEN']=str(length)
                result[current+'/DATA']=payload[:length]
                return
            for member,item in zip(members,value,strict=True):
                walk(member.get('DataType'),item,current+'/'+member.get('Name'),count(member.get('Dimension')))
            return
        if kind not in ('BOOL','SINT','INT','DINT','LINT','LDT','REAL','LREAL') or isinstance(value,list):
            raise ValueError('unsupported L5K native atom: '+kind)
        if kind not in ('REAL','LREAL') and not re.fullmatch(r'-?\d+|2#[01]',value):
            raise ValueError('noninteger L5K value for integer native type')
        result[current]=native_value(kind,value)
    walk(tag.get('DataType'),parse(''.join(data.itertext()).strip()),path,count(tag.get('Dimensions')))
    return result
