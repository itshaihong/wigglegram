#!/usr/bin/env python3
"""Small web gallery and capture trigger for the Raspberry Pi."""

from __future__ import annotations

import argparse
import html
import json
import mimetypes
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from wigglegram_phase1 import run as run_capture


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.json"
DEFAULT_OUTPUT_DIR = ROOT / "captures"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".gif", ".png"}

capture_lock = threading.Lock()
capture_state = {
    "running": False,
    "ok": True,
    "message": "Ready",
    "started_at": None,
    "finished_at": None,
}


INDEX_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wigglegram</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f6f7f2;
      --ink: #18201e;
      --muted: #63706b;
      --line: #d9ded6;
      --panel: #ffffff;
      --accent: #0f8f83;
      --accent-dark: #096d65;
      --warm: #e56f4f;
      --shadow: 0 18px 45px rgba(24, 32, 30, 0.12);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--ink);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }

    .shell {
      width: min(1120px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 36px;
    }

    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      padding-bottom: 20px;
      border-bottom: 1px solid var(--line);
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .mark {
      width: 42px;
      height: 42px;
      border-radius: 8px;
      background:
        linear-gradient(135deg, rgba(15,143,131,0.95), rgba(229,111,79,0.95)),
        #0f8f83;
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.35);
      flex: 0 0 auto;
    }

    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.1;
      font-weight: 750;
    }

    .subtitle {
      margin-top: 3px;
      color: var(--muted);
      font-size: 14px;
    }

    .actions {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    button, .button {
      appearance: none;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--ink);
      min-height: 40px;
      padding: 0 14px;
      border-radius: 8px;
      font: inherit;
      font-weight: 650;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      cursor: pointer;
      box-shadow: 0 1px 0 rgba(24,32,30,0.04);
    }

    button.primary {
      color: #fff;
      background: var(--accent);
      border-color: var(--accent-dark);
    }

    button:disabled {
      cursor: progress;
      opacity: 0.62;
    }

    .status {
      display: flex;
      align-items: center;
      gap: 10px;
      margin: 18px 0;
      color: var(--muted);
      font-size: 14px;
    }

    .dot {
      width: 9px;
      height: 9px;
      border-radius: 999px;
      background: var(--accent);
      box-shadow: 0 0 0 4px rgba(15,143,131,0.12);
      flex: 0 0 auto;
    }

    .dot.busy {
      background: var(--warm);
      box-shadow: 0 0 0 4px rgba(229,111,79,0.15);
    }

    .preview-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.4fr) minmax(280px, 0.8fr);
      gap: 18px;
      align-items: start;
    }

    .preview {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .preview-media {
      min-height: 360px;
      background: #101715;
      display: grid;
      place-items: center;
    }

    .preview-media img {
      width: 100%;
      height: 100%;
      max-height: 68vh;
      object-fit: contain;
      display: block;
    }

    .empty {
      color: #d7ded9;
      font-weight: 650;
      padding: 40px;
      text-align: center;
    }

    .preview-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 14px;
      border-top: 1px solid var(--line);
    }

    .file-title {
      font-weight: 750;
      overflow-wrap: anywhere;
    }

    .file-meta {
      color: var(--muted);
      font-size: 13px;
      margin-top: 2px;
    }

    .side {
      display: grid;
      gap: 12px;
    }

    .file-card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 12px;
      display: grid;
      grid-template-columns: 76px minmax(0, 1fr);
      gap: 12px;
      align-items: center;
      cursor: pointer;
    }

    .file-card.active {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(15,143,131,0.13);
    }

    .thumb {
      width: 76px;
      aspect-ratio: 4 / 3;
      border-radius: 6px;
      object-fit: cover;
      background: #dfe5df;
      display: block;
    }

    .file-row-actions {
      display: flex;
      gap: 8px;
      margin-top: 8px;
      flex-wrap: wrap;
    }

    .mini-link {
      color: var(--accent-dark);
      font-size: 13px;
      font-weight: 700;
      text-decoration: none;
    }

    @media (max-width: 780px) {
      header {
        align-items: flex-start;
        flex-direction: column;
      }

      .actions {
        width: 100%;
        justify-content: stretch;
      }

      button, .button {
        flex: 1 1 auto;
      }

      .preview-grid {
        grid-template-columns: 1fr;
      }

      .preview-media {
        min-height: 260px;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header>
      <div class="brand">
        <div class="mark" aria-hidden="true"></div>
        <div>
          <h1>Wigglegram</h1>
          <div class="subtitle">Camera preview and download</div>
        </div>
      </div>
      <div class="actions">
        <button id="captureBtn" class="primary" type="button">Capture</button>
        <button id="refreshBtn" type="button">Refresh</button>
      </div>
    </header>

    <div class="status">
      <span id="statusDot" class="dot"></span>
      <span id="statusText">Loading gallery</span>
    </div>

    <section class="preview-grid">
      <article class="preview">
        <div id="previewMedia" class="preview-media">
          <div class="empty">No captures yet</div>
        </div>
        <div class="preview-bar">
          <div>
            <div id="previewName" class="file-title">Waiting for image</div>
            <div id="previewMeta" class="file-meta">Run a capture to create the first frame.</div>
          </div>
          <a id="downloadBtn" class="button" href="#" download hidden>Download</a>
        </div>
      </article>

      <aside id="fileList" class="side" aria-label="Capture files"></aside>
    </section>
  </main>

  <script>
    const fileList = document.getElementById('fileList');
    const previewMedia = document.getElementById('previewMedia');
    const previewName = document.getElementById('previewName');
    const previewMeta = document.getElementById('previewMeta');
    const downloadBtn = document.getElementById('downloadBtn');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');
    const captureBtn = document.getElementById('captureBtn');
    const refreshBtn = document.getElementById('refreshBtn');
    let selectedName = null;

    function formatBytes(bytes) {
      if (bytes < 1024) return `${bytes} B`;
      if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
      return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
    }

    function setStatus(state) {
      const running = Boolean(state.running);
      statusDot.classList.toggle('busy', running);
      captureBtn.disabled = running;
      statusText.textContent = state.message || (running ? 'Capturing' : 'Ready');
    }

    function chooseDefault(files) {
      if (selectedName && files.some((file) => file.name === selectedName)) return selectedName;
      const gif = files.find((file) => file.name === 'wiggle.gif');
      if (gif) return gif.name;
      return files[0] ? files[0].name : null;
    }

    function showPreview(file) {
      selectedName = file.name;
      const mediaUrl = `/media/${encodeURIComponent(file.name)}?t=${Date.now()}`;
      previewMedia.innerHTML = `<img src="${mediaUrl}" alt="${file.name}">`;
      previewName.textContent = file.name;
      previewMeta.textContent = `${formatBytes(file.size)} · ${file.modified}`;
      downloadBtn.hidden = false;
      downloadBtn.href = `/download/${encodeURIComponent(file.name)}`;
      downloadBtn.download = file.name;
      document.querySelectorAll('.file-card').forEach((card) => {
        card.classList.toggle('active', card.dataset.name === file.name);
      });
    }

    function renderFiles(files) {
      fileList.innerHTML = '';
      if (!files.length) {
        fileList.innerHTML = '<div class="file-card"><div></div><div><div class="file-title">No files yet</div><div class="file-meta">Capture from the page or run ./run_once.sh.</div></div></div>';
        previewMedia.innerHTML = '<div class="empty">No captures yet</div>';
        previewName.textContent = 'Waiting for image';
        previewMeta.textContent = 'Run a capture to create the first frame.';
        downloadBtn.hidden = true;
        return;
      }

      const defaultName = chooseDefault(files);
      files.forEach((file) => {
        const card = document.createElement('button');
        card.className = 'file-card';
        card.type = 'button';
        card.dataset.name = file.name;
        card.innerHTML = `
          <img class="thumb" src="/media/${encodeURIComponent(file.name)}?t=${Date.now()}" alt="">
          <div>
            <div class="file-title">${file.name}</div>
            <div class="file-meta">${formatBytes(file.size)} · ${file.modified}</div>
            <div class="file-row-actions">
              <a class="mini-link" href="/download/${encodeURIComponent(file.name)}" download>Download</a>
            </div>
          </div>
        `;
        card.addEventListener('click', (event) => {
          if (event.target.tagName.toLowerCase() === 'a') return;
          showPreview(file);
        });
        fileList.appendChild(card);
      });

      const selected = files.find((file) => file.name === defaultName);
      if (selected) showPreview(selected);
    }

    async function loadGallery() {
      const response = await fetch('/api/files', { cache: 'no-store' });
      const data = await response.json();
      setStatus(data.capture);
      renderFiles(data.files);
    }

    async function capture() {
      setStatus({ running: true, message: 'Capturing image' });
      const response = await fetch('/api/capture', { method: 'POST' });
      const data = await response.json();
      setStatus(data.capture);
      await loadGallery();
    }

    refreshBtn.addEventListener('click', loadGallery);
    captureBtn.addEventListener('click', capture);
    loadGallery();
    setInterval(loadGallery, 5000);
  </script>
</body>
</html>
"""


def display_time(path: Path) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(path.stat().st_mtime))


def list_capture_files(output_dir: Path) -> list[dict[str, object]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for path in output_dir.iterdir():
        if path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS:
            stat = path.stat()
            files.append(
                {
                    "name": path.name,
                    "size": stat.st_size,
                    "modified": display_time(path),
                    "mtime": stat.st_mtime,
                }
            )
    return sorted(files, key=lambda item: item["mtime"], reverse=True)


def safe_media_path(output_dir: Path, raw_name: str) -> Path | None:
    name = Path(unquote(raw_name)).name
    path = (output_dir / name).resolve()
    try:
        path.relative_to(output_dir.resolve())
    except ValueError:
        return None
    if not path.is_file() or path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return None
    return path


def start_capture(config_path: Path) -> None:
    def worker() -> None:
        with capture_lock:
            capture_state.update(
                {
                    "running": True,
                    "ok": True,
                    "message": "Capturing image",
                    "started_at": time.time(),
                    "finished_at": None,
                }
            )
            try:
                run_capture(config_path)
            except Exception as exc:  # noqa: BLE001 - shown in local camera UI.
                capture_state.update(
                    {
                        "running": False,
                        "ok": False,
                        "message": f"Capture failed: {exc}",
                        "finished_at": time.time(),
                    }
                )
            else:
                capture_state.update(
                    {
                        "running": False,
                        "ok": True,
                        "message": "Capture complete",
                        "finished_at": time.time(),
                    }
                )

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


class GalleryHandler(BaseHTTPRequestHandler):
    server_version = "WigglegramGallery/1.0"

    @property
    def config_path(self) -> Path:
        return self.server.config_path  # type: ignore[attr-defined]

    @property
    def output_dir(self) -> Path:
        return self.server.output_dir  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    def send_bytes(self, status: HTTPStatus, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        self.send_bytes(
            status,
            "application/json; charset=utf-8",
            json.dumps(payload).encode("utf-8"),
        )

    def send_file(self, path: Path, download: bool) -> None:
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(path.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        if download:
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{html.escape(path.name, quote=True)}"',
            )
        self.end_headers()
        with path.open("rb") as file:
            while chunk := file.read(1024 * 64):
                self.wfile.write(chunk)

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        path = self.path.split("?", 1)[0]
        if path == "/":
            self.send_bytes(HTTPStatus.OK, "text/html; charset=utf-8", INDEX_HTML.encode("utf-8"))
            return

        if path == "/api/files":
            self.send_json({"files": list_capture_files(self.output_dir), "capture": capture_state})
            return

        if path.startswith("/media/"):
            media_path = safe_media_path(self.output_dir, path.removeprefix("/media/"))
            if media_path:
                self.send_file(media_path, download=False)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
            return

        if path.startswith("/download/"):
            media_path = safe_media_path(self.output_dir, path.removeprefix("/download/"))
            if media_path:
                self.send_file(media_path, download=True)
            else:
                self.send_error(HTTPStatus.NOT_FOUND)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API.
        path = self.path.split("?", 1)[0]
        if path != "/api/capture":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if capture_state["running"]:
            self.send_json({"capture": capture_state}, HTTPStatus.CONFLICT)
            return

        start_capture(self.config_path)
        self.send_json({"capture": capture_state}, HTTPStatus.ACCEPTED)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Wigglegram web gallery")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Capture config path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Capture output directory")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), GalleryHandler)
    server.config_path = args.config.resolve()  # type: ignore[attr-defined]
    server.output_dir = args.output_dir.resolve()  # type: ignore[attr-defined]

    print(f"Wigglegram gallery running at http://{args.host}:{args.port}")
    print(f"Open from camera Wi-Fi: http://192.168.50.1:{args.port}")
    print("Press Ctrl+C to stop")
    server.serve_forever()


if __name__ == "__main__":
    main()
