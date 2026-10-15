# S9 — read sessions and batch observations

`read_sessions.py` uses the existing S11_Scl scan counter on the physical
1214C V4.7.3. It logs in twice with the existing gateway user and TLS pin,
performs ten concurrent reads per client, closes/reconnects a socket while
keeping the token, explicitly logs one client out, observes code 2 Permission
denied on its old token, re-logs in and verifies the other client still reads.
It then reads the same counter sixteen times in each of ten JSON-RPC batches.
Every session logs out in `finally`; tokens/passwords are never printed.

Password comes from `FRAKTAL_TIA_WEB_PASSWORD`. Fixed target 192.168.0.10;
no tag, program or operating-mode writes. Run with:

```powershell
python FraktalCore/PLC/Siemens/Spikes/S9_WebRecovery/read_sessions.py
```

Measured: two distinct tokens and both clients pass; reconnect and explicit
re-login pass; **10/10 batches return differing counter values within one
batch**, disproving a single-scan Web API snapshot on this CPU.
`idle_session.py` observed token invalidation after 160 s idle and explicit
re-login. `mode_session.py --confirm-target 192.168.0.10` passed retained-token
reads through native STOP→RUN (requires the temporary diagnostics mode right
and both password environment variables); its mode helper identifies/confirms
before each POST. It restores RUN once after confirmed STOP, including a failed
read check. Physical cable interruption, retained-client download recovery and
end-to-end HMI freshness still need their own gates.
Record: [S9 evidence](../../../../../Specification/Siemens/Evidence/TIA_S9_READ_SESSIONS_2026-10-09.md).
