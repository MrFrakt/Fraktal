"""S9 retained read client across native STOP/RUN on the disconnected bench.

Requires --confirm-target 192.168.0.10, existing TLS pin and both WEB/DIAG
password environment variables. Each mode POST identifies/confirms the target
via S11's guarded helper. No tags are written and requests are not replayed.
"""
import argparse
import os
import pathlib
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "S11_Scl"))
from read_sessions import HOST, emit, read
from tia_webapi import WebApi, WebApiError
from web_mode import mode_change


def observed_read(api, path):
    try:
        value = api.call("PlcProgram.Read", {"var": path})
        emit("retained-client-read", path=path, renewed=False, value=value)
        return value
    except WebApiError as error:
        if error.code != 2:
            raise
        emit("retained-client-token-refused", code=error.code)
        api.token = None
        api.login("fraktal")
        value = api.call("PlcProgram.Read", {"var": path})
        emit("retained-client-read", path=path, renewed=True, value=value)
        return value


def main(target):
    if target != HOST:
        raise ValueError("exact bench target confirmation is required")
    pin_file = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal/TiaStations/192.168.0.10.webapi.pin"
    pin = pin_file.read_text(encoding="ascii").strip()
    api = WebApi(HOST, pin_file, False)
    try:
        api.login("fraktal")
        token = api.token
        before = read(api)
        emit("before-mode", value=before)
        mode_change("stop", target, pin)
        try:
            stopped_a = observed_read(api, '"S11Scl".Samples[1]')
            time.sleep(0.25)
            stopped_b = observed_read(api, '"S11Scl".Samples[1]')
            emit("stopped-counter", first=stopped_a, second=stopped_b, frozen=stopped_a == stopped_b)
            if stopped_a != stopped_b:
                raise ValueError("counter changed while SZL STOP was confirmed")
        finally:
            # Issue RUN once after confirmed STOP, including a failed read check.
            mode_change("run", target, pin)
        deadline = time.monotonic() + 30
        while observed_read(api, '"S11Scl".State') != 99:
            if time.monotonic() >= deadline:
                raise TimeoutError("fixture did not complete after RUN")
            time.sleep(0.1)
        after_a = observed_read(api, '"S11Scl".Samples[1]')
        after_b = observed_read(api, '"S11Scl".Samples[1]')
        if after_b <= after_a or after_a >= before:
            raise ValueError("cyclic counter did not restart and continue")
        emit("mode-session", result="PASS", same_token=api.token == token,
             before=before, after_first=after_a, after_second=after_b)
    finally:
        if api.token:
            try:
                api.call("Api.Logout")
            except (OSError, RuntimeError):
                pass
        api.conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--confirm-target", required=True)
    args = parser.parse_args()
    try:
        main(args.confirm_target)
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        emit("failed", type=type(error).__name__, message=str(error))
        raise SystemExit(1)
