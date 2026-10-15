"""Observe natural token invalidation after 160 seconds without API activity.

Read/authentication only. Do not change CPU mode, program or UMAC during this
probe; such a change would confound idle expiry. Credentials/pin come from the
same environment/file as read_sessions.py. Secrets are never printed.
"""
import os
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from read_sessions import HOST, emit, read
from tia_webapi import WebApi, WebApiError


def main():
    pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal/TiaStations/192.168.0.10.webapi.pin"
    api = WebApi(HOST, pin, False)
    try:
        api.login("fraktal")
        emit("before-idle", value=read(api))
        api.conn.close()
        started = time.monotonic()
        while time.monotonic() - started < 160:
            time.sleep(min(20, 160 - (time.monotonic() - started)))
            emit("idle-progress", elapsed_s=round(time.monotonic() - started, 3))
        try:
            value = read(api)
        except WebApiError as error:
            emit("after-idle-error", elapsed_s=round(time.monotonic() - started, 3),
                 code=error.code, message=str(error))
            if error.code != 2:
                raise ValueError("unexpected post-idle error") from error
            api.token = None
            api.login("fraktal")
            emit("idle-expiry-relogin", result="PASS", value=read(api))
        else:
            emit("after-idle", value=value, result="TOKEN_RETAINED", expiry="NOT_OBSERVED")
    finally:
        if api.token:
            try:
                api.call("Api.Logout")
            except (OSError, RuntimeError):
                pass
        api.conn.close()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError) as error:
        emit("failed", type=type(error).__name__, message=str(error))
        raise SystemExit(1)
