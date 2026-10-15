"""Generate the four S11 supervision/skip probes with the shared GRAPH writer."""
import copy
import json
import pathlib
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[3] / "tools"
sys.path.insert(0, str(TOOLS))
import fraktal_tia_graph as graph


def main(out, exported=None):
    out.mkdir(parents=True, exist_ok=True)
    reference = pathlib.Path(__file__).resolve().parents[1] / "reference" / "FB_GraphSample.xml"
    template = reference.read_text(encoding="utf-8-sig")
    base = {
        "inout": [["Seq", "FRK_SeqCtx"], ["Probe", "ST_S11GraphProbe"]],
        "steps": [
            {"no": 0, "label": "spike.step.start", "when": ["#Probe.Go"], "next": 100},
            {"no": 100, "label": "spike.step.extendA", "when": ["TRUE"], "next": 200},
            {"no": 200, "label": "spike.step.extendB", "when": ["TRUE"], "next": 300},
            {"no": 300, "label": "spike.step.retractBoth", "when": ["FALSE"], "next": 300},
        ],
    }
    for step in base["steps"]:
        step.update(maximum_step_time="T#100MS", warning_time="T#50MS")
    for number, name in enumerate(("Empty", "Ack", "Auto", "Skip"), start=31):
        chain = copy.deepcopy(base)
        chain.update(name="FB_S11" + name, number=number)
        chain["graph_settings"] = {"acknowledge_errors_required": name in ("Empty", "Ack"), "skip_steps": name == "Skip"}
        if name != "Empty":
            chain["steps"][0]["supervision"] = ["#Probe.Fault"]
        xml = graph.generate(chain, template)
        (out / (chain["name"] + ".xml")).write_bytes(xml.encode("ascii"))
        (out / (chain["name"] + ".json")).write_bytes((json.dumps(graph.dump(xml), indent=2) + "\n").encode("ascii"))
        if exported:
            actual = graph.dump((exported / (chain["name"] + ".xml")).read_text(encoding="utf-8-sig"))
            if actual != graph.dump(xml):
                raise ValueError("TIA read-back differs: " + chain["name"])
        print(chain["name"])


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else None)
