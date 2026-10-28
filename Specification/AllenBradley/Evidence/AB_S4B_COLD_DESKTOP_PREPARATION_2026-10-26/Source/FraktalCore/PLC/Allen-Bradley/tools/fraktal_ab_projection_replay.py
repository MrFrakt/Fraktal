#!/usr/bin/env python3
"""Legacy projection golden-capture oracle, isolated from the canonical reader.

Run in a fresh process: legacy projection chooses its declaration at import.
This station-aware adapter is test infrastructure, never a discovery client.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

from fraktal_ab_canonical_reader import load_json


class Replay:
    def __init__(self, reads):
        self.reads, self.index = reads, 0

    def Read(self, tag, count=None):
        if self.index >= len(self.reads):
            raise ValueError("projection requested an unrecorded read")
        item = self.reads[self.index]
        if (tag, count) != (item["tag"], item["count"]):
            raise ValueError(f"read {self.index}: recorded request differs from projection")
        self.index += 1
        value = item["value"]
        return SimpleNamespace(Status=item["status"], TagName=tag,
                               Value=bytes.fromhex(value["bytes"]) if "bytes" in value else value["json"])


def replay(capture):
    if "fraktal_ab_projection" in sys.modules:
        raise RuntimeError("legacy projection replay requires a fresh process")
    declaration = capture["declaration"]
    if not declaration.startswith("fraktal_ab_") or not declaration.isidentifier():
        raise ValueError("invalid recorded declaration module")
    os.environ["FRAKTAL_AB_DECLARATION"] = declaration
    import fraktal_ab_projection as projection
    comm = Replay(capture["reads"])
    document = projection.read_document(comm)
    if comm.index != len(comm.reads):
        raise ValueError("projection left recorded reads unused")
    if json.loads(json.dumps(document["values"])) != capture["values"]:
        raise ValueError("projection values differ from immutable golden capture")
    if document["contentHash"] != capture["contentHash"]:
        raise ValueError("projection content hash differs from golden capture")
    return dict(schema="fraktal.ab.projection-replay", equal=True, reads=comm.index,
                paths=len(document["values"]), declaration=declaration,
                typeAcceptance=False, reason="original capture omitted transport types")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = replay(load_json(args.capture))
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
            stream.write("\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
