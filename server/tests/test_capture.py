"""Tests for ScreenCapture PPM parsing and frame logic."""

import numpy as np
import pytest
from linuxextend.capture import ScreenCapture


def test_ppm_parsing_valid():
    capture = ScreenCapture.__new__(ScreenCapture)
    # Create simple 2x2 RGB image PPM:
    # P6\n2 2\n255\n<12 bytes>
    raw_pixels = bytes([
        255, 0, 0,    0, 255, 0,
        0, 0, 255,    255, 255, 255,
    ])
    ppm_data = b"P6\n2 2\n255\n" + raw_pixels
    img = capture._parse_ppm(ppm_data)

    assert img is not None
    assert img.shape == (2, 2, 3)
    assert np.array_equal(img[0, 0], [255, 0, 0])
    assert np.array_equal(img[0, 1], [0, 255, 0])
    assert np.array_equal(img[1, 0], [0, 0, 255])
    assert np.array_equal(img[1, 1], [255, 255, 255])


def test_ppm_parsing_with_comments():
    capture = ScreenCapture.__new__(ScreenCapture)
    raw_pixels = bytes([10, 20, 30, 40, 50, 60])
    ppm_data = b"P6\n# Created by grim\n2 1\n255\n" + raw_pixels
    img = capture._parse_ppm(ppm_data)

    assert img is not None
    assert img.shape == (1, 2, 3)
    assert np.array_equal(img[0, 0], [10, 20, 30])
    assert np.array_equal(img[0, 1], [40, 50, 60])


def test_ppm_parsing_invalid():
    capture = ScreenCapture.__new__(ScreenCapture)
    assert capture._parse_ppm(b"NOT_PPM") is None
    assert capture._parse_ppm(b"P6\n10 10\n255\nshort") is None


def test_dirty_frame_detection():
    capture = ScreenCapture.__new__(ScreenCapture)
    capture._prev_hash = None

    frame1 = np.zeros((100, 100, 3), dtype=np.uint8)
    assert capture._is_frame_dirty(frame1) is True
    # Second check with same frame should report not dirty
    assert capture._is_frame_dirty(frame1) is False

    # Modified frame
    frame2 = frame1.copy()
    frame2[::32, ::32, :] = 255
    assert capture._is_frame_dirty(frame2) is True
