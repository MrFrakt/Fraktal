# Windows clock final packaging — 2026-10-06

This record supersedes only package/installer hashes in
`2026-10-06_TC3_WindowsClock.json`. Library and executable bytes, native observer
queries, compiler results and pending runtime scope are unchanged.

The final installer uses a fresh protected directory ACL owned by Administrators:
SYSTEM and Administrators have full control, ordinary Users have read/execute.
Previous explicit file grants/ownership are cleared in the dedicated directory.
Reparse points and child directories are rejected before applying its ACL.
This prevents an old writable package-file ACL from surviving an update.

PowerShell syntax passed; the ACL was constructed and its owner, protection and
exact three rules verified in memory. Neither directory permissions nor a
startup task were applied on a target. Installation and SYSTEM execution remain
part of the target commissioning scope in the original acceptance record.

Both final archives were verified byte-for-byte against their unpacked package
files. Current delivery hashes are in
[the final packaging receipt](2026-10-06_TC3_WindowsClock_Packaging.json).
