"""Tests for LinuxExtend server configuration."""

from linuxextend.config import Config


def test_default_config():
    config = Config()
    assert config.resolution == "1920x1080"
    assert config.width == 1920
    assert config.height == 1080
    assert config.refresh_rate == 60
    assert config.position == "auto"
    assert config.target_fps == 25
    assert config.jpeg_quality == 75
    assert config.host == "0.0.0.0"
    assert config.port == 8080
    assert config.frame_interval == 1.0 / 25


def test_custom_config():
    config = Config(
        resolution="1920x1200",
        target_fps=30,
        jpeg_quality=85,
        port=9090,
    )
    assert config.resolution == "1920x1200"
    assert config.width == 1920
    assert config.height == 1200
    assert config.target_fps == 30
    assert config.jpeg_quality == 85
    assert config.port == 9090
    assert abs(config.frame_interval - 1.0 / 30) < 1e-6
