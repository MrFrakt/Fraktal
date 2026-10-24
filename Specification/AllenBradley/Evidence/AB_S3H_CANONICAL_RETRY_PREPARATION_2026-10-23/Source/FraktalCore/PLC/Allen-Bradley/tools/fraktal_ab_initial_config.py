"""Validated commissioning data for an offline generated download image.

This carries configuration, not command/session/runtime latches or credentials.
The declaration still owns layout, defaults, schemas, bounds and capabilities.
An input image cannot add a tag, a member or an externally writable surface.
"""
import xml.etree.ElementTree as ET
import re


def migrate_line_v2(app, image):
    """Explicit commissioning migration; no runtime state or credentials copied.

    Four released weekly rows are retained exactly. The fifth is unused and
    targets are unconfigured. Validate the entire resulting image before return.
    """
    import copy
    import fraktal_ab_line as line
    import fraktal_ab_generate as gen
    result = copy.deepcopy(image)
    source = result['records'].pop('FRK_T_LineCfgV2')
    expected = {'SchemaVersion', 'UtcOffsetMin'} | {
        f'{name}{i}' for i in range(1, 5) for name in ('StartMin', 'DurationMin', 'ActiveDays')}
    if set(source) != expected or type(source['SchemaVersion']) is not int or source['SchemaVersion'] != 2:
        raise ValueError('initial V2 line configuration schema differs')
    rows = line.migrate_weekly(source['UtcOffsetMin'], tuple(
        (source[f'StartMin{i}'], source[f'DurationMin{i}'], source[f'ActiveDays{i}']) for i in range(1, 5)))
    record = line.cfg(app)
    target = {m.name: m.initial for m in record.members}
    target.update(source, SchemaVersion=record.schema_version)
    for i in range(1, line.MAX_SHIFTS + 1):
        target[f'ProductionTarget{i}'] = 0
    for i, row in enumerate(rows, 1):
        target.update({f'{n}{i}': v for n, v in zip(('StartMin', 'DurationMin', 'ActiveDays'), row)})
    result['records'][record.name] = target
    apply(app, gen.controller_tags(app), result)
    return result


def apply(app, tags_xml, image):
    if image is None:
        return tags_xml
    import fraktal_ab_generate as gen
    required = {'records', 'models', 'modelOrdinal'}
    if set(image) not in (required, required | {'modelCodes'}):
        raise ValueError('initial configuration image shape differs')
    if set(image['records']) != {r.name for r in app.records}:
        raise ValueError('initial configuration records differ')
    codes = image.get('modelCodes', [model.code for model in app.models])
    capacity = app.model_capacity or len(app.models)
    if (type(codes) is not list or not len(app.models) <= len(codes) <= capacity
            or codes[:len(app.models)] != [model.code for model in app.models]):
        raise ValueError('initial configuration catalog differs')
    import fraktal_ab_models as models
    if any(type(code) is not str or not 1 <= len(code) <= models.CODE_MAX
           or any(not 33 <= ord(char) <= 126 for char in code) for code in codes):
        raise ValueError('initial configuration model code differs')
    if len(set(codes)) != len(codes):
        raise ValueError('initial configuration model codes repeat')
    if type(image['models']) is not list or len(image['models']) != len(codes):
        raise ValueError('initial configuration model count differs')
    if type(image['modelOrdinal']) is not int or not 1 <= image['modelOrdinal'] <= len(codes):
        raise ValueError('initial configuration model ordinal differs')

    def checked(members, values, version):
        if set(values) != {m.name for m in members} or values['SchemaVersion'] != version:
            raise ValueError('initial configuration schema differs')
        for member in members:
            value = values[member.name]
            if member.dimension or type(value) is not int or not -2147483648 <= value <= 2147483647:
                raise ValueError('initial configuration requires declared DINT scalars')
            if member.kind == 'boolean' and value not in (0, 1):
                raise ValueError('initial configuration boolean differs')
            if member.write_key and not member.minimum <= value <= member.maximum:
                raise ValueError('initial configuration value outside its capability')

    ET.fromstring(tags_xml)
    active = image['models'][image['modelOrdinal'] - 1]
    par_cfg = next(r for r in app.records if r.par_cfg)
    if any(image['records'][par_cfg.name].get(m.name) != active.get(m.name)
           for m in gen.model_scoped_members(app)):
        raise ValueError('initial active recipe differs from its model record')
    def replace_values(tag_name, values, index=None, arrays=None):
        nonlocal tags_xml
        pattern = rf'(<Tag Name="{re.escape(tag_name)}"[^>]*>)(.*?)(</Tag>)'
        hits = list(re.finditer(pattern, tags_xml, re.S))
        if len(hits) != 1:
            raise ValueError('initial configuration tag is not unique')
        hit = hits[0]
        body = hit.group(2)
        if index is not None:
            element = re.search(rf'<Element Index="\[{index}\]">.*?</Element>', body, re.S)
            if element is None:
                raise ValueError('initial configuration element is absent')
            target = element.group()
        else:
            target = body
        for name, value in values.items():
            target, count = re.subn(
                rf'(<DataValueMember Name="{re.escape(name)}"[^>]* Value=")[^"]*(")',
                lambda m: m.group(1) + str(value) + m.group(2), target)
            if count != 1:
                raise ValueError('initial configuration member is not unique')
        for name, values in (arrays or {}).items():
            pattern = rf'(<ArrayMember Name="{re.escape(name)}"[^>]*>)(.*?)(</ArrayMember>)'
            hits = list(re.finditer(pattern, target, re.S))
            if len(hits) != 1:
                raise ValueError('initial configuration array is not unique')
            array = hits[0]
            if len(re.findall(r'<Element\b', array.group(2))) != len(values):
                raise ValueError('initial configuration array dimension differs')
            content = array.group(2)
            for position, value in enumerate(values):
                content, count = re.subn(
                    rf'(<Element Index="\[{position}\]" Value=")[^"]*(")',
                    lambda m: m.group(1) + str(value) + m.group(2), content)
                if count != 1:
                    raise ValueError('initial configuration array element is not unique')
            target = target[:array.start(2)] + content + target[array.end(2):]
        if index is not None:
            body = body[:element.start()] + target + body[element.end():]
        else:
            body = target
        tags_xml = tags_xml[:hit.start(2)] + body + tags_xml[hit.end(2):]

    for record in app.records:
        values = image['records'][record.name]
        checked(record.members, values, record.schema_version)
        if record.line_cfg:
            import fraktal_ab_line as line
            line.validate_calendar(values['UtcOffsetMin'], tuple(
                (values[f'StartMin{i}'], values[f'DurationMin{i}'], values[f'ActiveDays{i}'])
                for i in range(1, line.MAX_SHIFTS + 1)))
        replace_values(record.name + 'Tag', values)
    for index, values in enumerate(image['models']):
        checked(gen.model_cfg_members(app), values, gen.model_cfg_schema_version(app))
        replace_values(gen.model_cfg_tag(app), values, index)
    if app.model_capacity and 'modelCodes' in image:
        lengths = [len(code) for code in codes] + [0] * (capacity - len(codes))
        data = [ord(char) for code in codes
                for char in code + '\0' * (models.CODE_MAX - len(code))]
        data += [0] * ((capacity - len(codes)) * models.CODE_MAX)
        replace_values(models.tag(app), {'SchemaVersion': 1, 'Count': len(codes)},
                       arrays={'CodeLength': lengths, 'CodeBytes': data})
    replace_values(f'FRK_{app.name}_Unit', {'ModelOrdinal': image['modelOrdinal']})
    # Preserve the frozen StringFamily/CDATA serialization byte for byte.
    return tags_xml
