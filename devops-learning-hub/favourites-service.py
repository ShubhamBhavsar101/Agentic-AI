#!/usr/bin/env python3
"""
Persistence Service — tiny backend for DevOps Learning Hub.

Serves the HTML file and provides JSON API for favourites and projects.
Data stored in .favourites.json and .projects.json, auto-committed to Git.

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
PROJ_FILE = os.path.join(SCRIPT_DIR, ".projects.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "devops-learning-hub.html")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def commit_all(msg):
    """Commit and push all data files. Called only on server shutdown."""
    # Run entire git workflow in a subprocess with a hard timeout
    # so it can never block the main thread
    import threading
    def _run():
        try:
            # Combine add+commit+push in one shell command
            cmd = (
                f'cd "{SCRIPT_DIR}" && '
                f'git add "{FAV_FILE}" "{PROJ_FILE}" && '
                f'git commit -m "{msg}" && '
                f'git push'
            )
            result = subprocess.run(
                cmd, shell=True, capture_output=True, timeout=20
            )
            if result.returncode == 0:
                print("Changes committed and pushed.")
            else:
                err = result.stderr.decode('utf-8', errors='replace')[:200]
                if 'nothing to commit' in err or 'nothing added' in err:
                    print("Nothing to commit.")
                else:
                    print(f"Git failed: {err}")
        except subprocess.TimeoutExpired:
            print("Git timed out — data may not have been pushed.")
        except Exception as e:
            print(f"Git error: {e}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=25)
    if t.is_alive():
        print("Git still running — moving on.")


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/favourites":
            favs = load_json(FAV_FILE)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(favs).encode())
            return
        if parsed.path == "/api/projects":
            projs = load_json(PROJ_FILE)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(projs).encode())
            return
        # Serve HTML and static files
        self.directory = SCRIPT_DIR
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/favourites":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            save_json(FAV_FILE, data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        if parsed.path == "/api/projects":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            save_json(PROJ_FILE, data)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        self.send_response(404)
        self.end_headers()

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/favourites/"):
            fav_id = parsed.path.split("/")[-1]
            favs = [f for f in load_json(FAV_FILE) if f.get("id") != fav_id]
            save_json(FAV_FILE, favs)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        if parsed.path.startswith("/api/projects/"):
            proj_id = parsed.path.split("/")[-1]
            projs = [p for p in load_json(PROJ_FILE) if str(p.get("id")) != proj_id]
            save_json(PROJ_FILE, projs)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b'{"ok":true}')
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress request logging


if __name__ == "__main__":
    import signal
    import threading

    os.chdir(SCRIPT_DIR)
    server = HTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Service running on http://localhost:{PORT}")
    print(f"  Favourites API:  GET/POST/DELETE /api/favourites")
    print(f"  Projects API:    GET/POST/DELETE /api/projects")

    shutdown_event = threading.Event()

    def shutdown_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down.")
        shutdown_event.set()
        server.shutdown()

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    # Serve in a thread so main thread can respond to signals
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    # Block main thread until shutdown signal
    try:
        shutdown_event.wait()
    except KeyboardInterrupt:
        pass

    print("Shutting down.")
    server.server_close()
    # Commmit in daemon thread, don't wait
    threading.Thread(target=commit_all, args=("sync: update data files",), daemon=True).start()
    print("Shutdown complete.")
