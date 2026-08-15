"""LinuxExtend CLI entry point.

Usage:
    python -m linuxextend                          # Start with defaults
    python -m linuxextend --resolution 1920x1200   # Custom resolution
    python -m linuxextend --fps 30 --quality 80    # Tweak capture settings
    python -m linuxextend --port 9090              # Custom port
    python -m linuxextend --setup-usb              # Set up USB forwarding
    python -m linuxextend --no-discovery            # Disable mDNS
"""

import argparse
import logging
import os
import signal
import subprocess
import sys
import time

import uvicorn

from .config import Config
from .capture import ScreenCapture
from .discovery import ServiceAdvertiser
from .display import VirtualDisplay, VirtualDisplayError
from . import server as server_module

# ANSI color codes for terminal output
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_YELLOW = "\033[93m"
_RED = "\033[91m"
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _print_banner() -> None:
    print(f"""
{_BOLD}{_CYAN}╔═══════════════════════════════════════╗
║         🖥️  LinuxExtend  v1.0         ║
║     Tablet as Second Monitor Tool     ║
╚═══════════════════════════════════════╝{_RESET}
""")


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format=f"{_DIM}%(asctime)s{_RESET} %(levelname)s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("zeroconf").setLevel(logging.WARNING)


def _setup_usb(port: int) -> None:
    """Set up ADB reverse port forwarding for USB connection."""
    adb_path = os.path.expanduser("~/Android/Sdk/platform-tools/adb")
    if not os.path.exists(adb_path):
        # Try system adb
        adb_path = "adb"

    print(f"{_CYAN}📱 Setting up USB port forwarding...{_RESET}")
    try:
        result = subprocess.run(
            [adb_path, "reverse", f"tcp:{port}", f"tcp:{port}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print(f"{_GREEN}✓ USB forwarding active: tablet localhost:{port} → laptop:{port}{_RESET}")
            print(f"{_DIM}  Connect in the app using: 127.0.0.1:{port}{_RESET}")
        else:
            stderr = result.stderr.strip()
            if "no devices" in stderr.lower() or "not found" in stderr.lower():
                print(f"{_RED}✗ No Android device connected via USB{_RESET}")
                print(f"{_DIM}  Connect your tablet and enable USB debugging{_RESET}")
            else:
                print(f"{_RED}✗ ADB error: {stderr}{_RESET}")
    except FileNotFoundError:
        print(f"{_RED}✗ ADB not found. Install Android SDK platform-tools{_RESET}")
    except subprocess.TimeoutExpired:
        print(f"{_RED}✗ ADB command timed out{_RESET}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="linuxextend",
        description="Use your tablet as a second monitor for Linux (Hyprland/Wayland)",
    )
    parser.add_argument(
        "--resolution", "-r",
        default="1920x1080",
        help="Virtual display resolution (default: 1920x1080)",
    )
    parser.add_argument(
        "--fps", "-f",
        type=int,
        default=25,
        help="Target capture FPS (default: 25)",
    )
    parser.add_argument(
        "--quality", "-q",
        type=int,
        default=75,
        help="JPEG quality 1-100 (default: 75)",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Server port (default: 8080)",
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--no-discovery",
        action="store_true",
        help="Disable mDNS service advertising",
    )
    parser.add_argument(
        "--setup-usb",
        action="store_true",
        help="Set up ADB USB port forwarding and exit",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    _setup_logging(args.verbose)
    _print_banner()

    # USB setup mode
    if args.setup_usb:
        _setup_usb(args.port)
        return

    config = Config(
        resolution=args.resolution,
        target_fps=args.fps,
        jpeg_quality=args.quality,
        port=args.port,
        host=args.host,
    )

    logger = logging.getLogger("linuxextend")
    display: VirtualDisplay | None = None
    capture: ScreenCapture | None = None
    advertiser: ServiceAdvertiser | None = None

    def shutdown(signum: int = 0, frame: object = None) -> None:
        """Clean shutdown handler."""
        print(f"\n{_YELLOW}⏹  Shutting down...{_RESET}")

        if capture:
            capture.stop()
            print(f"  {_DIM}Capture stopped{_RESET}")

        if advertiser:
            advertiser.stop()
            print(f"  {_DIM}mDNS unregistered{_RESET}")

        if display:
            display.remove()
            print(f"  {_DIM}Virtual display removed{_RESET}")

        print(f"{_GREEN}✓ Clean shutdown complete{_RESET}")

        if signum:
            sys.exit(0)

    # Register signal handlers
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        # Step 1: Create virtual display
        print(f"{_CYAN}🖥️  Creating virtual display...{_RESET}")
        display = VirtualDisplay(
            resolution=config.resolution,
            refresh_rate=config.refresh_rate,
        )
        display.create()
        print(f"  {_GREEN}✓ {display.name}{_RESET} — {config.resolution}@{config.refresh_rate}Hz")

        # Step 2: Start screen capture
        print(f"{_CYAN}📸 Starting screen capture...{_RESET}")
        capture = ScreenCapture(
            output_name=display.name,
            fps=config.target_fps,
            quality=config.jpeg_quality,
        )
        capture.start()
        print(f"  {_GREEN}✓ Capturing at {config.target_fps} FPS, JPEG quality {config.jpeg_quality}{_RESET}")

        # Step 3: Start mDNS advertising
        if not args.no_discovery:
            print(f"{_CYAN}🔍 Starting network discovery...{_RESET}")
            advertiser = ServiceAdvertiser(
                port=config.port,
                name=config.service_name,
                resolution=config.resolution,
            )
            advertiser.start()
            local_ip = advertiser.local_ip
            print(f"  {_GREEN}✓ Advertising as {config.service_name}._linuxextend._tcp.local.{_RESET}")
        else:
            from .discovery import _get_local_ip
            local_ip = _get_local_ip()

        # Set global references for the FastAPI app
        server_module.capture_engine = capture
        server_module.display_info = display.get_info()
        server_module.server_start_time = time.time()

        # Print connection info
        adb_path = os.path.expanduser("~/Android/Sdk/platform-tools/adb")
        adb_cmd = f"{adb_path} reverse tcp:{config.port} tcp:{config.port}"

        print(f"""
{_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{_RESET}
{_BOLD} Ready! Connect your tablet:{_RESET}

 {_GREEN}📡 Wi-Fi:{_RESET}  ws://{local_ip}:{config.port}/ws/screen
 {_GREEN}🌐 Test:{_RESET}   http://{local_ip}:{config.port}/
 {_GREEN}📱 USB:{_RESET}    {_DIM}{adb_cmd}{_RESET}
           then connect to ws://127.0.0.1:{config.port}/ws/screen
{_BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{_RESET}
""")

        # Step 4: Run the server (blocks until interrupted)
        uvicorn.run(
            server_module.app,
            host=config.host,
            port=config.port,
            log_level="warning",
        )

    except VirtualDisplayError as e:
        print(f"{_RED}✗ Display error: {e}{_RESET}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        print(f"{_RED}✗ Fatal error: {e}{_RESET}")
        sys.exit(1)
    finally:
        shutdown()


if __name__ == "__main__":
    main()
