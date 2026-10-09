"""Read the S7-1200 system web page 'Diagnostics -> Memory' after a form login.
Read-only. User/password from FRAKTAL_TIA_DIAG_USER / FRAKTAL_TIA_DIAG_PASSWORD.
Writes the page text (tags stripped) to argv[1] and prints the memory rows."""
import os, sys, pathlib, re, html, ssl, http.client, hashlib, urllib.parse

pin = (pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin").read_text().strip()
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
c = http.client.HTTPSConnection("192.168.0.10", 443, context=ctx, timeout=20); c.connect()
assert hashlib.sha256(c.sock.getpeercert(binary_form=True)).hexdigest() == pin, "certificate pin mismatch"

body = urllib.parse.urlencode({"Redirection": "", "Login": os.environ["FRAKTAL_TIA_DIAG_USER"],
                               "Password": os.environ["FRAKTAL_TIA_DIAG_PASSWORD"]})
# a prior GET (session cookie) and the page's own Referer/Origin, as a browser sends them
c.request("GET", "/Portal/Portal.mwsl?PriNav=Start"); r0 = c.getresponse(); r0.read()
pre = [v.split(";")[0] for k, v in r0.getheaders() if k.lower() == "set-cookie"]
login_headers = {"Content-Type": "application/x-www-form-urlencoded",
                 "Referer": "https://192.168.0.10/Portal/Portal.mwsl?PriNav=Start",
                 "Origin": "https://192.168.0.10"}
if pre:
    login_headers["Cookie"] = "; ".join(pre)
c.request("POST", "/FormLogin", body=body, headers=login_headers)
r = c.getresponse(); r.read()
cookies = [v.split(";")[0] for k, v in r.getheaders() if k.lower() == "set-cookie"]
print("login ->", r.status, "cookies:", [x.split("=")[0] for x in cookies])
headers = {"Cookie": "; ".join(cookies)}

target = sys.argv[2] if len(sys.argv) > 2 else "/Portal/Portal.mwsl?PriNav=Diagnostic"
c.request("GET", target, headers=headers)
r = c.getresponse(); page = r.read().decode("utf-8", "replace")
text = re.sub(r"[ \t]+", " ", html.unescape(re.sub(r"<[^>]+>", "\n", page)))
lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
pathlib.Path(sys.argv[1]).write_text("\n".join(lines), encoding="utf-8")
print("page", target, "->", r.status, len(page), "bytes; links:", sorted(set(re.findall(r'href="([^"]*mwsl[^"]*)"', page))))
for i, ln in enumerate(lines):
    if re.search(r"(?i)memory|byte|%", ln):
        print("  ", " | ".join(lines[i:i + 1]).encode("ascii", "replace").decode())
