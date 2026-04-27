import os
import zipfile

import pytest

from converter import extract_zip, guess_format, ls_files_r


# ---------------------------------------------------------------------------
# guess_format
# ---------------------------------------------------------------------------

class TestGuessFormat:
    def test_webm_is_video(self):
        assert guess_format("a.webm") == "video"

    def test_webp_is_static(self):
        assert guess_format("a.webp") == "static"

    def test_png_is_static(self):
        assert guess_format("a.png") == "static"

    def test_webm_uppercase_is_static(self):
        # guess_format uses str.endswith, not suffix.lower() — intentionally case-sensitive
        assert guess_format("a.WEBM") == "static"


# ---------------------------------------------------------------------------
# ls_files_r
# ---------------------------------------------------------------------------

class TestLsFilesR:
    def test_empty_directory(self, tmp_path):
        assert ls_files_r(str(tmp_path)) == []

    def test_lists_all_files(self, tmp_path):
        for name in ["a.png", "b.png", "c.png"]:
            (tmp_path / name).write_bytes(b"")
        result = ls_files_r(str(tmp_path))
        assert len(result) == 3

    def test_result_is_sorted(self, tmp_path):
        for name in ["c.png", "a.png", "b.png"]:
            (tmp_path / name).write_bytes(b"")
        result = ls_files_r(str(tmp_path))
        assert result == sorted(result)

    def test_must_have_filter(self, tmp_path):
        (tmp_path / "sticker_001.png").write_bytes(b"")
        (tmp_path / "key_001.png").write_bytes(b"")
        result = ls_files_r(str(tmp_path), must_have=["key"])
        assert len(result) == 1
        assert "key" in result[0]

    def test_must_not_have_filter(self, tmp_path):
        (tmp_path / "sticker_001.png").write_bytes(b"")
        (tmp_path / "key_001.png").write_bytes(b"")
        result = ls_files_r(str(tmp_path), must_not_have=["key"])
        assert len(result) == 1
        assert "sticker" in result[0]

    def test_nonexistent_directory_returns_empty(self, tmp_path):
        assert ls_files_r(str(tmp_path / "nonexistent")) == []


# ---------------------------------------------------------------------------
# extract_zip
# ---------------------------------------------------------------------------

class TestExtractZip:
    def test_valid_zip_extracts_files(self, tmp_path):
        zip_path = tmp_path / "test.zip"
        extract_dir = tmp_path / "extracted"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("sticker_001.png", b"PNG")
            zf.writestr("sticker_002.png", b"PNG")
        result = extract_zip(str(zip_path), str(extract_dir))
        assert len(result) == 2
        assert all(os.path.exists(f) for f in result)

    def test_invalid_file_returns_empty(self, tmp_path):
        bad_file = tmp_path / "not_a_zip.txt"
        bad_file.write_text("this is not a zip file")
        result = extract_zip(str(bad_file), str(tmp_path / "extracted"))
        assert result == []
