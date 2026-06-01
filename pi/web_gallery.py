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

import requests

from wigglegram_phase1 import (
    REQUEST_TIMEOUT_SECONDS,
    Camera,
    configure_camera,
    load_config,
    parse_cameras,
    run as run_capture,
)


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

FRAMESIZES = ["QQVGA", "QVGA", "CIF", "VGA", "SVGA", "XGA", "SXGA", "UXGA"]


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

    .control-panel {
      margin: 18px 0;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 10px 30px rgba(24, 32, 30, 0.08);
      overflow: hidden;
    }

    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 14px;
      padding: 14px;
      border-bottom: 1px solid var(--line);
    }

    .panel-title {
      font-weight: 800;
    }

    .panel-subtitle {
      color: var(--muted);
      font-size: 13px;
      margin-top: 2px;
    }

    .settings-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      padding: 14px;
    }

    .field {
      display: grid;
      gap: 7px;
      min-width: 0;
    }

    .field label {
      color: var(--muted);
      font-size: 12px;
      font-weight: 750;
      text-transform: uppercase;
    }

    .field output {
      color: var(--ink);
      font-size: 12px;
      font-weight: 750;
      margin-left: 5px;
    }

    select, input[type="range"] {
      width: 100%;
    }

    select {
      min-height: 36px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fff;
      color: var(--ink);
      font: inherit;
      padding: 0 10px;
    }

    input[type="range"] {
      accent-color: var(--accent);
    }

    .switches {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
    }

    .switch {
      min-height: 38px;
      border: 1px solid var(--line);
      border-radius: 8px;
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 0 10px;
      font-size: 13px;
      font-weight: 700;
      color: var(--ink);
      background: #fbfcfa;
    }

    .camera-strip {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      padding: 0 14px 14px;
    }

    .camera-pill {
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      color: var(--muted);
      font-size: 13px;
      font-weight: 750;
      background: #fbfcfa;
    }

    .camera-pill.online {
      color: var(--accent-dark);
      border-color: rgba(15, 143, 131, 0.35);
      background: rgba(15, 143, 131, 0.08);
    }

    .camera-pill.offline {
      color: #9b4a36;
      border-color: rgba(229, 111, 79, 0.35);
      background: rgba(229, 111, 79, 0.08);
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

      .settings-grid {
        grid-template-columns: 1fr 1fr;
      }

      .switches {
        grid-template-columns: 1fr 1fr;
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

    <section class="control-panel" aria-label="Camera settings">
      <div class="panel-head">
        <div>
          <div class="panel-title">Camera Settings</div>
          <div class="panel-subtitle">Applies the same profile to every configured camera.</div>
        </div>
        <button id="applySettingsBtn" type="button">Apply to All</button>
      </div>

      <div class="settings-grid">
        <div class="field">
          <label for="framesize">Resolution</label>
          <select id="framesize" data-setting="framesize">
            <option>QQVGA</option>
            <option>QVGA</option>
            <option>CIF</option>
            <option>VGA</option>
            <option selected>SVGA</option>
            <option>XGA</option>
            <option>SXGA</option>
            <option>UXGA</option>
          </select>
        </div>
        <div class="field">
          <label for="quality">JPEG Quality <output id="qualityOut">12</output></label>
          <input id="quality" data-setting="quality" type="range" min="4" max="63" value="12">
        </div>
        <div class="field">
          <label for="brightness">Brightness <output id="brightnessOut">0</output></label>
          <input id="brightness" data-setting="brightness" type="range" min="-2" max="2" value="0">
        </div>
        <div class="field">
          <label for="contrast">Contrast <output id="contrastOut">0</output></label>
          <input id="contrast" data-setting="contrast" type="range" min="-2" max="2" value="0">
        </div>
        <div class="field">
          <label for="saturation">Saturation <output id="saturationOut">0</output></label>
          <input id="saturation" data-setting="saturation" type="range" min="-2" max="2" value="0">
        </div>
        <div class="field">
          <label for="sharpness">Sharpness <output id="sharpnessOut">0</output></label>
          <input id="sharpness" data-setting="sharpness" type="range" min="-2" max="2" value="0">
        </div>
        <div class="field">
          <label for="aec_value">Exposure <output id="aec_valueOut">300</output></label>
          <input id="aec_value" data-setting="aec_value" type="range" min="0" max="1200" value="300">
        </div>
        <div class="field">
          <label for="ae_level">AE Level <output id="ae_levelOut">0</output></label>
          <input id="ae_level" data-setting="ae_level" type="range" min="-2" max="2" value="0">
        </div>
        <div class="field">
          <label for="agc_gain">AGC Gain <output id="agc_gainOut">0</output></label>
          <input id="agc_gain" data-setting="agc_gain" type="range" min="0" max="30" value="0">
        </div>
        <div class="field">
          <label for="gainceiling">Gain Ceiling</label>
          <select id="gainceiling" data-setting="gainceiling">
            <option value="0">2x</option>
            <option value="1">4x</option>
            <option value="2">8x</option>
            <option value="3">16x</option>
            <option value="4">32x</option>
            <option value="5">64x</option>
            <option value="6">128x</option>
          </select>
        </div>
        <div class="field">
          <label for="wb_mode">White Balance</label>
          <select id="wb_mode" data-setting="wb_mode">
            <option value="0">Auto</option>
            <option value="1">Sunny</option>
            <option value="2">Cloudy</option>
            <option value="3">Office</option>
            <option value="4">Home</option>
          </select>
        </div>
        <div class="field">
          <label for="special_effect">Effect</label>
          <select id="special_effect" data-setting="special_effect">
            <option value="0">None</option>
            <option value="1">Negative</option>
            <option value="2">Grayscale</option>
            <option value="3">Red Tint</option>
            <option value="4">Green Tint</option>
            <option value="5">Blue Tint</option>
            <option value="6">Sepia</option>
          </select>
        </div>

        <div class="switches">
          <label class="switch"><input data-setting="awb" type="checkbox" checked> AWB</label>
          <label class="switch"><input data-setting="awb_gain" type="checkbox" checked> AWB Gain</label>
          <label class="switch"><input data-setting="aec" type="checkbox" checked> AEC</label>
          <label class="switch"><input data-setting="aec2" type="checkbox"> AEC DSP</label>
          <label class="switch"><input data-setting="agc" type="checkbox" checked> AGC</label>
          <label class="switch"><input data-setting="bpc" type="checkbox"> BPC</label>
          <label class="switch"><input data-setting="wpc" type="checkbox" checked> WPC</label>
          <label class="switch"><input data-setting="raw_gma" type="checkbox" checked> Raw GMA</label>
          <label class="switch"><input data-setting="lenc" type="checkbox" checked> Lens Correct</label>
          <label class="switch"><input data-setting="vflip" type="checkbox"> V Flip</label>
          <label class="switch"><input data-setting="hmirror" type="checkbox"> H Mirror</label>
          <label class="switch"><input data-setting="dcw" type="checkbox" checked> DCW</label>
          <label class="switch"><input data-setting="colorbar" type="checkbox"> Color Bar</label>
        </div>
      </div>
      <div id="cameraStrip" class="camera-strip"></div>
    </section>

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
    const applySettingsBtn = document.getElementById('applySettingsBtn');
    const cameraStrip = document.getElementById('cameraStrip');
    const settingInputs = Array.from(document.querySelectorAll('[data-setting]'));
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
      applySettingsBtn.disabled = running;
      statusText.textContent = state.message || (running ? 'Capturing' : 'Ready');
    }

    function readSettings() {
      const settings = {};
      settingInputs.forEach((input) => {
        const key = input.dataset.setting;
        if (input.type === 'checkbox') {
          settings[key] = input.checked;
        } else if (input.tagName.toLowerCase() === 'select' && key === 'framesize') {
          settings[key] = input.value;
        } else {
          settings[key] = Number(input.value);
        }
      });
      return settings;
    }

    function writeSettings(settings) {
      settingInputs.forEach((input) => {
        const key = input.dataset.setting;
        if (!(key in settings)) return;
        if (input.type === 'checkbox') {
          input.checked = Boolean(settings[key]);
        } else {
          input.value = settings[key];
        }
        syncOutput(input);
      });
    }

    function syncOutput(input) {
      const output = document.getElementById(`${input.dataset.setting}Out`);
      if (output) output.textContent = input.value;
    }

    function renderCameras(cameras) {
      cameraStrip.innerHTML = '';
      cameras.forEach((camera) => {
        const pill = document.createElement('div');
        pill.className = `camera-pill ${camera.online ? 'online' : 'offline'}`;
        pill.textContent = `${camera.name} ${camera.online ? 'online' : 'offline'}`;
        cameraStrip.appendChild(pill);
      });
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
      previewMeta.textContent = `${formatBytes(file.size)} - ${file.modified}`;
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
            <div class="file-meta">${formatBytes(file.size)} - ${file.modified}</div>
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

    async function loadSettings() {
      const response = await fetch('/api/settings', { cache: 'no-store' });
      const data = await response.json();
      writeSettings(data.settings || {});
      renderCameras(data.cameras || []);
    }

    async function applySettings() {
      applySettingsBtn.disabled = true;
      statusText.textContent = 'Applying settings to all cameras';
      const response = await fetch('/api/settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(readSettings())
      });
      const data = await response.json();
      renderCameras(data.cameras || []);
      statusText.textContent = data.message || 'Settings applied';
      applySettingsBtn.disabled = false;
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
    applySettingsBtn.addEventListener('click', applySettings);
    settingInputs.forEach((input) => input.addEventListener('input', () => syncOutput(input)));
    loadGallery();
    loadSettings();
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


def load_gallery_config(config_path: Path) -> dict[str, object]:
    if not config_path.exists():
        raise FileNotFoundError(f"Missing config file: {config_path}")
    return load_config(config_path)


def write_gallery_config(config_path: Path, config: dict[str, object]) -> None:
    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")


def base_settings(config: dict[str, object]) -> dict[str, object]:
    cameras = config.get("cameras", [])
    if not isinstance(cameras, list) or not cameras:
        return {}
    first = cameras[0]
    if not isinstance(first, dict):
        return {}
    settings = first.get("config", {})
    return dict(settings) if isinstance(settings, dict) else {}


def save_settings_for_all(config_path: Path, settings: dict[str, object]) -> dict[str, object]:
    config = load_gallery_config(config_path)
    cameras = config.get("cameras", [])
    if not isinstance(cameras, list):
        raise ValueError("config.cameras must be a list")

    for camera in cameras:
        if isinstance(camera, dict):
            camera["config"] = dict(settings)

    write_gallery_config(config_path, config)
    return config


def camera_status(camera: Camera) -> dict[str, object]:
    try:
        response = requests.get(
            f"{camera.base_url}/status",
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        body = response.json()
        return {"name": camera.name, "base_url": camera.base_url, "online": True, "status": body}
    except Exception as exc:  # noqa: BLE001 - returned to local camera UI.
        return {
            "name": camera.name,
            "base_url": camera.base_url,
            "online": False,
            "error": str(exc),
        }


def list_cameras(config_path: Path, probe: bool = False) -> list[dict[str, object]]:
    config = load_gallery_config(config_path)
    cameras = parse_cameras(config)
    if probe:
        return [camera_status(camera) for camera in cameras]
    return [{"name": camera.name, "base_url": camera.base_url, "online": False} for camera in cameras]


def broadcast_settings(config_path: Path, settings: dict[str, object]) -> list[dict[str, object]]:
    config = save_settings_for_all(config_path, settings)
    results = []
    for camera in parse_cameras(config):
        try:
            response = configure_camera(Camera(camera.name, camera.base_url, dict(settings)))
            results.append(
                {
                    "name": camera.name,
                    "base_url": camera.base_url,
                    "online": True,
                    "response": response,
                }
            )
        except Exception as exc:  # noqa: BLE001 - returned to local camera UI.
            results.append(
                {
                    "name": camera.name,
                    "base_url": camera.base_url,
                    "online": False,
                    "error": str(exc),
                }
            )
    return results


def read_request_json(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


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

        if path == "/api/settings":
            config = load_gallery_config(self.config_path)
            self.send_json(
                {
                    "settings": base_settings(config),
                    "cameras": list_cameras(self.config_path, probe=True),
                }
            )
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
        if path == "/api/settings":
            try:
                settings = read_request_json(self)
                results = broadcast_settings(self.config_path, settings)
            except Exception as exc:  # noqa: BLE001 - returned to local camera UI.
                self.send_json({"message": f"Settings failed: {exc}"}, HTTPStatus.BAD_REQUEST)
                return

            online_count = sum(1 for result in results if result.get("online"))
            self.send_json(
                {
                    "message": f"Settings applied to {online_count}/{len(results)} cameras",
                    "settings": settings,
                    "cameras": results,
                }
            )
            return

        if path == "/api/capture":
            if capture_state["running"]:
                self.send_json({"capture": capture_state}, HTTPStatus.CONFLICT)
                return

            start_capture(self.config_path)
            self.send_json({"capture": capture_state}, HTTPStatus.ACCEPTED)
            return

        self.send_error(HTTPStatus.NOT_FOUND)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Wigglegram web gallery")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Capture config path")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Capture output directory")
    args = parser.parse_args()

    try:
        server = ThreadingHTTPServer((args.host, args.port), GalleryHandler)
    except OSError as exc:
        if exc.errno == 98:
            print(f"Port {args.port} is already in use.")
            print("A gallery server may already be running.")
            print()
            print(f"Try opening: http://192.168.50.1:{args.port}")
            print()
            print("Or stop the existing process:")
            print(f"  sudo lsof -i :{args.port}")
            print("  kill <PID>")
            print()
            print("Or start on another port:")
            print("  python web_gallery.py --port 8081 --config config.json --output-dir captures")
            raise SystemExit(1) from exc
        raise
    server.config_path = args.config.resolve()  # type: ignore[attr-defined]
    server.output_dir = args.output_dir.resolve()  # type: ignore[attr-defined]

    print(f"Wigglegram gallery running at http://{args.host}:{args.port}")
    print(f"Open from camera Wi-Fi: http://192.168.50.1:{args.port}")
    print("Press Ctrl+C to stop")
    server.serve_forever()


if __name__ == "__main__":
    main()
