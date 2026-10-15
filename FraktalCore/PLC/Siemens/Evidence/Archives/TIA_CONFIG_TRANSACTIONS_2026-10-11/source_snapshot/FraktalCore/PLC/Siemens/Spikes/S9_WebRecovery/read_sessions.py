"""Read-only S9 session/reconnect/batch observations on the fixed 1214C bench.

Requires the deployed S11_Scl counter fixture and existing TLS pin. Password is
read by WebApi from FRAKTAL_TIA_WEB_PASSWORD. No tags or operating mode are written.
Logout invalidation is a controlled substitute for testing invalid-token recovery;
it does not measure natural token expiry. Batch samples do not prove atomicity.
"""
import concurrent.futures
import json
import os
import pathlib
import sys
import threading
import time

TOOLS = pathlib.Path(__file__).resolve().parents[2] / "tools"
sys.path.insert(0, str(TOOLS))
from tia_webapi import WebApi, WebApiError

HOST = "192.168.0.10"
COUNTER = '"S11Scl".Samples[1]'


def emit(event, **fields):
    print(json.dumps({"event": event, **fields}), flush=True)


def read(api):
    return api.call("PlcProgram.Read", {"var": COUNTER})


def observe_client(api, label, barrier):
    barrier.wait(timeout=15)
    samples = []
    for index in range(10):
        started = time.monotonic()
        samples.append(read(api))
        emit("concurrent-read", client=label, index=index, value=samples[-1],
             elapsed_ms=round((time.monotonic() - started) * 1000, 3))
    if not all(isinstance(value, int) for value in samples):
        raise ValueError("counter read did not return integer values")
    if any(after < before for before, after in zip(samples, samples[1:])):
        raise ValueError("counter went backwards during read-only session test")
    return len(samples)


def main():
    pin = pathlib.Path(os.environ["LOCALAPPDATA"]) / "Fraktal/TiaStations/192.168.0.10.webapi.pin"
    clients = []
    try:
        for label in ("A", "B"):
            api = WebApi(HOST, pin, False)
            clients.append(api)
            api.login("fraktal")
            emit("login", client=label, authenticated=bool(api.token))
        emit("independent-tokens", distinct=clients[0].token != clients[1].token)
        barrier = threading.Barrier(2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            jobs = [executor.submit(observe_client, api, label, barrier)
                    for api, label in zip(clients, ("A", "B"))]
            counts = [job.result() for job in jobs]
        emit("concurrent-clients", result="PASS", reads=counts)

        api = clients[0]
        original_token = api.token
        api.conn.close()
        value = read(api)
        emit("socket-reconnect", result="PASS", same_token=api.token == original_token,
             pin_checked=True, value=value)

        api.call("Api.Logout")
        try:
            read(api)
        except WebApiError as error:
            emit("logged-out-token", code=error.code, message=str(error))
            if error.code != 2:
                raise ValueError("expected bench permission-denied code 2 after logout") from error
        else:
            raise ValueError("logged-out token still authorized a protected read")
        api.token = None
        api.login("fraktal")
        emit("explicit-relogin", result="PASS", value=read(api))
        emit("other-client-after-logout", result="PASS", value=read(clients[1]))

        varying = 0
        for index in range(10):
            started = time.monotonic()
            results = api.bulk([("PlcProgram.Read", {"var": COUNTER}) for _ in range(16)])
            if any(error for _, error in results):
                raise ValueError("batch read returned an error")
            values = [value for value, _ in results]
            same = len(set(values)) == 1
            varying += not same
            emit("batch-counter", index=index, values=values, same=same,
                 elapsed_ms=round((time.monotonic() - started) * 1000, 3))
        emit("batch-observation", batches=10, varying=varying,
             atomicity="DISPROVED" if varying else "NOT_PROVEN")
    finally:
        for api in clients:
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
