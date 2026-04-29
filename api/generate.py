"""
api/generate.py
---------------
Vercel Python serverless function — handles POST /api/generate.
"""

import json
import sys
import os
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.fetcher import build_context
from agent.synthesizer import generate_briefing


class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            context = build_context()
            briefing = generate_briefing(context)
            self._respond(200, {"ok": True, "briefing": briefing})
        except ValueError as e:
            self._respond(400, {"ok": False, "error": str(e)})
        except Exception as e:
            self._respond(500, {"ok": False, "error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _respond(self, status: int, body: dict):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
