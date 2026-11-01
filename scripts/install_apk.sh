#!/usr/bin/env bash
set -e

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$(dirname "$SCRIPT_PATH")")"
APK_PATH="$SCRIPT_DIR/android/app/build/outputs/apk/debug/app-debug.apk"

# Find ADB binary
ADB_BIN="$HOME/Android/Sdk/platform-tools/adb"
if [ ! -x "$ADB_BIN" ]; then
    if command -v adb >/dev/null 2>&1; then
        ADB_BIN="adb"
    else
        echo "❌ Error: ADB not found in ~/Android/Sdk/platform-tools/adb or PATH"
        exit 1
    fi
fi

if [ ! -f "$APK_PATH" ]; then
    echo "📦 APK not found. Building with Gradle..."
    if [ -z "$JAVA_HOME" ] || [ ! -d "$JAVA_HOME" ]; then
        for candidate in \
            "$HOME/.jdks/jbr-17.0.14" \
            "/usr/lib/jvm/java-17-openjdk" \
            "/usr/lib/jvm/java-17" \
            "/usr/lib/jvm/default-java"; do
            if [ -d "$candidate" ]; then
                export JAVA_HOME="$candidate"
                break
            fi
        done
    fi
    export ANDROID_HOME="${ANDROID_HOME:-$HOME/Android/Sdk}"
    cd "$SCRIPT_DIR/android"
    ./gradlew assembleDebug
fi

echo "📱 Checking for connected Android devices..."
DEVICES=$("$ADB_BIN" devices | grep -v "List of devices" | grep "device$" || true)

if [ -z "$DEVICES" ]; then
    echo "⚠️  No Android device detected. Please:"
    echo "   1. Connect your Samsung Tab A9+ with USB"
    echo "   2. Enable Developer Options & USB Debugging on tablet"
    echo "   3. Accept the USB debugging prompt on tablet"
    exit 1
fi

echo "🚀 Installing $APK_PATH on tablet..."
"$ADB_BIN" install -r "$APK_PATH"

echo "⚡ Setting up USB reverse port forwarding (8080)..."
"$ADB_BIN" reverse tcp:8080 tcp:8080

echo "✅ Installation complete! You can open the LinuxExtend app on your tablet."
