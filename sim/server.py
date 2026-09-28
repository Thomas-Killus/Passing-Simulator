"""Serves viewer/ plus the simulated pattern as /pattern.json."""

import http.server
import json
import threading
import webbrowser
from pathlib import Path

VIEWER = Path(__file__).parent.parent / "viewer"


def serve(doc: dict, port: int = 8000, open_browser: bool = True) -> None:
    payload = json.dumps(doc).encode()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(VIEWER), **kw)

        def do_GET(self):
            if self.path.split("?")[0] != "/pattern.json":
                return super().do_GET()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *a):
            pass

    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/"
        print(f"  serving {url}  (ctrl-c to stop)")
        if open_browser:
            threading.Timer(0.5, webbrowser.open, [url]).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
