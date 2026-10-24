"""本地预览用静态服务器：HTML 以 UTF-8 返回，并补上发布时外壳会加的 doctype/charset。"""
import functools
import http.server
import sys
from pathlib import Path

ROOT = Path(sys.argv[2] if len(sys.argv) > 2 else "demo").resolve()
SHELL = (
    '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    "</head><body>{}</body></html>"
)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            body = SHELL.format((ROOT / "index.html").read_text("utf-8")).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        super().do_GET()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(Handler, directory=str(ROOT))).serve_forever()
