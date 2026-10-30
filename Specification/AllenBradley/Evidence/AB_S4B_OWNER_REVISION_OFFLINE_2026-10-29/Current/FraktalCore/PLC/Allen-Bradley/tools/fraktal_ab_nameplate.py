"""Static nameplate declaration -> manifest -> generic HMI paths.

No gateway identity defaults or PLC configuration values become asset facts.
Version 5 appends text-key columns to the released numeric v4 row.
"""
from __future__ import annotations

from urllib.parse import urlsplit

import fraktal_ab_declaration as decl

# declaration member, manifest key column, generic repository leaf
FIELDS = (
    ('manufacturer', 'ManufacturerKey', 'ManufacturerName'),
    ('product', 'ProductKey', 'ProductDesignation'),
    ('serial', 'SerialKey', 'SerialNumber'),
    ('product_uri', 'AssetKey', 'ProductUri'),
    ('year', 'YearKey', 'YearOfConstruction'),
    ('hardware_version', 'HardwareVersionKey', 'HardwareVersion'),
    ('firmware_version', 'FirmwareVersionKey', 'FirmwareVersion'),
    ('software_version', 'SoftwareVersionKey', 'SoftwareVersion'),
    ('order_code', 'OrderCodeKey', 'OrderCode'),
    ('documentation_url', 'DocumentationKey', 'DocumentationUrl'),
)
V5_COLUMNS = tuple(column for _, column, _ in FIELDS[4:])


def declared(app):
    return any(owner.nameplate is not None for owner in (app, *app.modules))


def validate(app):
    findings = []
    for owner in (app, *app.modules):
        plate = owner.nameplate
        if plate is None:
            continue
        if not isinstance(plate, decl.Nameplate):
            findings.append(f'{owner.name}: nameplate must be a Nameplate')
            continue
        for field, _, _ in FIELDS:
            value = getattr(plate, field)
            if (not isinstance(value, str) or len(value) > 240
                    or (value and (not value.isascii() or not value.isprintable()))):
                findings.append(f'{owner.name}: nameplate {field} must be printable ASCII, at most 240 bytes')
        if not all(isinstance(getattr(plate, k), str) and getattr(plate, k).strip()
                   for k in ('manufacturer', 'product', 'serial')):
            findings.append(f'{owner.name}: nameplate requires manufacturer, product and serial')
        if isinstance(plate.year, str) and plate.year and (not plate.year.isdigit() or len(plate.year) != 4):
            findings.append(f'{owner.name}: nameplate year must contain four digits')
        if isinstance(plate.documentation_url, str) and plate.documentation_url:
            try:
                url = urlsplit(plate.documentation_url)
                if (url.scheme not in ('https', 'http') or not url.hostname
                        or url.username is not None or url.password is not None):
                    raise ValueError('invalid URL')
            except ValueError:
                findings.append(f'{owner.name}: nameplate documentation URL must be HTTP(S) without credentials')
    return findings


def rows(app, keys, ids):
    result = []
    for owner in (app, *app.modules):
        plate = owner.nameplate
        if plate is None:
            continue
        row = dict(ModuleId=ids[owner.name], ModelKey=0, HardwareRevision=0,
                   SoftwareRevision=0, LocationKey=0)
        for field, column, _ in FIELDS:
            value = getattr(plate, field)
            row[column] = keys.key(value) if value else 0
        result.append(row)
    return result


def project(rows, module_id):
    catalogue = {r['NumericKey']: r['PortableKey'] for r in rows['Localization']}
    plates = [r for r in rows['Nameplates'] if r['ModuleId'] == module_id]
    if len(plates) > 1:
        raise ValueError('duplicate nameplate for a module')
    if not plates:
        return {}
    result = {}
    for _, column, leaf in FIELDS:
        key = plates[0][column]
        if key and key not in catalogue:
            raise ValueError('nameplate text key is absent from the manifest')
        result[f'Nameplate/{leaf}'] = catalogue[key] if key else ''
    return result
