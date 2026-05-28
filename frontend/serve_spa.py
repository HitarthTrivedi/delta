from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os


BUILD_DIR = Path(__file__).resolve().parent / "build"


class SpaHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        requested = BUILD_DIR / self.path.lstrip("/").split("?", 1)[0]
        if self.path.startswith("/static/") or requested.exists():
            return super().do_GET()
        self.path = "/index.html"
        return super().do_GET()


if __name__ == "__main__":
    os.chdir(BUILD_DIR)
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), SpaHandler)
    print(f"Delta SPA server listening on http://localhost:{port}")
    server.serve_forever()
