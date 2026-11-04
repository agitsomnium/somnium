import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_sheets

URL = 'https://docs.google.com/spreadsheets/d/e/test/pub?output=csv&gid=0'


class FetchRetryTest(unittest.TestCase):
    def response(self, data=b'id,title\n1,test\n', content_type='text/csv'):
        response = mock.MagicMock()
        response.__enter__.return_value = response
        response.headers = {'Content-Type': content_type}
        response.read.return_value = data
        return response

    @mock.patch.object(fetch_sheets.time, 'sleep')
    @mock.patch.object(fetch_sheets.urllib.request, 'urlopen')
    def test_timeout_during_open_and_read_then_success(self, open_url, sleep):
        partial = self.response()
        partial.read.side_effect = TimeoutError('read timed out')
        open_url.side_effect = [TimeoutError('connect timed out'), partial, self.response()]
        self.assertIn('1,test', fetch_sheets.fetch_csv(URL))
        self.assertEqual(open_url.call_count, 3)
        self.assertEqual(sleep.call_args_list, [mock.call(2), mock.call(4)])
        partial.__exit__.assert_called_once()

    @mock.patch.object(fetch_sheets.time, 'sleep')
    @mock.patch.object(fetch_sheets.urllib.request, 'urlopen')
    def test_transient_http_and_network_failures_recover(self, open_url, sleep):
        for error in [urllib.error.URLError('temporary failure')] + [
            urllib.error.HTTPError(URL, code, 'temporary', {}, None)
            for code in (408, 429, 500, 502, 503, 504)
        ]:
            with self.subTest(error=error):
                open_url.reset_mock()
                sleep.reset_mock()
                open_url.side_effect = [error, self.response()]
                self.assertIn('1,test', fetch_sheets.fetch_csv(URL))
                self.assertEqual(open_url.call_count, 2)
                sleep.assert_called_once_with(2)

    @mock.patch.object(fetch_sheets.time, 'sleep')
    @mock.patch.object(fetch_sheets.urllib.request, 'urlopen')
    def test_permanent_http_error_is_not_retried(self, open_url, sleep):
        open_url.side_effect = urllib.error.HTTPError(URL, 403, 'forbidden', {}, None)
        with self.assertRaises(urllib.error.HTTPError):
            fetch_sheets.fetch_csv(URL)
        open_url.assert_called_once()
        sleep.assert_not_called()

    @mock.patch.object(fetch_sheets.time, 'sleep')
    @mock.patch.object(fetch_sheets.urllib.request, 'urlopen')
    def test_invalid_content_is_not_retried(self, open_url, sleep):
        for response in [self.response(b'<html>login</html>', 'text/html'),
                         self.response(b'<html>login</html>'), self.response(b''),
                         self.response(b'x' * (fetch_sheets.MAX_BYTES + 1))]:
            with self.subTest():
                open_url.reset_mock()
                open_url.return_value = response
                with self.assertRaises(ValueError):
                    fetch_sheets.fetch_csv(URL)
                open_url.assert_called_once()
                sleep.assert_not_called()

    @mock.patch.object(fetch_sheets.time, 'sleep')
    @mock.patch.object(fetch_sheets.urllib.request, 'urlopen')
    def test_exhausted_retries_preserve_existing_live_data(self, open_url, sleep):
        open_url.side_effect = TimeoutError('read timed out')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            live = root / 'data' / 'live'
            live.mkdir(parents=True)
            marker = live / 'marker.csv'
            marker.write_text('previous data')
            config = root / 'sheets.json'
            config.write_text(json.dumps({name: URL for name in fetch_sheets.SCHEMA}))
            with mock.patch.object(fetch_sheets, 'ROOT', root):
                with self.assertRaisesRegex(RuntimeError, '세미나: read timed out'):
                    fetch_sheets.fetch_all(config, live)
            self.assertEqual(marker.read_text(), 'previous data')
            self.assertEqual(list((root / 'data').iterdir()), [live])
        self.assertEqual(open_url.call_count, 3)
        self.assertEqual(sleep.call_count, 2)


if __name__ == '__main__':
    unittest.main()
