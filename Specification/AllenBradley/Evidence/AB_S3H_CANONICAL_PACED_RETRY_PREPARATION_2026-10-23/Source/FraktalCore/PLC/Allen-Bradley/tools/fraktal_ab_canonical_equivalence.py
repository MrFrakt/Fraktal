#!/usr/bin/env python3
"""Compare paired canonical/projection documents, path by path and type by type.

Only the five approved V2 D2 bounds may move a path. No value tolerance, ignored
path prefix, numeric bool coercion or implicit subset is accepted. Captured pairs
and a live acquisition callback use the same comparison. Matching manifest tokens
establish configuration coherence, not that two separate reads saw one scan.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import time

from fraktal_ab_canonical_reader import load_json

CONTRACT = Path(__file__).resolve().parents[4] / "Specification/AllenBradley/AB_FROZEN_CONTRACTS_V2.json"


def corrections():
    return load_json(CONTRACT)["arrayBounds"]["correctionsFromV1"]


def _type(doc, path):
    return doc.get("types", {}).get(path) or doc.get("dataValues", {}).get(path, {}).get("type")


def _equal(left, right):
    return type(left) is type(right) and left == right and not (
        isinstance(left, float) and (not math.isfinite(left) or not math.isfinite(right)))


def compare_documents(projection, canonical, *, require_types=True):
    old, new = projection["values"], canonical["values"]
    units = {p.removesuffix("/Status/ModuleType") for p, v in old.items()
             if p.endswith("/Status/ModuleType") and type(v) is int and v == 1}
    rules = corrections()
    mapped, differences, shifted = {}, [], []
    for path in sorted(old):
        target = path
        for unit in units:
            for rule in rules:
                prefix = re.escape(unit + "/" + rule["path"].removeprefix("<Unit>/"))
                hit = re.match(prefix + r"\[(\d+)\](?=/|$)", path)
                if hit:
                    index = int(hit[1])
                    if index < rule["oldLowerBound"]:
                        differences.append(dict(path=path, kind="invalidOldBound"))
                    target = path[:hit.start(1)] + str(index + rule["lowerBound"] - rule["oldLowerBound"]) + path[hit.end(1):]
                    shifted.append(dict(projectionPath=path, canonicalPath=target))
        if target in mapped:
            differences.append(dict(path=target, kind="mappingCollision", projectionPath=path))
        mapped[target] = path
    typed = 0
    for target in sorted(set(mapped) | set(new)):
        source = mapped.get(target)
        if source is None:
            differences.append(dict(path=target, kind="extraCanonical", canonical=new[target]))
            continue
        if target not in new:
            differences.append(dict(path=target, projectionPath=source, kind="missingCanonical", projection=old[source]))
            continue
        old_type, new_type = _type(projection, source), _type(canonical, target)
        if old_type is not None and new_type is not None:
            typed += 1
            if old_type != new_type:
                differences.append(dict(path=target, projectionPath=source, kind="type",
                                        projection=old_type, canonical=new_type))
        elif require_types:
            differences.append(dict(path=target, projectionPath=source, kind="missingType",
                                    projection=old_type, canonical=new_type))
        if not _equal(old[source], new[target]):
            differences.append(dict(path=target, projectionPath=source, kind="value",
                                    projection=old[source], canonical=new[target]))
    # V1 and V2 publish different manifests, hence different configuration hashes.
    # Each acquisition validates its own token. Same-state proof is separate.
    return dict(schema="fraktal.ab.canonical-equivalence", schemaVersion=1,
                equal=not differences, typeAcceptance=require_types and not differences and typed == len(mapped),
                comparedPaths=len(mapped), typedPaths=typed,
                d2AllowList=rules, correctedPaths=shifted, differences=differences)


def compare_live(acquire_pair):
    """Caller supplies one stable paired state; reject an unqualified live pair.

    S2's fixture must freeze the state or record a PLC snapshot-generation token.
    Merely reading two documents back-to-back cannot certify value equivalence.
    """
    pair = acquire_pair()
    if pair.get("sameStateVerified") is not True or not pair.get("stateEvidence"):
        raise ValueError("live equivalence requires recorded same-state evidence")
    report = compare_documents(pair["projection"], pair["canonical"])
    report["stateEvidence"] = pair["stateEvidence"]
    return report


def stable_scan_pair(read_generation, acquire, *, attempts=100, seconds=5.0, fresh_start=False):
    """Acquire only within one completed PLC scan, with bounded read-only retries.

    The PLC marks its entire scan odd before any owner runs and even after
    publication. Equality of an even generation around all paired reads proves
    they belong to that scan; configuration hashes alone cannot prove this.
    """
    if type(attempts) is not int or not 1 <= attempts <= 100 or not 0 < seconds <= 5 or type(fresh_start) is not bool:
        raise ValueError("invalid paired-acquisition budget")
    started, history = time.monotonic(), []
    previous = None
    for unused in range(attempts):
        if time.monotonic()-started > seconds:
            break
        before = read_generation()
        if type(before) is not int or not 1 <= before <= 2147483646:
            raise ValueError("invalid or uninitialized PLC scan generation")
        row = dict(before=before)
        history.append(row)
        if before % 2:
            previous = before
            continue
        if fresh_start and (previous is None or before == previous):
            # Waiting is part of this same bounded attempt history. Starting
            # near the even edge leaves the largest available read window;
            # it neither extends the budget nor accepts a changed generation.
            previous = before
            row['waitingFreshScan'] = True
            # Re-reading the same completed generation immediately can spend
            # the entire poll budget before enough scan edges are observed.
            # This wait stays inside the same attempt/time budget; the next
            # iteration checks its deadline before reading again.
            time.sleep(.001)
            continue
        pair = acquire()
        after = read_generation()
        row['after'] = after
        if type(after) is not int:
            raise ValueError("invalid trailing PLC scan generation")
        previous = after
        if before == after and time.monotonic()-started <= seconds:
            pair.update(sameStateVerified=True,
                        stateEvidence=dict(kind="PLC entire-scan generation", generation=before,
                                           attempts=history, readOnly=True))
            if fresh_start:pair['stateEvidence']['freshStart'] = True
            return pair
    error = ValueError("no completed PLC scan held across the paired read window")
    error.attempts = history
    raise error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--values-only", action="store_true", help="diagnostic: cannot pass type acceptance")
    args = parser.parse_args()
    report = compare_documents(load_json(args.projection), load_json(args.canonical),
                               require_types=not args.values_only)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({k: report[k] for k in ("equal", "typeAcceptance", "comparedPaths", "typedPaths")}))
    return 0 if report["equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
