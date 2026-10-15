"""Generate S11 recovery charts/inputs; preserve the existing station identity."""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SPIKES = HERE.parents[1]
TOOLS = SPIKES.parent / "tools"
sys.path.insert(0, str(TOOLS))
sys.path.insert(0, str(HERE.parent / "Semantics"))
import fraktal_tia_graph as graph
from make_charts import main as semantics_charts


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise ValueError("source anchor drift: " + old)
    return text.replace(old, new, 1)


def generate(out):
    out.mkdir(parents=True, exist_ok=False)
    for name in ("base", "late", "recovery", "charts", "chart_delta", "code_delta", "output_delta"):
        (out / name).mkdir()
    sources = {}
    for path in (SPIKES / "S2_Shape").iterdir():
        if path.suffix not in (".scl", ".udt", ".db"):
            continue
        payload = path.read_bytes()
        sources[str(path.relative_to(SPIKES))] = hashlib.sha256(payload).hexdigest()
        if path.name == "60_Harness.scl":
            text = payload.decode("ascii")
            text = replace_once(text, '"FRK_Registry".Count = 3', '"FRK_Registry".Count = 6')
            text = replace_once(text, 'Expected := 3, Actual := "FRK_Registry".Count', 'Expected := 6, Actual := "FRK_Registry".Count')
            payload = text.encode("ascii")
        (out / "base" / path.name).write_bytes(payload)
    main_path = out / "base/70_Main.scl"
    text = replace_once(main_path.read_text(encoding="ascii"), '\t"SpikeUnit"(Hal := "SpkHal".Unit);',
                        '\t"SpikeUnit"(Hal := "SpkHal".Unit);\n\t"S11Recovery"(InitialCall := "FRK_Clock".FirstScan);')
    (out / "late/70_Main.scl").write_bytes(text.encode("ascii"))
    for path in HERE.iterdir():
        if path.suffix in (".scl", ".udt", ".db"):
            sources[str(path.relative_to(SPIKES))] = hashlib.sha256(path.read_bytes()).hexdigest()
            (out / "recovery" / path.name).write_bytes(path.read_bytes())
    template = (HERE.parent / "reference/FB_GraphSample.xml").read_text(encoding="utf-8-sig")
    auto = json.loads((HERE.parent / "chain_auto.json").read_text(encoding="utf-8"))
    (out / "charts/FB_SpkAutoGraph.xml").write_bytes(graph.generate(auto, template).encode("ascii"))
    semantics_charts(out / "charts")
    chain = {
        "name": "FB_S11RecoveryGraph", "number": 35,
        "inout": [*auto["inout"], ["Control", "ST_S11RecoveryControl"]],
        "steps": [
            {"no": 0, "label": "spike.step.start", "when": ["#Control.Go"], "next": 100},
            {"no": 100, "label": "spike.step.extendA", "issue": [["CylA", 1]],
             "await": [{"idx": 1, "label": "CylA.EXTEND"}], "when": ["#CylA.Done"], "next": 999},
            {"no": 999, "label": "spike.step.retractBoth", "when": ["FALSE"], "next": 999},
        ],
    }
    for variant in ("charts", "chart_delta"):
        if variant == "chart_delta":
            chain["steps"][1]["label"] = "spike.step.extendB"
        xml = graph.generate(chain, template)
        (out / variant / "FB_S11RecoveryGraph.xml").write_bytes(xml.encode("ascii"))
        (out / variant / "declaration.json").write_bytes((json.dumps(chain, indent=2) + "\n").encode("ascii"))
        (out / variant / "dump.json").write_bytes((json.dumps(graph.dump(xml), indent=2) + "\n").encode("ascii"))
    marker = (HERE / "10_Marker.scl").read_text(encoding="ascii")
    (out / "code_delta/10_Marker.scl").write_bytes(replace_once(marker, '#Marker := 2101;', '#Marker := 2102;').encode("ascii"))
    (out / "output_delta/30_CylinderCM.scl").write_bytes((out / "base/30_CylinderCM.scl").read_bytes())
    (out / "output_delta/20_Rig.scl").write_bytes((out / "recovery/20_Rig.scl").read_bytes())
    (out / "manifest.json").write_bytes((json.dumps({"sources": sources, "target": "FrkS11 / PLCSIM 1516 V3.0",
        "registry_rows": 6, "variants": ["charts", "code_delta", "chart_delta"]}, indent=2) + "\n").encode("ascii"))
    print(json.dumps({"generated": str(out), "target": "S7-1500 simulation", "registry_rows": 6}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=pathlib.Path)
    generate(parser.parse_args().out)
