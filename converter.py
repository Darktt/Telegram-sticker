#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import logging
from typing import Optional

logger = logging.getLogger(__name__)

FFMPEG_BIN = "ffmpeg"
BSDTAR_BIN = "bsdtar"
CONVERT_BIN = "convert"
IDENTIFY_BIN = "identify"
CONVERT_ARGS: list[str] = []
IDENTIFY_ARGS: list[str] = []

MAX_SIZE = 255 * 1024  # 255 KiB


def init_convert():
    global CONVERT_BIN, IDENTIFY_BIN, CONVERT_ARGS, IDENTIFY_ARGS
    if platform.system() != "Linux":
        CONVERT_BIN = "magick"
        IDENTIFY_BIN = "magick"
        CONVERT_ARGS = ["convert"]
        IDENTIFY_ARGS = ["identify"]

    missing = []
    for tool in [FFMPEG_BIN, CONVERT_BIN, IDENTIFY_BIN, BSDTAR_BIN]:
        if shutil.which(tool) is None:
            missing.append(tool)
    if missing:
        logger.warning("Missing tools in PATH: %s", ", ".join(missing))


def identify_frames(f: str) -> int:
    try:
        args = [IDENTIFY_BIN] + IDENTIFY_ARGS + ["-format", "%n", f]
        result = subprocess.run(args, capture_output=True, text=True, timeout=30)
        text = result.stdout.strip()
        # identify may print one number per frame; take the first
        return int(text.split()[0]) if text else 1
    except Exception:
        return 1


def im_to_webp_static(f: str, is_emoji: bool = False) -> str:
    output = f + ".webp"

    if is_emoji:
        scale_args = [
            "-resize", "100x100",
            "-gravity", "center",
            "-extent", "100x100",
            "-background", "none",
        ]
    else:
        scale_args = ["-resize", "512x512"]

    def run_convert(extra_args: list[str]) -> bool:
        args = (
            [CONVERT_BIN] + CONVERT_ARGS
            + scale_args
            + ["-filter", "Lanczos"]
            + extra_args
            + [f + "[0]", output]
        )
        result = subprocess.run(args, capture_output=True)
        return result.returncode == 0

    run_convert(["-define", "webp:lossless=true"])

    if os.path.exists(output) and os.path.getsize(output) > MAX_SIZE:
        logger.debug("Lossless WEBP too large, retrying without lossless: %s", f)
        run_convert([])

    return output


def ff_to_webm_video(f: str, is_emoji: bool = False) -> str:
    output = f + ".webm"
    scale = "100:100" if is_emoji else "512:512"
    scale_filter = f"scale={scale}:force_original_aspect_ratio=decrease"

    bitrate_levels = [
        ["-minrate", "50k", "-b:v", "350k", "-maxrate", "450k"],
        ["-minrate", "50k", "-b:v", "200k", "-maxrate", "300k"],
        ["-minrate", "20k", "-b:v", "100k", "-maxrate", "200k"],
        ["-minrate", "10k", "-b:v", "50k",  "-maxrate", "100k"],
    ]

    for level in bitrate_levels:
        args = (
            [FFMPEG_BIN, "-hide_banner", "-i", f,
             "-vf", scale_filter,
             "-pix_fmt", "yuva420p",
             "-c:v", "libvpx-vp9",
             "-cpu-used", "5"]
            + level
            + ["-to", "00:00:03", "-an", "-y", output]
        )
        subprocess.run(args, capture_output=True)

        if os.path.exists(output) and os.path.getsize(output) <= MAX_SIZE:
            return output

        logger.debug("WEBM quality level %s too large, retrying lower bitrate", level)

    return output


def convert_to_tg_sticker(f: str, is_emoji: bool = False) -> tuple[str, str]:
    frames = identify_frames(f)
    if frames > 1:
        converted = ff_to_webm_video(f, is_emoji)
        return converted, "video"
    else:
        converted = im_to_webp_static(f, is_emoji)
        return converted, "static"


def guess_format(f: str) -> str:
    return "video" if f.endswith(".webm") else "static"


def extract_zip(zip_path: str, dest_dir: str) -> list[str]:
    os.makedirs(dest_dir, exist_ok=True)
    result = subprocess.run(
        [BSDTAR_BIN, "-xvf", zip_path, "-C", dest_dir],
        capture_output=True,
    )
    if result.returncode != 0:
        logger.error("bsdtar extraction failed: %s", result.stderr.decode(errors="replace"))
        return []
    return ls_files_r(dest_dir)


def ls_files_r(directory: str, must_have: Optional[list[str]] = None, must_not_have: Optional[list[str]] = None) -> list[str]:
    must_have = must_have or []
    must_not_have = must_not_have or []
    results = []
    for root, _, files in os.walk(directory):
        for name in files:
            path = os.path.join(root, name)
            lower = path.lower()
            if all(kw.lower() in lower for kw in must_have) and \
               not any(kw.lower() in lower for kw in must_not_have):
                results.append(path)
    return sorted(results)
