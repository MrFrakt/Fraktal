"""Copy exported sources in the generated model's dependency order."""
import argparse
import hashlib
import json
import pathlib

from make_fixture import native_name


def prepare(manifest, exported, out):
    model = json.loads(manifest.read_text())
    sources = {path.name: path for path in exported.iterdir() if path.suffix in (".udt", ".db", ".scl")}
    ordered = []
    for index, name in enumerate(model["ordered_types"]):
        source = sources.pop(native_name(name) + ".udt")
        ordered.append((source, "00_%03d_%s" % (index, source.name)))
    for name in sorted(sources):
        source = sources[name]
        if source.suffix == ".udt":
            raise ValueError("exported type absent from model: " + name)
        prefix = "05_" if source.suffix == ".db" else "30_" if name == "Main.scl" else "10_"
        ordered.append((source, prefix + name))
    out.mkdir(exist_ok=False)
    result = {}
    for source, name in ordered:
        payload = source.read_bytes()
        (out / name).write_bytes(payload)
        result[name] = {"source": source.name, "sha256": hashlib.sha256(payload).hexdigest()}
    (out / "inventory.json").write_bytes((json.dumps(result, indent=2) + "\n").encode("ascii"))
    print(json.dumps({"ordered_sources": len(result)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=pathlib.Path)
    parser.add_argument("exported", type=pathlib.Path)
    parser.add_argument("out", type=pathlib.Path)
    args = parser.parse_args()
    prepare(args.manifest, args.exported, args.out)
