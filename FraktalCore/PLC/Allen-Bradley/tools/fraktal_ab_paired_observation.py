"""Read the PLC observation frame inside the unchanged equal-even proof.

The frame's own Template, not a station list, locates every record: each
member is named for the controller tag it copies and must have that tag's
Template handle and warmed size. The frame must hold exactly what the oracle
reads, and its stamps must show a scan at or after the capture request and the
revision of the cached definition records. Only wire reads sit inside the
proof; slicing and every check follow its closing sample.
"""
import re
from types import SimpleNamespace

from fraktal_ab_canonical_equivalence import stable_scan_pair

ELEMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?:\[(\d+)\])?\Z")
DINT = 0xC4
# The qualified read size: 44 fragments fit the frame period, 500-byte mailbox
# framing needs about 350 and never does.
READ_CONNECTION_BYTES = 4000


def layout(seed, frame, tags, sizes, header):
    """Byte range of every live tag inside the frame, refused before any read."""
    symbols = {s["name"]: s for s in seed["symbols"]}
    templates = {t["handle"]: t for t in seed["templates"]}
    if frame not in symbols or symbols[frame]["arrayRank"] or symbols[frame]["handle"] not in templates:
        raise ValueError("observation frame Symbol/Template unavailable")
    template = templates[symbols[frame]["handle"]]
    members = {row["name"]: row for row in template["members"]}
    if any(members.get(name, {}).get("atomic") != DINT or members[name]["array"] for name in header):
        raise ValueError("observation frame header differs")
    slices, read = {}, set()
    for tag in tags:
        match = ELEMENT.fullmatch(tag)
        if not match or match.group(1) not in members or match.group(1) in header:
            raise ValueError(f"oracle read is not in the observation frame: {tag}")
        name, index = match.group(1), match.group(2)
        row, symbol = members[name], symbols.get(name)
        if (symbol is None or not row["struct"] or row["handle"] != symbol["handle"] or row["handle"] not in templates
                or bool(row["array"]) != bool(symbol["arrayRank"]) or (index is None) == bool(row["array"])):
            raise ValueError(f"observation frame member differs from its controller tag: {tag}")
        element = templates[row["handle"]]["byteSize"]
        position = int(index or 0)
        if element != sizes[tag] or position >= (row["info"] if row["array"] else 1):
            raise ValueError(f"observation frame member size or element differs: {tag}")
        start = row["offset"] + position * element
        slices[tag] = (start, start + element)
        read.add(name)
    if read != set(members) - set(header):
        raise ValueError("observation frame members differ from the oracle reads")
    ranges = sorted(slices.values())
    if ranges[-1][1] > template["byteSize"] or any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
        raise ValueError("observation frame ranges overlap or exceed the frame")
    return dict(size=template["byteSize"], slices=slices,
                header={name: members[name]["offset"] for name in header})


def _dint(raw, offset):
    return int.from_bytes(raw[offset:offset + 4], "little", signed=True)


def read(channels, *, frame, tags, sizes, seed, cached, live_generation, frame_generation,
         fragment_revision, period_scans):
    """The paired-read result shape of the live path, sourced from one frame."""
    import fraktal_ab_paired_fragments as fragments
    import fraktal_ab_paired_socket_reads as sockets
    import fraktal_ab_canonical_observation as observation
    sizes_in_use = sorted({c.ConnectionSize for c in channels})
    if sizes_in_use != [READ_CONNECTION_BYTES]:
        raise ValueError(f"observation frame reads need {READ_CONNECTION_BYTES}-byte connections, not {sizes_in_use}")
    live = [tag for tag in tags if tag not in cached]
    plan = layout(seed, frame, live, sizes, observation.HEADER)
    plans = fragments.partition(channels[0], [frame], {frame: plan["size"]}, connections=len(channels))
    not_before = live_generation()
    if type(not_before) is not int or not 1 <= not_before <= 2147483646:
        raise ValueError("invalid or uninitialized PLC scan generation")
    def acquire():
        return dict(rawBatches=[reply for group in sockets.acquire(channels, plans) for reply in group])
    pair = stable_scan_pair(frame_generation, acquire, fresh_start=True)
    read_plan = [item for p in plans for item in p]
    replies = pair.pop("rawBatches")
    raw = fragments.decode(read_plan, replies, {frame: plan["size"]})[frame].Value
    source = _dint(raw, plan["header"]["SourceGeneration"])
    revision = _dint(raw, plan["header"]["FragmentRevision"])
    if source % 2 or not 2 <= source <= 2147483646:
        raise ValueError("observation frame source generation is not a completed scan")
    if source < not_before:
        raise ValueError("observation frame predates the capture request")
    if revision != fragment_revision:
        raise ValueError("observation frame revision differs from the cached definitions")
    responses = {tag: SimpleNamespace(Status="Success", Value=raw[a:b]) for tag, (a, b) in plan["slices"].items()}
    responses.update(cached)
    pair["rawResponses"] = [responses[tag] for tag in tags]
    pair["readPlan"] = [{k: v for k, v in item.items() if k != "request"} for item in read_plan]
    pair["fragmentPacketEvidence"] = [dict(plan={k: v for k, v in item.items() if k != "request"},
        status=reply[0], rawHex=reply[1].hex()) for item, reply in zip(read_plan, replies, strict=True)]
    pair["readConnections"] = len(channels)
    pair["readTransport"] = "one outstanding read per socket; single multiplex owner"
    pair["stateEvidence"].update(kind="PLC observation frame generation", frame=dict(
        tag=frame, bytes=plan["size"], sourceGeneration=source, notBefore=not_before,
        fragmentRevision=revision, periodScans=period_scans))
    return pair
