#!/usr/bin/env python3
from __future__ import annotations

import logging
import os
from typing import Optional

from telethon import TelegramClient
from telethon.tl.functions.messages import UploadMediaRequest
from telethon.tl.functions.stickers import AddStickerToSetRequest, CreateStickerSetRequest
from telethon.tl.types import (
    DocumentAttributeFilename,
    InputDocument,
    InputMediaUploadedDocument,
    InputPeerSelf,
    InputStickerSetItem,
    InputStickerSetShortName,
)

logger = logging.getLogger(__name__)

SESSION_FILE = os.path.join(os.path.dirname(__file__), "msb_create")
DEFAULT_KEYWORDS = ["sticker", "moe_sticker_bot", "moe"]


def make_client(api_id: int, api_hash: str) -> TelegramClient:
    return TelegramClient(SESSION_FILE, api_id, api_hash)


async def ensure_connected(client: TelegramClient, phone: Optional[str] = None) -> None:
    await client.start(phone=phone)


async def upload_sticker_document(client: TelegramClient, file_path: str, fmt: str) -> InputDocument:
    mime = "image/webp" if fmt == "static" else "video/webm"
    fname = os.path.basename(file_path)

    logger.debug("Uploading %s ...", fname)
    uploaded = await client.upload_file(file_path)

    result = await client(UploadMediaRequest(
        peer=InputPeerSelf(),
        media=InputMediaUploadedDocument(
            file=uploaded,
            mime_type=mime,
            attributes=[DocumentAttributeFilename(file_name=fname)],
        ),
    ))

    doc = result.document
    return InputDocument(
        id=doc.id,
        access_hash=doc.access_hash,
        file_reference=doc.file_reference,
    )


async def create_sticker_set(
    client: TelegramClient,
    title: str,
    short_name: str,
    converted_files: list[tuple[str, str]],  # [(path, fmt), ...]
    default_emoji: str = "⭐",
    is_custom_emoji: bool = False,
) -> str:
    logger.info("Uploading %d sticker file(s)...", len(converted_files))

    items = []
    for path, fmt in converted_files:
        try:
            doc = await upload_sticker_document(client, path, fmt)
            items.append(InputStickerSetItem(document=doc, emoji=default_emoji))
            logger.info("Uploaded: %s", os.path.basename(path))
        except Exception as exc:
            logger.error("Failed to upload %s: %s", path, exc)

    if not items:
        raise RuntimeError("No stickers uploaded successfully.")

    logger.info("Creating sticker set '%s' (%d sticker(s))...", title, len(items))
    result = await client(CreateStickerSetRequest(
        user_id=InputPeerSelf(),
        title=title,
        short_name=short_name,
        stickers=items,
        emojis=is_custom_emoji,
    ))

    logger.info("Sticker set created.")
    return result.set.short_name


async def add_stickers_to_set(
    client: TelegramClient,
    short_name: str,
    converted_files: list[tuple[str, str]],
    default_emoji: str = "⭐",
) -> None:
    sticker_set = InputStickerSetShortName(short_name=short_name)

    for i, (path, fmt) in enumerate(converted_files, start=1):
        logger.info("Adding sticker %d/%d: %s", i, len(converted_files), os.path.basename(path))
        try:
            doc = await upload_sticker_document(client, path, fmt)
            item = InputStickerSetItem(document=doc, emoji=default_emoji)
            await client(AddStickerToSetRequest(stickerset=sticker_set, sticker=item))
        except Exception as exc:
            logger.error("Failed to add %s: %s", path, exc)
