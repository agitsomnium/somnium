"""Loopback-only real-Auth review. Never serves source directories or SMTP credentials."""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote

WEB = Path(__file__).resolve().parent
REPO = WEB.parents[1]


def handler(config, port):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_GET(self):
            if self.headers.get('Host') != f'127.0.0.1:{port}':
                self.send_error(403)
                return
            path = unquote(urlsplit(self.path).path)
            if path == '/runtime-config.json':
                data = json.dumps(config).encode()
                mime = 'application/json'
            else:
                routes = {'/': WEB / 'index.html', '/app.js': WEB / 'dist/app.js', '/app.js.LEGAL.txt': WEB / 'dist/app.js.LEGAL.txt',
                          '/brand.css': REPO / 'assets/site.css', '/tokens.css': REPO / 'assets/tokens.css',
                          '/fonts-display.css': REPO / 'assets/fonts-display.css', '/trial.css': REPO / 'classroom/trial.css'}
                file = routes.get(path)
                if file is None and path.startswith(('/fonts/', '/assets/fonts/')) and path.endswith('.woff2'):
                    relative = path.removeprefix('/assets/').lstrip('/')
                    candidate = (REPO / 'assets' / relative).resolve()
                    if candidate.is_relative_to((REPO / 'assets/fonts').resolve()):
                        file = candidate
                if path in ('/assets/brand.css', '/assets/somnium_wordmark_on_paper.svg', '/assets/SomniumDisplay.woff2'):
                    file = REPO / path.lstrip('/')
                if not file or not file.is_file():
                    self.send_error(404)
                    return
                data = file.read_bytes()
                mime = mimetypes.guess_type(file)[0] or 'application/octet-stream'
            self.send_response(200)
            for key, value in {
                'Content-Type': mime, 'Content-Length': str(len(data)), 'Cache-Control': 'no-store',
                'X-Robots-Tag': 'noindex, nofollow, noarchive', 'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'strict-origin-when-cross-origin', 'Cross-Origin-Resource-Policy': 'same-origin',
                'Content-Security-Policy': "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; connect-src 'self' https://jdfrottxrdhglxtqvtyx.supabase.co; frame-src https://www.youtube-nocookie.com https://player.vimeo.com; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
            }.items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(data)
    return Handler


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--port', type=int, default=8766)
    args = parser.parse_args()
    private = json.loads(args.config.read_text())
    if private.get('url') != 'https://jdfrottxrdhglxtqvtyx.supabase.co' or not private.get('publishableKey', '').startswith('sb_publishable_'):
        raise ValueError('Expected Somnium test project and publishable client key')
    config = {key: private[key] for key in ('url', 'publishableKey')}
    # UI review restriction; not an Auth server allowlist or a production access control.
    config['testEmails'] = ['agit.somnium@gmail.com']
    print(f'Real Auth review: http://127.0.0.1:{args.port}/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', args.port), handler(config, args.port)).serve_forever()
