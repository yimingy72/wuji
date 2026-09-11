"""Ephemeral synthetic HTTP surfaces. No target persistence or outbound requests."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os

HTML = b'<!doctype html><html><head><title>Catalog</title></head><body><h1>Catalog</h1><a href="/catalog/a">Catalog A</a><a href="/catalog/b">Catalog B</a><a href="/account/view">Account</a></body></html>'

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def respond(self):
        path = self.path.split('?', 1)[0]
        status, body, content_type = 200, b'{"items":[]}', 'application/json'
        headers = {}
        if path == '/':
            body, content_type = HTML, 'text/html; charset=utf-8'
        elif path in ('/catalog/a', '/catalog/b'):
            origin = self.headers.get('Origin')
            if origin and (path == '/catalog/a' or origin == 'https://trusted.example.invalid'):
                headers.update({'Access-Control-Allow-Origin': origin, 'Access-Control-Allow-Credentials': 'true', 'Vary': 'Origin'})
        elif path == '/account/view':
            status, body = 401, b'{"message":"Authentication required"}'
        else:
            status, body = 404, b'{"message":"Not found"}'
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        for key, value in headers.items():
            self.send_header(key, value)
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    do_GET = respond
    do_HEAD = respond
    do_OPTIONS = respond

if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '8000'))), Handler)
    print(f'listening:{server.server_port}', flush=True)
    server.serve_forever()
