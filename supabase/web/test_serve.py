import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from serve import handler


class ReviewBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler({}, 0))
        cls.port = cls.httpd.server_port
        cls.httpd.RequestHandlerClass = handler({'url': 'https://example.invalid', 'publishableKey': 'sb_publishable_test'}, cls.port)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def request(self, path, host=None, method='GET'):
        conn = HTTPConnection('127.0.0.1', self.port)
        conn.request(method, path, headers={'Host': host or f'127.0.0.1:{self.port}'})
        result = conn.getresponse()
        body = result.read()
        headers = dict(result.getheaders())
        status = result.status
        conn.close()
        return status, body, headers

    def test_dns_rebinding_host_denied(self):
        self.assertEqual(self.request('/runtime-config.json', host='attacker.invalid')[0], 403)

    def test_source_private_config_and_traversal_denied(self):
        for path in ['/serve.py', '/app.js.map', '/package-lock.json', '/.env', '/../night-setup-20261101/client-config.private.json', '/assets/fonts/../../supabase/web/serve.py', '/assets/%2e%2e/supabase/web/serve.py']:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 404)

    def test_no_local_mutation_endpoint(self):
        self.assertEqual(self.request('/', method='POST')[0], 501)

    def test_headers_and_browser_public_config(self):
        status, body, headers = self.request('/runtime-config.json')
        self.assertEqual(status, 200)
        self.assertEqual(set(json.loads(body)), {'url', 'publishableKey'})
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertIn("connect-src 'self' https://jdfrottxrdhglxtqvtyx.supabase.co", headers['Content-Security-Policy'])
        self.assertIn('noindex', headers['X-Robots-Tag'])

    def test_no_fake_auth_tools_or_privileged_keys_in_page(self):
        status, body, _ = self.request('/')
        self.assertEqual(status, 200)
        for fragment in [b'test-mail', b'data-email=', b'service_role', b'sb_secret_']:
            self.assertNotIn(fragment, body)


if __name__ == '__main__':
    unittest.main()
