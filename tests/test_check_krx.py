import io
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_krx


class MonitorTests(unittest.TestCase):
    def response(self, body):
        opener = MagicMock()
        opener.open.return_value.__enter__.return_value = io.StringIO(body)
        return opener

    def test_real_rows_required(self):
        for body, expected in [('{"OutBlock_1":[{"ISU_CD":"KR7005930003"}]}', True),
                               ('{"OutBlock_1":[]}', False),
                               ('{"OutBlock_1":[{}]}', False),
                               ('{"respCode":"401"}', False),
                               ('<html>error</html>', False)]:
            with self.subTest(body=body), patch.object(check_krx, "build_opener", return_value=self.response(body)):
                self.assertEqual(check_krx.check_krx("secret")[0], expected)

    def test_unauthorized_is_reported_without_secret(self):
        with patch.object(check_krx, "build_opener") as factory:
            factory.return_value.open.side_effect = HTTPError("https://example.com", 401, "secret", {}, None)
            success, detail = check_krx.check_krx("secret")
        self.assertFalse(success)
        self.assertIn("401", detail)
        self.assertNotIn("secret", detail)

    def test_only_successful_check_and_email_stop_workflow(self):
        env = {name: "test" for name in ["KRX_API_KEY", "SMTP_USER", "SMTP_APP_PASSWORD", "REPORT_TO", "GITHUB_TOKEN", "GITHUB_REPOSITORY"]}
        for success, mail_error, should_stop in [(False, None, False), (True, None, True), (True, RuntimeError(), False)]:
            with self.subTest(success=success, mail_error=mail_error), patch.dict(os.environ, env), \
                 patch.object(check_krx, "check_krx", return_value=(success, "result")), \
                 patch.object(check_krx, "send_result", side_effect=mail_error) as mail, \
                 patch.object(check_krx, "disable_workflow") as stop:
                if mail_error:
                    with self.assertRaises(RuntimeError):
                        check_krx.main()
                else:
                    check_krx.main()
                mail.assert_called_once_with(success, "result")
                self.assertEqual(stop.called, should_stop)


if __name__ == "__main__":
    unittest.main()
