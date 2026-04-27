# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案說明

從本地圖片（目錄、單檔或 ZIP）或 LINE 貼圖商店 URL 建立 Telegram 貼圖集的 Python CLI 工具。使用 Telethon（MTProto 用戶端 API）以用戶帳號直接操作，無需 Bot Token。

## 安裝與環境設定

```bash
# 安裝系統依賴、建立虛擬環境、安裝 Python 依賴
bash setup.sh

# 啟用虛擬環境（每次開發前需執行）
source .venv/bin/activate
```

設定 `.env`（由 `setup.sh` 從 `.env.example` 自動複製）：
```
API_ID=        # 從 https://my.telegram.org/apps 取得
API_HASH=      # 同上
PHONE=         # 國際格式手機號，如 +886912345678
```

首次執行時 Telethon 會要求 SMS 驗證碼，驗證後產生 `msb_create.session`（已 .gitignore）。

## 執行

```bash
# 測試 Telegram API 連線
python msb_create.py --test

# 從 LINE 貼圖商店下載並建立（標題自動取得）
python msb_create.py --line "https://store.line.me/stickershop/product/12345"

# 從本地目錄建立
python msb_create.py -i ./images/ -n "My Pack"

# 完整選項
python msb_create.py (-i INPUT | --line LINE_URL | --test) [-n TITLE] [-s SHORT_NAME] [-e EMOJI] [--custom_emoji] [--log_level LEVEL]
```

| 參數 | 說明 |
|------|------|
| `-i` | 輸入源：圖片目錄、單檔或 ZIP/CBZ/TAR（需搭配 `-n`） |
| `--line` | LINE 貼圖商店 URL（`-n` 可省略，自動取得標題）；URL 含特殊字元時須加引號 |
| `--test` | 測試 Telegram API 連線，印出帳號資訊後結束 |
| `-n` | 貼圖集標題（1–64 字符；使用 `-i` 時必填） |
| `-s` | 短名稱（自動產生或自訂，`[a-zA-Z0-9_]`，全域唯一） |
| `-e` | 預設 emoji（預設 `⭐`） |
| `--custom_emoji` | 建立自定義 Emoji 貼圖集 |

## 架構

```
msb_create.py        ← CLI 入口、參數解析、流程協調
converter.py         ← 圖片/影片轉換引擎（呼叫 ImageMagick/FFmpeg）
tg_api.py            ← Telethon 上層封裝（上傳、建立貼圖集）
line_downloader.py   ← LINE 商店頁面解析與 ZIP 下載
tools/line_dlink.sh  ← 手動查詢 LINE 下載連結的 Shell 腳本（獨立工具）
```

**資料流（`--line` 模式）**：
LINE URL → `line_downloader.py`（解析類型 + 下載 ZIP）→ `stickers/<pack_id>/`（解壓）→ 格式轉換（`converter.py`）→ 上傳至 Telegram（`tg_api.py`）→ 建立貼圖集

**資料流（`-i` 模式）**：
輸入驗證 → 檔案收集 → 格式轉換（`converter.py`）→ 上傳至 Telegram（`tg_api.py`）→ 建立貼圖集

## LINE 貼圖下載

`line_downloader.py` 移植自 `tools/line_dlink.sh`，依 HTML 中的 CSS class 判斷貼圖類型：

| CSS class | 類型 | 備註 |
|-----------|------|------|
| `MdIcoPlay_b` / `MdIcoAni_b` | animated | |
| `MdIcoNameSticker_b` | name | |
| `MdIcoFlash_b` / `MdIcoFlashAni_b` | popup | |
| `MdIcoEffectSticker_b` 等 | popup | |
| `MdIcoMessageSticker_b` | 不支援 | 需逐張 API，拋 `LineUnsupportedTypeError` |
| 其他（ID ≥ 775） | static | iphone ZIP |
| 其他（ID < 775） | static | android ZIP（iphone 版 PNG 編碼不相容 ImageMagick） |
| emojishop + `MdIcoPlay_b` | emoji_animated | |
| emojishop 其他 | emoji_static | |

下載後解壓至 `stickers/<pack_id>/`（已 .gitignore），自動排除 LINE 的縮圖與 UI 檔：`_key@2x`、`_key@3x`、`tab_off`、`tab_on`。

## 格式轉換規格

| 輸入格式 | 輸出 | 規格 |
|----------|------|------|
| PNG/JPG/BMP/WEBP（靜態） | WEBP | 512×512 |
| GIF/APNG（動畫） | VP9 WEBM | ≤3 秒、≤255 KiB |
| 自訂 Emoji（`--custom_emoji`） | WEBP/WEBM | 100×100 |
| `.webp`/`.webm` | 直接使用 | 無需轉換 |

## 測試

```bash
# 執行所有單元測試（不需要 Telegram 憑證或系統工具）
pytest tests/ -v
```

測試涵蓋三個模組（66 個測試案例）：

| 檔案 | 測試對象 |
|------|---------|
| `tests/test_msb_create.py` | `_is_wanted`、`generate_set_name`、`collect_input_files`、argparse |
| `tests/test_line_downloader.py` | HTML 解析、LINE 分類邏輯、HTTP mock（`fetch_line_info`、`download_zip`） |
| `tests/test_converter.py` | `guess_format`、`ls_files_r`、`extract_zip` |

`tg_api.py` 需要真實 Telegram 連線，使用 `--test` 指令手動驗證。

## 重要限制

- Telegram 單一貼圖集上限 **120 個**，超量會自動分批建立多個貼圖集
- 短名稱（`-s`）在 Telegram 上全域唯一，重複會報錯
- 系統需安裝 **ImageMagick**（`convert`/`magick`）與 **FFmpeg**，`setup.sh` 會自動處理
- LINE 訊息貼圖（`MdIcoMessageSticker_b`）不支援，需逐張 API
- `tg_api` 採 lazy import，在 `run()` 內部引入，確保測試不依賴 `telethon`
