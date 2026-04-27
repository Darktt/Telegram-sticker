"""
line_downloader - Fetch LINE sticker pack info and download the ZIP.

Ports the logic from tools/line_dlink.sh to Python for seamless integration.
"""

import json
import logging
import os
import re
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-Hant;q=0.9, ja;q=0.8, en;q=0.7",
}

_STICKERSHOP_BASE = "https://stickershop.line-scdn.net/stickershop/v1/product/{id}/iphone"
_STICONSHOP_BASE = "https://stickershop.line-scdn.net/sticonshop/v1/sticon/{id}/iphone"


class LineDownloadError(RuntimeError):
    pass


class LineUnsupportedTypeError(LineDownloadError):
    pass


@dataclass
class LinePackInfo:
    id: str
    title: str
    store_url: str
    category: str
    zip_url: str


def _parse_first_script(soup: BeautifulSoup) -> dict:
    tag = soup.find("script")
    if not tag or not tag.string:
        return {}
    try:
        return json.loads(tag.string.strip())
    except (json.JSONDecodeError, ValueError):
        return {}


def _extract_id_and_url(html: str, soup: BeautifulSoup) -> tuple[str, str]:
    data = _parse_first_script(soup)
    pack_id = str(data.get("sku", "")).strip()
    store_url = str(data.get("url", "")).strip()

    if not store_url:
        tag = soup.find("meta", attrs={"property": "og:url"})
        if tag:
            store_url = tag.get("content", "").strip()

    if not pack_id:
        tag = soup.find("link", attrs={"hreflang": "x-default"})
        if tag:
            href = tag.get("href", "")
            pack_id = os.path.basename(href.rstrip("/"))

    if not pack_id or not store_url:
        raise LineDownloadError("could not extract sticker ID or URL from page")

    return pack_id, store_url


def _classify_stickershop(html: str, pack_id: str) -> tuple[str, str]:
    base = _STICKERSHOP_BASE.format(id=pack_id)

    if re.search(r"MdIcoPlay_b|MdIcoAni_b", html):
        return "animated", f"{base}/stickerpack@2x.zip"

    if "MdIcoMessageSticker_b" in html:
        raise LineUnsupportedTypeError(
            "message stickers require per-sticker API and are not supported"
        )

    if "MdIcoNameSticker_b" in html:
        return "name", f"{base}/sticker_name_base@2x.zip"

    if re.search(r"MdIcoFlash_b|MdIcoFlashAni_b", html):
        return "popup", f"{base}/stickerpack@2x.zip"

    if re.search(r"MdIcoEffectSoundSticker_b|MdIcoEffectSticker_b", html):
        return "popup", f"{base}/stickerpack@2x.zip"

    # Static stickers — IDs before 775 use CgBI-encoded PNGs on iPhone;
    # the Android ZIP uses standard PNG that ImageMagick can read.
    try:
        if int(pack_id) < 775:
            android_url = (
                f"https://stickershop.line-scdn.net/stickershop/v1/product/{pack_id}"
                "/android/stickers.zip"
            )
            return "static", android_url
    except ValueError:
        pass

    return "static", f"{base}/stickers@2x.zip"


def _classify_emojishop(html: str, pack_id: str) -> tuple[str, str]:
    base = _STICONSHOP_BASE.format(id=pack_id)
    if "MdIcoPlay_b" in html:
        return "emoji_animated", f"{base}/package_animation.zip"
    return "emoji_static", f"{base}/package.zip"


def fetch_line_info(url: str) -> LinePackInfo:
    logging.debug("Fetching LINE page: %s", url)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise LineDownloadError(f"HTTP request failed: {exc}") from exc

    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    data = _parse_first_script(soup)
    title = str(data.get("name", "")).strip()

    pack_id, store_url = _extract_id_and_url(html, soup)
    logging.debug("Pack ID: %s  Store URL: %s", pack_id, store_url)

    if re.search(r"stickershop|officialaccount/event/sticker", store_url):
        category, zip_url = _classify_stickershop(html, pack_id)
    elif "emojishop" in store_url:
        category, zip_url = _classify_emojishop(html, pack_id)
    else:
        raise LineDownloadError(f"unknown LINE store category (URL: {store_url})")

    if not title:
        raise LineDownloadError(
            "could not determine sticker pack title; please specify -n"
        )

    logging.info("LINE pack: %r  category=%s  id=%s", title, category, pack_id)
    return LinePackInfo(
        id=pack_id,
        title=title,
        store_url=store_url,
        category=category,
        zip_url=zip_url,
    )


def download_zip(zip_url: str, dest_dir: str) -> str:
    dest_path = os.path.join(dest_dir, "line_stickers.zip")
    logging.info("Downloading: %s", zip_url)
    try:
        resp = requests.get(zip_url, headers=HEADERS, stream=True, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise LineDownloadError(f"ZIP download failed: {exc}") from exc

    with open(dest_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)

    size_kb = os.path.getsize(dest_path) // 1024
    logging.info("Downloaded %d KiB → %s", size_kb, dest_path)
    return dest_path
