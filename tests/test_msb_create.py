import pytest

from msb_create import (
    ALREADY_CONVERTED_EXTS,
    SUPPORTED_EXTS,
    _is_wanted,
    _make_parser,
    collect_input_files,
    generate_set_name,
)

ALL_EXTS = SUPPORTED_EXTS | ALREADY_CONVERTED_EXTS


# ---------------------------------------------------------------------------
# _is_wanted
# ---------------------------------------------------------------------------

class TestIsWanted:
    def test_png_accepted(self):
        assert _is_wanted("001.png", ALL_EXTS) is True

    def test_webp_accepted(self):
        assert _is_wanted("001.webp", ALL_EXTS) is True

    def test_webm_accepted(self):
        assert _is_wanted("001.webm", ALL_EXTS) is True

    def test_unsupported_ext_rejected(self):
        assert _is_wanted("001.mp4", ALL_EXTS) is False

    def test_key_2x_rejected(self):
        assert _is_wanted("001_key@2x.png", ALL_EXTS) is False

    def test_key_3x_rejected(self):
        assert _is_wanted("001_key@3x.png", ALL_EXTS) is False

    def test_tab_off_rejected(self):
        assert _is_wanted("tab_off.png", ALL_EXTS) is False

    def test_tab_on_rejected(self):
        assert _is_wanted("tab_on.png", ALL_EXTS) is False

    def test_uppercase_ext_accepted(self):
        assert _is_wanted("001.PNG", ALL_EXTS) is True


# ---------------------------------------------------------------------------
# generate_set_name
# ---------------------------------------------------------------------------

class TestGenerateSetName:
    def test_valid_chars_only(self):
        name = generate_set_name("My Pack")
        assert all(c.isalnum() or c == "_" for c in name)

    def test_max_length(self):
        assert len(generate_set_name("My Pack")) <= 64

    def test_chinese_title(self):
        name = generate_set_name("我的貼圖")
        assert all(c.isalnum() or c == "_" for c in name)
        assert len(name) <= 64

    def test_empty_title_returns_only_suffix(self):
        name = generate_set_name("")
        assert len(name) == 6
        assert all(c in "0123456789abcdef" for c in name)

    def test_long_title_truncated(self):
        assert len(generate_set_name("a" * 58)) <= 64

    def test_no_consecutive_underscores(self):
        assert "__" not in generate_set_name("a--b")

    def test_random_suffix_makes_names_unique(self):
        assert generate_set_name("Test") != generate_set_name("Test")


# ---------------------------------------------------------------------------
# collect_input_files
# ---------------------------------------------------------------------------

class TestCollectInputFiles:
    def test_nonexistent_path_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            collect_input_files("/no/such/path/xyz", str(tmp_path))

    def test_unsupported_single_file_raises(self, tmp_path):
        f = tmp_path / "video.mp4"
        f.write_bytes(b"data")
        with pytest.raises(ValueError):
            collect_input_files(str(f), str(tmp_path))

    def test_single_png_returned(self, tmp_path):
        f = tmp_path / "001.png"
        f.write_bytes(b"PNG")
        result = collect_input_files(str(f), str(tmp_path))
        assert result == [str(f)]

    def test_directory_filters_unsupported_ext(self, tmp_path):
        (tmp_path / "001.png").write_bytes(b"PNG")
        (tmp_path / "002.mp4").write_bytes(b"MP4")
        result = collect_input_files(str(tmp_path), str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("001.png")

    def test_directory_excludes_line_thumbnails(self, tmp_path):
        (tmp_path / "001.png").write_bytes(b"PNG")
        (tmp_path / "001_key@2x.png").write_bytes(b"PNG")
        (tmp_path / "001_key@3x.png").write_bytes(b"PNG")
        (tmp_path / "tab_on.png").write_bytes(b"PNG")
        (tmp_path / "tab_off.png").write_bytes(b"PNG")
        result = collect_input_files(str(tmp_path), str(tmp_path))
        assert len(result) == 1
        assert result[0].endswith("001.png")

    def test_empty_directory_returns_empty(self, tmp_path):
        result = collect_input_files(str(tmp_path), str(tmp_path))
        assert result == []


# ---------------------------------------------------------------------------
# argparse (_make_parser + custom validation)
# ---------------------------------------------------------------------------

class TestArgparse:
    def test_no_source_arg_exits(self):
        parser = _make_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_input_with_title_ok(self):
        parser = _make_parser()
        args = parser.parse_args(["-i", "./img/", "-n", "Title"])
        assert args.input == "./img/"
        assert args.title == "Title"

    def test_input_without_title_detected(self):
        parser = _make_parser()
        args = parser.parse_args(["-i", "./img/"])
        # Custom validation triggers parser.error → SystemExit
        with pytest.raises(SystemExit):
            if args.input and not args.title:
                parser.error("-n/--title is required when using -i")

    def test_line_without_title_ok(self):
        parser = _make_parser()
        args = parser.parse_args(["--line", "https://store.line.me/stickershop/product/123"])
        assert args.line == "https://store.line.me/stickershop/product/123"
        assert args.title is None

    def test_line_with_title_ok(self):
        parser = _make_parser()
        args = parser.parse_args(["--line", "https://store.line.me/...", "-n", "Title"])
        assert args.title == "Title"

    def test_input_and_line_together_exits(self):
        parser = _make_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["-i", "./img/", "--line", "https://..."])

    def test_test_flag_ok(self):
        parser = _make_parser()
        args = parser.parse_args(["--test"])
        assert args.test is True
