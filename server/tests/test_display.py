"""Tests for VirtualDisplay Hyprland output management."""

import json
from unittest.mock import MagicMock, patch
import pytest
from linuxextend.display import VirtualDisplay, VirtualDisplayError


def test_virtual_display_init():
    display = VirtualDisplay(resolution="1920x1200", refresh_rate=90, position="0x0")
    assert display.resolution == "1920x1200"
    assert display.refresh_rate == 90
    assert display.position == "0x0"
    assert display.name is None
    assert display.is_active is False


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
