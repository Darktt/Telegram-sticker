#!/usr/bin/env python3
"""
msb_create - Create Telegram sticker sets from local image files.

Based on moe-sticker-bot's sticker creation and conversion logic.
Uses the Telegram user client API (MTProto) via Telethon.

Usage:
  python msb_create.py -i ./images/ -n "My Pack"
  python msb_create.py -i pack.zip  -n "My Pack" --custom_emoji
"""

import argparse
import asyncio
import logging
import os
import re
import secrets
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from converter import convert_to_tg_sticker, extract_zip, guess_format, init_convert, ls_files_r
from tg_api import add_stickers_to_set, create_sticker_set, ensure_connected, make_client

load_dotenv()

SUPPORTED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".apng", ".webp", ".bmp"}
ALREADY_CONVERTED_EXTS = {".webp", ".webm"}
BATCH_LIMIT = 120  # Telegram MTProto sticker set limit


def collect_input_files(input_path: str, tmp_dir: str) -> list[str]:
    p = Path(input_path)
    if not p.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    all_exts = SUPPORTED_EXTS | ALREADY_CONVERTED_EXTS

    if p.is_file():
        suffix = p.suffix.lower()
        if suffix in (".zip", ".cbz", ".tar", ".tgz", ".tar.gz"):
            dest = os.path.join(tmp_dir, "extracted")
            files = extract_zip(str(p), dest)
            return [f for f in files if Path(f).suffix.lower() in all_exts]
        elif suffix in all_exts:
            return [str(p)]
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    if p.is_dir():
        all_files = ls_files_r(str(p))
        return sorted([f for f in all_files if Path(f).suffix.lower() in all_exts])

    raise ValueError(f"Input is neither a file nor a directory: {input_path}")


def generate_set_name(title: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9]", "_", title).strip("_")
    sanitized = re.sub(r"_+", "_", sanitized)
    suffix = secrets.token_hex(3)          # 6 hex chars for uniqueness
    max_base = 64 - len(suffix) - 1        # -1 for the joining underscore
    base = sanitized[:max_base].rstrip("_")
    return f"{base}_{suffix}" if base else suffix


async def run(args: argparse.Namespace, api_id: int, api_hash: str, phone: str) -> None:
    init_convert()

    tmp_dir = tempfile.mkdtemp(prefix="msb_create_")
    try:
        input_files = collect_input_files(args.input, tmp_dir)
        if not input_files:
            logging.error("No supported image files found in: %s", args.input)
            sys.exit(1)
        logging.info("Found %d input file(s).", len(input_files))

        converted: list[tuple[str, str]] = []
        for f in input_files:
            suffix = Path(f).suffix.lower()
            if suffix in ALREADY_CONVERTED_EXTS:
                converted.append((f, guess_format(f)))
                logging.info("Using pre-converted: %s", f)
            else:
                logging.info("Converting: %s", f)
                try:
                    path, fmt = convert_to_tg_sticker(f, args.custom_emoji)
                    converted.append((path, fmt))
                except Exception as exc:
                    logging.error("Conversion failed for %s: %s", f, exc)

        if not converted:
            logging.error("All conversions failed. Aborting.")
            sys.exit(1)

        set_name = args.name or generate_set_name(args.title)
        logging.info("Sticker set name : %s", set_name)
        logging.info("Sticker set title: %s", args.title)

        async with make_client(api_id, api_hash) as client:
            await ensure_connected(client, phone=phone)

            first_batch = converted[:BATCH_LIMIT]
            rest = converted[BATCH_LIMIT:]

            actual_name = await create_sticker_set(
                client,
                title=args.title,
                short_name=set_name,
                converted_files=first_batch,
                default_emoji=args.emoji,
                is_custom_emoji=args.custom_emoji,
            )

            if rest:
                logging.info("Adding %d remaining sticker(s)...", len(rest))
                await add_stickers_to_set(
                    client,
                    short_name=actual_name,
                    converted_files=rest,
                    default_emoji=args.emoji,
                )

        print(f"\nDone! View your sticker set:\nhttps://t.me/addstickers/{actual_name}\n")

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Telegram sticker set from local image files."
    )
    parser.add_argument("-i", "--input", required=True,
                        help="Image directory, single image file, or ZIP archive")
    parser.add_argument("-n", "--title", required=True,
                        help="Sticker set title (1-64 characters)")
    parser.add_argument("-s", "--name",
                        help="Sticker set short name (auto-generated if omitted)")
    parser.add_argument("-e", "--emoji", default="⭐",
                        help="Default emoji for all stickers (default: ⭐)")
    parser.add_argument("--custom_emoji", action="store_true",
                        help="Create as Custom Emoji set (100×100 format)")
    parser.add_argument("--log_level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                        help="Logging verbosity (default: INFO)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    api_id_str = os.environ.get("API_ID")
    api_hash = os.environ.get("API_HASH")
    phone = os.environ.get("PHONE")

    if not api_id_str:
        logging.error("API_ID is required. Set it in .env.")
        sys.exit(1)
    if not api_hash:
        logging.error("API_HASH is required. Set it in .env.")
        sys.exit(1)

    asyncio.run(run(args, int(api_id_str), api_hash, phone))


if __name__ == "__main__":
    main()
