# LinuxExtend 🖥️📱

Use your Samsung Galaxy Tab A9+ (or any Android tablet) as a second monitor for your Linux laptop.

Built for **Hyprland** (Wayland) on Fedora, but adaptable to other wlroots compositors.

## How It Works

```
┌──────────────────────┐          ┌──────────────────────┐
│   Linux Laptop       │  Wi-Fi   │   Android Tablet     │
│                      │  or USB  │                      │
│  Hyprland creates    │ ──────── │  App receives JPEG   │
│  virtual HEADLESS    │ WebSocket│  frames and renders   │
│  display → grim      │          │  fullscreen           │
│  captures → streams  │          │                      │
└──────────────────────┘          └──────────────────────┘
```

## Quick Start

### Server (Linux Laptop)

```bash
cd LinuxExtend/server

# Install dependencies
pip install -r requirements.txt

# Also need libturbojpeg system library
sudo dnf install turbojpeg-devel   # Fedora
# sudo apt install libturbojpeg0-dev  # Ubuntu/Debian

# Run the server
python -m linuxextend
```

The server will:
1. Create a virtual headless display on Hyprland
2. Start capturing frames at 25 FPS
3. Start a WebSocket server on port 8080
4. Advertise itself via mDNS for auto-discovery

### Android App (Tablet)

```bash
cd LinuxExtend/android

# Build the debug APK
./gradlew assembleDebug

# Install on connected tablet
~/Android/Sdk/platform-tools/adb install app/build/outputs/apk/debug/app-debug.apk
```

### USB Connection

For zero-latency USB connection:

```bash
# On the laptop (after connecting tablet via USB):
python -m linuxextend --setup-usb

# Then in the Android app, check "USB Mode" and connect
```

## Server Options

```
python -m linuxextend [options]

  --resolution, -r    Virtual display resolution (default: 1920x1080)
  --fps, -f           Target capture FPS (default: 25)
  --quality, -q       JPEG quality 1-100 (default: 75)
  --port, -p          Server port (default: 8080)
  --no-discovery      Disable mDNS advertising
  --setup-usb         Set up ADB USB forwarding and exit
  --verbose, -v       Enable debug logging
```

## Testing Without the App

Open `http://<your-ip>:8080/` in any browser to see the stream.

## Architecture

- **Virtual Display**: Hyprland's native `hyprctl output create headless`
- **Capture**: `grim` for Wayland screencopy → PPM → TurboJPEG encoding
- **Streaming**: WebSocket JPEG frames via FastAPI/uvicorn
- **Discovery**: Zeroconf/mDNS (`_linuxextend._tcp`)
- **Android Client**: Kotlin/Jetpack Compose + OkHttp WebSocket

## Requirements

### Server
- Hyprland (wlroots compositor)
- Python 3.12+
- `grim` (screen capture)
- `libturbojpeg` (JPEG encoding)

### Android
- Android 13+ (API 33+)
- Tested on Samsung Galaxy Tab A9+
