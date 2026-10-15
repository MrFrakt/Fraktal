# Root decision service qualification

This fixture extends the existing two-root, nested-Unit config bench. Twenty-eight
native service cases cover idempotence, overlapping requests, root isolation,
source ownership, valid answers, access/interlock denial, finite and indefinite
timeout, operator priority on expiry, withdrawal and closed audit events.
Large scratch records are private DB storage rather than temporary stack memory.
The Web API harvest adds eight checks for completion/counts, readonly publication,
private storage and final withdrawal. It records simulator identity before writes.

Prepare with Tests/Access/with_credentials.ps1 and this directory's make_fixture.py;
compile/import using the owner-whitelisted driver and an isolated project copy.
Use the same wrapper with -Action probe and probe_web.py for the harvest. Credentials
stay in DPAPI/environment handling. This fixture does not run a physical press.

Core owns one private decision slot per actual root; nested Units and CMs allocate
no decision strings. Only the raising module consumes an answer, and only the
root mailbox accepts it. Generated Unit management resolves or withdraws requests
on reset, mode change, abort, fault and loss of BUSY. Root mirrors are readonly.

Named configuration sets, broader durable providers and the complete sequence
frontier remain subsequent port work. See the dated decision/GRAPH evidence.
