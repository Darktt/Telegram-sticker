# Telegram-sticker — 本地貼圖建立工具

因應 moe-sticker-bot 失效後建立的 Telegram 貼圖工具,
從本地圖片檔案直接建立 Telegram 貼圖集，無需透過 Bot 的對話流程。
使用 Telegram 用戶端 API（MTProto）以你的帳號身份操作，不需要 Bot Token。

## 安裝

### 自動安裝（推薦）

不論平台，均在專案根目錄執行：

```bash
bash setup.sh
```

`setup.sh` 會自動偵測作業系統：

- **macOS** — 透過 Homebrew 安裝系統套件
- **Linux** — 自動移交給 `setup_linux.sh` 執行（支援 apt / dnf / yum）
- **其他平台** — 印出警告，請手動安裝系統套件後繼續

腳本完成以下步驟：

1. 安裝缺少的系統相依套件
2. 確認 Python 版本（需 3.9+）
3. 在 `.venv` 建立虛擬環境
4. 安裝 `requirements.txt` 中的所有 Python 套件
5. 若 `.env` 不存在，從 `.env.example` 複製一份

`setup_linux.sh` 也可在 Linux 上單獨執行：

```bash
bash setup_linux.sh
```

### 手動建立虛擬環境

若不使用安裝腳本，可自行建立：

```bash
# 建立虛擬環境（需 Python 3.9+）
python3 -m venv .venv

# 啟動虛擬環境
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows

# 安裝相依套件
pip install -r requirements.txt
```

### 啟動虛擬環境

每次開啟新的終端機視窗後，執行指令前都需要先啟動：

```bash
source .venv/bin/activate        # macOS / Linux
.venv\Scripts\activate           # Windows
```

啟動後提示字元會出現 `(.venv)` 前綴，表示已進入虛擬環境。

### 系統相依套件

| 套件 | 用途 | macOS | Debian/Ubuntu | RHEL/Fedora | CentOS |
|------|------|-------|---------------|-------------|--------|
| ImageMagick | 靜態圖片轉 WEBP | `brew install imagemagick` | `apt install imagemagick` | `dnf install ImageMagick` | `yum install ImageMagick` |
| FFmpeg | 動畫轉 WEBM（VP9）| `brew install ffmpeg` | `apt install ffmpeg` | `dnf install ffmpeg` | `yum install ffmpeg` |
| bsdtar | ZIP 解壓 | macOS 內建 | `apt install libarchive-tools` | `dnf install bsdtar` | `yum install bsdtar` |

> 若作業系統不在支援清單內，請手動安裝上述套件後再執行 `setup.sh`。

---

## 環境設定

### 取得 API 憑證

1. 前往 [my.telegram.org](https://my.telegram.org) 並登入
2. 點選 **API development tools**
3. 填寫表單
   * App title: sticker-convert
   * Short name: sticker-convert
   * URL: www.telegram.org
   * Platform: Desktop
   * Description: sticker-convert
4. 建立應用程式後取得 `API_ID` 和 `API_HASH`

### 建立 .env 檔案

```bash
cp .env.example .env
# 編輯 .env，填入實際值
```

`.env` 格式：

```
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
PHONE=+886912345678
```

| 變數 | 說明 |
|------|------|
| `API_ID` | 從 my.telegram.org 取得的數字 ID |
| `API_HASH` | 從 my.telegram.org 取得的雜湊字串 |
| `PHONE` | 你的 Telegram 帳號手機號碼（含國碼）|

> `.env` 和 `*.session` 均已列入 `.gitignore`，不會被提交到版本控制。

### 首次執行

第一次執行時，Telethon 會引導完成驗證：

```
Please enter your phone (or bot token): +886912345678
Please enter the code you received: 12345
```

驗證成功後會產生 `msb_create.session` 檔案，之後執行不再需要重新登入。

---

## 使用方式

```
python msb_create.py (-i INPUT | --line LINE_URL | --test) [OPTIONS]
```

輸入來源三選一（互斥）：

| 參數 | 說明 |
|------|------|
| `-i`, `--input` | 本地輸入：圖片目錄、單一圖片檔案、或 ZIP 壓縮包（需搭配 `-n`） |
| `--line LINE_URL` | LINE 貼圖商店網址，自動下載並轉換（`-n` 可省略，自動取得標題） |
| `--test` | 測試 Telegram API 連線，印出登入帳號資訊後結束 |
| `--clean` | 清理下載下來的貼圖檔案 |

### 選填參數

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `-n`, `--title` | — | 貼圖集標題（1–64 字符；使用 `-i` 時必填） |
| `-s`, `--name` | 自動產生 | 貼圖集短名稱（必須符合 `[a-zA-Z0-9_]`，全域唯一） |
| `-e`, `--emoji` | `⭐` | 所有貼圖使用的預設 emoji |
| `--custom_emoji` | — | 建立 Custom Emoji 貼圖集（圖片縮放至 100×100） |
| `--log_level` | `INFO` | 日誌詳細程度：`DEBUG` / `INFO` / `WARNING` / `ERROR` |

---

## 範例

```bash
# 確認 Telegram API 連線是否正常
python msb_create.py --test

# 從 LINE 貼圖商店直接下載並建立（標題自動取得）
python msb_create.py --line "https://store.line.me/stickershop/product/12345"

# 從 LINE 商店下載，手動指定標題
python msb_create.py --line "https://store.line.me/stickershop/product/12345" -n "我的貼圖集"

# 從本地目錄建立一般貼圖集
python msb_create.py -i ./my_stickers/ -n "My Sticker Pack"

# 從 ZIP 壓縮包建立
python msb_create.py -i stickers.zip -n "My Pack"

# 建立 Custom Emoji 貼圖集，指定 emoji 與自訂短名稱
python msb_create.py \
  -i ./emojis/ \
  -n "My Emojis" \
  -s "my_emojis_pack" \
  -e "🌸" \
  --custom_emoji
```

---

## 支援的輸入格式

| 格式 | 轉換結果 |
|------|---------|
| PNG、JPG、JPEG、BMP、WEBP（靜態） | 512×512 WEBP（一般貼圖）或 100×100 WEBP（Custom Emoji） |
| GIF、APNG（動畫） | VP9 WEBM，最長 3 秒，最大 255 KiB |
| ZIP 壓縮包 | 解壓後逐一轉換目錄內的圖片 |
| 已轉換的 `.webp` / `.webm` | 直接使用，略過轉換步驟 |

---

## 檔案說明

| 檔案 | 說明 |
|------|------|
| `msb_create.py` | CLI 入口，負責參數解析與整體流程 |
| `converter.py` | 圖片/影片轉換，對應專案的 `pkg/msbimport/convert.go` |
| `tg_api.py` | Telegram MTProto API 封裝（Telethon）|
| `line_downloader.py` | LINE 貼圖商店頁面解析與 ZIP 下載（供 `--line` 使用）|
| `requirements.txt` | Python 依賴（`telethon`、`python-dotenv`、`requests`、`beautifulsoup4`）|
| `setup.sh` | 安裝腳本（macOS / 通用入口），Linux 自動移交給 `setup_linux.sh` |
| `setup_linux.sh` | Linux 專用安裝腳本（apt / dnf / yum），可單獨執行 |
| `.env.example` | 環境變數範本，複製為 `.env` 後填入實際值 |
| `msb_create.session` | Telethon 登入 session（首次登入後自動產生，勿分享）|
| `tools/line_dlink.sh` | 手動查詢 LINE 貼圖下載連結的 Shell 腳本 |
