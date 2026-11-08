"""Verify parent commit sha for C5c."""
import subprocess, sys

out = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
print('HEAD:', out)
expected_parent = '08882bcd4d5071d5731ba3df8725c8211eaffac0'
assert out == expected_parent, f'Expected {expected_parent}, got {out}'
print('Bootstrap verified: parent commit matches.')
