#!/usr/bin/env python3
"""Preview only the public website at its GitHub Pages root URL."""

from __future__ import annotations

import argparse
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


SITE_PATH = "/"
PUBLIC_SUFFIXES = {
    ".html", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg",
    ".webp", ".avif", ".gif", ".ico", ".xml", ".txt", ".woff", ".woff2",
}


def make_handler(root: Path) -> type[BaseHTTPRequestHandler]:
    """Resolve requests under one root; never expose listings or source tooling."""

    class WebsiteHandler(BaseHTTPRequestHandler):
        server_version = "MoodumiPreview/1.0"

        def do_GET(self) -> None:
            self.serve(head_only=False)

        def do_HEAD(self) -> None:
            self.serve(head_only=True)

        def serve(self, *, head_only: bool) -> None:
            try:
                path = unquote(urlsplit(self.path).path, errors="strict")
            except (UnicodeError, ValueError):
                self.send_error(400, "Invalid URL path")
                return

            if not path.startswith(SITE_PATH):
                self.send_error(404, "Use the website root preview path")
                return

            relative = path[len(SITE_PATH):]
            parts = relative.split("/")
            if ("\\" in relative or "\x00" in relative
                    or any(part.startswith(".") for part in parts if part)):
                self.send_error(403, "Private paths are not served")
                return
            candidate = (root / relative).resolve()
            if not candidate.is_relative_to(root):
                self.send_error(403, "Path is outside the website")
                return
            if candidate.is_dir():
                candidate = (candidate / "index.html").resolve()
            if (not candidate.is_relative_to(root) or not candidate.is_file()
                    or candidate.suffix.lower() not in PUBLIC_SUFFIXES):
                self.send_error(404, "Public website file not found")
                return

            content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type in ("application/javascript", "image/svg+xml"):
                content_type += "; charset=utf-8"
            try:
                size = candidate.stat().st_size
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(size))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                if not head_only:
                    with candidate.open("rb") as source:
                        while chunk := source.read(64 * 1024):
                            self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                return

    return WebsiteHandler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765, help="Local port (default: 8765)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    root = Path(__file__).resolve().parent.parent
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(root))
    print(f"Moodumi local preview: http://127.0.0.1:{args.port}{SITE_PATH}", flush=True)
    print("Bound to this computer only. Press Ctrl+C to stop.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPreview stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
