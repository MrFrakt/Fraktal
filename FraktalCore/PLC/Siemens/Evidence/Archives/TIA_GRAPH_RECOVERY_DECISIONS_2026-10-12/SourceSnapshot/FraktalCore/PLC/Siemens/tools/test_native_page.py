"""Native-page close drops local credentials even when logout cannot finish."""
import http.client
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "Spikes/S11_Scl"))
import web_mode


class NativePageCloseTest(unittest.TestCase):
    def test_successful_http_logout_discards_local_authentication(self):
        connection = Mock()
        connection.getresponse.return_value.status = 302
        connection.getresponse.return_value.getheaders.return_value = []
        connection.getresponse.return_value.read.return_value = b""
        with patch.object(web_mode, "PinnedHttps", return_value=connection):
            page = web_mode.NativePage("unused-pin")
        page.cookies["siemens_ad_session"] = "test-session"
        page.close()
        self.assertEqual(page.cookies, {})
        connection.close.assert_called_once()

    def test_failed_logout_releases_authentication_and_socket_without_replay(self):
        for error in (TimeoutError("timeout"), http.client.RemoteDisconnected("closed")):
            with self.subTest(error=type(error).__name__):
                connection = Mock()
                connection.request.side_effect = error
                with patch.object(web_mode, "PinnedHttps", return_value=connection):
                    page = web_mode.NativePage("unused-pin")
                page.cookies["siemens_ad_session"] = "test-session"
                page.close()
                self.assertEqual(page.cookies, {})
                connection.close.assert_called_once()
                connection.request.assert_called_once()
                self.assertEqual(connection.request.call_args.args[:2], ("GET", "/FormLogin?LOGOUT"))


if __name__ == "__main__":
    unittest.main()
