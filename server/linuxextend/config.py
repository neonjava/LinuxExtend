"""Configuration for LinuxExtend server."""

from dataclasses import dataclass


@dataclass
class Config:
    """Server configuration with sensible defaults."""

    # Virtual display settings
    resolution: str = "1920x1080"
    refresh_rate: int = 60
    position: str = "auto"  # "auto" = right of primary monitor

    # Capture settings
    target_fps: int = 25
    jpeg_quality: int = 75

    # Server settings
    host: str = "0.0.0.0"
    port: int = 8080

    # mDNS settings
    service_name: str = "LinuxExtend"

    @property
    def width(self) -> int:
        return int(self.resolution.split("x")[0])

    @property
    def height(self) -> int:
        return int(self.resolution.split("x")[1])

    @property
    def frame_interval(self) -> float:
        return 1.0 / self.target_fps
