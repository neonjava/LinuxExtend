#!/usr/bin/env bash
set -e

echo "🔍 Checking LinuxExtend environment prerequisites..."

# 1. Check Hyprland
if hyprctl version >/dev/null 2>&1; then
    echo "  ✅ Hyprland is running"
else
    echo "  ⚠️  Warning: Hyprland was not detected. Make sure you are in a Hyprland session."
fi

# 2. Check grim
if command -v grim >/dev/null 2>&1; then
    echo "  ✅ grim screen capture tool found"
else
    echo "  ❌ grim not found. Install it with: sudo dnf install grim"
fi

# 3. Check Python dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "📦 Installing server Python dependencies..."
python3 -m pip install -r "$SCRIPT_DIR/server/requirements.txt"

# 4. Check ADB
ADB_BIN="$HOME/Android/Sdk/platform-tools/adb"
if [ -x "$ADB_BIN" ] || command -v adb >/dev/null 2>&1; then
    echo "  ✅ ADB tool available"
else
    echo "  ⚠️  ADB not found in default paths"
fi

echo "✨ Environment check complete!"
