#!/usr/bin/env python3
"""First phase Raspberry Pi controller for one ESP32-CAM."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from PIL import Image


REQUEST_TIMEOUT_SECONDS = 15


@dataclass(frozen=True)
class Camera:
    name: str
    base_url: str
    config: dict[str, Any]


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def request_json(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    response = requests.request(
        method,
        url,
        timeout=REQUEST_TIMEOUT_SECONDS,
        **kwargs,
    )
    response.raise_for_status()
    return response.json()


def check_status(camera: Camera) -> dict[str, Any]:
    return request_json("GET", f"{camera.base_url}/status")


def configure_camera(camera: Camera) -> dict[str, Any]:
    return request_json("POST", f"{camera.base_url}/config", json=camera.config)


def capture_jpeg(camera: Camera, output_path: Path) -> None:
    response = requests.get(
        f"{camera.base_url}/capture",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    content_type = response.headers.get("content-type", "")
    if "image/jpeg" not in content_type:
        raise RuntimeError(
            f"{camera.name} returned {content_type or 'unknown content type'}, expected image/jpeg"
        )

    output_path.write_bytes(response.content)


def make_gif(image_paths: list[Path], output_path: Path, duration_ms: int) -> None:
    if not image_paths:
        raise ValueError("At least one image is required to make a GIF")

    frames = [Image.open(path).convert("RGB") for path in image_paths]
    first, rest = frames[0], frames[1:]
    first.save(
        output_path,
        save_all=True,
        append_images=rest,
        duration=duration_ms,
        loop=0,
    )

    for frame in frames:
        frame.close()


def parse_cameras(raw_config: dict[str, Any]) -> list[Camera]:
    cameras = []
    for item in raw_config["cameras"]:
        cameras.append(
            Camera(
                name=item["name"],
                base_url=item["base_url"].rstrip("/"),
                config=item.get("config", {}),
            )
        )
    return cameras


def run(config_path: Path) -> None:
    config_path = config_path.resolve()
    raw_config = load_config(config_path)
    cameras = parse_cameras(raw_config)
    output_dir = Path(raw_config.get("output_dir", "captures"))
    if not output_dir.is_absolute():
        output_dir = config_path.parent / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    if len(cameras) != 1:
        raise RuntimeError("Phase 1 expects exactly one camera in the config file")

    camera = cameras[0]

    print(f"Checking {camera.name} at {camera.base_url}")
    status = check_status(camera)
    print(f"Camera status: {status}")

    print("Sending camera configuration")
    config_response = configure_camera(camera)
    print(f"Config response: {config_response}")

    jpg_path = output_dir / "latest.jpg"
    print(f"Capturing JPEG to {jpg_path}")
    capture_jpeg(camera, jpg_path)

    gif_path = output_dir / "wiggle.gif"
    duration_ms = int(raw_config.get("gif", {}).get("duration_ms", 140))
    print(f"Creating GIF at {gif_path}")
    make_gif([jpg_path], gif_path, duration_ms)

    print("Done")


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture from one ESP32-CAM")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.json"),
        help="Path to JSON config file",
    )
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
