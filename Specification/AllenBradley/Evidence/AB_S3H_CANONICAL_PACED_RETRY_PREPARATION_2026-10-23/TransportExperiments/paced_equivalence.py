import time

def stable_scan_pair(read_generation, acquire, *, attempts=100, seconds=5.0, fresh_start=False):
    """Acquire only within one completed PLC scan, with bounded read-only retries.

    The PLC marks its entire scan odd before any owner runs and even after
    publication. Equality of an even generation around all paired reads proves
    they belong to that scan; configuration hashes alone cannot prove this.
    """
    if type(attempts) is not int or not 1 <= attempts <= 100 or not 0 < seconds <= 5 or type(fresh_start) is not bool:
        raise ValueError("invalid paired-acquisition budget")
    started, history = time.monotonic(), []
    previous = None
    for unused in range(attempts):
        if time.monotonic()-started > seconds:
            break
        before = read_generation()
        if type(before) is not int or not 1 <= before <= 2147483646:
            raise ValueError("invalid or uninitialized PLC scan generation")
        row = dict(before=before)
        history.append(row)
        if before % 2:
            previous = before
            continue
        if fresh_start and (previous is None or before == previous):
            # Waiting is part of this same bounded attempt history. Starting
            # near the even edge leaves the largest available read window;
            # it neither extends the budget nor accepts a changed generation.
            previous = before
            row['waitingFreshScan'] = True
            time.sleep(.001)
            continue
        pair = acquire()
        after = read_generation()
        row['after'] = after
        if type(after) is not int:
            raise ValueError("invalid trailing PLC scan generation")
        previous = after
        if before == after and time.monotonic()-started <= seconds:
            pair.update(sameStateVerified=True,
                        stateEvidence=dict(kind="PLC entire-scan generation", generation=before,
                                           attempts=history, readOnly=True))
            if fresh_start:pair['stateEvidence']['freshStart'] = True
            return pair
    error = ValueError("no completed PLC scan held across the paired read window")
    error.attempts = history
    raise error

