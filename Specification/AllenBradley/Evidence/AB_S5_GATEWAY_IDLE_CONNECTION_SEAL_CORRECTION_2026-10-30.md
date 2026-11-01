# S5 idle-connection preparation: authorization seal correction

Before any session/controller access, review of the
[preparation](AB_S5_GATEWAY_IDLE_CONNECTION_PREPARATION_2026-10-30.md)
found that its generic JSON inventory also froze the intentionally unarmed
authorization.json. Arming standing O3 would therefore fail the source gate.
The standard protocol freezes authorization.template.json; the actual grant
is recorded after sealing and checked by the existing authorization validator.

Only the actual authorization.json pin is removed. The superseded binding is
preserved under a new filename and in this payload; the original preparation
payload is unchanged. Every other source/package/gate/image pin is rechecked.
The SDK, runner, validation rules, command vectors and rollback guards are
unchanged. No controller operation occurred. This corrected source_bindings.json
is the binding used by session_10. The preparation's other scopes/proofs apply.

Corrected binding SHA-256: 6680FD3846E6869AD1EE16A9D89236696BBEE00A85327E6CA6AADF15928AA95A.
Payload manifest SHA-256: C5B04B8A6C77107CC891D903793B0CF8D2B411D65432529458567C89E610BC89.
