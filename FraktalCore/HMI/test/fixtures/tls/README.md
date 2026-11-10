# Test-only TLS identity

`s7web_test_cert.pem` / `s7web_test_key.pem` are a self-signed certificate and
its unencrypted private key, generated for `test/s7web_direct_test.dart` only.
They let the test run a loopback HTTPS server and prove that the direct
`s7web://` transport accepts exactly the pinned certificate and refuses any
other. They secure nothing and must never be installed on a CPU, gateway or
proxy.

SHA-256 fingerprint:
`DB:09:EC:F4:AD:75:60:04:03:97:06:31:E5:9C:C3:67:DE:9B:FA:5C:35:87:F3:27:FA:B4:15:A0:FA:B7:2D:57`

Regenerate with
`openssl req -x509 -newkey rsa:2048 -nodes -keyout s7web_test_key.pem -out s7web_test_cert.pem -days 36500 -subj "/CN=fraktal-s7web-test"`
and update the fingerprint in the test.
