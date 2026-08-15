# LinuxExtend 🖥️📱

Use your Samsung Galaxy Tab A9+ (or any Android tablet / browser) as a seamless second monitor for Linux.

Built natively for **Hyprland** (Wayland) on Fedora/Arch/Debian, supporting both high-speed **Wi-Fi** and zero-latency **USB** streaming.

---

## 🌟 Features

- **⚡ Fast Streaming**: Low-latency screen capture via `grim` + JPEG streaming to WebSocket consumers.
- **📱 1-Tap Immersive Fullscreen**: Borderless edge-to-edge playback with zero UI clutter on the tablet.
- **🖱️ Full Mouse & Cursor Tracking**: Seamless hardware and software cursor rendering across screens.
- **🔄 Instant Monitor Switching**: Jump your mouse cursor between laptop and tablet with `SHIFT + TAB` or `ALT + TAB`.
- **🪟 Instant Window Movement**: Throw any active app window to the tablet with `SUPER + M` or `SUPER + SHIFT + TAB`.
- **📊 Dual Waybar Support**: Waybar runs simultaneously on both your laptop and tablet screen.
- **🖼️ Auto Wallpaper Sync**: Automatically detects and mirrors your desktop wallpaper to the virtual tablet monitor via `swww`.
- **🔍 Zero-Config mDNS Discovery**: Native Android `NsdManager` + Python `zeroconf` discovery over local LAN.
- **🔌 USB Mode**: Zero-latency ADB reverse port forwarding support.

---

## 🏗️ Architecture

```
┌──────────────────────────────────────┐          ┌──────────────────────────────────────┐
│       Linux Laptop (Hyprland)        │  Wi-Fi   │     Android Tablet (Tab A9+)         │
│                                      │  or USB  │                                      │
│  Hyprland creates HEADLESS display   │ ──────── │  Jetpack Compose / Web Browser       │
│  → grim captures with cursor (-c)    │WebSocket │  renders hardware RGB bitmap         │
│  → FastAPI WebSocket server streams  │ (8080)   │  fullscreen at native aspect ratio   │
└──────────────────────────────────────┘          └──────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Start the Server (Laptop)

```bash
# Clone the repository
git clone https://github.com/neonjava/LinuxExtend.git
cd LinuxExtend

# Run setup (checks dependencies and installs Python packages)
./scripts/setup_env.sh

# Start the server
./scripts/run_server.sh
```

*(Options: `./scripts/run_server.sh -r 1920x1200 -f 30 -q 60` for 16:10 resolution at 30 FPS)*

---

### 2. Connect Your Tablet

#### Option A: Web Browser (Instant — No app install needed)
1. Open Chrome or Samsung Internet on your tablet.
2. Go to: `http://<your-laptop-ip>:8080/` (e.g. `http://192.168.1.50:8080/`).
3. Tap anywhere on the screen for **100% borderless fullscreen**.

#### Option B: Native Android App (Fastest / Lowest Latency)
```bash
# Connect tablet with USB cable (enable USB Debugging) and run:
./scripts/install_apk.sh
```
In the app, check **USB Mode (localhost)** and tap **Connect**.

---

## ⌨️ Hyprland Keybindings

Add these lines to your `~/.config/hypr/UserConfigs/UserKeybinds.conf`:

```hyprlang
# Switch mouse cursor between laptop & tablet
bindd = SHIFT, Tab, Switch monitor cursor, exec, ~/.config/hypr/scripts/switch_monitor.sh
bindd = ALT, Tab, Switch monitor cursor, exec, ~/.config/hypr/scripts/switch_monitor.sh

# Move active window to tablet screen
bindd = $mainMod, M, Move window to other monitor, movewindow, mon:+1
bindd = $mainMod SHIFT, Tab, Move window to other monitor, movewindow, mon:+1
```

---

## 📋 Requirements

### Linux Host
- **Compositor**: Hyprland (wlroots)
- **Tools**: `grim`, `swww` (for wallpaper sync), `waybar`
- **Python**: 3.10+ (`fastapi`, `uvicorn`, `zeroconf`, `numpy`)

### Android Client
- Android 13+ (API 33+)
- Tested on Samsung Galaxy Tab A9+ (1920×1200)

---

## 🧪 Testing

Run the automated Python test suite:

```bash
cd server
pytest tests/ -v
```

---

## 📄 License

MIT License. Free and open source.
