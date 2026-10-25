"""Migration-only observation frame: one scan of the oracle's paired records.

Part III §3.13: a coherence-guarded set shall change less often than its read
window, or be buffered on the PLC side; retry is not a substitute. The S3h
oracle pairs the canonical root with the legacy owner records it projects,
about 172 KB that takes 8.7-15.9 ms to read against a 10 ms task. Every Nth
scan, after the canonical section has published, the PLC copies exactly those
records into one frame bracketed by its own odd/even generation, so a reader
holds still for N scans instead of racing one.

The frame is an instrument, never a shipping surface: it has no top-level
Status (no generic reader discovers it as a root), the manifest does not
describe it, it grants no write, and it exists only while legacy contexts do.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

# The stages whose oracle reads exactly legacy_sources(); a later stage that
# reads more extends both together.
FRAME_STAGES = (10,)
HEADER = ("SourceGeneration", "FragmentRevision")
NAME_LIMIT = 40
MAX_PERIOD_SCANS = 100


def enabled(app):
    return bool(app.canonical_observation_period_ms)


def period_scans(app):
    return app.canonical_observation_period_ms // app.task_period_ms


def frame_tag(app):
    return f"FRK_{app.name}_ObservationFrame"


def generation_tag(app):
    return f"FRK_{app.name}_ObservationGeneration"


def type_name(app):
    return f"FRK_T_{app.name}ObservationFrameS3h"


def public_tags(app):
    return (generation_tag(app), frame_tag(app)) if enabled(app) else ()


def legacy_sources(app):
    """The S3h oracle's legacy owner records, named by their owning helpers.

    The oracle checks its recorded reads against the frame Template, so a
    drift in either list fails the first capture instead of comparing less.
    """
    import fraktal_ab_access as access
    import fraktal_ab_canonical_config as config
    import fraktal_ab_data_access as data
    import fraktal_ab_generate as gen
    import fraktal_ab_host_events as host
    import fraktal_ab_models as models
    import fraktal_ab_part as part
    import fraktal_ab_sets as sets
    import fraktal_ab_signal_tower as tower
    n = app.name
    result = [f"FRK_{n}_Unit", *(gen.ctx_tag_for(app, m.name) for m in app.modules),
              f"FRK_{n}_Chart", *(f"{r.name}Tag" for r in app.records),
              gen.alarm_active_tag(app), gen.alarm_ring_tag(app)]
    if app.state_flags:result.append(gen.state_flags_tag(app))
    if app.access_users is not None:
        result += [access.tag(app, "State"), access.tag(app, "Audit"),
                   data.tag(app, "Policy"), data.tag(app, "Levels")]
    if app.model_capacity:result.append(models.tag(app))
    result.append(gen.config_persist_tag(app))
    if gen.model_cfg_members(app):result.append(gen.model_cfg_tag(app))
    if app.config_sets:result.append(sets.state_tag(app))
    result += [config.query_status_tag(app), gen.oee_tag(app), gen.profiler_tag(app)]
    if app.system_health is not None:result.append(gen.system_health_tag(app))
    result.append(gen.health_probe_tag(app))
    if app.part_carrier is not None:result.append(part.tag(app))
    if app.host_event_capacity:result.append(host.tag(app))
    if app.signal_tower is not None:result.append(tower.tag(app))
    return tuple(result)


def sources(app):
    return (app.name, *legacy_sources(app))


def validate(app):
    period = app.canonical_observation_period_ms
    if period == 0:
        return []
    if type(period) is not int or period < 0:
        return ["observation frame period is a non-negative integer of milliseconds"]
    if app.canonical_publication_stage not in FRAME_STAGES:
        return ["observation frame supports only the S3h oracle stage"]
    findings = []
    if period % app.task_period_ms or not 2 <= period // app.task_period_ms <= MAX_PERIOD_SCANS:
        findings.append(f"observation frame period is 2..{MAX_PERIOD_SCANS} whole task periods")
    names = sources(app)
    if len(set(names)) != len(names) or set(names) & set(HEADER):
        findings.append("observation frame members collide")
    if any(len(name) > NAME_LIMIT for name in (*names, frame_tag(app), generation_tag(app), type_name(app))):
        findings.append(f"observation frame identifier exceeds {NAME_LIMIT} characters")
    return findings


def _declared(app):
    """Each source's emitted DataType and dimension, from the one tag emitter."""
    import fraktal_ab_generate as gen
    tags = {tag.get("Name"): tag for tag in ET.fromstring(gen.controller_tags(app)).findall("Tag")}
    result = {}
    for name in sources(app):
        tag = tags.get(name)
        if tag is None:
            raise ValueError(f"observation source is not an emitted controller tag: {name}")
        result[name] = (tag.get("DataType"), int(tag.get("Dimensions") or 0))
    return result


def data_types(app):
    if not enabled(app):
        return []
    node = ET.Element("DataType", Name=type_name(app), Family="NoFamily", Class="User")
    members = ET.SubElement(node, "Members")
    for name in HEADER:
        ET.SubElement(members, "Member", Name=name, DataType="DINT", Dimension="0", Radix="Decimal",
                      Hidden="false", ExternalAccess="Read Only")
    for name, (kind, count) in _declared(app).items():
        ET.SubElement(members, "Member", Name=name, DataType=kind, Dimension=str(count), Radix="NullType",
                      Hidden="false", ExternalAccess="Read Only")
    return [ET.tostring(node, encoding="unicode")]


def tags(app):
    if not enabled(app):
        return []
    return [f'<Tag Name="{generation_tag(app)}" TagType="Base" DataType="DINT" Radix="Decimal" ExternalAccess="Read Only"/>',
            f'<Tag Name="{frame_tag(app)}" TagType="Base" DataType="{type_name(app)}" Constant="false" ExternalAccess="Read Only"/>']


def cyclic(app):
    """Last in the scan: every owner and the canonical section have run.

    The odd mark is derived, not incremented, so an interrupted copy is never
    followed by a frame that reads complete without a whole copy in between.
    """
    if not enabled(app):
        return []
    import fraktal_ab_canonical_publication as publisher
    g, frame = generation_tag(app), frame_tag(app)
    lines = [f"IF (FRK_{app.name}_ScanCount MOD {period_scans(app)}) = 0 THEN",
             f"IF ({g} < 0) OR ({g} >= 2147483645) THEN {g} := 0; END_IF;",
             f"{g} := {g} - ({g} MOD 2) + 1;",
             f"{frame}.SourceGeneration := {publisher.generation_tag(app)};",
             f"{frame}.FragmentRevision := {publisher.header_tag(app)}.FragmentRevision;"]
    for name, (unused, count) in _declared(app).items():
        lines += ([f"CPS({name}[{i}],{frame}.{name}[{i}],1);" for i in range(count)] if count
                  else [f"CPS({name},{frame}.{name},1);"])
    return lines + [f"{g} := {g} + 1;", "END_IF;"]
