#!/usr/bin/env python3
"""
Favourites Service — tiny persistence backend for DevOps Learning Hub.

Serves the HTML file and provides a JSON API for favourites.
Favourites are stored in .favourites.json and auto-committed to Git.

Usage:
    python3 favourites-service.py          # starts on http://localhost:5000
    python3 favourites-service.py --port 9000  # custom port
"""

import json
import os
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

PORT = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--port" else 5000
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FAV_FILE = os.path.join(SCRIPT_DIR, ".favourites.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "devops-learning-hub.html")


def load_favourites():
    if os.path.exists(FAV_FILE):
        with open(FAV_FILE, "r") as f:
            return json.load(f)
    return []


def save_favourites(favs):
    with open(FAV_FILE, "w") as f:
        json.dump(favs, f, indent=2)


def git_sync():
    """Auto-commit and push favourites file to Git."""
    try:
        os.chdir(SCRIPT_DIR)
        subprocess.run(["git", "add", ".favourites.json"], check=True, capture_output=True)
        result = subprocess.run(
            ["git", "commit", "-m", "sync: update favourites", "--allow-empty"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print("[git] Favourites synced to remote.")
        # if nothing to commit, that's fine — skip silently
    except subprocess.CalledProcessError as e:
        print(f"[git] Sync warning: {e.stderr.strip()}", file=sys.stderr)
    except FileNotFoundError:
        print("[git] Git not found — skipping sync.", file=sys.stderr)


class FavouritesHandler(SimpleHTTPRequestHandler):
    """Serves static files + handles /api/favourites endpoints."""

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/favourites":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            favs = load_favourites()
            self.wfile.write(json.dumps(favs).encode())
        elif parsed.path == "/" or parsed.path == "/index.html":
            # serve the learning hub at root
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(HTML_FILE, "rb") as f:
                self.wfile.write(f.read())
        else:
            # serve other static files normally
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/favourites":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            try:
                favs = json.loads(body)
                if not isinstance(favs, list):
                    raise ValueError("Expected a JSON array")
                save_favourites(favs)
                git_sync()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"ok": True}).encode())
            except (json.JSONDecodeError, ValueError) as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_OPTIONS(self):
        # handle CORS preflight
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        # quieter logging
        pass


if __name__ == "__main__":
    # ensure favourites file exists
    if not os.path.exists(FAV_FILE):
        save_favourites([])

    server = HTTPServer(("0.0.0.0", PORT), FavouritesHandler)
    print(f"DevOps Learning Hub running at http://localhost:{PORT}")
    print(f"  → Open http://localhost:{PORT} in your browser")
    print(f"  → Favourites stored in: {FAV_FILE}")
    print(f"  → Auto-syncs to Git on every change")
    print(f"  → Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()
