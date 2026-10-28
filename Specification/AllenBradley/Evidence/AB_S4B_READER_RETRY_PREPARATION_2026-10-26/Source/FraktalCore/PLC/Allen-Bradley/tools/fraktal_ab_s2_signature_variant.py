#!/usr/bin/env python3
"""Add one atomic Input to the exported disposable S2 leaf AOI.

This narrowly generates the optional/required signature-change inputs for the
S2 import-collision experiment. It accepts only the partial L5X export of
``FRK_S2_Level01`` revision 1.0 and refuses overwrite.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from fraktal_ab_phase0_fixture import replace_once, sha256


PARAMETER = """<Parameter Name="AddedInput" TagType="Base" DataType="DINT" Usage="Input" Radix="Decimal" Required="{required}" Visible="true" ExternalAccess="Read Only">
<DefaultData Format="L5K"><![CDATA[0]]></DefaultData>
<DefaultData Format="Decorated"><DataValue DataType="DINT" Radix="Decimal" Value="0"/></DefaultData>
</Parameter>"""


def generate(source: Path, output: Path, required: bool) -> dict[str, object]:
    source = source.resolve()
    output = output.resolve()
    if not source.is_file():
        raise ValueError(f"source does not exist: {source}")
    if source.suffix.lower() != ".l5x" or output.suffix.lower() != ".l5x":
        raise ValueError("source and output must use the .L5X extension")
    if source == output:
        raise ValueError("output must differ from source")
    if output.exists():
        raise ValueError(f"refusing to overwrite output: {output}")

    text = source.read_text(encoding="utf-8-sig")
    required_markers = (
        'TargetName="FRK_S2_Level01"',
        'TargetType="AddOnInstructionDefinition"',
        'Name="FRK_S2_Level01" Revision="1.0"',
        '<Parameter Name="ScalarOut"',
        'ScalarOut := Ctx.Result + Text.LEN;',
    )
    missing = [marker for marker in required_markers if marker not in text]
    if missing:
        raise ValueError(f"source is not the expected S2 leaf AOI export: {missing}")
    if "AddedInput" in text:
        raise ValueError("source already contains AddedInput")

    revision = "2.0" if required else "1.1"
    text = replace_once(text, 'TargetRevision="1.0 "', f'TargetRevision="{revision} "')
    text, revision_count = re.subn(
        r'(<AddOnInstructionDefinition\b[^>]*\bName="FRK_S2_Level01"\s+)Revision="1\.0"',
        rf'\1Revision="{revision}"',
        text,
        count=1,
    )
    if revision_count != 1:
        raise ValueError("leaf AOI revision was not changed exactly once")
    text = replace_once(
        text,
        "</Parameters>",
        PARAMETER.format(required=str(required).lower()) + "\n</Parameters>",
    )
    text = replace_once(
        text,
        "</STContent>",
        '<Line Number="4"><![CDATA[Ctx.Result := Ctx.Result + AddedInput;]]></Line>\n</STContent>',
    )
    output.write_text(text, encoding="utf-8", newline="\n")
    return {
        "Schema": "fraktal.ab.s2-signature-variant",
        "SchemaVersion": 1,
        "Source": str(source),
        "SourceSha256": sha256(source),
        "Output": str(output),
        "OutputSha256": sha256(output),
        "Aoi": "FRK_S2_Level01",
        "Revision": revision,
        "AddedParameter": "AddedInput",
        "Required": required,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--optional", action="store_true")
    group.add_argument("--required", action="store_true")
    args = parser.parse_args()
    try:
        evidence = generate(args.source, args.output, args.required)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
