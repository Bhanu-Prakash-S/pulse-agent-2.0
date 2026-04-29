"""
dev.py — local development server (replaces `vercel dev`)
Serves public/ as static files and routes POST /api/generate to the handler.
"""

import sys
import os
from http.server import HTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
PUBLIC = ROOT / "public"

sys.path.insert(0, str(ROOT))
from api.generate import handler as APIHandler


class DevHandler(APIHandler):

    def log_message(self, format, *args):
        print(f"  {self.command} {self.path}")

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/" or path == "":
            self._serve_file(PUBLIC / "index.html", "text/html")
        else:
            file = PUBLIC / path.lstrip("/")
            if file.exists() and file.is_file():
                ext = file.suffix
                ctype = {"css": "text/css", "js": "application/javascript"}.get(ext.lstrip("."), "text/html")
                self._serve_file(file, ctype)
            else:
                self.send_error(404, f"Not found: {path}")

    def _serve_file(self, path: Path, ctype: str):
        try:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except FileNotFoundError:
            self.send_error(404)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    server = HTTPServer(("localhost", port), DevHandler)
    print(f"\n  Pulse Agent running at http://localhost:{port}\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
