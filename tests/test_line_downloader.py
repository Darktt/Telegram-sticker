import pytest
from unittest.mock import MagicMock
from bs4 import BeautifulSoup

from line_downloader import (
    LineDownloadError,
    LinePackInfo,
    LineUnsupportedTypeError,
    _classify_emojishop,
    _classify_stickershop,
    _parse_first_script,
    download_zip,
    fetch_line_info,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def _stickershop_html(pack_id: str, title: str, extra: str = "") -> str:
    return (
        f'<html><head>'
        f'<script>{{"name":"{title}","sku":"{pack_id}",'
        f'"url":"https://store.line.me/stickershop/product/{pack_id}"}}</script>'
        f'</head><body>{extra}</body></html>'
    )


def _emojishop_html(pack_id: str, title: str, extra: str = "") -> str:
    return (
        f'<html><head>'
        f'<script>{{"name":"{title}","sku":"{pack_id}",'
        f'"url":"https://store.line.me/emojishop/product/{pack_id}"}}</script>'
        f'</head><body>{extra}</body></html>'
    )


def _mock_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.text = html
    resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# _parse_first_script
# ---------------------------------------------------------------------------

class TestParseFirstScript:
    def test_valid_json(self):
        result = _parse_first_script(_soup('<script>{"sku":"123","name":"Test"}</script>'))
        assert result == {"sku": "123", "name": "Test"}

    def test_no_script_tag(self):
        assert _parse_first_script(_soup("<html><body></body></html>")) == {}

    def test_empty_script(self):
        assert _parse_first_script(_soup("<script></script>")) == {}

    def test_non_json_script(self):
        assert _parse_first_script(_soup("<script>alert(1);</script>")) == {}


# ---------------------------------------------------------------------------
# _classify_stickershop
# ---------------------------------------------------------------------------

class TestClassifyStickershop:
    def test_animated_play(self):
        cat, url = _classify_stickershop('class="MdIcoPlay_b"', "1000")
        assert cat == "animated"
        assert "stickerpack@2x.zip" in url

    def test_animated_ani(self):
        cat, url = _classify_stickershop('class="MdIcoAni_b"', "1000")
        assert cat == "animated"
        assert "stickerpack@2x.zip" in url

    def test_message_sticker_unsupported(self):
        with pytest.raises(LineUnsupportedTypeError):
            _classify_stickershop('class="MdIcoMessageSticker_b"', "1000")

    def test_name_sticker(self):
        cat, url = _classify_stickershop('class="MdIcoNameSticker_b"', "1000")
        assert cat == "name"
        assert "sticker_name_base@2x.zip" in url

    def test_popup_flash(self):
        cat, url = _classify_stickershop('class="MdIcoFlash_b"', "1000")
        assert cat == "popup"
        assert "stickerpack@2x.zip" in url

    def test_effect_sticker(self):
        cat, url = _classify_stickershop('class="MdIcoEffectSticker_b"', "1000")
        assert cat == "popup"
        assert "stickerpack@2x.zip" in url

    def test_static_high_id(self):
        cat, url = _classify_stickershop("", "1000")
        assert cat == "static"
        assert "iphone" in url
        assert "stickers@2x.zip" in url

    def test_static_low_id(self):
        cat, url = _classify_stickershop("", "100")
        assert cat == "static"
        assert "android" in url

    def test_static_boundary_id_775(self):
        cat, url = _classify_stickershop("", "775")
        assert cat == "static"
        assert "iphone" in url
        assert "stickers@2x.zip" in url


# ---------------------------------------------------------------------------
# _classify_emojishop
# ---------------------------------------------------------------------------

class TestClassifyEmojishop:
    def test_animated_emoji(self):
        cat, url = _classify_emojishop('class="MdIcoPlay_b"', "999")
        assert cat == "emoji_animated"
        assert "package_animation.zip" in url

    def test_static_emoji(self):
        cat, url = _classify_emojishop("", "999")
        assert cat == "emoji_static"
        assert "package.zip" in url
        assert "package_animation.zip" not in url


# ---------------------------------------------------------------------------
# fetch_line_info
# ---------------------------------------------------------------------------

class TestFetchLineInfo:
    def test_http_error_raises(self, mocker):
        import requests
        mocker.patch("line_downloader.requests.get", side_effect=requests.HTTPError("404"))
        with pytest.raises(LineDownloadError):
            fetch_line_info("https://store.line.me/stickershop/product/123")

    def test_timeout_raises(self, mocker):
        import requests
        mocker.patch("line_downloader.requests.get", side_effect=requests.Timeout())
        with pytest.raises(LineDownloadError):
            fetch_line_info("https://store.line.me/stickershop/product/123")

    def test_message_sticker_raises(self, mocker):
        html = _stickershop_html("123", "Test", '<span class="MdIcoMessageSticker_b">')
        mocker.patch("line_downloader.requests.get", return_value=_mock_response(html))
        with pytest.raises(LineUnsupportedTypeError):
            fetch_line_info("https://store.line.me/stickershop/product/123")

    def test_empty_title_raises(self, mocker):
        html = _stickershop_html("123", "")
        mocker.patch("line_downloader.requests.get", return_value=_mock_response(html))
        with pytest.raises(LineDownloadError):
            fetch_line_info("https://store.line.me/stickershop/product/123")

    def test_no_id_url_raises(self, mocker):
        mocker.patch(
            "line_downloader.requests.get",
            return_value=_mock_response("<html><body>empty</body></html>"),
        )
        with pytest.raises(LineDownloadError):
            fetch_line_info("https://store.line.me/stickershop/product/123")

    def test_stickershop_static_success(self, mocker):
        html = _stickershop_html("1000", "My Stickers")
        mocker.patch("line_downloader.requests.get", return_value=_mock_response(html))
        info = fetch_line_info("https://store.line.me/stickershop/product/1000")
        assert isinstance(info, LinePackInfo)
        assert info.id == "1000"
        assert info.title == "My Stickers"
        assert info.category == "static"
        assert "stickers@2x.zip" in info.zip_url

    def test_emojishop_success(self, mocker):
        html = _emojishop_html("999", "My Emoji")
        mocker.patch("line_downloader.requests.get", return_value=_mock_response(html))
        info = fetch_line_info("https://store.line.me/emojishop/product/999")
        assert info.category.startswith("emoji_")

    def test_unknown_store_raises(self, mocker):
        html = (
            '<html><head>'
            '<script>{"name":"Test","sku":"123","url":"https://other.line.me/shop/123"}</script>'
            '</head></html>'
        )
        mocker.patch("line_downloader.requests.get", return_value=_mock_response(html))
        with pytest.raises(LineDownloadError):
            fetch_line_info("https://other.line.me/shop/123")


# ---------------------------------------------------------------------------
# download_zip
# ---------------------------------------------------------------------------

class TestDownloadZip:
    def test_success_creates_file(self, tmp_path, mocker):
        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"PK\x03\x04fake"]
        mock_resp.raise_for_status.return_value = None
        mocker.patch("line_downloader.requests.get", return_value=mock_resp)
        result = download_zip("https://example.com/stickers.zip", str(tmp_path))
        assert result.endswith("line_stickers.zip")
        assert (tmp_path / "line_stickers.zip").exists()

    def test_http_error_raises(self, tmp_path, mocker):
        import requests
        mocker.patch("line_downloader.requests.get", side_effect=requests.HTTPError("403"))
        with pytest.raises(LineDownloadError):
            download_zip("https://example.com/stickers.zip", str(tmp_path))
