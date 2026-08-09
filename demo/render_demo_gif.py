#!/usr/bin/env python3
"""Render an animated GIF from the real MCP demo terminal output."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
DEMO_SCRIPT = REPO_ROOT / "demo" / "run_mcp_demo.py"
OUTPUT_GIF = REPO_ROOT / "docs" / "demo" / "capcut-openclaw-demo.gif"
WIDTH = 1280
HEIGHT = 720
PADDING = 40
LINE_HEIGHT = 28
VISIBLE_LINES = 18


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def render_frame(lines: list[str], body_font, title_font) -> Image.Image:
    image = Image.new("RGB", (WIDTH, HEIGHT), "#081018")
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((24, 24, WIDTH - 24, HEIGHT - 24), radius=24, fill="#0F172A")
    draw.rounded_rectangle((24, 24, WIDTH - 24, 96), radius=24, fill="#111827")
    draw.text((48, 44), "CapCutAPI x OpenClaw MCP Demo", font=title_font, fill="#E5E7EB")
    draw.text((48, 80), "Generated from the real demo command", font=body_font, fill="#93C5FD")

    y = 128
    for line in lines[-VISIBLE_LINES:]:
        draw.text((PADDING, y), f"$ {line}" if y == 128 else line, font=body_font, fill="#D1D5DB")
        y += LINE_HEIGHT

    return image


def main() -> int:
    OUTPUT_GIF.parent.mkdir(parents=True, exist_ok=True)

    run = subprocess.run(
        [sys.executable, str(DEMO_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    output_lines = [line.rstrip() for line in run.stdout.splitlines() if line.strip()]
    if run.stderr.strip():
        output_lines.append("stderr:")
        output_lines.extend(line.rstrip() for line in run.stderr.splitlines() if line.strip())
    if run.returncode != 0:
        raise SystemExit(run.returncode)

    body_font = load_font(24)
    title_font = load_font(30)

    frames: list[Image.Image] = []
    durations: list[int] = []
    progressive: list[str] = []

    for line in output_lines:
        progressive.append(line)
        frames.append(render_frame(progressive, body_font, title_font))
        durations.append(900)

    for _ in range(3):
        frames.append(render_frame(progressive + ["Demo ready for README"], body_font, title_font))
        durations.append(1200)

    frames[0].save(
        OUTPUT_GIF,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=False,
    )

    print(f"Wrote {OUTPUT_GIF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
