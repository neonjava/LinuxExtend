"""Tests for VirtualDisplay Hyprland output management."""

import json
from unittest.mock import MagicMock, patch
import pytest
from linuxextend.display import VirtualDisplay, VirtualDisplayError


def test_virtual_display_left_position():
    display = VirtualDisplay(resolution="1920x1080", position="left", transform=1)
    primary = {"name": "eDP-1", "x": 0, "y": 0, "width": 1920, "height": 1080, "refreshRate": 144, "scale": 1.0}
    with patch.object(display, "_get_primary_monitor", return_value=primary):
        with patch.object(display, "_run_hyprctl", return_value="ok") as mock_hyprctl:
            pos = display._calc_position()
            assert pos == "0x0"
            # Primary should be shifted right by effective width (1080)
            mock_hyprctl.assert_called_with("keyword", "monitor", "eDP-1,1920x1080@144,1080x0,1.0")


def test_virtual_display_create_and_remove():
    display = VirtualDisplay(resolution="1920x1080", refresh_rate=60)

    # Mock hyprctl responses
    initial_monitors = [
        {"name": "eDP-1", "x": 0, "y": 0, "width": 1920, "height": 1080, "focused": True}
    ]
    after_monitors = [
        {"name": "eDP-1", "x": 0, "y": 0, "width": 1920, "height": 1080, "focused": True},
        {"name": "HEADLESS-1", "x": 1920, "y": 0, "width": 1920, "height": 1080, "focused": False}
    ]

    created_called = False

    with patch.object(display, "_run_hyprctl") as mock_run:
        def side_effect(*args):
            nonlocal created_called
            if args == ("monitors", "all", "-j"):
                if not created_called:
                    return json.dumps(initial_monitors)
                return json.dumps(after_monitors)
            if args == ("output", "create", "headless"):
                created_called = True
                return "ok"
            if args[0] == "keyword" and args[1] == "monitor":
                return "ok"
            if args == ("output", "remove", "HEADLESS-1"):
                return "ok"
            return ""

        mock_run.side_effect = side_effect

        name = display.create()
        assert name == "HEADLESS-1"
        assert display.is_active is True

        info = display.get_info()
        assert info["name"] == "HEADLESS-1"
        assert info["resolution"] == "1920x1080"

        display.remove()
        assert display.is_active is False


def test_virtual_display_hyprctl_not_found():
    display = VirtualDisplay()
    with patch("subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(VirtualDisplayError, match="hyprctl not found"):
            display._run_hyprctl("monitors", "all", "-j")
