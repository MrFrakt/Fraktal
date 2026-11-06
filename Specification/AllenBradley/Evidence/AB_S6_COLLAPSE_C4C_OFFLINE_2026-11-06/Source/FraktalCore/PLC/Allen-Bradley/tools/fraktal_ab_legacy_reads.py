"""Temporary legacy-baseline structure reader; removed with that read path.

One response, with the declared array extents, as the original press reader.
This decoder supplies historical fixture views, never the canonical client.
"""
import struct


def read_layout(comm, tag, layout):
    reply = comm.Read(tag)
    if reply.Status != 'Success':
        return None
    payload = reply.Value
    total = sum(m.dimension or 1 for m in layout)
    if not isinstance(payload, (bytes, bytearray)) or len(payload) < total * 4:
        return None
    values = struct.unpack_from(f'<{total}i', payload, 0)
    out, index = {}, 0
    for member in layout:
        if member.dimension:
            out[member.name] = list(values[index:index + member.dimension])
            index += member.dimension
        else:
            out[member.name] = values[index]
            index += 1
    return out
