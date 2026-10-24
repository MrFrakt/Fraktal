# S3h diagnostic service preflight — 2026-10-23

The owner approved the prepared diagnostic session (`call_b76d12f2f038411386f83c339fcd94e0:0`),
then requested resume after an interruption. No prior SDK/Python diagnostic
process was running and the one-shot workspace had no authorization, backup
or deployment artifacts. Approval is now bound to the sealed preparation;
all 159 project and two diagnostic source hashes match.

The fresh preflight stops because FactoryTalk Logix Echo Service is **Stopped**
and port 44818 has no listener. The current process is not an elevated
Administrator. The [handover](../AB_CANONICAL_PUBLICATION_HANDOVER_2026-10-20.md)
documents this boot-time issue and requires the owner to start the service in
an Administrator PowerShell:

```powershell
Start-Service "FactoryTalk Logix Echo Service"
```

| Check | Exact outcome |
|---|---|
| Prepared image | C6B42327BA819D6D79BB4618DCE70555F9DA305DCF0715BE2FCD2B9685D7D9DC unchanged |
| Initial service guard | Refused, exit 1 |
| MANUAL helper | Its internal service guard refused before writes, exit 1 |
| Document preflight | Exact local Echo identity unavailable, exit 1 |
| Backup helper | Its internal guard refused before upload, exit 3762504530 |
| Backup/restore/deployment artifacts | No new ACD, backup.sha256 or deploy_attempt.json |
| Controller-changing operations | None |
| Authorization | Recorded, not consumed; no second download approval requested |

The command orchestration should have stopped at the first nonzero guard.
The SDK helper failed closed independently. The replacement guarded runner
uses check=True for each subprocess and cannot start a later dependency after
a failed guard/audit. Failed logs and both orchestration versions remain in
the payload. Fresh identity/service/listener/fault/Remote/session/document
checks remain mandatory after restart. A fault clear is not authorized.

This report records the stopped-service observation at
`2026-10-24T04:47:29.410168+00:00`. It does not claim a current controller mode or final
readiness while Echo is offline. S3h remains incomplete and V2 inactive.
No commit or push. Work folder: `C:/work/fraktal-ab-s3h-20261023/runtime_b1730f6ce242464a817b4d8eb4d38abb`.
