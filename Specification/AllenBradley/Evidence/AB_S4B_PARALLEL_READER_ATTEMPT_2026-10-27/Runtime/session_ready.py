"""Bounded validation of a helper's ready message, including partial writes."""
import json
import time

def wait_for_ready(path,expected,process,*,timeout):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        if process.poll() is not None:
            raise RuntimeError('helper exited before readiness was validated')
        try:
            raw=path.read_bytes()
        except FileNotFoundError:
            raw=b''
        if len(raw)>1024:
            raise ValueError('ready message exceeds its size bound')
        try:
            value=json.loads(raw)
        except (json.JSONDecodeError,UnicodeDecodeError):
            pass
        else:
            if not isinstance(value,dict) or value.keys()!=expected.keys() or any(
                type(value[key]) is not type(wanted) or value[key]!=wanted
                for key,wanted in expected.items()):
                raise ValueError('unexpected readiness message')
            return value
        remaining=deadline-time.monotonic()
        if remaining>0:
            time.sleep(min(.05,remaining))
    raise RuntimeError('helper readiness deadline exceeded; no complete validated message')
