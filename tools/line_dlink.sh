#!/bin/bash
# line_dlink.sh - Parse a LINE store URL and print the sticker pack download link.
# Usage: ./line_dlink.sh <LINE store URL>

set -e

LINK="$1"
if [ -z "$LINK" ]; then
    echo "Usage: $0 <LINE store URL>" >&2
    exit 1
fi

# --- Step 1: Fetch the LINE store page ---
# Use a browser UA so LINE doesn't block the request, and prefer zh-Hant.
PAGE=$(curl -s -L \
    -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36" \
    -H "Accept-Language: zh-Hant;q=0.9, ja;q=0.8, en;q=0.7" \
    "$LINK")

# --- Step 2: Extract sticker ID and canonical URL from the first <script> JSON ---
# The first <script> tag on LINE store pages is a JSON blob like:
#   {"name":"...", "sku":"28648903", "url":"https://store.line.me/stickershop/..."}
FIRST_SCRIPT=$(echo "$PAGE" | python3 -c "
import sys, re
html = sys.stdin.read()
m = re.search(r'<script[^>]*>(.*?)</script>', html, re.DOTALL)
print(m.group(1) if m else '')
")

ID=$(echo "$FIRST_SCRIPT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('sku', ''))
except: pass
" 2>/dev/null)

STORE_URL=$(echo "$FIRST_SCRIPT" | python3 -c "
import sys, json
try:
    print(json.load(sys.stdin).get('url', ''))
except: pass
" 2>/dev/null)

# --- Step 2 (fallback): Some newer LINE pages don't have the JSON script ---
# Extract URL from <meta property="og:url"> and ID from <link hreflang="x-default">.
if [ -z "$STORE_URL" ]; then
    STORE_URL=$(echo "$PAGE" | grep -o 'property="og:url" content="[^"]*"' | sed 's/.*content="\([^"]*\)".*/\1/')
fi

if [ -z "$ID" ]; then
    DEFAULT_LINK=$(echo "$PAGE" | grep -o 'hreflang="x-default"[^>]*href="[^"]*"' | grep -o 'href="[^"]*"' | sed 's/href="\(.*\)"/\1/')
    ID=$(basename "$DEFAULT_LINK")
fi

if [ -z "$ID" ] || [ -z "$STORE_URL" ]; then
    echo "Error: could not extract sticker ID or URL from page." >&2
    exit 1
fi

echo "ID:        $ID"
echo "Store URL: $STORE_URL"

# --- Step 3: Determine sticker type by checking CSS classes in page HTML ---
# LINE uses specific icon classes to indicate the sticker type.
BASE="https://stickershop.line-scdn.net/stickershop/v1/product/${ID}/iphone"

if echo "$STORE_URL" | grep -qE "stickershop|officialaccount/event/sticker"; then

    if echo "$PAGE" | grep -qE "MdIcoPlay_b|MdIcoAni_b"; then
        CATEGORY="animated"
        DLINK="${BASE}/stickerpack@2x.zip"

    elif echo "$PAGE" | grep -q "MdIcoMessageSticker_b"; then
        # Message stickers have per-sticker individual URLs, not a single ZIP.
        # This script only handles the simple ZIP case; signal this as unsupported.
        CATEGORY="message (unsupported: requires per-sticker API)"
        DLINK="(see productInfo.meta: https://stickershop.line-scdn.net/stickershop/v1/product/${ID}/iphone/productInfo.meta)"

    elif echo "$PAGE" | grep -q "MdIcoNameSticker_b"; then
        CATEGORY="name"
        DLINK="${BASE}/sticker_name_base@2x.zip"

    elif echo "$PAGE" | grep -qE "MdIcoFlash_b|MdIcoFlashAni_b"; then
        CATEGORY="popup (fullscreen)"
        DLINK="${BASE}/stickerpack@2x.zip"

    elif echo "$PAGE" | grep -qE "MdIcoEffectSoundSticker_b|MdIcoEffectSticker_b"; then
        CATEGORY="popup effect"
        DLINK="${BASE}/stickerpack@2x.zip"

    else
        CATEGORY="static"
        # IDs before 775 use a non-standard CgBI PNG encoding on iPhone.
        # The Android ZIP uses standard PNG that ImageMagick can read.
        if [ "$ID" -lt 775 ] 2>/dev/null; then
            DLINK="https://stickershop.line-scdn.net/stickershop/v1/product/${ID}/android/stickers.zip"
        else
            DLINK="${BASE}/stickers@2x.zip"
        fi
    fi

elif echo "$STORE_URL" | grep -q "emojishop"; then

    if echo "$PAGE" | grep -q "MdIcoPlay_b"; then
        CATEGORY="emoji animated"
        DLINK="https://stickershop.line-scdn.net/sticonshop/v1/sticon/${ID}/iphone/package_animation.zip"
    else
        CATEGORY="emoji static"
        DLINK="https://stickershop.line-scdn.net/sticonshop/v1/sticon/${ID}/iphone/package.zip"
    fi

else
    echo "Error: unknown LINE store category (URL: $STORE_URL)" >&2
    exit 1
fi

echo "Category:  $CATEGORY"
echo "DLink:     $DLINK"
