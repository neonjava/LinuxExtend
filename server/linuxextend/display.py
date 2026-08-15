"""Virtual display management for Hyprland headless outputs."""

import json
import logging
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)


class VirtualDisplayError(Exception):
    """Raised when virtual display operations fail."""


class VirtualDisplay:
    """Creates and manages a Hyprland headless virtual output.

    Usage:
        with VirtualDisplay(resolution="1920x1080") as display:
            print(f"Created: {display.name}")
            # display is active until context manager exits

    Or manually:
        display = VirtualDisplay()
        display.create()
        # ...
        display.remove()
    """

    def __init__(
        self,
        resolution: str = "1920x1080",
        refresh_rate: int = 60,
        position: str = "auto",
    ):
        self.resolution = resolution
        self.refresh_rate = refresh_rate
        self.position = position
        self.name: str | None = None
        self._created = False

    def __enter__(self) -> "VirtualDisplay":
        self.create()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.remove()

    def _run_hyprctl(self, *args: str) -> str:
        """Run a hyprctl command and return stdout."""
        cmd = ["hyprctl", *args]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                raise VirtualDisplayError(
                    f"hyprctl {' '.join(args)} failed: {result.stderr.strip()}"
                )
            return result.stdout.strip()
        except FileNotFoundError:
            raise VirtualDisplayError(
                "hyprctl not found. Is Hyprland running?"
            )
        except subprocess.TimeoutExpired:
            raise VirtualDisplayError(
                f"hyprctl {' '.join(args)} timed out"
            )

    def _get_monitors(self) -> list[dict]:
        """Get all monitors as JSON."""
        output = self._run_hyprctl("monitors", "all", "-j")
        return json.loads(output)

    def _get_headless_names(self) -> set[str]:
        """Get names of all current HEADLESS outputs."""
        monitors = self._get_monitors()
        return {
            m["name"]
            for m in monitors
            if m["name"].startswith("HEADLESS-")
        }

    def _get_primary_monitor(self) -> dict | None:
        """Find the primary (focused) monitor."""
        monitors = self._get_monitors()
        for m in monitors:
            if m.get("focused", False):
                return m
        # Fallback: first non-headless monitor
        for m in monitors:
            if not m["name"].startswith("HEADLESS-"):
                return m
        return None

    def create(self) -> str:
        """Create a new headless virtual display.

        Returns the output name (e.g. 'HEADLESS-4').
        """
        if self._created:
            raise VirtualDisplayError("Display already created")

        # Snapshot current headless outputs
        before = self._get_headless_names()

        # Create the headless output
        result = self._run_hyprctl("output", "create", "headless")
        if "ok" not in result.lower():
            raise VirtualDisplayError(f"Failed to create headless output: {result}")

        # Brief wait for Hyprland to register the new output
        time.sleep(0.3)

        # Find the new output by diffing
        after = self._get_headless_names()
        new_outputs = after - before

        if not new_outputs:
            raise VirtualDisplayError(
                "Headless output was created but could not be found in monitor list"
            )

        self.name = new_outputs.pop()
        self._created = True
        logger.info("Created headless output: %s", self.name)

        # Configure resolution and position
        self._configure()

        return self.name

    def _configure(self) -> None:
        """Configure the resolution, refresh rate, and position of the virtual display."""
        if not self.name:
            return

        # Determine position
        if self.position == "auto":
            primary = self._get_primary_monitor()
            if primary:
                # Place to the right of the primary monitor
                pos_x = primary["x"] + primary["width"]
                pos_y = primary["y"]
                position_str = f"{pos_x}x{pos_y}"
            else:
                position_str = "0x0"
        else:
            position_str = self.position

        # Apply monitor configuration
        # Format: hyprctl keyword monitor NAME,WxH@R,POS,SCALE
        monitor_rule = (
            f"{self.name},"
            f"{self.resolution}@{self.refresh_rate},"
            f"{position_str},"
            f"1"
        )

        result = self._run_hyprctl("keyword", "monitor", monitor_rule)
        if "ok" not in result.lower() and "error" in result.lower():
            logger.warning("Monitor configuration warning: %s", result)
        else:
            logger.info(
                "Configured %s: %s@%dHz at %s",
                self.name, self.resolution, self.refresh_rate, position_str,
            )

    def remove(self) -> None:
        """Remove the headless virtual display."""
        if not self._created or not self.name:
            return

        try:
            result = self._run_hyprctl("output", "remove", self.name)
            if "ok" in result.lower():
                logger.info("Removed headless output: %s", self.name)
            else:
                logger.warning("Unexpected result removing %s: %s", self.name, result)
        except VirtualDisplayError as e:
            logger.error("Failed to remove display %s: %s", self.name, e)
        finally:
            self._created = False

    def get_info(self) -> dict:
        """Get current info about this virtual display."""
        if not self.name:
            return {"status": "not created"}

        monitors = self._get_monitors()
        for m in monitors:
            if m["name"] == self.name:
                return {
                    "name": m["name"],
                    "resolution": f"{m['width']}x{m['height']}",
                    "refresh_rate": m.get("refreshRate", 0),
                    "position": f"{m['x']}x{m['y']}",
                    "active_workspace": m.get("activeWorkspace", {}).get("name", ""),
                    "focused": m.get("focused", False),
                    "dpms": m.get("dpmsStatus", False),
                }

        return {"status": "not found", "name": self.name}

    @property
    def is_active(self) -> bool:
        """Check if the display is currently active."""
        if not self.name or not self._created:
            return False
        info = self.get_info()
        return info.get("status") != "not found"
