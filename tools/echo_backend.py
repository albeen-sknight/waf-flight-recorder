#!/usr/bin/env python3
"""Tiny stand in for OWASP Juice Shop, used only when the lab runs natively
(without Docker). It answers every request with 200/201 and echoes what it
received, so the WAF's decision is the only thing that can make a test fail.

The WAF inspects the request, not the application, so rule behaviour seen
here carries over to the real Juice Shop. CI runs the real Juice Shop.

    python3 tools/echo_backend.py            # listens on 127.0.0.1:3000
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

HOST, PORT = "127.0.0.1", 3000


class Handler(BaseHTTPRequestHandler):
    server_version = "wfr-echo-backend"

    def _answer(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length).decode("utf-8", "replace") if length else ""
        url = urlsplit(self.path)
        status = 201 if self.command == "POST" else 200
        payload = {
            "backend": "wfr-echo-backend",
            "method": self.command,
            "path": url.path,
            "query": url.query,
            "body": body,
        }
        if url.path == "/" and self.command == "GET":
            data = b"<html><body><h1>OWASP Juice Shop (stand in)</h1></body></html>"
            ctype = "text/html"
        else:
            data = json.dumps(payload).encode()
            ctype = "application/json"
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_HEAD = do_OPTIONS = _answer

    def log_message(self, fmt, *args):  # keep the console quiet
        pass


if __name__ == "__main__":
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
