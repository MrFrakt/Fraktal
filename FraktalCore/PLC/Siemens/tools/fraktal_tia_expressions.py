"""Prefix declared locals in the small platform-neutral expression ports."""
import re

TOKEN=re.compile(r"//[^\n]*|\(\*.*?\*\)|'(?:\$.|[^'])*'|[A-Za-z_]\w*|.",re.S)


def locals_in(text,variables):
    pieces=[];previous='';tokens=[m[0] for m in TOKEN.finditer(text)]
    for index,token in enumerate(tokens):
        value=token
        following=next((v for v in tokens[index+1:] if v.strip()),'')
        formal=previous in ('(', ',') and following==':'
        if value in variables and previous!='.' and not formal:value='#'+value
        pieces.append(value)
        if value.strip() and not value.startswith('//'):previous=value
    return ''.join(pieces)
