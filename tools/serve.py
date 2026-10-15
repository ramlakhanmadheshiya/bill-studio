#!/usr/bin/env python3
"""Local dev server (threaded, large backlog, no caching). Usage: python3 tools/serve.py [port]"""
import http.server, socketserver, sys, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
class H(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, '.js': 'text/javascript', '.webmanifest': 'application/manifest+json', '.woff2': 'font/woff2', '.svg': 'image/svg+xml'}
    def end_headers(self):
        self.send_header('Cache-Control', 'no-store'); super().end_headers()
    def log_message(self, *a): pass
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True; request_queue_size = 256; allow_reuse_address = True
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
print(f'Serving on http://127.0.0.1:{port}/', flush=True)
S(('127.0.0.1', port), H).serve_forever()
