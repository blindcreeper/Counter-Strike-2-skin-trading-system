"""Lightweight HTTP status server for remote monitoring.

Provides:
  GET /           - JSON status snapshot
  GET /health     - Simple health check (200 = alive)
  GET /heartbeat  - Last heartbeat timestamp

Runs in a daemon thread, does not block the main scan loop.
"""
import json
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler


class StatusHandler(BaseHTTPRequestHandler):
    stats = None  # set before server starts

    def do_GET(self):
        if self.path == "/health":
            self._json({"status": "alive", "time": datetime.now().isoformat()}, 200)
        elif self.path == "/heartbeat":
            snap = self.stats.get_snapshot() if self.stats else {}
            self._json({
                "last_heartbeat": snap.get("last_heartbeat"),
                "status": snap.get("status", "unknown"),
            })
        else:
            snap = self.stats.get_snapshot() if self.stats else {"status": "no_stats"}
            self._json(snap)

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass  # suppress access logs


def start_status_server(stats, host="0.0.0.0", port=8199):
    """Start the status HTTP server in a daemon thread."""
    StatusHandler.stats = stats
    server = HTTPServer((host, port), StatusHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[StatusServer] http://{host}:{port}/  (daemon thread)")
    return server
