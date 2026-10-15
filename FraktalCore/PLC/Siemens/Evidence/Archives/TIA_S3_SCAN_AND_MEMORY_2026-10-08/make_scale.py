"""Build an S3 scale-fixture source folder: the S2 sources unchanged, plus N idle
cylinder CMs called every scan after the composition root. Repository sources
are only read. Usage: python make_scale.py <N> <out-dir> [named]"""
import pathlib, shutil, sys

NL = "\n"
TAB = "\t"
Q = '"'

n = int(sys.argv[1])
out = pathlib.Path(sys.argv[2])
named = len(sys.argv) > 3 and sys.argv[3] in ("named", "empty")
empty = len(sys.argv) > 3 and sys.argv[3] == "empty"
src = pathlib.Path(r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\Spikes\S2_Shape")
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
for f in src.iterdir():
    if f.suffix in (".udt", ".scl", ".db"):
        shutil.copy2(f, out / f.name)

cm = Q + ("FB_SpkEmptyCM" if empty else "FB_SpkCylinderCM") + Q
if empty:
    # the CM's exact interface and data, an empty body: call + parameter overhead only
    text = (src / "30_CylinderCM.scl").read_text(encoding="ascii")
    head = text[text.index('FUNCTION_BLOCK "FB_SpkCylinderCM"'):text.index("BEGIN", text.index('FUNCTION_BLOCK "FB_SpkCylinderCM"'))]
    head = head.replace('"FB_SpkCylinderCM"', '"FB_SpkEmptyCM"', 1)
    (out / "71_EmptyCM.scl").write_text(
        "// S3: FB_SpkCylinderCM's interface and data with an empty body." + NL + head + "BEGIN" + NL + TAB + ";" + NL + "END_FUNCTION_BLOCK" + NL,
        encoding="ascii")
hal = Q + "ST_SpkCylHal" + Q
if named:
    # the generated composition form: every child a named static, called by name
    decl = "".join("      Cyl%02d : %s;%s      Hal%02d : %s;%s" % (i, cm, NL, i, hal, NL) for i in range(1, n + 1))
    temp = ""
    body = "".join("%s#Cyl%02d(Hal := #Hal%02d);%s" % (TAB, i, i, NL) for i in range(1, n + 1))
else:
    decl = "      Cyl : Array[1..%d] of %s;%s      Hal : Array[1..%d] of %s;%s" % (n, cm, NL, n, hal, NL)
    temp = "   VAR_TEMP" + NL + "      i : Int;" + NL + "   END_VAR" + NL + NL
    body = (TAB + "FOR #i := 1 TO %d DO" + NL + TAB + "    #Cyl[#i](Hal := #Hal[#i]);" + NL + TAB + "END_FOR;" + NL) % n

lines = [
    "// S3 scale fixture (Part IV s.12): %d idle cylinder CMs called every scan (%s form)," % (n, "empty" if empty else "named" if named else "array"),
    "// as most modules of a press are idle. Measures work memory and cycle time per CM.",
    "FUNCTION_BLOCK " + Q + "FB_SpkScale" + Q,
    "{ S7_Optimized_Access := 'TRUE' }",
    "VERSION : 0.1",
    "   VAR",
]
text = NL.join(lines) + NL + decl + "   END_VAR" + NL + NL + temp + NL + "BEGIN" + NL + body + "END_FUNCTION_BLOCK" + NL
(out / "72_Scale.scl").write_text(text, encoding="ascii")

(out / "73_ScaleInstance.db").write_text(NL.join([
    "// S3 scale fixture instance (not a deployed root: no Status at its top level).",
    "DATA_BLOCK " + Q + "SpkScale" + Q,
    "{ S7_Optimized_Access := 'TRUE' }",
    "VERSION : 0.1",
    "NON_RETAIN",
    Q + "FB_SpkScale" + Q,
    "",
    "BEGIN",
    "",
    "END_DATA_BLOCK",
    "",
]), encoding="ascii")

ob1 = (out / "80_OB1.scl").read_text(encoding="ascii")
call = TAB + Q + "SpkMain" + Q + "();" + NL
assert ob1.count(call) == 1
(out / "80_OB1.scl").write_text(ob1.replace(call, call + TAB + Q + "SpkScale" + Q + "();" + NL), encoding="ascii")
print("scale fixture N=%d (%s) -> %s (%d files)" % (n, "empty" if empty else "named" if named else "array", out, len(list(out.iterdir()))))
