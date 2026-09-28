"""Serves docs/ — exactly the files GitHub Pages publishes, nothing extra."""

import http.server
import threading
import webbrowser
from pathlib import Path

SITE = Path(__file__).parent.parent / "docs"


def serve(port: int = 8000, open_browser: bool = True, pattern: str = "") -> None:
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(SITE), **kw)

        def log_message(self, *a):
            pass

    with http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler) as httpd:
        url = f"http://127.0.0.1:{port}/" + (f"?p={pattern}" if pattern else "")
        print(f"  serving {url}  (ctrl-c to stop)")
        if open_browser:
            threading.Timer(0.5, webbrowser.open, [url]).start()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print()
