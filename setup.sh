#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# ---------------------------------------------------------------------------
# System dependencies
# ---------------------------------------------------------------------------

install_system_deps_macos() {
    if ! command -v brew &>/dev/null; then
        echo "Error: Homebrew not found. Install it from https://brew.sh" >&2
        exit 1
    fi
    echo "Installing system dependencies via Homebrew ..."
    brew install imagemagick ffmpeg libarchive
    # libarchive keg is not linked by default; ensure bsdtar is accessible
    if ! command -v bsdtar &>/dev/null; then
        brew link --force libarchive
    fi
}

check_or_install_system_deps() {
    local missing=()
    command -v ffmpeg &>/dev/null || missing+=(ffmpeg)
    command -v magick &>/dev/null || command -v convert &>/dev/null || missing+=(imagemagick)
    command -v bsdtar &>/dev/null || missing+=(bsdtar)

    if [ ${#missing[@]} -eq 0 ]; then
        echo "System dependencies already satisfied."
        return
    fi

    echo "Missing system tools: ${missing[*]}"
    install_system_deps_macos
}

# ---------------------------------------------------------------------------
# OS detection — delegate Linux to setup_linux.sh
# ---------------------------------------------------------------------------

if [ "$(uname -s)" = "Linux" ]; then
    exec bash "$SCRIPT_DIR/setup_linux.sh" "$@"
fi

if [ "$(uname -s)" != "Darwin" ]; then
    echo "Warning: unsupported OS. Install manually: ffmpeg imagemagick bsdtar" >&2
fi

# ---------------------------------------------------------------------------
# Python version check
# ---------------------------------------------------------------------------

PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo "Error: python3 not found in PATH." >&2
    exit 1
fi

PY_VERSION=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "Error: Python 3.9+ required (found $PY_VERSION)." >&2
    exit 1
fi

echo "Using Python $PY_VERSION"

# ---------------------------------------------------------------------------
# Main setup
# ---------------------------------------------------------------------------

check_or_install_system_deps

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    "$PYTHON" -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

echo "Installing Python dependencies ..."
"$VENV_DIR/bin/pip" install --upgrade pip -q
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

if [ ! -f "$SCRIPT_DIR/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo ""
    echo "Created .env from .env.example — please fill in API_ID, API_HASH, and PHONE."
fi

echo ""
echo "Setup complete. To use:"
echo "  source $VENV_DIR/bin/activate"
echo "  python msb_create.py -i ./images/ -n \"My Pack\""
