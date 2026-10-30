"""Generate cross-language V6.10 metadata goldens; no native ABI claim."""
import argparse
import gzip
import json
import hashlib
from copy import deepcopy
from pathlib import Path

import fraktal_ab_canonical_manifest as wire
import fraktal_ab_canonical_publication as pub
import fraktal_ab_owner_read_bindings as owner


def fixture(app):
    definitions = pub.schema(app)
    header = pub.manifest_values(app, definitions)

    def physical(kind, value):
        if kind.startswith(pub.PREFIX + 'String'):
            raw = value.encode('utf-8')
            return dict(string=True, width=pub.string_width(kind), LEN=len(raw), bytes=raw.hex())
        if kind not in definitions:
            return value
        return {m.name: ([physical(m.kind, v) for v in value[m.name]] if m.count
                         else physical(m.kind, value[m.name])) for m in definitions[kind]}

    normalized = wire.normalize(physical(pub.header_type(app), header))
    return dict(schema='fraktal.ab.owner-metadata-fixture', schemaVersion=1,
                nativeCapture=False, nativeAcceptanceClaim=False,
                physicalManifest=header, normalized=normalized,
                expectedHeaderPaths=sum(len(json.loads(r['MembersJson'])) for r in owner.rows(app, definitions)))


def apparatus(app, capture_bytes):
    """Keep native product bytes; synthesize only additive discovery metadata.

    Handles/layouts allocated here are peer apparatus, never measured Logix ABI.
    Actual ABI, fit and runtime correctness require the new-image native gates.
    """
    pin = 'b0ebfbd06853fbaf1262c3b74549f88f99bd9af37e1585844dc5b9a4291afb4a'
    if hashlib.sha256(capture_bytes).hexdigest() != pin:
        raise ValueError('apparatus source differs from sealed V6.8 capture')
    capture = json.loads(gzip.decompress(capture_bytes))
    metadata = fixture(app)
    old_manifest = capture['manifest']
    # Preserve the captured runtime publication token, not the generator's
    # pre-run initializer. It is outside the immutable manifest hash body.
    metadata['normalized']['fragmentRevision'] = old_manifest['fragmentRevision']
    for key, value in old_manifest.items():
        if key not in ('schemaMinor', 'contentHash', 'configRevision') and metadata['normalized'][key] != value:
            raise ValueError('apparatus would change existing manifest facts: '+key)
    definitions = pub.schema(app)
    templates = capture['templates']
    by_name = {t['name']:t for t in templates}
    used = {t['handle'] for t in templates}
    def allocate():
        handle = next(h for h in range(1, 4096) if h not in used)
        used.add(handle)
        return handle
    def structure(kind):
        if kind in by_name:
            return by_name[kind]
        handle = allocate(); offset = 0; members = []
        for m in definitions[kind]:
            if m.kind != 'DINT':
                child = structure(m.kind); code = 0x8000 | child['handle']; size = child['byteSize']
            else:
                code, size = 0xc4, 4
            members.append(dict(name=m.name, info=m.count, code=code | (0x2000 if m.count else 0),
                                offset=offset))
            offset += size * (m.count or 1)
        result = dict(handle=handle, name=kind, byteSize=offset, structureHandle=50000+handle, members=members)
        templates.append(result); by_name[kind] = result
        return result
    # All old header columns retain their exact native layouts and capacities.
    source = next(t for t in templates if t['name'].endswith('CanonicalManifestV68'))
    header = deepcopy(source); header.update(handle=allocate(), name=pub.header_type(app))
    header['structureHandle'] = 50000 + header['handle']
    row = structure(owner.ROW); offset = source['byteSize']
    for name in ('OwnerReadBindingsCount', 'OwnerReadBindingsCapacity'):
        header['members'].append(dict(name=name, info=0, code=0xc4, offset=offset)); offset += 4
    count = len(metadata['normalized']['ownerReadBindings'])
    header['members'].append(dict(name='OwnerReadBindings', info=count,
        code=0xa000 | row['handle'], offset=offset))
    header['byteSize'] = offset + count * row['byteSize']
    templates.append(header)
    for symbol in capture['symbols']:
        if symbol.get('handle') == source['handle']:
            symbol['handle'] = header['handle']
    for binding in metadata['normalized']['ownerReadBindings']:
        capture['symbols'].append(dict(name=binding['RevisionSymbol'], atomic=0xc4, arrayRank=0))
    capture['manifest'] = metadata['normalized']
    from fraktal_ab_canonical_reader import coherence_token
    capture['coherenceBefore'] = capture['coherenceAfter'] = coherence_token(capture['manifest'])
    capture['apparatus'] = dict(nativeCapture=False, nativeAcceptanceClaim=False,
        sourceCaptureSha256=pin, synthetic='V6.10 manifest templates and owner counter Symbols only',
        nativeProductBytesUnchanged=True)
    return capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--apparatus-from', type=Path)
    args = parser.parse_args()
    from fraktal_ab_genealogy_s4b_owner_demo import application
    value = (apparatus(application(), args.apparatus_from.read_bytes())
             if args.apparatus_from else fixture(application()))
    with args.output.open('xb') as stream:
        stream.write(gzip.compress(json.dumps(value, ensure_ascii=True, separators=(',', ':')).encode(), mtime=0))
    print(json.dumps(dict(output=str(args.output), nativeCapture=False,
        expectedHeaderPaths=(value.get('expectedHeaderPaths') if not args.apparatus_from else
            sum(len(json.loads(r['MembersJson'])) for r in value['manifest']['ownerReadBindings'])))))


if __name__ == '__main__':
    main()
