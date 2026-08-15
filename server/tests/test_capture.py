"""Tests for ScreenCapture parallel worker logic and frame getters."""

import pytest
import threading
from linuxextend.capture import ScreenCapture, CaptureError


def test_capture_initialization():
    capture = ScreenCapture(output_name="HEADLESS-1", fps=30, quality=50, num_workers=3)
    assert capture.output_name == "HEADLESS-1"
    assert capture.target_fps == 30
    assert capture.quality == 50
    assert capture.num_workers == 3
    assert capture.is_running is False
    assert capture.actual_fps == 0.0


def test_frame_getters_empty():
    capture = ScreenCapture(output_name="HEADLESS-1", fps=30)
    assert capture.get_frame() is None
    frame, frame_id = capture.get_frame_with_id()
    assert frame is None
    assert frame_id == 0


def test_frame_getters_with_data():
    capture = ScreenCapture(output_name="HEADLESS-1", fps=30)
    sample_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF"
    with capture._lock:
        capture._latest_frame = sample_jpg
        capture._frame_id = 42

    assert capture.get_frame() == sample_jpg
    frame, frame_id = capture.get_frame_with_id()
    assert frame == sample_jpg
    assert frame_id == 42


def test_lifecycle_start_stop():
    capture = ScreenCapture(output_name="HEADLESS-1", fps=30, num_workers=2)
    # Start and stop without errors
    capture.start()
    assert capture.is_running is True
    capture.stop()
    assert capture.is_running is False
