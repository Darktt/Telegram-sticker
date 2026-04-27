# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案說明

從本地圖片（目錄、單檔或 ZIP）建立 Telegram 貼圖集的 Python CLI 工具。使用 Telethon（MTProto 用戶端 API）以用戶帳號直接操作，無需 Bot Token。

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
# 基本用法
python msb_create.py -i ./images/ -n "My Pack"

# 完整選項
python msb_create.py -i INPUT -n TITLE [-s SHORT_NAME] [-e EMOJI] [--custom_emoji] [--log_level LEVEL]
```

| 參數 | 說明 |
|------|------|
| `-i` | 輸入源：圖片目錄、單檔或 ZIP/CBZ/TAR |
| `-n` | 貼圖集標題（1–64 字符） |
| `-s` | 短名稱（自動產生或自訂，`[a-zA-Z0-9_]`，全域唯一） |
| `-e` | 預設 emoji（預設 `⭐`） |
| `--custom_emoji` | 建立自定義 Emoji 貼圖集 |

## 架構

```
msb_create.py   ← CLI 入口、參數解析、流程協調
converter.py    ← 圖片/影片轉換引擎（呼叫 ImageMagick/FFmpeg）
tg_api.py       ← Telethon 上層封裝（上傳、建立貼圖集）
```

**資料流**：輸入驗證 → 檔案收集 → 格式轉換（`converter.py`）→ 上傳至 Telegram（`tg_api.py`）→ 建立貼圖集

## 格式轉換規格

| 輸入格式 | 輸出 | 規格 |
|----------|------|------|
| PNG/JPG/BMP/WEBP（靜態） | WEBP | 512×512 |
| GIF/APNG（動畫） | VP9 WEBM | ≤3 秒、≤255 KiB |
| 自訂 Emoji（`--custom_emoji`） | WEBP/WEBM | 100×100 |
| `.webp`/`.webm` | 直接使用 | 無需轉換 |

## 重要限制

- Telegram 單一貼圖集上限 **120 個**，超量會自動分批建立多個貼圖集
- 短名稱（`-s`）在 Telegram 上全域唯一，重複會報錯
- 系統需安裝 **ImageMagick**（`convert`/`magick`）與 **FFmpeg**，`setup.sh` 會自動處理
