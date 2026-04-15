"""
Proxy léger pour contourner les restrictions CORS de Keycloak.
Le site appelle ce proxy en localhost, le proxy fait les requêtes Keycloak côté serveur.

Usage:
    python proxy.py

Le proxy écoute sur http://localhost:3001
"""

import json
import urllib.request
import urllib.parse
import urllib.error
from http.server import BaseHTTPRequestHandler, HTTPServer

PROXY_PORT = 3001


class ProxyHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        print(f"  {self.address_string()} - {format % args}")

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        # Lire le body
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        try:
            payload = json.loads(body)
        except Exception:
            self.send_response(400)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"invalid json body"}')
            return

        target_url = payload.get("url")
        form_data  = payload.get("data", {})
        headers    = payload.get("headers", {})

        if not target_url:
            self.send_response(400)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"missing url"}')
            return

        # Construire la requête vers Keycloak
        encoded = urllib.parse.urlencode(form_data).encode()
        req = urllib.request.Request(target_url, data=encoded, method="POST")
        req.add_header("Content-Type", "application/x-www-form-urlencoded")
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                result = resp.read()
        except urllib.error.HTTPError as e:
            status = e.code
            result = e.read()
        except Exception as e:
            self.send_response(502)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(result)

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""

        try:
            payload = json.loads(body)
        except Exception:
            self.send_response(400)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"error":"invalid json body"}')
            return

        target_url  = payload.get("url")
        json_body   = payload.get("data", {})
        headers     = payload.get("headers", {})

        req = urllib.request.Request(
            target_url,
            data=json.dumps(json_body).encode(),
            method="PUT"
        )
        req.add_header("Content-Type", "application/json")
        for k, v in headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                result = resp.read() or b"{}"
        except urllib.error.HTTPError as e:
            status = e.code
            result = e.read() or b"{}"
        except Exception as e:
            self.send_response(502)
            self._cors_headers()
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
            return

        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(result)


if __name__ == "__main__":
    server = HTTPServer(("localhost", PROXY_PORT), ProxyHandler)
    print(f"Proxy démarré sur http://localhost:{PROXY_PORT}")
    print("Ctrl+C pour arrêter\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nProxy arrêté.")
