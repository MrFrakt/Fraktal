"""Strict Core declaration parsing shared by the TIA generators and probes."""
import re


def plain(text):
    return re.sub(r"//[^\n]*|\(\*.*?\*\)", "", text, flags=re.S)


def bound(expression, capacities):
    expression = re.sub(r"PL_Fraktal\.(MAX_\w+)", r"\1", str(expression))
    for name in sorted(capacities, key=len, reverse=True):
        expression = re.sub(r"\b" + name + r"\b", str(capacities[name]), expression)
    if not re.fullmatch(r"[\d+* -]+", expression):
        raise ValueError("unsupported constant expression: " + expression)
    return eval(expression, {"__builtins__": {}}, {})


def struct_members(declaration):
    match = re.search(r"\bSTRUCT\b(.*?)\bEND_STRUCT\b", plain(declaration), re.S)
    if not match:
        raise ValueError("no structure declaration")
    structure = match.group(1)
    pattern = (r"\s*((?:\{attribute\s+'OPC\.UA\.DA'\s*:=\s*'[01]'\}\s*)*)"
               r"(\w+)\s*:\s*([^;]+);")
    matches = list(re.finditer(pattern, structure, re.I))
    if not matches:
        raise ValueError("no fields parsed")
    if re.sub(pattern, "", structure, flags=re.I).strip():
        raise ValueError("unsupported field declaration; refusing partial structure")
    names = [member[2].casefold() for member in matches]
    if len(names) != len(set(names)):
        raise ValueError("duplicate structure field")
    members = []
    for member in matches:
        attributes = re.findall(r"'([01])'", member[1])
        if len(attributes) > 1:
            raise ValueError("duplicate publication attribute")
        members.append({"name": member[2], "type": member[3],
                        "accessible": not attributes or attributes[0] == "1"})
    return members


def struct_fields(declaration):
    return [(member["name"], member["type"]) for member in struct_members(declaration)]


def enum_values(declaration):
    text = plain(declaration)
    body = re.search(r"\((.*?)\)\s*(?:DINT|INT|UINT|UDINT)?\s*;", text, re.S)
    if not body:
        raise ValueError("no enum declaration")
    result = {}
    for item in body[1].split(","):
        match = re.fullmatch(r"\s*(\w+)\s*:=\s*(-?\d+)\s*", item)
        if not match:
            raise ValueError("enum expression not supported: " + item)
        if match[1].casefold() in {name.casefold() for name in result}:
            raise ValueError("duplicate enum member: " + match[1])
        value = int(match[2])
        if not -2147483648 <= value <= 2147483647:
            raise ValueError("enum ordinal exceeds DInt: " + match[1])
        result[match[1]] = value
    return result
