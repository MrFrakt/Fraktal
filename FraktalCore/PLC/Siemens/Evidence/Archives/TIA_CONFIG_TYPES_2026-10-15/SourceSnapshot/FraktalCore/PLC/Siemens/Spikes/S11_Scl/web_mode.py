"""S11 bench-only native HTTPS STOP/RUN and read-only startup snapshots.

Secrets: FRAKTAL_TIA_DIAG_PASSWORD (native page), FRAKTAL_TIA_WEB_PASSWORD
(Web API snapshots). Every TLS connection checks the existing certificate pin.
Mode changes identify the fixed bench immediately before the POST and are never
replayed. The diagnostics role's temporary mode right must be restored afterwards.
"""
import argparse
import hashlib
import http.client
import json
import os
import pathlib
import ssl
import subprocess
import sys
import time
import urllib.parse
from html.parser import HTMLParser

TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
from s7_bench_mode import HOST, confirm, emit, state
from s7_probe import S7Session
from tia_webapi import WebApi

PAGE = "/Portal/Portal.mwsl?PriNav=Start"


class PinnedHttps(http.client.HTTPSConnection):
    def __init__(self, pin):
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        super().__init__(HOST, timeout=15, context=context)
        self.pin = pin

    def connect(self):
        super().connect()
        actual = hashlib.sha256(self.sock.getpeercert(binary_form=True)).hexdigest()
        if actual != self.pin:
            self.close()
            raise ssl.SSLError("native web certificate pin mismatch")


class Forms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = {}
        self.active = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.active = attrs.get("id")
            self.forms[self.active] = {"method": attrs.get("method", "GET").upper(),
                                       "action": attrs.get("action"), "fields": {}}
        elif tag == "input" and self.active and attrs.get("name"):
            self.forms[self.active]["fields"][attrs["name"]] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = None


class NativePage:
    def __init__(self, pin):
        self.conn = PinnedHttps(pin)
        self.cookies = {}

    def request(self, method, path, fields=None):
        headers = {"Origin": "https://" + HOST, "Referer": "https://" + HOST + PAGE}
        if self.cookies:
            headers["Cookie"] = "; ".join(key + "=" + value for key, value in self.cookies.items())
        body = None
        if fields is not None:
            body = urllib.parse.urlencode(fields)
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        # No retry: a failed control request has an unknown outcome.
        self.conn.request(method, path, body=body, headers=headers)
        response = self.conn.getresponse()
        data = response.read().decode("utf-8", "replace")
        for key, value in response.getheaders():
            if key.lower() == "set-cookie":
                name, item = value.split(";", 1)[0].split("=", 1)
                self.cookies[name] = item
        return response.status, data

    def login(self):
        self.request("GET", PAGE)
        code, _ = self.request("POST", "/FormLogin", {"Redirection": "", "Login": "fraktal-diag",
                                                        "Password": os.environ["FRAKTAL_TIA_DIAG_PASSWORD"]})
        if code != 302 or not self.cookies.get("siemens_ad_session"):
            raise ValueError("native form login refused")
        emit("native-login", user="fraktal-diag", authenticated=True)

    def close(self):
        try:
            if self.cookies.get("siemens_ad_session"):
                try:
                    # Best effort only: the 1214C accepts the old cookie after
                    # either measured GET logout form. Do not claim revocation.
                    self.request("GET", "/FormLogin?LOGOUT")
                except (OSError, http.client.HTTPException):
                    pass
        finally:
            self.cookies.clear()
            self.conn.close()


def mode_change(mode, target, pin):
    if target != HOST:
        raise ValueError("--confirm-target " + HOST + " is required")
    page = NativePage(pin)
    try:
        page.login()
        code, text = page.request("GET", PAGE)
        if code != 200:
            raise ValueError("native Start page unavailable")
        forms = Forms()
        forms.feed(text)
        form = forms.forms.get("goTo%sForm" % mode.title())
        if not form or form["method"] != "POST" or form["action"] != "/CPUCommands":
            raise ValueError("authenticated mode form absent or unrecognized")
        if form["fields"].get(mode.title()) != "1":
            raise ValueError("native mode form has an unexpected command")
        subprocess.run([sys.executable, str(TOOLS / "s7_probe.py"), "ident", "--host", HOST], check=True)
        session = S7Session(HOST)
        try:
            confirm(session, target)
            before = state(session)
            if before not in ("run", "stop"):
                raise ValueError("CPU is starting; wait for a stable operating mode")
            if before == mode:
                raise ValueError("CPU already in requested mode; no transition measured")
            emit("native-mode-before", mode=before)
            code, _ = page.request("POST", form["action"], form["fields"])
            emit("native-mode-post", requested=mode, status=code)
            if code not in (200, 302, 303):
                raise ValueError("native mode request refused")
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                after = state(session)
                if after == mode:
                    emit("native-mode-after", mode=after)
                    return
                time.sleep(0.05)
            raise TimeoutError("native mode change not confirmed by SZL")
        finally:
            session.close()
    finally:
        page.close()


def snapshot(pin_file):
    fields = ["State", "StartupSeen", "StartupSafe", "InitialCallSeen", "StartupRc", "ValueRead", "LocalCode", "AfterError", "Samples[0]", "Samples[1]"]
    fields += ["StartupAt." + member for member in ("YEAR", "MONTH", "DAY", "HOUR", "MINUTE", "SECOND", "NANOSECOND")]
    paths = ['"S11Scl".' + field for field in fields]
    paths += ['"FRK_Clock".Scans', '"FRK_Clock".NowMs', '"SpikeUnit".Status.State',
              '"SpikeUnit".HmiRequest.Sequence', '"SpikeUnit".HmiResponse.AckSequence']
    api = WebApi(HOST, pin_file, False)
    try:
        api.login("fraktal")
        values = {}
        for path, (value, error) in zip(paths, api.bulk([("PlcProgram.Read", {"var": path}) for path in paths])):
            if error:
                raise ValueError("snapshot leaf refused: %s: %s" % (path, error))
            values[path] = value
        session = S7Session(HOST)
        try:
            emit("snapshot", host=HOST, mode=state(session), values=values)
        finally:
            session.close()
    finally:
        if api.token:
            try:
                api.call("Api.Logout")
            except (OSError, RuntimeError):
                pass
        api.conn.close()


def inspect_role(pin, diagnostics_only):
    page = NativePage(pin)
    try:
        page.login()
        code, text = page.request("GET", PAGE)
        if code != 200:
            raise ValueError("authenticated native Start page unavailable")
        forms = Forms()
        forms.feed(text)
        controls = [name for name in ("goToStopForm", "goToRunForm") if name in forms.forms]
        emit("native-role-inspection", authenticated=True, mode_controls=controls)
        if diagnostics_only and controls:
            raise ValueError("native mode controls still offered to diagnostics user")
    finally:
        page.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("action", choices=("stop", "run", "snapshot", "inspect"))
    parser.add_argument("--confirm-target")
    parser.add_argument("--diagnostics-only", action="store_true")
    args = parser.parse_args()
    if args.diagnostics_only and args.action != "inspect":
        parser.error("--diagnostics-only is valid only with inspect")
    pin_file = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal/TiaStations/192.168.0.10.webapi.pin"
    if args.action == "snapshot":
        snapshot(pin_file)
    elif args.action == "inspect":
        inspect_role(pin_file.read_text(encoding="ascii").strip(), args.diagnostics_only)
    else:
        mode_change(args.action, args.confirm_target, pin_file.read_text(encoding="ascii").strip())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        emit("failed", message=str(error))
        raise SystemExit(1)
