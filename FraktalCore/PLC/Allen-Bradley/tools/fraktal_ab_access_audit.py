#!/usr/bin/env python3
"""Audit a project's controller-side External Access allow-list (AB §11.2.1).

AB §11.2.1 requires that the controller-side allow-list be *generated and
audited*: manifest and public data read-only, root mailboxes read/write, and
**everything else None**. Generating it is the future generator's job; auditing
it is this tool's, and the audit has to exist first — otherwise "audited" means
"someone looked".

The rule is applied fail-closed. A tag is judged against exactly one class:

* **mailbox** - declared with `--mailbox`; shall be `Read/Write`;
* **public** - declared with `--public`; shall be `Read Only`;
* **everything else** - shall be `None`.

Nothing is inferred from a name pattern. A tag the caller did not classify is
not given the benefit of the doubt: it must be `None`, because an unclassified
readable tag is exactly the surface the allow-list exists to remove. That makes
an incomplete invocation fail loudly rather than silently approve a project.

The audit reads only the offline L5X. It never contacts a controller.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path


SCHEMA = "fraktal.ab.access-audit"
SCHEMA_VERSION = 1

MAILBOX_ACCESS = "Read/Write"
PUBLIC_ACCESS = "Read Only"
PRIVATE_ACCESS = "None"


class AuditError(ValueError):
    """The document cannot be audited, so no verdict is claimed."""


def controller_tags(path: Path) -> dict[str, str | None]:
    try:
        root = ElementTree.parse(path).getroot()
    except (OSError, ElementTree.ParseError) as exc:
        raise AuditError(f"cannot parse {path}: {exc}") from exc
    controller = root.find("Controller")
    if controller is None:
        raise AuditError(f"{path} is not a full-project L5X document")
    container = controller.find("Tags")
    if container is None:
        return {}
    return {
        tag.get("Name"): tag.get("ExternalAccess")
        for tag in container.findall("Tag")
    }


def audit(
    tags: dict[str, str | None],
    mailbox: set[str],
    public: set[str],
) -> dict[str, object]:
    findings: list[str] = []
    verdicts: list[dict[str, object]] = []

    for name in sorted(tags):
        access = tags[name]
        if name in mailbox and name in public:
            findings.append(f"{name}: declared both mailbox and public")
            expected = None
        elif name in mailbox:
            expected = MAILBOX_ACCESS
        elif name in public:
            expected = PUBLIC_ACCESS
        else:
            expected = PRIVATE_ACCESS

        conforms = expected is not None and access == expected
        verdicts.append(
            {
                "tag": name,
                "class": (
                    "mailbox" if name in mailbox
                    else "public" if name in public
                    else "unclassified"
                ),
                "externalAccess": access,
                "expected": expected,
                "conforms": conforms,
            }
        )
        if expected is not None and not conforms:
            # an omitted attribute is not "None": Studio writes its default on
            # export, so an absent value is an unproven write surface
            findings.append(
                f"{name}: External Access {access!r}, allow-list requires "
                f"{expected!r}"
            )

    for declared, label in ((mailbox, "mailbox"), (public, "public")):
        for name in sorted(declared - set(tags)):
            findings.append(f"{name}: declared {label} but not present in the project")

    return {
        "Schema": SCHEMA,
        "SchemaVersion": SCHEMA_VERSION,
        "TagsAudited": len(tags),
        "Mailbox": sorted(mailbox),
        "Public": sorted(public),
        "WriteSurface": sorted(
            item["tag"] for item in verdicts
            if item["externalAccess"] == MAILBOX_ACCESS
        ),
        "Verdicts": verdicts,
        "Findings": findings,
        "Conforms": not findings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path, help="full-project L5X")
    parser.add_argument(
        "--mailbox", action="append", default=[],
        help="tag that shall be Read/Write; repeatable",
    )
    parser.add_argument(
        "--public", action="append", default=[],
        help="tag that shall be Read Only; repeatable",
    )
    args = parser.parse_args(argv)
    try:
        report = audit(
            controller_tags(args.project), set(args.mailbox), set(args.public)
        )
    except (OSError, AuditError) as exc:
        print(f"ERROR [ab-access-audit] {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["Conforms"] else 1


if __name__ == "__main__":
    sys.exit(main())
