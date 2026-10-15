"""Read S12 witnesses and clock samples through pinned, licence-free Web API."""
import argparse
import datetime
import json
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "tools"))
from tia_webapi import WebApi, WebApiError, leaf_var

SCALARS = {"BoolTrue": True, "BoolFalse": False, "IntMin": -32768, "IntMax": 32767,
           "DIntMin": -2147483648, "DIntMax": 2147483647, "UIntMax": 65535,
           "UDIntMax": 4294967295, "RealValue": 1.25, "LRealValue": 1.23456789012345,
           "TimeValue": 1234, "NegativeTime": -2345, "LongMin": -9223372036854775808,
           "LongMax": 9223372036854775807, "UnsignedMax": 18446744073709551615,
           "BeyondJsonExact": 9007199254740993, "Text254": "a" * 253 + "Z",
           "Text255": "b" * 254 + "Y", "Text480": "c" * 479 + "X",
           "EscapedText": "A'B\"C", "UnicodeText": "\u03a9\u4e2d",
           "Text254Length": 254, "Text255Length": 255, "Text480Length": 480,
           "WideConcat": "b" * 254 + "Y!", "WideTail": "ccX"}


def emit(stream, event, **values):
    stream.write(json.dumps({"t": datetime.datetime.now(datetime.timezone.utc).isoformat(), "event": event, **values}, ensure_ascii=True) + "\n")
    stream.flush()


def variable(path):
    return leaf_var(path.split("."))


def read_batch(api, names):
    return api.bulk([("PlcProgram.Read", {"var": variable(name)}) for name in names])


def auth_diagnostics(api, stream):
    try:
        rejected_login = api.call("Api.Login", {"user": "fraktal", "password": "S12-deliberately-invalid"})
    except WebApiError as error:
        emit(stream, "negative-login", rejected=True, code=error.code)
    else:
        api.token = rejected_login["token"]
        emit(stream, "negative-login", rejected=False, token_length=len(api.token))
        api.call("Api.Logout")
        api.token = None
    login = api.call("Api.Login", {"user": "fraktal", "password": os.environ["FRAKTAL_TIA_WEB_PASSWORD"],
                                   "include_web_application_cookie": True})
    api.token = login["token"]
    cookie = login.get("web_application_cookie")
    emit(stream, "login-shape", fields=sorted(login), cookie_present=bool(cookie),
         token_length=len(api.token), permissions=api.call("Api.GetPermissions"))
    for variant in ("token", "token-cookie", "cookie-only", "lowercase-token", "origin-token", "new-connection", "explicit-simple", "explicit-raw"):
        headers = {"Content-Type": "application/json"}
        if variant != "cookie-only":
            headers["x-auth-token" if variant == "lowercase-token" else "X-Auth-Token"] = api.token
        if variant in {"token-cookie", "cookie-only"}:
            if not cookie:
                emit(stream, "auth-variant-skipped", variant=variant, reason="no cookie returned")
                continue
            headers["Cookie"] = "siemens_web_secure=" + cookie
        if variant == "origin-token":
            headers["Origin"] = "https://" + api.host
        if variant == "new-connection":
            api.conn.close()
        if api.conn.sock is None:
            api._connect()
        payload = {"jsonrpc": "2.0", "id": 999, "method": "PlcProgram.Read",
                   "params": {"var": '\"S12Probe\".Ready'}}
        if variant.startswith("explicit-"):
            payload["params"]["mode"] = variant.split("-", 1)[1]
        api.conn.request("POST", "/api/jsonrpc", body=json.dumps(payload).encode("ascii"), headers=headers)
        response = api.conn.getresponse()
        reply = json.loads(response.read().decode("utf-8"))
        emit(stream, "auth-variant", variant=variant, status=response.status,
             value=reply.get("result"), error=reply.get("error"))


def token_controls(api, stream):
    """Compare authorization without ever recording an authentication token."""
    authenticated = api.token
    try:
        for variant, token in (("absent", None), ("invalid", "S12-invalid-token"),
                               ("authenticated", authenticated)):
            api.token = token
            for method, params in (("Api.GetPermissions", None),
                                   ("Plc.ReadOperatingMode", None),
                                   ("PlcProgram.Read", {"var": '"S12Probe".Ready'})):
                try:
                    value = api.call(method, params)
                    emit(stream, "token-control", variant=variant, method=method, value=value)
                except WebApiError as error:
                    emit(stream, "token-control", variant=variant, method=method, code=error.code)
    finally:
        api.token = authenticated


def witnesses(api, manifest, stream):
    for attempt in range(120):
        if api.call("PlcProgram.Read", {"var": '"S12Probe".Ready'}) is True:
            break
        time.sleep(0.25)
    else:
        raise ValueError("S12 fill not complete")
    emit(stream, "browse", name="S12Probe", children=api.call("PlcProgram.Browse", {"var": '"S12Probe"', "mode": "children"}))
    expected = {"S12Probe." + name: value for name, value in SCALARS.items()}
    expected.update({"S12Probe.LowerArray[%d]" % n: n * 100 + 7 for n in range(-2, 3)})
    expected.update(manifest.get("web_witnesses", manifest["witnesses"]))
    names = list(expected)
    failures = []
    for offset in range(0, len(names), 32):
        batch = names[offset:offset+32]
        for name, (value, error) in zip(batch, read_batch(api, batch)):
            wanted = expected[name]
            # Siemens uses decimal strings for native 64-bit integer wire values.
            decimal64 = (name.rsplit(".", 1)[-1] in {"LongMin", "LongMax", "UnsignedMax", "BeyondJsonExact"}
                         or manifest.get("witness_encodings", {}).get(name) == "ldt")
            normalized = int(value) if decimal64 and isinstance(value, str) else value
            passed = error is None and type(normalized) is type(wanted) and normalized == wanted
            emit(stream, "witness", name=name, value=value, expected=wanted, error=error, passed=passed)
            if not passed:
                failures.append(name)
    for name in ("StampDtl", "StampLdt", "StampDt"):
        for mode in ("simple", "raw"):
            try:
                value = api.call("PlcProgram.Read", {"var": '"S12Probe".' + name, "mode": mode})
                emit(stream, "timestamp", name=name, mode=mode, value=value)
            except Exception as error:
                emit(stream, "timestamp-failed", name=name, mode=mode, message=str(error))
        try:
            emit(stream, "timestamp-browse", name=name, children=api.call("PlcProgram.Browse", {"var": '"S12Probe".' + name, "mode": "children"}))
        except Exception as error:
            emit(stream, "timestamp-browse-failed", name=name, message=str(error))
    emit(stream, "summary", witnesses=len(names), passed=len(names)-len(failures), failed=failures)
    return not failures


def clock(api, stream, minutes, period):
    started = time.monotonic()
    end = started + minutes * 60
    names = ["S12Probe." + field for field in ("Ready", "Scans", "MonoSec", "BadDelta", "MaxDeltaSec")]
    initial = None
    samples = []
    while True:
        before = time.monotonic()
        replies = read_batch(api, names)
        after = time.monotonic()
        if any(error is not None for _, error in replies):
            raise ValueError("clock read failed; no retry of a reset or download")
        values = {name.rsplit(".", 1)[-1]: reply[0] for name, reply in zip(names, replies)}
        row = {"before": before, "after": after, "values": values}
        if initial is None:
            initial = row
        elapsed = (before + after - initial["before"] - initial["after"]) / 2
        mono_elapsed = values["MonoSec"] - initial["values"]["MonoSec"]
        emit(stream, "clock", host_elapsed=elapsed, plc_elapsed=mono_elapsed,
             error_seconds=mono_elapsed-elapsed, request_span=after-before, **values)
        samples.append(row)
        if after >= end:
            break
        time.sleep(min(period, max(0.01, end-after)))
    if elapsed < minutes * 60 - 1 or any(row["values"]["Ready"] is not True or row["values"]["BadDelta"] != 0 for row in samples):
        raise ValueError("clock interval incomplete or PLC delta rejected")
    if values["Scans"] <= initial["values"]["Scans"]:
        raise ValueError("scan counter did not advance")
    tolerance = max(1.0, elapsed * 0.001)
    passed = abs(mono_elapsed-elapsed) <= tolerance
    emit(stream, "clock-summary", minutes=minutes, host_elapsed=elapsed, plc_elapsed=mono_elapsed,
         tolerance_seconds=tolerance, passed=passed)
    return passed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("witnesses", "clock", "permissions", "diagnostics", "auth-diagnostics", "token-controls", "capabilities"))
    parser.add_argument("out", type=pathlib.Path)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--trust-first", action="store_true")
    parser.add_argument("--minutes", type=float, default=60)
    parser.add_argument("--period", type=float, default=30)
    parser.add_argument("--certificate", type=pathlib.Path)
    args = parser.parse_args()
    with args.out.open("x", encoding="ascii", newline="\n") as stream:
        pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal/TiaStations/FrkS12.webapi.pin"
        api = WebApi("169.254.212.49", pin, args.trust_first, timeout=30)
        try:
            if args.certificate:
                with args.certificate.open("xb") as certificate:
                    certificate.write(api.conn.sock.getpeercert(binary_form=True))
            emit(stream, "connection", address=api.host, certificate_sha256=api.fingerprint, version=api.call("Api.Version"))
            if args.action == "auth-diagnostics":
                auth_diagnostics(api, stream)
                passed = True
            else:
                api.login("fraktal")
            if args.action == "diagnostics":
                for method in ("Plc.ReadOperatingMode", "Plc.ReadSystemTime"):
                    try:
                        emit(stream, "platform-read", method=method, value=api.call(method))
                    except WebApiError as error:
                        emit(stream, "platform-read-failed", method=method, code=error.code)
                calls = [("PlcProgram.Browse", {"mode": "children"}),
                         ("PlcProgram.Browse", {"var": '"S12Probe"', "mode": "children"})]
                calls += [("PlcProgram.Read", {"var": name}) for name in ('"S12Probe".Ready', '"S12Probe"."Ready"', 'S12Probe.Ready', '"S12Probe".Stage', '"S12Probe".Text254')]
                for (method, params), (value, error) in zip(calls, api.bulk(calls)):
                    emit(stream, "diagnostic", method=method, params=params, value=value, error=error)
                passed = True
            elif args.action == "permissions":
                emit(stream, "permissions", value=api.call("Api.GetPermissions"), token_length=len(api.token or ""))
                passed = True
            elif args.action == "token-controls":
                token_controls(api, stream)
                passed = True
            elif args.action == "witnesses":
                passed = witnesses(api, json.loads(args.manifest.read_text()), stream)
            elif args.action == "capabilities":
                methods = api.call("Api.Browse")
                emit(stream, "methods", names=sorted(method["name"] if isinstance(method, dict) else str(method) for method in methods))
                try:
                    emit(stream, "limits", value=api.call("Api.GetQuantityStructures"))
                except WebApiError as error:
                    emit(stream, "limits-unavailable", code=error.code)
                passed = True
            elif args.action == "clock":
                passed = clock(api, stream, args.minutes, args.period)
        finally:
            if api.token:
                api.call("Api.Logout")
            api.conn.close()
        raise SystemExit(0 if passed else 1)
