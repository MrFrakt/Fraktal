"""S3 measurement of the running image, read-only: memory from the system web
page (fraktal-diag), cycle time from the PLC's own FRK_Clock over the Web API
(fraktal). Prints one JSON line. Passwords from FRAKTAL_TIA_DIAG_PASSWORD and
FRAKTAL_TIA_WEB_PASSWORD."""
import sys, os, json, pathlib, re, html, ssl, http.client, hashlib, urllib.parse, time, statistics
sys.path.insert(0, r"C:\Projects\Fraktal\FraktalCore\PLC\Siemens\tools")
import tia_webapi as w

label = sys.argv[1]
pin_file = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal" / "TiaStations" / "192.168.0.10.webapi.pin"
pin = pin_file.read_text().strip()

# --- memory: system web page Diagnostics > Memory -----------------------------
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
c = http.client.HTTPSConnection("192.168.0.10", 443, context=ctx, timeout=30); c.connect()
assert hashlib.sha256(c.sock.getpeercert(binary_form=True)).hexdigest() == pin, "certificate pin mismatch"
c.request("GET", "/Portal/Portal.mwsl?PriNav=Start"); r0 = c.getresponse(); r0.read()
pre = [v.split(";")[0] for k, v in r0.getheaders() if k.lower() == "set-cookie"]
hdr = {"Content-Type": "application/x-www-form-urlencoded", "Origin": "https://192.168.0.10",
       "Referer": "https://192.168.0.10/Portal/Portal.mwsl?PriNav=Start"}
if pre:
    hdr["Cookie"] = "; ".join(pre)
c.request("POST", "/FormLogin", headers=hdr, body=urllib.parse.urlencode(
    {"Redirection": "", "Login": "fraktal-diag", "Password": os.environ["FRAKTAL_TIA_DIAG_PASSWORD"]}))
r = c.getresponse(); r.read()
cookies = [v.split(";")[0] for k, v in r.getheaders() if k.lower() == "set-cookie"]
c.request("GET", "/Portal/Portal.mwsl?PriNav=Online&SecNav=Memory", headers={"Cookie": "; ".join(cookies)})
page = c.getresponse().read().decode("utf-8", "replace")
text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", page)))
# close the legacy-page session: the CPU caps active sessions and these do not
# end with the TCP connection (measured: unclosed logins locked the form login out)
logout = re.findall(r'(?:href|action)="([^"]*(?:LOGOUT|Logout|logout)[^"]*)"', page)
pathlib.Path(os.environ["TEMP"], "s3_memory_page.html").write_text(page, encoding="utf-8")
if logout:
    try:
        c.request("GET", html.unescape(logout[0]), headers={"Cookie": "; ".join(cookies)}); c.getresponse().read()
    except (http.client.RemoteDisconnected, ConnectionError):
        pass  # the CPU closes the connection after /FormLogin?LOGOUT (measured)
login_status = r.status


def area(name):
    m = re.search(name + r" ([\d.]+)% in use Free: ([\d.]+) (KB|MB) / Total: ([\d.]+) (KB|MB)", text)
    if not m:
        return None
    unit = 1024.0 if m.group(3) == "MB" else 1.0
    free_kb = float(m.group(2)) * unit
    total_kb = float(m.group(4)) * (1024.0 if m.group(5) == "MB" else 1.0)
    return {"percent": float(m.group(1)), "used_kb": round(total_kb - free_kb, 2), "total_kb": total_kb}


memory = {"load": area("Load memory"), "work": area("Work Memory"), "retentive": area("Retentive memory")}

# --- cycle time: FRK_Clock.CycleMs + Scans over the Web API ---------------------
api = w.WebApi("192.168.0.10", pin_file, False)
api.login("fraktal")
reads = [("PlcProgram.Read", {"var": '"FRK_Clock"."CycleMs"'}), ("PlcProgram.Read", {"var": '"FRK_Clock"."Scans"'})]
samples, first, last = [], None, None
t_end = time.time() + 10
while time.time() < t_end:
    (cyc, _), (scans, _) = api.bulk(reads)
    samples.append(float(cyc))
    now = (time.perf_counter(), int(scans))
    first = first or now
    last = now
rate = (last[1] - first[1]) / (last[0] - first[0])
print(json.dumps({"image": label, "web_logout": logout[:1], "memory": memory,
                  "cycle": {"mean_ms": round(1000.0 / rate, 3), "scans_per_s": round(rate, 1),
                            "sample_median_ms": round(statistics.median(samples), 3),
                            "sample_max_ms": round(max(samples), 3), "samples": len(samples)}}))
